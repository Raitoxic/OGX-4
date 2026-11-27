from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Configure isolated SQLite DB & fast execution stage timing BEFORE app import
_tmp_dir = tempfile.mkdtemp(prefix="vyrox_test_")
_test_db_path = Path(_tmp_dir) / "test_vyrox.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path.as_posix()}"
os.environ["DEMO_STEP_STAGE_DELAY_SEC"] = "0.05"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from backend.core.rate_limit import rate_limiter  # noqa: E402
from backend.database.session import SessionLocal  # noqa: E402
from backend.execution.runner import recover_orphaned_running_tasks  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.task import AgentPlan, ExecutionStep, Task  # noqa: E402
from backend.orchestration.state_machine import StepStatus, TaskStatus  # noqa: E402
from ml.inference.predictor import supervision_predictor  # noqa: E402


def _auth_headers(client: TestClient, email: str, name: str = "VYRO-X Researcher") -> dict:
    rate_limiter.reset()
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": name, "password": "SecurePassword123!"},
    )
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_alembic_upgrade_on_fresh_database() -> None:
    """Verifies Alembic migration upgrades a completely fresh database cleanly."""
    fresh_db = Path(tempfile.mkdtemp(prefix="vyrox_alembic_")) / "fresh.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{fresh_db.as_posix()}"
    alembic_bin = Path(sys.executable).parent / "alembic"
    proc = subprocess.run(
        [str(alembic_bin), "-c", "backend/alembic.ini", "upgrade", "head"],
        cwd=str(Path(__file__).resolve().parent.parent.parent),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert fresh_db.exists()


def test_auth_session_revocation_and_user_isolation() -> None:
    with TestClient(app) as client:
        h1 = _auth_headers(client, "alice@vyrox.org", "Alice")
        h2 = _auth_headers(client, "bob@vyrox.org", "Bob")

        # Profile + autonomy settings sync (training consent defaults to False!)
        me = client.get("/api/auth/me", headers=h1)
        assert me.status_code == 200
        assert me.json()["training_consent_opt_in"] is False

        upd = client.patch(
            "/api/auth/me",
            headers=h1,
            json={"default_autonomy_mode": "balanced", "theme_preference": "dark", "ml_recommendations_enabled": True},
        )
        assert upd.status_code == 200
        assert upd.json()["theme_preference"] == "dark"

        # Create task as Alice
        created = client.post(
            "/api/tasks",
            headers=h1,
            json={"prompt": "Research distributed consensus algorithms for edge systems"},
        )
        assert created.status_code == 201, created.text
        task = created.json()
        assert task["interaction_mode"] == "vyrox"

        # Bob must not access Alice's task
        assert client.get(f"/api/tasks/{task['id']}", headers=h2).status_code == 404

        # Security headers present
        health = client.get("/api/health")
        assert health.headers.get("x-content-type-options") == "nosniff"
        assert health.headers.get("x-frame-options") == "DENY"
        assert health.json()["product"] == "VYRO-X"

        # Server-side session revocation on logout
        out = client.post("/api/auth/logout", headers=h1)
        assert out.status_code == 200
        assert out.json()["session_revoked"] is True
        # Revoked token must now be rejected with 401
        assert client.get("/api/auth/me", headers=h1).status_code == 401


def test_agent_plan_versioning_locking_replan_and_rejection() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client, "planner@vyrox.org")
        resp = client.post(
            "/api/tasks",
            headers=headers,
            json={
                "prompt": "Research zero-trust service meshes in multi-region Kubernetes",
                "autonomy_mode": "supervised",
            },
        )
        assert resp.status_code == 201
        task = resp.json()
        task_id = task["id"]
        assert task["status"] == TaskStatus.AWAITING_APPROVAL
        assert len(task["steps"]) == 5

        step1 = task["steps"][0]
        step2 = task["steps"][1]

        # Edit & lock step 1
        edited = client.patch(
            f"/api/tasks/{task_id}/steps/{step1['id']}",
            headers=headers,
            json={"description": "Focus specifically on SPIFFE/SPIRE identity rotation under 50ms p99 latency."},
        )
        assert edited.status_code == 200
        assert client.post(f"/api/tasks/{task_id}/steps/{step1['id']}/lock", headers=headers, json={"is_locked": True}).status_code == 200
        # Editing locked step blocked
        assert client.patch(f"/api/tasks/{task_id}/steps/{step1['id']}", headers=headers, json={"description": "Blocked"}).status_code == 409

        # Replan preserves locked step 1 and creates AgentPlan v2
        replanned = client.post(
            f"/api/tasks/{task_id}/replan",
            headers=headers,
            json={"reason": "Emphasize multi-cloud failover compliance"},
        )
        assert replanned.status_code == 200
        r_steps = replanned.json()["steps"]
        assert r_steps[0]["description"] == "Focus specifically on SPIFFE/SPIRE identity rotation under 50ms p99 latency."
        assert "multi-cloud failover compliance" in r_steps[1]["description"]

        db = SessionLocal()
        try:
            plans = db.query(AgentPlan).filter(AgentPlan.task_id == task_id).all()
            assert len(plans) == 2
        finally:
            db.close()

        # Reject step 2 with alternative generation
        rejected = client.post(
            f"/api/tasks/{task_id}/steps/{step2['id']}/reject",
            headers=headers,
            json={"reason": "Narrow to control-plane latency overhead", "generate_alternative": True},
        )
        assert rejected.status_code == 200
        assert "Alternative Approach" in rejected.json()["step"]["title"]
        assert rejected.json()["task"]["adaptive_caution_level"] == "elevated_caution"


def test_interrupt_resume_checkpoints_rollback_and_artifact_revisions() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client, "interrupt@vyrox.org")
        task = client.post(
            "/api/tasks",
            headers=headers,
            json={
                "prompt": "Research stateful AI agent checkpointing and deterministic recovery",
                "autonomy_mode": "higher_autonomy",
            },
        ).json()
        task_id = task["id"]

        assert client.post(f"/api/tasks/{task_id}/start", headers=headers).status_code == 200
        time.sleep(0.28)
        interrupted = client.post(f"/api/tasks/{task_id}/interrupt", headers=headers)
        assert interrupted.status_code == 200
        int_task = interrupted.json()["task"]
        assert int_task["status"] == TaskStatus.INTERRUPTED

        cps = client.get(f"/api/tasks/{task_id}/checkpoints", headers=headers).json()["checkpoints"]
        assert any(cp["trigger_type"] == "interrupt" for cp in cps)
        cp_before_edit = cps[0]

        completed_before_resume = [s["id"] for s in int_task["steps"] if s["status"] == StepStatus.COMPLETED]
        remaining = [s for s in int_task["steps"] if s["status"] != StepStatus.COMPLETED]
        assert len(remaining) >= 1
        assert client.patch(
            f"/api/tasks/{task_id}/steps/{remaining[0]['id']}",
            headers=headers,
            json={"description": "Explicitly cover SQLite WAL recovery and PostgreSQL ACID durability."},
        ).status_code == 200
        assert client.post(
            f"/api/tasks/{task_id}/instructions",
            headers=headers,
            json={"instruction": "Include concrete RTO/RPO recovery targets in remaining sections."},
        ).status_code == 200

        # Resume and approve gated steps (adaptive medium + mandatory high-risk invariant!)
        assert client.post(f"/api/tasks/{task_id}/resume", headers=headers).status_code == 200
        approved_risks = []
        for _ in range(60):
            time.sleep(0.08)
            cur = client.get(f"/api/tasks/{task_id}", headers=headers).json()
            if cur["status"] == TaskStatus.AWAITING_APPROVAL:
                awaiting = [s for s in cur["steps"] if s["status"] == StepStatus.AWAITING_APPROVAL]
                assert len(awaiting) == 1
                approved_risks.append(awaiting[0]["risk_level"])
                client.post(f"/api/tasks/{task_id}/steps/{awaiting[0]['id']}/approve", headers=headers)
            elif cur["status"] == TaskStatus.COMPLETED:
                break

        assert "high" in approved_risks
        final_task = client.get(f"/api/tasks/{task_id}", headers=headers).json()
        assert final_task["status"] == TaskStatus.COMPLETED
        assert final_task["recovery_count"] >= 1
        for cid in completed_before_resume:
            assert any(s["id"] == cid and s["status"] == StepStatus.COMPLETED for s in final_task["steps"])

        # Completed task cannot be resumed directly
        assert client.post(f"/api/tasks/{task_id}/resume", headers=headers).status_code == 409

        # Artifact co-edit + diff + revision restore
        first_sec = final_task["artifact_sections"][0]
        edited_sec = client.patch(
            f"/api/tasks/{task_id}/artifact/sections/{first_sec['id']}",
            headers=headers,
            json={"current_content": first_sec["current_content"] + "\n\n**Human Review:** Verified."},
        )
        assert edited_sec.status_code == 200
        assert edited_sec.json()["authorship"] == "collaborative"

        revs = client.get(f"/api/tasks/{task_id}/artifact/sections/{first_sec['id']}/revisions", headers=headers).json()["revisions"]
        assert len(revs) >= 2

        # Record SSE latency telemetry
        assert client.post(f"/api/tasks/{task_id}/telemetry/sse-latency", headers=headers, json={"latency_ms": 24.5}).status_code == 200

        # Checkpoint rollback restores prior state cleanly
        rb = client.post(f"/api/tasks/{task_id}/checkpoints/{cp_before_edit['id']}/rollback", headers=headers)
        assert rb.status_code == 200
        assert rb.json()["task"]["status"] == TaskStatus.ROLLED_BACK
        assert rb.json()["task"]["completed_steps_count"] < 5


def test_ml_inference_monitoring_and_14_metric_evaluation() -> None:
    supervision_predictor.reload()
    with TestClient(app) as client:
        headers = _auth_headers(client, "ml_eval@vyrox.org")

        # ML status returns trained model report & explicit synthetic provenance
        ml_st = client.get("/api/ml/status", headers=headers)
        assert ml_st.status_code == 200
        st_data = ml_st.json()
        assert st_data["model_available"] is True
        assert st_data["dataset_provenance"] == "SYNTHETIC_DEMO_DATASET"
        assert st_data["latest_report"]["test_evaluation"]["selected_model"]["f1_macro"] > 0.70

        # Create VYRO-X task and invoke live ML prediction endpoint
        t_vyrox = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research distributed consensus protocols for cloud control planes", "autonomy_mode": "supervised"},
        ).json()
        pred = client.post(f"/api/ml/predict/{t_vyrox['id']}", headers=headers)
        assert pred.status_code == 200
        p_data = pred.json()
        assert p_data["available"] is True
        assert p_data["recommended_autonomy"] in ("supervised", "balanced", "higher_autonomy")
        # Manual autonomy mode must NEVER be overridden by ML prediction!
        refreshed = client.get(f"/api/tasks/{t_vyrox['id']}", headers=headers).json()
        assert refreshed["autonomy_mode"] == "supervised"

        # Run Baseline task, submit ratings & qualitative feedback, inspect 14-metric evaluation
        t_base = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research distributed consensus protocols for cloud control planes", "interaction_mode": "baseline"},
        ).json()
        assert client.post(
            "/api/evaluation/rate",
            headers=headers,
            json={"task_id": t_base["id"], "scenario_key": "distributed-consensus", "effort_rating": 5, "trust_rating": 3, "control_rating": 2, "notes": "Opaque pass"},
        ).status_code == 200
        assert client.post(
            "/api/evaluation/feedback",
            headers=headers,
            json={"task_id": t_vyrox["id"], "category": "autonomy", "rating": 5, "comment": "Clear lock and interrupt semantics."},
        ).status_code == 200

        ev = client.get("/api/evaluation", headers=headers).json()
        assert "vyrox" in ev["measured"] and "baseline" in ev["measured"]
        assert "avg_interrupt_latency_ms" in ev["measured"]["vyrox"]
        assert "checkpoint_restoration_success_rate" in ev["measured"]["vyrox"]
        assert len(ev["statistical_tests"]) >= 4
        assert len(ev["recent_feedback"]) >= 1


def test_backend_restart_orphan_recovery() -> None:
    with TestClient(app) as client:
        headers = _auth_headers(client, "restart@vyrox.org")
        created = client.post(
            "/api/tasks",
            headers=headers,
            json={"prompt": "Research durable workflow checkpointing for distributed agents"},
        ).json()
        task_id = created["id"]

        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            steps = db.query(ExecutionStep).filter(ExecutionStep.task_id == task_id).order_by(ExecutionStep.step_order.asc()).all()
            steps[0].status = StepStatus.COMPLETED
            steps[0].output_content = "Completed step 1 persisted output"
            steps[1].status = StepStatus.RUNNING
            task.status = TaskStatus.RUNNING
            db.commit()
        finally:
            db.close()

        recover_orphaned_running_tasks()

        recovered = client.get(f"/api/tasks/{task_id}", headers=headers).json()
        assert recovered["status"] == TaskStatus.INTERRUPTED
        assert recovered["steps"][0]["status"] == StepStatus.COMPLETED
        assert recovered["steps"][1]["status"] == StepStatus.INTERRUPTED
