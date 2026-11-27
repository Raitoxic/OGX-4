import React from 'react';

const STATUS_STYLES: Record<string, { label: string; dot: string; pill: string; pulse?: boolean }> = {
  CREATED: {
    label: 'Created',
    dot: 'bg-neutral-400',
    pill: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
  PENDING: {
    label: 'Pending',
    dot: 'bg-neutral-400',
    pill: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
  PLANNING: {
    label: 'Planning',
    dot: 'bg-indigo-500',
    pill: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300',
    pulse: true,
  },
  RUNNING: {
    label: 'Running',
    dot: 'bg-[#0071E3] dark:bg-[#2997FF]',
    pill: 'bg-blue-50 text-[#0071E3] dark:bg-blue-950/60 dark:text-[#2997FF]',
    pulse: true,
  },
  RESUMING: {
    label: 'Resuming',
    dot: 'bg-[#0071E3] dark:bg-[#2997FF]',
    pill: 'bg-blue-50 text-[#0071E3] dark:bg-blue-950/60 dark:text-[#2997FF]',
    pulse: true,
  },
  AWAITING_APPROVAL: {
    label: 'Awaiting Approval',
    dot: 'bg-amber-500',
    pill: 'bg-amber-50 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300',
  },
  PAUSED: {
    label: 'Paused',
    dot: 'bg-neutral-500',
    pill: 'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
  },
  INTERRUPTED: {
    label: 'Interrupted',
    dot: 'bg-orange-500',
    pill: 'bg-orange-50 text-orange-800 dark:bg-orange-950/60 dark:text-orange-300',
  },
  ROLLED_BACK: {
    label: 'Rolled Back',
    dot: 'bg-purple-500',
    pill: 'bg-purple-50 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300',
  },
  COMPLETED: {
    label: 'Completed',
    dot: 'bg-emerald-500',
    pill: 'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300',
  },
  FAILED: {
    label: 'Failed',
    dot: 'bg-red-500',
    pill: 'bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-300',
  },
  REJECTED: {
    label: 'Rejected',
    dot: 'bg-red-500',
    pill: 'bg-red-50 text-red-700 dark:bg-red-950/60 dark:text-red-300',
  },
};

export const StatusBadge: React.FC<{ status: string; size?: 'sm' | 'md' }> = ({
  status,
  size = 'sm',
}) => {
  const cfg = STATUS_STYLES[status] || {
    label: status,
    dot: 'bg-neutral-400',
    pill: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${cfg.pill} ${
        size === 'sm' ? 'px-2.5 py-0.5 text-[11px]' : 'px-3 py-1 text-[12px]'
      }`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {cfg.pulse && (
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-75 ${cfg.dot}`}
          />
        )}
        <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
      </span>
      <span>{cfg.label}</span>
    </span>
  );
};
