import React, { useEffect, useState } from 'react';
import { GitCompare, History, Plus, RotateCcw, X } from 'lucide-react';
import { api } from '../services/api';
import { StatusBadge } from '../components/StatusBadge';
import type { CheckpointComparison, CheckpointItem } from '../types/hai';

interface CheckpointDrawerProps {
  open: boolean;
  taskId: string;
  checkpoints: CheckpointItem[];
  onClose: () => void;
  onCreateCheckpoint: (label: string) => Promise<void>;
  onRollback: (checkpointId: string) => Promise<void>;
}

const TRIGGER_LABELS: Record<string, string> = {
  plan_created: 'Plan Created',
  step_completed: 'Step Completed',
  interrupt: 'Mid-Run Interrupt',
  pause: 'Paused',
  pre_replan: 'Before Replan',
  pre_rollback: 'Safety Snapshot',
  manual: 'Manual Save',
  completed: 'Completed',
};

export const CheckpointDrawer: React.FC<CheckpointDrawerProps> = ({
  open,
  taskId,
  checkpoints,
  onClose,
  onCreateCheckpoint,
  onRollback,
}) => {
  const [label, setLabel] = useState('');
  const [creating, setCreating] = useState(false);
  const [rollingBackId, setRollingBackId] = useState<string | null>(null);

  const [compareFrom, setCompareFrom] = useState('');
  const [compareTo, setCompareTo] = useState('');
  const [comparison, setComparison] = useState<CheckpointComparison | null>(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const handleManualSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return;
    setCreating(true);
    try {
      await onCreateCheckpoint(label.trim());
      setLabel('');
    } finally {
      setCreating(false);
    }
  };

  const handleRollback = async (cpId: string) => {
    setRollingBackId(cpId);
    try {
      await onRollback(cpId);
    } finally {
      setRollingBackId(null);
    }
  };

  const handleCompare = async () => {
    if (!compareFrom || !compareTo || compareFrom === compareTo) return;
    setComparing(true);
    try {
      const res = await api.compareCheckpoints(taskId, compareFrom, compareTo);
      setComparison(res);
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-[540px] flex-col border-l border-apple-border bg-apple-elevated shadow-apple-lg">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-apple-border px-5 py-4">
          <div className="flex items-center gap-2">
            <History className="h-4 w-4 text-apple-blue" />
            <div>
              <h2 className="text-[16px] font-semibold">Checkpoints & Rollback</h2>
              <p className="text-[11.5px] text-apple-secondary">
                Persisted in database across reloads and backend restarts.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 text-apple-secondary hover:bg-apple-surface hover:text-apple-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-5">
          {/* Save Manual Checkpoint */}
          <form onSubmit={handleManualSave} className="flex gap-2">
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Save manual checkpoint label..."
              className="flex-1 rounded-xl border border-apple-border bg-apple-bg px-3 py-1.5 text-[13px] outline-none focus:border-apple-blue"
            />
            <button
              type="submit"
              disabled={creating || !label.trim()}
              className="apple-pill-primary px-3.5 py-1.5 text-[12px] disabled:opacity-50"
            >
              <Plus className="h-3.5 w-3.5" /> Save
            </button>
          </form>

          {/* Compare Two Checkpoints */}
          {checkpoints.length >= 2 && (
            <div className="rounded-2xl border border-apple-border bg-apple-surface p-3.5">
              <p className="flex items-center gap-1.5 text-[12px] font-semibold">
                <GitCompare className="h-3.5 w-3.5 text-apple-blue" /> Compare Execution Versions
              </p>
              <div className="mt-2.5 flex flex-wrap items-center gap-2">
                <select
                  value={compareFrom}
                  onChange={(e) => setCompareFrom(e.target.value)}
                  className="flex-1 rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[12px]"
                >
                  <option value="">From checkpoint...</option>
                  {checkpoints.map((cp) => (
                    <option key={cp.id} value={cp.id}>
                      v{cp.version_number} — {cp.label.slice(0, 32)}
                    </option>
                  ))}
                </select>
                <select
                  value={compareTo}
                  onChange={(e) => setCompareTo(e.target.value)}
                  className="flex-1 rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[12px]"
                >
                  <option value="">To checkpoint...</option>
                  {checkpoints.map((cp) => (
                    <option key={cp.id} value={cp.id}>
                      v{cp.version_number} — {cp.label.slice(0, 32)}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!compareFrom || !compareTo || compareFrom === compareTo || comparing}
                  onClick={handleCompare}
                  className="rounded-full bg-apple-ink px-3.5 py-1.5 text-[12px] font-medium text-apple-bg disabled:opacity-40"
                >
                  {comparing ? 'Diffing...' : 'Compare'}
                </button>
              </div>

              {comparison && (
                <div className="mt-3 space-y-2 border-t border-apple-border pt-3 text-[12px]">
                  <p className="font-semibold">
                    Step Differences ({comparison.step_diffs.length}):
                  </p>
                  {comparison.step_diffs.length === 0 ? (
                    <p className="text-apple-secondary">No step changes between selected checkpoints.</p>
                  ) : (
                    <ul className="space-y-1">
                      {comparison.step_diffs.map((d) => (
                        <li key={d.step_order} className="rounded-lg bg-apple-elevated px-2.5 py-1.5">
                          <strong>Step {d.step_order} ({d.title}):</strong> {d.changes.join(', ')}
                        </li>
                      ))}
                    </ul>
                  )}
                  {comparison.artifact_unified_diff.length > 0 && (
                    <div className="mt-2 max-h-44 overflow-y-auto rounded-lg bg-apple-elevated p-2 font-mono text-[11px]">
                      {comparison.artifact_unified_diff.map((line, i) => (
                        <div
                          key={i}
                          className={
                            line.startsWith('+')
                              ? 'text-emerald-700 dark:text-emerald-300'
                              : line.startsWith('-')
                                ? 'text-red-600 dark:text-red-400'
                                : 'text-apple-secondary'
                          }
                        >
                          {line}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Checkpoint Timeline List */}
          <div className="space-y-2.5">
            {checkpoints.map((cp) => (
              <div
                key={cp.id}
                className="rounded-2xl border border-apple-border bg-apple-bg p-3.5 transition hover:border-apple-blue/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="rounded-full bg-apple-surface px-2 py-0.5 font-mono text-[11px] font-semibold">
                        v{cp.version_number}
                      </span>
                      <span className="text-[13.5px] font-semibold">{cp.label}</span>
                    </div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11.5px] text-apple-secondary">
                      <StatusBadge status={cp.task_status} />
                      <span>{TRIGGER_LABELS[cp.trigger_type] || cp.trigger_type}</span>
                      <span>·</span>
                      <span>
                        {cp.completed_steps_count}/{cp.total_steps_count} steps done
                      </span>
                      {cp.created_at && (
                        <>
                          <span>·</span>
                          <span>{new Date(cp.created_at).toLocaleTimeString()}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <button
                    type="button"
                    disabled={rollingBackId !== null}
                    onClick={() => handleRollback(cp.id)}
                    className="inline-flex shrink-0 items-center gap-1 rounded-full border border-purple-500/30 bg-purple-50/70 px-3 py-1 text-[11.5px] font-medium text-purple-700 transition hover:bg-purple-100 disabled:opacity-40 dark:bg-purple-950/40 dark:text-purple-300"
                  >
                    <RotateCcw className="h-3 w-3" />
                    <span>{rollingBackId === cp.id ? 'Restoring...' : 'Restore'}</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
