# VYRO-X Adaptive Supervision Prediction Dataset Documentation

## Provenance & Disclosure

- **Dataset Identifier:** `synthetic_supervision_v1`
- **Source Type:** `SYNTHETIC_DEMO_DATASET`
- **Real-World User Validation Status:** **Not validated on real-world users.** This dataset is a reproducible synthetic demonstration dataset created because real labelled production user supervision telemetry is not yet available.
- **Privacy & Consent Separation:** Synthetic records are stored strictly under `ml/data/`. Private user interaction records in the VYRO-X database are never included in training unless a user explicitly enables `training_consent_opt_in` in Settings, and real datasets are kept strictly separate from synthetic datasets.

## Feature Schema

| Feature | Type | Range / Encoding | Description |
| :--- | :--- | :--- | :--- |
| `prev_approvals` | int | `>= 0` | Historical approved agent steps |
| `prev_rejections` | int | `>= 0` | Historical rejected agent proposals |
| `user_corrections` | int | `>= 0` | Historical corrective signals (artifact edits, replans) |
| `interruptions_count` | int | `>= 0` | Mid-execution interrupts triggered by the human |
| `manual_step_edits` | int | `>= 0` | Explicit edits made to proposed step instructions |
| `task_complexity` | float | `[0.0, 1.0]` | Normalized structural complexity of the task |
| `task_risk_level` | int | `{0: low, 1: medium, 2: high}` | Maximum risk tier present in the task plan |
| `prev_completion_rate` | float | `[0.0, 1.0]` | Prior task completion reliability |
| `intervention_frequency` | float | `>= 0.0` | Average human interventions per task |
| `historical_recovery_rate` | float | `[0.0, 1.0]` | Historical recovery success after interrupts/failures |

## Target Label Generation Methodology

Target labels (`supervised`, `balanced`, `higher_autonomy`) are **not** inferred solely from approval counts or intervention frequency. Instead, `generate_dataset.py` models a composite latent supervision requirement score combining:
1. Task-inherent risk and structural complexity (including non-linear `risk * complexity` interaction).
2. Historical execution reliability (`prev_completion_rate` and `historical_recovery_rate`).
3. Behavioural friction signals (rejections, corrections, edits, interruptions, and intervention frequency).
4. Controlled stochastic label ambiguity (`N(0, 0.28)`) to reflect real-world preference variance and prevent trivial rule memorization.
5. Deliberate 2% missing values across numeric features to exercise median imputation inside the scikit-learn pipeline.

## Limitations

- Performance metrics obtained on `synthetic_supervision_v1` measure model fidelity on simulated interaction distributions only.
- Before deploying autonomous supervision adjustments in production, consented real-world human-in-the-loop interaction logs with explicit user-rated preferred supervision levels must be collected and evaluated.
