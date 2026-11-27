from __future__ import annotations

import difflib
import json
from typing import Any, Dict, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.models.artifact import ArtifactRevision, ArtifactSection
from backend.models.checkpoint import Checkpoint
from backend.models.task import ExecutionStep, Task
from backend.models.user import User
from backend.orchestration.state_machine import StepStatus, TaskStatus, validate_task_transition
from backend.services.history_service import record_event
from backend.streaming.broker import sse_broker


def serialize_task_snapshot(db: Session, task: Task) -> Dict[str, Any]:
    steps = (
        db.query(ExecutionStep)
        .filter(ExecutionStep.task_id == task.id)
        .order_by(ExecutionStep.step_order.asc())
        .all()
    )
    sections = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.task_id == task.id)
        .order_by(ArtifactSection.section_order.asc())
        .all()
    )
    return {
        "task": {
            "status": task.status,
            "autonomy_mode": task.autonomy_mode,
            "adaptive_enabled": task.adaptive_enabled,
            "adaptive_caution_level": task.adaptive_caution_level,
            "adaptive_reason": task.adaptive_reason,
            "plan_approved": task.plan_approved,
            "current_step_index": task.current_step_index,
            "current_activity": task.current_activity,
            "additional_instructions": json.loads(task.additional_instructions_json or "[]"),
        },
        "steps": [
            {
                "id": s.id,
                "step_order": s.step_order,
                "title": s.title,
                "description": s.description,
                "rationale": s.rationale,
                "expected_outcome": s.expected_outcome,
                "risk_level": s.risk_level,
                "status": s.status,
                "is_locked": s.is_locked,
                "requires_approval": s.requires_approval,
                "approved_by_user": s.approved_by_user,
                "approval_reason": s.approval_reason,
                "confidence_basis": s.confidence_basis,
                "uncertainty_notes": s.uncertainty_notes,
                "sources": json.loads(s.sources_json or "[]"),
                "output_content": s.output_content,
                "partial_output": s.partial_output,
                "completed_stages": json.loads(s.completed_stages_json or "[]"),
                "user_modified": s.user_modified,
                "user_edit_note": s.user_edit_note,
                "rejected_reason": s.rejected_reason,
                "revision_number": s.revision_number,
                "duration_ms": s.duration_ms,
            }
            for s in steps
        ],
        "artifact_sections": [
            {
                "id": sec.id,
                "step_id": sec.step_id,
                "section_order": sec.section_order,
                "heading": sec.heading,
                "ai_content": sec.ai_content,
                "current_content": sec.current_content,
                "authorship": sec.authorship,
                "version": sec.version,
            }
            for sec in sections
        ],
    }


def create_checkpoint(
    db: Session,
    task: Task,
    user_id: str,
    trigger_type: str,
    label: str,
    commit: bool = False,
) -> Checkpoint:
    snapshot = serialize_task_snapshot(db, task)
    steps_data = snapshot["steps"]
    completed_count = sum(1 for s in steps_data if s["status"] == StepStatus.COMPLETED)

    latest = (
        db.query(Checkpoint)
        .filter(Checkpoint.task_id == task.id)
        .order_by(Checkpoint.version_number.desc())
        .first()
    )
    next_version = (latest.version_number + 1) if latest else 1

    cp = Checkpoint(
        task_id=task.id,
        version_number=next_version,
        label=label[:195],
        trigger_type=trigger_type,
        task_status=task.status,
        current_step_index=task.current_step_index,
        completed_steps_count=completed_count,
        total_steps_count=len(steps_data),
        snapshot_json=json.dumps(snapshot, default=str),
    )
    db.add(cp)
    db.flush()

    record_event(
        db,
        task_id=task.id,
        user_id=user_id,
        event_type="CHECKPOINT_CREATED",
        actor="system" if trigger_type != "manual" else "human",
        summary=f"Saved Checkpoint v{next_version}: {label} ({completed_count}/{len(steps_data)} steps completed)",
        payload={
            "checkpoint_id": cp.id,
            "version_number": next_version,
            "trigger_type": trigger_type,
            "task_status": task.status,
        },
    )

    if commit:
        db.commit()
        db.refresh(cp)

    sse_broker.publish(
        task.id,
        "checkpoint_created",
        {
            "id": cp.id,
            "version_number": cp.version_number,
            "label": cp.label,
            "trigger_type": cp.trigger_type,
            "task_status": cp.task_status,
            "completed_steps_count": cp.completed_steps_count,
            "total_steps_count": cp.total_steps_count,
            "created_at": cp.created_at.isoformat() if cp.created_at else None,
        },
    )
    return cp


def list_checkpoints(db: Session, task_id: str) -> List[Checkpoint]:
    return (
        db.query(Checkpoint)
        .filter(Checkpoint.task_id == task_id)
        .order_by(Checkpoint.version_number.desc())
        .all()
    )


def compare_checkpoints(db: Session, task_id: str, from_checkpoint_id: str, to_checkpoint_id: str) -> Dict[str, Any]:
    cp_from = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == from_checkpoint_id, Checkpoint.task_id == task_id)
        .first()
    )
    cp_to = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == to_checkpoint_id, Checkpoint.task_id == task_id)
        .first()
    )
    if not cp_from or not cp_to:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or both checkpoints were not found.")

    snap_a = json.loads(cp_from.snapshot_json)
    snap_b = json.loads(cp_to.snapshot_json)

    steps_a = {s["step_order"]: s for s in snap_a.get("steps", [])}
    steps_b = {s["step_order"]: s for s in snap_b.get("steps", [])}
    all_orders = sorted(set(steps_a.keys()) | set(steps_b.keys()))

    step_diffs: List[Dict[str, Any]] = []
    for order in all_orders:
        sa = steps_a.get(order)
        sb = steps_b.get(order)
        if sa and sb:
            changes: List[str] = []
            if sa["status"] != sb["status"]:
                changes.append(f"status: {sa['status']} -> {sb['status']}")
            if sa["description"] != sb["description"]:
                changes.append("instructions edited")
            if sa["is_locked"] != sb["is_locked"]:
                changes.append(f"lock: {sa['is_locked']} -> {sb['is_locked']}")
            if changes:
                step_diffs.append(
                    {
                        "step_order": order,
                        "title": sb["title"],
                        "change_type": "modified",
                        "changes": changes,
                    }
                )
        elif sb and not sa:
            step_diffs.append({"step_order": order, "title": sb["title"], "change_type": "added", "changes": ["step added"]})
        elif sa and not sb:
            step_diffs.append({"step_order": order, "title": sa["title"], "change_type": "removed", "changes": ["step removed"]})

    text_a = "\n\n".join(f"## {s['heading']}\n{s['current_content']}" for s in snap_a.get("artifact_sections", []))
    text_b = "\n\n".join(f"## {s['heading']}\n{s['current_content']}" for s in snap_b.get("artifact_sections", []))
    unified = list(
        difflib.unified_diff(
            text_a.splitlines(),
            text_b.splitlines(),
            fromfile=f"Checkpoint v{cp_from.version_number}",
            tofile=f"Checkpoint v{cp_to.version_number}",
            lineterm="",
        )
    )

    return {
        "from_checkpoint": {
            "id": cp_from.id,
            "version_number": cp_from.version_number,
            "label": cp_from.label,
            "task_status": cp_from.task_status,
            "completed_steps_count": cp_from.completed_steps_count,
        },
        "to_checkpoint": {
            "id": cp_to.id,
            "version_number": cp_to.version_number,
            "label": cp_to.label,
            "task_status": cp_to.task_status,
            "completed_steps_count": cp_to.completed_steps_count,
        },
        "step_diffs": step_diffs,
        "artifact_unified_diff": unified[:250],
    }


def rollback_to_checkpoint(
    db: Session,
    task: Task,
    user: User,
    checkpoint_id: str,
) -> Checkpoint:
    target = (
        db.query(Checkpoint)
        .filter(Checkpoint.id == checkpoint_id, Checkpoint.task_id == task.id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checkpoint not found.")

    validate_task_transition(
        task.status,
        TaskStatus.ROLLED_BACK,
        "Pause or interrupt active execution before rolling back if transition is blocked.",
    )
    task.rollback_attempts_count += 1

    # Save a pre-rollback safety checkpoint so rollback itself is non-destructive and reversible
    create_checkpoint(
        db,
        task=task,
        user_id=user.id,
        trigger_type="pre_rollback",
        label=f"Safety snapshot before rollback to v{target.version_number}",
        commit=False,
    )

    snapshot = json.loads(target.snapshot_json)
    task_snap = snapshot.get("task", {})

    # Restore task metadata & execution pointer
    task.autonomy_mode = task_snap.get("autonomy_mode", task.autonomy_mode)
    task.adaptive_enabled = task_snap.get("adaptive_enabled", task.adaptive_enabled)
    task.adaptive_caution_level = task_snap.get("adaptive_caution_level", "normal")
    task.adaptive_reason = task_snap.get("adaptive_reason", "")
    task.plan_approved = task_snap.get("plan_approved", False)
    task.current_step_index = task_snap.get("current_step_index", 0)
    task.additional_instructions_json = json.dumps(task_snap.get("additional_instructions", []))
    task.status = TaskStatus.ROLLED_BACK
    task.completed_at = None
    task.error_message = None
    task.is_interruptible = True
    task.current_activity = f"Rolled back to Checkpoint v{target.version_number} ({target.label}). Ready to edit or resume."

    # Replace execution steps cleanly from snapshot while preserving original IDs
    db.query(ExecutionStep).filter(ExecutionStep.task_id == task.id).delete(synchronize_session=False)
    db.flush()

    for s in snapshot.get("steps", []):
        restored_status = s["status"]
        if restored_status == StepStatus.RUNNING:
            restored_status = StepStatus.INTERRUPTED
        db.add(
            ExecutionStep(
                id=s["id"],
                task_id=task.id,
                step_order=s["step_order"],
                title=s["title"],
                description=s["description"],
                rationale=s["rationale"],
                expected_outcome=s["expected_outcome"],
                risk_level=s["risk_level"],
                status=restored_status,
                is_locked=s["is_locked"],
                requires_approval=s["requires_approval"],
                approved_by_user=s["approved_by_user"],
                approval_reason=s.get("approval_reason", ""),
                confidence_basis=s.get("confidence_basis", ""),
                uncertainty_notes=s.get("uncertainty_notes", ""),
                sources_json=json.dumps(s.get("sources", [])),
                output_content=s.get("output_content", ""),
                partial_output=s.get("partial_output", ""),
                completed_stages_json=json.dumps(s.get("completed_stages", [])),
                user_modified=s.get("user_modified", False),
                user_edit_note=s.get("user_edit_note", ""),
                rejected_reason=s.get("rejected_reason"),
                revision_number=s.get("revision_number", 1),
                duration_ms=s.get("duration_ms", 0),
            )
        )

    # Restore artifact sections from snapshot
    db.query(ArtifactRevision).filter(ArtifactRevision.task_id == task.id).delete(synchronize_session=False)
    db.query(ArtifactSection).filter(ArtifactSection.task_id == task.id).delete(synchronize_session=False)
    db.flush()

    for sec in snapshot.get("artifact_sections", []):
        restored_sec = ArtifactSection(
            id=sec["id"],
            task_id=task.id,
            step_id=sec.get("step_id"),
            section_order=sec["section_order"],
            heading=sec["heading"],
            ai_content=sec.get("ai_content", ""),
            current_content=sec.get("current_content", ""),
            authorship=sec.get("authorship", "ai"),
            version=sec.get("version", 1),
        )
        db.add(restored_sec)
        db.flush()
        db.add(
            ArtifactRevision(
                task_id=task.id,
                section_id=restored_sec.id,
                version=restored_sec.version,
                content=restored_sec.current_content,
                author_type="rollback",
                summary=f"Restored from Checkpoint v{target.version_number}",
            )
        )

    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="CHECKPOINT_RESTORED",
        actor="human",
        summary=f"Rolled back workspace to Checkpoint v{target.version_number}: {target.label}",
        payload={
            "restored_checkpoint_id": target.id,
            "restored_version": target.version_number,
            "restored_step_index": task.current_step_index,
        },
    )

    task.rollback_success_count += 1
    db.commit()
    db.refresh(task)

    sse_broker.publish(
        task.id,
        "task_rolled_back",
        {
            "task_status": task.status,
            "checkpoint_id": target.id,
            "version_number": target.version_number,
            "current_activity": task.current_activity,
        },
    )
    return target
