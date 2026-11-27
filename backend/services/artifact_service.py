from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from backend.autonomy.service import record_signal_and_adapt
from backend.models.artifact import ArtifactRevision, ArtifactSection
from backend.models.task import ExecutionStep, Task
from backend.models.user import User
from backend.services.history_service import record_event
from backend.streaming.broker import sse_broker


def upsert_ai_section(
    db: Session,
    task: Task,
    step: ExecutionStep,
    heading: str,
    content: str,
    is_partial: bool = False,
) -> ArtifactSection:
    section = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.task_id == task.id, ArtifactSection.step_id == step.id)
        .first()
    )

    if section is None:
        section = ArtifactSection(
            task_id=task.id,
            step_id=step.id,
            section_order=step.step_order,
            heading=heading,
            ai_content=content,
            current_content=content,
            authorship="ai",
            version=1,
        )
        db.add(section)
        db.flush()
    else:
        section.heading = heading
        section.ai_content = content
        if section.authorship == "ai":
            section.current_content = content
        elif not is_partial:
            # Preserve user edits explicitly while appending updated AI synthesis note
            if content.strip() and content.strip() not in section.current_content:
                section.current_content = (
                    f"{section.current_content.rstrip()}\n\n---\n"
                    f"*(Updated AI synthesis appended while preserving your edits)*\n\n{content}"
                )
            section.authorship = "collaborative"
        section.version += 1

    if not is_partial:
        revision = ArtifactRevision(
            task_id=task.id,
            section_id=section.id,
            version=section.version,
            content=section.current_content,
            author_type="ai",
            summary=f"AI completed step '{step.title}'",
        )
        db.add(revision)
        record_event(
            db,
            task_id=task.id,
            user_id=task.user_id,
            step_id=step.id,
            event_type="ARTIFACT_AI_UPDATED",
            actor="agent",
            summary=f"Updated shared artifact section '{heading}' from Step {step.step_order}",
            payload={"section_id": section.id, "version": section.version},
        )

    db.flush()
    sse_broker.publish(
        task.id,
        "artifact_updated",
        {
            "section_id": section.id,
            "step_id": section.step_id,
            "heading": section.heading,
            "authorship": section.authorship,
            "version": section.version,
            "is_partial": is_partial,
        },
    )
    return section


def apply_user_section_edit(
    db: Session,
    task: Task,
    user: User,
    section_id: str,
    new_content: str,
    new_heading: Optional[str] = None,
) -> ArtifactSection:
    section = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.id == section_id, ArtifactSection.task_id == task.id)
        .first()
    )
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact section not found.")

    task.artifact_updates_count += 1
    if new_heading is not None and new_heading.strip():
        section.heading = new_heading.strip()

    section.current_content = new_content
    if section.ai_content.strip():
        section.authorship = "ai" if new_content.strip() == section.ai_content.strip() else "collaborative"
    else:
        section.authorship = "human"
    section.version += 1

    revision = ArtifactRevision(
        task_id=task.id,
        section_id=section.id,
        version=section.version,
        content=section.current_content,
        author_type="human",
        summary=f"User edited '{section.heading}'",
    )
    db.add(revision)

    record_signal_and_adapt(
        db,
        user=user,
        task=task,
        signal_type="artifact_edit",
        step_risk_level="low",
        note=f"User modified artifact section '{section.heading}'",
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        step_id=section.step_id,
        event_type="ARTIFACT_USER_EDITED",
        actor="human",
        summary=f"Edited shared artifact section '{section.heading}' (v{section.version})",
        payload={"section_id": section.id, "version": section.version, "authorship": section.authorship},
    )
    task.artifact_updates_success_count += 1
    db.commit()
    db.refresh(section)

    sse_broker.publish(
        task.id,
        "artifact_updated",
        {
            "section_id": section.id,
            "step_id": section.step_id,
            "heading": section.heading,
            "authorship": section.authorship,
            "version": section.version,
            "is_partial": False,
        },
    )
    return section


def create_user_section(
    db: Session,
    task: Task,
    user: User,
    heading: str,
    content: str,
) -> ArtifactSection:
    max_order = (
        db.query(ArtifactSection)
        .filter(ArtifactSection.task_id == task.id)
        .count()
    )
    section = ArtifactSection(
        task_id=task.id,
        step_id=None,
        section_order=max_order + 1,
        heading=heading.strip(),
        ai_content="",
        current_content=content,
        authorship="human",
        version=1,
    )
    db.add(section)
    db.flush()

    db.add(
        ArtifactRevision(
            task_id=task.id,
            section_id=section.id,
            version=1,
            content=content,
            author_type="human",
            summary=f"User added section '{section.heading}'",
        )
    )
    record_event(
        db,
        task_id=task.id,
        user_id=user.id,
        event_type="ARTIFACT_USER_EDITED",
        actor="human",
        summary=f"Added new user-authored artifact section '{section.heading}'",
        payload={"section_id": section.id},
    )
    task.artifact_updates_success_count += 1
    db.commit()
    db.refresh(section)

    sse_broker.publish(
        task.id,
        "artifact_updated",
        {"section_id": section.id, "heading": section.heading, "authorship": "human", "version": 1},
    )
    return section


def compute_section_diff(section: ArtifactSection) -> Dict[str, Any]:
    ai_lines = section.ai_content.splitlines()
    cur_lines = section.current_content.splitlines()
    matcher = difflib.SequenceMatcher(a=ai_lines, b=cur_lines)
    diff_lines: List[Dict[str, str]] = []
    added = 0
    removed = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in ai_lines[i1:i2]:
                diff_lines.append({"type": "unchanged", "text": line})
        elif tag == "delete":
            for line in ai_lines[i1:i2]:
                diff_lines.append({"type": "removed", "text": line})
                removed += 1
        elif tag == "insert":
            for line in cur_lines[j1:j2]:
                diff_lines.append({"type": "added", "text": line})
                added += 1
        elif tag == "replace":
            for line in ai_lines[i1:i2]:
                diff_lines.append({"type": "removed", "text": line})
                removed += 1
            for line in cur_lines[j1:j2]:
                diff_lines.append({"type": "added", "text": line})
                added += 1

    return {
        "section_id": section.id,
        "heading": section.heading,
        "authorship": section.authorship,
        "has_user_changes": section.ai_content.strip() != section.current_content.strip(),
        "lines_added": added,
        "lines_removed": removed,
        "diff": diff_lines,
    }
