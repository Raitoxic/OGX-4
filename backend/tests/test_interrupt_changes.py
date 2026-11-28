from __future__ import annotations

import asyncio
import os
import tempfile
import uuid
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_interrupt_test_")
_test_db_path = Path(_tmp_dir) / "test_interrupt.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from backend.core.security import hash_password  # noqa: E402
from backend.database.init_db import init_db  # noqa: E402
from backend.database.session import SessionLocal  # noqa: E402
from backend.api.tasks import replan_unlocked_steps  # noqa: E402
from backend.execution.control_service import (  # noqa: E402
    add_instruction_to_task,
    interrupt_task_execution,
)
from backend.models.task import ExecutionStep, Task  # noqa: E402
from backend.models.user import User  # noqa: E402
from backend.orchestration.state_machine import StepStatus, TaskStatus  # noqa: E402

init_db()


def _make_task(db) -> tuple[Task, User]:
    user = User(
        email=f"u_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Interrupt Tester",
        password_hash=hash_password("SecurePassword123!"),
    )
    db.add(user)
    db.flush()
    task = Task(
        user_id=user.id,
        title="Interrupt flow",
        prompt="Build a thing with several steps.",
        interaction_mode="vyrox",
        status=TaskStatus.RUNNING,
        plan_approved=True,
        current_step_index=1,
    )
    db.add(task)
    db.flush()
    for i in range(1, 4):
        db.add(
            ExecutionStep(
                task_id=task.id,
                step_order=i,
                title=f"Step {i}",
                description=f"Description {i}",
                rationale=f"Rationale {i}",
                expected_outcome=f"Outcome {i}",
                status=StepStatus.COMPLETED if i == 1 else StepStatus.PENDING,
                requires_approval=False,
            )
        )
    db.commit()
    db.refresh(task)
    return task, user


def test_interrupt_preserves_completed_and_replans_with_changes() -> None:
    db = SessionLocal()
    try:
        task, user = _make_task(db)
        completed_before = [s.id for s in task.steps if s.status == StepStatus.COMPLETED]
        assert completed_before, "expected a completed step"

        # 1. Interrupt during execution (not actually running in this unit test).
        outcome = asyncio.run(interrupt_task_execution(db, task, user))
        assert outcome["task"].status == TaskStatus.INTERRUPTED
        # Completed step preserved.
        assert any(s.status == StepStatus.COMPLETED for s in outcome["task"].steps)

        # 2. Add new instructions (dedup identical consecutive instruction).
        e1 = add_instruction_to_task(db, task, user, "Focus on security hardening.")
        e2 = add_instruction_to_task(db, task, user, "Focus on security hardening.")
        assert e1["id"] == e2["id"], "duplicate instruction should be deduped"
        instructions = __import__("json").loads(task.additional_instructions_json)
        assert len(instructions) == 1

        # 3. Replan updates remaining plan, preserves completed, awaits approval.
        updated = asyncio.run(replan_unlocked_steps(db, task, user, reason="Applied new instructions after interrupt."))
        assert updated.status == TaskStatus.AWAITING_APPROVAL
        completed_after = [s for s in updated.steps if s.status == StepStatus.COMPLETED]
        assert {s.id for s in completed_after} >= set(completed_before)
        # Completed step content untouched.
        first = next(s for s in updated.steps if s.id in completed_before)
        assert first.status == StepStatus.COMPLETED
    finally:
        db.close()


def test_resume_from_interrupted_is_valid_transition() -> None:
    from backend.orchestration.state_machine import can_transition_task

    assert can_transition_task(TaskStatus.INTERRUPTED, TaskStatus.RESUMING)
    assert can_transition_task(TaskStatus.INTERRUPTED, TaskStatus.PLANNING)
    assert can_transition_task(TaskStatus.INTERRUPTED, TaskStatus.AWAITING_APPROVAL)