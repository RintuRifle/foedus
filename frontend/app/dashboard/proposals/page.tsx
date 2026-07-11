"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { Proposal } from "@/lib/types";
import { Spinner, Stamp } from "@/components/ui";

const STATUS_TONE: Record<string, "brass" | "emerald" | "azure" | "crimson"> = {
  draft: "brass",
  reviewed: "azure",
  submitted: "emerald",
  archived: "crimson",
};

export default function ProposalsPage() {
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Proposal[]>("/proposals")
      .then(setProposals)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
          Drafted by the Writer · Reviewed by the Reviewer
        </p>
        <h1 className="mt-2 font-display text-4xl font-light text-cream">
          Proposals
        </h1>
      </header>

      {loading ? (
        <Spinner label="Fetching drafts…" />
      ) : proposals.length === 0 ? (
        <p className="text-sm text-muted">
          No proposals yet. Run an evaluation — the Writer agent drafts one
          automatically when a tender clears the audit.
        </p>
      ) : (
        <div className="space-y-3">
          {proposals.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <Link
                href={`/dashboard/proposals/${p.id}`}
                className="dossier group flex items-center gap-5 rounded-lg px-5 py-4 transition-colors hover:border-brass/40"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-cream group-hover:text-brass-bright">
                    {p.title ?? "Untitled proposal"}
                  </p>
                  <p className="mt-0.5 font-mono text-[11px] text-muted">
                    v{p.version} · updated{" "}
                    {new Date(p.updated_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                    })}
                  </p>
                </div>
                <Stamp tone={STATUS_TONE[p.status] ?? "brass"}>{p.status}</Stamp>
              </Link>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
