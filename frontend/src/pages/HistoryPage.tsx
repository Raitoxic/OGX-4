import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowUpRight,
  Bot,
  Clock,
  Cpu,
  FileText,
  History,
  Trash2,
  User,
} from 'lucide-react';
import { StatusBadge } from '../components/StatusBadge';
import { api } from '../services/api';
import type { TaskDetail, TaskSummary } from '../types/hai';

export const HistoryPage: React.FC = () => {
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [selectedTask, setSelectedTask] = useState<TaskDetail | null>(null);
  const [modeFilter, setModeFilter] = useState<'all' | 'vyrox' | 'baseline'>('all');
  const [actorFilter, setActorFilter] = useState<'all' | 'human' | 'agent' | 'system'>('all');
  const [loading, setLoading] = useState(true);

  const loadList = async () => {
    setLoading(true);
    try {
      const res = await api.listTasks(modeFilter === 'all' ? undefined : modeFilter);
      setTasks(res.tasks);
      if (res.tasks.length > 0) {
        const detail = await api.getTask(res.tasks[0].id);
        setSelectedTask(detail);
      } else {
        setSelectedTask(null);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadList();
  }, [modeFilter]);

  const handleSelect = async (taskId: string) => {
    const detail = await api.getTask(taskId);
    setSelectedTask(detail);
  };

  const handleDelete = async (taskId: string) => {
    await api.deleteTask(taskId);
    await loadList();
  };

  const filteredEvents =
    selectedTask?.recent_events.filter((ev) =>
      actorFilter === 'all' ? true : ev.actor === actorFilter,
    ) || [];

  return (
    <div className="min-h-[calc(100vh-3rem)] bg-apple-surface px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1320px] space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.12em] text-apple-blue">
              Persistent Audit Trail
            </p>
            <h1 className="apple-headline mt-1 text-[32px]">Task & Interaction History</h1>
            <p className="mt-1 text-[14px] text-apple-secondary">
              Reopen previous tasks, inspect saved checkpoints, review completed artifacts, and audit every decision.
            </p>
          </div>

          <div className="inline-flex rounded-full border border-apple-border bg-apple-elevated p-1">
            {(['all', 'vyrox', 'baseline'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setModeFilter(tab)}
                className={`rounded-full px-4 py-1 text-[12px] font-medium uppercase transition ${
                  modeFilter === tab
                    ? 'bg-apple-ink text-apple-bg'
                    : 'text-apple-secondary hover:text-apple-ink'
                }`}
              >
                {tab === 'all' ? 'All Modes' : tab === 'vyrox' ? 'VYRO-X' : 'Baseline'}
              </button>
            ))}
          </div>
        </div>

        {loading ? (
          <div className="rounded-xl border border-apple-border bg-apple-elevated p-10 text-center text-[14px] text-apple-secondary">
            Loading persisted task history...
          </div>
        ) : tasks.length === 0 ? (
          <div className="rounded-xl border border-apple-border bg-apple-elevated p-12 text-center">
            <History className="mx-auto h-9 w-9 text-apple-tertiary" />
            <h2 className="mt-3 text-[18px] font-semibold">No tasks recorded yet</h2>
            <p className="mt-1 text-[14px] text-apple-secondary">
              Create your first collaborative task in the VYRO-X Workspace to start building a complete interaction history.
            </p>
            <Link to="/workspace" className="apple-pill-primary mt-5 px-5 py-2 text-[13.5px]">
              Open Workspace
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
            {/* Task List */}
            <div className="space-y-3 lg:col-span-5">
              {tasks.map((t) => {
                const active = selectedTask?.id === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => handleSelect(t.id)}
                    className={`cursor-pointer rounded-lg border p-4 transition ${
                      active
                        ? 'border-apple-blue bg-apple-elevated shadow-apple-sm'
                        : 'border-apple-border bg-apple-elevated/70 hover:border-apple-blue/40'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-[14.5px] font-semibold leading-snug">{t.title}</h3>
                      <span className="rounded-full bg-apple-surface px-2 py-0.5 text-[10.5px] font-semibold uppercase text-apple-secondary">
                        {t.interaction_mode === 'baseline' ? 'Baseline' : 'VYRO-X'}
                      </span>
                    </div>

                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <StatusBadge status={t.status} />
                      <span className="text-[11.5px] text-apple-secondary">
                        {t.completed_steps_count}/{t.total_steps_count} steps
                      </span>
                      <span className="text-[11.5px] text-apple-secondary">
                        · {t.checkpoints_count} checkpoints
                      </span>
                    </div>

                    <div className="mt-2.5 flex items-center justify-between text-[11px] text-apple-tertiary">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        Updated {t.updated_at ? new Date(t.updated_at).toLocaleString() : '—'}
                      </span>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(t.id);
                        }}
                        className="rounded p-1 text-apple-tertiary hover:text-red-500"
                        title="Delete task"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Task Inspector */}
            {selectedTask && (
              <div className="space-y-5 rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm lg:col-span-7">
                <div className="flex flex-wrap items-start justify-between gap-3 border-b border-apple-border pb-4">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={selectedTask.status} size="md" />
                      <span className="text-[12px] text-apple-secondary">
                        Created {selectedTask.created_at ? new Date(selectedTask.created_at).toLocaleString() : '—'}
                      </span>
                    </div>
                    <h2 className="mt-2 text-[20px] font-semibold tracking-tight">
                      {selectedTask.title}
                    </h2>
                    <p className="mt-1 text-[13px] text-apple-secondary">{selectedTask.prompt}</p>
                  </div>

                  {selectedTask.interaction_mode !== 'baseline' && (
                    <Link
                      to={`/workspace/${selectedTask.id}`}
                      className="apple-pill-primary shrink-0 px-4 py-1.5 text-[12.5px]"
                    >
                      <span>Reopen in Workspace</span>
                      <ArrowUpRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>

                {/* Saved Checkpoints Summary */}
                <div>
                  <h3 className="text-[13.5px] font-semibold">
                    Saved Checkpoints ({selectedTask.checkpoints.length})
                  </h3>
                  {selectedTask.checkpoints.length === 0 ? (
                    <p className="mt-1 text-[12.5px] text-apple-secondary">
                      No checkpoints (Prompt-and-Wait Baseline tasks execute in a single opaque pass).
                    </p>
                  ) : (
                    <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      {selectedTask.checkpoints.slice(0, 6).map((cp) => (
                        <div
                          key={cp.id}
                          className="rounded-xl border border-apple-border bg-apple-bg px-3 py-2 text-[12px]"
                        >
                          <div className="font-semibold">
                            v{cp.version_number} · {cp.label}
                          </div>
                          <div className="mt-0.5 text-[11px] text-apple-secondary">
                            {cp.task_status} · {cp.completed_steps_count}/{cp.total_steps_count} steps
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Artifact Outputs Summary */}
                <div>
                  <h3 className="flex items-center gap-1.5 text-[13.5px] font-semibold">
                    <FileText className="h-3.5 w-3.5 text-apple-blue" /> Artifact Sections (
                    {selectedTask.artifact_sections.length})
                  </h3>
                  <div className="mt-2 space-y-2">
                    {selectedTask.artifact_sections.map((sec) => (
                      <div
                        key={sec.id}
                        className="rounded-xl border border-apple-border bg-apple-bg p-3 text-[12.5px]"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold">{sec.heading}</span>
                          <span className="rounded-full bg-apple-surface px-2 py-0.5 text-[10.5px] capitalize text-apple-secondary">
                            {sec.authorship} · v{sec.version}
                          </span>
                        </div>
                        <p className="mt-1 line-clamp-2 text-apple-secondary">
                          {sec.current_content}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Complete Chronological Interaction History */}
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-[13.5px] font-semibold">
                      Interaction History ({filteredEvents.length} events)
                    </h3>
                    <div className="flex gap-1">
                      {(['all', 'human', 'agent', 'system'] as const).map((a) => (
                        <button
                          key={a}
                          type="button"
                          onClick={() => setActorFilter(a)}
                          className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium capitalize ${
                            actorFilter === a
                              ? 'bg-apple-ink text-apple-bg'
                              : 'bg-apple-surface text-apple-secondary'
                          }`}
                        >
                          {a}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="mt-2.5 max-h-72 space-y-2 overflow-y-auto pr-1">
                    {filteredEvents.map((ev) => (
                      <div
                        key={ev.id}
                        className="rounded-xl border border-apple-border bg-apple-bg px-3 py-2 text-[12px]"
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
                          <span className="text-[10.5px] text-apple-tertiary">
                            {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <p className="mt-0.5 text-apple-ink">{ev.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
