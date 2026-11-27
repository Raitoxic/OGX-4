import { useEffect, useRef, useState } from 'react';
import { api, apiUrl, getStoredToken } from '../services/api';
import type { TaskDetail } from '../types/hai';

interface LiveProgress {
  stepId: string | null;
  activity: string;
  stageLabel?: string;
  isInterruptible: boolean;
}

interface UseTaskStreamOptions {
  taskId: string | null;
  onSyncRequired: () => void;
  onSnapshot?: (task: TaskDetail) => void;
  onToast?: (message: string, tone?: 'info' | 'warning' | 'success' | 'error') => void;
}

export function useTaskStream({ taskId, onSyncRequired, onSnapshot, onToast }: UseTaskStreamOptions) {
  const [connected, setConnected] = useState(false);
  const [liveProgress, setLiveProgress] = useState<LiveProgress | null>(null);

  const syncRef = useRef(onSyncRequired);
  const snapRef = useRef(onSnapshot);
  const toastRef = useRef(onToast);
  syncRef.current = onSyncRequired;
  snapRef.current = onSnapshot;
  toastRef.current = onToast;

  useEffect(() => {
    if (!taskId) {
      setConnected(false);
      setLiveProgress(null);
      return;
    }
    const token = getStoredToken();
    if (!token) return;

    const url = apiUrl(
      `/api/tasks/${encodeURIComponent(taskId)}/stream?token=${encodeURIComponent(token)}`,
    );
    const es = new EventSource(url);

    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);

    es.addEventListener('task_snapshot', (ev: MessageEvent) => {
      try {
        const snapshot = JSON.parse(ev.data) as TaskDetail;
        snapRef.current?.(snapshot);
        setLiveProgress({
          stepId: null,
          activity: snapshot.current_activity,
          isInterruptible: snapshot.is_interruptible,
        });
      } catch {
        // ignore parse errors
      }
    });

    es.addEventListener('step_progress', (ev: MessageEvent) => {
      try {
        const envelope = JSON.parse(ev.data);
        if (typeof envelope.emitted_at_ms === 'number') {
          const latency = Math.max(0, Date.now() - envelope.emitted_at_ms);
          if (latency < 30000) {
            api.recordSseLatency(taskId, latency).catch(() => {});
          }
        }
        const d = envelope.data || {};
        setLiveProgress({
          stepId: d.step_id ?? null,
          activity: d.activity || 'Working...',
          stageLabel: d.detail,
          isInterruptible: d.is_interruptible ?? true,
        });
        syncRef.current();
      } catch {
        // ignore
      }
    });

    const syncEvents = [
      'task_state_changed',
      'plan_generated',
      'step_updated',
      'artifact_updated',
      'checkpoint_created',
      'instruction_added',
      'autonomy_adjusted',
      'activity_event',
    ];
    for (const evtName of syncEvents) {
      es.addEventListener(evtName, () => {
        syncRef.current();
      });
    }

    es.addEventListener('approval_requested', (ev: MessageEvent) => {
      syncRef.current();
      try {
        const d = JSON.parse(ev.data)?.data;
        toastRef.current?.(`Approval needed for Step ${d?.step_order ?? ''}: ${d?.title ?? ''}`, 'warning');
      } catch {
        toastRef.current?.('Human approval requested to proceed.', 'warning');
      }
    });

    es.addEventListener('task_interrupted', () => {
      syncRef.current();
      toastRef.current?.('Execution interrupted safely. Persistent checkpoint saved.', 'info');
    });

    es.addEventListener('task_resumed', () => {
      syncRef.current();
      toastRef.current?.('Resumed execution from saved checkpoint.', 'info');
    });

    es.addEventListener('task_rolled_back', (ev: MessageEvent) => {
      syncRef.current();
      try {
        const d = JSON.parse(ev.data)?.data;
        toastRef.current?.(`Rolled back to Checkpoint v${d?.version_number ?? ''}.`, 'info');
      } catch {
        toastRef.current?.('Workspace rolled back to checkpoint.', 'info');
      }
    });

    es.addEventListener('task_completed', () => {
      syncRef.current();
      toastRef.current?.('Task completed. Shared artifact ready for review and editing.', 'success');
    });

    es.addEventListener('task_failed', (ev: MessageEvent) => {
      syncRef.current();
      try {
        const d = JSON.parse(ev.data)?.data;
        toastRef.current?.(`Execution error: ${d?.error ?? 'Check activity log.'}`, 'error');
      } catch {
        toastRef.current?.('Execution encountered an error.', 'error');
      }
    });

    return () => {
      es.close();
      setConnected(false);
    };
  }, [taskId]);

  return { connected, liveProgress };
}
