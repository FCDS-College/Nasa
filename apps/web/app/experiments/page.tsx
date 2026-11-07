"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Empty, ErrorNote, Loading } from "@/components/fire/FireUi";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const SOURCES = [
  { id: "FF-PSI-69", label: "FLEX (droplets)" },
  { id: "FF-PSI-25", label: "BASS-II (solids)" },
  { id: "FF-PSI-107", label: "SPICE (gas co-flow)" },
  { id: "FF-PSI-98", label: "SAFFIRE-I (large-scale fabric)" },
];
const PAGE_SIZE = 12;

interface Condition { variable: string; value_numeric: number | null; value_text: string | null; unit_original: string | null; evidence_id: string }
interface Experiment { experiment_id: string; test_id: string; investigation: string | null; fuel_or_material: string | null; gravity_regime: string; conditions?: Condition[] }

async function getJson(path: string) {
  const res = await fetch(`${API_BASE}/api/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`The Flame API answered ${res.status}.`);
  return res.json();
}

export default function FlightTestBrowser() {
  const [source, setSource] = useState(SOURCES[0].id);
  const [page, setPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const key = `${source}:${page}:${attempt}`;
  const [loaded, setLoaded] = useState<{ key: string; items: Experiment[]; total: number } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);

  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const list = await getJson(`experiments?source_id=${source}&page=${page}&page_size=${PAGE_SIZE}`);
        const details = await Promise.all(list.items.map((e: Experiment) => getJson(`experiments/${e.experiment_id}`)));
        if (live) setLoaded({ key, items: details.map((d) => d.experiment), total: list.pagination.total_items });
      } catch (e) {
        if (live) setFailure({ key, message: e instanceof Error ? e.message : "Could not load flight tests." });
      }
    })();
    return () => { live = false; };
  }, [source, page, key]);

  const items = loaded?.key === key ? loaded.items : null;
  const total = loaded?.total ?? 0;
  const error = failure?.key === key ? failure.message : null;
  const load = () => setAttempt((n) => n + 1);
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
      <header>
        <h1 className="flex items-center gap-2 text-2xl font-bold"><FlaskConical className="h-5 w-5" style={{ color: "var(--accent-flame)" }} aria-hidden="true" /> Flight Test Browser</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-muted)" }}>
          Every row of NASA&apos;s published experimental tables, as ingested: values exactly as published, each linked to its source cell.
        </p>
      </header>
      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Investigation">
        {SOURCES.map((s) => (
          <button key={s.id} role="tab" aria-selected={source === s.id} onClick={() => { setSource(s.id); setPage(1); }}
                  className="rounded-lg px-3 py-1.5 text-xs font-medium"
                  style={{ background: source === s.id ? "rgba(59,130,246,0.14)" : "var(--bg-elevated)",
                           border: `1px solid ${source === s.id ? "rgba(59,130,246,0.4)" : "var(--border-default)"}`, color: "var(--text-primary)" }}>
            {s.label}
          </button>
        ))}
        <Link href={`/investigations/${source}`} className="ml-auto self-center text-xs" style={{ color: "var(--accent-ember)" }}>Investigation summary →</Link>
      </div>
      {error && <ErrorNote message={error} onRetry={load} />}
      {!items && !error && <Loading label="Loading flight tests…" />}
      {items && items.length === 0 && <Empty message="No flight tests ingested for this investigation. Run the ingest (DEMO_RUNBOOK.md)." />}
      {items && items.length > 0 && (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            {items.map((e) => (
              <Card key={e.experiment_id}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="text-sm font-semibold">{e.investigation} test {e.test_id}</h2>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{e.fuel_or_material ?? "fuel not recorded"} · {e.gravity_regime}</p>
                  </div>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-1.5 text-[11px]">
                  {(e.conditions ?? []).filter((c) => c.value_numeric !== null || c.value_text).slice(0, 10).map((c) => (
                    <div key={c.evidence_id} className="rounded-md px-2 py-1" style={{ background: "var(--bg-elevated)" }}>
                      <dt style={{ color: "var(--text-dim)" }}>{c.variable.replaceAll("_", " ")}</dt>
                      <dd style={{ fontFamily: "var(--font-mono)" }}>
                        <Link href={`/evidence?id=${c.evidence_id}`} className="hover:underline">{c.value_numeric ?? c.value_text}</Link>
                      </dd>
                    </div>
                  ))}
                </dl>
              </Card>
            ))}
          </div>
          <nav className="flex items-center justify-center gap-3 text-xs" aria-label="Pages">
            <button disabled={page <= 1} onClick={() => setPage(page - 1)} className="rounded-lg px-3 py-1.5 disabled:opacity-40" style={{ border: "1px solid var(--border-default)" }}>Previous</button>
            <span style={{ color: "var(--text-muted)" }}>Page {page} of {pages} · {total} tests</span>
            <button disabled={page >= pages} onClick={() => setPage(page + 1)} className="rounded-lg px-3 py-1.5 disabled:opacity-40" style={{ border: "1px solid var(--border-default)" }}>Next</button>
          </nav>
        </>
      )}
    </div>
  );
}
