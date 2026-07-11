"use client";

// The Evaluation Theater — live WebSocket agent progress,
// then the full intelligence report with compliance matrix.

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { api, getToken, WS_URL } from "@/lib/api";
import type {
  ComplianceItem,
  EvalProgress,
  EvalReport,
  Proposal,
  WsProgressEvent,
} from "@/lib/types";
import {
  ErrorNote,
  Hairline,
  ScoreRing,
  Spinner,
  Stamp,
} from "@/components/ui";

const AGENTS = [
  { key: "context_builder", label: "Context", icon: "◰" },
  { key: "preprocessor", label: "Preprocessor", icon: "◱" },
  { key: "matchmaker", label: "Matchmaker", icon: "◲" },
  { key: "auditor", label: "Auditor", icon: "◳" },
  { key: "risk_assessor", label: "Risk", icon: "◴" },
  { key: "writer", label: "Writer", icon: "◵" },
  { key: "reviewer", label: "Reviewer", icon: "◶" },
];

export default function EvaluationPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [progress, setProgress] = useState(0);
  const [agent, setAgent] = useState("context_builder");
  const [message, setMessage] = useState("Connecting to war room…");
  const [status, setStatus] = useState<string>("running");
  const [log, setLog] = useState<WsProgressEvent[]>([]);
  const [report, setReport] = useState<EvalReport | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // ── Live progress: WebSocket with polling fallback ────────
  useEffect(() => {
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let done = false;

    const finish = (finalStatus: string) => {
      done = true;
      setStatus(finalStatus);
      if (pollTimer) clearInterval(pollTimer);
      if (finalStatus === "completed") loadReport();
    };

    const applyEvent = (ev: WsProgressEvent) => {
      setProgress(ev.progress);
      setAgent(ev.agent);
      setMessage(ev.message);
      setLog((l) =>
        l.some((x) => x.message === ev.message) ? l : [...l, ev],
      );
      if (ev.status === "completed" || ev.status === "failed")
        finish(ev.status);
    };

    const startPolling = () => {
      if (pollTimer || done) return;
      pollTimer = setInterval(async () => {
        try {
          const p = await api<EvalProgress>(`/evaluations/${jobId}/status`);
          setProgress(p.progress_pct);
          if (p.current_agent) setAgent(p.current_agent);
          if (p.current_message) setMessage(p.current_message);
          if (p.status === "completed" || p.status === "failed")
            finish(p.status);
        } catch {
          /* retry next tick */
        }
      }, 2500);
    };

    try {
      const ws = new WebSocket(
        `${WS_URL}/ws/evaluations/${jobId}?token=${getToken()}`,
      );
      wsRef.current = ws;
      ws.onmessage = (e) => applyEvent(JSON.parse(e.data));
      ws.onerror = () => startPolling();
      ws.onclose = () => {
        if (!done) startPolling();
      };
    } catch {
      startPolling();
    }

    async function loadReport() {
      try {
        setReport(await api<EvalReport>(`/evaluations/${jobId}/report`));
        const proposals = await api<Proposal[]>("/proposals");
        setProposal(
          proposals.find((p) => p.evaluation_id === jobId) ?? null,
        );
      } catch {
        /* report view shows error state */
      }
    }

    // If already finished when page opens
    api<EvalProgress>(`/evaluations/${jobId}/status`)
      .then((p) => {
        setProgress(p.progress_pct);
        if (p.current_agent) setAgent(p.current_agent);
        if (p.status === "completed" || p.status === "failed")
          finish(p.status);
      })
      .catch(() => {});

    return () => {
      done = true;
      wsRef.current?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  const activeIdx = AGENTS.findIndex((a) => a.key === agent);

  return (
    <div className="mx-auto max-w-3xl">
      <AnimatePresence mode="wait">
        {status === "running" && (
          <motion.div key="live" exit={{ opacity: 0, y: -18 }}>
            <header className="mb-10">
              <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass animate-pulseSoft">
                ● Live Operation
              </p>
              <h1 className="mt-2 font-display text-4xl font-light text-cream">
                Agents at work
              </h1>
            </header>

            {/* Agent rail */}
            <div className="dossier scan-container rounded-lg p-8 shadow-dossier">
              <div className="flex items-center justify-between">
                {AGENTS.map((a, i) => {
                  const state =
                    i < activeIdx ? "done" : i === activeIdx ? "active" : "idle";
                  return (
                    <div key={a.key} className="flex flex-col items-center gap-2">
                      <span
                        className={`flex h-10 w-10 items-center justify-center rounded-full border text-lg transition-all duration-500 ${
                          state === "done"
                            ? "border-emerald/50 text-emerald"
                            : state === "active"
                              ? "border-brass text-brass-bright shadow-glowbrass animate-pulseSoft"
                              : "border-line text-muted/40"
                        }`}
                      >
                        {state === "done" ? "✓" : a.icon}
                      </span>
                      <span
                        className={`font-mono text-[9px] uppercase tracking-wider ${
                          state === "active" ? "text-brass-bright" : "text-muted/60"
                        }`}
                      >
                        {a.label}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-8 h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
                <motion.div
                  className="h-full rounded-full bg-gradient-to-r from-brass-dim via-brass to-brass-bright"
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                />
              </div>

              <p className="mt-4 text-center font-mono text-sm text-brass-bright">
                {message}
              </p>
              <p className="mt-1 text-center font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
                {progress}% · do not close — agents are reading the tender
              </p>
            </div>

            {/* Event log */}
            {log.length > 0 && (
              <div className="mt-6 space-y-1.5 px-2">
                {log.slice(-6).map((ev) => (
                  <motion.p
                    key={ev.timestamp + ev.agent}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 0.7, x: 0 }}
                    className="font-mono text-[11px] text-muted"
                  >
                    <span className="text-emerald">✓</span>{" "}
                    <span className="text-brass/70">
                      [{ev.agent}]
                    </span>{" "}
                    {ev.message}
                  </motion.p>
                ))}
              </div>
            )}
          </motion.div>
        )}

        {status === "failed" && (
          <motion.div
            key="failed"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <Stamp tone="crimson">Operation Failed</Stamp>
            <h1 className="mt-4 font-display text-3xl text-cream">
              The agents hit a wall.
            </h1>
            <p className="mt-2 text-sm text-muted">
              Usually a malformed tender PDF or an LLM hiccup. Re-run from the
              tender dossier — retries are free of charge on our conscience.
            </p>
            <Link
              href="/dashboard/pipeline"
              className="mt-6 inline-block font-mono text-[11px] uppercase tracking-wider text-brass hover:text-brass-bright"
            >
              ← Back to pipeline
            </Link>
          </motion.div>
        )}

        {status === "completed" && (
          <motion.div
            key="report"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            {report ? (
              <ReportView report={report} proposal={proposal} />
            ) : (
              <div className="flex h-64 items-center justify-center">
                <Spinner label="Compiling intelligence report…" />
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── The Intelligence Report ──────────────────────────────────

function ReportView({
  report,
  proposal,
}: {
  report: EvalReport;
  proposal: Proposal | null;
}) {
  const met = report.compliance_matrix.filter((c) => c.status === "met").length;
  const total = report.compliance_matrix.length;

  return (
    <div>
      <header className="mb-8">
        <Stamp tone="emerald">Evaluation Complete</Stamp>
        <h1 className="mt-4 font-display text-3xl leading-tight text-cream">
          {report.tender_title}
        </h1>
        {report.duration_seconds !== null && (
          <p className="mt-1.5 font-mono text-[11px] uppercase tracking-wider text-muted">
            Analysed in {Math.round(report.duration_seconds)}s by 6 agents
          </p>
        )}
      </header>

      {/* Verdict strip */}
      <div className="dossier grid grid-cols-3 gap-6 rounded-lg p-6 shadow-dossier">
        <Verdict
          label="Profile Match"
          ring={report.match_score ?? 0}
        />
        <Verdict
          label="Win Probability"
          ring={report.win_probability ?? 0}
        />
        <div className="flex flex-col items-center justify-center text-center">
          <p className="font-display text-3xl text-brass-bright">
            {met}/{total}
          </p>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
            Criteria Met
          </p>
          {report.competition_level && (
            <p className="mt-2 font-mono text-[10px] text-muted">
              competition: <span className="text-amberwarn">{report.competition_level}</span>
            </p>
          )}
        </div>
      </div>

      {/* Compliance matrix */}
      <section className="mt-10">
        <h2 className="font-display text-xl text-cream">Compliance Matrix</h2>
        <p className="mt-1 text-sm text-muted">
          Tender ki har requirement, aapke documents se cross-checked.
        </p>
        <div className="mt-4 space-y-2">
          {report.compliance_matrix.map((item, i) => (
            <ComplianceRow key={i} item={item} index={i} />
          ))}
          {total === 0 && (
            <p className="text-sm text-muted">
              No structured criteria extracted for this tender.
            </p>
          )}
        </div>
      </section>

      {/* Risk factors */}
      {(report.risk_factors?.length ?? 0) > 0 && (
        <section className="mt-10">
          <h2 className="font-display text-xl text-cream">Risk Factors</h2>
          <ul className="mt-3 space-y-2">
            {report.risk_factors!.map((r) => (
              <li key={r} className="flex gap-3 text-sm text-muted">
                <span className="text-amberwarn">⚠</span> {r}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="my-10">
        <Hairline />
      </div>

      {/* Proposal CTA */}
      {proposal ? (
        <div className="dossier flex items-center justify-between rounded-lg p-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-emerald">
              ✓ Proposal drafted & reviewed
            </p>
            <p className="mt-1 font-display text-lg text-cream">
              {proposal.title ?? "Technical Proposal"}
            </p>
          </div>
          <Link
            href={`/dashboard/proposals/${proposal.id}`}
            className="rounded-md bg-brass px-5 py-2.5 text-sm font-semibold text-ink shadow-glowbrass transition-all hover:bg-brass-bright"
          >
            Open Proposal →
          </Link>
        </div>
      ) : (
        <ErrorNote message="Proposal not generated (likely below match threshold)." />
      )}
    </div>
  );
}

function Verdict({ label, ring }: { label: string; ring: number }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2">
      <ScoreRing value={ring} size={76} />
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
        {label}
      </p>
    </div>
  );
}

function ComplianceRow({
  item,
  index,
}: {
  item: ComplianceItem;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  const tone =
    item.status === "met"
      ? { icon: "✓", cls: "text-emerald border-emerald/30 bg-emerald/5" }
      : item.status === "partial"
        ? { icon: "◐", cls: "text-amberwarn border-amberwarn/30 bg-amberwarn/5" }
        : { icon: "✕", cls: "text-crimson border-crimson/30 bg-crimson/5" };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04 }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full rounded-md border px-4 py-3 text-left transition-all ${tone.cls} ${
          open ? "" : "hover:brightness-125"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm">{tone.icon}</span>
          <span className="flex-1 text-sm text-cream">{item.criterion}</span>
          {item.category && (
            <span className="font-mono text-[9px] uppercase tracking-wider text-muted">
              {item.category}
            </span>
          )}
        </div>
        {open && (
          <div className="mt-3 grid grid-cols-2 gap-4 pl-7 text-xs">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-wider text-muted">
                Tender requires
              </p>
              <p className="mt-0.5 text-cream/90">{item.required_value ?? "—"}</p>
            </div>
            <div>
              <p className="font-mono text-[9px] uppercase tracking-wider text-muted">
                You have
              </p>
              <p className="mt-0.5 text-cream/90">{item.user_value ?? "—"}</p>
            </div>
            {item.source_quote && (
              <p className="col-span-2 border-l-2 border-line pl-3 italic text-muted">
                &ldquo;{item.source_quote}&rdquo;
              </p>
            )}
            {item.notes && (
              <p className="col-span-2 text-muted">{item.notes}</p>
            )}
          </div>
        )}
      </button>
    </motion.div>
  );
}
