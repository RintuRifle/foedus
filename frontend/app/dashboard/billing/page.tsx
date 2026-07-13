"use client";

// Billing — plan status + Razorpay Checkout upgrade flow.

import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { api } from "@/lib/api";
import { Button, ErrorNote, Hairline, Spinner, Stamp } from "@/components/ui";

interface BillingState {
  plan: string;
  evals_used: number;
  eval_limit: number | null;
  period_end: string | null;
}

interface OrderResponse {
  order_id: string;
  amount: number;
  currency: string;
  key_id: string;
  name: string;
  description: string;
  prefill_email: string;
}

interface PlanInfo {
  name: string;
  price_inr: number;
  evals_per_month: number | null;
  features: string[];
}

declare global {
  interface Window {
    Razorpay?: new (options: Record<string, unknown>) => { open: () => void };
  }
}

function loadRazorpay(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) return resolve(true);
    const script = document.createElement("script");
    script.src = "https://checkout.razorpay.com/v1/checkout.js";
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingState | null>(null);
  const [plans, setPlans] = useState<Record<string, PlanInfo> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paying, setPaying] = useState(false);
  const [justUpgraded, setJustUpgraded] = useState(false);

  const refresh = useCallback(() => {
    api<BillingState>("/payments/subscription").then(setBilling).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    api<Record<string, PlanInfo>>("/payments/plans").then(setPlans).catch(() => {});
  }, [refresh]);

  async function upgrade() {
    setError(null);
    setPaying(true);
    try {
      const ok = await loadRazorpay();
      if (!ok) throw new Error("Could not load payment gateway");

      const order = await api<OrderResponse>("/payments/create-order", {
        method: "POST",
      });

      const rzp = new window.Razorpay!({
        key: order.key_id,
        amount: order.amount,
        currency: order.currency,
        name: order.name,
        description: order.description,
        order_id: order.order_id,
        prefill: { email: order.prefill_email },
        theme: { color: "#D4A853", backdrop_color: "#08090C" },
        handler: async (resp: {
          razorpay_order_id: string;
          razorpay_payment_id: string;
          razorpay_signature: string;
        }) => {
          try {
            await api("/payments/verify", { method: "POST", body: resp });
            setJustUpgraded(true);
            refresh();
          } catch (e) {
            setError(
              e instanceof Error ? e.message : "Verification failed — contact support",
            );
          } finally {
            setPaying(false);
          }
        },
        modal: { ondismiss: () => setPaying(false) },
      });
      rzp.open();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Payment failed");
      setPaying(false);
    }
  }

  const isPro = billing?.plan === "pro";

  return (
    <div className="mx-auto max-w-3xl">
      <header className="mb-8">
        <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-brass">
          Membership
        </p>
        <h1 className="mt-2 font-display text-4xl font-light text-cream">
          Billing
        </h1>
      </header>

      {justUpgraded && (
        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          className="dossier mb-6 rounded-lg border-emerald/40 p-5 text-center"
        >
          <p className="font-display text-xl text-emerald">
            Welcome to Pro. 🎖️
          </p>
          <p className="mt-1 text-sm text-muted">
            Unlimited evaluations unlocked. Ab tender machine full speed pe.
          </p>
        </motion.div>
      )}

      {error && (
        <div className="mb-6">
          <ErrorNote message={error} />
        </div>
      )}

      {!billing || !plans ? (
        <Spinner label="Fetching billing state…" />
      ) : (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Free card */}
          <PlanCard
            info={plans.free}
            active={!isPro}
            footer={
              !isPro ? (
                <p className="font-mono text-xs text-muted">
                  {billing.evals_used}/{billing.eval_limit} evaluations used this month
                </p>
              ) : null
            }
          />

          {/* Pro card */}
          <PlanCard
            info={plans.pro}
            active={isPro}
            highlight
            footer={
              isPro ? (
                <p className="font-mono text-xs text-emerald">
                  Active until{" "}
                  {billing.period_end
                    ? new Date(billing.period_end).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })
                    : "—"}
                </p>
              ) : (
                <Button onClick={upgrade} disabled={paying} className="w-full">
                  {paying ? "Opening checkout…" : "Upgrade — ₹999/month"}
                </Button>
              )
            }
          />
        </div>
      )}

      <p className="mt-8 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-muted/60">
        Payments secured by Razorpay · UPI / Cards / NetBanking
      </p>
    </div>
  );
}

function PlanCard({
  info,
  active,
  highlight,
  footer,
}: {
  info: PlanInfo;
  active: boolean;
  highlight?: boolean;
  footer: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className={`dossier flex flex-col rounded-lg p-7 ${
        highlight ? "border-brass/40 shadow-glowbrass" : ""
      }`}
    >
      <div className="flex items-center justify-between">
        <h2 className="font-display text-2xl text-cream">{info.name}</h2>
        {active && <Stamp tone="emerald">Current</Stamp>}
      </div>
      <p className="mt-2 font-display text-4xl text-brass-bright">
        ₹{info.price_inr}
        <span className="font-sans text-sm text-muted">/month</span>
      </p>

      <div className="my-5">
        <Hairline />
      </div>

      <ul className="flex-1 space-y-2.5">
        {info.features.map((f) => (
          <li key={f} className="flex gap-2.5 text-sm text-muted">
            <span className="text-emerald">✓</span> {f}
          </li>
        ))}
      </ul>

      <div className="mt-6">{footer}</div>
    </motion.div>
  );
}
