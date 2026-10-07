"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { fetchEvidence } from "@/lib/api/client";
import { EvidenceRecord } from "@/lib/api/types";

import { Badge } from "@/components/ui/Badge";
import {
  ShieldCheck,
  ExternalLink,
  BookOpen,
  Hash,
  FileSearch,
  Fingerprint,
} from "lucide-react";

function EvidenceContent() {
  const searchParams = useSearchParams();
  const idFromUrl = searchParams.get("id");
  const [evidenceId, setEvidenceId] = useState(idFromUrl || "");
  const [evidence, setEvidence] = useState<EvidenceRecord | null>(null);

  const [draft, setDraft] = useState(idFromUrl || "");
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    if (!evidenceId) return;
    fetchEvidence(evidenceId).then((res) => {
      setEvidence(res);
      setNotFound(res === null);
    });
  }, [evidenceId]);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <Fingerprint className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Evidence Inspector
          </h1>
          {evidence && (
            <Badge variant={evidence.review_status === "verified" ? "success" : "default"}>
              {evidence.review_status === "verified" ? "Verified Record" : "Unreviewed Record"}
            </Badge>
          )}
        </div>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Trace scientific claims back to exact documents, pages, raw experimental tables, and SHA-256 signatures.
        </p>
      </div>

      {/* Evidence lookup */}
      <form
        onSubmit={(e) => { e.preventDefault(); setEvidenceId(draft.trim()); }}
        className="flex gap-2 animate-fade-in-up"
        style={{ animationDelay: '100ms' }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Evidence ID (from a search result)"
          className="flex-1 rounded-lg px-3 py-2 text-xs"
          style={{ fontFamily: 'var(--font-mono)', background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)', color: 'var(--text-primary)' }}
        />
        <button type="submit" className="rounded-lg px-4 py-2 text-xs font-semibold"
                style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)', border: '1px solid rgba(59,130,246,0.3)' }}>
          Inspect
        </button>
      </form>
      {notFound && (
        <p className="text-sm" style={{ color: 'var(--accent-danger)' }}>Evidence record not found.</p>
      )}

      {evidence && (
        <div className="space-y-6 animate-fade-in-up" style={{ animationDelay: '150ms' }}>
          <div className="rounded-2xl p-6 space-y-6"
               style={{
                 background: 'var(--bg-card)',
                 border: '1px solid var(--border-default)',
                 boxShadow: 'var(--shadow-card)',
               }}>
            {/* Header Info */}
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 pb-5"
                 style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div>
                <span className="text-[10px] font-bold uppercase tracking-[0.15em]"
                      style={{ color: 'var(--accent-flame)' }}>
                  {evidence.kind.replace("_", " ")}
                </span>
                <h2 className="mt-1 text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                  {evidence.citation}
                </h2>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Extracted via:{" "}
                  <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                    {evidence.extraction_method}
                  </span>{" "}
                  ({evidence.transformation_id})
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold"
                      style={{
                        background: 'rgba(16,185,129,0.08)',
                        color: 'var(--accent-success)',
                        border: '1px solid rgba(16,185,129,0.2)',
                      }}>
                  <ShieldCheck className="h-4 w-4" />
                  {evidence.review_status.toUpperCase()}
                </span>
              </div>
            </div>

            {/* Excerpt */}
            <div className="space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-[0.15em]"
                    style={{ color: 'var(--text-muted)' }}>
                Verbatim Scientific Content
              </span>
              {evidence.excerpt && (
                <div className="rounded-xl p-5 text-sm leading-relaxed italic"
                     style={{
                       background: 'var(--border-subtle)',
                       border: '1px solid var(--border-default)',
                       color: 'var(--text-primary)',
                       fontFamily: 'Georgia, serif',
                     }}>
                  &quot;{evidence.excerpt}&quot;
                </div>
              )}
              {evidence.value && (
                <div className="rounded-xl p-4 flex items-center gap-4"
                     style={{
                       background: 'var(--border-subtle)',
                       border: '1px solid var(--border-default)',
                     }}>
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Parsed Value:</span>
                  <span className="text-xl font-bold"
                        style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-flame)' }}>
                    {evidence.value.text} {evidence.value.unit}
                  </span>
                </div>
              )}
            </div>

            {/* Provenance Grid */}
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="rounded-xl p-4 space-y-2"
                   style={{
                     background: 'var(--border-subtle)',
                     border: '1px solid var(--border-subtle)',
                   }}>
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] flex items-center gap-1.5"
                      style={{ color: 'var(--text-muted)' }}>
                  <BookOpen className="h-3.5 w-3.5" style={{ color: 'var(--accent-flame)' }} />
                  Exact Locator & Citation
                </span>
                <div className="text-xs space-y-1"
                     style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  <p>Type: {evidence.locator?.type}</p>
                  <p>Label: {evidence.locator?.label}</p>
                  {evidence.locator?.section && <p>Section: {evidence.locator.section}</p>}
                </div>
              </div>

              <div className="rounded-xl p-4 space-y-2"
                   style={{
                     background: 'var(--border-subtle)',
                     border: '1px solid var(--border-subtle)',
                   }}>
                <span className="text-[10px] font-bold uppercase tracking-[0.12em] flex items-center gap-1.5"
                      style={{ color: 'var(--text-muted)' }}>
                  <Hash className="h-3.5 w-3.5" style={{ color: 'var(--accent-aurora)' }} />
                  Cryptographic Integrity (SHA-256)
                </span>
                <div className="text-xs space-y-1"
                     style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  <p className="truncate">Hash: {evidence.file?.sha256}</p>
                  <p>File: {evidence.file?.original_filename}</p>
                  <p>Size: {((evidence.file?.size_bytes || 0) / 1024).toFixed(1)} KB</p>
                </div>
              </div>
            </div>

            {/* Source Reference */}
            {evidence.source && (
              <div className="flex flex-wrap items-center justify-between pt-4 text-xs"
                   style={{
                     borderTop: '1px solid var(--border-subtle)',
                     color: 'var(--text-muted)',
                   }}>
                <span>
                  Repository: <strong style={{ color: 'var(--text-secondary)' }}>{evidence.source.repository}</strong>{" "}
                  (Source ID: {evidence.source.source_id})
                </span>
                {evidence.source.access_url && (
                  <a
                    href={evidence.source.access_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1"
                    style={{ color: 'var(--accent-flame)', transition: 'opacity var(--transition-fast)' }}
                  >
                    Open in NASA Archives <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvidencePage() {
  return (
    <Suspense fallback={
      <div className="p-8" style={{ color: 'var(--text-muted)' }}>
        <FileSearch className="h-5 w-5 animate-spin inline mr-2" style={{ color: 'var(--accent-flame)' }} />
        Loading evidence viewer...
      </div>
    }>
      <EvidenceContent />
    </Suspense>
  );
}
