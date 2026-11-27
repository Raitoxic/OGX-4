import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  AlertTriangle,
  ArrowRight,
  Beaker,
  Check,
  FlaskConical,
  MessageSquare,
  Play,
  ShieldCheck,
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import type { EvaluationDashboardData, TaskDetail, TaskSummary } from '../types/hai';

export const EvaluationPage: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<EvaluationDashboardData | null>(null);
  const [completedTasks, setCompletedTasks] = useState<TaskSummary[]>([]);
  const [rateTaskId, setRateTaskId] = useState('');
  const [rateSavedNotice, setRateSavedNotice] = useState(false);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<'measured' | 'illustrative'>('measured');

  const [selectedScenarioKey, setSelectedScenarioKey] = useState('distributed-consensus');
  const [runningBaseline, setRunningBaseline] = useState(false);
  const [launchingVyrox, setLaunchingVyrox] = useState(false);
  const [baselineResult, setBaselineResult] = useState<TaskDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [effort, setEffort] = useState(5);
  const [trust, setTrust] = useState(3);
  const [control, setControl] = useState(2);
  const [notes, setNotes] = useState('');
  const [ratingSubmitted, setRatingSubmitted] = useState(false);

  // Structured User Feedback state
  const [fbCategory, setFbCategory] = useState<'general' | 'usability' | 'autonomy' | 'accuracy' | 'bug' | 'suggestion'>('usability');
  const [fbRating, setFbRating] = useState(5);
  const [fbComment, setFbComment] = useState('');
  const [fbSaved, setFbSaved] = useState(false);

  const loadEvaluation = async () => {
    setLoading(true);
    try {
      const [res, tasksRes] = await Promise.all([api.getEvaluation(), api.listTasks()]);
      setData(res);
      const done = tasksRes.tasks.filter((t) => t.status === 'COMPLETED');
      setCompletedTasks(done);
      if (done.length > 0 && !rateTaskId) {
        setRateTaskId(done[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluation();
  }, []);

  const activeScenario =
    data?.comparable_scenarios.find((s) => s.key === selectedScenarioKey) ||
    data?.comparable_scenarios[0];

  const handleRunBaseline = async () => {
    if (!activeScenario) return;
    setRunningBaseline(true);
    setError(null);
    setRatingSubmitted(false);
    try {
      const created = await api.createTask({
        title: `[Baseline] ${activeScenario.title}`,
        prompt: activeScenario.prompt,
        interaction_mode: 'baseline',
      });
      setBaselineResult(created);
      await loadEvaluation();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Baseline run failed.');
    } finally {
      setRunningBaseline(false);
    }
  };

  const handleLaunchMatchedVyrox = async () => {
    if (!activeScenario) return;
    setLaunchingVyrox(true);
    setError(null);
    try {
      const created = await api.createTask({
        title: `[VYRO-X Eval] ${activeScenario.title}`,
        prompt: activeScenario.prompt,
        interaction_mode: 'vyrox',
        autonomy_mode: 'balanced',
      });
      navigate(`/workspace/${created.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unable to launch VYRO-X evaluation task.');
      setLaunchingVyrox(false);
    }
  };

  const handleSubmitBaselineRating = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!baselineResult || !activeScenario) return;
    await api.submitEvaluationRating({
      task_id: baselineResult.id,
      scenario_key: activeScenario.key,
      effort_rating: effort,
      trust_rating: trust,
      control_rating: control,
      notes,
    });
    setRatingSubmitted(true);
    setNotes('');
    await loadEvaluation();
  };

  const handleSubmitFeedback = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fbComment.trim()) return;
    await api.submitFeedback({
      task_id: rateTaskId || undefined,
      category: fbCategory,
      rating: fbRating,
      comment: fbComment.trim(),
    });
    setFbComment('');
    setFbSaved(true);
    await loadEvaluation();
  };

  if (loading || !data) {
    return (
      <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-apple-surface text-[14px] text-apple-secondary">
        Loading VYRO-X evaluation dashboard...
      </div>
    );
  }

  const isIllustrative = viewMode === 'illustrative';
  const vyroxStats = isIllustrative ? data.illustrative_demo_reference.vyrox_illustrative : data.measured.vyrox;
  const baseStats = isIllustrative
    ? data.illustrative_demo_reference.baseline_illustrative
    : data.measured.baseline;

  const fmt = (val: unknown, suffix = '') =>
    val === null || val === undefined ? 'Not yet measured' : `${val}${suffix}`;

  const scaleChartData = [
    { metric: 'Perceived Control (1-7)', 'VYRO-X': Number(vyroxStats.avg_perceived_control ?? 0), Baseline: Number(baseStats.avg_perceived_control ?? 0) },
    { metric: 'Perceived Trust (1-7)', 'VYRO-X': Number(vyroxStats.avg_perceived_trust ?? 0), Baseline: Number(baseStats.avg_perceived_trust ?? 0) },
    { metric: 'User Effort (1-7, lower=better)', 'VYRO-X': Number(vyroxStats.avg_user_effort ?? 0), Baseline: Number(baseStats.avg_user_effort ?? 0) },
  ];

  const reliabilityChartData = [
    { metric: 'Completion (%)', 'VYRO-X': Number(vyroxStats.task_completion_rate ?? 0), Baseline: Number(baseStats.task_completion_rate ?? 0) },
    { metric: 'Recovery (%)', 'VYRO-X': Number(vyroxStats.recovery_success_rate ?? 0), Baseline: Number(baseStats.recovery_success_rate ?? 0) },
    { metric: 'Plan Mod (%)', 'VYRO-X': Number(vyroxStats.plan_modification_success_rate ?? 0), Baseline: Number(baseStats.plan_modification_success_rate ?? 0) },
    { metric: 'Rollback (%)', 'VYRO-X': Number(vyroxStats.checkpoint_restoration_success_rate ?? 0), Baseline: Number(baseStats.checkpoint_restoration_success_rate ?? 0) },
  ];

  // All 14 required performance metrics
  const metricRows = [
    { name: 'Sample Size (Executed Tasks)', v: isIllustrative ? 'Template (n=0)' : `${data.measured.vyrox.sample_size} task(s)`, b: isIllustrative ? 'Template (n=0)' : `${data.measured.baseline.sample_size} task(s)` },
    { name: '1. Task Completion Rate', v: fmt(vyroxStats.task_completion_rate, '%'), b: fmt(baseStats.task_completion_rate, '%') },
    { name: '2. Task Completion Time', v: fmt(vyroxStats.avg_completion_time_sec, 's'), b: fmt(baseStats.avg_completion_time_sec, 's') },
    { name: '3. Human Intervention Count', v: fmt(vyroxStats.avg_interventions_per_task, ' / task'), b: fmt(baseStats.avg_interventions_per_task, ' / task') },
    { name: '4. User Effort (1–7, lower=easier)', v: fmt(vyroxStats.avg_user_effort, ' / 7'), b: fmt(baseStats.avg_user_effort, ' / 7') },
    { name: '5. Perceived Trust (1–7)', v: fmt(vyroxStats.avg_perceived_trust, ' / 7'), b: fmt(baseStats.avg_perceived_trust, ' / 7') },
    { name: '6. Perceived Control (1–7)', v: fmt(vyroxStats.avg_perceived_control, ' / 7'), b: fmt(baseStats.avg_perceived_control, ' / 7') },
    { name: '7. Recovery Success Rate', v: fmt(vyroxStats.recovery_success_rate, '%'), b: fmt(baseStats.recovery_success_rate, '%') },
    { name: '8. Plan Modification Success', v: fmt(vyroxStats.plan_modification_success_rate, '%'), b: fmt(baseStats.plan_modification_success_rate, '%') },
    { name: '9. Approval Response Time', v: fmt(vyroxStats.avg_approval_response_sec, 's'), b: fmt(baseStats.avg_approval_response_sec, 's') },
    { name: '10. Interrupt Response Latency', v: fmt(vyroxStats.avg_interrupt_latency_ms, ' ms'), b: fmt(baseStats.avg_interrupt_latency_ms, ' ms') },
    { name: '11. Checkpoint Restoration Success', v: fmt(vyroxStats.checkpoint_restoration_success_rate, '%'), b: fmt(baseStats.checkpoint_restoration_success_rate, '%') },
    { name: '12. Agent Execution Failure Rate', v: fmt(vyroxStats.agent_execution_failure_rate, '%'), b: fmt(baseStats.agent_execution_failure_rate, '%') },
    { name: '13. Artifact Revision Success', v: fmt(vyroxStats.artifact_revision_success_rate, '%'), b: fmt(baseStats.artifact_revision_success_rate, '%') },
    { name: '14. SSE Update Latency', v: fmt(vyroxStats.avg_sse_update_latency_ms, ' ms'), b: fmt(baseStats.avg_sse_update_latency_ms, ' ms') },
  ];

  return (
    <div className="min-h-[calc(100vh-3rem)] bg-apple-surface px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1280px] space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-[12px] font-semibold uppercase tracking-[0.12em] text-apple-blue">
              VYRO-X Scientific Evaluation
            </p>
            <h1 className="apple-headline mt-1 text-[32px]">VYRO-X vs. Prompt-and-Wait Baseline</h1>
            <p className="mt-1 max-w-[740px] text-[14px] text-apple-secondary">
              Run matched technical scenarios across both interaction models, measure 14 operational
              and human-experience metrics, and inspect real statistical tests without fabricated claims.
            </p>
          </div>

          <div className="inline-flex rounded-full border border-apple-border bg-apple-elevated p-1">
            <button
              type="button"
              onClick={() => setViewMode('measured')}
              className={`rounded-full px-4 py-1.5 text-[12px] font-medium transition ${
                viewMode === 'measured' ? 'bg-apple-blue text-white' : 'text-apple-secondary hover:text-apple-ink'
              }`}
            >
              Measured Local Data (Real)
            </button>
            <button
              type="button"
              onClick={() => setViewMode('illustrative')}
              className={`rounded-full px-4 py-1.5 text-[12px] font-medium transition ${
                viewMode === 'illustrative' ? 'bg-amber-500 text-white' : 'text-apple-secondary hover:text-apple-ink'
              }`}
            >
              Illustrative Demo Preview
            </button>
          </div>
        </div>

        {/* Strict Provenance Banner */}
        {isIllustrative ? (
          <div className="flex items-start gap-3 rounded-2xl border border-amber-500/40 bg-amber-50 px-4 py-3 text-[13px] text-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <strong>ILLUSTRATIVE / SIMULATED PREVIEW ONLY: </strong>
              {data.illustrative_demo_reference.disclaimer}
            </div>
          </div>
        ) : (
          <div className="flex items-start gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-50/70 px-4 py-3 text-[13px] text-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <strong>MEASURED LOCAL SESSION DATA: </strong>
              Displaying strictly recorded tasks from your database (VYRO-X n={data.measured.vyrox.sample_size},
              Baseline n={data.measured.baseline.sample_size}).
            </div>
          </div>
        )}

        {/* Live Paired Benchmark Runner */}
        <section className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
          <div className="flex items-center gap-2">
            <FlaskConical className="h-4 w-4 text-apple-blue" />
            <h2 className="text-[17px] font-semibold">Live Paired Benchmark Runner</h2>
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
            {data.comparable_scenarios.map((sc) => (
              <button
                key={sc.key}
                type="button"
                onClick={() => setSelectedScenarioKey(sc.key)}
                className={`rounded-2xl border p-4 text-left transition ${
                  selectedScenarioKey === sc.key
                    ? 'border-apple-blue bg-blue-50/40 dark:bg-blue-950/25'
                    : 'border-apple-border bg-apple-bg hover:border-apple-blue/40'
                }`}
              >
                <p className="text-[11px] font-semibold uppercase tracking-wider text-apple-blue">{sc.difficulty}</p>
                <p className="mt-1 text-[14px] font-semibold">{sc.title}</p>
              </button>
            ))}
          </div>

          {activeScenario && (
            <div className="mt-4 rounded-2xl border border-apple-border bg-apple-surface p-4">
              <p className="text-[11.5px] font-semibold uppercase tracking-wider text-apple-secondary">
                Shared Scenario Prompt
              </p>
              <p className="mt-1 text-[13.5px] text-apple-ink">{activeScenario.prompt}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  disabled={runningBaseline}
                  onClick={handleRunBaseline}
                  className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-elevated px-5 py-2 text-[13px] font-medium text-apple-ink transition hover:border-apple-ink disabled:opacity-50"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span>{runningBaseline ? 'Running Prompt-and-Wait...' : 'Run Prompt-and-Wait Baseline'}</span>
                </button>
                <button
                  type="button"
                  disabled={launchingVyrox}
                  onClick={handleLaunchMatchedVyrox}
                  className="apple-pill-primary px-5 py-2 text-[13px] disabled:opacity-50"
                >
                  <span>{launchingVyrox ? 'Creating VYRO-X Plan...' : 'Launch Matched VYRO-X Trial'}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
              {error && <p className="mt-2 text-[12.5px] text-red-600">{error}</p>}
            </div>
          )}

          {baselineResult && (
            <div className="mt-5 grid grid-cols-1 gap-4 rounded-2xl border border-apple-border bg-apple-bg p-5 lg:grid-cols-12">
              <div className="lg:col-span-7">
                <span className="text-[12px] font-semibold uppercase tracking-wider text-apple-secondary">
                  Baseline Single-Pass Output ({baselineResult.total_execution_ms} ms)
                </span>
                <div className="mt-2 max-h-56 overflow-y-auto whitespace-pre-wrap rounded-xl bg-apple-surface p-3.5 text-[12.5px] leading-relaxed text-apple-secondary">
                  {baselineResult.artifact_sections[0]?.current_content || 'Baseline completed.'}
                </div>
              </div>
              <div className="lg:col-span-5">
                <h3 className="text-[14px] font-semibold">Rate Baseline Experience (1–7)</h3>
                {ratingSubmitted ? (
                  <p className="mt-3 flex items-center gap-1.5 text-[13px] font-medium text-emerald-700 dark:text-emerald-300">
                    <Check className="h-4 w-4" /> Baseline rating recorded. Now run the Matched VYRO-X Trial!
                  </p>
                ) : (
                  <form onSubmit={handleSubmitBaselineRating} className="mt-3 space-y-2.5 text-[12.5px]">
                    <label className="block">Effort (1–7): <strong>{effort}</strong><input type="range" min={1} max={7} value={effort} onChange={(e) => setEffort(Number(e.target.value))} className="w-full accent-[#0071E3]" /></label>
                    <label className="block">Trust (1–7): <strong>{trust}</strong><input type="range" min={1} max={7} value={trust} onChange={(e) => setTrust(Number(e.target.value))} className="w-full accent-[#0071E3]" /></label>
                    <label className="block">Control (1–7): <strong>{control}</strong><input type="range" min={1} max={7} value={control} onChange={(e) => setControl(Number(e.target.value))} className="w-full accent-[#0071E3]" /></label>
                    <input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Brief notes..." className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[12px]" />
                    <button type="submit" className="apple-pill-primary w-full py-1.5 text-[12.5px]">Save Baseline Rating</button>
                  </form>
                )}
              </div>
            </div>
          )}

          {completedTasks.length > 0 && (
            <div className="mt-5 rounded-2xl border border-apple-border bg-apple-surface p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-[13.5px] font-semibold">Record Measured Rating for Any Completed Task</h3>
                {rateSavedNotice && (
                  <span className="inline-flex items-center gap-1 text-[12px] font-medium text-emerald-700 dark:text-emerald-300">
                    <Check className="h-3.5 w-3.5" /> Saved to measured dataset
                  </span>
                )}
              </div>
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  if (!rateTaskId) return;
                  await api.submitEvaluationRating({
                    task_id: rateTaskId,
                    scenario_key: selectedScenarioKey,
                    effort_rating: effort,
                    trust_rating: trust,
                    control_rating: control,
                    notes,
                  });
                  setRateSavedNotice(true);
                  setNotes('');
                  await loadEvaluation();
                }}
                className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-12 md:items-end"
              >
                <div className="md:col-span-4">
                  <select
                    value={rateTaskId}
                    onChange={(e) => {
                      setRateTaskId(e.target.value);
                      setRateSavedNotice(false);
                    }}
                    className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[12.5px]"
                  >
                    {completedTasks.map((t) => (
                      <option key={t.id} value={t.id}>
                        [{t.interaction_mode === 'baseline' ? 'Baseline' : 'VYRO-X'}] {t.title.slice(0, 42)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2"><label className="block text-[11px] text-apple-secondary">Effort: <strong>{effort}</strong></label><input type="range" min={1} max={7} value={effort} onChange={(e) => setEffort(Number(e.target.value))} className="w-full accent-[#0071E3]" /></div>
                <div className="md:col-span-2"><label className="block text-[11px] text-apple-secondary">Trust: <strong>{trust}</strong></label><input type="range" min={1} max={7} value={trust} onChange={(e) => setTrust(Number(e.target.value))} className="w-full accent-[#0071E3]" /></div>
                <div className="md:col-span-2"><label className="block text-[11px] text-apple-secondary">Control: <strong>{control}</strong></label><input type="range" min={1} max={7} value={control} onChange={(e) => setControl(Number(e.target.value))} className="w-full accent-[#0071E3]" /></div>
                <div className="md:col-span-2"><button type="submit" className="apple-pill-primary w-full py-1.5 text-[12px]">Record Rating</button></div>
              </form>
            </div>
          )}
        </section>

        {/* 14-Metric Comparison Table + Charts */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm lg:col-span-5">
            <h2 className="text-[16px] font-semibold">
              14-Metric Comparison ({isIllustrative ? 'Illustrative Preview' : 'Measured'})
            </h2>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-[12px]">
                <thead className="border-b border-apple-border text-apple-secondary">
                  <tr>
                    <th className="py-2 pr-2 font-medium">Metric</th>
                    <th className="py-2 pr-2 font-semibold text-apple-blue">VYRO-X</th>
                    <th className="py-2 font-medium">Baseline</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apple-border">
                  {metricRows.map((row) => (
                    <tr key={row.name}>
                      <td className="py-2 pr-2 text-apple-ink">{row.name}</td>
                      <td className="py-2 pr-2 font-semibold text-apple-blue">{row.v}</td>
                      <td className="py-2 text-apple-secondary">{row.b}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="space-y-5 lg:col-span-7">
            <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
              <h2 className="text-[15.5px] font-semibold">
                Human Experience Ratings (1–7 Scale · {isIllustrative ? 'Illustrative' : 'Measured'})
              </h2>
              <div className="mt-4 h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={scaleChartData} margin={{ top: 8, right: 12, left: -18, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(134,134,139,0.2)" />
                    <XAxis dataKey="metric" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <YAxis domain={[0, 7]} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: '8px', color: 'var(--text-primary)', fontSize: '12px' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="VYRO-X" fill="#0071E3" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="Baseline" fill="#86868B" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
              <h2 className="text-[15.5px] font-semibold">
                Reliability & Control Metrics (% · {isIllustrative ? 'Illustrative' : 'Measured'})
              </h2>
              <div className="mt-4 h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={reliabilityChartData} margin={{ top: 8, right: 12, left: -18, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(134,134,139,0.2)" />
                    <XAxis dataKey="metric" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                    <Tooltip contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: '8px', color: 'var(--text-primary)', fontSize: '12px' }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Bar dataKey="VYRO-X" fill="#0071E3" radius={[6, 6, 0, 0]} />
                    <Bar dataKey="Baseline" fill="#86868B" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>

        {/* SciPy Statistical Tests Table */}
        <section className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
          <h2 className="text-[16px] font-semibold">Statistical Analysis (Measured Local Sessions Only)</h2>
          <p className="mt-1 text-[12.5px] text-apple-secondary">
            Descriptive statistics (mean, SD, median, 95% CI) and two-group inference (Welch’s t-test,
            Mann-Whitney U, Cohen’s d) computed strictly when n ≥ 2 per group.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-[12px]">
              <thead className="border-b border-apple-border text-apple-secondary">
                <tr>
                  <th className="py-2 pr-3">Metric</th>
                  <th className="py-2 pr-3">VYRO-X (n / mean / SD)</th>
                  <th className="py-2 pr-3">Baseline (n / mean / SD)</th>
                  <th className="py-2 pr-3">Welch p / MWU p</th>
                  <th className="py-2">Cohen’s d / Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-border">
                {data.statistical_tests.map((st) => (
                  <tr key={st.metric}>
                    <td className="py-2.5 pr-3 font-medium">{st.metric}</td>
                    <td className="py-2.5 pr-3">
                      n={st.vyrox.n} · {st.vyrox.mean ?? '—'} {st.vyrox.std !== null ? `± ${st.vyrox.std}` : ''}
                    </td>
                    <td className="py-2.5 pr-3">
                      n={st.baseline.n} · {st.baseline.mean ?? '—'} {st.baseline.std !== null ? `± ${st.baseline.std}` : ''}
                    </td>
                    <td className="py-2.5 pr-3 font-mono text-[11.5px]">
                      {st.sufficient_data ? `${st.welch_t_p ?? '—'} / ${st.mann_whitney_p ?? '—'}` : 'Insufficient n'}
                    </td>
                    <td className="py-2.5 text-apple-secondary">
                      {st.sufficient_data ? `d = ${st.cohens_d ?? '—'}` : st.note}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Qualitative User Feedback & Methodology */}
        <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
          <section className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm lg:col-span-5">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-apple-blue" />
              <h2 className="text-[16px] font-semibold">Submit Qualitative Feedback</h2>
            </div>
            <form onSubmit={handleSubmitFeedback} className="mt-4 space-y-3 text-[13px]">
              <div className="grid grid-cols-2 gap-3">
                <select
                  value={fbCategory}
                  onChange={(e) => setFbCategory(e.target.value as typeof fbCategory)}
                  className="rounded-xl border border-apple-border bg-apple-bg px-3 py-1.5 text-[12.5px]"
                >
                  <option value="usability">Usability</option>
                  <option value="autonomy">Autonomy</option>
                  <option value="accuracy">Accuracy</option>
                  <option value="suggestion">Suggestion</option>
                  <option value="bug">Issue Report</option>
                  <option value="general">General</option>
                </select>
                <select
                  value={fbRating}
                  onChange={(e) => setFbRating(Number(e.target.value))}
                  className="rounded-xl border border-apple-border bg-apple-bg px-3 py-1.5 text-[12.5px]"
                >
                  {[5, 4, 3, 2, 1].map((r) => (
                    <option key={r} value={r}>{r} / 5 Stars</option>
                  ))}
                </select>
              </div>
              <textarea
                required
                rows={3}
                value={fbComment}
                onChange={(e) => {
                  setFbComment(e.target.value);
                  setFbSaved(false);
                }}
                placeholder="Share observations on control, transparency, interruption reliability, or UX..."
                className="w-full rounded-xl border border-apple-border bg-apple-bg p-3 text-[12.5px] outline-none focus:border-apple-blue"
              />
              <button type="submit" className="apple-pill-primary px-5 py-1.5 text-[12.5px]">
                Save Feedback
              </button>
              {fbSaved && <p className="text-[12px] text-emerald-600 dark:text-emerald-400">Feedback persisted to database.</p>}
            </form>
          </section>

          <section className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm lg:col-span-7">
            <div className="flex items-center gap-2">
              <Beaker className="h-4 w-4 text-apple-blue" />
              <h2 className="text-[16px] font-semibold">Evaluation Methodology & Limitations</h2>
            </div>
            <div className="mt-3 space-y-3 text-[12.5px] text-apple-secondary">
              <p><strong className="text-apple-ink">Baseline: </strong>{data.methodology.baseline_definition}</p>
              <p><strong className="text-apple-blue">VYRO-X: </strong>{data.methodology.proposed_model_definition}</p>
              <div className="rounded-xl border border-amber-500/25 bg-amber-50/50 p-3.5 dark:bg-amber-950/20">
                <p className="font-semibold text-amber-900 dark:text-amber-200">Known Limitations</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-amber-900/90 dark:text-amber-200/90">
                  {data.methodology.known_limitations.map((lim) => (
                    <li key={lim}>{lim}</li>
                  ))}
                </ul>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};
