import React, { useState } from 'react';
import {
  Activity,
  CheckCircle2,
  GitBranch,
  History,
  MessageSquarePlus,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Sliders,
  Square,
  XCircle,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import type { AutonomyMode, TaskDetail } from '../types/hai';

interface ExecutionControlBarProps {
  task: TaskDetail;
  sseConnected: boolean;
  liveActivity?: string;
  isInterruptibleLive?: boolean;
  busyAction: string | null;
  onStart: () => Promise<void>;
  onPause: () => Promise<void>;
  onInterrupt: () => Promise<void>;
  onResume: () => Promise<void>;
  onApprove: () => Promise<void>;
  onRejectAwaiting: (reason: string) => Promise<void>;
  onAddInstruction: (text: string) => Promise<void>;
  onReplan: (reason: string) => Promise<void>;
  onUpdateAutonomy: (mode: AutonomyMode, adaptive: boolean) => Promise<void>;
  onOpenCheckpoints: () => void;
  onOpenActivity: () => void;
}

export const ExecutionControlBar: React.FC<ExecutionControlBarProps> = ({
  task,
  sseConnected,
  liveActivity,
  isInterruptibleLive,
  busyAction,
  onStart,
  onPause,
  onInterrupt,
  onResume,
  onApprove,
  onRejectAwaiting,
  onAddInstruction,
  onReplan,
  onUpdateAutonomy,
  onOpenCheckpoints,
  onOpenActivity,
}) => {
  const [showInstructionBox, setShowInstructionBox] = useState(false);
  const [instructionText, setInstructionText] = useState('');

  const [showReplanBox, setShowReplanBox] = useState(false);
  const [replanReason, setReplanReason] = useState('');

  const [showRejectBox, setShowRejectBox] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const isRunning = task.status === 'RUNNING' || task.status === 'RESUMING';
  const isCompleted = task.status === 'COMPLETED';
  const isAwaiting = task.status === 'AWAITING_APPROVAL';
  const canResume =
    task.status === 'INTERRUPTED' ||
    task.status === 'PAUSED' ||
    task.status === 'ROLLED_BACK' ||
    task.status === 'FAILED';
  const awaitingStep = task.steps.find((s) => s.status === 'AWAITING_APPROVAL');
  const activeStep =
    task.steps.find((s) => s.status === 'RUNNING') ||
    awaitingStep ||
    task.steps.find((s) => s.status === 'INTERRUPTED' || s.status === 'PAUSED' || s.status === 'FAILED') ||
    task.steps.find((s) => s.status === 'PENDING');
  const recentEvents = task.recent_events.slice(0, 2);
  const interruptible = isInterruptibleLive ?? task.is_interruptible;

  const handleSubmitInstruction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!instructionText.trim()) return;
    await onAddInstruction(instructionText.trim());
    setInstructionText('');
    setShowInstructionBox(false);
  };

  const handleSubmitReplan = async (e: React.FormEvent) => {
    e.preventDefault();
    await onReplan(replanReason.trim());
    setReplanReason('');
    setShowReplanBox(false);
  };

  const handleSubmitReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rejectReason.trim()) return;
    await onRejectAwaiting(rejectReason.trim());
    setRejectReason('');
    setShowRejectBox(false);
  };

  const cautionLabel =
    task.adaptive_caution_level === 'elevated_caution'
      ? 'Elevated Caution'
      : task.adaptive_caution_level === 'relaxed'
        ? 'Streamlined'
        : 'Calibrated';

  return (
    <div className="rounded-xl border border-apple-border bg-apple-elevated px-4 py-3 shadow-apple-sm">
      {/* Row 1: Status, Progress, Autonomy Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2.5">
          <StatusBadge status={task.status} size="md" />
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
              sseConnected
                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
                : 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400'
            }`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${sseConnected ? 'bg-emerald-500' : 'bg-neutral-400'}`} />
            {sseConnected ? 'SSE Live' : 'Syncing'}
          </span>
          <span className="text-[12.5px] font-medium text-apple-secondary">
            {task.completed_steps_count} / {task.total_steps_count} steps ({task.progress_percent}%)
          </span>
          {activeStep && (
            <span className="hidden items-center gap-1 rounded-full border border-apple-border bg-apple-surface px-2.5 py-0.5 text-[11px] font-medium text-apple-ink md:inline-flex">
              <span className="text-apple-secondary">Active:</span>
              <span className="max-w-[200px] truncate">
                Step {activeStep.step_order} · {activeStep.title}
              </span>
            </span>
          )}
          {!interruptible && isRunning && (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
              <ShieldAlert className="h-3 w-3" /> Atomic commit in progress
            </span>
          )}
        </div>

        {/* Manual Autonomy Mode Override + Adaptive Toggle */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-surface px-2.5 py-1 text-[11.5px]">
            <Sliders className="h-3 w-3 text-apple-blue" />
            <select
              aria-label="Autonomy Mode"
              value={task.autonomy_mode}
              onChange={(e) => onUpdateAutonomy(e.target.value as AutonomyMode, task.adaptive_enabled)}
              className="bg-transparent font-medium text-apple-ink outline-none"
            >
              <option value="supervised">Supervised Mode</option>
              <option value="balanced">Balanced Mode</option>
              <option value="higher_autonomy">Higher Autonomy</option>
            </select>
          </div>
          {task.ml_recommended_autonomy && (
            <div className="flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-50/70 px-2.5 py-1 text-[11px] font-medium text-indigo-800 dark:bg-indigo-950/40 dark:text-indigo-200" title={task.ml_recommendation_reason || 'Advisory ML recommendation (synthetic demo model)'}>
              <span>
                ML Advisor: <strong className="capitalize">{task.ml_recommended_autonomy.replace('_', ' ')}</strong>
                {typeof task.ml_recommendation_confidence === 'number' && ` (${Math.round(task.ml_recommendation_confidence * 100)}%)`}
              </span>
              {task.ml_recommended_autonomy !== task.autonomy_mode && (
                <button
                  type="button"
                  onClick={() => onUpdateAutonomy(task.ml_recommended_autonomy!, task.adaptive_enabled)}
                  className="ml-1 rounded-full bg-indigo-600 px-2 py-0.5 text-[10px] font-semibold text-white hover:bg-indigo-700"
                >
                  Apply
                </button>
              )}
            </div>
          )}
          <button
            type="button"
            onClick={() => onUpdateAutonomy(task.autonomy_mode, !task.adaptive_enabled)}
            title={task.adaptive_reason || 'Toggle adaptive autonomy'}
            className={`rounded-full border px-2.5 py-1 text-[11px] font-medium transition ${
              task.adaptive_enabled
                ? task.adaptive_caution_level === 'elevated_caution'
                  ? 'border-amber-500/35 bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-300'
                  : 'border-apple-blue/30 bg-blue-50/70 text-apple-blue dark:bg-blue-950/40'
                : 'border-apple-border bg-apple-surface text-apple-secondary'
            }`}
          >
            Adaptive: {task.adaptive_enabled ? cautionLabel : 'Manual Lock'}
          </button>
        </div>
      </div>

      {/* Progress bar & Live Activity Text */}
      <div className="mt-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-apple-surface">
          <div
            className="h-full rounded-full bg-apple-blue transition-all duration-300"
            style={{ width: `${Math.max(task.progress_percent, isRunning ? 8 : 0)}%` }}
          />
        </div>
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-[12.5px]">
          <p className="min-w-0 flex-1 truncate text-apple-ink">
            <span className="font-medium text-apple-secondary">Activity: </span>
            {liveActivity || task.current_activity}
          </p>
          {task.adaptive_enabled && task.adaptive_reason && (
            <span className="hidden text-[11.5px] text-apple-secondary xl:inline">
              Policy: {task.adaptive_reason}
            </span>
          )}
        </div>
        {recentEvents.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-apple-secondary">
            <span className="font-semibold uppercase tracking-wider text-apple-tertiary">Recent:</span>
            {recentEvents.map((ev) => (
              <button
                key={ev.id}
                type="button"
                onClick={onOpenActivity}
                className="inline-flex max-w-[340px] items-center gap-1.5 truncate rounded-full bg-apple-surface px-2.5 py-0.5 text-left transition hover:text-apple-ink"
                title={ev.summary}
              >
                <span className="font-mono text-[10px] text-apple-blue">{ev.event_type}</span>
                <span className="truncate">{ev.summary}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Row 2: Dedicated Action Controls (Every single button wired to real backend APIs) */}
      <div className="mt-3.5 flex flex-wrap items-center gap-2 border-t border-apple-border pt-3.5">
        {/* Start Task */}
        {!isRunning && !isCompleted && !canResume && (
          <button
            type="button"
            disabled={busyAction !== null}
            onClick={onStart}
            className="apple-pill-primary px-3.5 py-1.5 text-[12.5px] disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>{busyAction === 'start' ? 'Starting...' : 'Start Task'}</span>
          </button>
        )}

        {/* Resume */}
        {canResume && (
          <button
            type="button"
            disabled={busyAction !== null}
            onClick={onResume}
            className="apple-pill-primary px-3.5 py-1.5 text-[12.5px] disabled:opacity-50"
          >
            <Play className="h-3.5 w-3.5 fill-current" />
            <span>{busyAction === 'resume' ? 'Resuming...' : 'Resume'}</span>
          </button>
        )}

        {/* Pause */}
        <button
          type="button"
          disabled={!isRunning || busyAction !== null}
          onClick={onPause}
          className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-bg px-3.5 py-1.5 text-[12.5px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Pause className="h-3.5 w-3.5" />
          <span>{busyAction === 'pause' ? 'Pausing...' : 'Pause'}</span>
        </button>

        {/* Genuine Mid-Execution Interrupt */}
        <button
          type="button"
          disabled={(!isRunning && !isAwaiting) || busyAction !== null}
          onClick={onInterrupt}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-[12.5px] font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
            isRunning
              ? 'border-orange-500/40 bg-orange-500 text-white hover:bg-orange-600'
              : 'border-orange-500/30 bg-orange-50 text-orange-800 hover:bg-orange-100 dark:bg-orange-950/40 dark:text-orange-300'
          }`}
        >
          <Square className="h-3 w-3 fill-current" />
          <span>{busyAction === 'interrupt' ? 'Interrupting...' : 'Interrupt'}</span>
        </button>

        {/* Approve */}
        <button
          type="button"
          disabled={!isAwaiting || busyAction !== null}
          onClick={onApprove}
          className={`inline-flex items-center gap-1.5 rounded-full border px-3.5 py-1.5 text-[12.5px] font-medium transition disabled:cursor-not-allowed disabled:opacity-40 ${
            isAwaiting
              ? 'border-emerald-600 bg-emerald-600 text-white hover:bg-emerald-700'
              : 'border-apple-border bg-apple-bg text-apple-ink'
          }`}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>{awaitingStep ? `Approve Step ${awaitingStep.step_order}` : 'Approve Plan'}</span>
        </button>

        {/* Reject (for awaiting step) */}
        <button
          type="button"
          disabled={!awaitingStep || busyAction !== null}
          onClick={() => {
            setShowRejectBox((v) => !v);
            setShowInstructionBox(false);
            setShowReplanBox(false);
          }}
          className="inline-flex items-center gap-1.5 rounded-full border border-red-500/30 bg-red-50/70 px-3.5 py-1.5 text-[12.5px] font-medium text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-40 dark:bg-red-950/30 dark:text-red-300"
        >
          <XCircle className="h-3.5 w-3.5" />
          <span>Reject</span>
        </button>

        {/* Add Instructions (works mid-flight OR paused!) */}
        <button
          type="button"
          disabled={isCompleted || busyAction !== null}
          onClick={() => {
            setShowInstructionBox((v) => !v);
            setShowReplanBox(false);
            setShowRejectBox(false);
          }}
          className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-bg px-3.5 py-1.5 text-[12.5px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:cursor-not-allowed disabled:opacity-40"
        >
          <MessageSquarePlus className="h-3.5 w-3.5 text-apple-blue" />
          <span>Add Instructions</span>
        </button>

        {/* Replan */}
        <button
          type="button"
          disabled={isRunning || isCompleted || busyAction !== null}
          onClick={() => {
            setShowReplanBox((v) => !v);
            setShowInstructionBox(false);
            setShowRejectBox(false);
          }}
          className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-bg px-3.5 py-1.5 text-[12.5px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:cursor-not-allowed disabled:opacity-40"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Replan</span>
        </button>

        {/* Rollback / Checkpoints Drawer */}
        <button
          type="button"
          onClick={onOpenCheckpoints}
          className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-bg px-3.5 py-1.5 text-[12.5px] font-medium text-apple-ink transition hover:bg-apple-surface"
        >
          <RotateCcw className="h-3.5 w-3.5 text-purple-600 dark:text-purple-400" />
          <span>Rollback ({task.checkpoints.length})</span>
        </button>

        {/* Activity Stream Drawer */}
        <button
          type="button"
          onClick={onOpenActivity}
          className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-surface px-3 py-1.5 text-[12px] font-medium text-apple-secondary transition hover:text-apple-ink"
        >
          <Activity className="h-3.5 w-3.5" />
          <span>Events ({task.recent_events.length})</span>
        </button>
      </div>

      {/* Inline Add Instructions Drawer */}
      {showInstructionBox && (
        <form onSubmit={handleSubmitInstruction} className="mt-3 flex flex-wrap gap-2 rounded-2xl bg-apple-surface p-3">
          <input
            type="text"
            value={instructionText}
            onChange={(e) => setInstructionText(e.target.value)}
            placeholder="Inject guidance for remaining steps (even while running)..."
            className="min-w-[220px] flex-1 rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[13px] outline-none focus:border-apple-blue"
            autoFocus
          />
          <button type="submit" className="apple-pill-primary px-4 py-1.5 text-[12.5px]">
            Inject Instruction
          </button>
          <button
            type="button"
            onClick={() => setShowInstructionBox(false)}
            className="rounded-full px-3 py-1.5 text-[12.5px] text-apple-secondary hover:text-apple-ink"
          >
            Cancel
          </button>
        </form>
      )}

      {/* Inline Replan Drawer */}
      {showReplanBox && (
        <form onSubmit={handleSubmitReplan} className="mt-3 flex flex-wrap gap-2 rounded-2xl bg-apple-surface p-3">
          <div className="flex w-full items-center gap-1.5 text-[11.5px] text-apple-secondary">
            <GitBranch className="h-3.5 w-3.5 text-apple-blue" />
            <span>Replan updates unlocked pending steps only. Completed and locked steps stay strictly protected.</span>
          </div>
          <input
            type="text"
            value={replanReason}
            onChange={(e) => setReplanReason(e.target.value)}
            placeholder="Describe changed requirements (e.g., focus on multi-region failover and cost bounds)..."
            className="min-w-[220px] flex-1 rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[13px] outline-none focus:border-apple-blue"
            autoFocus
          />
          <button type="submit" className="apple-pill-primary px-4 py-1.5 text-[12.5px]">
            Generate Updated Plan
          </button>
          <button
            type="button"
            onClick={() => setShowReplanBox(false)}
            className="rounded-full px-3 py-1.5 text-[12.5px] text-apple-secondary hover:text-apple-ink"
          >
            Cancel
          </button>
        </form>
      )}

      {/* Inline Reject Awaiting Step Drawer */}
      {showRejectBox && awaitingStep && (
        <form onSubmit={handleSubmitReject} className="mt-3 flex flex-wrap gap-2 rounded-2xl border border-red-500/20 bg-red-50/50 p-3 dark:bg-red-950/20">
          <input
            type="text"
            required
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder={`Why reject Step ${awaitingStep.step_order}? Agent will propose an alternative...`}
            className="min-w-[220px] flex-1 rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[13px] outline-none focus:border-red-500"
            autoFocus
          />
          <button
            type="submit"
            className="rounded-full bg-red-600 px-4 py-1.5 text-[12.5px] font-medium text-white hover:bg-red-700"
          >
            Reject & Propose Alternative
          </button>
          <button
            type="button"
            onClick={() => setShowRejectBox(false)}
            className="rounded-full px-3 py-1.5 text-[12.5px] text-apple-secondary hover:text-apple-ink"
          >
            Cancel
          </button>
        </form>
      )}
    </div>
  );
};
