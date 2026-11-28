import React, { useState } from 'react';
import {
  Check,
  Download,
  Edit3,
  FileText,
  GitCompare,
  History,
  Link2,
  Plus,
  Star,
} from 'lucide-react';
import { api } from '../services/api';
import { ResearchPanel } from './ResearchPanel';
import type {
  ArtifactRevision,
  ArtifactSection,
  ArtifactSectionDiff,
  CitationStyle,
  Claim,
  ExecutionStep,
  StepSource,
  TaskDetail,
} from '../types/hai';

interface SharedArtifactPanelProps {
  task: TaskDetail;
  highlightedStepId: string | null;
  onHighlightStep: (stepId: string | null) => void;
  onEditSection: (sectionId: string, heading: string, content: string) => Promise<void>;
  onAddSection: (heading: string, content: string) => Promise<void>;
  onRatingSubmitted?: () => void;
}

const AUTHORSHIP_BADGE: Record<string, { label: string; style: string }> = {
  ai: {
    label: 'AI Generated',
    style: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
  collaborative: {
    label: 'Co-Authored (AI + Human)',
    style: 'bg-blue-50 text-[#0071E3] dark:bg-blue-950/60 dark:text-[#2997FF]',
  },
  human: {
    label: 'Human Authored',
    style: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
  },
};

/** Clean lightweight Markdown renderer supporting headings, tables, blockquotes, lists & inline bold/code */
const MarkdownBlock: React.FC<{ content: string }> = ({ content }) => {
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let i = 0;

  const renderInline = (text: string) => {
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={idx} className="font-semibold text-apple-ink">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code
            key={idx}
            className="rounded bg-apple-surface px-1.5 py-0.5 font-mono text-[12px] text-apple-ink"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        return (
          <em key={idx} className="italic">
            {part.slice(1, -1)}
          </em>
        );
      }
      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  };

  while (i < lines.length) {
    const line = lines[i];

    // Pipe Table
    if (line.trim().startsWith('|') && i + 1 < lines.length && lines[i + 1].trim().startsWith('|')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        tableLines.push(lines[i]);
        i++;
      }
      const rows = tableLines
        .filter((l) => !/^\|[\s:|-]+\|$/.test(l.trim()))
        .map((l) =>
          l
            .trim()
            .replace(/^\||\|$/g, '')
            .split('|')
            .map((cell) => cell.trim()),
        );
      if (rows.length > 0) {
        elements.push(
          <div key={`tbl-${i}`} className="my-3 overflow-x-auto rounded-xl border border-apple-border">
            <table className="w-full text-left text-[12.5px]">
              <thead className="bg-apple-surface text-apple-ink">
                <tr>
                  {rows[0].map((head, hi) => (
                    <th key={hi} className="px-3 py-2 font-semibold">
                      {renderInline(head)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-apple-border">
                {rows.slice(1).map((r, ri) => (
                  <tr key={ri}>
                    {r.map((cell, ci) => (
                      <td key={ci} className="px-3 py-2 text-apple-secondary">
                        {renderInline(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>,
        );
      }
      continue;
    }

    if (line.startsWith('#### ')) {
      elements.push(
        <h4 key={i} className="mt-4 mb-1.5 text-[14.5px] font-semibold text-apple-ink">
          {renderInline(line.slice(5))}
        </h4>,
      );
    } else if (line.startsWith('### ')) {
      elements.push(
        <h3 key={i} className="mt-4 mb-1.5 text-[15.5px] font-semibold text-apple-ink">
          {renderInline(line.slice(4))}
        </h3>,
      );
    } else if (line.startsWith('## ')) {
      elements.push(
        <h2 key={i} className="mt-4 mb-2 text-[17px] font-semibold text-apple-ink">
          {renderInline(line.slice(3))}
        </h2>,
      );
    } else if (line.startsWith('> ')) {
      elements.push(
        <blockquote
          key={i}
          className="my-1.5 border-l-2 border-apple-blue bg-blue-50/40 px-3 py-1.5 text-[12.5px] text-apple-ink dark:bg-blue-950/25"
        >
          {renderInline(line.slice(2))}
        </blockquote>,
      );
    } else if (line.trim().startsWith('- ')) {
      elements.push(
        <li key={i} className="ml-5 list-disc text-[13.5px] leading-relaxed text-apple-secondary">
          {renderInline(line.trim().slice(2))}
        </li>,
      );
    } else if (/^\d+\.\s/.test(line.trim())) {
      elements.push(
        <li key={i} className="ml-5 list-decimal text-[13.5px] leading-relaxed text-apple-secondary">
          {renderInline(line.trim().replace(/^\d+\.\s/, ''))}
        </li>,
      );
    } else if (line.trim() === '---') {
      elements.push(<hr key={i} className="my-3 border-apple-border" />);
    } else if (line.trim()) {
      elements.push(
        <p key={i} className="my-1.5 text-[13.5px] leading-relaxed text-apple-secondary">
          {renderInline(line)}
        </p>,
      );
    }
    i++;
  }

  return <div>{elements}</div>;
};

const ACCESS_LABEL: Record<string, { label: string; tone: string }> = {
  retrieved_full: {
    label: 'Full text accessed',
    tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
  },
  retrieved_partial: {
    label: 'Abstract / partial accessed',
    tone: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  },
  abstract_accessed: {
    label: 'Abstract accessed (not full text)',
    tone: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  },
  pdf_excerpt: {
    label: 'PDF excerpt accessed',
    tone: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300',
  },
  metadata_only: {
    label: 'Metadata only — not retrieved',
    tone: 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300',
  },
  demo_metadata_only: {
    label: 'Demo metadata — not retrieved',
    tone: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
  user_provided: {
    label: 'User-provided',
    tone: 'bg-blue-50 text-[#0071E3] dark:bg-blue-950/60 dark:text-[#2997FF]',
  },
  internal_trace: {
    label: 'Internal trace (not external)',
    tone: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
  not_verified: {
    label: 'Not verified',
    tone: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300',
  },
};

const accessInfo = (s: StepSource): { label: string; tone: string } => {
  const key = (s.access_status || '').trim();
  if (ACCESS_LABEL[key]) return ACCESS_LABEL[key];
  if (s.type === 'demo_reference') return ACCESS_LABEL.demo_metadata_only;
  if (s.type === 'user_input') return ACCESS_LABEL.user_provided;
  if (s.type === 'internal_trace') return ACCESS_LABEL.internal_trace;
  return ACCESS_LABEL.not_verified;
};

const isExternalRetrieved = (s: StepSource): boolean => {
  const k = (s.access_status || '').trim();
  return (
    k === 'retrieved_full' ||
    k === 'retrieved_partial' ||
    k === 'abstract_accessed' ||
    k === 'pdf_excerpt'
  );
};

const locator = (s: StepSource): string => {
  const fn = s.filename?.trim();
  if (!fn) return '';
  return s.page != null ? `${fn}, p. ${s.page}` : fn;
};

const formatCitation = (s: StepSource, n: number, style: CitationStyle): string => {
  const authors = s.authors?.trim();
  const title = s.title?.trim() || 'Untitled source';
  const year = s.year != null && `${s.year}`.trim() ? `${s.year}`.trim() : '';
  const venue = s.venue?.trim();
  const doi = s.doi?.trim();
  const url = s.url?.trim() || (/^https?:\/\//i.test(s.reference || '') ? s.reference.trim() : '');
  const doiLine = doi ? ` DOI: ${doi.startsWith('http') ? doi : `https://doi.org/${doi}`}.` : '';
  const urlLine = !doi && url ? ` Available: ${url}` : '';
  const loc = locator(s);
  const suffix = loc ? ` (${loc})` : '';
  if (style === 'ieee') {
    const a = authors ? `${authors}, ` : '';
    const v = venue ? `${venue}, ` : '';
    const y = year ? `${year}.` : '';
    return `[${n}] ${a}"${title}," ${v}${y}${doiLine}${urlLine}${suffix}`.replace(/\s+/g, ' ').trim();
  }
  if (style === 'apa') {
    const a = authors ? `${authors} ` : '';
    const y = year ? `(${year}). ` : '';
    const v = venue ? `${venue}. ` : '';
    return `${a}${y}${title}. ${v}${doiLine}${urlLine}${suffix}`.replace(/\s+/g, ' ').trim();
  }
  const v = venue ? `${venue}, ` : '';
  const y = year ? `${year}.` : '';
  return `[${n}] ${title}. ${v}${y}${doiLine}${urlLine}${suffix}`.replace(/\s+/g, ' ').trim();
};

const OutputMetrics: React.FC<{
  step?: ExecutionStep;
  content: string;
  citationStyle: CitationStyle;
  stale?: boolean;
  usedSources?: StepSource[];
  additionalSources?: StepSource[];
  claims?: Claim[];
}> = ({ step, content, citationStyle, stale, usedSources, additionalSources, claims }) => {
  const started = step?.started_at ? new Date(step.started_at) : null;
  const completed = step?.completed_at ? new Date(step.completed_at) : null;
  const durationMs =
    step?.duration_ms && step.duration_ms > 0
      ? step.duration_ms
      : started && completed
        ? completed.getTime() - started.getTime()
        : null;
  const totalSec = durationMs != null ? durationMs / 1000 : null;
  const exceedsTarget = totalSec != null && totalSec > 20;
  const resolvedUsed = usedSources ?? (step?.sources ?? []).filter((s) => s.used !== false);
  const resolvedAdditional =
    additionalSources ?? (step?.sources ?? []).filter((s) => s.used === false);
  const hasInternalSource = resolvedUsed.some(
    (s) => s.type === 'user_input' || s.type === 'internal_trace',
  );
  const heuristicClaims = content
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(
      (p) =>
        p.length > 0 &&
        !p.startsWith('#') &&
        !p.startsWith('|') &&
        !p.startsWith('>') &&
        !p.startsWith('- ') &&
        !/^\d+\.\s/.test(p),
    );
  const fmtTime = (d: Date | null) => (d ? d.toLocaleTimeString() : '—');

  return (
    <div className="mt-3 space-y-2 rounded-xl border border-apple-border bg-apple-surface p-3 text-[11.5px]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-semibold text-apple-ink">Output Time Sequence</span>
        <span className="text-apple-secondary">
          Start: <span className="text-apple-ink">{fmtTime(started)}</span>
        </span>
        <span className="text-apple-secondary">
          Completed: <span className="text-apple-ink">{fmtTime(completed)}</span>
        </span>
        <span className="text-apple-secondary">
          Total response time:{' '}
          <span
            className={
              exceedsTarget
                ? 'font-semibold text-amber-700 dark:text-amber-300'
                : 'font-semibold text-apple-ink'
            }
          >
            {totalSec != null ? `${totalSec.toFixed(2)}s` : '—'}
          </span>
        </span>
        {totalSec != null && (
          <span
            className={`rounded-full px-2 py-0.5 text-[10.5px] font-medium ${
              exceedsTarget
                ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/50 dark:text-amber-300'
                : 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300'
            }`}
          >
            {exceedsTarget
              ? `Exceeded 20s target (actual ${totalSec.toFixed(2)}s)`
              : 'Within 20s target'}
          </span>
        )}
      </div>

      {stale && (
        <div className="rounded-lg border border-amber-500/40 bg-amber-50 px-2.5 py-1.5 text-[11px] font-medium text-amber-800 dark:bg-amber-950/30 dark:text-amber-200">
          Verification stale — this section was edited by a human and has not been re-verified against its references.
        </div>
      )}

      <div>
        <p className="font-semibold text-apple-ink">
          Research References Used to Generate This Output ({resolvedUsed.length})
        </p>
        {resolvedUsed.length === 0 ? (
          <p className="text-apple-secondary">
            No external research was used for this output (research disabled, not requested, or no relevant sources).
          </p>
        ) : (
          <ol className="mt-1 space-y-1.5">
            {resolvedUsed.map((s, i) => {
              const access = accessInfo(s);
              return (
                <li key={i} className="rounded-lg bg-apple-elevated px-2.5 py-1.5">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-apple-secondary">{formatCitation(s, i + 1, citationStyle)}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${access.tone}`}>
                      {access.label}
                    </span>
                    {isExternalRetrieved(s) && s.used !== false ? (
                      <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
                        Used
                      </span>
                    ) : (
                      <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-medium text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300">
                        Not retrieved
                      </span>
                    )}
                  </div>
                  <details className="mt-1">
                    <summary className="cursor-pointer text-[10.5px] text-apple-tertiary hover:text-apple-ink">
                      Source details
                    </summary>
                    <div className="mt-1 space-y-0.5 text-[10.5px] text-apple-secondary">
                      {s.authors && <div>Authors: {s.authors}</div>}
                      {s.year != null && `${s.year}` !== '' && <div>Year: {s.year}</div>}
                      {s.venue && <div>Venue: {s.venue}</div>}
                      {s.provider && <div>Provider: {s.provider}</div>}
                      {s.filename && <div>File: {s.filename}</div>}
                      {s.page != null && <div>Page: {s.page}</div>}
                      {s.doi && (
                        <div>
                          DOI:{' '}
                          <a
                            href={s.doi.startsWith('http') ? s.doi : `https://doi.org/${s.doi}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-apple-blue hover:underline"
                          >
                            {s.doi}
                          </a>
                        </div>
                      )}
                      {/^https?:\/\//i.test(s.reference || '') && (
                        <div>
                          Source:{' '}
                          <a
                            href={s.reference}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-apple-blue hover:underline"
                          >
                            {s.reference}
                          </a>
                        </div>
                      )}
                      {s.reliability_note && <div>Note: {s.reliability_note}</div>}
                      {!s.authors && !s.year && !s.venue && !s.doi && !s.provider && !s.filename && (
                        <div className="text-apple-tertiary">
                          Author, year, venue, and DOI not available for this source.
                        </div>
                      )}
                    </div>
                  </details>
                </li>
              );
            })}
          </ol>
        )}

        {resolvedAdditional.length > 0 && (
          <div className="mt-2">
            <p className="font-medium text-apple-ink">Additional Sources Retrieved ({resolvedAdditional.length})</p>
            <ul className="mt-1 space-y-0.5">
              {resolvedAdditional.map((s, i) => (
                <li key={i} className="text-[10.5px] text-apple-secondary">
                  • {s.title}
                  {s.provider ? ` — ${s.provider}` : ''}
                  {locator(s) ? ` (${locator(s)})` : ''}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div>
        <p className="font-semibold text-apple-ink">Claim Support</p>
        {claims && claims.length > 0 ? (
          <ul className="mt-1 space-y-1.5">
            {claims.map((c) => {
              const tone =
                c.support === 'evidence_backed'
                  ? 'text-emerald-700 dark:text-emerald-300'
                  : c.support === 'partial' || c.support === 'stale'
                    ? 'text-amber-700 dark:text-amber-300'
                    : c.support === 'no_research'
                      ? 'text-apple-secondary'
                      : 'text-red-600 dark:text-red-400';
              return (
                <li key={c.index} className="rounded-lg bg-apple-elevated px-2.5 py-1.5">
                  <span className="line-clamp-1 text-apple-ink">{c.text}</span>
                  {' — '}
                  <span className={tone}>{c.support_label}</span>
                  {c.ref_numbers.length > 0 && (
                    <span className="text-apple-secondary"> [{c.ref_numbers.join(', ')}]</span>
                  )}
                  {c.supporting_passage && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-[10.5px] text-apple-tertiary hover:text-apple-ink">
                        Supporting passage
                      </summary>
                      <p className="mt-1 text-[10.5px] text-apple-secondary">{c.supporting_passage}</p>
                    </details>
                  )}
                </li>
              );
            })}
          </ul>
        ) : heuristicClaims.length === 0 ? (
          <p className="text-apple-secondary">No discrete claims to evaluate.</p>
        ) : (
          <ul className="mt-1 space-y-1">
            {heuristicClaims.map((c, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <span
                  className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${
                    hasInternalSource ? 'bg-blue-500' : 'bg-red-500'
                  }`}
                />
                <span className="text-apple-secondary">
                  <span className="line-clamp-1 text-apple-ink">{c.slice(0, 140)}</span>
                  {' — '}
                  {hasInternalSource ? (
                    <span className="text-apple-blue">
                      Grounded in user-provided specification / internal trace (not external research).
                    </span>
                  ) : (
                    <span className="text-red-600 dark:text-red-400">
                      Unverified claim — no sufficiently supporting reference was identified.
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-apple-ink">Output Accuracy:</span>
        <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10.5px] font-medium text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
          Accuracy not verified
        </span>
        {step?.confidence_basis && (
          <span className="text-apple-secondary">
            Estimated confidence (not measured):{' '}
            <span className="text-apple-ink">{step.confidence_basis}</span>
          </span>
        )}
      </div>
    </div>
  );
};

export const SharedArtifactPanel: React.FC<SharedArtifactPanelProps> = ({
  task,
  highlightedStepId,
  onHighlightStep,
  onEditSection,
  onAddSection,
  onRatingSubmitted,
}) => {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [headingDraft, setHeadingDraft] = useState('');
  const [contentDraft, setContentDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [citationStyle, setCitationStyle] = useState<CitationStyle>(task.citation_style || 'simple');

  const handleCitationStyleChange = (style: CitationStyle) => {
    setCitationStyle(style);
    api.setCitationStyle(task.id, style).catch(() => {
      /* non-fatal: style still applies locally for this session */
    });
  };

  const [diffMap, setDiffMap] = useState<Record<string, ArtifactSectionDiff | null>>({});
  const [revMap, setRevMap] = useState<Record<string, ArtifactRevision[] | null>>({});

  const [showAddSection, setShowAddSection] = useState(false);
  const [newHeading, setNewHeading] = useState('');
  const [newContent, setNewContent] = useState('');

  // Quick post-task rating capture for Evaluation Dashboard
  const [effort, setEffort] = useState(3);
  const [trust, setTrust] = useState(6);
  const [control, setControl] = useState(6);
  const [ratingNotes, setRatingNotes] = useState('');
  const [ratingSaved, setRatingSaved] = useState(false);

  const stepById = new Map(task.steps.map((s) => [s.id, s]));

  const startEditing = (sec: ArtifactSection) => {
    setEditingId(sec.id);
    setHeadingDraft(sec.heading);
    setContentDraft(sec.current_content);
  };

  const handleSaveEdit = async (sectionId: string) => {
    setSaving(true);
    try {
      await onEditSection(sectionId, headingDraft, contentDraft);
      setEditingId(null);
      setDiffMap((prev) => ({ ...prev, [sectionId]: null }));
      setRevMap((prev) => ({ ...prev, [sectionId]: null }));
    } finally {
      setSaving(false);
    }
  };

  const toggleDiff = async (sectionId: string) => {
    if (diffMap[sectionId]) {
      setDiffMap((prev) => ({ ...prev, [sectionId]: null }));
      return;
    }
    const diff = await api.getSectionDiff(task.id, sectionId);
    setDiffMap((prev) => ({ ...prev, [sectionId]: diff }));
  };

  const toggleRevisions = async (sectionId: string) => {
    if (revMap[sectionId]) {
      setRevMap((prev) => ({ ...prev, [sectionId]: null }));
      return;
    }
    const res = await api.getSectionRevisions(task.id, sectionId);
    setRevMap((prev) => ({ ...prev, [sectionId]: res.revisions }));
  };

  const handleCreateSection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newHeading.trim() || !newContent.trim()) return;
    setSaving(true);
    try {
      await onAddSection(newHeading.trim(), newContent.trim());
      setNewHeading('');
      setNewContent('');
      setShowAddSection(false);
    } finally {
      setSaving(false);
    }
  };

  const handleExportMarkdown = async () => {
    try {
      const md = await api.exportArtifactMarkdown(task.id);
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${task.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 50)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // Fallback: client-side render preserving references from task-level data.
      const used = task.research_enabled ? task.research_used : [];
      const additional = task.research_enabled ? task.research_retrieved : [];
      const refBlock = used.length
        ? `\n\n**Research References Used to Generate This Output**\n\n${used
            .map((s, i) => formatCitation(s, i + 1, citationStyle))
            .join('\n')}\n`
        : `\n\n**Research References Used to Generate This Output** — No external research was used.\n`;
      const addBlock = additional.length
        ? `\n\n**Additional Sources Retrieved**\n\n${additional.map((s) => `- ${s.title}`).join('\n')}\n`
        : '';
      const md = [
        `# ${task.title}`,
        ``,
        `> Mode: ${task.interaction_mode.toUpperCase()} · Engine: ${task.provider_mode === 'demo' ? 'Deterministic Demo Mode' : task.provider_name}`,
        ``,
        ...task.artifact_sections.map(
          (sec) =>
            `## ${sec.heading}\n*(${AUTHORSHIP_BADGE[sec.authorship]?.label || sec.authorship} · v${sec.version})*\n\n${sec.current_content}`,
        ),
        refBlock + addBlock,
      ].join('\n');
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${task.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 50)}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleSubmitRating = async (e: React.FormEvent) => {
    e.preventDefault();
    await api.submitEvaluationRating({
      task_id: task.id,
      scenario_key: task.topic.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60) || 'custom',
      effort_rating: effort,
      trust_rating: trust,
      control_rating: control,
      notes: ratingNotes,
    });
    setRatingSaved(true);
    onRatingSubmitted?.();
  };

  return (
    <div className="flex h-full flex-col rounded-xl border border-apple-border bg-apple-elevated p-4 shadow-apple-sm">
      {/* Header */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-apple-border pb-2.5">
        <div>
          <p className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-apple-tertiary">
            Shared Workspace
          </p>
          <h2 className="text-[15px] font-semibold tracking-tight">Collaborative Artifact</h2>
          <p className="text-[11px] text-apple-secondary">
            {task.research_enabled
              ? task.research_used.length
              : task.artifact_sections.reduce(
                  (n, sec) => {
                    const l = sec.step_id ? stepById.get(sec.step_id) : undefined;
                    return n + (l?.sources?.filter((s) => s.used !== false).length ?? 0);
                  },
                  0,
                )}{' '}
            references used
          </p>
          {task.research_enabled && (
            <p className="text-[11px] text-apple-secondary">
              Research: <span className="text-apple-ink">{task.research_status}</span> · used {task.research_used_count} ·
              additional {task.research_retrieved_count}
              {task.research_duration_ms != null ? ` · ${(task.research_duration_ms / 1000).toFixed(2)}s` : ''}
            </p>
          )}
        </div>

        <div className="flex items-center gap-2">
          <select
            aria-label="Citation Style"
            value={citationStyle}
            onChange={(e) => handleCitationStyleChange(e.target.value as CitationStyle)}
            className="rounded-full border border-apple-border bg-apple-elevated px-2.5 py-1 text-[11.5px] font-medium text-apple-ink outline-none focus:border-apple-blue"
          >
            <option value="simple">Simple Numbered</option>
            <option value="ieee">IEEE</option>
            <option value="apa">APA 7th</option>
          </select>
          <button
            type="button"
            onClick={() => setShowAddSection((v) => !v)}
            className="inline-flex items-center gap-1 rounded-full border border-apple-border px-3 py-1 text-[12px] font-medium text-apple-ink transition hover:bg-apple-surface"
          >
            <Plus className="h-3.5 w-3.5" /> Add Section
          </button>
          <button
            type="button"
            disabled={task.artifact_sections.length === 0}
            onClick={handleExportMarkdown}
            className="inline-flex items-center gap-1 rounded-full border border-apple-border px-3 py-1 text-[12px] font-medium text-apple-ink transition hover:bg-apple-surface disabled:opacity-40"
          >
            <Download className="h-3.5 w-3.5" /> Export .md
          </button>
        </div>
      </div>

      {/* Research Activity & Reference Summary (honest, real data only) */}
      <div className="mb-3">
        <ResearchPanel task={task} />
      </div>

      {/* Add User Section Form */}
      {showAddSection && (
        <form onSubmit={handleCreateSection} className="mb-4 space-y-2.5 rounded-2xl border border-apple-blue/30 bg-apple-surface p-4">
          <h3 className="text-[13px] font-semibold">Add Human-Authored Artifact Section</h3>
          <input
            type="text"
            required
            value={newHeading}
            onChange={(e) => setNewHeading(e.target.value)}
            placeholder="Section heading (e.g., Team Decision Notes)"
            className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[13px] outline-none focus:border-apple-blue"
          />
          <textarea
            required
            rows={4}
            value={newContent}
            onChange={(e) => setNewContent(e.target.value)}
            placeholder="Write markdown content..."
            className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-2 text-[13px] outline-none focus:border-apple-blue"
          />
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className="apple-pill-primary px-4 py-1.5 text-[12px]">
              Add to Artifact
            </button>
            <button
              type="button"
              onClick={() => setShowAddSection(false)}
              className="rounded-full px-3 py-1.5 text-[12px] text-apple-secondary"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Artifact Sections Stream */}
      <div className="flex-1 space-y-4 overflow-y-auto pr-1">
        {task.artifact_sections.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center rounded-2xl border border-dashed border-apple-border bg-apple-surface/50 px-6 text-center">
            <FileText className="h-8 w-8 text-apple-tertiary" />
            <h3 className="mt-3 text-[15px] font-semibold">Shared Artifact Ready</h3>
            <p className="mt-1 max-w-[380px] text-[13px] text-apple-secondary">
              Approve the execution plan or click <strong>Start Task</strong> to watch structured
              report sections materialize here in real time. You can edit any section or add your own at any time.
            </p>
          </div>
        ) : (
          task.artifact_sections.map((sec) => {
            const badge = AUTHORSHIP_BADGE[sec.authorship] || AUTHORSHIP_BADGE.ai;
            const linkedStep = sec.step_id ? stepById.get(sec.step_id) : undefined;
            const linkedOrder = linkedStep?.step_order ?? null;
            const isStreamingLive = linkedStep?.status === 'RUNNING';
            const isHighlighted = highlightedStepId !== null && sec.step_id === highlightedStepId;
            const isEditing = editingId === sec.id;
            const diff = diffMap[sec.id];
            const revisions = revMap[sec.id];

            const authorshipBorder =
              sec.authorship === 'collaborative'
                ? 'border-l-[3px] border-l-apple-blue'
                : sec.authorship === 'human'
                  ? 'border-l-[3px] border-l-emerald-500'
                  : 'border-l-[3px] border-l-neutral-400/50 dark:border-l-neutral-600';

            return (
              <article
                key={sec.id}
                id={`artifact-step-${sec.step_id || sec.id}`}
                className={`rounded-lg border p-4 transition-colors ${authorshipBorder} ${
                  isHighlighted
                    ? 'border-apple-blue ring-2 ring-apple-blue/20 bg-apple-blue/[0.04]'
                    : 'border-apple-border bg-apple-bg'
                }`}
              >
                {/* Section Header & Provenance */}
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="text-[16px] font-semibold tracking-tight text-apple-ink">
                      {sec.heading}
                    </h3>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                      <span className={`rounded-full px-2.5 py-0.5 text-[10.5px] font-medium ${badge.style}`}>
                        {badge.label}
                      </span>
                      <span className="text-[11px] text-apple-secondary">v{sec.version}</span>
                      {isStreamingLive && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10.5px] font-medium text-apple-blue dark:bg-blue-950/60">
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-apple-blue" />
                          Streaming Live
                        </span>
                      )}
                      {sec.step_id && linkedOrder && (
                        <button
                          type="button"
                          onClick={() => onHighlightStep(isHighlighted ? null : sec.step_id)}
                          className="inline-flex items-center gap-1 rounded-full bg-apple-surface px-2 py-0.5 text-[10.5px] font-medium text-apple-blue hover:underline"
                        >
                          <Link2 className="h-2.5 w-2.5" /> Linked to Step {linkedOrder}
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Section Controls */}
                  <div className="flex items-center gap-1.5">
                    {!isEditing && (
                      <button
                        type="button"
                        onClick={() => startEditing(sec)}
                        className="inline-flex items-center gap-1 rounded-full border border-apple-border px-2.5 py-1 text-[11.5px] font-medium hover:bg-apple-surface"
                      >
                        <Edit3 className="h-3 w-3" /> Edit
                      </button>
                    )}
                    {sec.ai_content && (
                      <button
                        type="button"
                        onClick={() => toggleDiff(sec.id)}
                        className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11.5px] font-medium transition ${
                          diff
                            ? 'border-apple-blue bg-blue-50 text-apple-blue dark:bg-blue-950/50'
                            : 'border-apple-border hover:bg-apple-surface'
                        }`}
                      >
                        <GitCompare className="h-3 w-3" /> Diff
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => toggleRevisions(sec.id)}
                      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11.5px] font-medium transition ${
                        revisions
                          ? 'border-apple-blue bg-blue-50 text-apple-blue dark:bg-blue-950/50'
                          : 'border-apple-border hover:bg-apple-surface'
                      }`}
                    >
                      <History className="h-3 w-3" /> History
                    </button>
                  </div>
                </div>

                {/* Editor OR Rendered Markdown */}
                {isEditing ? (
                  <div className="mt-3 space-y-2.5">
                    <input
                      type="text"
                      value={headingDraft}
                      onChange={(e) => setHeadingDraft(e.target.value)}
                      className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[14px] font-semibold outline-none focus:border-apple-blue"
                    />
                    <textarea
                      rows={10}
                      value={contentDraft}
                      onChange={(e) => setContentDraft(e.target.value)}
                      className="w-full rounded-xl border border-apple-border bg-apple-elevated px-3 py-2 font-mono text-[12.5px] leading-relaxed outline-none focus:border-apple-blue"
                    />
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => handleSaveEdit(sec.id)}
                        className="apple-pill-primary px-4 py-1.5 text-[12px]"
                      >
                        {saving ? 'Saving...' : 'Save Collaborative Edit'}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingId(null)}
                        className="rounded-full px-3 py-1.5 text-[12px] text-apple-secondary hover:text-apple-ink"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3">
                    <MarkdownBlock content={sec.current_content} />
                  </div>
                )}

                {/* Output Time Sequence, References & Accuracy (additive, real data only) */}
                <OutputMetrics
                  step={linkedStep}
                  content={sec.current_content}
                  citationStyle={citationStyle}
                  stale={sec.authorship !== 'ai' || sec.has_user_edits}
                  usedSources={task.research_enabled ? task.research_used : undefined}
                  additionalSources={task.research_enabled ? task.research_retrieved : undefined}
                  claims={sec.claims}
                />

                {/* Inline AI vs Human Diff View */}
                {diff && (
                  <div className="mt-4 rounded-xl border border-apple-border bg-apple-surface p-3">
                    <div className="mb-2 flex items-center justify-between text-[11.5px]">
                      <span className="font-semibold text-apple-ink">
                        AI Draft vs. Current Collaborative Text
                      </span>
                      <span className="text-apple-secondary">
                        +{diff.lines_added} added / -{diff.lines_removed} removed
                      </span>
                    </div>
                    {!diff.has_user_changes ? (
                      <p className="text-[12px] text-apple-secondary">
                        Matches original AI-generated draft with no human modifications yet.
                      </p>
                    ) : (
                      <div className="max-h-56 overflow-y-auto rounded-lg bg-apple-elevated p-2 font-mono text-[11.5px]">
                        {diff.diff.map((d, idx) => (
                          <div
                            key={idx}
                            className={`whitespace-pre-wrap px-2 py-0.5 ${
                              d.type === 'added'
                                ? 'bg-emerald-500/15 text-emerald-800 dark:text-emerald-300'
                                : d.type === 'removed'
                                  ? 'bg-red-500/15 text-red-700 line-through dark:text-red-300'
                                  : 'text-apple-secondary'
                            }`}
                          >
                            {d.type === 'added' ? '+ ' : d.type === 'removed' ? '- ' : '  '}
                            {d.text}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Revision History Trail */}
                {revisions && (
                  <div className="mt-4 rounded-xl border border-apple-border bg-apple-surface p-3">
                    <p className="mb-2 text-[11.5px] font-semibold text-apple-ink">
                      Preserved Section Revisions ({revisions.length})
                    </p>
                    <div className="space-y-1.5">
                      {revisions.map((r) => (
                        <div
                          key={r.id}
                          className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-apple-elevated px-3 py-1.5 text-[11.5px]"
                        >
                          <div>
                            <span className="font-semibold">v{r.version}</span>{' '}
                            <span className="capitalize text-apple-blue">({r.author_type})</span> —{' '}
                            <span className="text-apple-secondary">{r.summary}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {r.version !== sec.version && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={async () => {
                                  setSaving(true);
                                  try {
                                    await onEditSection(sec.id, sec.heading, r.content);
                                    setRevMap((prev) => ({ ...prev, [sec.id]: null }));
                                  } finally {
                                    setSaving(false);
                                  }
                                }}
                                className="rounded-full border border-apple-border px-2 py-0.5 text-[10.5px] font-medium text-apple-blue hover:bg-blue-50 dark:hover:bg-blue-950/40"
                              >
                                Restore v{r.version}
                              </button>
                            )}
                            {r.created_at && (
                              <span className="text-[10.5px] text-apple-tertiary">
                                {new Date(r.created_at).toLocaleTimeString()}
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </article>
            );
          })
        )}

        {/* Post-Completion Scientific Evaluation Rating Capture */}
        {task.status === 'COMPLETED' && (
          <div className="rounded-[18px] border border-apple-blue/25 bg-blue-50/40 p-5 dark:bg-blue-950/20">
            <div className="flex items-center gap-2 text-[14px] font-semibold">
              <Star className="h-4 w-4 text-apple-blue" /> Record Evaluation Rating for This Task
            </div>
            <p className="mt-1 text-[12.5px] text-apple-secondary">
              Optional: Rate your experience on consistent 1–7 scales to populate genuine measured
              data in the Evaluation Dashboard.
            </p>
            {ratingSaved ? (
              <p className="mt-3 flex items-center gap-1.5 text-[13px] font-medium text-emerald-700 dark:text-emerald-300">
                <Check className="h-4 w-4" /> Evaluation response recorded for this {task.interaction_mode.toUpperCase()} session.
              </p>
            ) : (
              <form onSubmit={handleSubmitRating} className="mt-3 space-y-3">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div>
                    <label className="block text-[11.5px] font-medium text-apple-secondary">
                      User Effort (1=Easy, 7=Hard): <strong className="text-apple-ink">{effort}</strong>
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={7}
                      value={effort}
                      onChange={(e) => setEffort(Number(e.target.value))}
                      className="mt-1 w-full accent-[#0071E3]"
                    />
                  </div>
                  <div>
                    <label className="block text-[11.5px] font-medium text-apple-secondary">
                      Perceived Trust (1–7): <strong className="text-apple-ink">{trust}</strong>
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={7}
                      value={trust}
                      onChange={(e) => setTrust(Number(e.target.value))}
                      className="mt-1 w-full accent-[#0071E3]"
                    />
                  </div>
                  <div>
                    <label className="block text-[11.5px] font-medium text-apple-secondary">
                      Perceived Control (1–7): <strong className="text-apple-ink">{control}</strong>
                    </label>
                    <input
                      type="range"
                      min={1}
                      max={7}
                      value={control}
                      onChange={(e) => setControl(Number(e.target.value))}
                      className="mt-1 w-full accent-[#0071E3]"
                    />
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <input
                    type="text"
                    value={ratingNotes}
                    onChange={(e) => setRatingNotes(e.target.value)}
                    placeholder="Optional observation notes..."
                    className="min-w-[200px] flex-1 rounded-xl border border-apple-border bg-apple-elevated px-3 py-1.5 text-[12.5px] outline-none focus:border-apple-blue"
                  />
                  <button type="submit" className="apple-pill-primary px-4 py-1.5 text-[12px]">
                    Save Measured Rating
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
