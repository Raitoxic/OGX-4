import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, FolderOpen, Plus, Sparkles, X } from 'lucide-react';
import { ModeBanner } from '../components/ModeBanner';
import { useAuth } from '../context/AuthContext';
import { useTaskStream } from '../hooks/useTaskStream';
import { api, ApiError } from '../services/api';
import type { AutonomyMode, TaskDetail, TaskSummary } from '../types/hai';
import { ActivityDrawer } from '../workspace/ActivityDrawer';
import { CheckpointDrawer } from '../workspace/CheckpointDrawer';
import { ExecutionControlBar } from '../workspace/ExecutionControlBar';
import { LivePlanPanel } from '../workspace/LivePlanPanel';
import { SharedArtifactPanel } from '../workspace/SharedArtifactPanel';

const DEMO_PROMPTS = [
  {
    label: 'Distributed Consensus (Raft vs Paxos)',
    prompt:
      'Research and write a structured technical report on Distributed Consensus and Fault-Tolerant State Replication (Raft vs Paxos vs PBFT) for latency-sensitive cloud control planes, including failure modes and a phased production rollout roadmap.',
  },
  {
    label: 'Production AI Agent Checkpointing',
    prompt:
      'Research and generate a structured research report on Human-in-the-Loop Control, Checkpointing, and Adaptive Autonomy for long-running enterprise AI agents, covering interruption semantics, auditability, and operational risk safeguards.',
  },
  {
    label: 'Zero-Trust Service Mesh Security',
    prompt:
      'Research and write a structured technical report on Zero-Trust Service Mesh Architectures (mTLS, SPIFFE/SPIRE, and policy enforcement) for multi-region Kubernetes clusters, comparing performance overhead and recovery strategies.',
  },
];

export const WorkspacePage: React.FC = () => {
  const { taskId: routeTaskId } = useParams<{ taskId?: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tasksList, setTasksList] = useState<TaskSummary[]>([]);
  const [activeTask, setActiveTask] = useState<TaskDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [toast, setToast] = useState<{ text: string; tone: 'info' | 'warning' | 'success' | 'error' } | null>(null);

  const [showNewTaskModal, setShowNewTaskModal] = useState(false);
  const [newPrompt, setNewPrompt] = useState('');
  const [showInterruptModal, setShowInterruptModal] = useState(false);
  const [interruptInstruction, setInterruptInstruction] = useState('');
  const [newTitle, setNewTitle] = useState('');
  const [newAutonomy, setNewAutonomy] = useState<AutonomyMode>(
    user?.default_autonomy_mode || 'balanced',
  );
  const [newResearch, setNewResearch] = useState(false);
  const [creatingTask, setCreatingTask] = useState(false);

  const [checkpointsOpen, setCheckpointsOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [highlightedStepId, setHighlightedStepId] = useState<string | null>(null);
  const [mobilePane, setMobilePane] = useState<'plan' | 'artifact'>('plan');

  const pushToast = useCallback(
    (text: string, tone: 'info' | 'warning' | 'success' | 'error' = 'info') => {
      setToast({ text, tone });
    },
    [],
  );

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 4500);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const loadTasksList = useCallback(async () => {
    const res = await api.listTasks('vyrox');
    setTasksList(res.tasks);
    return res.tasks;
  }, []);

  const fetchTaskDetail = useCallback(async (id: string) => {
    const detail = await api.getTask(id);
    setActiveTask(detail);
  }, []);

  // Initial load & route sync
  useEffect(() => {
    let active = true;
    (async () => {
      setLoading(true);
      try {
        const list = await loadTasksList();
        const targetId = routeTaskId || list[0]?.id;
        if (targetId && active) {
          await fetchTaskDetail(targetId);
        } else if (active) {
          setActiveTask(null);
        }
      } catch (err) {
        if (active) {
          pushToast(err instanceof ApiError ? err.message : 'Unable to load workspace.', 'error');
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [routeTaskId, loadTasksList, fetchTaskDetail, pushToast]);

  const handleSyncRequired = useCallback(() => {
    if (activeTask?.id) {
      fetchTaskDetail(activeTask.id).catch(() => {});
      loadTasksList().catch(() => {});
    }
  }, [activeTask?.id, fetchTaskDetail, loadTasksList]);

  const { connected: sseConnected, liveProgress } = useTaskStream({
    taskId: activeTask?.id ?? null,
    onSyncRequired: handleSyncRequired,
    onSnapshot: (snap) => setActiveTask(snap),
    onToast: pushToast,
  });

  const runAction = useCallback(async (name: string, fn: () => Promise<void>) => {
    setBusyAction(name);
    try {
      await fn();
      await loadTasksList();
    } catch (err) {
      pushToast(err instanceof ApiError ? err.message : 'Action failed.', 'error');
    } finally {
      setBusyAction(null);
    }
  }, [loadTasksList, pushToast]);

  const handleInterrupt = useCallback(async (): Promise<void> => {
    if (!activeTask) return;
    if (!['RUNNING', 'RESUMING', 'AWAITING_APPROVAL'].includes(activeTask.status)) {
      pushToast('Interrupt unavailable: task is not currently running or awaiting approval.', 'info');
      return;
    }
    await runAction('interrupt', async () => {
      const res = await api.interruptTask(activeTask.id);
      setActiveTask(res.task);
      pushToast(res.message || 'Task interrupted safely. State preserved.', 'warning');
      if (res.task.status === 'INTERRUPTED') {
        setInterruptInstruction('');
        setShowInterruptModal(true);
      }
    });
  }, [activeTask, runAction, pushToast]);

  const handleInterruptSubmitChanges = async () => {
    if (!activeTask || !interruptInstruction.trim()) return;
    setBusyAction('interrupt');
    try {
      await api.addInstruction(activeTask.id, interruptInstruction.trim());
      await api.replanTask(activeTask.id, 'Applied new instructions after interrupt.');
      setShowInterruptModal(false);
      setInterruptInstruction('');
      pushToast('Changes saved. Remaining plan updated for approval; completed steps preserved.', 'success');
      await fetchTaskDetail(activeTask.id);
      await loadTasksList();
    } catch (err) {
      pushToast(err instanceof Error ? err.message : 'Failed to apply changes.', 'error');
    } finally {
      setBusyAction(null);
    }
  };

  const handleInterruptResume = async () => {
    if (!activeTask) return;
    setBusyAction('interrupt');
    try {
      const resumed = await api.resumeTask(activeTask.id);
      setActiveTask(resumed);
      setShowInterruptModal(false);
      setInterruptInstruction('');
      pushToast('Resuming from the interruption point without changes.', 'info');
      await fetchTaskDetail(activeTask.id);
      await loadTasksList();
    } catch (err) {
      pushToast(err instanceof Error ? err.message : 'Failed to resume task.', 'error');
    } finally {
      setBusyAction(null);
    }
  };

  // Listen for Raycast-style ⌘K Command Palette workspace actions
  useEffect(() => {
    const handler = (e: Event) => {
      const action = (e as CustomEvent<{ action?: string }>).detail?.action;
      if (!action) return;
      if (action === 'new-task') {
        setShowNewTaskModal(true);
        return;
      }
      if (!activeTask) {
        pushToast('No active task loaded. Create a new task first.', 'info');
        return;
      }
      if (action === 'checkpoints') setCheckpointsOpen(true);
      else if (action === 'events') setActivityOpen(true);
      else if (action === 'start-or-resume') {
        if (activeTask.status === 'RUNNING' || activeTask.status === 'RESUMING') {
          pushToast('Task is already executing.', 'info');
          return;
        }
        if (activeTask.status === 'COMPLETED') {
          pushToast('Task is already completed. Open Rollback to restore an earlier checkpoint.', 'warning');
          return;
        }
        const canResume = ['INTERRUPTED', 'PAUSED', 'ROLLED_BACK', 'FAILED'].includes(activeTask.status);
        runAction(canResume ? 'resume' : 'start', async () => {
          const updated = canResume
            ? await api.resumeTask(activeTask.id)
            : await api.startTask(activeTask.id);
          setActiveTask(updated);
        });
      } else if (action === 'pause') {
        if (activeTask.status !== 'RUNNING' && activeTask.status !== 'RESUMING') {
          pushToast('Pause unavailable: no execution is currently running.', 'info');
          return;
        }
        runAction('pause', async () => {
          const updated = await api.pauseTask(activeTask.id);
          setActiveTask(updated);
          pushToast('Execution paused and checkpoint saved.', 'info');
        });
      } else if (action === 'interrupt') {
        handleInterrupt();
      } else if (action === 'approve') {
        if (activeTask.status !== 'AWAITING_APPROVAL') {
          pushToast('No pending plan or step approval right now.', 'info');
          return;
        }
        runAction('approve', async () => {
          const updated = await api.approveTask(activeTask.id, { auto_continue: true });
          setActiveTask(updated);
        });
      }
    };
    window.addEventListener('vyrox:workspace-command', handler);
    return () => window.removeEventListener('vyrox:workspace-command', handler);
  }, [activeTask, runAction, pushToast, handleInterrupt]);

  useEffect(() => {
    if (!showNewTaskModal) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowNewTaskModal(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showNewTaskModal]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPrompt.trim()) return;
    setCreatingTask(true);
    try {
      const created = await api.createTask({
        prompt: newPrompt.trim(),
        title: newTitle.trim() || undefined,
        interaction_mode: 'vyrox',
        autonomy_mode: newAutonomy,
        research_enabled: newResearch,
      });
      setActiveTask(created);
      await loadTasksList();
      setNewPrompt('');
      setNewTitle('');
      setNewResearch(false);
      setShowNewTaskModal(false);
      navigate(`/workspace/${created.id}`);
      pushToast('Structured execution plan generated. Inspect, edit, lock, or approve to begin.', 'success');
    } catch (err) {
      pushToast(err instanceof ApiError ? err.message : 'Failed to create task.', 'error');
    } finally {
      setCreatingTask(false);
    }
  };

  const handleProvenanceSelect = (stepId: string) => {
    setHighlightedStepId((prev) => (prev === stepId ? null : stepId));
    const el = document.getElementById(`artifact-step-${stepId}`);
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  const handleHighlightFromArtifact = (stepId: string | null) => {
    setHighlightedStepId(stepId);
    if (stepId) {
      const el = document.getElementById(`step-card-${stepId}`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div className="min-h-[calc(100vh-3rem)] bg-apple-bg px-4 py-5 sm:px-6">
      <div className="mx-auto max-w-[1440px] space-y-4">
        {/* Top Workspace Header & Task Switcher */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-3">
            <h1 className="apple-headline truncate text-[22px] sm:text-[25px]">
              {activeTask ? activeTask.title : 'VYRO-X Workspace'}
            </h1>
            {tasksList.length > 0 && (
              <div className="flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-surface px-3 py-1 text-[12px]">
                <FolderOpen className="h-3.5 w-3.5 text-apple-secondary" />
                <select
                  aria-label="Switch Task"
                  value={activeTask?.id || ''}
                  onChange={(e) => {
                    if (e.target.value) navigate(`/workspace/${e.target.value}`);
                  }}
                  className="max-w-[210px] bg-transparent font-medium text-apple-ink outline-none"
                >
                  {tasksList.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.title.slice(0, 38)} ({t.status})
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setShowNewTaskModal(true)}
            className="apple-pill-primary px-4 py-1.5 text-[13px]"
          >
            <Plus className="h-4 w-4" />
            <span>New Task</span>
          </button>
        </div>

        <p className="text-[13.5px] text-apple-secondary">
          Guide, steer, and supervise the agent — inspect the live plan, interrupt mid-execution, and roll back at any time.
        </p>

        {/* Honest AI / Demo Mode Disclosure */}
        <ModeBanner
          providerMode={activeTask?.provider_mode}
          providerName={activeTask?.provider_name}
          compact={Boolean(activeTask)}
        />

        {activeTask && (
          <div className="space-y-3">
            {/* Completed-vs-Total Progress Bar */}
            <div className="rounded-xl border border-apple-border bg-apple-surface px-4 py-3">
              <div className="mb-1.5 flex items-center justify-between text-[12px] font-medium text-apple-secondary">
                <span>Plan Progress</span>
                <span>
                  {activeTask.completed_steps_count}/{activeTask.total_steps_count} steps · {activeTask.progress_percent}%
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-apple-elevated">
                <div
                  className="h-full rounded-full bg-apple-blue transition-all"
                  style={{ width: `${activeTask.progress_percent}%` }}
                />
              </div>
            </div>

            {/* Prominent Approval Gate */}
            {activeTask.status === 'AWAITING_APPROVAL' && (
              <div className="rounded-xl border-2 border-amber-500 bg-amber-50 px-4 py-3 dark:bg-amber-950/30">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2 font-semibold text-amber-800 dark:text-amber-200">
                    <AlertTriangle className="h-4 w-4 shrink-0" />
                    <span>Your approval is required to continue</span>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setMobilePane('plan')}
                      className="rounded-full border border-amber-500/40 bg-white px-4 py-1.5 text-[13px] font-medium text-amber-800 transition hover:bg-amber-100 dark:bg-amber-900/40 dark:text-amber-100"
                    >
                      Review Plan
                    </button>
                    <button
                      type="button"
                      disabled={busyAction === 'approve'}
                      onClick={() =>
                        runAction('approve', async () => {
                          const updated = await api.approveTask(activeTask.id, { auto_continue: true });
                          setActiveTask(updated);
                        })
                      }
                      className="rounded-full bg-emerald-600 px-4 py-1.5 text-[13px] font-semibold text-white transition hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {busyAction === 'approve' ? 'Approving...' : 'Approve & Continue'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Active Constraints as Chips */}
            {activeTask.additional_instructions.length > 0 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <span className="text-[12px] font-medium text-apple-secondary">Active Constraints:</span>
                {activeTask.additional_instructions.map((ins) => (
                  <span
                    key={ins.id}
                    className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-[11px] font-medium text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300"
                  >
                    {ins.text}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Toast Alert */}
        {toast && (
          <div
            className={`flex items-center justify-between rounded-2xl border px-4 py-2.5 text-[13px] font-medium ${
              toast.tone === 'error'
                ? 'border-red-500/30 bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300'
                : toast.tone === 'warning'
                  ? 'border-amber-500/30 bg-amber-50 text-amber-900 dark:bg-amber-950/50 dark:text-amber-200'
                  : toast.tone === 'success'
                    ? 'border-emerald-500/30 bg-emerald-50 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200'
                    : 'border-apple-blue/30 bg-blue-50 text-[#0071E3] dark:bg-blue-950/50 dark:text-[#2997FF]'
            }`}
          >
            <span>{toast.text}</span>
            <button type="button" onClick={() => setToast(null)} className="ml-3 opacity-70 hover:opacity-100">
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {loading ? (
          <div className="flex h-80 items-center justify-center rounded-xl border border-apple-border bg-apple-surface text-[14px] text-apple-secondary">
            Loading workspace state...
          </div>
        ) : !activeTask ? (
          /* Empty State — Direct Task Launcher */
          <div className="mx-auto max-w-[760px] rounded-xl border border-apple-border bg-apple-surface p-8 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-apple-elevated text-apple-blue shadow-apple-sm">
              <Sparkles className="h-6 w-6" />
            </div>
            <h2 className="apple-headline mt-4 text-[28px]">Start a collaborative research task</h2>
            <p className="mx-auto mt-2 max-w-[560px] text-[14.5px] text-apple-secondary">
              Submit a technical topic in natural language. VYRO-X will propose an inspectable,
              editable, lockable plan that you can interrupt, steer, and roll back at any moment.
            </p>

            <form onSubmit={handleCreateTask} className="mt-6 space-y-3 text-left">
              <textarea
                required
                rows={3}
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                placeholder="e.g., Research and write a structured technical report on Distributed Consensus (Raft vs Paxos) for cloud control planes..."
                className="w-full rounded-2xl border border-apple-border bg-apple-elevated p-4 text-[14px] outline-none focus:border-apple-blue"
              />
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2">
                  {DEMO_PROMPTS.map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => setNewPrompt(preset.prompt)}
                      className="rounded-full border border-apple-border bg-apple-elevated px-3 py-1 text-[11.5px] font-medium text-apple-secondary transition hover:border-apple-blue hover:text-apple-ink"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <button
                  type="submit"
                  disabled={creatingTask || !newPrompt.trim()}
                  className="apple-pill-primary px-6 py-2 text-[14px] disabled:opacity-50"
                >
                  {creatingTask ? 'Generating Plan...' : 'Generate Structured Plan'}
                </button>
              </div>
            </form>
          </div>
        ) : (
          <>
            {/* Dedicated Execution Control Bar */}
            <ExecutionControlBar
              task={activeTask}
              sseConnected={sseConnected}
              liveActivity={liveProgress?.activity}
              isInterruptibleLive={liveProgress?.isInterruptible}
              busyAction={busyAction}
              onStart={() =>
                runAction('start', async () => {
                  const updated = await api.startTask(activeTask.id);
                  setActiveTask(updated);
                })
              }
              onPause={() =>
                runAction('pause', async () => {
                  const updated = await api.pauseTask(activeTask.id);
                  setActiveTask(updated);
                  pushToast('Execution paused and checkpoint saved.', 'info');
                })
              }
              onInterrupt={handleInterrupt}
              onResume={() =>
                runAction('resume', async () => {
                  const updated = await api.resumeTask(activeTask.id);
                  setActiveTask(updated);
                  pushToast('Resumed from saved checkpoint without restarting completed steps.', 'info');
                })
              }
              onApprove={() =>
                runAction('approve', async () => {
                  const updated = await api.approveTask(activeTask.id, { auto_continue: true });
                  setActiveTask(updated);
                })
              }
              onRejectAwaiting={(reason) =>
                runAction('reject', async () => {
                  const awaiting = activeTask.steps.find((s) => s.status === 'AWAITING_APPROVAL');
                  if (!awaiting) return;
                  const res = await api.rejectStep(activeTask.id, awaiting.id, reason, true);
                  setActiveTask(res.task);
                  pushToast('Step rejected. VYRO-X proposed a revised alternative for your review.', 'info');
                })
              }
              onAddInstruction={(text) =>
                runAction('instruct', async () => {
                  const res = await api.addInstruction(activeTask.id, text);
                  setActiveTask(res.task);
                  pushToast('Mid-execution instruction queued for upcoming steps.', 'success');
                })
              }
              onReplan={(reason) =>
                runAction('replan', async () => {
                  const updated = await api.replanTask(activeTask.id, reason);
                  setActiveTask(updated);
                  pushToast('Replanned unlocked pending steps while preserving locked & completed steps.', 'success');
                })
              }
              onUpdateAutonomy={(mode, adaptive) =>
                runAction('autonomy', async () => {
                  const updated = await api.updateAutonomy(activeTask.id, {
                    autonomy_mode: mode,
                    adaptive_enabled: adaptive,
                  });
                  setActiveTask(updated);
                  pushToast(`Autonomy updated: ${mode.replace('_', ' ')} (adaptive ${adaptive ? 'on' : 'off'}).`, 'info');
                })
              }
              onOpenCheckpoints={() => setCheckpointsOpen(true)}
              onOpenActivity={() => setActivityOpen(true)}
            />

            {/* Mobile / Tablet Pane Switcher (keeps Execution Controls permanently accessible above) */}
            <div className="flex rounded-lg border border-apple-border bg-apple-surface p-1 lg:hidden">
              <button
                type="button"
                onClick={() => setMobilePane('plan')}
                className={`flex-1 rounded-md py-1.5 text-[12.5px] font-medium transition ${
                  mobilePane === 'plan'
                    ? 'bg-apple-elevated text-apple-ink shadow-apple-sm'
                    : 'text-apple-secondary hover:text-apple-ink'
                }`}
              >
                Live Plan ({activeTask.completed_steps_count}/{activeTask.total_steps_count})
              </button>
              <button
                type="button"
                onClick={() => setMobilePane('artifact')}
                className={`flex-1 rounded-md py-1.5 text-[12.5px] font-medium transition ${
                  mobilePane === 'artifact'
                    ? 'bg-apple-elevated text-apple-ink shadow-apple-sm'
                    : 'text-apple-secondary hover:text-apple-ink'
                }`}
              >
                Shared Artifact ({activeTask.artifact_sections.length})
              </button>
            </div>

            {/* Main Split-Pane Collaborative Canvas */}
            <div className="grid grid-cols-1 gap-3.5 lg:min-h-[calc(100vh-14.5rem)] lg:grid-cols-12">
              {/* LEFT PANEL — LIVE AGENT PLAN */}
              <div className={`${mobilePane === 'plan' ? 'block' : 'hidden'} lg:col-span-5 lg:block`}>
                <LivePlanPanel
                  task={activeTask}
                  highlightedStepId={highlightedStepId}
                  onEditStep={async (stepId, payload) => {
                    const res = await api.editStep(activeTask.id, stepId, payload);
                    setActiveTask(res.task);
                    pushToast('Step instructions updated and persisted.', 'success');
                  }}
                  onToggleLock={async (stepId, locked) => {
                    const res = await api.lockStep(activeTask.id, stepId, locked);
                    setActiveTask(res.task);
                    pushToast(locked ? 'Step locked — protected from agent replanning.' : 'Step unlocked.', 'info');
                  }}
                  onApproveStep={async (stepId) => {
                    const updated = await api.approveStep(activeTask.id, stepId, true);
                    setActiveTask(updated);
                    pushToast('Step approved.', 'success');
                  }}
                  onRejectStep={async (stepId, reason, genAlt) => {
                    const res = await api.rejectStep(activeTask.id, stepId, reason, genAlt);
                    setActiveTask(res.task);
                    pushToast('Step rejected and alternative proposed.', 'warning');
                  }}
                  onSelectProvenance={(stepId) => {
                    setMobilePane('artifact');
                    handleProvenanceSelect(stepId);
                  }}
                />
              </div>

              {/* RIGHT PANEL — SHARED WORKSPACE / ARTIFACT */}
              <div className={`${mobilePane === 'artifact' ? 'block' : 'hidden'} lg:col-span-7 lg:block`}>
                <SharedArtifactPanel
                  task={activeTask}
                  highlightedStepId={highlightedStepId}
                  onHighlightStep={(stepId) => {
                    if (stepId) setMobilePane('plan');
                    handleHighlightFromArtifact(stepId);
                  }}
                  onEditSection={async (sectionId, heading, content) => {
                    await api.editArtifactSection(activeTask.id, sectionId, {
                      heading,
                      current_content: content,
                    });
                    await fetchTaskDetail(activeTask.id);
                    pushToast('Artifact edit saved with AI-vs-Human diff preserved.', 'success');
                  }}
                  onAddSection={async (heading, content) => {
                    await api.addArtifactSection(activeTask.id, { heading, content });
                    await fetchTaskDetail(activeTask.id);
                    pushToast('Human-authored section added to shared artifact.', 'success');
                  }}
                  onRatingSubmitted={() => pushToast('Evaluation rating recorded.', 'success')}
                />
              </div>
            </div>

            {/* Slide-over Checkpoints & Rollback Drawer */}
            <CheckpointDrawer
              open={checkpointsOpen}
              taskId={activeTask.id}
              checkpoints={activeTask.checkpoints}
              onClose={() => setCheckpointsOpen(false)}
              onCreateCheckpoint={async (label) => {
                await api.createCheckpoint(activeTask.id, label);
                await fetchTaskDetail(activeTask.id);
                pushToast(`Saved manual checkpoint: ${label}`, 'success');
              }}
              onRollback={async (cpId) => {
                const res = await api.rollbackCheckpoint(activeTask.id, cpId);
                setActiveTask(res.task);
                setCheckpointsOpen(false);
                pushToast(
                  `Rolled back to Checkpoint v${res.restored_checkpoint.version_number}. Edit or click Resume to continue.`,
                  'info',
                );
              }}
            />

            {/* Slide-over Live Interaction Events Drawer */}
            <ActivityDrawer
              open={activityOpen}
              events={activeTask.recent_events}
              onClose={() => setActivityOpen(false)}
            />
          </>
        )}
      </div>

      {/* New Task Creation Modal */}
      {showNewTaskModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4 backdrop-blur-sm">
          <div className="w-full max-w-[600px] rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-lg">
            <div className="flex items-center justify-between">
              <h2 className="text-[20px] font-semibold tracking-tight">Create New Collaborative Task</h2>
              <button
                type="button"
                onClick={() => setShowNewTaskModal(false)}
                className="rounded-full p-1.5 text-apple-secondary hover:bg-apple-surface"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleCreateTask} className="mt-4 space-y-4">
              <div>
                <label className="mb-1 block text-[12px] font-medium text-apple-secondary">
                  Task Title (optional — auto-derived from prompt if blank)
                </label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g., Distributed Consensus Architecture Report"
                  className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2 text-[13.5px] outline-none focus:border-apple-blue"
                />
              </div>

              <div>
                <label className="mb-1 block text-[12px] font-medium text-apple-secondary">
                  Natural-Language Task Instruction
                </label>
                <textarea
                  required
                  rows={4}
                  value={newPrompt}
                  onChange={(e) => setNewPrompt(e.target.value)}
                  placeholder="Describe the technical topic and desired research report..."
                  className="w-full rounded-xl border border-apple-border bg-apple-bg p-3.5 text-[13.5px] outline-none focus:border-apple-blue"
                />
              </div>

              <div>
                <p className="mb-1.5 text-[11.5px] font-medium text-apple-secondary">Quick Research Presets:</p>
                <div className="flex flex-wrap gap-1.5">
                  {DEMO_PROMPTS.map((preset) => (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => setNewPrompt(preset.prompt)}
                      className="rounded-full border border-apple-border bg-apple-surface px-3 py-1 text-[11.5px] font-medium hover:border-apple-blue"
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="mb-1 block text-[12px] font-medium text-apple-secondary">
                  Initial Autonomy Mode
                </label>
                <select
                  value={newAutonomy}
                  onChange={(e) => setNewAutonomy(e.target.value as AutonomyMode)}
                  className="w-full rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2 text-[13.5px] outline-none focus:border-apple-blue"
                >
                  <option value="supervised">Supervised — Approve every step</option>
                  <option value="balanced">Balanced — Adaptive oversight (Recommended)</option>
                  <option value="higher_autonomy">Higher Autonomy — Streamlined (High-risk gated)</option>
                </select>
              </div>

              <label className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-apple-border bg-apple-bg px-3.5 py-3">
                <input
                  type="checkbox"
                  checked={newResearch}
                  onChange={(e) => setNewResearch(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-[#0071E3]"
                />
                <span>
                  <span className="block text-[13px] font-medium text-apple-ink">
                    Enable research-driven generation
                  </span>
                  <span className="block text-[11.5px] text-apple-secondary">
                    Retrieve academic papers & technical sources and ground the output in them with transparent,
                    verifiable references. Skip for simple coding, formatting, or calculation tasks.
                  </span>
                </span>
              </label>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowNewTaskModal(false)}
                  className="rounded-full px-4 py-2 text-[13px] text-apple-secondary hover:text-apple-ink"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingTask || !newPrompt.trim()}
                  className="apple-pill-primary px-5 py-2 text-[13.5px] disabled:opacity-50"
                >
                  {creatingTask ? 'Planning...' : 'Generate Plan'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showInterruptModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setShowInterruptModal(false)}
        >
          <div
            className="w-full max-w-[560px] rounded-2xl border border-apple-borderStrong bg-apple-elevated p-6 shadow-apple-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-[18px] font-semibold tracking-tight text-apple-ink">Task Interrupted</h2>
                <p className="mt-1 text-[12.5px] leading-relaxed text-apple-secondary">
                  Execution was safely interrupted. Completed steps, history, shared artifacts, and checkpoints
                  are preserved. Enter changes to apply, or resume without changes.
                </p>
              </div>
              <span className="shrink-0 rounded-full bg-orange-50 px-2.5 py-0.5 text-[11px] font-medium text-orange-800 dark:bg-orange-950/60 dark:text-orange-300">
                Interrupted
              </span>
            </div>

            <textarea
              rows={6}
              value={interruptInstruction}
              onChange={(e) => setInterruptInstruction(e.target.value)}
              placeholder="Enter the changes or new instructions you want to apply..."
              className="mt-4 w-full resize-y rounded-xl border border-apple-border bg-apple-bg px-3.5 py-2.5 text-[13.5px] leading-relaxed text-apple-ink outline-none transition focus:border-apple-blue"
            />

            <div className="mt-4 flex flex-wrap items-center justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowInterruptModal(false)}
                className="rounded-full border border-apple-border px-4 py-1.5 text-[12.5px] font-medium text-apple-secondary transition hover:bg-apple-surface"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={busyAction !== null}
                onClick={handleInterruptResume}
                className="rounded-full border border-apple-border px-4 py-1.5 text-[12.5px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:opacity-40"
              >
                Resume Without Changes
              </button>
              <button
                type="button"
                disabled={busyAction !== null || !interruptInstruction.trim()}
                onClick={handleInterruptSubmitChanges}
                className="apple-pill-primary px-4 py-1.5 text-[12.5px] disabled:opacity-40"
              >
                {busyAction === 'interrupt' ? 'Applying...' : 'Submit Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
