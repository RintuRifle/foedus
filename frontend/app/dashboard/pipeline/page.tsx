"use client";

// Pipeline — every evaluation job, newest first, with live-ish status.

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { EvalProgress } from "@/lib/types";
import { Spinner, Stamp } from "@/components/ui";

const STATUS_TONE: Record<string, "brass" | "emerald" | "crimson" | "azure"> = {
  queued: "azure",
  pending: "azure",
  running: "brass",
  completed: "emerald",
  failed: "crimson",
};

export default function PipelinePage() {
  const [jobs, setJobs] = useState<EvalProgress[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = () =>
      api<EvalProgress[]>("/evaluations")
        .then(setJobs)
        .catch(() => {})
        .finally(() => setLoading(false));
    load();
    const t = setInterval(load, 8000); // keep running jobs fresh
    return () => clearInterval(t);
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
          Agent Operations
        </p>
        <h1 className="mt-2 font-display text-4xl font-light text-cream">
          Pipeline
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Every evaluation your agents have run.
        </p>
      </header>

      {loading ? (
        <Spinner label="Fetching operations…" />
      ) : jobs.length === 0 ? (
        <p className="text-sm text-muted">
          No evaluations yet. Open a tender dossier and hit{" "}
          <span className="text-brass">Evaluate</span>.
        </p>
      ) : (
        <div className="space-y-3">
          {jobs.map((job, i) => (
            <motion.div
              key={job.job_id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <Link
                href={`/dashboard/evaluations/${job.job_id}`}
                className="dossier group flex items-center gap-5 rounded-lg px-5 py-4 transition-colors hover:border-brass/40"
              >
                <div className="w-16 text-center">
                  <p className="font-mono text-lg text-brass-bright">
                    {job.progress_pct}%
                  </p>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="h-1 w-full overflow-hidden rounded-full bg-surface-3">
                    <div
                      className={`h-full rounded-full transition-all duration-700 ${
                        job.status === "failed" ? "bg-crimson" : "bg-brass"
                      } ${job.status === "running" ? "animate-pulseSoft" : ""}`}
                      style={{ width: `${job.progress_pct}%` }}
                    />
                  </div>
                  <p className="mt-2 truncate font-mono text-[11px] text-muted">
                    {job.current_message ??
                      job.current_agent ??
                      "waiting in queue"}
                    {job.duration_seconds !== null &&
                      ` · ${Math.round(job.duration_seconds)}s`}
                  </p>
                </div>

                <Stamp tone={STATUS_TONE[job.status] ?? "brass"}>
                  {job.status}
                </Stamp>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
