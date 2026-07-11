"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { motion } from "framer-motion";
import { isLoggedIn } from "@/lib/api";

const ease = [0.22, 1, 0.36, 1] as const;

export default function Landing() {
  const router = useRouter();

  useEffect(() => {
    if (isLoggedIn()) router.replace("/dashboard");
  }, [router]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.8 }}
        className="mb-6 font-mono text-[11px] uppercase tracking-[0.35em] text-brass"
      >
        Tender Intelligence · Bharat Edition
      </motion.p>

      <motion.h1
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease }}
        className="max-w-3xl text-center font-display text-6xl font-light leading-[1.05] text-cream md:text-8xl"
      >
        Foedus
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.9, ease }}
        className="mt-6 max-w-xl text-center text-lg leading-relaxed text-muted"
      >
        Six AI agents read 80-page government tenders at midnight —{" "}
        <span className="text-cream">so you don&apos;t have to.</span>{" "}
        Discovery, eligibility audit, and a ready-to-submit proposal in
        under two minutes.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.8, ease }}
        className="mt-10 flex items-center gap-4"
      >
        <Link
          href="/register"
          className="rounded-md bg-brass px-7 py-3 text-sm font-semibold tracking-wide text-ink shadow-glowbrass transition-all hover:bg-brass-bright active:scale-[0.98]"
        >
          Open Your Dossier →
        </Link>
        <Link
          href="/login"
          className="rounded-md border border-line px-7 py-3 text-sm text-cream transition-colors hover:border-brass/50"
        >
          Sign In
        </Link>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.6, duration: 1 }}
        className="mt-20 flex items-center gap-8 font-mono text-[10px] uppercase tracking-[0.2em] text-muted/60"
      >
        <span>eprocure.gov.in</span>
        <span className="text-brass/40">◆</span>
        <span>GeM</span>
        <span className="text-brass/40">◆</span>
        <span>CPPP</span>
        <span className="text-brass/40">◆</span>
        <span>State Portals</span>
      </motion.div>
    </main>
  );
}
