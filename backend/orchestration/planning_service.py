from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.agents.demo_provider import extract_topic
from backend.agents.llm_provider import get_agent_provider
from backend.autonomy.service import apply_policy_to_pending_steps, record_signal_and_adapt
from backend.checkpoints.service import create_checkpoint
from backend.models.artifact import ArtifactRevision, ArtifactSection
from backend.models.task import AgentPlan, ExecutionStep, Task
from backend.models.user import User
from backend.orchestration.state_machine import (
    StepStatus,
    TaskStatus,
    validate_task_transition,
)
from backend.services.history_service import record_event
from backend.services.ml_service import estimate_task_complexity, predict_supervision_for_task
from backend.streaming.broker import sse_broker


async def create_task_and_generate_plan(
    db: Session,
    user: User,
    prompt: str,
    title: Optional[str] = None,
    interaction_mode: str = "vyrox",
    autonomy_mode: Optional[str] = None,
    adaptive_enabled: Optional[bool] = None,
    research_enabled: bool = False,
) -> Task:
    provider = get_agent_provider()
    topic = extract_topic(prompt)
    resolved_title = (title or "").strip() or f"Research Report: {topic}"
    resolved_autonomy = autonomy_mode or user.default_autonomy_mode or "balanced"
    resolved_adaptive = user.adaptive_autonomy_enabled if adaptive_enabled is None else adaptive_enabled
    normalized_mode = "baseline" if interaction_mode == "baseline" else "vyrox"

    task = Task(
        user_id=user.id,
        title=resolved_title[:195],
        prompt=prompt.strip(),
        topic=topic[:195],
        interaction_mode=normalized_mode,
        provider_mode=provider.provider_mode,
        provider_name=provider.provider_name,
        status=TaskStatus.CREATED,
        autonomy_mode=resolved_autonomy,
        adaptive_enabled=resolved_adaptive,
        adaptive_caution_level="normal",
        adaptive_reason="Baseline calibrated policy active.",
        complexity_score=estimate_task_complexity(prompt, 5),
        plan_approved=not user.require_plan_approval,
        current_step_index=0,
        current_activity="Interpreting task prompt...",
        research_enabled=research_enabled,
        research_status="disabled" if not research_enabled else "pending",
    )
    db.add(task)
    db.flush()

    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="TASK_CREATED",
        actor="human",
        summary=f"Created {'VYRO-X' if normalized_mode == 'vyrox' else 'Baseline'} task: '{task.title}'",
        payload={"interaction_mode": normalized_mode, "provider_mode": provider.provider_mode},
    )

    # Conventional Prompt-and-Wait Baseline Mode (for scientific evaluation comparison)
    if normalized_mode == "baseline":
        t0 = time.monotonic()
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        task.current_activity = "Executing conventional Prompt-and-Wait single pass..."
        db.flush()

        baseline = await provider.execute_baseline_report(prompt=task.prompt, topic=task.topic)
        elapsed_ms = max(1, int((time.monotonic() - t0) * 1000))

        step = ExecutionStep(
            task_id=task.id,
            step_order=1,
            title="Single-Pass Prompt-and-Wait Generation",
            description="Conventional black-box single prompt execution without step planning or mid-run intervention.",
            rationale="Baseline interaction comparator for VYRO-X evaluation.",
            expected_outcome="Single final generated report without intermediate checkpoints.",
            risk_level="medium",
            status=StepStatus.COMPLETED,
            confidence_basis=f"{provider.provider_mode.title()} baseline execution ({provider.provider_name}).",
            uncertainty_notes="No interactive plan inspection, step locks, or mid-run edits available in baseline mode.",
            output_content=baseline["content"],
            duration_ms=elapsed_ms,
            started_at=task.started_at,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(step)
        db.flush()

        section = ArtifactSection(
            task_id=task.id,
            step_id=step.id,
            section_order=1,
            heading=baseline["heading"],
            ai_content=baseline["content"],
            current_content=baseline["content"],
            authorship="ai",
            version=1,
        )
        db.add(section)
        db.flush()
        db.add(
            ArtifactRevision(
                task_id=task.id,
                section_id=section.id,
                version=1,
                content=baseline["content"],
                author_type="ai",
                summary="Baseline single-pass output",
            )
        )

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        task.total_execution_ms = elapsed_ms
        task.current_step_index = 1
        task.current_activity = "Completed in Prompt-and-Wait Baseline Mode."
        record_event(
            db,
            task_id=task.id,
            user_id=user.id,
            step_id=step.id,
            event_type="TASK_COMPLETED",
            actor="agent",
            summary=f"Completed Prompt-and-Wait baseline task in {elapsed_ms} ms.",
            payload={"elapsed_ms": elapsed_ms},
        )
        db.commit()
        db.refresh(task)
        return task

    # Interactive VYRO-X Mode: generate inspectable versioned plan
    validate_task_transition(task.status, TaskStatus.PLANNING)
    task.status = TaskStatus.PLANNING
    task.current_activity = "Generating structured execution plan..."
    db.flush()

    specs = await provider.generate_plan(prompt=task.prompt, topic=task.topic)
    plan_row = AgentPlan(
        task_id=task.id,
        version_number=1,
        status="active",
        summary=f"Initial {len(specs)}-step plan for '{task.topic}'",
        step_count=len(specs),
        created_by="agent",
    )
    db.add(plan_row)
    db.flush()

    for idx, spec in enumerate(specs, start=1):
        step = ExecutionStep(
            task_id=task.id,
            plan_id=plan_row.id,
            step_order=idx,
            title=spec.title,
            description=spec.description,
            rationale=spec.rationale,
            expected_outcome=spec.expected_outcome,
            risk_level=spec.risk_level,
            status=StepStatus.PENDING,
            is_locked=False,
            confidence_basis=spec.confidence_basis,
            uncertainty_notes=spec.uncertainty_notes,
            sources_json=json.dumps(spec.sources),
        )
        db.add(step)

    db.flush()
    db.refresh(task)
    apply_policy_to_pending_steps(task, user)
    predict_supervision_for_task(db, user, task, log_prediction=True, commit=False)

    if user.require_plan_approval or resolved_autonomy == "supervised":
        task.status = TaskStatus.AWAITING_APPROVAL
        task.plan_approved = False
        task.current_activity = "Structured plan ready. Review, edit, lock, or approve to begin execution."
    else:
        task.status = TaskStatus.PAUSED
        task.plan_approved = True
        task.current_activity = "Plan ready. Click Start Task to begin execution."

    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="PLAN_GENERATED",
        actor="agent",
        summary=f"Generated {len(specs)}-step execution plan for '{task.topic}' ({provider.provider_mode} mode).",
        payload={"step_count": len(specs), "provider_mode": provider.provider_mode},
    )

    create_checkpoint(
        db,
        task=task,
        user_id=user.id,
        trigger_type="plan_created",
        label="Initial generated execution plan",
        commit=False,
    )

    db.commit()
    db.refresh(task)
    sse_broker.publish(task.id, "plan_generated", {"task_status": task.status, "step_count": len(specs)})
    return task


def edit_step_instruction(
    db: Session,
    task: Task,
    user: User,
    step_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    expected_outcome: Optional[str] = None,
    edit_note: Optional[str] = None,
) -> ExecutionStep:
    step = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.id == step_id, ExecutionStep.task_id == task.id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution step not found.")
    if step.status == StepStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot edit a step while it is actively running. Interrupt or pause execution first.",
        )
    if step.status == StepStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed steps cannot be edited directly. Roll back to an earlier checkpoint to re-run this step.",
        )
    if step.is_locked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This step is locked. Unlock it first if you intentionally want to modify its instructions.",
        )

    if title is not None and title.strip():
        step.title = title.strip()[:195]
    if description is not None and description.strip():
        step.description = description.strip()
    if expected_outcome is not None and expected_outcome.strip():
        step.expected_outcome = expected_outcome.strip()
    if edit_note is not None:
        step.user_edit_note = edit_note.strip()

    was_rejected = step.status == StepStatus.REJECTED
    if was_rejected:
        step.status = StepStatus.PENDING
        step.rejected_reason = None

    step.user_modified = True
    step.revision_number += 1
    task.plan_edits_count += 1

    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="step_edit",
        step_risk_level=step.risk_level,
        note=f"User edited Step {step.step_order}: '{step.title}'",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        step_id=step.id,
        event_type="STEP_EDITED",
        actor="human",
        summary=f"Edited Step {step.step_order} ('{step.title}')",
        payload={"revision_number": step.revision_number, "description_preview": step.description[:140]},
    )

    db.commit()
    db.refresh(step)
    sse_broker.publish(task.id, "step_updated", {"step_id": step.id, "status": step.status, "user_modified": True})
    return step


def set_step_lock(
    db: Session,
    task: Task,
    user: User,
    step_id: str,
    is_locked: bool,
) -> ExecutionStep:
    step = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.id == step_id, ExecutionStep.task_id == task.id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution step not found.")

    step.is_locked = is_locked
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        step_id=step.id,
        event_type="STEP_LOCKED" if is_locked else "STEP_UNLOCKED",
        actor="human",
        summary=f"{'Locked' if is_locked else 'Unlocked'} Step {step.step_order} ('{step.title}')",
        payload={"is_locked": is_locked},
    )
    db.commit()
    db.refresh(step)
    sse_broker.publish(task.id, "step_updated", {"step_id": step.id, "is_locked": is_locked})
    return step


async def replan_unlocked_steps(
    db: Session,
    task: Task,
    user: User,
    reason: str = "",
) -> Task:
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Interrupt or pause active execution before replanning.",
        )
    validate_task_transition(task.status, TaskStatus.PLANNING)

    create_checkpoint(
        db,
        task=task,
        user_id=user.id,
        trigger_type="pre_replan",
        label=f"Before replan ({reason[:60] or 'user request'})",
        commit=False,
    )

    prev_status = task.status
    task.status = TaskStatus.PLANNING
    task.current_activity = "Replanning unlocked pending steps while protecting completed and locked steps..."
    db.flush()

    steps: List[ExecutionStep] = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.task_id == task.id)
        .order_by(ExecutionStep.step_order.asc())
        .all()
    )
    preserved = [s for s in steps if s.status == StepStatus.COMPLETED or s.is_locked]
    mutable = [s for s in steps if s.status != StepStatus.COMPLETED and not s.is_locked]

    if not mutable:
        task.status = prev_status if prev_status != TaskStatus.PLANNING else TaskStatus.AWAITING_APPROVAL
        task.current_activity = "All remaining steps are completed or locked — no steps altered."
        db.commit()
        db.refresh(task)
        return task

    provider = get_agent_provider()
    additional = [item["text"] for item in json.loads(task.additional_instructions_json or "[]")]
    replanned_specs = await provider.replan_unlocked_steps(
        prompt=task.prompt,
        topic=task.topic,
        locked_or_completed_steps=[{"step_order": s.step_order, "title": s.title, "description": s.description} for s in preserved],
        unlocked_pending_steps=[
            {
                "step_order": s.step_order,
                "title": s.title,
                "description": s.description,
                "expected_outcome": s.expected_outcome,
                "risk_level": s.risk_level,
                "sources": json.loads(s.sources_json or "[]"),
            }
            for s in mutable
        ],
        replan_reason=reason,
        additional_instructions=additional,
    )

    # Persist new AgentPlan version for replan traceability
    prev_plans = db.query(AgentPlan).filter(AgentPlan.task_id == task.id).all()
    for p in prev_plans:
        p.status = "superseded"
    new_plan = AgentPlan(
        task_id=task.id,
        version_number=(max((p.version_number for p in prev_plans), default=0) + 1),
        status="active",
        summary=f"Replanned {len(mutable)} unlocked step(s): {(reason or 'updated requirements')[:180]}",
        step_count=len(steps),
        created_by="replan",
    )
    db.add(new_plan)
    db.flush()

    old_mutable: Dict[int, ExecutionStep] = {s.step_order: s for s in mutable}
    referenced: set = set()
    next_order = max((s.step_order for s in steps), default=0)
    added_count = 0
    modified_count = 0

    for spec in replanned_specs:
        change = (spec.replan_change or "").strip().lower()
        key = spec.step_key
        if key is not None and key in old_mutable:
            step_obj = old_mutable[key]
            referenced.add(key)
            step_obj.plan_id = new_plan.id
            step_obj.title = spec.title
            step_obj.description = spec.description
            step_obj.rationale = spec.rationale
            step_obj.expected_outcome = spec.expected_outcome
            step_obj.risk_level = spec.risk_level
            step_obj.confidence_basis = spec.confidence_basis
            step_obj.uncertainty_notes = spec.uncertainty_notes
            step_obj.sources_json = json.dumps(spec.sources)
            step_obj.status = StepStatus.PENDING
            step_obj.approved_by_user = False
            step_obj.rejected_reason = None
            step_obj.completed_stages_json = "[]"
            step_obj.partial_output = ""
            step_obj.replan_change = change if change in ("modified", "unchanged") else "modified"
            step_obj.revision_number += 1
            if step_obj.replan_change == "modified":
                modified_count += 1
        else:
            next_order += 1
            db.add(
                ExecutionStep(
                    task_id=task.id,
                    plan_id=new_plan.id,
                    step_order=next_order,
                    title=spec.title,
                    description=spec.description,
                    rationale=spec.rationale,
                    expected_outcome=spec.expected_outcome,
                    risk_level=spec.risk_level,
                    status=StepStatus.PENDING,
                    requires_approval=False,
                    confidence_basis=spec.confidence_basis,
                    uncertainty_notes=spec.uncertainty_notes,
                    sources_json=json.dumps(spec.sources),
                    replan_change="added",
                )
            )
            added_count += 1

    # Pending steps dropped from the revised plan are marked removed (never executed).
    removed_count = 0
    for key, step_obj in old_mutable.items():
        if key not in referenced:
            step_obj.status = StepStatus.REJECTED
            step_obj.replan_change = "removed"
            step_obj.rejected_reason = "Removed during replan per new instructions."
            removed_count += 1

    db.flush()
    db.refresh(task)
    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="replan",
        step_risk_level="medium",
        note=f"User triggered replan ({len(mutable)} unlocked step(s) updated; {len(preserved)} locked/completed preserved)",
    )
    apply_policy_to_pending_steps(task, user)

    task.status = TaskStatus.AWAITING_APPROVAL
    task.plan_approved = False
    task.current_activity = (
        f"Replanned: {modified_count} modified, {added_count} added, {removed_count} removed; "
        f"preserved {len(preserved)} completed/locked step(s). Review and approve the revised plan."
    )

    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="REPLAN_EXECUTED",
        actor="agent",
        summary=(
            f"Replanned unlocked steps ({modified_count} modified, {added_count} added, {removed_count} removed) "
            f"while preserving {len(preserved)} locked/completed step(s)."
        ),
        payload={
            "reason": reason,
            "modified_count": modified_count,
            "added_count": added_count,
            "removed_count": removed_count,
            "preserved_count": len(preserved),
        },
    )
    create_checkpoint(
        db,
        task=task,
        user_id=user.id,
        trigger_type="plan_created",
        label=f"Replanned execution plan ({reason[:50] or 'updated requirements'})",
        commit=False,
    )

    db.commit()
    db.refresh(task)
    sse_broker.publish(task.id, "plan_generated", {"task_status": task.status, "replanned": True})
    return task
