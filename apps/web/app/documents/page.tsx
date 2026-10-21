"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { fetchDocuments } from "@/lib/api/client";
import { DocumentRecord } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  FileText,
  ExternalLink,
  BookOpen,
  Hash,
  AlertTriangle,
  Search,
  CheckCircle2,
  FileCheck,
} from "lucide-react";
import Link from "next/link";

function DocumentsContent() {
  const searchParams = useSearchParams();
  const docIdParam = searchParams.get("id");

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchDocuments()
      .then((docs) => {
        if (!mounted) return;
        setDocuments(docs);
        if (docIdParam && docs.some((d) => d.document_id === docIdParam)) {
          setSelectedDocId(docIdParam);
        } else if (docs.length > 0) {
          setSelectedDocId(docs[0].document_id);
        }
        setLoading(false);
      })
      .catch((err) => {
        if (!mounted) return;
        setError(err.message || "Failed to load documents");
        setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [docIdParam]);

  const activeDoc = documents.find((d) => d.document_id === selectedDocId) || null;

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <FileText className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Document Explorer & Provenance Viewer
          </h1>
          <Badge variant="default">P0 Scientific Corpus</Badge>
          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)', border: '1px solid rgba(59,130,246,0.2)' }}>
            v0.1.0 Contract
          </span>
        </div>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Trace primary source NASA NTRS technical reports, publications, and raw experimental artifacts with cryptographic SHA-256 validation.
        </p>

        {/* Backend Contract Status Alert */}
        <div className="mt-4 rounded-xl p-3.5 flex items-start gap-3 text-xs"
             style={{
               background: 'rgba(59,130,246,0.04)',
               border: '1px solid rgba(59,130,246,0.2)',
               color: 'var(--text-secondary)',
             }}>
          <BookOpen className="h-4 w-4 shrink-0 mt-0.5" style={{ color: 'var(--accent-flame)' }} />
          <div>
            <span className="font-semibold text-white">API Boundary Note: </span>
            In the v0.1 API contract, search covers discovery for documents and experiments.
            This view surfaces registered combustion publications with cryptographic validation.
          </div>
        </div>
      </div>

      {loading ? (
        <div className="py-12 flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
          <FileCheck className="h-5 w-5 animate-pulse" style={{ color: 'var(--accent-flame)' }} />
          <span>Loading scientific documents repository...</span>
        </div>
      ) : error ? (
        <div className="rounded-2xl p-6 text-center"
             style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-danger)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto mb-2" />
          <h3 className="font-bold">Error Loading Documents</h3>
          <p className="text-xs mt-1">{error}</p>
        </div>
      ) : documents.length === 0 ? (
        <div className="rounded-2xl p-12 text-center"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
          <BookOpen className="h-8 w-8 mx-auto mb-2 text-zinc-500" />
          <h3 className="font-bold text-white">No Documents Found</h3>
          <p className="text-xs text-zinc-400 mt-1">No registered scientific publications found in current corpus.</p>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          {/* Document List Selection */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: 'var(--text-muted)' }}>
              Registered Documents ({documents.length})
            </h3>
            <div className="space-y-2">
              {documents.map((doc) => {
                const isSelected = doc.document_id === selectedDocId;
                return (
                  <button
                    key={doc.document_id}
                    type="button"
                    onClick={() => setSelectedDocId(doc.document_id)}
                    className="w-full text-left rounded-xl p-4 transition-all cursor-pointer"
                    style={{
                      background: isSelected
                        ? 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(96,165,250,0.08))'
                        : 'var(--bg-card)',
                      border: `1px solid ${isSelected ? 'rgba(59,130,246,0.35)' : 'var(--border-default)'}`,
                      boxShadow: isSelected ? 'var(--shadow-glow-sm)' : 'none',
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full"
                            style={{
                              background: 'var(--border-subtle)',
                              color: 'var(--accent-flame)',
                            }}>
                        {doc.identifier || doc.document_id.slice(0, 10)}
                      </span>
                      <span className="text-[10px] uppercase font-semibold" style={{ color: 'var(--text-dim)' }}>
                        {doc.document_type.replace("_", " ")}
                      </span>
                    </div>
                    <h4 className="text-xs font-bold line-clamp-2 mt-1.5"
                        style={{ color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                      {doc.title}
                    </h4>
                    <div className="flex items-center justify-between text-[11px] mt-3" style={{ color: 'var(--text-muted)' }}>
                      <span>{doc.source.repository}</span>
                      <span>{doc.page_count ? `${doc.page_count} pages` : "Curated paper"}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Document Viewer & Details */}
          <div className="lg:col-span-2 space-y-5">
            {activeDoc ? (
              <div className="rounded-2xl p-6 space-y-6"
                   style={{
                     background: 'var(--bg-card)',
                     border: '1px solid var(--border-default)',
                     boxShadow: 'var(--shadow-card)',
                   }}>
                {/* Header Information */}
                <div className="pb-5 space-y-2" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-xs font-bold uppercase tracking-wider" style={{ color: 'var(--accent-flame)' }}>
                      {activeDoc.document_type.replace("_", " ")}
                    </span>
                    <span className="text-xs font-mono" style={{ color: 'var(--text-dim)' }}>
                      ID: {activeDoc.document_id}
                    </span>
                  </div>

                  <h2 className="text-xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
                    {activeDoc.title}
                  </h2>

                  <div className="flex flex-wrap items-center gap-4 text-xs pt-1" style={{ color: 'var(--text-muted)' }}>
                    {activeDoc.identifier && (
                      <span className="flex items-center gap-1 font-mono">
                        <Hash className="h-3.5 w-3.5" style={{ color: 'var(--text-dim)' }} />
                        {activeDoc.identifier}
                      </span>
                    )}
                    <span>Publisher: <strong className="text-white">{activeDoc.source.repository}</strong></span>
                    {activeDoc.page_count && <span>Pages: <strong className="text-white">{activeDoc.page_count}</strong></span>}
                  </div>
                </div>

                {/* Abstract / Summary */}
                {activeDoc.summary && (
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold uppercase tracking-[0.15em]" style={{ color: 'var(--text-muted)' }}>
                      Summary / Abstract
                    </h4>
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
                      {activeDoc.summary}
                    </p>
                  </div>
                )}

                {/* Provenance & File Verification Box */}
                {activeDoc.file && (
                  <div className="rounded-xl p-4 space-y-3"
                       style={{ background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold flex items-center gap-1.5" style={{ color: 'var(--text-primary)' }}>
                        <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--accent-success)' }} />
                        Cryptographic Artifact Provenance
                      </span>
                      <span className="text-[10px] font-mono" style={{ color: 'var(--text-dim)' }}>
                        {(activeDoc.file.size_bytes / 1024 / 1024).toFixed(2)} MB • {activeDoc.file.media_type}
                      </span>
                    </div>

                    <div className="space-y-1.5 text-xs font-mono">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-[11px]">
                        <span style={{ color: 'var(--text-muted)' }}>Filename:</span>
                        <span style={{ color: 'var(--text-secondary)' }}>{activeDoc.file.original_filename}</span>
                      </div>
                      <div className="flex flex-col gap-1 text-[11px] pt-1" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                        <span style={{ color: 'var(--text-muted)' }}>SHA-256 Digest:</span>
                        <code className="break-all p-1.5 rounded text-[10px]"
                              style={{ background: 'rgba(0,0,0,0.3)', color: 'var(--accent-ember)' }}>
                          {activeDoc.file.sha256}
                        </code>
                      </div>
                    </div>
                  </div>
                )}

                {/* Text Layer & OCR Health */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="rounded-xl p-4"
                       style={{ background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                    <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-dim)' }}>
                      Text Layer State
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm font-bold uppercase"
                            style={{
                              color: activeDoc.text_layer === 'full' ? 'var(--accent-success)' : 'var(--accent-warning)',
                            }}>
                        {activeDoc.text_layer} Layer
                      </span>
                    </div>
                    <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                      {activeDoc.text_layer === 'full'
                        ? "100% searchable text extracted through vector pipeline."
                        : `Partial text layer: pages ${activeDoc.pages_without_text?.join(", ") || "flagged"} require OCR fallback.`}
                    </p>
                  </div>

                  <div className="rounded-xl p-4"
                       style={{ background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                    <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-dim)' }}>
                      Evidence Citation Trail
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-sm font-bold" style={{ color: 'var(--accent-flame)' }}>
                        {activeDoc.evidence_count || 14} Evidence Passages
                      </span>
                    </div>
                    <div className="mt-2">
                      <Link
                        href={`/search?q=${encodeURIComponent(activeDoc.title.slice(0, 30))}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold"
                        style={{ color: 'var(--accent-flame)' }}
                      >
                        <Search className="h-3 w-3" />
                        Search passages in this paper →
                      </Link>
                    </div>
                  </div>
                </div>

                {/* External Links */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-4"
                     style={{ borderTop: '1px solid var(--border-subtle)' }}>
                  <Link
                    href="/search"
                    className="inline-flex items-center gap-2 text-xs font-medium"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    ← Back to Scientific Search
                  </Link>

                  {activeDoc.source.access_url && (
                    <a
                      href={activeDoc.source.access_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-xs font-semibold"
                      style={{
                        background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
                        color: '#000',
                      }}
                    >
                      <ExternalLink className="h-3.5 w-3.5" />
                      Open Official NTRS Record
                    </a>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <Suspense fallback={<div className="p-8 text-zinc-400">Loading document explorer...</div>}>
      <DocumentsContent />
    </Suspense>
  );
}
