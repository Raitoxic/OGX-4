from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlannedStepSpec:
    title: str
    description: str
    rationale: str
    expected_outcome: str
    risk_level: str  # low | medium | high
    confidence_basis: str
    uncertainty_notes: str
    sources: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class StepStageSpec:
    stage_key: str
    label: str
    detail: str
    partial_markdown: str


@dataclass
class StepExecutionResult:
    section_heading: str
    output_markdown: str
    confidence_basis: str
    uncertainty_notes: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    honored_user_modifications: bool = False


class AgentProvider(ABC):
    provider_mode: str  # "demo" | "live"
    provider_name: str

    @abstractmethod
    async def generate_plan(
        self,
        prompt: str,
        topic: str,
        additional_instructions: Optional[List[str]] = None,
    ) -> List[PlannedStepSpec]:
        raise NotImplementedError

    @abstractmethod
    async def replan_unlocked_steps(
        self,
        prompt: str,
        topic: str,
        locked_or_completed_steps: List[Dict[str, Any]],
        unlocked_pending_steps: List[Dict[str, Any]],
        replan_reason: str,
        additional_instructions: List[str],
    ) -> List[PlannedStepSpec]:
        raise NotImplementedError

    @abstractmethod
    async def propose_alternative_step(
        self,
        prompt: str,
        topic: str,
        rejected_step: Dict[str, Any],
        rejection_reason: str,
    ) -> PlannedStepSpec:
        raise NotImplementedError

    @abstractmethod
    def get_execution_stages(
        self,
        topic: str,
        step: Dict[str, Any],
        additional_instructions: List[str],
    ) -> List[StepStageSpec]:
        raise NotImplementedError

    @abstractmethod
    async def execute_step(
        self,
        prompt: str,
        topic: str,
        step: Dict[str, Any],
        prior_outputs: List[Dict[str, str]],
        additional_instructions: List[str],
    ) -> StepExecutionResult:
        raise NotImplementedError

    @abstractmethod
    async def execute_baseline_report(
        self,
        prompt: str,
        topic: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError
