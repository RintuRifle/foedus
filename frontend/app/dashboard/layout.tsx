"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, clearTokens, isLoggedIn } from "@/lib/api";
import type { User } from "@/lib/types";

const NAV = [
  { href: "/dashboard", label: "Daily Matches", code: "01" },
  { href: "/dashboard/saved", label: "Saved", code: "02" },
  { href: "/dashboard/pipeline", label: "Pipeline", code: "03" },
  { href: "/dashboard/proposals", label: "Proposals", code: "04" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    if (!isLoggedIn()) {
      router.replace("/login");
      return;
    }
    api<User>("/auth/me").then(setUser).catch(() => {});
  }, [router]);

  return (
    <div className="flex min-h-screen">
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside className="fixed inset-y-0 left-0 z-20 flex w-60 flex-col border-r border-line bg-surface/70 backdrop-blur-md">
        <div className="px-6 py-7">
          <Link href="/dashboard" className="font-display text-2xl text-brass-bright">
            Foedus
          </Link>
          <p className="mt-1 font-mono text-[9px] uppercase tracking-[0.3em] text-muted">
            Tender War Room
          </p>
        </div>

        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((item) => {
            const active =
              item.href === "/dashboard"
                ? pathname === "/dashboard"
                : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-all ${
                  active
                    ? "bg-brass/10 text-brass-bright"
                    : "text-muted hover:bg-surface-2 hover:text-cream"
                }`}
              >
                <span
                  className={`font-mono text-[10px] ${active ? "text-brass" : "text-muted/50"}`}
                >
                  {item.code}
                </span>
                {item.label}
                {active && (
                  <span className="ml-auto h-1 w-1 rounded-full bg-brass" />
                )}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-line px-6 py-5">
          {user && (
            <>
              <p className="truncate text-sm text-cream">
                {user.full_name ?? user.email}
              </p>
              <p className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
                {user.plan} plan · {user.evals_used} evals used
              </p>
            </>
          )}
          <button
            onClick={() => {
              clearTokens();
              router.push("/");
            }}
            className="mt-3 font-mono text-[10px] uppercase tracking-wider text-muted transition-colors hover:text-crimson"
          >
            Sign out ✕
          </button>
        </div>
      </aside>

      {/* ── Content ──────────────────────────────────────── */}
      <main className="ml-60 flex-1 px-10 py-8">{children}</main>
    </div>
  );
}
