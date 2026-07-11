"use client";

// A single tender rendered as a classified dossier card.

import Link from "next/link";
import type { TenderFeedItem } from "@/lib/types";
import { ScoreRing, Stamp, Tag, formatLakh } from "@/components/ui";

export default function TenderCard({
  item,
  compact,
}: {
  item: TenderFeedItem;
  compact?: boolean;
}) {
  const t = item.tender;
  const deadlineTone =
    t.days_remaining !== null && t.days_remaining <= 5
      ? "text-crimson"
      : t.days_remaining !== null && t.days_remaining <= 12
        ? "text-amberwarn"
        : "text-emerald";

  return (
    <div className="dossier flex h-full flex-col rounded-lg p-6 shadow-dossier">
      {/* Header row */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
            {t.source} · {t.external_id ?? "REF—"}
          </p>
          <h3
            className={`mt-2 font-display text-cream ${compact ? "text-lg leading-snug" : "text-2xl leading-tight"}`}
          >
            {t.title}
          </h3>
        </div>
        <ScoreRing value={item.match_score} size={compact ? 52 : 64} />
      </div>

      {/* Meta */}
      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 font-mono text-xs text-muted">
        <span>
          <span className="text-brass-bright">{formatLakh(t.value_lakh)}</span>{" "}
          value
        </span>
        {t.emd_amount !== null && <span>EMD {formatLakh(t.emd_amount)}</span>}
        {t.state && <span>{t.state}</span>}
        {t.days_remaining !== null && (
          <span className={deadlineTone}>
            {t.days_remaining === 0
              ? "Closes today"
              : `${t.days_remaining}d left`}
          </span>
        )}
      </div>

      {/* Sectors */}
      {(t.sector?.length ?? 0) > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {t.sector!.slice(0, 4).map((s) => (
            <Tag key={s}>{s}</Tag>
          ))}
        </div>
      )}

      {/* Why matched */}
      {!compact && (item.match_reasons?.length ?? 0) > 0 && (
        <ul className="mt-4 space-y-1">
          {item.match_reasons!.slice(0, 3).map((r) => (
            <li key={r} className="text-xs text-muted">
              <span className="text-emerald">＋</span> {r}
            </li>
          ))}
        </ul>
      )}

      {/* Description */}
      {!compact && t.description && (
        <p className="mt-4 line-clamp-3 text-sm leading-relaxed text-muted/80">
          {t.description}
        </p>
      )}

      <div className="mt-auto pt-5">
        <div className="flex items-center justify-between">
          {t.department ? (
            <p className="truncate pr-4 font-mono text-[10px] uppercase tracking-wider text-muted/60">
              {t.department}
            </p>
          ) : (
            <span />
          )}
          {item.is_saved && <Stamp tone="emerald">Saved</Stamp>}
        </div>
      </div>
    </div>
  );
}

export function TenderRow({ item }: { item: TenderFeedItem }) {
  const t = item.tender;
  return (
    <div className="dossier group flex items-center gap-5 rounded-lg px-5 py-4 transition-colors hover:border-brass/40">
      <ScoreRing value={item.match_score} size={44} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-cream group-hover:text-brass-bright">
          {t.title}
        </p>
        <p className="mt-0.5 font-mono text-[11px] text-muted">
          {formatLakh(t.value_lakh)} · {t.state ?? "—"} ·{" "}
          {t.days_remaining !== null ? `${t.days_remaining}d left` : "no deadline"}
        </p>
      </div>
      <Link
        href={`/dashboard/tender/${t.id}`}
        className="rounded-md border border-line px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-muted transition-all hover:border-brass/50 hover:text-brass-bright"
      >
        Open →
      </Link>
    </div>
  );
}
