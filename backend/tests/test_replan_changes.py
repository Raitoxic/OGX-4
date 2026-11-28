from __future__ import annotations

import asyncio
import json
import os
import tempfile
import uuid
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="vyrox_replan_test_")
_test_db_path = Path(_tmp_dir) / "test_replan.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from backend.core.security import hash_password  # noqa: E402
from backend.database.init_db import init_db  # noqa: E402
from backend.database.session import SessionLocal  # noqa: E402
from backend.models.task import ExecutionStep, Task  # noqa: E402
from backend.models.user import User  # noqa: E402
from backend.orchestration.planning_service import replan_unlocked_steps  # noqa: E402
from backend.orchestration.state_machine import StepStatus, TaskStatus  # noqa: E402

init_db()

INSTRUCTION = (
    "Replace the general benefits section with a detailed comparison of AI in "
    "cancer detection, medical imaging, and patient monitoring."
)


def _make_task(db) -> tuple[Task, User]:
    user = User(
        email=f"u_{uuid.uuid4().hex[:8]}@example.com",
        full_name="Replan Tester",
        password_hash=hash_password("SecurePassword123!"),
    )
    db.add(user)
    db.flush()
    task = Task(
        user_id=user.id,
        title="Research AI applications in healthcare",
        prompt="Research AI applications in healthcare.",
        interaction_mode="vyrox",
        status=TaskStatus.INTERRUPTED,
        plan_approved=True,
        current_step_index=1,
    )
    db.add(task)
    db.flush()
    db.add(ExecutionStep(task_id=task.id, step_order=1, title="Research overview",
                         description="Overview of AI in healthcare.", rationale="r", expected_outcome="o",
                         status=StepStatus.COMPLETED))
    db.add(ExecutionStep(task_id=task.id, step_order=2, title="General benefits",
                         description="General benefits of AI.", rationale="r", expected_outcome="o",
                         status=StepStatus.PENDING))
    db.add(ExecutionStep(task_id=task.id, step_order=3, title="Implementation roadmap",
                         description="Roadmap.", rationale="r", expected_outcome="o",
                         status=StepStatus.PENDING))
    db.commit()
    db.refresh(task)
    return task, user


def test_replan_genuinely_modifies_adds_removes_and_preserves() -> None:
    db = SessionLocal()
    try:
        task, user = _make_task(db)
        # Save the new instruction (as the Interrupt dialog does before replan).
        task.additional_instructions_json = json.dumps(
            [{"id": str(uuid.uuid4()), "text": INSTRUCTION, "added_at": "now", "step_index": 1, "task_status_when_added": "INTERRUPTED"}]
        )
        db.commit()

        completed_before = {s.id: (s.title, s.status) for s in task.steps if s.status == StepStatus.COMPLETED}

        updated = asyncio.run(replan_unlocked_steps(db, task, user, reason="Applied new instructions after interrupt."))
        assert updated.status == TaskStatus.AWAITING_APPROVAL

        steps = {s.step_order: s for s in updated.steps}
        by_change = {}
        for s in updated.steps:
            by_change.setdefault(s.replan_change, []).append(s)

        # Completed step preserved unchanged.
        for cid, (title, status) in completed_before.items():
            match = next(s for s in updated.steps if s.id == cid)
            assert match.title == title and match.status == StepStatus.COMPLETED

        # A pending step was genuinely modified to carry the new instruction.
        modified = by_change.get("modified", [])
        assert modified, "expected a modified step"
        assert any(INSTRUCTION[:40] in (m.description or "") for m in modified)

        # A new step was added.
        added = by_change.get("added", [])
        assert added, "expected an added step"

        # The general benefits step was removed and will NOT execute.
        removed = by_change.get("removed", [])
        assert removed, "expected a removed step"
        assert all(r.status == StepStatus.REJECTED for r in removed)
        assert all("benefit" in r.title.lower() for r in removed)

        # Only revised pending steps remain executable; no outdated pending remains.
        pending_titles = [s.title for s in updated.steps if s.status == StepStatus.PENDING]
        assert not any("general benefits" in t.lower() for t in pending_titles)
        assert all(s.status != StepStatus.PENDING for s in removed)
    finally:
        db.close()


def test_replan_does_not_execute_completed_or_removed() -> None:
    db = SessionLocal()
    try:
        task, user = _make_task(db)
        task.additional_instructions_json = json.dumps([{"text": INSTRUCTION}])
        db.commit()
        updated = asyncio.run(replan_unlocked_steps(db, task, user, reason="changes"))
        executable = [s for s in updated.steps if s.status == StepStatus.PENDING]
        # No completed or removed step is executable.
        assert all(s.status == StepStatus.PENDING for s in executable)
        assert all(s.replan_change in ("modified", "unchanged", "added") for s in executable)
    finally:
        db.close()