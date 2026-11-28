export type TaskStatus =
  | 'CREATED'
  | 'PLANNING'
  | 'AWAITING_APPROVAL'
  | 'RUNNING'
  | 'PAUSED'
  | 'INTERRUPTED'
  | 'RESUMING'
  | 'COMPLETED'
  | 'FAILED'
  | 'ROLLED_BACK';

export type StepStatus =
  | 'PENDING'
  | 'PLANNING'
  | 'RUNNING'
  | 'AWAITING_APPROVAL'
  | 'COMPLETED'
  | 'INTERRUPTED'
  | 'PAUSED'
  | 'FAILED'
  | 'REJECTED';

export type AutonomyMode = 'supervised' | 'balanced' | 'higher_autonomy';
export type RiskLevel = 'low' | 'medium' | 'high';
export type InteractionMode = 'vyrox' | 'baseline';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  default_autonomy_mode: AutonomyMode;
  adaptive_autonomy_enabled: boolean;
  ml_recommendations_enabled: boolean;
  training_consent_opt_in: boolean;
  require_plan_approval: boolean;
  require_high_risk_approval: boolean;
  theme_preference: 'light' | 'dark' | 'system';
  notifications_enabled: boolean;
  created_at: string;
}

export interface SystemInfo {
  product_name?: string;
  tagline?: string;
  provider_mode: 'demo' | 'live';
  provider_name: string;
  database_dialect: string;
  demo_notice: string;
}

export interface StepSource {
  title: string;
  type: string;
  reference: string;
  reliability_note: string;
  authors?: string | null;
  year?: number | string | null;
  venue?: string | null;
  doi?: string | null;
  url?: string | null;
  provider?: string | null;
  access_status?: string | null;
  used?: boolean | null;
  abstract?: string | null;
  filename?: string | null;
  page?: number | null;
}

export type CitationStyle = 'ieee' | 'apa' | 'simple';

export type ClaimSupport = 'evidence_backed' | 'partial' | 'unverified' | 'stale' | 'no_research';

export interface Claim {
  index: number;
  text: string;
  support: ClaimSupport;
  support_label: string;
  ref_numbers: number[];
  supporting_passage: string;
}

export interface ExecutionStep {
  id: string;
  task_id: string;
  step_order: number;
  title: string;
  description: string;
  rationale: string;
  expected_outcome: string;
  risk_level: RiskLevel;
  status: StepStatus;
  is_locked: boolean;
  requires_approval: boolean;
  approved_by_user: boolean;
  approval_reason: string;
  confidence_basis: string;
  uncertainty_notes: string;
  sources: StepSource[];
  output_content: string;
  partial_output: string;
  completed_stages: string[];
  user_modified: boolean;
  user_edit_note: string;
  rejected_reason: string | null;
  revision_number: number;
  duration_ms: number;
  started_at: string | null;
  completed_at: string | null;
  updated_at: string | null;
}

export interface ArtifactSection {
  id: string;
  task_id: string;
  step_id: string | null;
  section_order: number;
  heading: string;
  ai_content: string;
  current_content: string;
  authorship: 'ai' | 'human' | 'collaborative';
  version: number;
  has_user_edits: boolean;
  updated_at: string | null;
  claims?: Claim[];
}

export interface ArtifactDiffLine {
  type: 'unchanged' | 'added' | 'removed';
  text: string;
}

export interface ArtifactSectionDiff {
  section_id: string;
  heading: string;
  authorship: string;
  has_user_changes: boolean;
  lines_added: number;
  lines_removed: number;
  diff: ArtifactDiffLine[];
}

export interface ArtifactRevision {
  id: string;
  version: number;
  author_type: 'ai' | 'human' | 'rollback';
  summary: string;
  content: string;
  created_at: string | null;
}

export interface CheckpointItem {
  id: string;
  task_id: string;
  version_number: number;
  label: string;
  trigger_type: string;
  task_status: TaskStatus;
  current_step_index: number;
  completed_steps_count: number;
  total_steps_count: number;
  created_at: string | null;
}

export interface CheckpointComparison {
  from_checkpoint: Partial<CheckpointItem>;
  to_checkpoint: Partial<CheckpointItem>;
  step_diffs: Array<{
    step_order: number;
    title: string;
    change_type: string;
    changes: string[];
  }>;
  artifact_unified_diff: string[];
}

export interface InteractionEvent {
  id: string;
  task_id: string;
  step_id: string | null;
  event_type: string;
  actor: 'human' | 'agent' | 'system';
  summary: string;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export interface AdditionalInstruction {
  id: string;
  text: string;
  added_at: string;
  step_index: number;
  task_status_when_added: string;
}

export interface TaskSummary {
  id: string;
  title: string;
  prompt: string;
  topic: string;
  interaction_mode: InteractionMode;
  provider_mode: 'demo' | 'live';
  provider_name: string;
  status: TaskStatus;
  autonomy_mode: AutonomyMode;
  adaptive_enabled: boolean;
  adaptive_caution_level: 'relaxed' | 'normal' | 'elevated_caution';
  adaptive_reason: string;
  complexity_score?: number;
  ml_recommended_autonomy?: AutonomyMode | null;
  ml_recommendation_confidence?: number | null;
  ml_model_version?: string | null;
  ml_recommendation_reason?: string;
  plan_approved: boolean;
  current_step_index: number;
  current_activity: string;
  is_interruptible: boolean;
  completed_steps_count: number;
  total_steps_count: number;
  progress_percent: number;
  checkpoints_count: number;
  interruption_count: number;
  recovery_count: number;
  plan_edits_count: number;
  total_execution_ms: number;
  research_enabled: boolean;
  research_status: string;
  research_duration_ms: number | null;
  research_used_count: number;
  research_retrieved_count: number;
  research_used: StepSource[];
  research_retrieved: StepSource[];
  citation_style: CitationStyle;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface TaskDetail extends TaskSummary {
  error_message: string | null;
  additional_instructions: AdditionalInstruction[];
  steps: ExecutionStep[];
  artifact_sections: ArtifactSection[];
  checkpoints: CheckpointItem[];
  recent_events: InteractionEvent[];
}

export interface AnalyticsData {
  has_data: boolean;
  summary: {
    total_tasks: number;
    vyrox_tasks: number;
    baseline_tasks: number;
    completed_tasks: number;
    task_completion_rate: number;
    approvals_count: number;
    rejections_count: number;
    approval_rate: number;
    rejection_rate: number;
    total_modifications: number;
    modification_frequency_per_task: number;
    total_interventions: number;
    intervention_frequency_per_task: number;
    autonomy_adjustments_count: number;
  };
  event_distribution: Array<{ category: string; count: number }>;
  timeline: Array<{ date: string; approvals: number; modifications: number; interventions: number }>;
  recent_autonomy_signals: Array<{
    id: string;
    task_id: string;
    signal_type: string;
    step_risk_level: string;
    previous_caution: string;
    new_caution: string;
    reason: string;
    created_at: string | null;
  }>;
  epistemic_note: string;
}

export interface ModeMetrics {
  sample_size: number;
  task_completion_rate: number | null;
  avg_completion_time_sec: number | null;
  avg_interventions_per_task: number | null;
  avg_user_effort: number | null;
  avg_perceived_trust: number | null;
  avg_perceived_control: number | null;
  recovery_success_rate: number | null;
  plan_modification_success_rate: number | null;
  avg_approval_response_sec: number | null;
  avg_interrupt_latency_ms: number | null;
  checkpoint_restoration_success_rate: number | null;
  agent_execution_failure_rate: number | null;
  artifact_revision_success_rate: number | null;
  avg_sse_update_latency_ms: number | null;
  failed_tasks: number;
  interrupted_tasks: number;
  recovered_tasks: number;
  ratings_count: number;
}

export interface StatisticalTestResult {
  metric: string;
  vyrox: { n: number; mean: number | null; std: number | null; median: number | null; ci_95: [number, number] | null };
  baseline: { n: number; mean: number | null; std: number | null; median: number | null; ci_95: [number, number] | null };
  sufficient_data: boolean;
  note: string;
  welch_t_p: number | null;
  mann_whitney_p: number | null;
  cohens_d: number | null;
}

export interface EvaluationDashboardData {
  data_provenance: string;
  has_measured_comparison: boolean;
  measured: {
    vyrox: ModeMetrics;
    baseline: ModeMetrics;
  };
  statistical_tests: StatisticalTestResult[];
  illustrative_demo_reference: {
    data_provenance: string;
    disclaimer: string;
    vyrox_illustrative: Record<string, number | null>;
    baseline_illustrative: Record<string, number | null | string>;
  };
  comparable_scenarios: Array<{
    key: string;
    title: string;
    difficulty: string;
    prompt: string;
  }>;
  recent_ratings: Array<{
    id: string;
    task_id: string;
    interaction_mode: InteractionMode;
    scenario_key: string;
    effort_rating: number;
    trust_rating: number;
    control_rating: number;
    notes: string;
    created_at: string | null;
  }>;
  recent_feedback: Array<{
    id: string;
    task_id: string | null;
    category: string;
    rating: number;
    comment: string;
    created_at: string | null;
  }>;
  methodology: {
    baseline_definition: string;
    proposed_model_definition: string;
    protocol_steps: string[];
    metric_definitions: Array<{
      metric: string;
      measures: string;
      cannot_establish: string;
    }>;
    known_limitations: string[];
  };
}

export interface MLPredictionResponse {
  available: boolean;
  recommended_autonomy: AutonomyMode;
  probabilities: Record<string, number>;
  confidence: number;
  model_version: string;
  algorithm: string;
  dataset_provenance: string;
  inference_latency_ms: number;
  explanation: string;
  safety_notice: string;
  features_used?: Record<string, number>;
}

export interface MLStatusResponse {
  model_available: boolean;
  dataset_provenance: string;
  provenance_disclosure: string;
  latest_report: {
    trained_at: string;
    random_seed: number;
    selection_metric: string;
    dataset: {
      dataset_version: string;
      dataset_provenance: string;
      sample_count: number;
      class_distribution: Record<string, number>;
      sha256_hash: string;
    };
    splits: {
      train_count: number;
      validation_count: number;
      test_count: number;
      leakage_verified: boolean;
    };
    selected_model: {
      model_version: string;
      algorithm: string;
      training_time_sec: number;
      inference_latency: { mean_ms: number; p95_ms: number; runs: number };
      feature_importances: Record<string, number>;
      best_params: Record<string, unknown>;
    };
    test_evaluation: {
      selected_model: {
        accuracy: number;
        precision_macro: number;
        recall_macro: number;
        f1_macro: number;
        roc_auc_ovr: number | null;
        classes: string[];
        confusion_matrix: number[][];
        class_report: Record<string, { precision: number; recall: number; f1_score: number; support: number }>;
      };
      logistic_regression_baseline: { f1_macro: number; accuracy: number; roc_auc_ovr: number | null };
      rule_based_baseline: { f1_macro: number; accuracy: number; recall_macro: number };
      delta_vs_rule_baseline: { f1_macro_delta: number; accuracy_delta: number; recall_macro_delta: number };
    };
    limitations: string[];
  } | null;
  registered_versions: Array<{
    model_version: string;
    algorithm: string;
    dataset_version: string;
    dataset_provenance: string;
    training_time_sec: number;
    inference_latency_ms: number;
    is_active: boolean;
    created_at: string | null;
  }>;
  monitoring: {
    total_predictions_logged: number;
    user_agreement_rate_pct: number | null;
    avg_live_inference_latency_ms: number | null;
    recent_predictions: Array<{
      id: string;
      task_id: string | null;
      model_version: string;
      predicted_autonomy: string;
      user_actual_mode: string | null;
      inference_latency_ms: number;
      created_at: string | null;
    }>;
  };
}
