"use client";

// Proposal viewer + editor with export to PDF/Markdown.

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, API_URL, getToken } from "@/lib/api";
import type { Proposal } from "@/lib/types";
import { Button, ErrorNote, Spinner, Stamp } from "@/components/ui";

export default function ProposalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Proposal>(`/proposals/${id}`)
      .then((p) => {
        setProposal(p);
        setDraft(p.content_md ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Load failed"));
  }, [id]);

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updated = await api<Proposal>(`/proposals/${id}`, {
        method: "PATCH",
        body: { content_md: draft },
      });
      setProposal(updated);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function download(kind: "pdf" | "md") {
    try {
      const res = await fetch(`${API_URL}/proposals/${id}/export.${kind}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Export failed (${res.status})`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${proposal?.title ?? "proposal"}.${kind}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  if (error && !proposal) return <ErrorNote message={error} />;
  if (!proposal)
    return (
      <div className="flex h-96 items-center justify-center">
        <Spinner label="Opening proposal…" />
      </div>
    );

  return (
    <div className="mx-auto max-w-3xl">
      <button
        onClick={() => router.back()}
        className="mb-6 font-mono text-[11px] uppercase tracking-wider text-muted hover:text-cream"
      >
        ← Back
      </button>

      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <Stamp>{proposal.status} · v{proposal.version}</Stamp>
          <h1 className="mt-3 font-display text-3xl leading-tight text-cream">
            {proposal.title ?? "Technical Proposal"}
          </h1>
        </div>
        <div className="flex shrink-0 gap-2">
          {editing ? (
            <>
              <Button variant="ghost" onClick={() => setEditing(false)}>
                Cancel
              </Button>
              <Button onClick={save} disabled={saving}>
                {saving ? "Saving…" : "Save Draft"}
              </Button>
            </>
          ) : (
            <>
              <Button variant="outline" onClick={() => setEditing(true)}>
                ✎ Edit
              </Button>
              <Button variant="outline" onClick={() => download("md")}>
                .md
              </Button>
              <Button onClick={() => download("pdf")}>Export PDF</Button>
            </>
          )}
        </div>
      </header>

      {error && (
        <div className="mb-4">
          <ErrorNote message={error} />
        </div>
      )}

      <div className="dossier rounded-lg p-8 shadow-dossier">
        {editing ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            spellCheck={false}
            className="h-[65vh] w-full resize-none bg-transparent font-mono text-sm leading-relaxed text-cream outline-none"
          />
        ) : (
          <article className="prose-dossier">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {proposal.content_md ?? "*Empty proposal*"}
            </ReactMarkdown>
          </article>
        )}
      </div>

      <p className="mt-4 text-center font-mono text-[10px] uppercase tracking-[0.2em] text-muted/60">
        AI-drafted · review before submission · every edit bumps the version
      </p>
    </div>
  );
}
