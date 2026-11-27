import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { BarChart3, Brain, Info, RefreshCw, Sliders } from 'lucide-react';
import { api } from '../services/api';
import type { AnalyticsData, MLStatusResponse } from '../types/hai';

export const AnalyticsPage: React.FC = () => {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [mlStatus, setMlStatus] = useState<MLStatusResponse | null>(null);
  const [retraining, setRetraining] = useState(false);
  const [retrainMessage, setRetrainMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [an, ml] = await Promise.all([api.getAnalytics(), api.getMlStatus()]);
      setData(an);
      setMlStatus(ml);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrainMessage(null);
    try {
      await api.retrainModel();
      await loadAll();
      setRetrainMessage('Model retrained on synthetic demonstration dataset and activated.');
    } catch {
      setRetrainMessage('Retraining rate limit or error encountered. Please retry shortly.');
    } finally {
      setRetraining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-3rem)] items-center justify-center bg-apple-surface text-[14px] text-apple-secondary">
        Calculating analytics from persisted VYRO-X records...
      </div>
    );
  }

  const report = mlStatus?.latest_report;
  const s = data?.summary;

  return (
    <div className="min-h-[calc(100vh-3rem)] bg-apple-surface px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1280px] space-y-6">
        <div>
          <p className="text-[12px] font-semibold uppercase tracking-[0.12em] text-apple-blue">
            VYRO-X Intelligence & Telemetry
          </p>
          <h1 className="apple-headline mt-1 text-[32px]">Agent Analytics & ML Supervision Model</h1>
          <p className="mt-1 text-[14px] text-apple-secondary">
            Real interaction metrics computed strictly from persisted database records, alongside
            reproducible Adaptive Supervision ML evaluation and live monitoring.
          </p>
        </div>

        {/* Workspace Interaction Analytics */}
        {!data || !data.has_data || !s ? (
          <div className="rounded-xl border border-apple-border bg-apple-elevated p-8 text-center shadow-apple-sm">
            <BarChart3 className="mx-auto h-9 w-9 text-apple-blue" />
            <h2 className="mt-3 text-[20px] font-semibold">No Recorded Workspace Interactions Yet</h2>
            <p className="mx-auto mt-1.5 max-w-[540px] text-[13.5px] text-apple-secondary">
              VYRO-X never fabricates telemetry. Run at least one task in the Workspace to view live
              approval rates, modification frequency, interventions, and adaptive autonomy shifts.
            </p>
            <Link to="/workspace" className="apple-pill-primary mt-5 px-5 py-2 text-[13.5px]">
              Launch Workspace
            </Link>
          </div>
        ) : (
          <>
            <div className="flex items-start gap-2.5 rounded-2xl border border-apple-border bg-apple-elevated px-4 py-3 text-[12.5px] text-apple-secondary">
              <Info className="mt-0.5 h-4 w-4 shrink-0 text-apple-blue" />
              <span>{data.epistemic_note}</span>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { label: 'Task Completion Rate', value: `${s.task_completion_rate}%`, sub: `${s.completed_tasks} of ${s.total_tasks} tasks completed` },
                { label: 'Approval Rate', value: `${s.approval_rate}%`, sub: `${s.approvals_count} approvals · ${s.rejections_count} rejections` },
                { label: 'Rejection Rate', value: `${s.rejection_rate}%`, sub: 'Triggers alternative proposals & caution' },
                { label: 'Modification Frequency', value: `${s.modification_frequency_per_task}/task`, sub: `${s.total_modifications} total plan + artifact edits` },
                { label: 'Intervention Frequency', value: `${s.intervention_frequency_per_task}/task`, sub: `${s.total_interventions} total steering actions` },
                { label: 'Autonomy Adjustments', value: `${s.autonomy_adjustments_count}`, sub: 'Automatic policy threshold shifts' },
              ].map((kpi) => (
                <div
                  key={kpi.label}
                  className="rounded-lg border border-apple-border bg-apple-elevated p-5 shadow-apple-sm"
                >
                  <p className="text-[12px] font-medium text-apple-secondary">{kpi.label}</p>
                  <p className="mt-2 text-[32px] font-semibold tracking-tight text-apple-ink">
                    {kpi.value}
                  </p>
                  <p className="mt-1 text-[12px] text-apple-tertiary">{kpi.sub}</p>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
                <h2 className="text-[16px] font-semibold">Interaction Event Breakdown</h2>
                <p className="mt-0.5 text-[12.5px] text-apple-secondary">
                  Persisted human-agent control actions across your workspace.
                </p>
                <div className="mt-5 h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.event_distribution} margin={{ top: 10, right: 12, left: -16, bottom: 24 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(134,134,139,0.2)" />
                      <XAxis dataKey="category" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} angle={-20} textAnchor="end" interval={0} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: '8px', color: 'var(--text-primary)', fontSize: '12px' }} />
                      <Bar dataKey="count" name="Recorded Events" fill="#0071E3" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
                <h2 className="text-[16px] font-semibold">Historical Interaction Patterns</h2>
                <p className="mt-0.5 text-[12.5px] text-apple-secondary">
                  Daily approvals, modifications, and mid-run interventions.
                </p>
                <div className="mt-5 h-72 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.timeline} margin={{ top: 10, right: 12, left: -16, bottom: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(134,134,139,0.2)" />
                      <XAxis dataKey="date" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <YAxis allowDecimals={false} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                      <Tooltip contentStyle={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: '8px', color: 'var(--text-primary)', fontSize: '12px' }} />
                      <Legend wrapperStyle={{ fontSize: 12 }} />
                      <Line type="monotone" dataKey="approvals" name="Approvals" stroke="#0071E3" strokeWidth={2} />
                      <Line type="monotone" dataKey="modifications" name="Modifications" stroke="#5E5CE6" strokeWidth={2} />
                      <Line type="monotone" dataKey="interventions" name="Interventions" stroke="#FF9F0A" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ==============================================================
            TRAINED ML MODEL PERFORMANCE & MONITORING
        ============================================================== */}
        <section className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Brain className="h-4 w-4 text-apple-blue" />
                <h2 className="text-[17px] font-semibold">Adaptive Supervision Prediction Model</h2>
                <span className="rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800 dark:bg-amber-950/50 dark:text-amber-300">
                  {mlStatus?.dataset_provenance || 'SYNTHETIC_DEMO_DATASET'}
                </span>
              </div>
              <p className="mt-1 text-[12.5px] text-apple-secondary">
                {mlStatus?.provenance_disclosure}
              </p>
            </div>

            <button
              type="button"
              disabled={retraining}
              onClick={handleRetrain}
              className="inline-flex items-center gap-1.5 rounded-full border border-apple-border bg-apple-bg px-4 py-1.5 text-[12.5px] font-medium hover:border-apple-blue disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${retraining ? 'animate-spin' : ''}`} />
              <span>{retraining ? 'Retraining Pipeline...' : 'Run Reproducible Retrain'}</span>
            </button>
          </div>

          {retrainMessage && (
            <p className="mt-2 text-[12.5px] font-medium text-apple-blue">{retrainMessage}</p>
          )}

          {report ? (
            <div className="mt-5 space-y-5">
              {/* Top ML KPIs */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {[
                  { label: 'Selected Model', value: report.selected_model.algorithm.replace('_', ' ') },
                  { label: 'Test Macro-F1', value: report.test_evaluation.selected_model.f1_macro.toFixed(4) },
                  { label: 'Rule Baseline F1', value: report.test_evaluation.rule_based_baseline.f1_macro.toFixed(4) },
                  { label: 'Test Accuracy', value: `${(report.test_evaluation.selected_model.accuracy * 100).toFixed(1)}%` },
                  { label: 'ROC-AUC (OvR)', value: report.test_evaluation.selected_model.roc_auc_ovr?.toFixed(4) ?? '—' },
                  { label: 'Mean Latency', value: `${report.selected_model.inference_latency.mean_ms} ms` },
                ].map((m) => (
                  <div key={m.label} className="rounded-2xl border border-apple-border bg-apple-bg p-3.5">
                    <p className="text-[11px] font-medium text-apple-secondary">{m.label}</p>
                    <p className="mt-1 text-[17px] font-semibold capitalize text-apple-ink">{m.value}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                {/* Class-wise Performance */}
                <div className="rounded-2xl border border-apple-border bg-apple-bg p-4">
                  <h3 className="text-[13.5px] font-semibold">
                    Held-Out Test Class-Wise Performance (n={report.splits.test_count})
                  </h3>
                  <table className="mt-3 w-full text-left text-[12px]">
                    <thead className="border-b border-apple-border text-apple-secondary">
                      <tr>
                        <th className="py-1.5">Class</th>
                        <th className="py-1.5">Precision</th>
                        <th className="py-1.5">Recall</th>
                        <th className="py-1.5">F1-Score</th>
                        <th className="py-1.5">Support</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-apple-border">
                      {Object.entries(report.test_evaluation.selected_model.class_report).map(([cls, stats]) => (
                        <tr key={cls}>
                          <td className="py-2 font-medium capitalize">{cls.replace('_', ' ')}</td>
                          <td className="py-2">{stats.precision.toFixed(3)}</td>
                          <td className="py-2">{stats.recall.toFixed(3)}</td>
                          <td className="py-2 font-semibold text-apple-blue">{stats.f1_score.toFixed(3)}</td>
                          <td className="py-2 text-apple-secondary">{stats.support}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Confusion Matrix & Monitoring */}
                <div className="rounded-2xl border border-apple-border bg-apple-bg p-4">
                  <h3 className="text-[13.5px] font-semibold">
                    Test Confusion Matrix & Live Inference Monitoring
                  </h3>
                  <table className="mt-3 w-full text-center text-[11.5px]">
                    <thead className="border-b border-apple-border text-apple-secondary">
                      <tr>
                        <th className="py-1.5 text-left">True \ Pred</th>
                        <th>Supervised</th>
                        <th>Balanced</th>
                        <th>Higher Auto</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-apple-border">
                      {report.test_evaluation.selected_model.confusion_matrix.map((row, rIdx) => (
                        <tr key={rIdx}>
                          <td className="py-1.5 text-left font-medium capitalize">
                            {report.test_evaluation.selected_model.classes[rIdx]?.replace('_', ' ')}
                          </td>
                          {row.map((cell, cIdx) => (
                            <td
                              key={cIdx}
                              className={`py-1.5 font-mono ${
                                rIdx === cIdx ? 'font-bold text-apple-blue' : 'text-apple-secondary'
                              }`}
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <div className="mt-3 flex flex-wrap gap-3 border-t border-apple-border pt-3 text-[11.5px] text-apple-secondary">
                    <span>Version: <strong className="font-mono text-apple-ink">{report.selected_model.model_version}</strong></span>
                    <span>Live Predictions: <strong className="text-apple-ink">{mlStatus?.monitoring.total_predictions_logged ?? 0}</strong></span>
                    {mlStatus?.monitoring.user_agreement_rate_pct !== null && mlStatus?.monitoring.user_agreement_rate_pct !== undefined && (
                      <span>User Agreement: <strong className="text-apple-ink">{mlStatus.monitoring.user_agreement_rate_pct}%</strong></span>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-[13px] text-apple-secondary">
              No trained model artifact found. Click <strong>Run Reproducible Retrain</strong> to train and evaluate the model.
            </p>
          )}
        </section>

        {/* Adaptive Policy Signal Log */}
        {data && data.recent_autonomy_signals.length > 0 && (
          <div className="rounded-xl border border-apple-border bg-apple-elevated p-6 shadow-apple-sm">
            <div className="flex items-center gap-2">
              <Sliders className="h-4 w-4 text-apple-blue" />
              <h2 className="text-[16px] font-semibold">Adaptive Autonomy Behavioural Signal Log</h2>
            </div>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-[12.5px]">
                <thead className="border-b border-apple-border text-apple-secondary">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Signal</th>
                    <th className="py-2 pr-4 font-medium">Risk</th>
                    <th className="py-2 pr-4 font-medium">Policy Transition</th>
                    <th className="py-2 pr-4 font-medium">Explanation</th>
                    <th className="py-2 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-apple-border">
                  {data.recent_autonomy_signals.map((sig) => (
                    <tr key={sig.id}>
                      <td className="py-2.5 pr-4 font-mono text-[11.5px] font-semibold text-apple-blue">
                        {sig.signal_type}
                      </td>
                      <td className="py-2.5 pr-4 capitalize text-apple-secondary">{sig.step_risk_level}</td>
                      <td className="py-2.5 pr-4 font-medium">
                        {sig.previous_caution} → {sig.new_caution}
                      </td>
                      <td className="py-2.5 pr-4 text-apple-secondary">{sig.reason}</td>
                      <td className="py-2.5 text-[11.5px] text-apple-tertiary">
                        {sig.created_at ? new Date(sig.created_at).toLocaleTimeString() : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
