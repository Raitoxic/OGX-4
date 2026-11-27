# VYRO-X — Academic Demonstration & Validation Package
**Product:** VYRO-X — *Human Intelligence. Agent Evolution.*  
**Repository:** `/Users/nishithrai/OGX-4`  
**Core Interaction Paradigm:** Continuous, Transparent, Interruptible Human-Agent Collaboration

---

## 1. Human-Agent Interaction (HAI) Problem-Statement Mapping

Conventional AI systems operate on a **prompt-and-wait** loop: a user submits a prompt, waits without visibility into intermediate steps, and must restart from scratch when requirements evolve or outputs drift. VYRO-X addresses all four HAI research pillars directly:

| HAI Pillar | Prompt-and-Wait Limitation | VYRO-X Mechanism | Verification Anchor |
| :--- | :--- | :--- | :--- |
| **Interaction Design** | Single chat box, opaque final dump. | Split-pane collaborative workspace (**Live Execution Plan** + **Shared Editable Artifact**), compact sidebar, and global `⌘K` Command Palette. | `frontend/src/pages/WorkspacePage.tsx`, `CommandPalette.tsx` |
| **Trust & Transparency** | Unexplained outputs; fabricated numeric confidence scores. | Per-step rationale, expected outcome, risk tier, evidence/grounding basis, honest uncertainty notes, AI-vs-Human artifact diffs, and explicit **Deterministic Demo Mode** vs. **Live AI Mode** disclosure. | `StepCard.tsx`, `SharedArtifactPanel.tsx`, `ModeBanner.tsx` |
| **Human-in-the-Loop Control** | No mid-run steering, locking, or reversible recovery. | Inline step editing, server-enforced immutable locks (`409` on agent/locked edits), reject-with-alternative, cooperative micro-stage mid-execution interrupt, mid-flight instruction injection, persistent checkpoints, checkpoint comparison, and non-destructive rollback. | `backend/execution/runner.py`, `checkpoints/service.py`, `state_machine.py` |
| **Agent Behaviour Modelling** | Static one-size-fits-all autonomy. | Transparent rule-based adaptive autonomy (`Supervised`, `Balanced`, `Higher Autonomy`) driven by real behavioural signals + reproducible **Adaptive Supervision Prediction Model** (advisory only; never bypasses manual overrides or mandatory high-risk gates). | `backend/autonomy/service.py`, `ml/training/train.py`, `ml/inference/predictor.py` |
| **Scientific Evaluation** | Anecdotal impressions without baseline comparator. | Built-in **Paired Benchmark Runner** (Prompt-and-Wait Baseline vs. VYRO-X), 14 operational & subjective metrics, SciPy statistical inference (`n >= 2`), and strict separation of Measured, Automated, Synthetic, and Illustrative data. | `backend/services/evaluation_service.py`, `EvaluationPage.tsx` |

---

## 2. Final Feature Verification Summary

All 17 core end-to-end HAI workflow stages were verified against the live running VYRO-X stack (`http://127.0.0.1:5173` → `http://127.0.0.1:8000`) and automated `pytest` suite (`6/6 passed`):

1. **Register & Log In:** PBKDF2-HMAC-SHA256 (`310,000` iterations) + persisted JWT `auth_sessions`.
2. **Create Task & Generate Agent Plan:** Structured 5-step risk-tiered plan persisted to `agent_plans` + `execution_steps` with advisory ML supervision recommendation.
3. **Review, Lock & Approve Plan:** Server-enforced step locking (`is_locked=True` preserved across replans) and plan approval.
4. **Live Execution & SSE Progress:** Real-time Server-Sent Events (`task_snapshot`, `step_progress`, `artifact_updated`, `approval_requested`, `task_interrupted`, `task_completed`).
5. **Mid-Execution Interrupt & Persistence:** Cooperative cancellation halts scheduling cleanly, preserves completed work & partial drafts, measures interrupt latency, and writes an `interrupt` checkpoint.
6. **Step Modification & Mid-Flight Instructions:** Pending unlocked steps edited (`user_modified=True`) and mid-execution directives queued and integrated into subsequent outputs.
7. **Resume Without Redoing Completed Work:** Resumes strictly from the first non-completed step while enforcing mandatory high-risk approval gates (`Step 4`).
8. **Shared Artifact Co-Editing & Revision Restore:** Inline Markdown editing updates authorship to `collaborative`, generates AI-vs-Human line diffs, preserves `artifact_revisions`, and supports one-click **Restore vX**.
9. **Checkpoints, Comparison & Rollback:** Manual & automatic checkpoints persist across reloads/restarts; pre-rollback safety snapshots keep rollback reversible.
10. **Activity Timeline, Analytics, Evaluation & Settings:** Complete audit log (`interaction_events`), DB-computed analytics, 14-metric evaluation dashboard, persisted `autonomy_settings`, and verified server-side JWT revocation on `/api/auth/logout` (`401` on subsequent requests).

---

## 3. Manual Multi-Viewport Browser Test Checklist

> **Transparency Note:** Automated browser verification (Playwright / Chrome DevTools) was **not executed** because neither Playwright nor an active Chrome remote-debugging port is installed in this environment. Perform this checklist manually at `http://127.0.0.1:5173/` before live presentation.

### Viewports to Inspect
- [ ] **Desktop (`1440px`)** — Full fixed `228px` sidebar + 5/7 split-pane Workspace + zero horizontal overflow.
- [ ] **Laptop (`1280px`)** — ExecutionControlBar wraps cleanly without clipping buttons or ML Advisor pill.
- [ ] **Tablet (`768px`)** — Sidebar collapses to drawer toggle; Workspace switches to **Live Plan | Shared Artifact** tabs with Execution Controls always visible above.
- [ ] **Mobile (`390px`)** — Landing page, Auth forms, Workspace tabs, Analytics charts, and Evaluation tables remain legible with no broken layout overflow.

### Interactive & Accessibility Checks
- [ ] Open `⌘K` (macOS) / `Ctrl+K` (Windows/Linux) → test `↑`/`↓`, `Enter`, `Esc`, theme toggle, and unavailable-action toast feedback.
- [ ] Verify `Esc` closes New Task modal, Checkpoint Drawer, and Activity Drawer.
- [ ] Toggle Dark ↔ Light mode across Landing, Workspace, Analytics charts, and Evaluation charts; verify readable axis/tooltip contrast.
- [ ] Verify Navbar anchor links (`Product`, `Planning`, `Autonomy`, `Architecture`) work from `/login` and `/register`.
- [ ] Open browser DevTools Console and confirm **0 uncaught runtime errors** across all 7 routes.

---

## 4. Architecture & Database Documentation

### System Architecture
- **Frontend:** Vite + React 18 + TypeScript + Tailwind CSS + Recharts + Lucide Icons.
- **Backend:** Modular FastAPI application (`api/`, `orchestration/`, `execution/`, `checkpoints/`, `autonomy/`, `agents/`, `streaming/`, `services/`, `core/`).
- **Database:** SQLAlchemy 2.x ORM + Alembic migrations (`backend/alembic/versions/0001_vyrox_initial_schema.py`).

### Exact Database Schema (18 Tables Total)
- **17 Application Tables:** `users`, `auth_sessions`, `autonomy_settings`, `tasks`, `agent_plans`, `execution_steps`, `artifact_sections`, `artifact_revisions`, `checkpoints`, `interaction_events`, `autonomy_signals`, `evaluation_responses`, `user_feedback`, `ml_datasets`, `ml_model_versions`, `ml_evaluation_results`, `ml_prediction_logs`.
- **1 Migration Metadata Table:** `alembic_version` (at revision `0001_vyrox_initial (head)`).

### PostgreSQL Compatibility & Local Verification Status
- **Production Configuration:** Ready for PostgreSQL via `DATABASE_URL=postgresql+psycopg2://...` with `psycopg2-binary` installed and `pool_pre_ping=True`.
- **Actual Testing Performed:** Live PostgreSQL server testing was **not performed** because `psql` / PostgreSQL server is not installed on this local machine. All migrations and integration tests were executed against local **SQLite WAL** (`backend/vyrox.db` + isolated temp test DBs).

---

## 5. ML Methodology & Evaluation Report

- **Task:** Multi-class advisory supervision prediction (`supervised`, `balanced`, `higher_autonomy`) from 10 interaction/task features + 5 domain-engineered features (`ml/features/pipeline.py`).
- **Dataset Provenance:** `synthetic_supervision_v1` (**`SYNTHETIC_DEMO_DATASET`** — 1,800 rows, 309 deliberate missing cells imputed via train-fit median, seed `42`, stratified 70/15/15 split: `train=1260`, `val=270`, `test=270`, verified zero index leakage). **Not real user data; not validated on real-world users.**
- **Model Selection (strictly by Validation Macro-F1):**
  - `logistic_regression` (`C=1.0`): Val Macro-F1 `0.8375` (`2.131s`) — **Selected**
  - `random_forest`: Val Macro-F1 `0.7997` (`2.186s`)
  - `gradient_boosting`: Val Macro-F1 `0.7916` (`6.089s`)
  - `rule_based_baseline`: Val Macro-F1 `0.4070`
- **Held-Out Test Results (`n = 270`, Synthetic Demo Data):**
  - **Accuracy:** `0.8259` (vs. Rule-Based Baseline `0.4630`, `+0.3629`)
  - **Macro-F1:** `0.8302` (vs. Rule-Based Baseline `0.3676`, `+0.4626`)
  - **Macro Precision / Recall:** `0.8231` / `0.8410`
  - **ROC-AUC (OvR Macro):** `0.9546`
  - **Inference Latency:** `0.605 ms` mean (`0.643 ms` p95)
  - **Confusion Matrix (`[supervised, balanced, higher_autonomy]`):** `[[69, 7, 0], [16, 94, 14], [0, 10, 60]]`
- **Safety Guarantee:** Model predictions are strictly advisory. High-risk steps unconditionally require explicit human approval, locked steps cannot be modified by the agent, and manual user autonomy mode is never overwritten.

### Real-Participant HAI Evaluation Procedure (For Future User Study)
1. Recruit participants (`n >= 10` recommended for statistical power) using a within-subjects counterbalanced design (half start with Prompt-and-Wait, half with VYRO-X).
2. Assign comparable scenarios from `COMPARABLE_SCENARIOS` in `/evaluation` with a mandatory mid-task requirement change.
3. Capture all 14 system-logged operational metrics + post-task 1–7 Effort, Trust, and Control ratings + qualitative feedback.
4. Run paired statistical analysis (Wilcoxon signed-rank / paired t-test + effect sizes) directly on the persisted `evaluation_responses` and `tasks` records.

---

## 6. Known Limitations & Production-Readiness Checklist

### Known Limitations
- **Deterministic Demo Mode:** When `OPENAI_API_KEY` and `GEMINI_API_KEY` are unset, generation uses `vyrox-deterministic-v1` (clearly disclosed in the UI banner).
- **Single-Instance Architecture:** In-process `ExecutionManager`, `SSEBroker`, and `SlidingWindowRateLimiter` assume a single uvicorn worker; multi-worker horizontal scaling requires Redis-backed pub/sub, distributed locking, and shared rate limiting.
- **Synthetic ML Dataset & Unrun User Study:** ML metrics reflect `SYNTHETIC_DEMO_DATASET`; real-participant HAI comparison data starts at `n = 0` until live trials are run.
- **Unverified Live PostgreSQL & Automated Browser Visuals:** Local testing used SQLite WAL and HTTP/SSE/pytest automation without Playwright or a live Postgres server.

### Production-Readiness Checklist
- [ ] Provision managed PostgreSQL and run `alembic -c backend/alembic.ini upgrade head`.
- [ ] Set strong `JWT_SECRET_KEY`, restricted `CORS_ORIGINS`, and HTTPS termination.
- [ ] Configure live LLM credentials (`OPENAI_API_KEY` or `GEMINI_API_KEY`) with spend limits.
- [ ] Replace in-memory rate limiter / SSE broker with Redis for multi-worker deployment.
- [ ] Add Playwright multi-viewport CI tests and collect consented real-world ML training data.

---

## 7. Complete 5–7 Minute Live Academic Demonstration Script

| Time | Segment | Actions & Key Talking Points |
| :--- | :--- | :--- |
| **0:00–0:45** | **Problem & VYRO-X Overview** | Open `http://127.0.0.1:5173/`. Contrast conventional prompt-and-wait with VYRO-X (*"Work with AI. Stay in Control."*). Toggle the interactive **Step Lock** and **Autonomy Mode** previews on the landing page. |
| **0:45–1:30** | **Auth & Task Planning** | Click **Explore Workspace** → Register/Sign in. Create a task using the *Distributed Consensus* preset. Point out the **Deterministic Demo Mode** disclosure banner, the structured 5-step plan with risk tiers/rationale, and the advisory **ML Advisor** badge. |
| **1:30–2:45** | **Lock, Start, Live SSE & Mid-Run Interrupt** | Click **Lock** on Step 1. Click **Approve Plan** / **Start Task**. Point out live SSE micro-stage streaming and live artifact updates. Click **Interrupt** mid-run — show immediate safe halt, saved `Mid-Run Interrupt` checkpoint, and preserved state. |
| **2:45–3:45** | **Edit, Mid-Flight Guidance & Step-Skipping Resume** | While interrupted, **Edit** an unlocked pending step and use **Add Instructions** to inject a failover SLO requirement. Click **Resume** — emphasize that completed steps are never repeated. Pause at high-risk **Step 4** to show the mandatory safety gate, then click **Approve Step 4** to finish. |
| **3:45–4:45** | **Artifact Co-Editing, Revisions & Checkpoint Rollback** | In the Right Panel, click **Edit** on Section 1, add a human review note, save, and open **Diff** (AI vs. Human lines) + **History** (**Restore vX**). Open **Rollback** (`⌘K` → *Checkpoints*), compare two checkpoints side-by-side, and demonstrate restoring a prior state. |
| **4:45–6:00** | **Analytics, ML Model & 14-Metric Evaluation** | Open **Analytics & ML** via the sidebar: show real DB telemetry + the trained Adaptive Supervision model (`Macro-F1 0.8302` vs. Rule Baseline `0.3676`, `SYNTHETIC_DEMO_DATASET` badge, confusion matrix). Open **Evaluation**: run a live **Prompt-and-Wait Baseline** trial, submit 1–7 ratings, and explain the 14 metrics + honest provenance separation. |
| **6:00–6:30** | **Settings, Logout & Q&A** | Open **Settings** (show opt-in ML training consent defaulting to Off, locked high-risk safety invariant). Click **Sign Out** and note server-side JWT session revocation (`auth_sessions`). |
