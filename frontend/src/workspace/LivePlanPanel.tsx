import React from 'react';
import { AlertCircle, MessageSquare, Sparkles } from 'lucide-react';
import { StepCard } from './StepCard';
import type { TaskDetail } from '../types/hai';

interface LivePlanPanelProps {
  task: TaskDetail;
  highlightedStepId: string | null;
  onEditStep: (
    stepId: string,
    payload: { title?: string; description?: string; expected_outcome?: string; edit_note?: string },
  ) => Promise<void>;
  onToggleLock: (stepId: string, locked: boolean) => Promise<void>;
  onApproveStep: (stepId: string) => Promise<void>;
  onRejectStep: (stepId: string, reason: string, generateAlt: boolean) => Promise<void>;
  onSelectProvenance: (stepId: string) => void;
}

export const LivePlanPanel: React.FC<LivePlanPanelProps> = ({
  task,
  highlightedStepId,
  onEditStep,
  onToggleLock,
  onApproveStep,
  onRejectStep,
  onSelectProvenance,
}) => {
  const sectionStepIds = new Set(task.artifact_sections.map((s) => s.step_id).filter(Boolean));
  const awaitingStep = task.steps.find((s) => s.status === 'AWAITING_APPROVAL');

  return (
    <div className="flex h-full flex-col rounded-xl border border-apple-border bg-apple-surface/70 p-3.5">
      <div className="mb-3 flex items-center justify-between border-b border-apple-border pb-2.5">
        <div>
          <p className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-apple-tertiary">
            Execution Plan
          </p>
          <h2 className="text-[15px] font-semibold tracking-tight text-apple-ink">Live Agent Steps</h2>
        </div>
        <span className="rounded-md border border-apple-border bg-apple-elevated px-2 py-0.5 font-mono text-[11px] font-medium text-apple-secondary">
          {task.steps.length} steps
        </span>
      </div>

      {/* Original User Task Card */}
      <div className="mb-3 rounded-2xl border border-apple-border bg-apple-elevated p-3.5">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-apple-secondary">
          <Sparkles className="h-3 w-3 text-apple-blue" /> Original Task Instruction
        </div>
        <p className="mt-1.5 text-[13px] leading-relaxed text-apple-ink">{task.prompt}</p>

        {/* Active Mid-Execution User Instructions */}
        {task.additional_instructions.length > 0 && (
          <div className="mt-3 space-y-1.5 border-t border-apple-border pt-2.5">
            <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-apple-blue">
              <MessageSquare className="h-3 w-3" /> Added Mid-Execution Directives ({task.additional_instructions.length})
            </p>
            {task.additional_instructions.map((item) => (
              <div
                key={item.id}
                className="rounded-xl bg-blue-50/60 px-2.5 py-1.5 text-[12px] text-apple-ink dark:bg-blue-950/30"
              >
                {item.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Failure Recovery Callout */}
      {task.status === 'FAILED' && (
        <div className="mb-3 flex items-start gap-2.5 rounded-2xl border border-red-500/35 bg-red-50/70 p-3 text-[12.5px] text-red-800 dark:bg-red-950/35 dark:text-red-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">Execution Halted — Recovery Ready</p>
            <p className="mt-0.5 text-[12px] opacity-90">
              {task.error_message || 'An error occurred during step execution.'} Edit the failed
              step, roll back to a saved checkpoint, or click Resume to retry without losing completed steps.
            </p>
          </div>
        </div>
      )}

      {/* Pending Approval Callout */}
      {task.status === 'AWAITING_APPROVAL' && (
        <div className="mb-3 flex items-start gap-2.5 rounded-2xl border border-amber-500/35 bg-amber-50/70 p-3 text-[12.5px] text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">
              {awaitingStep
                ? `Human Approval Needed — Step ${awaitingStep.step_order}: ${awaitingStep.title}`
                : 'Execution Plan Ready for Your Review'}
            </p>
            <p className="mt-0.5 text-[12px] opacity-90">
              {awaitingStep
                ? awaitingStep.approval_reason || 'Review rationale and risk level before authorizing.'
                : 'Inspect, edit, or lock any step below, then click Approve Plan or Start Task.'}
            </p>
          </div>
        </div>
      )}

      {/* Ordered Step List */}
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {task.steps.map((step) => (
          <StepCard
            key={step.id}
            step={step}
            highlighted={highlightedStepId === step.id}
            hasArtifactSection={sectionStepIds.has(step.id)}
            onEdit={onEditStep}
            onToggleLock={onToggleLock}
            onApprove={onApproveStep}
            onReject={onRejectStep}
            onSelectProvenance={onSelectProvenance}
          />
        ))}
      </div>
    </div>
  );
};
