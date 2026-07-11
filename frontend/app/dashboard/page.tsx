"use client";

// Daily Matches — Tinder-style swipe deck over AI-matched tenders.

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AnimatePresence,
  motion,
  useMotionValue,
  useTransform,
} from "framer-motion";
import { api } from "@/lib/api";
import type { TenderFeedItem, TenderListResponse } from "@/lib/types";
import TenderCard from "@/components/TenderCard";
import { Button, Spinner } from "@/components/ui";

export default function DailyMatchesPage() {
  const router = useRouter();
  const [deck, setDeck] = useState<TenderFeedItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [exitDir, setExitDir] = useState<1 | -1>(1);

  useEffect(() => {
    api<TenderListResponse>("/tenders/feed?per_page=25&min_score=0")
      .then((res) => setDeck(res.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const top = deck[0];

  const decide = useCallback(
    async (dir: 1 | -1) => {
      if (!top) return;
      setExitDir(dir);
      setDeck((d) => d.slice(1));
      const action = dir === 1 ? "save" : "reject";
      try {
        await api(`/tenders/${top.tender.id}/${action}`, { method: "POST" });
      } catch {
        /* non-blocking */
      }
    },
    [top],
  );

  // Keyboard: ← reject, → save, ↵ open
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowRight") decide(1);
      if (e.key === "ArrowLeft") decide(-1);
      if (e.key === "Enter" && top)
        router.push(`/dashboard/tender/${top.tender.id}`);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [decide, top, router]);

  return (
    <div className="mx-auto max-w-xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
          Today&apos;s Intelligence
        </p>
        <h1 className="mt-2 font-display text-4xl font-light text-cream">
          Daily Matches
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          Swipe right to save · left to dismiss · {deck.length} in the stack
        </p>
      </header>

      {loading ? (
        <div className="flex h-96 items-center justify-center">
          <Spinner label="Pulling today's tenders…" />
        </div>
      ) : !top ? (
        <EmptyDeck />
      ) : (
        <>
          <div className="relative h-[480px]">
            {/* Under-cards peek */}
            {deck.slice(1, 3).map((item, i) => (
              <div
                key={item.tender.id}
                className="absolute inset-0"
                style={{
                  transform: `translateY(${(i + 1) * 12}px) scale(${1 - (i + 1) * 0.035})`,
                  opacity: 1 - (i + 1) * 0.35,
                  zIndex: 2 - i,
                }}
              >
                <TenderCard item={item} />
              </div>
            ))}

            <AnimatePresence>
              <SwipeCard
                key={top.tender.id}
                item={top}
                exitDir={exitDir}
                onDecide={decide}
                onOpen={() =>
                  router.push(`/dashboard/tender/${top.tender.id}`)
                }
              />
            </AnimatePresence>
          </div>

          <div className="mt-8 flex items-center justify-center gap-4">
            <Button variant="danger" onClick={() => decide(-1)}>
              ✕ Dismiss
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push(`/dashboard/tender/${top.tender.id}`)}
            >
              Open Dossier
            </Button>
            <Button onClick={() => decide(1)}>★ Save</Button>
          </div>
        </>
      )}
    </div>
  );
}

function SwipeCard({
  item,
  exitDir,
  onDecide,
  onOpen,
}: {
  item: TenderFeedItem;
  exitDir: 1 | -1;
  onDecide: (dir: 1 | -1) => void;
  onOpen: () => void;
}) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-260, 260], [-10, 10]);
  const saveOpacity = useTransform(x, [60, 160], [0, 1]);
  const rejectOpacity = useTransform(x, [-160, -60], [1, 0]);

  return (
    <motion.div
      className="absolute inset-0 z-10 cursor-grab active:cursor-grabbing"
      style={{ x, rotate }}
      drag="x"
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.9}
      onDragEnd={(_, info) => {
        if (info.offset.x > 130) onDecide(1);
        else if (info.offset.x < -130) onDecide(-1);
      }}
      onDoubleClick={onOpen}
      initial={{ scale: 0.96, y: 14, opacity: 0 }}
      animate={{ scale: 1, y: 0, opacity: 1 }}
      exit={{
        x: exitDir * 480,
        rotate: exitDir * 14,
        opacity: 0,
        transition: { duration: 0.32, ease: "easeIn" },
      }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Verdict stamps revealed by drag */}
      <motion.div
        style={{ opacity: saveOpacity }}
        className="dossier-stamp absolute left-6 top-6 z-20 px-3 py-1 font-mono text-sm font-semibold uppercase text-emerald"
      >
        Saved
      </motion.div>
      <motion.div
        style={{ opacity: rejectOpacity }}
        className="dossier-stamp absolute right-6 top-6 z-20 px-3 py-1 font-mono text-sm font-semibold uppercase text-crimson"
      >
        Rejected
      </motion.div>

      <TenderCard item={item} />
    </motion.div>
  );
}

function EmptyDeck() {
  return (
    <div className="dossier flex h-96 flex-col items-center justify-center rounded-lg text-center">
      <span className="font-display text-5xl text-brass/40">◈</span>
      <p className="mt-4 font-display text-xl text-cream">Stack cleared.</p>
      <p className="mt-1 max-w-xs text-sm text-muted">
        The scraper hunts new tenders every morning at 6 AM. Check your saved
        pile meanwhile.
      </p>
    </div>
  );
}
