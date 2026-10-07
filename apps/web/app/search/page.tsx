"use client";

import { useState } from "react";
import { searchResearch } from "@/lib/api/client";
import { SearchResponse } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  Search as SearchIcon,
  FileText,
  ExternalLink,
  Filter,
  Fingerprint,
  Globe,
  BarChart3,
} from "lucide-react";
import Link from "next/link";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<SearchResponse>({
    request_id: "",
    retrieval: { mode: "lexical", corpus_version: "" },
    pagination: { page: 1, total_items: 0, total_pages: 0 },
    results: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [domainFilter, setDomainFilter] = useState<"combustion" | "all">("combustion");

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await searchResearch(query, { domain: domainFilter });
      setData(res);
    } catch {
      setError("Search is unavailable right now.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
            style={{ color: 'var(--text-primary)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <SearchIcon className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          Scientific Evidence Search
        </h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Search indexed NASA NTRS technical papers, PSI experiment matrices, and research corpora.
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-3 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
        <div className="relative flex-1">
          <SearchIcon className="absolute left-4 top-3.5 h-4 w-4" style={{ color: 'var(--text-dim)' }} />
          <input
            id="search-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search experiments, fuels, microgravity conditions, or papers..."
            className="w-full rounded-xl py-3 pl-11 pr-4 text-sm"
            style={{
              background: 'var(--border-subtle)',
              border: '1px solid var(--border-default)',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-sans)',
              outline: 'none',
              transition: 'border-color var(--transition-fast)',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)'; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
          />
        </div>
        <button
          id="search-btn"
          type="submit"
          disabled={loading}
          className="rounded-xl px-6 py-3 text-sm font-semibold"
          style={{
            background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
            color: '#000',
            transition: 'all var(--transition-fast)',
            boxShadow: '0 0 12px rgba(59,130,246,0.2)',
          }}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Domain Policy */}
      <div className="flex items-center justify-between rounded-xl px-4 py-2.5 text-xs animate-fade-in-up"
           style={{
             animationDelay: '150ms',
             background: 'var(--border-subtle)',
             border: '1px solid var(--border-subtle)',
             color: 'var(--text-muted)',
           }}>
        <div className="flex items-center gap-2">
          <Filter className="h-3.5 w-3.5" style={{ color: 'var(--text-dim)' }} />
          <span>Domain Filter:</span>
          <button
            onClick={() => setDomainFilter(domainFilter === "combustion" ? "all" : "combustion")}
            className="font-semibold underline underline-offset-2"
            style={{ color: domainFilter === "combustion" ? 'var(--accent-flame)' : 'var(--text-secondary)' }}
          >
            {domainFilter === "combustion" ? "Combustion Only" : "All Sources"}
          </button>
        </div>
        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-dim)' }}>
          {data.retrieval.mode} · {data.pagination.total_items} results
        </span>
      </div>

      {/* Results */}
      {error && (
        <p className="text-sm" style={{ color: 'var(--accent-danger)' }}>{error}</p>
      )}
      <div className="space-y-4">
        {data.results.map((result, i) => (
          <div
            key={result.result_id}
            className="rounded-2xl p-5 space-y-4 animate-fade-in-up"
            style={{
              animationDelay: `${200 + i * 80}ms`,
              background: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-card)',
              transition: 'all var(--transition-default)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(59,130,246,0.2)';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-default)';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              <div className="space-y-2">
                <div className="flex items-center gap-2.5">
                  <Badge variant={result.result_type === "document" ? "default" : "flame"}>
                    {result.result_type.toUpperCase()}
                  </Badge>
                  <h2 className="text-base font-semibold tracking-tight"
                      style={{ color: 'var(--text-primary)' }}>
                    {result.title}
                  </h2>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span className="flex items-center gap-1" style={{ color: 'var(--accent-flame)' }}>
                    <Globe className="h-3 w-3" />
                    {result.source.repository} ({result.source.short_name})
                  </span>
                  {result.locator && (
                    <span className="rounded px-2 py-0.5 text-[11px]"
                          style={{
                            fontFamily: 'var(--font-mono)',
                            background: 'var(--border-subtle)',
                            border: '1px solid var(--border-subtle)',
                            color: 'var(--text-secondary)',
                          }}>
                      {result.locator.label}
                    </span>
                  )}
                  <span className="flex items-center gap-1" style={{ color: 'var(--text-dim)' }}>
                    <BarChart3 className="h-3 w-3" />
                    Score: {result.score.toFixed(2)}
                  </span>
                </div>
              </div>

              {result.evidence_id && (
                <Link
                  href={`/evidence?id=${result.evidence_id}`}
                  className="inline-flex shrink-0 items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold"
                  style={{
                    background: 'rgba(59,130,246,0.08)',
                    border: '1px solid rgba(59,130,246,0.2)',
                    color: 'var(--accent-flame)',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  <Fingerprint className="h-3.5 w-3.5" />
                  Inspect Evidence
                </Link>
              )}
            </div>

            {/* Excerpt */}
            <blockquote
              className="rounded-xl p-4 text-sm leading-relaxed italic"
              style={{
                background: 'var(--border-subtle)',
                borderLeft: '3px solid rgba(59,130,246,0.4)',
                color: 'var(--text-secondary)',
              }}
            >
              &quot;{result.snippet}&quot;
            </blockquote>

            {/* Source Reference */}
            <div className="flex items-center justify-between pt-3 text-xs"
                 style={{
                   borderTop: '1px solid var(--border-subtle)',
                   color: 'var(--text-dim)',
                 }}>
              <span style={{ fontFamily: 'var(--font-mono)' }}>Source ID: {result.source.source_id}</span>
              {result.source.access_url && (
                <a
                  href={result.source.access_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1"
                  style={{ color: 'var(--text-muted)', transition: 'color var(--transition-fast)' }}
                >
                  NASA Repository <ExternalLink className="h-3 w-3" />
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
