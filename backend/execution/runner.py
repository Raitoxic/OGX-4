from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from backend.agents.llm_provider import get_agent_provider
from backend.autonomy.service import evaluate_step_approval, record_signal_and_adapt
from backend.checkpoints.service import create_checkpoint
from backend.core.config import settings
from backend.database.session import SessionLocal
from backend.models.task import ExecutionStep, Task
from backend.models.user import User
from backend.orchestration.state_machine import StepStatus, TaskStatus
from backend.services.artifact_service import upsert_ai_section
from backend.services.history_service import record_event
from backend.streaming.broker import sse_broker


@dataclass
class ExecutionHandle:
    task_id: str
    execution_token: str = field(default_factory=lambda: str(uuid.uuid4()))
    interrupt_event: asyncio.Event = field(default_factory=asyncio.Event)
    pause_event: asyncio.Event = field(default_factory=asyncio.Event)
    done_event: asyncio.Event = field(default_factory=asyncio.Event)
    async_task: Optional[asyncio.Task] = None
    is_atomic_commit: bool = False
    stop_reason: Optional[str] = None


async def _interruptible_sleep(duration: float, handle: ExecutionHandle) -> bool:
    """
    Waits up to `duration` seconds, waking immediately if interrupt_event or pause_event fires.
    Returns True if stopped early by interrupt or pause, False if full duration elapsed.
    """
    if duration <= 0:
        return handle.interrupt_event.is_set() or handle.pause_event.is_set()
    if handle.interrupt_event.is_set() or handle.pause_event.is_set():
        return True

    int_wait = asyncio.create_task(handle.interrupt_event.wait())
    pause_wait = asyncio.create_task(handle.pause_event.wait())
    try:
        done, pending = await asyncio.wait(
            {int_wait, pause_wait},
            timeout=duration,
            return_when=asyncio.FIRST_COMPLETED,
        )
        for p in pending:
            p.cancel()
        return len(done) > 0
    finally:
        for t in (int_wait, pause_wait):
            if not t.done():
                t.cancel()


class ExecutionManager:
    """Manages active stateful agent execution loops with duplicate-run protection and genuine cancellation."""

    def __init__(self) -> None:
        self._handles: Dict[str, ExecutionHandle] = {}

    def get_handle(self, task_id: str) -> Optional[ExecutionHandle]:
        handle = self._handles.get(task_id)
        if handle and handle.async_task and handle.async_task.done():
            self._handles.pop(task_id, None)
            return None
        return handle

    def is_running(self, task_id: str) -> bool:
        return self.get_handle(task_id) is not None

    def launch(self, task_id: str, user_id: str) -> ExecutionHandle:
        existing = self.get_handle(task_id)
        if existing is not None:
            return existing

        handle = ExecutionHandle(task_id=task_id)
        self._handles[task_id] = handle
        handle.async_task = asyncio.create_task(self._run_loop(task_id, user_id, handle))
        return handle

    async def request_interrupt(self, task_id: str, wait_timeout: float = 5.0) -> Dict[str, object]:
        handle = self.get_handle(task_id)
        if not handle:
            return {"was_running": False, "deferred_atomic": False}

        deferred = handle.is_atomic_commit
        handle.stop_reason = "interrupt"
        handle.interrupt_event.set()

        if deferred:
            sse_broker.publish(
                task_id,
                "activity_event",
                {
                    "event_type": "INTERRUPT_PENDING",
                    "actor": "system",
                    "summary": "Interrupt received during atomic save — safely finishing commit before halting.",
                },
            )

        try:
            await asyncio.wait_for(handle.done_event.wait(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            pass
        return {"was_running": True, "deferred_atomic": deferred}

    async def request_pause(self, task_id: str, wait_timeout: float = 5.0) -> Dict[str, object]:
        handle = self.get_handle(task_id)
        if not handle:
            return {"was_running": False}

        handle.stop_reason = "pause"
        handle.pause_event.set()
        try:
            await asyncio.wait_for(handle.done_event.wait(), timeout=wait_timeout)
        except asyncio.TimeoutError:
            pass
        return {"was_running": True}

    async def abort_for_rollback(self, task_id: str) -> None:
        handle = self.get_handle(task_id)
        if handle:
            handle.stop_reason = "rollback"
            handle.interrupt_event.set()
            try:
                await asyncio.wait_for(handle.done_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                if handle.async_task and not handle.async_task.done():
                    handle.async_task.cancel()

    async def _run_loop(self, task_id: str, user_id: str, handle: ExecutionHandle) -> None:
        db = SessionLocal()
        provider = get_agent_provider()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            user = db.query(User).filter(User.id == user_id).first()
            if not task or not user:
                return

            if task.started_at is None:
                task.started_at = datetime.now(timezone.utc)
            task.status = TaskStatus.RUNNING
            task.error_message = None
            task.is_interruptible = True
            task.current_activity = "Resuming stateful execution..."
            db.commit()

            sse_broker.publish(
                task_id,
                "task_state_changed",
                {"status": task.status, "current_activity": task.current_activity},
            )

            while True:
                db.expire_all()
                task = db.query(Task).filter(Task.id == task_id).first()
                user = db.query(User).filter(User.id == user_id).first()
                if not task or not user:
                    return

                steps: List[ExecutionStep] = (
                    db.query(ExecutionStep)
                    .filter(ExecutionStep.task_id == task_id)
                    .order_by(ExecutionStep.step_order.asc())
                    .all()
                )

                # Skip all already-COMPLETED steps (never redo completed work!)
                next_step: Optional[ExecutionStep] = None
                for s in steps:
                    if s.status != StepStatus.COMPLETED:
                        next_step = s
                        break

                if next_step is None:
                    # All steps complete
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now(timezone.utc)
                    task.current_step_index = len(steps)
                    task.is_interruptible = True
                    task.current_activity = "Task completed. Shared artifact is ready for review and co-editing."
                    create_checkpoint(
                        db,
                        task=task,
                        user_id=user.id,
                        trigger_type="completed",
                        label="Final completed execution state",
                        commit=False,
                    )
                    record_event(
                        db,
                        task_id=task.id,
                        user_id=user.id,
                        event_type="TASK_COMPLETED",
                        actor="agent",
                        summary=f"Completed all {len(steps)} execution steps for '{task.title}'.",
                        payload={"total_execution_ms": task.total_execution_ms},
                    )
                    db.commit()
                    sse_broker.publish(
                        task_id,
                        "task_completed",
                        {
                            "status": task.status,
                            "current_activity": task.current_activity,
                            "total_execution_ms": task.total_execution_ms,
                        },
                    )
                    return

                # Never silently execute a rejected step
                if next_step.status == StepStatus.REJECTED:
                    task.status = TaskStatus.AWAITING_APPROVAL
                    task.current_step_index = next_step.step_order
                    task.current_activity = (
                        f"Step {next_step.step_order} ('{next_step.title}') was rejected. "
                        "Edit, generate an alternative, or approve before continuing."
                    )
                    db.commit()
                    sse_broker.publish(
                        task_id,
                        "approval_requested",
                        {
                            "step_id": next_step.id,
                            "step_order": next_step.step_order,
                            "title": next_step.title,
                            "reason": "Step was rejected and requires explicit human action.",
                        },
                    )
                    return

                # Check stop signals before scheduling next step
                if handle.interrupt_event.is_set() or handle.pause_event.is_set():
                    await self._finalize_stop(db, task, user, next_step, handle, preserve_step_pending=True)
                    return

                # Evaluate adaptive autonomy & safety gate for this step
                req_approval, approval_reason = evaluate_step_approval(task, next_step, user)
                next_step.requires_approval = req_approval
                next_step.approval_reason = approval_reason

                if req_approval and not next_step.approved_by_user:
                    next_step.status = StepStatus.AWAITING_APPROVAL
                    next_step.approval_requested_at = datetime.now(timezone.utc)
                    task.status = TaskStatus.AWAITING_APPROVAL
                    task.current_step_index = next_step.step_order
                    task.current_activity = f"Awaiting approval for Step {next_step.step_order}: {next_step.title}"
                    record_event(
                        db,
                        task_id=task.id,
                        user_id=user.id,
                        step_id=next_step.id,
                        event_type="STEP_APPROVAL_REQUESTED",
                        actor="agent",
                        summary=f"Requested human approval for Step {next_step.step_order} ('{next_step.title}'): {approval_reason}",
                        payload={"risk_level": next_step.risk_level, "reason": approval_reason},
                    )
                    db.commit()
                    sse_broker.publish(
                        task_id,
                        "approval_requested",
                        {
                            "task_status": task.status,
                            "step_id": next_step.id,
                            "step_order": next_step.step_order,
                            "title": next_step.title,
                            "risk_level": next_step.risk_level,
                            "reason": approval_reason,
                        },
                    )
                    return

                # Begin executing next_step
                step_t0 = time.monotonic()
                next_step.status = StepStatus.RUNNING
                if next_step.started_at is None:
                    next_step.started_at = datetime.now(timezone.utc)
                task.status = TaskStatus.RUNNING
                task.current_step_index = next_step.step_order
                task.is_interruptible = True
                task.current_activity = f"Executing Step {next_step.step_order}/{len(steps)}: {next_step.title}"
                record_event(
                    db,
                    task_id=task.id,
                    user_id=user.id,
                    step_id=next_step.id,
                    event_type="STEP_STARTED",
                    actor="agent",
                    summary=f"Started Step {next_step.step_order}: '{next_step.title}'",
                    payload={"step_order": next_step.step_order, "risk_level": next_step.risk_level},
                )
                db.commit()
                sse_broker.publish(
                    task_id,
                    "step_updated",
                    {
                        "step_id": next_step.id,
                        "step_order": next_step.step_order,
                        "status": next_step.status,
                        "task_status": task.status,
                        "current_activity": task.current_activity,
                    },
                )

                additional = [
                    item["text"] for item in json.loads(task.additional_instructions_json or "[]")
                ]
                step_dict = {
                    "id": next_step.id,
                    "step_order": next_step.step_order,
                    "title": next_step.title,
                    "description": next_step.description,
                    "expected_outcome": next_step.expected_outcome,
                    "risk_level": next_step.risk_level,
                    "is_locked": next_step.is_locked,
                    "user_modified": next_step.user_modified,
                    "sources": json.loads(next_step.sources_json or "[]"),
                }
                completed_stages: List[str] = json.loads(next_step.completed_stages_json or "[]")
                stages = provider.get_execution_stages(task.topic, step_dict, additional)

                # Cooperative interruptible micro-stages
                for idx_stage, stage in enumerate(stages, start=1):
                    if stage.stage_key in completed_stages:
                        continue

                    if handle.interrupt_event.is_set() or handle.pause_event.is_set():
                        await self._finalize_stop(db, task, user, next_step, handle, preserve_step_pending=False)
                        return

                    task.current_activity = f"Step {next_step.step_order} ({idx_stage}/{len(stages)}): {stage.label}"
                    next_step.partial_output = stage.partial_markdown
                    upsert_ai_section(
                        db,
                        task=task,
                        step=next_step,
                        heading=next_step.title,
                        content=stage.partial_markdown,
                        is_partial=True,
                    )
                    db.commit()
                    sse_broker.publish(
                        task_id,
                        "step_progress",
                        {
                            "step_id": next_step.id,
                            "step_order": next_step.step_order,
                            "stage": stage.stage_key,
                            "stage_index": idx_stage,
                            "stage_total": len(stages),
                            "activity": task.current_activity,
                            "detail": stage.detail,
                            "is_interruptible": True,
                        },
                    )

                    stopped_early = await _interruptible_sleep(settings.demo_step_stage_delay_sec, handle)
                    if stopped_early:
                        await self._finalize_stop(db, task, user, next_step, handle, preserve_step_pending=False)
                        return

                    completed_stages.append(stage.stage_key)
                    next_step.completed_stages_json = json.dumps(completed_stages)
                    db.commit()

                # Final check before atomic generation & commit
                if handle.interrupt_event.is_set() or handle.pause_event.is_set():
                    await self._finalize_stop(db, task, user, next_step, handle, preserve_step_pending=False)
                    return

                # Reload latest mid-execution instructions just in case the user added one during stages
                db.refresh(task)
                additional = [
                    item["text"] for item in json.loads(task.additional_instructions_json or "[]")
                ]

                prior_outputs = [
                    {"title": s.title, "output": s.output_content[:1200]}
                    for s in steps
                    if s.status == StepStatus.COMPLETED and s.output_content
                ]

                # Atomic commit boundary (explicitly communicated to UI if interrupt arrives here)
                handle.is_atomic_commit = True
                task.is_interruptible = False
                task.current_activity = f"Step {next_step.step_order}: Committing verified output to shared artifact..."
                db.commit()
                sse_broker.publish(
                    task_id,
                    "step_progress",
                    {
                        "step_id": next_step.id,
                        "step_order": next_step.step_order,
                        "stage": "atomic_commit",
                        "activity": task.current_activity,
                        "is_interruptible": False,
                    },
                )

                result = await provider.execute_step(
                    prompt=task.prompt,
                    topic=task.topic,
                    step=step_dict,
                    prior_outputs=prior_outputs,
                    additional_instructions=additional,
                )

                elapsed_ms = max(1, int((time.monotonic() - step_t0) * 1000))
                next_step.output_content = result.output_markdown
                next_step.partial_output = ""
                next_step.confidence_basis = result.confidence_basis
                next_step.uncertainty_notes = result.uncertainty_notes
                if result.sources:
                    next_step.sources_json = json.dumps(result.sources)
                next_step.status = StepStatus.COMPLETED
                next_step.duration_ms += elapsed_ms
                next_step.completed_at = datetime.now(timezone.utc)
                task.total_execution_ms += elapsed_ms

                if next_step.user_modified and result.honored_user_modifications:
                    task.plan_edits_honored_count += 1

                upsert_ai_section(
                    db,
                    task=task,
                    step=next_step,
                    heading=result.section_heading,
                    content=result.output_markdown,
                    is_partial=False,
                )

                record_event(
                    db,
                    task_id=task.id,
                    user_id=user.id,
                    step_id=next_step.id,
                    event_type="STEP_COMPLETED",
                    actor="agent",
                    summary=f"Completed Step {next_step.step_order}: '{next_step.title}' ({elapsed_ms} ms)",
                    payload={
                        "step_order": next_step.step_order,
                        "duration_ms": elapsed_ms,
                        "honored_user_modifications": result.honored_user_modifications,
                    },
                )

                create_checkpoint(
                    db,
                    task=task,
                    user_id=user.id,
                    trigger_type="step_completed",
                    label=f"After Step {next_step.step_order}: {next_step.title}",
                    commit=False,
                )

                handle.is_atomic_commit = False
                task.is_interruptible = True
                db.commit()

                sse_broker.publish(
                    task_id,
                    "step_updated",
                    {
                        "step_id": next_step.id,
                        "step_order": next_step.step_order,
                        "status": next_step.status,
                        "duration_ms": next_step.duration_ms,
                        "task_status": task.status,
                    },
                )

                # If interrupt or pause was requested during atomic commit, halt cleanly before next step
                if handle.interrupt_event.is_set() or handle.pause_event.is_set():
                    await self._finalize_stop(db, task, user, None, handle, preserve_step_pending=True)
                    return

        except Exception as exc:
            handle.is_atomic_commit = False
            try:
                db.rollback()
                task = db.query(Task).filter(Task.id == task_id).first()
                if task:
                    running_step = (
                        db.query(ExecutionStep)
                        .filter(ExecutionStep.task_id == task_id, ExecutionStep.status == StepStatus.RUNNING)
                        .first()
                    )
                    if running_step:
                        running_step.status = StepStatus.FAILED
                    task.status = TaskStatus.FAILED
                    task.is_interruptible = True
                    task.error_message = str(exc)
                    task.current_activity = f"Execution error: {str(exc)[:220]}"
                    record_event(
                        db,
                        task_id=task.id,
                        user_id=task.user_id,
                        step_id=running_step.id if running_step else None,
                        event_type="TASK_FAILED",
                        actor="system",
                        summary=f"Execution failed: {str(exc)[:260]}",
                        payload={"error": str(exc)},
                    )
                    create_checkpoint(
                        db,
                        task=task,
                        user_id=task.user_id,
                        trigger_type="interrupt",
                        label="Error recovery checkpoint",
                        commit=False,
                    )
                    db.commit()
                    sse_broker.publish(
                        task_id,
                        "task_failed",
                        {"status": task.status, "error": str(exc)},
                    )
            except Exception:
                pass
        finally:
            handle.is_atomic_commit = False
            handle.done_event.set()
            if self._handles.get(task_id) is handle:
                self._handles.pop(task_id, None)
            db.close()

    async def _finalize_stop(
        self,
        db,
        task: Task,
        user: User,
        active_step: Optional[ExecutionStep],
        handle: ExecutionHandle,
        preserve_step_pending: bool,
    ) -> None:
        if handle.stop_reason == "rollback":
            return

        is_interrupt = handle.stop_reason == "interrupt" or handle.interrupt_event.is_set()
        target_task_status = TaskStatus.INTERRUPTED if is_interrupt else TaskStatus.PAUSED
        target_step_status = StepStatus.INTERRUPTED if is_interrupt else StepStatus.PAUSED

        if active_step is not None and not preserve_step_pending and active_step.status == StepStatus.RUNNING:
            active_step.status = target_step_status

        task.status = target_task_status
        task.is_interruptible = True

        if is_interrupt:
            task.interruption_count += 1
            step_label = f"during Step {active_step.step_order} ('{active_step.title}')" if active_step else "between steps"
            task.current_activity = (
                f"Interrupted safely {step_label}. Completed steps and partial work preserved in checkpoint."
            )
            record_signal_and_adapt(
                db,
                user=user,
                task=task,
                signal_type="interrupt",
                step_risk_level=active_step.risk_level if active_step else "low",
                note=f"User interrupted execution {step_label}",
            )
            record_event(
                db,
                task_id=task.id,
                user_id=user.id,
                step_id=active_step.id if active_step else None,
                event_type="TASK_INTERRUPTED",
                actor="human",
                summary=f"Interrupted execution {step_label}. State saved to persistent checkpoint.",
                payload={"step_order": active_step.step_order if active_step else None},
            )
            cp = create_checkpoint(
                db,
                task=task,
                user_id=user.id,
                trigger_type="interrupt",
                label=f"Mid-execution interrupt {step_label}",
                commit=False,
            )
            db.commit()
            sse_broker.publish(
                task.id,
                "task_interrupted",
                {
                    "status": task.status,
                    "current_activity": task.current_activity,
                    "checkpoint_id": cp.id,
                    "checkpoint_version": cp.version_number,
                },
            )
        else:
            step_label = f"at Step {active_step.step_order}" if active_step else "between steps"
            task.current_activity = f"Paused {step_label}. Edit steps or click Resume when ready."
            record_event(
                db,
                task_id=task.id,
                user_id=user.id,
                step_id=active_step.id if active_step else None,
                event_type="TASK_PAUSED",
                actor="human",
                summary=f"Paused execution {step_label}.",
            )
            cp = create_checkpoint(
                db,
                task=task,
                user_id=user.id,
                trigger_type="pause",
                label=f"Paused execution {step_label}",
                commit=False,
            )
            db.commit()
            sse_broker.publish(
                task.id,
                "task_state_changed",
                {
                    "status": task.status,
                    "current_activity": task.current_activity,
                    "checkpoint_id": cp.id,
                },
            )


def recover_orphaned_running_tasks() -> None:
    """
    Ensures database consistency after a backend restart:
    any task left in RUNNING/RESUMING with no active in-memory runner transitions cleanly to INTERRUPTED
    while keeping all completed steps and checkpoints intact.
    """
    db = SessionLocal()
    try:
        orphans = (
            db.query(Task)
            .filter(Task.status.in_([TaskStatus.RUNNING, TaskStatus.RESUMING]))
            .all()
        )
        for task in orphans:
            running_steps = (
                db.query(ExecutionStep)
                .filter(ExecutionStep.task_id == task.id, ExecutionStep.status == StepStatus.RUNNING)
                .all()
            )
            for s in running_steps:
                s.status = StepStatus.INTERRUPTED
            task.status = TaskStatus.INTERRUPTED
            task.is_interruptible = True
            task.current_activity = (
                "Recovered from server restart — completed steps and checkpoints preserved. Click Resume to continue."
            )
            record_event(
                db,
                task_id=task.id,
                user_id=task.user_id,
                event_type="TASK_INTERRUPTED",
                actor="system",
                summary="Recovered interrupted task cleanly after backend restart.",
                emit_sse=False,
            )
        if orphans:
            db.commit()
    finally:
        db.close()


execution_manager = ExecutionManager()
