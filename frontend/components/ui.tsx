"use client";

// ── Foedus UI primitives — "The Dossier" design system ───────

import { ReactNode } from "react";

export function Button({
  children,
  onClick,
  variant = "brass",
  disabled,
  type = "button",
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: "brass" | "ghost" | "danger" | "outline";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const base =
    "inline-flex items-center justify-center gap-2 px-5 py-2.5 text-sm font-medium tracking-wide transition-all duration-200 rounded-md disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]";
  const variants = {
    brass:
      "bg-brass text-ink hover:bg-brass-bright shadow-glowbrass font-semibold",
    ghost: "text-muted hover:text-cream hover:bg-surface-2",
    danger:
      "border border-crimson/40 text-crimson hover:bg-crimson/10",
    outline:
      "border border-line text-cream hover:border-brass/50 hover:text-brass-bright",
  };
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Input({
  label,
  type = "text",
  value,
  onChange,
  placeholder,
  required,
  mono,
}: {
  label: string;
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  mono?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[11px] uppercase tracking-[0.18em] text-muted">
        {label}
      </span>
      <input
        type={type}
        value={value}
        required={required}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className={`w-full rounded-md border border-line bg-surface px-4 py-2.5 text-sm text-cream placeholder:text-muted/50 outline-none transition-colors focus:border-brass/60 ${
          mono ? "font-mono" : ""
        }`}
      />
    </label>
  );
}

export function Stamp({
  children,
  tone = "brass",
}: {
  children: ReactNode;
  tone?: "brass" | "emerald" | "crimson" | "azure";
}) {
  const tones = {
    brass: "text-brass",
    emerald: "text-emerald",
    crimson: "text-crimson",
    azure: "text-azure",
  };
  return (
    <span
      className={`dossier-stamp inline-block px-2 py-0.5 font-mono text-[10px] font-medium uppercase ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Tag({ children }: { children: ReactNode }) {
  return (
    <span className="inline-block rounded-full border border-line bg-surface-2 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
      {children}
    </span>
  );
}

export function Hairline() {
  return <div className="hairline w-full" />;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 text-muted">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-brass/30 border-t-brass" />
      {label && <span className="font-mono text-xs tracking-wider">{label}</span>}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <p className="rounded-md border border-crimson/30 bg-crimson/5 px-4 py-2.5 text-sm text-crimson">
      {message}
    </p>
  );
}

export function ScoreRing({
  value,
  size = 64,
  tone,
}: {
  value: number; // 0..1
  size?: number;
  tone?: "auto" | "brass";
}) {
  const pct = Math.round(value * 100);
  const color =
    tone === "brass"
      ? "#D4A853"
      : pct >= 70
        ? "#3DD68C"
        : pct >= 45
          ? "#E8A33D"
          : "#F0526A";
  const r = size / 2 - 5;
  const circ = 2 * Math.PI * r;
  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#1B1F2B"
          strokeWidth="4"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={circ * (1 - value)}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.22,1,0.36,1)" }}
        />
      </svg>
      <span
        className="absolute inset-0 flex items-center justify-center font-mono text-xs font-medium"
        style={{ color }}
      >
        {pct}%
      </span>
    </div>
  );
}

export function formatLakh(v: number | null): string {
  if (v === null || v === undefined) return "—";
  if (v >= 100) return `₹${(v / 100).toFixed(1)} Cr`;
  return `₹${v.toFixed(0)} L`;
}
