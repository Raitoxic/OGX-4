from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

import httpx

from backend.agents.base import (
    AgentProvider,
    PlannedStepSpec,
    StepExecutionResult,
    StepStageSpec,
)
from backend.agents.demo_provider import DeterministicDemoProvider, extract_topic
from backend.core.config import settings


def _extract_json_block(text: str) -> Any:
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", cleaned)
    if fence:
        cleaned = fence.group(1).strip()
    return json.loads(cleaned)


class LiveLLMProvider(AgentProvider):
    """
    Configurable live LLM provider supporting OpenAI-compatible APIs and Google Gemini API.
    Activated only when OPENAI_API_KEY or GEMINI_API_KEY is explicitly configured in environment variables.
    """

    provider_mode = "live"

    def __init__(self, backend_kind: str, model_name: str) -> None:
        self.backend_kind = backend_kind  # "openai" | "gemini"
        self.model_name = model_name
        self.provider_name = f"{backend_kind}:{model_name}"
        self._stage_helper = DeterministicDemoProvider()

    async def _call_model(self, system_prompt: str, user_prompt: str) -> str:
        timeout = httpx.Timeout(settings.llm_timeout_sec)
        async with httpx.AsyncClient(timeout=timeout) as client:
            if self.backend_kind == "openai":
                resp = await client.post(
                    f"{settings.openai_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "temperature": 0.3,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]

            if self.backend_kind == "gemini":
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{self.model_name}:generateContent?key={settings.gemini_api_key}"
                )
                resp = await client.post(
                    url,
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": [{"parts": [{"text": user_prompt}]}],
                        "generationConfig": {"temperature": 0.3},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]

            raise RuntimeError(f"Unsupported LLM backend kind: {self.backend_kind}")

    async def generate_plan(
        self,
        prompt: str,
        topic: str,
        additional_instructions: Optional[List[str]] = None,
    ) -> List[PlannedStepSpec]:
        t = topic or extract_topic(prompt)
        sys_prompt = (
            "You are VYRO-X, a transparent collaborative agent planner. "
            "Return ONLY a JSON array of 5 structured research execution steps. "
            "Each item must contain keys: title, description, rationale, expected_outcome, "
            "risk_level ('low'|'medium'|'high'), confidence_basis (qualitative basis, never fake %), "
            "uncertainty_notes, sources (array of {title, type, reference, reliability_note}). "
            "Mark high-impact prescriptive recommendations as risk_level='high'."
        )
        usr_prompt = f"User prompt: {prompt}\nTopic: {t}\nAdditional instructions: {additional_instructions or []}"
        raw = await self._call_model(sys_prompt, usr_prompt)
        parsed = _extract_json_block(raw)
        specs: List[PlannedStepSpec] = []
        for item in parsed[:6]:
            risk = str(item.get("risk_level", "low")).lower()
            if risk not in ("low", "medium", "high"):
                risk = "medium"
            specs.append(
                PlannedStepSpec(
                    title=str(item["title"])[:190],
                    description=str(item["description"]),
                    rationale=str(item.get("rationale", "Structured task decomposition.")),
                    expected_outcome=str(item.get("expected_outcome", "Structured report section.")),
                    risk_level=risk,
                    confidence_basis=str(item.get("confidence_basis", f"Live AI ({self.provider_name})")),
                    uncertainty_notes=str(item.get("uncertainty_notes", "Verify critical claims independently.")),
                    sources=item.get("sources") if isinstance(item.get("sources"), list) else [],
                )
            )
        return specs

    async def replan_unlocked_steps(
        self,
        prompt: str,
        topic: str,
        locked_or_completed_steps: List[Dict[str, Any]],
        unlocked_pending_steps: List[Dict[str, Any]],
        replan_reason: str,
        additional_instructions: List[str],
    ) -> List[PlannedStepSpec]:
        sys_prompt = (
            "You are VYRO-X replanning ONLY unlocked pending steps. Never alter locked or completed steps. "
            "Return ONLY a JSON array with the exact same count of updated pending steps using keys: "
            "title, description, rationale, expected_outcome, risk_level, confidence_basis, uncertainty_notes, sources."
        )
        usr_prompt = json.dumps(
            {
                "prompt": prompt,
                "topic": topic,
                "preserved_steps": [s["title"] for s in locked_or_completed_steps],
                "steps_to_replan": unlocked_pending_steps,
                "replan_reason": replan_reason,
                "additional_instructions": additional_instructions,
            }
        )
        raw = await self._call_model(sys_prompt, usr_prompt)
        parsed = _extract_json_block(raw)
        return [
            PlannedStepSpec(
                title=str(item["title"])[:190],
                description=str(item["description"]),
                rationale=str(item.get("rationale", "Replanned per user request.")),
                expected_outcome=str(item.get("expected_outcome", "Updated section.")),
                risk_level=str(item.get("risk_level", "medium")).lower()
                if str(item.get("risk_level", "medium")).lower() in ("low", "medium", "high")
                else "medium",
                confidence_basis=str(item.get("confidence_basis", f"Live AI ({self.provider_name}) replan")),
                uncertainty_notes=str(item.get("uncertainty_notes", "")),
                sources=item.get("sources") if isinstance(item.get("sources"), list) else [],
            )
            for item in parsed
        ]

    async def propose_alternative_step(
        self,
        prompt: str,
        topic: str,
        rejected_step: Dict[str, Any],
        rejection_reason: str,
    ) -> PlannedStepSpec:
        sys_prompt = (
            "A user rejected a planned step. Propose a revised alternative step addressing their feedback. "
            "Return ONLY a single JSON object with keys: title, description, rationale, expected_outcome, "
            "risk_level, confidence_basis, uncertainty_notes, sources."
        )
        usr_prompt = json.dumps(
            {"prompt": prompt, "topic": topic, "rejected_step": rejected_step, "rejection_reason": rejection_reason}
        )
        raw = await self._call_model(sys_prompt, usr_prompt)
        item = _extract_json_block(raw)
        return PlannedStepSpec(
            title=str(item["title"])[:190],
            description=str(item["description"]),
            rationale=str(item.get("rationale", "Alternative generated after user rejection.")),
            expected_outcome=str(item.get("expected_outcome", "Revised output.")),
            risk_level=str(item.get("risk_level", "medium")).lower()
            if str(item.get("risk_level", "medium")).lower() in ("low", "medium", "high")
            else "medium",
            confidence_basis=str(item.get("confidence_basis", f"Live AI ({self.provider_name}) alternative")),
            uncertainty_notes=str(item.get("uncertainty_notes", "")),
            sources=item.get("sources") if isinstance(item.get("sources"), list) else [],
        )

    def get_execution_stages(
        self,
        topic: str,
        step: Dict[str, Any],
        additional_instructions: List[str],
    ) -> List[StepStageSpec]:
        return self._stage_helper.get_execution_stages(topic, step, additional_instructions)

    async def execute_step(
        self,
        prompt: str,
        topic: str,
        step: Dict[str, Any],
        prior_outputs: List[Dict[str, str]],
        additional_instructions: List[str],
    ) -> StepExecutionResult:
        sys_prompt = (
            "You are VYRO-X executing a single structured research step for a collaborative report. "
            "Strictly honor the step's description, any locked constraints, and all mid-execution user instructions. "
            "Be transparent about limitations and never invent citations or numeric confidence percentages. "
            "Return clean Markdown for this section."
        )
        usr_prompt = json.dumps(
            {
                "original_prompt": prompt,
                "topic": topic,
                "step": {
                    "title": step["title"],
                    "description": step["description"],
                    "expected_outcome": step["expected_outcome"],
                    "is_locked": step.get("is_locked", False),
                    "user_modified": step.get("user_modified", False),
                },
                "prior_sections": prior_outputs[-3:],
                "additional_user_instructions": additional_instructions,
            }
        )
        markdown = await self._call_model(sys_prompt, usr_prompt)
        return StepExecutionResult(
            section_heading=step["title"],
            output_markdown=markdown.strip(),
            confidence_basis=f"Live AI ({self.provider_name}) synthesis incorporating task context and human guidance.",
            uncertainty_notes="Model output without live web browser verification; review critical facts before publication.",
            sources=step.get("sources") or [],
            honored_user_modifications=bool(step.get("user_modified") or additional_instructions or step.get("is_locked")),
        )

    async def execute_baseline_report(self, prompt: str, topic: str) -> Dict[str, Any]:
        sys_prompt = (
            "Produce a single-pass structured technical research report in Markdown addressing the user's prompt."
        )
        markdown = await self._call_model(sys_prompt, prompt)
        return {
            "heading": f"Baseline Report — {topic or extract_topic(prompt)}",
            "content": markdown.strip(),
            "provider_mode": self.provider_mode,
            "provider_name": self.provider_name,
        }


def get_agent_provider() -> AgentProvider:
    mode, provider_label = settings.active_provider_info
    if mode == "live":
        kind, model_name = provider_label.split(":", 1)
        return LiveLLMProvider(kind, model_name)
    return DeterministicDemoProvider()
