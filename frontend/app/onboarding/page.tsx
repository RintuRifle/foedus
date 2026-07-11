"use client";

// ✨ Magic Onboarding — drop a brochure, watch the AI build your profile.

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { API_URL, getToken } from "@/lib/api";
import type { BrochureParse } from "@/lib/types";
import { Button, Hairline, Stamp, Tag } from "@/components/ui";

type Phase = "drop" | "parsing" | "review";

const PARSE_LINES = [
  "Opening brochure…",
  "Reading company overview…",
  "Extracting sectors & capabilities…",
  "Finding turnover & team size…",
  "Cataloguing certifications…",
  "Summarising past projects…",
];

export default function OnboardingPage() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>("drop");
  const [dragOver, setDragOver] = useState(false);
  const [lineIdx, setLineIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [parsed, setParsed] = useState<BrochureParse | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setError(null);
      setPhase("parsing");
      setLineIdx(0);

      // Cycle status lines while the AI works
      const ticker = setInterval(
        () => setLineIdx((i) => Math.min(i + 1, PARSE_LINES.length - 1)),
        2200,
      );

      try {
        const fd = new FormData();
        fd.append("file", file);
        const res = await fetch(`${API_URL}/company/onboard-brochure`, {
          method: "POST",
          headers: { Authorization: `Bearer ${getToken()}` },
          body: fd,
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail ?? `Upload failed (${res.status})`);
        }
        setParsed(await res.json());
        setPhase("review");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Parsing failed");
        setPhase("drop");
      } finally {
        clearInterval(ticker);
      }
    },
    [],
  );

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16">
      <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
        Step 1 of 1 · Company Profile
      </p>
      <h1 className="mt-3 font-display text-4xl font-light text-cream">
        Don&apos;t fill a form.
        <br />
        <span className="text-brass-bright">Drop your brochure.</span>
      </h1>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted">
        Company profile PDF, capability statement, ya purani brochure — the AI
        reads it and builds your profile. Agents use this to hunt tenders for
        you.
      </p>

      <div className="my-8">
        <Hairline />
      </div>

      <AnimatePresence mode="wait">
        {phase === "drop" && (
          <motion.div
            key="drop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
          >
            <div
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                const f = e.dataTransfer.files[0];
                if (f) handleFile(f);
              }}
              className={`dossier flex cursor-pointer flex-col items-center justify-center rounded-lg px-8 py-16 text-center transition-all duration-300 ${
                dragOver
                  ? "border-brass shadow-glowbrass"
                  : "hover:border-brass/40"
              }`}
            >
              <span className="font-display text-5xl text-brass/60">⌖</span>
              <p className="mt-4 text-sm text-cream">
                Drop your brochure PDF here
              </p>
              <p className="mt-1 font-mono text-[11px] uppercase tracking-wider text-muted">
                or click to browse · max 15 MB
              </p>
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleFile(f);
                }}
              />
            </div>

            {error && (
              <p className="mt-4 rounded-md border border-crimson/30 bg-crimson/5 px-4 py-2.5 text-sm text-crimson">
                {error}
              </p>
            )}

            <button
              onClick={() => router.push("/dashboard")}
              className="mt-6 font-mono text-[11px] uppercase tracking-wider text-muted transition-colors hover:text-cream"
            >
              Skip for now →
            </button>
          </motion.div>
        )}

        {phase === "parsing" && (
          <motion.div
            key="parsing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="dossier scan-container rounded-lg px-8 py-16 text-center"
          >
            <Stamp>Analysing</Stamp>
            <div className="mt-8 space-y-2">
              {PARSE_LINES.slice(0, lineIdx + 1).map((line, i) => (
                <motion.p
                  key={line}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: i === lineIdx ? 1 : 0.35 }}
                  className="font-mono text-xs tracking-wider text-brass-bright"
                >
                  {i < lineIdx ? "✓" : "▸"} {line}
                </motion.p>
              ))}
            </div>
          </motion.div>
        )}

        {phase === "review" && parsed && (
          <motion.div
            key="review"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="dossier rounded-lg p-7 shadow-dossier"
          >
            <div className="flex items-start justify-between">
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-muted">
                  Extracted Profile
                </p>
                <h2 className="mt-1 font-display text-2xl text-cream">
                  {parsed.name ?? "Your Company"}
                </h2>
              </div>
              <Stamp tone={parsed.confidence >= 0.7 ? "emerald" : "brass"}>
                {Math.round(parsed.confidence * 100)}% confident
              </Stamp>
            </div>

            {parsed.description && (
              <p className="mt-4 text-sm leading-relaxed text-muted">
                {parsed.description}
              </p>
            )}

            <div className="mt-5 grid grid-cols-3 gap-4">
              <Fact label="Turnover" value={parsed.turnover_lakh ? `₹${parsed.turnover_lakh} L` : "—"} />
              <Fact label="Team" value={parsed.emp_count ? `${parsed.emp_count}` : "—"} />
              <Fact label="Experience" value={parsed.years_experience ? `${parsed.years_experience} yrs` : "—"} />
            </div>

            {(parsed.sector?.length ?? 0) > 0 && (
              <div className="mt-5 flex flex-wrap gap-2">
                {parsed.sector!.map((s) => (
                  <Tag key={s}>{s}</Tag>
                ))}
              </div>
            )}

            {(parsed.iso_certs?.length ?? 0) > 0 && (
              <p className="mt-4 font-mono text-xs text-emerald">
                ✓ {parsed.iso_certs!.join(" · ")}
              </p>
            )}

            <div className="my-6">
              <Hairline />
            </div>

            <div className="flex items-center justify-between">
              <p className="text-xs text-muted">
                Saved to your profile. Edit anytime from settings.
              </p>
              <Button onClick={() => router.push("/dashboard")}>
                Enter War Room →
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </main>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted">
        {label}
      </p>
      <p className="mt-1 font-display text-xl text-brass-bright">{value}</p>
    </div>
  );
}
