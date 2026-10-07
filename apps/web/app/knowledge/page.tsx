"use client";

import { useEffect, useState } from "react";
import { fetchKnowledge } from "@/lib/api/client";
import { KnowledgeEntity } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Network, Link as LinkIcon, ShieldCheck, FileCheck, Search, Share2 } from "lucide-react";
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
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
            style={{ color: 'var(--text-primary)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <Network className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          Knowledge Explorer
        </h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Browse extracted scientific entities, relations, and the evidence connecting them.
        </p>
      </div>

      {/* Search */}
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
            transition: 'border-color var(--transition-fast)',
          }}
          onFocus={(e) => { e.currentTarget.style.borderColor = 'rgba(59,130,246,0.4)'; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border-default)'; }}
        />
      </div>

      {loading ? (
        <div className="flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
          <Share2 className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          Loading knowledge graph...
        </div>
      ) : (
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
                transition: 'all var(--transition-default)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(59,130,246,0.2)';
                e.currentTarget.style.transform = 'translateY(-2px)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-default)';
                e.currentTarget.style.transform = 'translateY(0)';
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
                {entity.status === "verified" && (
                  <Badge variant="success">
                    <ShieldCheck className="h-3 w-3 mr-1" /> Verified
                  </Badge>
                )}
              </div>

              <div className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                {entity.definition}
              </div>

              {entity.aliases.length > 0 && (
                <div>
                  <span className="text-[10px] font-bold uppercase"
                        style={{ color: 'var(--text-dim)' }}>Aliases:</span>
                  <div className="flex flex-wrap gap-1.5 mt-1.5">
                    {entity.aliases.map((alias) => (
                      <span key={alias} className="px-2 py-0.5 rounded-md text-[11px]"
                            style={{
                              background: 'var(--border-subtle)',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-secondary)',
                            }}>
                        {alias}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div className="pt-4 mt-2" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <span className="text-[10px] font-bold uppercase tracking-[0.12em]"
                      style={{ color: 'var(--accent-flame)', opacity: 0.8 }}>
                  Extracted Relations
                </span>
                <ul className="mt-2.5 space-y-3">
                  {entity.relations.map((rel, idx) => (
                    <li key={idx} className="text-xs">
                      <div className="flex items-center gap-1.5" style={{ color: 'var(--text-secondary)' }}>
                        <LinkIcon className="h-3 w-3" style={{ color: 'var(--text-dim)' }} />
                        <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                          {rel.predicate}
                        </span>
                        <span className="font-semibold">{rel.target_label}</span>
                        <span className="ml-auto text-[10px]" style={{ color: 'var(--text-dim)' }}>
                          {(rel.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      {rel.evidence_ids.length > 0 && (
                        <div className="mt-1.5 ml-4 flex gap-1.5">
                          {rel.evidence_ids.map((eid) => (
                            <Link
                              key={eid}
                              href={`/evidence?id=${eid}`}
                              className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-md"
                              style={{
                                background: 'rgba(59,130,246,0.06)',
                                border: '1px solid rgba(59,130,246,0.15)',
                                color: 'var(--accent-flame)',
                                transition: 'all var(--transition-fast)',
                              }}
                            >
                              <FileCheck className="h-3 w-3" />
                              Cite
                            </Link>
                          ))}
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
