import React, { useEffect, useState } from 'react';
import {
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronUp,
  Edit3,
  FileText,
  Info,
  Lock,
  Unlock,
  X,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import type { ExecutionStep } from '../types/hai';

interface StepCardProps {
  step: ExecutionStep;
  highlighted: boolean;
  hasArtifactSection: boolean;
  onEdit: (
    stepId: string,
    payload: { title?: string; description?: string; expected_outcome?: string; edit_note?: string },
  ) => Promise<void>;
  onToggleLock: (stepId: string, locked: boolean) => Promise<void>;
  onApprove: (stepId: string) => Promise<void>;
  onReject: (stepId: string, reason: string, generateAlt: boolean) => Promise<void>;
  onSelectProvenance: (stepId: string) => void;
}

const RISK_STYLE: Record<string, string> = {
  low: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
  medium: 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300',
  high: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
};

export const StepCard: React.FC<StepCardProps> = ({
  step,
  highlighted,
  hasArtifactSection,
  onEdit,
  onToggleLock,
  onApprove,
  onReject,
  onSelectProvenance,
}) => {
  const [expanded, setExpanded] = useState(
    step.status === 'RUNNING' || step.status === 'AWAITING_APPROVAL' || step.status === 'INTERRUPTED' || step.status === 'FAILED',
  );

  useEffect(() => {
    if (step.status === 'AWAITING_APPROVAL' || step.status === 'INTERRUPTED' || step.status === 'FAILED') {
      setExpanded(true);
    }
  }, [step.status]);
  const [editing, setEditing] = useState(false);
  const [titleDraft, setTitleDraft] = useState(step.title);
  const [descDraft, setDescDraft] = useState(step.description);
  const [outcomeDraft, setOutcomeDraft] = useState(step.expected_outcome);
  const [saving, setSaving] = useState(false);

  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const isCompleted = step.status === 'COMPLETED';
  const isRunning = step.status === 'RUNNING';
  const canEdit = !isCompleted && !isRunning && !step.is_locked;
  const canApprove = !isCompleted && !isRunning && !step.approved_by_user;
  const canReject = !isCompleted && !isRunning;

  const openEdit = () => {
    setTitleDraft(step.title);
    setDescDraft(step.description);
    setOutcomeDraft(step.expected_outcome);
    setEditing(true);
    setExpanded(true);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onEdit(step.id, {
        title: titleDraft,
        description: descDraft,
        expected_outcome: outcomeDraft,
      });
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  const handleSubmitReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectReason.trim()) return;
    setSaving(true);
    try {
      await onReject(step.id, rejectReason.trim(), true);
      setRejectReason('');
      setRejecting(false);
    } finally {
      setSaving(false);
    }
  };

  const statusAccentBar =
    step.status === 'RUNNING'
      ? 'border-l-[3px] border-l-apple-blue border-apple-blue/40 bg-apple-blue/[0.04]'
      : step.status === 'AWAITING_APPROVAL'
        ? 'border-l-[3px] border-l-amber-500 border-amber-500/40 bg-amber-500/[0.05]'
        : step.status === 'INTERRUPTED'
          ? 'border-l-[3px] border-l-orange-500 border-orange-500/40 bg-orange-500/[0.05]'
          : step.status === 'FAILED' || step.status === 'REJECTED'
            ? 'border-l-[3px] border-l-red-500 border-red-500/40 bg-red-500/[0.04]'
            : step.status === 'COMPLETED'
              ? 'border-l-[3px] border-l-emerald-500/75 border-apple-border bg-apple-elevated'
              : 'border-apple-border bg-apple-elevated';

  return (
    <div
      id={`step-card-${step.id}`}
      className={`rounded-lg border p-3.5 transition-colors ${
        highlighted
          ? 'border-apple-blue ring-2 ring-apple-blue/25 bg-apple-blue/[0.06]'
          : statusAccentBar
      }`}
    >
      {/* Top Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-apple-surface text-[11px] font-semibold text-apple-secondary">
              {step.step_order}
            </span>
            <h3 className="text-[14px] font-semibold leading-snug text-apple-ink">{step.title}</h3>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <StatusBadge status={step.status} />
            <span className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium capitalize ${RISK_STYLE[step.risk_level] || RISK_STYLE.low}`}>
              {step.risk_level} risk
            </span>
            {step.is_locked && (
              <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10.5px] font-medium text-apple-blue dark:bg-blue-950/50">
                <Lock className="h-2.5 w-2.5" /> Locked
              </span>
            )}
            {step.user_modified && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[10.5px] font-medium text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300">
                Edited (v{step.revision_number})
              </span>
            )}
            {step.duration_ms > 0 && (
              <span className="text-[11px] text-apple-secondary">
                {(step.duration_ms / 1000).toFixed(1)}s
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="rounded-lg p-1 text-apple-secondary transition hover:bg-apple-surface hover:text-apple-ink"
          aria-label={expanded ? 'Collapse step details' : 'Expand step details'}
        >
          {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Compact Description */}
      {!editing && (
        <p className="mt-2.5 text-[13px] leading-relaxed text-apple-secondary">{step.description}</p>
      )}

      {/* Action Buttons Row */}
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {canApprove && (
          <button
            type="button"
            onClick={() => onApprove(step.id)}
            className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11.5px] font-medium transition ${
              step.status === 'AWAITING_APPROVAL'
                ? 'bg-emerald-600 text-white hover:bg-emerald-700'
                : 'border border-emerald-500/30 bg-emerald-50/70 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-300'
            }`}
          >
            <Check className="h-3 w-3" /> Approve
          </button>
        )}

        {canReject && (
          <button
            type="button"
            onClick={() => setRejecting((v) => !v)}
            className="inline-flex items-center gap-1 rounded-full border border-red-500/25 px-2.5 py-1 text-[11.5px] font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/30"
          >
            <X className="h-3 w-3" /> Reject
          </button>
        )}

        <button
          type="button"
          disabled={!canEdit}
          onClick={openEdit}
          title={
            step.is_locked
              ? 'Unlock step first to edit'
              : isCompleted
                ? 'Roll back to an earlier checkpoint to re-edit completed steps'
                : 'Edit step instructions'
          }
          className="inline-flex items-center gap-1 rounded-full border border-apple-border px-2.5 py-1 text-[11.5px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Edit3 className="h-3 w-3" /> Edit
        </button>

        <button
          type="button"
          onClick={() => onToggleLock(step.id, !step.is_locked)}
          className="inline-flex items-center gap-1 rounded-full border border-apple-border px-2.5 py-1 text-[11.5px] font-medium text-apple-ink transition hover:bg-apple-surface"
        >
          {step.is_locked ? (
            <>
              <Unlock className="h-3 w-3 text-apple-blue" /> Unlock
            </>
          ) : (
            <>
              <Lock className="h-3 w-3" /> Lock
            </>
          )}
        </button>

        {hasArtifactSection && (
          <button
            type="button"
            onClick={() => onSelectProvenance(step.id)}
            className="ml-auto inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11.5px] font-medium text-apple-blue hover:bg-blue-50/70 dark:hover:bg-blue-950/40"
          >
            <FileText className="h-3 w-3" /> View Output
          </button>
        )}
      </div>

      {/* Inline Rejection Form */}
      {rejecting && (
        <form onSubmit={handleSubmitReject} className="mt-3 space-y-2 rounded-xl border border-red-500/25 bg-red-50/50 p-3 dark:bg-red-950/20">
          <label className="block text-[11.5px] font-medium text-red-700 dark:text-red-300">
            Rejection Feedback (VYRO-X will propose an alternative step)
          </label>
          <input
            type="text"
            required
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g., Focus on reliability trade-offs instead of general history..."
            className="w-full rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[12.5px] outline-none focus:border-red-500"
          />
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={saving}
              className="rounded-full bg-red-600 px-3 py-1 text-[11.5px] font-medium text-white hover:bg-red-700"
            >
              {saving ? 'Generating Alternative...' : 'Reject & Propose Alternative'}
            </button>
            <button
              type="button"
              onClick={() => setRejecting(false)}
              className="rounded-full px-2.5 py-1 text-[11.5px] text-apple-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Inline Edit Form */}
      {editing && (
        <form onSubmit={handleSaveEdit} className="mt-3 space-y-2.5 rounded-xl border border-apple-blue/30 bg-apple-surface p-3">
          <div>
            <label className="mb-1 block text-[11px] font-medium text-apple-secondary">Step Title</label>
            <input
              type="text"
              required
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              className="w-full rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[13px] outline-none focus:border-apple-blue"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-apple-secondary">
              Execution Instructions
            </label>
            <textarea
              required
              rows={3}
              value={descDraft}
              onChange={(e) => setDescDraft(e.target.value)}
              className="w-full rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[12.5px] outline-none focus:border-apple-blue"
            />
          </div>
          <div>
            <label className="mb-1 block text-[11px] font-medium text-apple-secondary">
              Expected Outcome
            </label>
            <input
              type="text"
              value={outcomeDraft}
              onChange={(e) => setOutcomeDraft(e.target.value)}
              className="w-full rounded-lg border border-apple-border bg-apple-elevated px-2.5 py-1.5 text-[12.5px] outline-none focus:border-apple-blue"
            />
          </div>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={saving}
              className="apple-pill-primary px-3.5 py-1 text-[12px]"
            >
              {saving ? 'Saving...' : 'Save Instructions'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="rounded-full px-3 py-1 text-[12px] text-apple-secondary hover:text-apple-ink"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Expanded Transparency Details */}
      {expanded && !editing && (
        <div className="mt-3.5 space-y-2.5 border-t border-apple-border pt-3 text-[12px]">
          <div>
            <span className="font-semibold text-apple-ink">Rationale: </span>
            <span className="text-apple-secondary">{step.rationale}</span>
          </div>
          <div>
            <span className="font-semibold text-apple-ink">Expected Outcome: </span>
            <span className="text-apple-secondary">{step.expected_outcome}</span>
          </div>
          {step.approval_reason && (
            <div className="flex items-start gap-1.5 rounded-lg bg-apple-surface px-2.5 py-1.5 text-[11.5px]">
              <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-apple-blue" />
              <span className="text-apple-secondary">
                <strong className="text-apple-ink">Autonomy Gate: </strong>
                {step.approval_reason}
              </span>
            </div>
          )}
          {step.confidence_basis && (
            <div>
              <span className="font-semibold text-apple-ink">Evidence / Grounding Basis: </span>
              <span className="text-apple-secondary">{step.confidence_basis}</span>
            </div>
          )}
          {step.uncertainty_notes && (
            <div className="flex items-start gap-1.5 text-amber-800 dark:text-amber-300">
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
              <span>
                <strong>Uncertainty: </strong>
                {step.uncertainty_notes}
              </span>
            </div>
          )}
          {step.sources && step.sources.length > 0 && (
            <div>
              <p className="font-semibold text-apple-ink">Referenced Sources:</p>
              <ul className="mt-1 space-y-1 pl-3">
                {step.sources.map((src, i) => (
                  <li key={`${src.title}-${i}`} className="list-disc text-[11.5px] text-apple-secondary">
                    <span className="font-medium text-apple-ink">{src.title}</span> — {src.reliability_note}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {step.partial_output && step.status !== 'COMPLETED' && (
            <div className="rounded-lg border border-orange-500/25 bg-orange-50/40 p-2.5 text-[11.5px] dark:bg-orange-950/20">
              <p className="font-semibold text-orange-800 dark:text-orange-300">Preserved Partial Progress:</p>
              <p className="mt-1 whitespace-pre-wrap text-apple-secondary">{step.partial_output}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
