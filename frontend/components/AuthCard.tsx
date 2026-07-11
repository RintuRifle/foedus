"use client";

// Shared auth screen used by /login and /register.

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { api, setTokens } from "@/lib/api";
import type { TokenResponse } from "@/lib/types";
import { Button, ErrorNote, Hairline, Input } from "@/components/ui";

export default function AuthCard({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await api<TokenResponse>(
        isRegister ? "/auth/register" : "/auth/login",
        {
          method: "POST",
          auth: false,
          body: isRegister
            ? { email, password, full_name: fullName || null }
            : { email, password },
        },
      );
      setTokens(tokens);
      router.push(isRegister ? "/onboarding" : "/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="dossier w-full max-w-md rounded-lg p-8 shadow-dossier"
      >
        <Link
          href="/"
          className="font-display text-2xl text-brass-bright transition-colors hover:text-brass"
        >
          Foedus
        </Link>
        <h1 className="mt-5 font-display text-3xl font-light text-cream">
          {isRegister ? "Open your dossier" : "Welcome back"}
        </h1>
        <p className="mt-1.5 text-sm text-muted">
          {isRegister
            ? "3 free AI evaluations every month. No card needed."
            : "Your agents have been waiting."}
        </p>

        <div className="my-6">
          <Hairline />
        </div>

        <form onSubmit={submit} className="space-y-4">
          {isRegister && (
            <Input
              label="Full Name"
              value={fullName}
              onChange={setFullName}
              placeholder="Priya Sharma"
            />
          )}
          <Input
            label="Email"
            type="email"
            value={email}
            onChange={setEmail}
            placeholder="you@company.in"
            required
          />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={setPassword}
            placeholder={isRegister ? "Min 8 characters" : "••••••••"}
            required
          />

          {error && <ErrorNote message={error} />}

          <Button type="submit" disabled={loading} className="w-full">
            {loading
              ? "Authenticating…"
              : isRegister
                ? "Create Account"
                : "Sign In"}
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-muted">
          {isRegister ? "Already have an account? " : "New to Foedus? "}
          <Link
            href={isRegister ? "/login" : "/register"}
            className="text-brass hover:text-brass-bright"
          >
            {isRegister ? "Sign in" : "Create one"}
          </Link>
        </p>
      </motion.div>
    </main>
  );
}
