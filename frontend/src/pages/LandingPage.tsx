import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Brain,
  Check,
  ChevronRight,
  Command,
  Cpu,
  Eye,
  GitBranch,
  History,
  Layers,
  Lock,
  Pause,
  RotateCcw,
  Shield,
  Sliders,
  Square,
  Unlock,
} from 'lucide-react';
import { VyroLogo } from '../components/VyroLogo';
import { useAuth } from '../context/AuthContext';

export const LandingPage: React.FC = () => {
  const { user } = useAuth();
  const [previewLocked, setPreviewLocked] = useState(true);
  const [previewAutonomy, setPreviewAutonomy] = useState<'supervised' | 'balanced' | 'higher_autonomy'>('balanced');

  const workspaceTarget = user ? '/workspace' : '/register';

  const autonomySpec = {
    supervised: {
      title: 'Supervised Mode',
      summary: 'Every execution step pauses for explicit human confirmation before running.',
      low: 'Approval Required',
      medium: 'Approval Required',
      high: 'Mandatory Gate',
    },
    balanced: {
      title: 'Balanced Adaptive Mode',
      summary:
        'Low-risk steps proceed with live interrupt active; medium and high-risk actions pause. Automatically tightens check-ins after edits or interrupts.',
      low: 'Auto-Proceeds (Interruptible)',
      medium: 'Approval Required',
      high: 'Mandatory Gate',
    },
    higher_autonomy: {
      title: 'Higher Autonomy Mode',
      summary:
        'Low and medium steps stream continuously while remaining interruptible. High-impact actions remain strictly gated behind human approval.',
      low: 'Auto-Proceeds',
      medium: 'Auto-Proceeds (Adaptive)',
      high: 'Mandatory Gate',
    },
  }[previewAutonomy];

  return (
    <div className="bg-apple-bg text-apple-ink">
      {/* ================================================================
          HERO — Linear / Vercel Product-Led Precision
      ================================================================ */}
      <section className="relative border-b border-apple-border px-4 pb-20 pt-16 sm:px-6 sm:pt-24">
        <div className="vyrox-grid-bg pointer-events-none absolute inset-0 opacity-40" />
        <div className="relative mx-auto max-w-[1160px]">
          <div className="max-w-[740px]">
            <div className="inline-flex items-center gap-2 rounded-md border border-apple-border bg-apple-surface px-2.5 py-1 text-[11.5px] font-medium text-apple-secondary">
              <span className="h-1.5 w-1.5 rounded-full bg-apple-blue" />
              <span>VYRO-X · Human Intelligence. Agent Evolution.</span>
            </div>

            <h1 className="apple-display mt-5 text-[42px] text-apple-ink sm:text-[62px]">
              Work with AI.
              <br />
              Stay in Control.
            </h1>

            <p className="apple-subhead mt-5 max-w-[600px] text-[17px] text-apple-secondary sm:text-[19px]">
              An intelligent collaborative workspace where humans guide, supervise, and collaborate
              with adaptive AI agents — with live plan editing, safe mid-run interrupts, and
              persistent checkpoints.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to={workspaceTarget} className="apple-pill-primary px-5 py-2.5 text-[14px]">
                <span>{user ? 'Open Workspace' : 'Explore Workspace'}</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#product" className="apple-pill-secondary px-5 py-2.5 text-[14px]">
                <span>See How It Works</span>
              </a>
              <span className="hidden items-center gap-1.5 pl-2 text-[12px] text-apple-tertiary sm:inline-flex">
                <Command className="h-3.5 w-3.5" /> Press <span className="vyrox-kbd">⌘K</span> inside workspace
              </span>
            </div>
          </div>

          {/* Realistic VYRO-X Product Preview (Sidebar + Split-Pane + Command Chrome) */}
          <div className="mt-14 overflow-hidden rounded-xl border border-apple-borderStrong bg-apple-sidebar shadow-apple-lg">
            {/* Top Window Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-apple-border bg-apple-surface px-4 py-2.5">
              <div className="flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full bg-neutral-500/40" />
                <span className="h-2.5 w-2.5 rounded-full bg-neutral-500/40" />
                <span className="h-2.5 w-2.5 rounded-full bg-neutral-500/40" />
                <span className="ml-2 font-mono text-[11.5px] text-apple-secondary">
                  vyro-x / workspace / distributed-consensus-report
                </span>
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span className="inline-flex items-center gap-1.5 rounded-md bg-apple-blue/15 px-2 py-0.5 font-medium text-apple-blue">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-apple-blue" />
                  Step 3/5 · Running
                </span>
                <span className="inline-flex items-center gap-1 rounded-md border border-orange-500/30 bg-orange-500/10 px-2 py-0.5 font-medium text-orange-500">
                  <Square className="h-2.5 w-2.5 fill-current" /> Interrupt
                </span>
                <span className="hidden items-center gap-1 rounded-md border border-apple-border bg-apple-elevated px-2 py-0.5 font-mono text-apple-secondary sm:inline-flex">
                  <History className="h-2.5 w-2.5" /> v3 checkpoint
                </span>
              </div>
            </div>

            {/* App Grid: Compact Sidebar + Split Workspace */}
            <div className="grid grid-cols-1 lg:grid-cols-12">
              {/* Miniature Sidebar */}
              <div className="hidden border-r border-apple-border bg-apple-sidebar p-3 lg:col-span-2 lg:block">
                <div className="mb-3 flex items-center justify-between rounded-md border border-apple-border bg-apple-surface px-2 py-1 text-[11px] text-apple-tertiary">
                  <span>Search...</span>
                  <span className="vyrox-kbd">⌘K</span>
                </div>
                <div className="space-y-1 text-[12px]">
                  {['Workspace', 'History', 'Analytics & ML', 'Evaluation', 'Settings'].map((nav, i) => (
                    <div
                      key={nav}
                      className={`rounded-md px-2 py-1 ${
                        i === 0
                          ? 'bg-apple-hover font-medium text-apple-ink'
                          : 'text-apple-tertiary'
                      }`}
                    >
                      {nav}
                    </div>
                  ))}
                </div>
              </div>

              {/* Left Pane: Live Execution Plan */}
              <div className="border-b border-apple-border bg-apple-bg p-4 lg:col-span-4 lg:border-b-0 lg:border-r">
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-mono text-[10.5px] uppercase tracking-wider text-apple-tertiary">
                    Live Execution Plan
                  </span>
                  <span className="text-[11px] font-medium text-apple-blue">ML Advisor: Balanced</span>
                </div>
                <div className="space-y-2">
                  <div className="rounded-lg border border-apple-border border-l-[3px] border-l-emerald-500/75 bg-apple-elevated p-2.5">
                    <div className="flex items-center justify-between gap-2 text-[12.5px] font-medium">
                      <span>1. Scope & Research Questions</span>
                      <span className="text-[10.5px] text-emerald-500">Done</span>
                    </div>
                    <p className="mt-1 flex items-center gap-1 text-[11px] text-apple-tertiary">
                      <Lock className="h-3 w-3 text-apple-blue" /> Locked by human
                    </p>
                  </div>

                  <div className="rounded-lg border border-apple-border border-l-[3px] border-l-emerald-500/75 bg-apple-elevated p-2.5">
                    <div className="flex items-center justify-between gap-2 text-[12.5px] font-medium">
                      <span>2. Core Architecture Landscape</span>
                      <span className="text-[10.5px] text-emerald-500">Done</span>
                    </div>
                  </div>

                  <div className="rounded-lg border border-apple-blue/40 border-l-[3px] border-l-apple-blue bg-apple-blue/[0.05] p-2.5">
                    <div className="flex items-center justify-between gap-2 text-[12.5px] font-semibold">
                      <span>3. Comparative Trade-Off Matrix</span>
                      <span className="font-mono text-[10.5px] text-apple-blue">Stage 2/3</span>
                    </div>
                    <p className="mt-1 text-[11.5px] text-apple-secondary">
                      Evaluating Raft vs. Paxos tail-latency bounds with your mid-flight directive...
                    </p>
                  </div>

                  <div className="rounded-lg border border-amber-500/35 border-l-[3px] border-l-amber-500 bg-amber-500/[0.05] p-2.5">
                    <div className="flex items-center justify-between gap-2 text-[12.5px] font-medium">
                      <span>4. Implementation & Safeguards</span>
                      <span className="text-[10.5px] text-amber-500">High Risk Gate</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Pane: Shared Collaborative Artifact */}
              <div className="bg-apple-bg p-4 lg:col-span-6">
                <div className="mb-3 flex items-center justify-between">
                  <span className="font-mono text-[10.5px] uppercase tracking-wider text-apple-tertiary">
                    Shared Collaborative Artifact
                  </span>
                  <span className="rounded-md bg-apple-blue/12 px-2 py-0.5 text-[10.5px] font-medium text-apple-blue">
                    Co-Authored · Diff Tracked
                  </span>
                </div>

                <div className="space-y-3">
                  <div className="rounded-lg border border-apple-border border-l-[3px] border-l-apple-blue bg-apple-elevated p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-[13.5px] font-semibold">1. Scope & Research Questions</h3>
                      <span className="font-mono text-[10.5px] text-apple-tertiary">v2 · Step 1</span>
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-apple-secondary">
                      Examines fault-tolerant state replication for latency-sensitive control planes,
                      focusing on deterministic recovery and measurable RTO/RPO bounds.
                    </p>
                    <div className="mt-2 rounded-md border-l-2 border-emerald-500 bg-emerald-500/10 px-2.5 py-1.5 font-mono text-[11px] text-emerald-600 dark:text-emerald-300">
                      + Human edit: Include cross-AZ quorum recovery benchmarks under 150ms.
                    </div>
                  </div>

                  <div className="rounded-lg border border-apple-border border-l-[3px] border-l-neutral-500/50 bg-apple-elevated p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-[13.5px] font-semibold">2. Core Architecture Landscape</h3>
                      <span className="font-mono text-[10.5px] text-apple-tertiary">AI · Step 2</span>
                    </div>
                    <p className="mt-1.5 text-[12.5px] leading-relaxed text-apple-secondary">
                      Separates control-plane state machines, cooperative micro-stage execution,
                      persistent relational checkpoints, and real-time Server-Sent Event streams.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          PRODUCT ARCHITECTURE — Prompt-and-Wait vs VYRO-X
      ================================================================ */}
      <section id="product" className="border-b border-apple-border px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-[1160px]">
          <div className="max-w-[640px]">
            <p className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-apple-blue">
              Why VYRO-X
            </p>
            <h2 className="apple-headline mt-2 text-[30px] sm:text-[38px]">
              Built for continuous human supervision, not blind prompting.
            </h2>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-apple-border bg-apple-surface p-6">
              <p className="font-mono text-[11px] uppercase tracking-wider text-apple-tertiary">
                Conventional Prompt-and-Wait
              </p>
              <ul className="mt-4 space-y-3 text-[13.5px] text-apple-secondary">
                <li>• Single opaque pass with no visible plan or rationale before running.</li>
                <li>• Mid-task course corrections discard completed work and force restarts.</li>
                <li>• No versioned checkpoints, state rollback, or AI-vs-human authorship diffs.</li>
              </ul>
            </div>

            <div className="rounded-xl border border-apple-blue/35 bg-apple-elevated p-6">
              <p className="font-mono text-[11px] uppercase tracking-wider text-apple-blue">
                VYRO-X Collaborative Execution
              </p>
              <ul className="mt-4 space-y-3 text-[13.5px] text-apple-ink">
                <li className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-apple-blue" />
                  <span>Inspectable, editable, lockable multi-step plan with risk tiers and rationale.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-apple-blue" />
                  <span>Safe mid-execution interrupts, persistent checkpoints, and step-skipping resume.</span>
                </li>
                <li className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-apple-blue" />
                  <span>Shared artifact co-editing with section revision restore and adaptive autonomy.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          INTELLIGENT PLANNING — Interactive Lock Invariant Demo
      ================================================================ */}
      <section id="planning" className="border-b border-apple-border px-4 py-20 sm:px-6">
        <div className="mx-auto grid max-w-[1160px] grid-cols-1 items-center gap-10 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <p className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-apple-blue">
              Plan & Control
            </p>
            <h2 className="apple-headline mt-2 text-[28px] sm:text-[36px]">
              Edit any step. Lock critical invariants.
            </h2>
            <p className="mt-3 text-[15px] leading-relaxed text-apple-secondary">
              Shape the agent’s execution plan before or during a run. Locked steps are enforced
              server-side — agent replanning preserves them verbatim while adapting only unlocked
              downstream steps.
            </p>
            <div className="mt-6 grid grid-cols-2 gap-2.5 text-[12.5px] text-apple-ink">
              {['Inline step editing', 'Server-enforced locks', 'Reject & propose alternative', 'Mid-flight instructions'].map(
                (item) => (
                  <div
                    key={item}
                    className="flex items-center gap-2 rounded-lg border border-apple-border bg-apple-surface px-3 py-2"
                  >
                    <Check className="h-3.5 w-3.5 text-apple-blue" />
                    <span>{item}</span>
                  </div>
                ),
              )}
            </div>
          </div>

          <div className="lg:col-span-7">
            <div className="rounded-xl border border-apple-border bg-apple-surface p-5">
              <div className="mb-3 flex items-center justify-between">
                <span className="font-mono text-[11px] uppercase tracking-wider text-apple-tertiary">
                  Interactive Step Lock Preview
                </span>
                <button
                  type="button"
                  onClick={() => setPreviewLocked((v) => !v)}
                  className="inline-flex items-center gap-1.5 rounded-md border border-apple-borderStrong bg-apple-elevated px-3 py-1 text-[12px] font-medium text-apple-ink transition hover:border-apple-blue"
                >
                  {previewLocked ? (
                    <>
                      <Lock className="h-3.5 w-3.5 text-apple-blue" /> Locked
                    </>
                  ) : (
                    <>
                      <Unlock className="h-3.5 w-3.5 text-apple-tertiary" /> Unlocked
                    </>
                  )}
                </button>
              </div>
              <div className="rounded-lg border border-apple-border bg-apple-elevated p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[14px] font-semibold">Step 1 · Scope & Evaluation Criteria</span>
                  <span
                    className={`rounded-md px-2 py-0.5 font-mono text-[10.5px] font-medium ${
                      previewLocked
                        ? 'bg-apple-blue/15 text-apple-blue'
                        : 'bg-apple-surface text-apple-secondary'
                    }`}
                  >
                    {previewLocked ? 'IMMUTABLE' : 'REPLAN-ELIGIBLE'}
                  </span>
                </div>
                <p className="mt-2 text-[13px] leading-relaxed text-apple-secondary">
                  Define quorum invariants, measurable p99 tail-latency bounds (&lt;25ms), and
                  failure-domain boundaries before evaluating implementations.
                </p>
                <p className="mt-3 rounded-md bg-apple-surface px-3 py-2 text-[12px] text-apple-tertiary">
                  {previewLocked
                    ? 'Protected: Replan preserves this step verbatim and updates only unlocked pending steps.'
                    : 'Unlocked: Editable directly or eligible for agent revision during Replan.'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          HUMAN APPROVAL & ADAPTIVE AUTONOMY
      ================================================================ */}
      <section id="autonomy" className="border-b border-apple-border px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-[1160px]">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div className="max-w-[620px]">
              <p className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-apple-blue">
                Adaptive Autonomy & Safety
              </p>
              <h2 className="apple-headline mt-2 text-[28px] sm:text-[36px]">
                Calibrated supervision with hard safety invariants.
              </h2>
              <p className="mt-2.5 text-[14.5px] text-apple-secondary">
                Choose your oversight mode or let VYRO-X’s behavioural policy and ML Supervision
                Advisor recommend adjustments. High-impact actions remain gated unconditionally.
              </p>
            </div>

            <div className="inline-flex rounded-lg border border-apple-border bg-apple-surface p-1">
              {(
                [
                  { id: 'supervised', label: 'Supervised' },
                  { id: 'balanced', label: 'Balanced' },
                  { id: 'higher_autonomy', label: 'Higher Autonomy' },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setPreviewAutonomy(tab.id)}
                  className={`rounded-md px-3.5 py-1.5 text-[12.5px] font-medium transition ${
                    previewAutonomy === tab.id
                      ? 'bg-apple-elevated text-apple-ink shadow-apple-sm'
                      : 'text-apple-secondary hover:text-apple-ink'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          <div className="mt-6 rounded-xl border border-apple-border bg-apple-surface p-6">
            <h3 className="text-[18px] font-semibold">{autonomySpec.title}</h3>
            <p className="mt-1 text-[13.5px] text-apple-secondary">{autonomySpec.summary}</p>
            <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
              {[
                { label: 'Low-Risk Steps', value: autonomySpec.low, tone: 'text-emerald-500' },
                { label: 'Medium-Risk Steps', value: autonomySpec.medium, tone: 'text-amber-500' },
                { label: 'High-Impact Actions', value: autonomySpec.high, tone: 'text-apple-blue' },
              ].map((row) => (
                <div key={row.label} className="rounded-lg border border-apple-border bg-apple-elevated p-4">
                  <p className="font-mono text-[10.5px] uppercase tracking-wider text-apple-tertiary">
                    {row.label}
                  </p>
                  <p className={`mt-1.5 text-[14px] font-semibold ${row.tone}`}>{row.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ================================================================
          ARCHITECTURE & CAPABILITIES GRID
      ================================================================ */}
      <section id="architecture" className="border-b border-apple-border px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-[1160px]">
          <p className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-apple-blue">
            Platform Architecture
          </p>
          <h2 className="apple-headline mt-2 text-[28px] sm:text-[36px]">
            Engineered for real state reliability.
          </h2>

          <div className="mt-8 grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { icon: Pause, title: 'Cooperative Mid-Run Interrupts', text: 'Stops scheduling immediately, finishes atomic commits cleanly, and saves partial progress.' },
              { icon: RotateCcw, title: 'Persistent Checkpoints & Rollback', text: 'Compare any two execution snapshots and restore safely with pre-rollback protection.' },
              { icon: Eye, title: 'Real-Time SSE Telemetry', text: 'Live stage-by-stage agent feedback synced continuously with persisted database state.' },
              { icon: Layers, title: '17 Relational Tables + Alembic', text: 'SQLAlchemy 2.x schema with PostgreSQL production support, SQLite WAL fallback, and session revocation.' },
              { icon: Brain, title: 'Reproducible ML Supervision', text: 'Advisory supervision model trained via stratified CV with transparent synthetic provenance.' },
              { icon: Sliders, title: '14-Metric Scientific Evaluation', text: 'Paired Prompt-and-Wait vs. VYRO-X runner with SciPy statistical testing and strict provenance tags.' },
            ].map((item) => (
              <div key={item.title} className="rounded-xl border border-apple-border bg-apple-elevated p-5">
                <item.icon className="h-4 w-4 text-apple-blue" />
                <h3 className="mt-3 text-[15px] font-semibold">{item.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-apple-secondary">{item.text}</p>
              </div>
            ))}
          </div>

          {/* Compact Final CTA */}
          <div className="mt-14 flex flex-wrap items-center justify-between gap-6 rounded-xl border border-apple-borderStrong bg-apple-surface p-7">
            <div>
              <h2 className="apple-headline text-[24px] sm:text-[28px]">
                Ready to collaborate with full control?
              </h2>
              <p className="mt-1.5 text-[14px] text-apple-secondary">
                Launch a research task, interrupt mid-execution, refine the plan, and resume from
                your saved checkpoint.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <Link to={workspaceTarget} className="apple-pill-primary px-5 py-2.5 text-[13.5px]">
                <span>{user ? 'Open Workspace' : 'Create Account'}</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/evaluation" className="apple-pill-secondary px-4 py-2.5 text-[13.5px]">
                <span>Evaluation Suite</span>
                <ChevronRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="px-4 py-7 text-[12px] text-apple-tertiary sm:px-6">
        <div className="mx-auto flex max-w-[1160px] flex-wrap items-center justify-between gap-4">
          <VyroLogo size="sm" />
          <div className="flex items-center gap-4">
            <span className="inline-flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-apple-blue" /> Human-in-the-Loop Safety Enforced
            </span>
            <span className="inline-flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5" /> VYRO-X
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
};
