"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, ExternalLink, FileText } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { END_STATE_LABELS, ErrorNote, InsightCard, Loading, RelevanceBar, ScenarioNote, SectionTitle } from "@/components/fire/FireUi";
import { fetchInvestigation, fmtRange, type InvestigationDetail, type Scenario, type ScenarioQuery } from "@/lib/api/fireSafety";

function readQuery(): ScenarioQuery {
  const p = new URLSearchParams(window.location.search);
  const o2 = p.get("o2_fraction"), kpa = p.get("pressure_kpa");
  return o2 && kpa ? { o2_fraction: Number(o2), pressure_kpa: Number(kpa) } : { scenario: p.get("scenario") ?? "iss_nominal" };
}

export default function InvestigationPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<{ investigation: InvestigationDetail; scenario: Scenario } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let live = true;
    queueMicrotask(() => setSearch(window.location.search));
    fetchInvestigation(id, readQuery())
      .then((d) => { if (live) { setData(d); setError(null); } })
      .catch((e) => { if (live) setError(e instanceof Error ? e.message : "Could not load."); });
    return () => { live = false; };
  }, [id, attempt]);
  const load = () => setAttempt((n) => n + 1);

  const inv = data?.investigation;
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
      <Link href={`/${search}`} className="inline-flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
        <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" /> Back to the dashboard
      </Link>
      {error && <ErrorNote message={error} onRetry={load} />}
      {!inv && !error && <Loading label="Loading investigation…" />}
      {inv && data && (
        <>
          <header className="flex flex-col gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--accent-ember)" }}>
              {inv.flight_platform ?? "Platform not recorded"} · {inv.dates ?? "dates not recorded"}
            </p>
            <h1 className="text-2xl font-bold">{inv.acronym} · {inv.title}</h1>
            <div className="flex flex-wrap gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
              {inv.persistent_identifier && <span style={{ fontFamily: "var(--font-mono)" }}>{inv.persistent_identifier}</span>}
              {inv.license && <span>License {inv.license}</span>}
              {inv.access_url && (
                <a href={inv.access_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">
                  NASA PSI page <ExternalLink className="h-3 w-3" aria-hidden="true" />
                </a>
              )}
            </div>
          </header>

          {inv.relevance && (
            <Card>
              <SectionTitle title={`Relevance to: ${data.scenario.name}`} subtitle="Evidence relevance, not risk." />
              <RelevanceBar relevance={inv.relevance} />
              <ul className="mt-3 list-disc pl-5 text-xs" style={{ color: "var(--text-secondary)" }}>
                {inv.relevance.explanation.map((e) => <li key={e}>{e}</li>)}
              </ul>
              <div className="mt-3"><ScenarioNote scenario={data.scenario} /></div>
            </Card>
          )}

          <Card>
            <SectionTitle title="Summary, in NASA's words" subtitle="Verbatim from the investigation's PSI ISA-Tab metadata. Each section links to its evidence row." />
            {inv.summary_sections.length === 0 ? (
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>No NASA metadata has been ingested for this investigation.</p>
            ) : (
              <div className="flex flex-col gap-4">
                {inv.summary_sections.map((s) => (
                  <section key={s.heading}>
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold">{s.heading}</h3>
                      <Link href={`/evidence?id=${s.evidence_id}`} className="inline-flex items-center gap-1 text-[11px]" style={{ color: "var(--accent-ember)" }}>
                        <FileText className="h-3 w-3" aria-hidden="true" /> source
                      </Link>
                    </div>
                    <p className="mt-1 whitespace-pre-line text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{s.text}</p>
                  </section>
                ))}
              </div>
            )}
          </Card>

          <Card>
            <SectionTitle title="What the published flight-test table covers" subtitle={inv.coverage_note ?? undefined} />
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
              {[
                ["Flight tests", String(inv.data.tests)],
                ["O₂ fraction", fmtRange(inv.data.o2_fraction, 3) + (inv.data.o2_approximate ? " (approximate)" : "")],
                ["Pressure", fmtRange(inv.data.pressure_kpa, 1, "kPa")],
                ["Flow velocity", fmtRange(inv.data.flow_velocity_m_s, 2, "m/s")],
                ["Fuels / materials", `${inv.data.distinct_fuels_or_materials ?? inv.data.fuels_or_materials.length} distinct`],
                ["End states", inv.data.end_states ? Object.entries(inv.data.end_states).map(([k, v]) => `${v} ${END_STATE_LABELS[k as keyof typeof END_STATE_LABELS]?.toLowerCase() ?? k}`).join(", ") : "not recorded in the table"],
              ].map(([k, v]) => (
                <div key={k} className="rounded-lg p-3" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                  <dt className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{k}</dt>
                  <dd className="mt-1" style={{ fontFamily: "var(--font-mono)" }}>{v}</dd>
                </div>
              ))}
            </dl>
            {inv.data.quality_flags && Object.keys(inv.data.quality_flags).length > 0 && (
              <p className="mt-3 text-xs" style={{ color: "var(--text-muted)" }}>
                Data-quality flags: {Object.entries(inv.data.quality_flags).map(([k, v]) => `${k.replaceAll("_", " ")} (${v})`).join(", ")}.
              </p>
            )}
            {inv.data.fuels_or_materials.length > 0 && (
              <p className="mt-3 text-xs" style={{ color: "var(--text-secondary)" }}>
                Most tested: {inv.data.fuels_or_materials.slice(0, 6).map((f) => `${f.name} (${f.tests})`).join(" · ")}
              </p>
            )}
          </Card>

          {inv.insights.length > 0 && (
            <Card>
              <SectionTitle title="Findings from this investigation's data" />
              <div className="grid gap-3">{inv.insights.map((i) => <InsightCard key={i.insight_id} insight={i} />)}</div>
            </Card>
          )}

          {inv.publications.length > 0 && (
            <Card>
              <SectionTitle title="Publications listed by NASA" subtitle={`${inv.publications.length} links from the ISA-Tab metadata.`} />
              <ul className="flex flex-col gap-1 text-xs">
                {inv.publications.slice(0, 15).map((p) => (
                  <li key={p}><a href={p} target="_blank" rel="noreferrer" className="break-all hover:underline" style={{ color: "var(--accent-ember)" }}>{p}</a></li>
                ))}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
