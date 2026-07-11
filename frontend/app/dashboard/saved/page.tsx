"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import type { TenderFeedItem, TenderListResponse } from "@/lib/types";
import { TenderRow } from "@/components/TenderCard";
import { Spinner } from "@/components/ui";

export default function SavedPage() {
  const [items, setItems] = useState<TenderFeedItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<TenderListResponse>("/tenders/saved?per_page=50")
      .then((res) => setItems(res.items))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
          Bookmarked Dossiers
        </p>
        <h1 className="mt-2 font-display text-4xl font-light text-cream">
          Saved Tenders
        </h1>
      </header>

      {loading ? (
        <Spinner label="Opening the vault…" />
      ) : items.length === 0 ? (
        <p className="text-sm text-muted">
          Nothing saved yet. Swipe right on Daily Matches to build your pile.
        </p>
      ) : (
        <div className="space-y-3">
          {items.map((item, i) => (
            <motion.div
              key={item.tender.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
            >
              <TenderRow item={item} />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
