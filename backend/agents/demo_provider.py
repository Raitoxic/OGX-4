from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.agents.base import (
    AgentProvider,
    PlannedStepSpec,
    StepExecutionResult,
    StepStageSpec,
)


def extract_topic(prompt: str) -> str:
    cleaned = re.sub(r"\s+", " ", prompt.strip())
    lowered = cleaned.lower()
    prefixes = [
        "research and write a structured technical report on ",
        "research and generate a structured research report on ",
        "research and generate a technical report on ",
        "research a selected technical topic:",
        "write a research report on ",
        "generate a report on ",
        "research ",
        "analyze ",
        "investigate ",
    ]
    topic = cleaned
    for prefix in prefixes:
        if lowered.startswith(prefix):
            topic = cleaned[len(prefix):].strip(" .:-")
            break
    if len(topic) > 110:
        topic = topic[:107].rsplit(" ", 1)[0] + "..."
    return topic or "Selected Technical Systems Architecture"


class DeterministicDemoProvider(AgentProvider):
    """
    Clearly labelled deterministic demonstration agent.
    Generates domain-tailored structured technical research plans and reports while
    genuinely incorporating user edits, locked constraints, rejections, and mid-flight instructions.
    Never fabricates numeric confidence scores or live web citations.
    """

    provider_mode = "demo"
    provider_name = "vyrox-deterministic-v1"

    async def generate_plan(
        self,
        prompt: str,
        topic: str,
        additional_instructions: Optional[List[str]] = None,
    ) -> List[PlannedStepSpec]:
        t = topic or extract_topic(prompt)
        extra_note = ""
        if additional_instructions:
            extra_note = f" Incorporate user constraint(s): {'; '.join(additional_instructions)}."

        return [
            PlannedStepSpec(
                title="Scope Definition & Research Questions",
                description=(
                    f"Define exact research boundaries, core problem framing, and measurable evaluation criteria "
                    f"for '{t}'. Clarify target system assumptions and audience depth.{extra_note}"
                ),
                rationale="Establishing explicit scope and questions upfront prevents drift during synthesis and gives the human collaborator a clean contract to edit or lock.",
                expected_outcome="A concise Scope & Research Questions section with 4 concrete technical questions and explicit inclusion/exclusion boundaries.",
                risk_level="low",
                confidence_basis="Deterministic Demo Mode — structured directly from user task prompt (not live web retrieval).",
                uncertainty_notes="Ambiguities in deployment scale, budget constraints, or regulatory context require user guidance if domain-specific.",
                sources=[
                    {
                        "title": "User Task Specification",
                        "type": "user_input",
                        "reference": "Original prompt & active workspace constraints",
                        "reliability_note": "Primary authoritative requirement source.",
                    }
                ],
            ),
            PlannedStepSpec(
                title="Core Architecture & Technical Landscape",
                description=(
                    f"Map the foundational architectural components, core algorithms/protocols, and key implementation "
                    f"mechanisms underpinning '{t}'. Document system invariants and operational dependencies."
                ),
                rationale="Understanding structural building blocks is necessary before comparing trade-offs or proposing production recommendations.",
                expected_outcome="A structured Technical Architecture Overview outlining core layers, data/control flows, and key engineering invariants.",
                risk_level="low",
                confidence_basis="Deterministic Demo Mode — synthesized from curated systems-engineering taxonomy (illustrative, non-live).",
                uncertainty_notes="Benchmark figures and vendor-specific release notes from recent months are not retrieved in offline demo mode.",
                sources=[
                    {
                        "title": "VYRO-X Curated Systems Taxonomy (Demo Corpus)",
                        "type": "demo_reference",
                        "reference": "demo://knowledge/systems-architecture",
                        "reliability_note": "Clearly labelled offline demonstration knowledge base.",
                    },
                    {
                        "title": "Engineering Design Patterns Reference (Demo)",
                        "type": "demo_reference",
                        "reference": "demo://knowledge/distributed-reliability",
                        "reliability_note": "Offline structural reference — verify against live specs for production.",
                    },
                ],
            ),
            PlannedStepSpec(
                title="Comparative Trade-Off & Failure Mode Analysis",
                description=(
                    f"Compare leading architectural approaches for '{t}' across latency, reliability, operational "
                    f"complexity, and cost. Identify top failure modes and observability blind spots."
                ),
                rationale="Real engineering decisions hinge on trade-offs and failure behaviour rather than idealized feature lists.",
                expected_outcome="A structured Comparative Trade-Off Matrix and Failure Mode catalog highlighting when each approach succeeds or degrades.",
                risk_level="medium",
                confidence_basis="Deterministic Demo Mode — comparative rubric grounded in standard reliability and performance dimensions.",
                uncertainty_notes="Weighting between latency, cost, and safety depends on organizational priorities; user editing is recommended.",
                sources=[
                    {
                        "title": "Comparative Systems Evaluation Rubric (Demo)",
                        "type": "demo_reference",
                        "reference": "demo://knowledge/tradeoff-matrix",
                        "reliability_note": "Qualitative engineering criteria; quantitative benchmarks require live telemetry.",
                    }
                ],
            ),
            PlannedStepSpec(
                title="Recommended Implementation Roadmap & Safeguards",
                description=(
                    f"Propose a phased implementation plan, governance controls, rollback strategy, and high-impact "
                    f"operational safeguards for deploying '{t}' safely."
                ),
                rationale="Prescriptive architecture recommendations carry high downstream impact and should always pass explicit human review before finalizing.",
                expected_outcome="A concrete 3-phase Implementation & Risk Mitigation blueprint with explicit go/no-go validation gates.",
                risk_level="high",
                confidence_basis="Deterministic Demo Mode — high-impact prescriptive guidance; explicitly gated for human approval.",
                uncertainty_notes="High consequential impact: organizational compliance, security posture, and team expertise must be validated by the human owner.",
                sources=[
                    {
                        "title": "Production Readiness & Rollback Checklist (Demo)",
                        "type": "demo_reference",
                        "reference": "demo://knowledge/production-safeguards",
                        "reliability_note": "Baseline safeguard patterns; requires human domain sign-off.",
                    }
                ],
            ),
            PlannedStepSpec(
                title="Executive Summary & Open Limitations",
                description=(
                    f"Synthesize all verified findings for '{t}' into an executive brief, summarize key decisions, "
                    f"and clearly document remaining open questions and evidence limitations."
                ),
                rationale="Providing a transparent executive summary with explicit limitations reinforces epistemic trust and makes the shared report immediately actionable.",
                expected_outcome="A polished Executive Summary & Limitations closing section aligned with all preceding steps and human modifications.",
                risk_level="medium",
                confidence_basis="Deterministic Demo Mode — derived strictly from completed preceding steps and human instructions.",
                uncertainty_notes="Reflects demo-mode synthesis boundaries; enable Live LLM Mode in .env for external model generation.",
                sources=[
                    {
                        "title": "Preceding Verified Report Sections",
                        "type": "internal_trace",
                        "reference": "Workspace artifact sections 1–4",
                        "reliability_note": "Directly traceable to approved workspace steps.",
                    }
                ],
            ),
        ]

    async def replan_unlocked_steps(
        self,
        prompt: str,
        topic: str,
        locked_or_completed_steps: List[Dict[str, Any]],
        unlocked_pending_steps: List[Dict[str, Any]],
        replan_reason: str,
        additional_instructions: List[str],
    ) -> List[PlannedStepSpec]:
        t = topic or extract_topic(prompt)
        directive = (additional_instructions[-1] if additional_instructions else "") or replan_reason.strip() or "Refined user requirements"
        directive_l = directive.lower()
        preserved_titles = [s["title"] for s in locked_or_completed_steps]

        if not unlocked_pending_steps:
            return []

        # Decide which pending step to remove (only when the user asks to replace
        # a general/benefits section). Never touch completed/locked steps.
        remove_idx = None
        if "replace" in directive_l or "remove" in directive_l:
            for idx, s in enumerate(unlocked_pending_steps):
                title_l = s["title"].lower()
                if any(k in title_l for k in ("benefit", "general", "overview", "introduction")):
                    remove_idx = idx
                    break

        revised: List[PlannedStepSpec] = []
        modified_done = False
        for idx, existing in enumerate(unlocked_pending_steps):
            if idx == remove_idx:
                # Genuinely removed from the plan (API marks it removed/not executed).
                continue
            step_key = existing["step_order"]
            if not modified_done:
                # Modify the first remaining pending step to carry the new focus.
                modified_done = True
                revised.append(
                    PlannedStepSpec(
                        title=f"{existing['title']} (Revised)",
                        description=(
                            f"{existing['description']} "
                            f"REVISED REQUIREMENT: {directive} "
                            f"Continuity with preserved steps: {', '.join(preserved_titles[:3]) or 'none'}."
                        ),
                        rationale=f"Replanned to incorporate the user's new instruction: '{directive}'.",
                        expected_outcome=f"Addresses '{directive}' instead of the previous general scope.",
                        risk_level=existing.get("risk_level", "medium"),
                        confidence_basis="Deterministic Demo Mode — genuinely replanned around completed steps.",
                        uncertainty_notes="Revised scope reflects the latest human directive; verify before approving.",
                        sources=[
                            {
                                "title": "Human Replan Directive",
                                "type": "user_input",
                                "reference": directive[:120],
                                "reliability_note": "Direct user steering input.",
                            }
                        ],
                        step_key=step_key,
                        replan_change="modified",
                    )
                )
            else:
                revised.append(
                    PlannedStepSpec(
                        title=existing["title"],
                        description=existing["description"],
                        rationale=existing.get("rationale", "Unchanged pending step."),
                        expected_outcome=existing["expected_outcome"],
                        risk_level=existing.get("risk_level", "medium"),
                        confidence_basis="Deterministic Demo Mode — unchanged pending step.",
                        uncertainty_notes="",
                        sources=existing.get("sources") or [],
                        step_key=step_key,
                        replan_change="unchanged",
                    )
                )

        # Add a genuinely new step that produces the requested detailed comparison.
        revised.append(
            PlannedStepSpec(
                title="Detailed Comparison & Analysis",
                description=(
                    f"Produce a detailed, evidence-grounded comparison specifically addressing: {directive}. "
                    f"Cover each requested dimension explicitly and contrast alternatives."
                ),
                rationale="New step added during replan to satisfy the user's revised requirement.",
                expected_outcome=f"A comparison section that directly answers '{directive}'.",
                risk_level="medium",
                confidence_basis="Deterministic Demo Mode — added step from user directive.",
                uncertainty_notes="Newly added scope; verify coverage before approving.",
                sources=[
                    {
                        "title": "Human Replan Directive",
                        "type": "user_input",
                        "reference": directive[:120],
                        "reliability_note": "Direct user steering input.",
                    }
                ],
                step_key=None,
                replan_change="added",
            )
        )
        return revised

    async def propose_alternative_step(
        self,
        prompt: str,
        topic: str,
        rejected_step: Dict[str, Any],
        rejection_reason: str,
    ) -> PlannedStepSpec:
        t = topic or extract_topic(prompt)
        reason = rejection_reason.strip() or "User requested a more focused, lower-risk approach"
        base_title = rejected_step["title"].replace(" (Alternative Approach)", "")
        return PlannedStepSpec(
            title=f"{base_title} (Alternative Approach)",
            description=(
                f"Revised execution approach for '{t}' addressing rejection feedback: \"{reason}\". "
                f"Narrow scope to verifiable criteria, explicitly avoid assumptions flagged during review, "
                f"and present concrete trade-offs before making prescriptive claims."
            ),
            rationale=f"Generated as a direct alternative after the user rejected the prior proposal ('{reason}').",
            expected_outcome=f"A revised section addressing '{reason}' with transparent assumptions and human-verifiable checkpoints.",
            risk_level=rejected_step.get("risk_level", "medium"),
            confidence_basis="Deterministic Demo Mode — reconstructed strictly in response to user rejection rationale.",
            uncertainty_notes="Requires explicit user approval before execution; never auto-executed after rejection.",
            sources=[
                {
                    "title": "User Rejection Feedback",
                    "type": "user_input",
                    "reference": reason[:140],
                    "reliability_note": "Direct human correction signal.",
                }
            ],
        )

    def get_execution_stages(
        self,
        topic: str,
        step: Dict[str, Any],
        additional_instructions: List[str],
    ) -> List[StepStageSpec]:
        title = step["title"]
        desc = step["description"]
        t = topic or "Technical Topic"
        extra_line = (
            f"\n- Active mid-flight human directives: {len(additional_instructions)} queued"
            if additional_instructions
            else ""
        )
        lock_line = "\n- Lock constraint active: preserving exact user-locked specification" if step.get("is_locked") else ""
        return [
            StepStageSpec(
                stage_key="context_load",
                label="Loading constraints & prior state",
                detail=f"Checking locked steps, user edits, and prior findings for '{title}'.",
                partial_markdown=(
                    f"### {title} *(In Progress — Stage 1/3)*\n\n"
                    f"> Loading task context for **{t}**. Active instruction: _{desc[:180]}_"
                    f"{lock_line}{extra_line}\n"
                ),
            ),
            StepStageSpec(
                stage_key="evidence_synthesis",
                label="Structuring evidence & technical analysis",
                detail=f"Compiling structured criteria, trade-offs, and evidence notes for '{title}'.",
                partial_markdown=(
                    f"### {title} *(In Progress — Stage 2/3)*\n\n"
                    f"Synthesizing technical analysis for **{t}** based on active step scope:\n"
                    f"- Verified step goal: {desc[:220]}\n"
                    f"- Evaluating core design trade-offs, operational risks, and verification criteria.\n"
                    f"- Preparing structured artifact draft (interruptible checkpoint boundary ready).\n"
                ),
            ),
            StepStageSpec(
                stage_key="draft_finalize",
                label="Drafting & verifying artifact section",
                detail=f"Writing structured report section and updating provenance links for '{title}'.",
                partial_markdown=(
                    f"### {title} *(Finalizing — Stage 3/3)*\n\n"
                    f"Finalizing structured prose, source annotations, and uncertainty notes for **{t}**...\n"
                ),
            ),
        ]

    async def execute_step(
        self,
        prompt: str,
        topic: str,
        step: Dict[str, Any],
        prior_outputs: List[Dict[str, str]],
        additional_instructions: List[str],
        research_context: Optional[str] = None,
        research_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> StepExecutionResult:
        t = topic or extract_topic(prompt)
        order = int(step.get("step_order", 1))
        title = step["title"]
        description = step["description"]
        user_modified = bool(step.get("user_modified"))
        is_locked = bool(step.get("is_locked"))

        customization_block = ""
        if user_modified or additional_instructions or is_locked:
            notes: List[str] = []
            if is_locked:
                notes.append("**Locked Step Honored:** Executed strictly against the user-locked specification without autonomous drift.")
            if user_modified:
                notes.append(f"**User Plan Edit Applied:** Tailored directly to modified step instruction — *\"{description}\"*")
            if additional_instructions:
                joined = "; ".join(additional_instructions)
                notes.append(f"**Mid-Execution User Guidance Integrated:** {joined}")
            customization_block = "\n> **Human-in-the-Loop Alignment**\n> " + "\n> ".join(notes) + "\n\n"

        if order == 1 or "scope" in title.lower():
            body = (
                f"{customization_block}"
                f"#### Problem Framing\n"
                f"This technical research report examines **{t}** with an emphasis on architectural clarity, "
                f"operational reliability, and verifiable engineering trade-offs.\n\n"
                f"#### Core Research Questions\n"
                f"1. What structural components and control-plane invariants define a production-grade implementation of **{t}**?\n"
                f"2. Where do conventional designs fail under latency pressure, partial outages, or evolving human requirements?\n"
                f"3. Which comparative trade-offs matter most across reliability, cost, observability, and maintainability?\n"
                f"4. What phased safeguards and rollback mechanisms reduce deployment risk?\n\n"
                f"#### Scope Boundaries\n"
                f"- **Included:** Architectural patterns, failure-mode analysis, risk-tiered rollout guidelines, and human-oversight checkpoints.\n"
                f"- **Excluded:** Vendor pricing negotiations and unverified marketing claims.\n"
                f"- **Step Focus Applied:** {description}\n"
            )
        elif order == 2 or "architecture" in title.lower() or "landscape" in title.lower():
            body = (
                f"{customization_block}"
                f"#### Reference Architecture Layers for {t}\n"
                f"A resilient implementation of **{t}** separates concerns across four decoupled planes:\n\n"
                f"1. **Control & Orchestration Plane:** Enforces deterministic state transitions, concurrency guards, and explicit policy gates before consequential actions execute.\n"
                f"2. **Execution & Data Processing Plane:** Performs modular, checkpointed units of work so long-running tasks remain observable and safely interruptible.\n"
                f"3. **State & Persistence Layer:** Persists durable snapshots, provenance metadata, and versioned artifacts so system recovery survives crashes or process restarts.\n"
                f"4. **Observability & Human Oversight Interface:** Streams real-time activity, rationale, and uncertainty metadata to operators.\n\n"
                f"#### Key Engineering Invariants\n"
                f"- **Idempotency & Concurrency Safety:** Prevent duplicate runs using execution tokens and atomic state transitions.\n"
                f"- **Explicit Provenance:** Link every output artifact back to the step, constraints, and evidence that produced it.\n"
                f"- **Applied Step Instruction:** {description}\n"
            )
        elif order == 3 or "comparative" in title.lower() or "trade-off" in title.lower():
            body = (
                f"{customization_block}"
                f"#### Comparative Architectural Matrix ({t})\n\n"
                f"| Dimension | Monolithic / Black-Box Approach | Modular Stateful Approach (Recommended) | Lightweight Heuristic Approach |\n"
                f"| :--- | :--- | :--- | :--- |\n"
                f"| **Controllability** | Low — opaque end-to-end execution | High — step-level inspection, edit & interrupt | Medium — manual glue required |\n"
                f"| **Failure Recovery** | Expensive full restart | Checkpoint restore & partial resume | Ad-hoc retry logic |\n"
                f"| **Auditability** | Post-hoc logs only | Full provenance & versioned diffs | Partial logs |\n"
                f"| **Implementation Effort** | Low initial, high maintenance | Moderate structured investment | Low initial, brittle at scale |\n\n"
                f"#### Primary Failure Modes & Mitigations\n"
                f"- **Silent Drift During Long Tasks:** Mitigated by step-level plans, explicit human lock constraints, and live event streaming.\n"
                f"- **State Corruption on Mid-Run Cancellation:** Mitigated by cooperative cancellation boundaries and pre-commit snapshots.\n"
                f"- **Over-Automation of High-Risk Actions:** Mitigated by mandatory human approval invariants on high-impact operations.\n"
                f"- **Applied Step Instruction:** {description}\n"
            )
        elif order == 4 or "roadmap" in title.lower() or "safeguard" in title.lower() or "implementation" in title.lower():
            body = (
                f"{customization_block}"
                f"#### Phased Deployment Blueprint for {t}\n\n"
                f"- **Phase 1 — Foundation & Observability:** Establish persistent state schemas, deterministic state machines, and structured audit logging before scaling throughput.\n"
                f"- **Phase 2 — Controlled Rollout & Human Gates:** Enable human-in-the-loop approvals for medium/high-risk operations, validate interrupt/resume under load, and verify rollback restoration times.\n"
                f"- **Phase 3 — Adaptive Calibration:** Monitor real correction, rejection, and recovery metrics to calibrate oversight thresholds without removing hard safety invariants.\n\n"
                f"#### Mandatory Pre-Production Safeguards\n"
                f"1. Automated rollback verification across process restarts.\n"
                f"2. Strict authorization boundaries and input schema validation.\n"
                f"3. Explicit operational playbooks for degraded or non-interruptible operations.\n"
                f"4. **Verified Scope Alignment:** {description}\n"
            )
        else:
            prior_titles = ", ".join(p["title"] for p in prior_outputs) or "preceding analysis sections"
            body = (
                f"{customization_block}"
                f"#### Executive Synthesis — {t}\n"
                f"Integrating findings across {prior_titles}, adopting a **modular, checkpointed, human-controllable architecture** "
                f"delivers materially stronger reliability, auditability, and recovery resilience for **{t}** compared to opaque black-box pipelines.\n\n"
                f"#### Key Takeaways\n"
                f"- Explicit state machines and persistent checkpoints eliminate costly full restarts after mid-task course corrections.\n"
                f"- Separating low-risk routine steps from high-impact consequential decisions balances execution speed with operational safety.\n"
                f"- Co-authored artifacts with preserved AI-vs-human provenance ensure technical teams retain clear ownership.\n\n"
                f"#### Honest Limitations & Disclosure\n"
                f"- *Mode Notice:* This section was generated in **Deterministic Demo Mode** (offline demonstration synthesis). "
                f"Configure `OPENAI_API_KEY` or `GEMINI_API_KEY` in `backend/.env` to activate Live AI Mode.\n"
                f"- *Step Focus Applied:* {description}\n"
            )

        return StepExecutionResult(
            section_heading=title,
            output_markdown=body.strip(),
            confidence_basis=(
                f"Deterministic Demo Mode — grounded in task prompt, {len(prior_outputs)} prior completed step(s)"
                + (", and explicit human edits/directives." if (user_modified or additional_instructions) else ".")
            ),
            uncertainty_notes=(
                "Demo synthesis does not fetch live external web citations. Verify empirical benchmarks before production deployment."
            ),
            sources=step.get("sources") or [],
            honored_user_modifications=bool(user_modified or additional_instructions or is_locked),
        )

    async def execute_baseline_report(self, prompt: str, topic: str) -> Dict[str, Any]:
        t = topic or extract_topic(prompt)
        markdown = (
            f"## Research Report: {t}\n\n"
            f"*Generated via Conventional Prompt-and-Wait Baseline Mode (single-pass execution; no plan inspection, step editing, locking, mid-run interruption, or checkpointing).* \n\n"
            f"### Overview\n"
            f"**{t}** encompasses architectural, reliability, and operational trade-offs across modern engineering systems. "
            f"Organizations adopting this technology typically evaluate control-plane modularity, state persistence, observability, and deployment safety.\n\n"
            f"### Technical Summary\n"
            f"Standard implementations combine modular processing pipelines with persistent storage and automated monitoring. "
            f"Key considerations include latency predictability, graceful degradation under load, clear failure recovery, and maintainable interfaces.\n\n"
            f"### General Recommendations\n"
            f"1. Start with a scoped prototype and clear success criteria.\n"
            f"2. Instrument latency, error rates, and recovery paths.\n"
            f"3. Validate security and rollback procedures prior to general availability.\n\n"
            f"### Baseline Mode Limitation Note\n"
            f"Because Prompt-and-Wait executes as a single opaque pass, any mid-task requirement change or scope refinement requires starting a new prompt from scratch."
        )
        return {
            "heading": f"Baseline Report — {t}",
            "content": markdown,
            "provider_mode": self.provider_mode,
            "provider_name": self.provider_name,
        }
