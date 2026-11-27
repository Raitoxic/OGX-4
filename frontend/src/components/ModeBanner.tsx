import React from 'react';
import { Cpu, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const ModeBanner: React.FC<{
  providerMode?: 'demo' | 'live';
  providerName?: string;
  compact?: boolean;
}> = ({ providerMode, providerName, compact = false }) => {
  const { systemInfo } = useAuth();
  const mode = providerMode || systemInfo?.provider_mode || 'demo';
  const name = providerName || systemInfo?.provider_name || 'deterministic-research-v1';

  const isDemo = mode === 'demo';

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-2 rounded-apple-sm border px-3.5 py-2 text-[12px] ${
        isDemo
          ? 'border-amber-500/25 bg-amber-50/70 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200'
          : 'border-emerald-500/25 bg-emerald-50/70 text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200'
      }`}
    >
      <div className="flex items-center gap-2">
        {isDemo ? (
          <ShieldCheck className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <Cpu className="h-3.5 w-3.5 shrink-0" />
        )}
        <span className="font-semibold">
          {isDemo ? 'Deterministic Demo Mode' : `Live AI Mode (${name})`}
        </span>
        {!compact && (
          <span className="opacity-85">
            {isDemo
              ? '— Clearly labelled local research engine (no external API key configured). All state transitions, interrupts, checkpoints, and edits are live and persisted.'
              : '— Connected via environment-configured model provider with human-in-the-loop safety gates.'}
          </span>
        )}
      </div>
      <span className="font-mono text-[11px] opacity-75">{name}</span>
    </div>
  );
};
