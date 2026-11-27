# VYRO-X
### **Human Intelligence. Agent Evolution.**

> **"Work with AI. Stay in Control."**  
> An intelligent collaborative workspace where humans guide, supervise, and collaborate with adaptive AI agents.

VYRO-X replaces opaque prompt-and-wait AI workflows with a continuous, transparent, interruptible, checkpointed human-agent collaboration platform backed by relational persistence (PostgreSQL / SQLite + Alembic), a reproducible Adaptive Supervision ML pipeline, and a 14-metric scientific evaluation suite.

---

## Key Capabilities

1. **Split-Pane Collaborative Workspace**
   - **Live Agent Plan (Left Panel):** Structured multi-step decomposition with rationale, expected outcome, risk tier, evidence basis, inline editing, immutable user locks, approve/reject controls (rejections generate revised alternatives), and lock-safe replanning.
   - **Shared Collaborative Artifact (Right Panel):** Live section-by-section synthesis linked to originating steps, inline human co-editing, `AI Generated` / `Co-Authored` / `Human Authored` attribution, line-level AI-vs-Human diffs, revision history with one-click restore, and Markdown export.
2. **Genuine Mid-Execution Interrupt & Resume**
   - Cooperative micro-stage async runner (`backend/execution/runner.py`) with atomic commit boundaries, instant interrupt wake-up, persisted partial progress, automatic interrupt checkpoints, restart orphan recovery, and step-skipping resumption.
3. **Production-Ready Relational Database & Alembic Migrations**
   - 17 normalized SQLAlchemy 2.x application tables (`users`, `auth_sessions`, `autonomy_settings`, `tasks`, `agent_plans`, `execution_steps`, `artifact_sections`, `artifact_revisions`, `checkpoints`, `interaction_events`, `autonomy_signals`, `evaluation_responses`, `user_feedback`, `ml_datasets`, `ml_model_versions`, `ml_evaluation_results`, `ml_prediction_logs`, plus `alembic_version` = 18 total tables).
   - Supports **PostgreSQL** (recommended production) and **SQLite WAL** (local development fallback) via `DATABASE_URL` and Alembic migrations (`backend/alembic/`).
4. **Reproducible Adaptive Supervision ML Pipeline (`ml/`)**
   - Predicts advisory supervision mode (`supervised` | `balanced` | `higher_autonomy`) from 10 interaction & task features plus 5 domain-engineered features.
   - Compares **Logistic Regression**, **Random Forest**, **Gradient Boosting**, and a **Rule-Based Baseline** using 5-fold stratified CV on Train, selecting by Validation **Macro-F1**, and evaluating once on a strictly disjoint held-out Test split.
   - Trained on a clearly labelled **synthetic demonstration dataset** (`SYNTHETIC_DEMO_DATASET`, documented in `ml/data/README.md`). Advisory only — never overrides manual user controls, locked steps, or mandatory high-risk approvals.
5. **14-Metric Scientific Evaluation & Statistical Analysis**
   - Live Paired Benchmark Runner comparing **Prompt-and-Wait Baseline** vs. **VYRO-X** across 14 operational and human-experience metrics with SciPy statistical inference (mean, SD, median, 95% CI, Welch's t-test, Mann-Whitney U, Cohen's d) and strict data provenance separation.

---

## Project Structure

```text
OGX-4/
├── .env.example
├── backend/
│   ├── alembic.ini              # Alembic migration configuration
│   ├── alembic/                 # Database migration scripts
│   ├── main.py                  # FastAPI app, security headers, global error handling
│   ├── core/                    # Env config, PBKDF2 + persisted JWT sessions, rate limiting
│   ├── database/                # SQLAlchemy 2.x engine & session management
│   ├── models/                  # 17 ORM tables (Users, Sessions, Plans, Tasks, ML Registry, etc.)
│   ├── orchestration/           # State machine & versioned planning/replanning
│   ├── execution/               # Cooperative async runner & human control service
│   ├── checkpoints/             # Persistent snapshots, comparison diffs & rollback
│   ├── autonomy/                # Adaptive policy engine & hard safety invariants
│   ├── agents/                  # Dual-mode AgentProvider (Deterministic Demo / OpenAI / Gemini)
│   ├── streaming/               # Thread-safe Server-Sent Events (SSE) broker with latency timestamps
│   ├── services/                # ML service, artifact versioning, analytics, 14-metric evaluation
│   ├── api/                     # Modular REST & SSE routers (auth, tasks, steps, checkpoints, artifacts, stream, analytics, evaluation, ml)
│   └── tests/                   # Comprehensive pytest suite
├── ml/
│   ├── config/training_config.json
│   ├── data/                    # Synthetic generator, validator, dataset documentation
│   ├── features/                # Leakage-safe sklearn Pipeline & rule-based baseline
│   ├── training/                # Reproducible CV training, selection & DB registration
│   ├── evaluation/              # Classification metrics, latency benchmark & JSON report
│   ├── models/                  # Serialized joblib artifacts & version registry
│   └── inference/               # Production advisory prediction service
└── frontend/
    ├── public/favicon.svg       # Custom VYRO-X geometric emblem
    └── src/
        ├── components/          # VyroLogo, Navbar, StatusBadge, ModeBanner
        ├── pages/               # Landing, Login, Register, Workspace, History, Analytics, Evaluation, Settings
        ├── workspace/           # ExecutionControlBar, LivePlanPanel, StepCard, SharedArtifactPanel, Drawers
        └── services/            # Typed REST API client & SSE hook
```

---

## Database Setup & Migrations

### Local Development (SQLite Fallback)
```bash
cp .env.example .env
./backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```
This initializes `backend/vyrox.db` in WAL mode with foreign keys enabled.

### Production (PostgreSQL)
Set `DATABASE_URL` in `.env`:
```env
DATABASE_URL=postgresql+psycopg2://vyrox_user:strong_password@localhost:5432/vyrox
```
Then apply migrations:
```bash
./backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
```
*Database-specific note:* SQLite uses `PRAGMA journal_mode=WAL` and `render_as_batch=True` in Alembic for safe schema evolution; PostgreSQL uses native transactional DDL and connection pooling (`pool_pre_ping=True`).

---

## Reproducible ML Model Training

Run the complete dataset generation, validation, CV training, test evaluation, serialization, and DB registration pipeline:
```bash
./backend/.venv/bin/python -m ml.training.train
```
Outputs:
- Dataset: `ml/data/synthetic_supervision_v1.csv` (`SYNTHETIC_DEMO_DATASET`, seed `42`)
- Serialized model: `ml/models/vyrox_supervision_<algorithm>_<timestamp>.joblib`
- Registry & Evaluation Report: `ml/models/registry.json` and `ml/evaluation/latest_evaluation_report.json`

---

## Application Startup

### 1. Backend (FastAPI)
```bash
cd backend
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cd ..
./backend/.venv/bin/alembic -c backend/alembic.ini upgrade head
./backend/.venv/bin/uvicorn backend.main:app --reload --port 8000
```
OpenAPI documentation: `http://127.0.0.1:8000/docs`

### 2. Frontend (Vite + React + TypeScript)
```bash
cd frontend
npm install
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.

---

## Running Tests

```bash
# Backend, DB migrations, auth sessions, interrupt/resume, rollback & ML tests
./backend/.venv/bin/python -m pytest -v backend/tests/

# Frontend TypeScript check & production build
cd frontend && npm run build
```

---

## End-to-End Demonstration Guide

1. Open `http://127.0.0.1:5173` to explore the **VYRO-X** landing page.
2. Click **Explore Workspace** and create an account (`/register`).
3. Choose a technical research preset (e.g., *Distributed Consensus*) and click **Generate Structured Plan**.
4. Inspect the 5-step plan, **Lock** Step 1, observe the advisory **ML Advisor** badge, and click **Approve Plan**.
5. While execution streams live over SSE, click **Interrupt** — VYRO-X halts safely, records interrupt latency, and saves a persistent checkpoint.
6. Edit an unlocked pending step, inject a mid-flight instruction via **Add Instructions**, and click **Resume** (completed steps are never repeated).
7. Approve the mandatory high-risk Step 4 gate to complete the report.
8. Co-edit a section in the **Shared Collaborative Artifact**, inspect **Diff**, and test **History → Restore vX**.
9. Open **Rollback** to compare checkpoints and restore an earlier snapshot; refresh the browser to verify persistence.
10. Visit **Analytics** (real DB metrics + trained ML evaluation & confusion matrix) and **Evaluation** (run a matched Prompt-and-Wait Baseline trial and inspect all 14 metrics + statistical analysis).

---

## Known Limitations

- **Deterministic Demo Mode:** When `OPENAI_API_KEY` and `GEMINI_API_KEY` are unset, generation uses the clearly labelled local deterministic research engine (`vyrox-deterministic-v1`).
- **Synthetic ML Dataset:** The Adaptive Supervision Prediction Model is trained on `synthetic_supervision_v1` (`SYNTHETIC_DEMO_DATASET`) and has not yet been validated on consented real-world user populations.
- **Statistical Power:** Two-group SciPy statistical tests (`Welch's t-test`, `Mann-Whitney U`, `Cohen's d`) require `n >= 2` recorded sessions in both VYRO-X and Baseline groups; below that threshold, the UI explicitly reports insufficient observations.


gf