"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowRight, ChevronLeft, ChevronRight, Network, Search } from "lucide-react";
import { Empty, ErrorNote, EvidenceChips, Loading, SectionTitle } from "@/components/fire/FireUi";
import {
  ALL_PREDICATES, ENTITY_TYPES, PREDICATE_LABEL, TYPE_LABEL, edgeValue, entityLabel, getEntity, listEntities,
  type GraphEdge, type GraphEntity, type GraphEntityDetail, type GraphEntityList, type GraphEntityType, type GraphPredicate,
} from "@/lib/api/graph";

const PAGE_SIZE = 25;
const MAX_EDGES = 200;
const GROUP_PREVIEW = 10;   // links shown per group before "Show all"

type Loaded<T> = { key: string; data?: T; error?: string };

const card = { background: "var(--bg-card)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-card)" } as const;
const chip = (active: boolean) => ({
  background: active ? "rgba(59,130,246,0.12)" : "var(--bg-elevated)",
  border: `1px solid ${active ? "rgba(59,130,246,0.4)" : "var(--border-default)"}`,
  color: active ? "var(--accent-flame)" : "var(--text-secondary)",
});

function KnowledgeContent() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const selectedId = searchParams.get("id");

  const [type, setType] = useState<GraphEntityType | "">("investigation");
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [depth, setDepth] = useState(1);
  const [predicates, setPredicates] = useState<GraphPredicate[]>([]);
  const [retry, setRetry] = useState(0);

  const listKey = `${type}|${query}|${page}|${retry}`;
  const [list, setList] = useState<Loaded<GraphEntityList> | null>(null);
  useEffect(() => {
    let live = true;
    listEntities({ type: type || undefined, q: query || undefined, page, page_size: PAGE_SIZE })
      .then((data) => { if (live) setList({ key: listKey, data }); })
      .catch((e: Error) => { if (live) setList({ key: listKey, error: e.message }); });
    return () => { live = false; };
  }, [type, query, page, listKey]);

  const detailKey = `${selectedId}|${depth}|${predicates.join(",")}|${retry}`;
  const [detail, setDetail] = useState<Loaded<GraphEntityDetail> | null>(null);
  useEffect(() => {
    if (!selectedId) return;
    let live = true;
    getEntity(selectedId, { depth, predicate: predicates, max_edges: MAX_EDGES })
      .then((data) => { if (live) setDetail({ key: detailKey, data }); })
      .catch((e: Error) => { if (live) setDetail({ key: detailKey, error: e.message }); });
    return () => { live = false; };
  }, [selectedId, depth, predicates, detailKey]);

  // Below the lg breakpoint the details sit under the list. After a tap, bring them into view once they
  // have loaded: scrolling earlier is undone by the reflow when the content arrives.
  const detailRef = useRef<HTMLElement>(null);
  const pendingScroll = useRef(false);
  const select = (entityId: string) => {
    pendingScroll.current = typeof window !== "undefined" && window.innerWidth < 1024;
    router.replace(`${pathname}?id=${encodeURIComponent(entityId)}`, { scroll: false });
  };
  useEffect(() => {
    if (!pendingScroll.current || !detail || detail.key !== detailKey) return;
    pendingScroll.current = false;
    detailRef.current?.scrollIntoView({ block: "start" });
  }, [detail, detailKey]);

  const listLoading = !list || list.key !== listKey;
  const detailLoading = !!selectedId && (!detail || detail.key !== detailKey);

  return (
    <div className="flex w-full flex-col space-y-6 p-4 sm:p-6 lg:p-8">
      <div className="animate-fade-in-up">
        <h1 className="flex items-center gap-2.5 text-2xl font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)" }}>
            <Network className="h-4 w-4" style={{ color: "var(--accent-flame)" }} aria-hidden="true" />
          </div>
          Knowledge Graph
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Investigations, flight tests, fuels, recorded conditions and outcomes, linked as NASA&apos;s PSI tables and
          ISA-Tab records state them. Every link cites the table cell it was read from. Platforms, instruments and links
          from NASA reports are not extracted.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        {/* Entity browser */}
        <section aria-label="Entities" className="space-y-4 rounded-2xl p-4" style={card}>
          <div className="flex flex-wrap gap-1.5" role="group" aria-label="Entity type">
            {[{ value: "" as const, label: "All" }, ...ENTITY_TYPES].map((t) => (
              <button key={t.value || "all"} type="button" aria-pressed={type === t.value}
                      onClick={() => { setType(t.value); setPage(1); }}
                      className="rounded-full px-2.5 py-1 text-[11px] font-semibold" style={chip(type === t.value)}>
                {t.label}
              </button>
            ))}
          </div>
          <form onSubmit={(e) => { e.preventDefault(); setQuery(draft.trim()); setPage(1); }} className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4" style={{ color: "var(--text-dim)" }} aria-hidden="true" />
            <input id="knowledge-search" type="search" value={draft} onChange={(e) => setDraft(e.target.value)}
                   placeholder="Name or alias, e.g. heptane" aria-label="Search entities by name or alias"
                   className="w-full rounded-xl py-2 pl-9 pr-3 text-sm"
                   style={{ background: "var(--border-subtle)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }} />
          </form>

          {listLoading ? <Loading label="Loading entities..." />
            : list?.error ? <ErrorNote message={list.error} onRetry={() => setRetry((n) => n + 1)} />
            : !list?.data?.items.length ? (
              <Empty message={query ? `No entity matches "${query}".` : "The knowledge graph is empty: run the ingest (it builds the graph)."} />
            ) : (
              <>
                <ul className="space-y-1">
                  {list.data.items.map((entity) => (
                    <li key={entity.entity_id}>
                      <button type="button" onClick={() => select(entity.entity_id)}
                              aria-current={entity.entity_id === selectedId ? "true" : undefined}
                              className="flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm"
                              style={entity.entity_id === selectedId
                                ? { background: "rgba(59,130,246,0.1)", color: "var(--text-primary)" }
                                : { color: "var(--text-secondary)" }}>
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{entityLabel(entity)}</span>
                          <span className="text-[11px]" style={{ color: "var(--text-dim)" }}>{TYPE_LABEL[entity.entity_type]}</span>
                        </span>
                        <span className="shrink-0 text-[11px]" style={{ color: "var(--text-dim)" }}
                              title="Links to other entities">
                          {entity.relation_count ?? 0} links
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
                <Pager page={page} totalPages={list.data.pagination.total_pages} total={list.data.pagination.total_items}
                       onPage={setPage} />
              </>
            )}
        </section>

        {/* Selected entity and its neighbourhood */}
        <section ref={detailRef} aria-label="Selected entity" className="min-w-0 scroll-mt-20 rounded-2xl p-4 sm:p-5" style={card}>
          {!selectedId ? (
            <Empty message="Choose an entity to see what it links to, with the NASA evidence for each link." />
          ) : detailLoading ? <Loading label="Walking the graph..." />
            : detail?.error ? <ErrorNote message={detail.error} onRetry={() => setRetry((n) => n + 1)} />
            : detail?.data ? (
              <EntityDetail detail={detail.data} depth={depth} onDepth={setDepth} predicates={predicates}
                            onPredicates={setPredicates} onSelect={select} />
            ) : null}
        </section>
      </div>
    </div>
  );
}

function Pager({ page, totalPages, total, onPage }: { page: number; totalPages: number; total: number; onPage: (p: number) => void }) {
  if (totalPages <= 1) return <p className="text-[11px]" style={{ color: "var(--text-dim)" }}>{total} entities</p>;
  return (
    <div className="flex items-center justify-between text-[11px]" style={{ color: "var(--text-dim)" }}>
      <button type="button" disabled={page <= 1} onClick={() => onPage(page - 1)} aria-label="Previous page"
              className="rounded-md p-1 disabled:opacity-40" style={{ border: "1px solid var(--border-default)" }}>
        <ChevronLeft className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
      <span>Page {page} of {totalPages} · {total} entities</span>
      <button type="button" disabled={page >= totalPages} onClick={() => onPage(page + 1)} aria-label="Next page"
              className="rounded-md p-1 disabled:opacity-40" style={{ border: "1px solid var(--border-default)" }}>
        <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}

function EntityDetail({ detail, depth, onDepth, predicates, onPredicates, onSelect }: {
  detail: GraphEntityDetail; depth: number; onDepth: (d: number) => void;
  predicates: GraphPredicate[]; onPredicates: (p: GraphPredicate[]) => void; onSelect: (id: string) => void;
}) {
  const { entity, neighbourhood } = detail;
  const byId = useMemo(() => new Map(neighbourhood.entities.map((e) => [e.entity_id, e])), [neighbourhood.entities]);
  const groups = useMemo(() => {
    const out = new Map<GraphPredicate, GraphEdge[]>();
    for (const edge of neighbourhood.edges) out.set(edge.predicate, [...(out.get(edge.predicate) ?? []), edge]);
    return ALL_PREDICATES.filter((p) => out.has(p)).map((p) => [p, out.get(p)!] as const);
  }, [neighbourhood.edges]);
  const properties = Object.entries(entity.properties).filter(([, v]) => v !== null && v !== "" && typeof v !== "object");
  const togglePredicate = (p: GraphPredicate) =>
    onPredicates(predicates.includes(p) ? predicates.filter((x) => x !== p) : [...predicates, p]);
  // Counts include the selected entity itself; leave it out of "what it links to".
  const reachable = Object.entries(neighbourhood.reachable_by_type)
    .map(([t, n]) => [t, t === entity.entity_type ? (n ?? 0) - 1 : n ?? 0] as const)
    .filter(([, n]) => n > 0);

  return (
    <div className="space-y-5">
      <div>
        <div className="text-[11px] font-bold uppercase tracking-[0.12em]" style={{ color: "var(--text-dim)" }}>
          {TYPE_LABEL[entity.entity_type]}
        </div>
        <h2 className="mt-1 text-xl font-bold" style={{ color: "var(--text-primary)" }}>{entityLabel(entity)}</h2>
        {detail.resolved_from && (
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            The requested entity was merged into this one; its links are shown here.
          </p>
        )}
        {entity.aliases.length > 0 && (
          <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
            Also written as: {entity.aliases.map((a) => <code key={a} className="mr-1.5">{a}</code>)}
          </p>
        )}
        {properties.length > 0 && (
          <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
            {properties.map(([k, v]) => (
              <div key={k} className="contents">
                <dt style={{ color: "var(--text-dim)" }}>{k.replaceAll("_", " ")}</dt>
                <dd className="break-words" style={{ color: "var(--text-secondary)", fontFamily: "var(--font-mono)" }}>{String(v)}</dd>
              </div>
            ))}
          </dl>
        )}
        {entity.evidence_ids.length > 0 && (
          <div className="mt-3"><EvidenceChips evidence={entity.evidence_ids.map((evidence_id) => ({ evidence_id }))} /></div>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-2 text-[11px]" style={{ color: "var(--text-dim)" }}>
        <span>Hops:</span>
        {[1, 2].map((d) => (
          <button key={d} type="button" aria-pressed={depth === d} onClick={() => onDepth(d)}
                  className="rounded-full px-2.5 py-1 font-semibold" style={chip(depth === d)}>{d}</button>
        ))}
        <span className="ml-2">Links:</span>
        {ALL_PREDICATES.map((p) => (
          <button key={p} type="button" aria-pressed={predicates.includes(p)} onClick={() => togglePredicate(p)}
                  className="rounded-full px-2.5 py-1 font-semibold" style={chip(predicates.includes(p))}>
            {PREDICATE_LABEL[p]}
          </button>
        ))}
      </div>

      <p className="text-xs" style={{ color: "var(--text-muted)" }}>
        Within {neighbourhood.depth} hop{neighbourhood.depth > 1 ? "s" : ""}: {reachable.length
          ? reachable.map(([t, n]) => `${n} ${TYPE_LABEL[t as GraphEntityType].toLowerCase()}${n === 1 ? "" : "s"}`).join(", ")
          : "nothing linked"}.
        {neighbourhood.truncated && ` Showing the nearest ${neighbourhood.edges.length} links; narrow by link type or use 1 hop to see the rest.`}
      </p>

      {groups.length === 0 ? <Empty message="No links match these filters." /> : groups.map(([predicate, edges]) => (
        <EdgeGroup key={`${entity.entity_id}|${predicate}`} predicate={predicate} edges={edges} byId={byId}
                   current={entity.entity_id} onSelect={onSelect} />
      ))}
    </div>
  );
}

function EdgeGroup({ predicate, edges, byId, current, onSelect }: {
  predicate: GraphPredicate; edges: GraphEdge[]; byId: Map<string, GraphEntity>; current: string; onSelect: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? edges : edges.slice(0, GROUP_PREVIEW);
  return (
    <div>
      <SectionTitle title={`${PREDICATE_LABEL[predicate]} · ${edges.length}`} />
      <ul className="-mt-2 space-y-1.5">
        {shown.map((edge) => {
          const value = edgeValue(edge);
          return (
            <li key={edge.relation_id} className="flex flex-wrap items-center gap-x-2 gap-y-1 rounded-lg px-3 py-2 text-sm"
                style={{ background: "var(--bg-elevated)" }}>
              <EntityLink entity={byId.get(edge.subject_id)} current={current} onSelect={onSelect} />
              <ArrowRight className="h-3.5 w-3.5 shrink-0" style={{ color: "var(--text-dim)" }} aria-label={PREDICATE_LABEL[predicate]} />
              <EntityLink entity={byId.get(edge.object_id)} current={current} onSelect={onSelect} />
              {value && <span className="text-xs" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>= {value}</span>}
              <span className="ml-auto">
                {edge.evidence_id && <EvidenceChips evidence={[{ evidence_id: edge.evidence_id }]} />}
              </span>
            </li>
          );
        })}
      </ul>
      {edges.length > GROUP_PREVIEW && (
        <button type="button" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded}
                className="mt-2 rounded-lg px-3 py-1.5 text-xs font-semibold"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-secondary)" }}>
          {expanded ? "Show fewer" : `Show all ${edges.length}`}
        </button>
      )}
    </div>
  );
}

function EntityLink({ entity, current, onSelect }: { entity?: GraphEntity; current: string; onSelect: (id: string) => void }) {
  if (!entity) return <span style={{ color: "var(--text-dim)" }}>unknown</span>;
  if (entity.entity_id === current) return <span className="font-semibold" style={{ color: "var(--text-primary)" }}>{entityLabel(entity)}</span>;
  return (
    <button type="button" onClick={() => onSelect(entity.entity_id)} className="font-medium underline-offset-2 hover:underline"
            style={{ color: "var(--accent-flame)" }} title={TYPE_LABEL[entity.entity_type]}>
      {entityLabel(entity)}
    </button>
  );
}

export default function KnowledgePage() {
  return (
    <Suspense fallback={<div className="p-8"><Loading label="Loading..." /></div>}>
      <KnowledgeContent />
    </Suspense>
  );
}
