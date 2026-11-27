from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional

import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from backend.models.task import Task
from backend.models.telemetry import EvaluationResponse, InteractionEvent, UserFeedback
from backend.orchestration.state_machine import TaskStatus

COMPARABLE_SCENARIOS: List[Dict[str, str]] = [
    {
        "key": "distributed-consensus",
        "title": "Distributed Consensus & Fault-Tolerant State Replication",
        "difficulty": "High — Multi-constraint systems architecture",
        "prompt": (
            "Research and write a structured technical report on Distributed Consensus and Fault-Tolerant State "
            "Replication (Raft vs Paxos vs PBFT) for latency-sensitive cloud control planes, including failure modes "
            "and a phased production rollout roadmap."
        ),
    },
    {
        "key": "agent-observability",
        "title": "Human-in-the-Loop Control & Observability for Production AI Agents",
        "difficulty": "High — Interactive AI systems design",
        "prompt": (
            "Research and generate a structured research report on Human-in-the-Loop Control, Checkpointing, and "
            "Adaptive Autonomy for long-running enterprise AI agents, covering interruption semantics, auditability, "
            "and operational risk safeguards."
        ),
    },
    {
        "key": "zero-trust-microservices",
        "title": "Zero-Trust Service Mesh Security for Multi-Region Microservices",
        "difficulty": "Medium — Security & cloud architecture",
        "prompt": (
            "Research and write a structured technical report on Zero-Trust Service Mesh Architectures (mTLS, SPIFFE/SPIRE, "
            "and policy enforcement) for multi-region Kubernetes clusters, comparing performance overhead and recovery strategies."
        ),
    },
]


def _descriptive_stats(values: List[float]) -> Dict[str, Any]:
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": None, "std": None, "median": None, "ci_95": None}
    arr = np.array(values, dtype=float)
    mean_v = float(np.mean(arr))
    median_v = float(np.median(arr))
    if n < 2:
        return {
            "n": n,
            "mean": round(mean_v, 3),
            "std": None,
            "median": round(median_v, 3),
            "ci_95": None,
        }
    std_v = float(np.std(arr, ddof=1))
    sem = std_v / math.sqrt(n)
    if sem > 0:
        lo, hi = stats.t.interval(0.95, df=n - 1, loc=mean_v, scale=sem)
        ci = [round(float(lo), 3), round(float(hi), 3)]
    else:
        ci = [round(mean_v, 3), round(mean_v, 3)]
    return {
        "n": n,
        "mean": round(mean_v, 3),
        "std": round(std_v, 3),
        "median": round(median_v, 3),
        "ci_95": ci,
    }


def _two_group_test(vyrox_vals: List[float], base_vals: List[float], label: str) -> Dict[str, Any]:
    desc_v = _descriptive_stats(vyrox_vals)
    desc_b = _descriptive_stats(base_vals)
    if len(vyrox_vals) < 2 or len(base_vals) < 2:
        return {
            "metric": label,
            "vyrox": desc_v,
            "baseline": desc_b,
            "sufficient_data": False,
            "note": "Insufficient observations for significance testing (requires n >= 2 per group).",
            "welch_t_p": None,
            "mann_whitney_p": None,
            "cohens_d": None,
        }

    a = np.array(vyrox_vals, dtype=float)
    b = np.array(base_vals, dtype=float)
    try:
        _t_stat, t_p = stats.ttest_ind(a, b, equal_var=False)
        t_p_val = None if math.isnan(float(t_p)) else round(float(t_p), 4)
    except Exception:
        t_p_val = None
    try:
        _u_stat, u_p = stats.mannwhitneyu(a, b, alternative="two-sided")
        u_p_val = None if math.isnan(float(u_p)) else round(float(u_p), 4)
    except Exception:
        u_p_val = None

    pooled_var = ((len(a) - 1) * np.var(a, ddof=1) + (len(b) - 1) * np.var(b, ddof=1)) / max(
        1, (len(a) + len(b) - 2)
    )
    cohens_d = round(float((np.mean(a) - np.mean(b)) / math.sqrt(pooled_var)), 3) if pooled_var > 0 else 0.0

    return {
        "metric": label,
        "vyrox": desc_v,
        "baseline": desc_b,
        "sufficient_data": True,
        "note": "Computed via Welch's t-test, Mann-Whitney U, and pooled Cohen's d on local recorded sessions.",
        "welch_t_p": t_p_val,
        "mann_whitney_p": u_p_val,
        "cohens_d": cohens_d,
    }


def _aggregate_mode_metrics(
    tasks: List[Task],
    events: List[InteractionEvent],
    responses: List[EvaluationResponse],
) -> Dict[str, Any]:
    n = len(tasks)
    if n == 0:
        return {
            "sample_size": 0,
            "task_completion_rate": None,
            "avg_completion_time_sec": None,
            "avg_interventions_per_task": None,
            "avg_user_effort": None,
            "avg_perceived_trust": None,
            "avg_perceived_control": None,
            "recovery_success_rate": None,
            "plan_modification_success_rate": None,
            "avg_approval_response_sec": None,
            "avg_interrupt_latency_ms": None,
            "checkpoint_restoration_success_rate": None,
            "agent_execution_failure_rate": None,
            "artifact_revision_success_rate": None,
            "avg_sse_update_latency_ms": None,
            "failed_tasks": 0,
            "interrupted_tasks": 0,
            "recovered_tasks": 0,
            "ratings_count": 0,
        }

    completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    failed = [t for t in tasks if t.status == TaskStatus.FAILED]
    completion_rate = round((len(completed) / n) * 100, 1)
    failure_rate = round((len(failed) / n) * 100, 1)

    completed_durations = [t.total_execution_ms / 1000.0 for t in completed if t.total_execution_ms > 0]
    avg_time_sec = round(sum(completed_durations) / len(completed_durations), 2) if completed_durations else None

    task_ids = {t.id for t in tasks}
    intervention_types = {
        "TASK_INTERRUPTED",
        "TASK_PAUSED",
        "STEP_EDITED",
        "STEP_REJECTED",
        "INSTRUCTION_ADDED",
        "REPLAN_EXECUTED",
        "CHECKPOINT_RESTORED",
    }
    interventions = sum(1 for e in events if e.task_id in task_ids and e.event_type in intervention_types)
    avg_interventions = round(interventions / n, 2)

    interrupted_total = sum(t.interruption_count for t in tasks)
    recovered_total = sum(t.recovery_count for t in tasks)
    recovery_rate: Optional[float] = (
        round(min(100.0, (recovered_total / interrupted_total) * 100), 1) if interrupted_total > 0 else None
    )

    total_edits = sum(t.plan_edits_count for t in tasks)
    honored_edits = sum(t.plan_edits_honored_count for t in tasks)
    plan_mod_rate: Optional[float] = (
        round(min(100.0, (honored_edits / total_edits) * 100), 1) if total_edits > 0 else None
    )

    # Extended operational metrics (Section 6)
    appr_ms = sum(t.approval_response_ms_total for t in tasks)
    appr_cnt = sum(t.approval_response_count for t in tasks)
    avg_appr_sec = round((appr_ms / appr_cnt) / 1000.0, 2) if appr_cnt > 0 else None

    int_ms = sum(t.interrupt_latency_ms_total for t in tasks)
    int_cnt = sum(t.interrupt_latency_count for t in tasks)
    avg_int_ms = round(int_ms / int_cnt, 1) if int_cnt > 0 else None

    rb_att = sum(t.rollback_attempts_count for t in tasks)
    rb_ok = sum(t.rollback_success_count for t in tasks)
    rb_rate = round((rb_ok / rb_att) * 100, 1) if rb_att > 0 else None

    art_att = sum(t.artifact_updates_count for t in tasks)
    art_ok = sum(t.artifact_updates_success_count for t in tasks)
    art_rate = round((art_ok / art_att) * 100, 1) if art_att > 0 else None

    sse_samples: List[float] = []
    for t in tasks:
        try:
            vals = json.loads(t.sse_latency_samples_json or "[]")
            sse_samples.extend(float(v) for v in vals if isinstance(v, (int, float)) and 0 <= v <= 60000)
        except Exception:
            pass
    avg_sse_ms = round(sum(sse_samples) / len(sse_samples), 1) if sse_samples else None

    r_count = len(responses)
    avg_effort = round(sum(r.effort_rating for r in responses) / r_count, 2) if r_count else None
    avg_trust = round(sum(r.trust_rating for r in responses) / r_count, 2) if r_count else None
    avg_control = round(sum(r.control_rating for r in responses) / r_count, 2) if r_count else None

    return {
        "sample_size": n,
        "task_completion_rate": completion_rate,
        "avg_completion_time_sec": avg_time_sec,
        "avg_interventions_per_task": avg_interventions,
        "avg_user_effort": avg_effort,
        "avg_perceived_trust": avg_trust,
        "avg_perceived_control": avg_control,
        "recovery_success_rate": recovery_rate,
        "plan_modification_success_rate": plan_mod_rate,
        "avg_approval_response_sec": avg_appr_sec,
        "avg_interrupt_latency_ms": avg_int_ms,
        "checkpoint_restoration_success_rate": rb_rate,
        "agent_execution_failure_rate": failure_rate,
        "artifact_revision_success_rate": art_rate,
        "avg_sse_update_latency_ms": avg_sse_ms,
        "failed_tasks": len(failed),
        "interrupted_tasks": interrupted_total,
        "recovered_tasks": recovered_total,
        "ratings_count": r_count,
    }


def get_evaluation_dashboard(db: Session, user_id: str) -> Dict[str, Any]:
    tasks: List[Task] = db.query(Task).filter(Task.user_id == user_id).all()
    events: List[InteractionEvent] = db.query(InteractionEvent).filter(InteractionEvent.user_id == user_id).all()
    responses: List[EvaluationResponse] = (
        db.query(EvaluationResponse)
        .filter(EvaluationResponse.user_id == user_id)
        .order_by(EvaluationResponse.created_at.desc())
        .all()
    )
    feedback_rows: List[UserFeedback] = (
        db.query(UserFeedback)
        .filter(UserFeedback.user_id == user_id)
        .order_by(UserFeedback.created_at.desc())
        .limit(20)
        .all()
    )

    vyrox_tasks = [t for t in tasks if t.interaction_mode != "baseline"]
    baseline_tasks = [t for t in tasks if t.interaction_mode == "baseline"]
    vyrox_responses = [r for r in responses if r.interaction_mode != "baseline"]
    baseline_responses = [r for r in responses if r.interaction_mode == "baseline"]

    measured_vyrox = _aggregate_mode_metrics(vyrox_tasks, events, vyrox_responses)
    measured_baseline = _aggregate_mode_metrics(baseline_tasks, events, baseline_responses)

    statistical_tests = [
        _two_group_test(
            [float(r.control_rating) for r in vyrox_responses],
            [float(r.control_rating) for r in baseline_responses],
            "Perceived Control (1-7)",
        ),
        _two_group_test(
            [float(r.trust_rating) for r in vyrox_responses],
            [float(r.trust_rating) for r in baseline_responses],
            "Perceived Trust (1-7)",
        ),
        _two_group_test(
            [float(r.effort_rating) for r in vyrox_responses],
            [float(r.effort_rating) for r in baseline_responses],
            "User Effort (1-7, lower is easier)",
        ),
        _two_group_test(
            [t.total_execution_ms / 1000.0 for t in vyrox_tasks if t.status == TaskStatus.COMPLETED and t.total_execution_ms > 0],
            [t.total_execution_ms / 1000.0 for t in baseline_tasks if t.status == TaskStatus.COMPLETED and t.total_execution_ms > 0],
            "Task Completion Time (sec)",
        ),
    ]

    illustrative_reference = {
        "data_provenance": "ILLUSTRATIVE_DEMO_ONLY",
        "disclaimer": (
            "Illustrative template values shown strictly to preview the evaluation layout before running live trials. "
            "These are NOT measured experimental results and must NOT be cited as proven improvement."
        ),
        "vyrox_illustrative": {
            "sample_size": 0,
            "task_completion_rate": 92.0,
            "avg_completion_time_sec": 18.4,
            "avg_interventions_per_task": 2.4,
            "avg_user_effort": 2.8,
            "avg_perceived_trust": 5.9,
            "avg_perceived_control": 6.4,
            "recovery_success_rate": 100.0,
            "plan_modification_success_rate": 95.0,
            "avg_approval_response_sec": 4.2,
            "avg_interrupt_latency_ms": 48.0,
            "checkpoint_restoration_success_rate": 100.0,
            "agent_execution_failure_rate": 0.0,
            "artifact_revision_success_rate": 100.0,
            "avg_sse_update_latency_ms": 32.0,
        },
        "baseline_illustrative": {
            "sample_size": 0,
            "task_completion_rate": 78.0,
            "avg_completion_time_sec": 12.1,
            "avg_interventions_per_task": 0.0,
            "avg_user_effort": 4.9,
            "avg_perceived_trust": 3.8,
            "avg_perceived_control": 2.3,
            "recovery_success_rate": 0.0,
            "plan_modification_success_rate": 0.0,
            "avg_approval_response_sec": None,
            "avg_interrupt_latency_ms": None,
            "checkpoint_restoration_success_rate": 0.0,
            "agent_execution_failure_rate": 5.0,
            "artifact_revision_success_rate": 0.0,
            "avg_sse_update_latency_ms": None,
        },
    }

    methodology = {
        "baseline_definition": (
            "Conventional Prompt-and-Wait: the user submits a natural-language instruction, waits for single-pass generation, "
            "and receives the final output without plan inspection, step locking, mid-run interruption, or checkpoint recovery."
        ),
        "proposed_model_definition": (
            "VYRO-X Collaborative Workspace: the user inspects a structured plan, edits/locks/approves/rejects steps, interrupts "
            "execution safely with persistent checkpoints, injects mid-flight instructions, rolls back states, and co-edits the artifact."
        ),
        "protocol_steps": [
            "Select an identical technical research scenario from the comparable task suite.",
            "Execute the task in Prompt-and-Wait Baseline Mode and record completion metrics + post-task 1–7 Effort, Trust, and Control ratings.",
            "Execute the matched scenario in VYRO-X Mode (including at least one mid-execution interrupt, step edit, and resume).",
            "Record post-task ratings using the identical 1–7 scales and inspect paired measured metrics and statistical tests.",
        ],
        "metric_definitions": [
            {
                "metric": "Task Completion Rate (%) & Failure Rate (%)",
                "measures": "Share of initiated tasks reaching COMPLETED vs FAILED state.",
                "cannot_establish": "Deep factual domain accuracy without independent human peer review.",
            },
            {
                "metric": "Task Completion Time & Approval Response Time",
                "measures": "Active execution duration and human latency when responding to approval gates.",
                "cannot_establish": "Whether faster execution implies higher quality; VYRO-X intentionally trades minor review time for alignment.",
            },
            {
                "metric": "Interrupt Response Latency & SSE Update Latency (ms)",
                "measures": "System responsiveness from interrupt trigger to persisted checkpoint, and backend-to-browser SSE delivery delay.",
                "cannot_establish": "Latency under high multi-tenant network load without dedicated load testing.",
            },
            {
                "metric": "Recovery, Checkpoint Restoration & Artifact Revision Success (%)",
                "measures": "Reliability of resuming interrupted work, rolling back saved snapshots, and restoring artifact revisions.",
                "cannot_establish": "Idempotency of arbitrary external third-party side-effect APIs.",
            },
            {
                "metric": "User Effort, Perceived Trust & Perceived Control (1–7)",
                "measures": "Self-reported workload, confidence in system transparency, and agency over execution.",
                "cannot_establish": "Objective trust calibration or long-term learning effects from small sample sizes.",
            },
        ],
        "known_limitations": [
            "When running without external LLM credentials, generation uses clearly labelled Deterministic Demo Mode.",
            "Statistical significance tests require at least n >= 2 recorded observations in both VYRO-X and Baseline groups; otherwise results are explicitly marked insufficient.",
            "The Adaptive Supervision ML model is trained on a clearly labelled synthetic demonstration dataset (SYNTHETIC_DEMO_DATASET) and has not yet been validated on real-world production users.",
        ],
    }

    return {
        "data_provenance": "MEASURED_LOCAL_SESSIONS",
        "has_measured_comparison": measured_vyrox["sample_size"] > 0 and measured_baseline["sample_size"] > 0,
        "measured": {
            "vyrox": measured_vyrox,
            "baseline": measured_baseline,
        },
        "statistical_tests": statistical_tests,
        "illustrative_demo_reference": illustrative_reference,
        "comparable_scenarios": COMPARABLE_SCENARIOS,
        "recent_ratings": [
            {
                "id": r.id,
                "task_id": r.task_id,
                "interaction_mode": "vyrox" if r.interaction_mode != "baseline" else "baseline",
                "scenario_key": r.scenario_key,
                "effort_rating": r.effort_rating,
                "trust_rating": r.trust_rating,
                "control_rating": r.control_rating,
                "notes": r.notes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in responses[:20]
        ],
        "recent_feedback": [
            {
                "id": f.id,
                "task_id": f.task_id,
                "category": f.category,
                "rating": f.rating,
                "comment": f.comment,
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in feedback_rows
        ],
        "methodology": methodology,
    }


def submit_evaluation_rating(
    db: Session,
    user_id: str,
    task: Task,
    effort_rating: int,
    trust_rating: int,
    control_rating: int,
    scenario_key: str = "custom",
    notes: str = "",
) -> EvaluationResponse:
    mode = "baseline" if task.interaction_mode == "baseline" else "vyrox"
    existing = (
        db.query(EvaluationResponse)
        .filter(EvaluationResponse.task_id == task.id, EvaluationResponse.user_id == user_id)
        .first()
    )
    if existing:
        existing.effort_rating = effort_rating
        existing.trust_rating = trust_rating
        existing.control_rating = control_rating
        existing.scenario_key = scenario_key or existing.scenario_key
        existing.notes = notes.strip()
        db.commit()
        db.refresh(existing)
        return existing

    resp = EvaluationResponse(
        task_id=task.id,
        user_id=user_id,
        interaction_mode=mode,
        scenario_key=scenario_key or "custom",
        effort_rating=effort_rating,
        trust_rating=trust_rating,
        control_rating=control_rating,
        notes=notes.strip(),
    )
    db.add(resp)
    db.commit()
    db.refresh(resp)
    return resp


def submit_user_feedback(
    db: Session,
    user_id: str,
    comment: str,
    category: str = "general",
    rating: int = 5,
    task_id: Optional[str] = None,
) -> UserFeedback:
    fb = UserFeedback(
        user_id=user_id,
        task_id=task_id,
        category=category,
        rating=rating,
        comment=comment.strip(),
    )
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb
