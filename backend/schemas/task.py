from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from backend.models.artifact import ArtifactSection
from backend.models.checkpoint import Checkpoint
from backend.models.task import ExecutionStep, Task
from backend.models.telemetry import InteractionEvent
from backend.orchestration.state_machine import StepStatus
from backend.research.claims import map_claims
from backend.research.citations import normalize_style


# ---- Source / Reference Schema (honest attribution; missing metadata stays empty) ----

class StepSource(BaseModel):
    """A single reference/source attached to a step.

    Only ``title`` is conventionally present. Author/year/venue/DOI/provider and
    access status are optional and must NEVER be fabricated — when unknown they
    remain ``None`` so the UI can honestly display "Not available".
    """

    title: str = ""
    type: str = ""
    reference: str = ""
    reliability_note: str = ""
    authors: Optional[str] = None
    year: Optional[Any] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    provider: Optional[str] = None
    access_status: Optional[str] = None
    used: Optional[bool] = None
    abstract: Optional[str] = None


def normalize_sources(raw_json: str) -> List[Dict[str, Any]]:
    """Parse stored sources JSON into validated dicts with safe defaults.

    Malformed or partial entries never raise; missing bibliographic metadata is
    preserved as ``None`` rather than invented.
    """
    try:
        raw = json.loads(raw_json or "[]")
    except (ValueError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    normalized: List[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            normalized.append(StepSource(**item).model_dump())
    return normalized


# ---- Request Schemas ----

class CreateTaskRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=4000)
    title: Optional[str] = Field(default=None, max_length=200)
    interaction_mode: Literal["vyrox", "baseline", "hai"] = "vyrox"
    autonomy_mode: Optional[Literal["supervised", "balanced", "higher_autonomy"]] = None
    adaptive_enabled: Optional[bool] = None
    research_enabled: bool = False


class SseLatencyRequest(BaseModel):
    latency_ms: float = Field(ge=0.0, le=60000.0)


class UserFeedbackRequest(BaseModel):
    task_id: Optional[str] = None
    category: Literal["general", "usability", "autonomy", "accuracy", "bug", "suggestion"] = "general"
    rating: int = Field(default=5, ge=1, le=5)
    comment: str = Field(min_length=3, max_length=2000)


class EditStepRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = Field(default=None, min_length=5, max_length=4000)
    expected_outcome: Optional[str] = Field(default=None, min_length=3, max_length=2000)
    edit_note: Optional[str] = Field(default="", max_length=500)


class LockStepRequest(BaseModel):
    is_locked: bool


class ApproveRequest(BaseModel):
    step_id: Optional[str] = None
    auto_continue: bool = True


class RejectStepRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)
    generate_alternative: bool = True


class AddInstructionRequest(BaseModel):
    instruction: str = Field(min_length=2, max_length=2000)


class ReplanRequest(BaseModel):
    reason: str = Field(default="", max_length=1000)


class UpdateAutonomyRequest(BaseModel):
    autonomy_mode: Optional[Literal["supervised", "balanced", "higher_autonomy"]] = None
    adaptive_enabled: Optional[bool] = None


class CreateCheckpointRequest(BaseModel):
    label: str = Field(min_length=2, max_length=180)


class UpdateArtifactSectionRequest(BaseModel):
    heading: Optional[str] = Field(default=None, min_length=2, max_length=200)
    current_content: str = Field(min_length=0, max_length=50000)


class CreateArtifactSectionRequest(BaseModel):
    heading: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=1, max_length=50000)


class SubmitEvaluationRequest(BaseModel):
    task_id: str
    scenario_key: str = Field(default="custom", max_length=100)
    effort_rating: int = Field(ge=1, le=7)
    trust_rating: int = Field(ge=1, le=7)
    control_rating: int = Field(ge=1, le=7)
    notes: str = Field(default="", max_length=2000)


# ---- Serialization Helpers ----

def serialize_step(step: ExecutionStep) -> Dict[str, Any]:
    return {
        "id": step.id,
        "task_id": step.task_id,
        "step_order": step.step_order,
        "title": step.title,
        "description": step.description,
        "rationale": step.rationale,
        "expected_outcome": step.expected_outcome,
        "risk_level": step.risk_level,
        "status": step.status,
        "is_locked": step.is_locked,
        "requires_approval": step.requires_approval,
        "approved_by_user": step.approved_by_user,
        "approval_reason": step.approval_reason,
        "confidence_basis": step.confidence_basis,
        "uncertainty_notes": step.uncertainty_notes,
        "sources": normalize_sources(step.sources_json),
        "output_content": step.output_content,
        "partial_output": step.partial_output,
        "completed_stages": json.loads(step.completed_stages_json or "[]"),
        "user_modified": step.user_modified,
        "user_edit_note": step.user_edit_note,
        "rejected_reason": step.rejected_reason,
        "revision_number": step.revision_number,
        "duration_ms": step.duration_ms,
        "started_at": step.started_at.isoformat() if step.started_at else None,
        "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        "updated_at": step.updated_at.isoformat() if step.updated_at else None,
    }


def serialize_section(sec: ArtifactSection) -> Dict[str, Any]:
    return {
        "id": sec.id,
        "task_id": sec.task_id,
        "step_id": sec.step_id,
        "section_order": sec.section_order,
        "heading": sec.heading,
        "ai_content": sec.ai_content,
        "current_content": sec.current_content,
        "authorship": sec.authorship,
        "version": sec.version,
        "has_user_edits": sec.ai_content.strip() != sec.current_content.strip(),
        "updated_at": sec.updated_at.isoformat() if sec.updated_at else None,
    }


def serialize_checkpoint(cp: Checkpoint) -> Dict[str, Any]:
    return {
        "id": cp.id,
        "task_id": cp.task_id,
        "version_number": cp.version_number,
        "label": cp.label,
        "trigger_type": cp.trigger_type,
        "task_status": cp.task_status,
        "current_step_index": cp.current_step_index,
        "completed_steps_count": cp.completed_steps_count,
        "total_steps_count": cp.total_steps_count,
        "created_at": cp.created_at.isoformat() if cp.created_at else None,
    }


def serialize_event(ev: InteractionEvent) -> Dict[str, Any]:
    return {
        "id": ev.id,
        "task_id": ev.task_id,
        "step_id": ev.step_id,
        "event_type": ev.event_type,
        "actor": ev.actor,
        "summary": ev.summary,
        "payload": json.loads(ev.payload_json or "{}"),
        "created_at": ev.created_at.isoformat() if ev.created_at else None,
    }


def serialize_task_summary(task: Task) -> Dict[str, Any]:
    steps = task.steps or []
    completed_count = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
    total_count = len(steps)
    progress = round((completed_count / total_count) * 100) if total_count else 0
    return {
        "id": task.id,
        "title": task.title,
        "prompt": task.prompt,
        "topic": task.topic,
        "interaction_mode": task.interaction_mode,
        "provider_mode": task.provider_mode,
        "provider_name": task.provider_name,
        "status": task.status,
        "autonomy_mode": task.autonomy_mode,
        "adaptive_enabled": task.adaptive_enabled,
        "adaptive_caution_level": task.adaptive_caution_level,
        "adaptive_reason": task.adaptive_reason,
        "complexity_score": task.complexity_score,
        "ml_recommended_autonomy": task.ml_recommended_autonomy,
        "ml_recommendation_confidence": task.ml_recommendation_confidence,
        "ml_model_version": task.ml_model_version,
        "ml_recommendation_reason": task.ml_recommendation_reason,
        "plan_approved": task.plan_approved,
        "current_step_index": task.current_step_index,
        "current_activity": task.current_activity,
        "is_interruptible": task.is_interruptible,
        "completed_steps_count": completed_count,
        "total_steps_count": total_count,
        "progress_percent": progress,
        "checkpoints_count": len(task.checkpoints or []),
        "interruption_count": task.interruption_count,
        "recovery_count": task.recovery_count,
        "plan_edits_count": task.plan_edits_count,
        "total_execution_ms": task.total_execution_ms,
        "research_enabled": task.research_enabled,
        "research_status": task.research_status,
        "research_duration_ms": task.research_duration_ms,
        "research_used_count": task.research_used_count,
        "research_retrieved_count": task.research_retrieved_count,
        "research_used": normalize_sources(task.research_used_json),
        "research_retrieved": normalize_sources(task.research_retrieved_json),
        "citation_style": normalize_style(task.citation_style),
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def serialize_task_detail(task: Task) -> Dict[str, Any]:
    base = serialize_task_summary(task)
    used_sources = normalize_sources(task.research_used_json)
    artifact_sections = sorted(task.artifact_sections, key=lambda x: x.section_order)
    serialized_sections = []
    for sec in artifact_sections:
        sec_dict = serialize_section(sec)
        # Heuristic claim-to-source mapping (never proof of correctness). A section
        # edited by a human is marked stale until re-verified.
        has_user_edits = sec.ai_content.strip() != sec.current_content.strip()
        sec_dict["claims"] = map_claims(sec.current_content, used_sources, stale=has_user_edits)
        serialized_sections.append(sec_dict)
    base.update(
        {
            "error_message": task.error_message,
            "additional_instructions": json.loads(task.additional_instructions_json or "[]"),
            "steps": [serialize_step(s) for s in sorted(task.steps, key=lambda x: x.step_order)],
            "artifact_sections": serialized_sections,
            "checkpoints": [
                serialize_checkpoint(cp) for cp in sorted(task.checkpoints, key=lambda x: x.version_number, reverse=True)
            ],
            "recent_events": [
                serialize_event(ev)
                for ev in sorted(task.events, key=lambda x: x.created_at or datetime.min, reverse=True)[:80]
            ],
        }
    )
    return base
