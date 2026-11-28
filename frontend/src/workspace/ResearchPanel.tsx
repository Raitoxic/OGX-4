import React from 'react';
import { AlertCircle, CheckCircle2, Clock, Database, FileSearch } from 'lucide-react';
import type { TaskDetail } from '../types/hai';

interface ResearchPanelProps {
  task: TaskDetail;
}

const STATUS_TONE: Record<string, string> = {
  completed: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
  running: 'bg-blue-50 text-[#0071E3] dark:bg-blue-950/60 dark:text-[#2997FF]',
  pending: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  no_results: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  disabled: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  not_required: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
};

export const ResearchPanel: React.FC<ResearchPanelProps> = ({ task }) => {
  if (!task.research_enabled) {
    return (
      <div className="flex items-start gap-2 rounded-xl border border-apple-border bg-apple-surface px-3.5 py-2.5 text-[12px] text-apple-secondary">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-apple-tertiary" />
        <span>
          Research was not requested for this task. Output is generated without external sources; enable
          research at task creation to retrieve and cite academic material.
        </span>
      </div>
    );
  }

  const used = task.research_used ?? [];
  const additional = task.research_retrieved ?? [];
  const claims = task.artifact_sections.flatMap((s) => s.claims ?? []);
  const partial = claims.filter((c) => c.support === 'partial').length;
  const unverified = claims.filter((c) => c.support === 'unverified').length;
  const stale = claims.filter((c) => c.support === 'stale').length;
  const status = task.research_status;
  const tone = STATUS_TONE[status] ?? STATUS_TONE.disabled;
  const durationSec = task.research_duration_ms != null ? (task.research_duration_ms / 1000).toFixed(2) : null;

  return (
    <div className="space-y-2.5 rounded-xl border border-apple-border bg-apple-surface px-3.5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <FileSearch className="h-4 w-4 text-apple-blue" />
          <span className="text-[13px] font-semibold text-apple-ink">Research Activity</span>
          <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${tone}`}>{status}</span>
        </div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-apple-secondary">
          <span className="inline-flex items-center gap-1">
            <Database className="h-3 w-3" /> {used.length} used · {additional.length} additional
          </span>
          {durationSec && (
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" /> {durationSec}s retrieval
            </span>
          )}
        </div>
      </div>

      {status === 'no_results' && (
        <p className="text-[11.5px] text-amber-700 dark:text-amber-300">
          Research completed but no relevant sources were retrieved. The output below is not externally grounded.
        </p>
      )}
      {(status === 'disabled' || status === 'not_required') && (
        <p className="text-[11.5px] text-apple-secondary">
          Research did not run ({status}). No external references were used.
        </p>
      )}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <SummaryStat label="Sources used" value={used.length} tone="emerald" />
        <SummaryStat label="Additional retrieved" value={additional.length} tone="neutral" />
        <SummaryStat label="Partially supported" value={partial} tone="amber" />
        <SummaryStat label="Unverified claims" value={unverified} tone="red" />
      </div>

      {stale > 0 && (
        <p className="inline-flex items-center gap-1 text-[11px] font-medium text-amber-700 dark:text-amber-300">
          <AlertCircle className="h-3 w-3" /> {stale} claim(s) stale after human editing — not yet re-verified.
        </p>
      )}
      {status === 'completed' && used.length === 0 && additional.length === 0 && (
        <p className="inline-flex items-center gap-1 text-[11px] text-apple-secondary">
          <CheckCircle2 className="h-3 w-3" /> Research completed; no sources were available to cite.
        </p>
      )}
    </div>
  );
};

const SummaryStat: React.FC<{ label: string; value: number; tone: 'emerald' | 'neutral' | 'amber' | 'red' }> = ({
  label,
  value,
  tone,
}) => {
  const toneClass =
    tone === 'emerald'
      ? 'text-emerald-700 dark:text-emerald-300'
      : tone === 'amber'
        ? 'text-amber-700 dark:text-amber-300'
        : tone === 'red'
          ? 'text-red-600 dark:text-red-400'
          : 'text-apple-ink';
  return (
    <div className="rounded-lg bg-apple-elevated px-2.5 py-1.5">
      <p className={`text-[15px] font-semibold ${toneClass}`}>{value}</p>
      <p className="text-[10.5px] text-apple-secondary">{label}</p>
    </div>
  );
};