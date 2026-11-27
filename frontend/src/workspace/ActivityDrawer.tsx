import React, { useEffect, useState } from 'react';
import { Activity, Bot, Cpu, User, X } from 'lucide-react';
import type { InteractionEvent } from '../types/hai';

interface ActivityDrawerProps {
  open: boolean;
  events: InteractionEvent[];
  onClose: () => void;
}

export const ActivityDrawer: React.FC<ActivityDrawerProps> = ({ open, events, onClose }) => {
  const [actorFilter, setActorFilter] = useState<'all' | 'human' | 'agent' | 'system'>('all');

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  if (!open) return null;

  const filtered =
    actorFilter === 'all' ? events : events.filter((ev) => ev.actor === actorFilter);

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-sm">
      <div className="flex h-full w-full max-w-[480px] flex-col border-l border-apple-border bg-apple-elevated shadow-apple-lg">
        <div className="flex items-center justify-between border-b border-apple-border px-5 py-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-apple-blue" />
            <div>
              <h2 className="text-[16px] font-semibold">Interaction Event Stream</h2>
              <p className="text-[11.5px] text-apple-secondary">
                Complete persisted audit trail of human and agent actions.
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

        <div className="flex items-center gap-1.5 border-b border-apple-border px-5 py-2.5">
          {(['all', 'human', 'agent', 'system'] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setActorFilter(f)}
              className={`rounded-full px-3 py-1 text-[11.5px] font-medium capitalize transition ${
                actorFilter === f
                  ? 'bg-apple-ink text-apple-bg'
                  : 'bg-apple-surface text-apple-secondary hover:text-apple-ink'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <div className="flex-1 space-y-2.5 overflow-y-auto p-5">
          {filtered.map((ev) => (
            <div
              key={ev.id}
              className="rounded-2xl border border-apple-border bg-apple-bg p-3 text-[12.5px]"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1 font-mono text-[10.5px] font-semibold text-apple-blue">
                  {ev.actor === 'human' ? (
                    <User className="h-3 w-3" />
                  ) : ev.actor === 'agent' ? (
                    <Bot className="h-3 w-3" />
                  ) : (
                    <Cpu className="h-3 w-3" />
                  )}
                  {ev.event_type}
                </span>
                {ev.created_at && (
                  <span className="text-[10.5px] text-apple-tertiary">
                    {new Date(ev.created_at).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <p className="mt-1 text-apple-ink">{ev.summary}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
