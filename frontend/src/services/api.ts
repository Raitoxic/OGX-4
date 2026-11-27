import type {
  AnalyticsData,
  ArtifactRevision,
  ArtifactSection,
  ArtifactSectionDiff,
  AutonomyMode,
  CheckpointComparison,
  CheckpointItem,
  EvaluationDashboardData,
  ExecutionStep,
  InteractionEvent,
  InteractionMode,
  MLPredictionResponse,
  MLStatusResponse,
  SystemInfo,
  TaskDetail,
  TaskSummary,
  UserProfile,
} from '../types/hai';

const TOKEN_KEY = 'vyrox_auth_token';

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export function apiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(apiUrl(path), { ...options, headers });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const errBody = await res.json();
      if (typeof errBody.detail === 'string') {
        detail = errBody.detail;
      } else if (Array.isArray(errBody.detail) && errBody.detail[0]?.msg) {
        detail = errBody.detail[0].msg;
      }
    } catch {
      // fallback to status message
    }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // System
  systemInfo: () => request<SystemInfo>('/api/auth/system-info'),

  // Auth
  register: (body: { email: string; full_name: string; password: string }) =>
    request<{ access_token: string; user: UserProfile }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  login: (body: { email: string; password: string }) =>
    request<{ access_token: string; user: UserProfile }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  logout: () => request<{ status: string }>('/api/auth/logout', { method: 'POST' }),
  getMe: () => request<UserProfile>('/api/auth/me'),
  updateProfile: (body: Partial<UserProfile>) =>
    request<UserProfile>('/api/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    request<{ status: string }>('/api/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  // Tasks
  listTasks: (mode?: InteractionMode) =>
    request<{ tasks: TaskSummary[] }>(mode ? `/api/tasks?interaction_mode=${mode}` : '/api/tasks'),
  createTask: (body: {
    prompt: string;
    title?: string;
    interaction_mode?: InteractionMode;
    autonomy_mode?: AutonomyMode;
    adaptive_enabled?: boolean;
  }) =>
    request<TaskDetail>('/api/tasks', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getTask: (taskId: string) => request<TaskDetail>(`/api/tasks/${taskId}`),
  deleteTask: (taskId: string) => request<{ status: string }>(`/api/tasks/${taskId}`, { method: 'DELETE' }),

  // Execution Controls
  startTask: (taskId: string) => request<TaskDetail>(`/api/tasks/${taskId}/start`, { method: 'POST' }),
  pauseTask: (taskId: string) => request<TaskDetail>(`/api/tasks/${taskId}/pause`, { method: 'POST' }),
  interruptTask: (taskId: string) =>
    request<{ message: string; deferred_atomic: boolean; task: TaskDetail }>(`/api/tasks/${taskId}/interrupt`, {
      method: 'POST',
    }),
  resumeTask: (taskId: string) => request<TaskDetail>(`/api/tasks/${taskId}/resume`, { method: 'POST' }),
  approveTask: (taskId: string, body?: { step_id?: string; auto_continue?: boolean }) =>
    request<TaskDetail>(`/api/tasks/${taskId}/approve`, {
      method: 'POST',
      body: JSON.stringify(body ?? { auto_continue: true }),
    }),
  replanTask: (taskId: string, reason: string) =>
    request<TaskDetail>(`/api/tasks/${taskId}/replan`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  addInstruction: (taskId: string, instruction: string) =>
    request<{ instruction: unknown; task: TaskDetail }>(`/api/tasks/${taskId}/instructions`, {
      method: 'POST',
      body: JSON.stringify({ instruction }),
    }),
  updateAutonomy: (taskId: string, body: { autonomy_mode?: AutonomyMode; adaptive_enabled?: boolean }) =>
    request<TaskDetail>(`/api/tasks/${taskId}/autonomy`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  getTaskHistory: (taskId: string, params?: { event_type?: string; actor?: string }) => {
    const qs = new URLSearchParams();
    if (params?.event_type) qs.set('event_type', params.event_type);
    if (params?.actor) qs.set('actor', params.actor);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return request<{ task_id: string; events: InteractionEvent[] }>(`/api/tasks/${taskId}/history${suffix}`);
  },

  // Step Controls
  editStep: (
    taskId: string,
    stepId: string,
    body: { title?: string; description?: string; expected_outcome?: string; edit_note?: string },
  ) =>
    request<{ step: ExecutionStep; task: TaskDetail }>(`/api/tasks/${taskId}/steps/${stepId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  lockStep: (taskId: string, stepId: string, is_locked: boolean) =>
    request<{ step: ExecutionStep; task: TaskDetail }>(`/api/tasks/${taskId}/steps/${stepId}/lock`, {
      method: 'POST',
      body: JSON.stringify({ is_locked }),
    }),
  approveStep: (taskId: string, stepId: string, auto_continue = true) =>
    request<TaskDetail>(`/api/tasks/${taskId}/steps/${stepId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ auto_continue }),
    }),
  rejectStep: (taskId: string, stepId: string, reason: string, generate_alternative = true) =>
    request<{ step: ExecutionStep; task: TaskDetail }>(`/api/tasks/${taskId}/steps/${stepId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason, generate_alternative }),
    }),

  // Checkpoints & Rollback
  listCheckpoints: (taskId: string) =>
    request<{ checkpoints: CheckpointItem[] }>(`/api/tasks/${taskId}/checkpoints`),
  createCheckpoint: (taskId: string, label: string) =>
    request<CheckpointItem>(`/api/tasks/${taskId}/checkpoints`, {
      method: 'POST',
      body: JSON.stringify({ label }),
    }),
  compareCheckpoints: (taskId: string, fromId: string, toId: string) =>
    request<CheckpointComparison>(
      `/api/tasks/${taskId}/checkpoints/compare?from_id=${encodeURIComponent(fromId)}&to_id=${encodeURIComponent(toId)}`,
    ),
  rollbackCheckpoint: (taskId: string, checkpointId: string) =>
    request<{ restored_checkpoint: CheckpointItem; task: TaskDetail }>(
      `/api/tasks/${taskId}/checkpoints/${checkpointId}/rollback`,
      { method: 'POST' },
    ),

  // Shared Artifact
  editArtifactSection: (
    taskId: string,
    sectionId: string,
    body: { heading?: string; current_content: string },
  ) =>
    request<ArtifactSection>(`/api/tasks/${taskId}/artifact/sections/${sectionId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  addArtifactSection: (taskId: string, body: { heading: string; content: string }) =>
    request<ArtifactSection>(`/api/tasks/${taskId}/artifact/sections`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getSectionDiff: (taskId: string, sectionId: string) =>
    request<ArtifactSectionDiff>(`/api/tasks/${taskId}/artifact/sections/${sectionId}/diff`),
  getSectionRevisions: (taskId: string, sectionId: string) =>
    request<{ revisions: ArtifactRevision[] }>(`/api/tasks/${taskId}/artifact/sections/${sectionId}/revisions`),

  // Analytics, Evaluation, Feedback & ML
  getAnalytics: () => request<AnalyticsData>('/api/analytics'),
  getEvaluation: () => request<EvaluationDashboardData>('/api/evaluation'),
  submitEvaluationRating: (body: {
    task_id: string;
    scenario_key: string;
    effort_rating: number;
    trust_rating: number;
    control_rating: number;
    notes: string;
  }) =>
    request<unknown>('/api/evaluation/rate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  submitFeedback: (body: {
    task_id?: string;
    category: 'general' | 'usability' | 'autonomy' | 'accuracy' | 'bug' | 'suggestion';
    rating: number;
    comment: string;
  }) =>
    request<unknown>('/api/evaluation/feedback', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  recordSseLatency: (taskId: string, latency_ms: number) =>
    request<{ recorded: boolean }>(`/api/tasks/${taskId}/telemetry/sse-latency`, {
      method: 'POST',
      body: JSON.stringify({ latency_ms }),
    }),
  getMlStatus: () => request<MLStatusResponse>('/api/ml/status'),
  predictSupervision: (taskId: string) =>
    request<MLPredictionResponse>(`/api/ml/predict/${taskId}`, { method: 'POST' }),
  retrainModel: () => request<unknown>('/api/ml/retrain', { method: 'POST' }),
};
