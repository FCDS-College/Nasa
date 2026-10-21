"use client";

import { useEffect, useState } from "react";
import { fetchKnowledge } from "@/lib/api/client";
import { KnowledgeEntity } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Network, Search, Share2 } from "lucide-react";
import Link from "next/link";

export default function KnowledgePage() {
  const [entities, setEntities] = useState<KnowledgeEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchKnowledge().then((data) => {
      setEntities(data);
      setLoading(false);
    });
  }, []);

  const filtered = entities.filter(
    (e) =>
      e.label.toLowerCase().includes(search.toLowerCase()) ||
      e.aliases.some((a) => a.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <Network className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Knowledge Base
          </h1>
          <Badge variant="default">Phase 2 Planned</Badge>
        </div>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Browse extracted scientific combustion entities, physical relations, and the empirical evidence connecting them.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center gap-3 py-16" style={{ color: 'var(--text-muted)' }}>
          <Share2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          <span>Checking knowledge graph service status...</span>
        </div>
      ) : entities.length === 0 ? (
        /* Honest empty state per Task R3 (No mockKnowledge fallback) */
        <div className="rounded-2xl p-12 text-center max-w-xl mx-auto space-y-4 animate-fade-in-up"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl mx-auto"
               style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid var(--border-subtle)' }}>
            <Network className="h-8 w-8" style={{ color: 'var(--accent-flame)', opacity: 0.8 }} />
          </div>
          <div>
            <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md"
                  style={{ background: 'var(--border-subtle)', color: 'var(--text-secondary)' }}>
              Not available yet
            </span>
            <h3 className="text-base font-bold text-white mt-3">Knowledge Graph Endpoint Deferred</h3>
            <p className="text-xs mt-2 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              The AURA-backed knowledge extraction graph endpoint is not part of the current v0.1 API contract (<code>docs/api/FRONTEND_API_CONTRACT.md §6</code>).
              Scientific discovery is currently powered by the hybrid search engine.
            </p>
          </div>
          <div className="pt-2">
            <Link
              href="/search"
              className="inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-xs font-semibold cursor-pointer"
              style={{
                background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
                color: '#000',
              }}
            >
              <Search className="h-3.5 w-3.5" />
              Explore Evidence via Search
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* Search Filter */}
          <div className="relative max-w-md animate-fade-in-up" style={{ animationDelay: '80ms' }}>
            <Search className="absolute left-4 top-3.5 h-4 w-4" style={{ color: 'var(--text-dim)' }} />
            <input
              id="knowledge-search"
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search entities or aliases..."
              className="w-full rounded-xl py-3 pl-11 pr-4 text-sm"
              style={{
                background: 'var(--border-subtle)',
                border: '1px solid var(--border-default)',
                color: 'var(--text-primary)',
                outline: 'none',
              }}
            />
          </div>

          <div className="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((entity, i) => (
              <div
                key={entity.id}
                className="rounded-2xl p-5 space-y-4 animate-fade-in-up"
                style={{
                  animationDelay: `${150 + i * 80}ms`,
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  boxShadow: 'var(--shadow-card)',
                }}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
                      {entity.label}
                    </h3>
                    <div className="text-[10px] mt-1 uppercase tracking-[0.15em] font-bold"
                         style={{ color: 'var(--text-dim)' }}>
                      {entity.type}
                    </div>
                  </div>
                  <Badge variant={entity.status === "verified" ? "success" : "default"}>
                    {entity.status.toUpperCase()}
                  </Badge>
                </div>

                <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                  {entity.definition}
                </p>

                {entity.aliases.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {entity.aliases.map((alias) => (
                      <span
                        key={alias}
                        className="text-[10px] px-2 py-0.5 rounded-full"
                        style={{
                          background: 'var(--border-subtle)',
                          color: 'var(--text-secondary)',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {alias}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
