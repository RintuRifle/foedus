"use client";

// Tender detail dossier + the trigger that unleashes the agents.

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api, ApiError } from "@/lib/api";
import type { EvalStartResponse, Tender } from "@/lib/types";
import {
  Button,
  ErrorNote,
  Hairline,
  Spinner,
  Stamp,
  Tag,
  formatLakh,
} from "@/components/ui";

export default function TenderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Tender>(`/tenders/${id}`)
      .then(setTender)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [id]);

  async function evaluate() {
    setStarting(true);
    setError(null);
    try {
      const res = await api<EvalStartResponse>("/evaluations/start", {
        method: "POST",
        body: { tender_id: id },
      });
      router.push(`/dashboard/evaluations/${res.job_id}`);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 402
          ? e.message
          : e instanceof Error
            ? e.message
            : "Failed to start evaluation",
      );
      setStarting(false);
    }
  }

  if (loading)
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner label="Opening dossier…" />
      </div>
    );
  if (!tender)
    return <ErrorNote message={error ?? "Tender not found"} />;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="mx-auto max-w-3xl"
    >
      <button
        onClick={() => router.back()}
        className="mb-6 font-mono text-[11px] uppercase tracking-wider text-muted hover:text-cream"
      >
        ← Back
      </button>

      <div className="dossier rounded-lg p-8 shadow-dossier">
        <div className="flex items-start justify-between gap-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
              {tender.source} · {tender.external_id ?? "REF—"}
            </p>
            <h1 className="mt-2 font-display text-3xl leading-tight text-cream">
              {tender.title}
            </h1>
          </div>
          <Stamp tone={tender.status === "active" ? "emerald" : "crimson"}>
            {tender.status}
          </Stamp>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-x-8 gap-y-4 md:grid-cols-4">
          <Fact label="Value" value={formatLakh(tender.value_lakh)} />
          <Fact label="EMD" value={formatLakh(tender.emd_amount)} />
          <Fact
            label="Deadline"
            value={
              tender.days_remaining !== null
                ? `${tender.days_remaining} days`
                : "—"
            }
            danger={tender.days_remaining !== null && tender.days_remaining <= 5}
          />
          <Fact label="State" value={tender.state ?? "—"} />
        </div>

        {(tender.sector?.length ?? 0) > 0 && (
          <div className="mt-5 flex flex-wrap gap-2">
            {tender.sector!.map((s) => (
              <Tag key={s}>{s}</Tag>
            ))}
          </div>
        )}

        <div className="my-6">
          <Hairline />
        </div>

        {tender.department && (
          <p className="font-mono text-xs text-muted">
            Issued by{" "}
            <span className="text-cream">{tender.department}</span>
            {tender.organization && ` — ${tender.organization}`}
          </p>
        )}

        {tender.description && (
          <p className="mt-4 text-sm leading-relaxed text-muted">
            {tender.description}
          </p>
        )}

        {error && (
          <div className="mt-6">
            <ErrorNote message={error} />
            {error.toLowerCase().includes("limit") && (
              <a
                href="/dashboard/billing"
                className="mt-3 inline-block rounded-md bg-brass px-5 py-2.5 text-sm font-semibold text-ink shadow-glowbrass transition-all hover:bg-brass-bright"
              >
                Upgrade to Pro — unlimited evaluations →
              </a>
            )}
          </div>
        )}

        <div className="mt-8 flex items-center gap-4">
          <Button onClick={evaluate} disabled={starting}>
            {starting ? "Deploying agents…" : "⚡ Evaluate with AI"}
          </Button>
          {tender.pdf_url && (
            <a
              href={tender.pdf_url}
              target="_blank"
              rel="noreferrer"
              className="font-mono text-[11px] uppercase tracking-wider text-muted transition-colors hover:text-brass-bright"
            >
              Original PDF ↗
            </a>
          )}
        </div>
        <p className="mt-3 font-mono text-[10px] uppercase tracking-wider text-muted/60">
          6 agents · match → audit → risk → draft → review · ~90 seconds
        </p>
      </div>
    </motion.div>
  );
}

function Fact({
  label,
  value,
  danger,
}: {
  label: string;
  value: string;
  danger?: boolean;
}) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
        {label}
      </p>
      <p
        className={`mt-1 font-display text-xl ${danger ? "text-crimson" : "text-brass-bright"}`}
      >
        {value}
      </p>
    </div>
  );
}
