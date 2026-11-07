"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Database, Flame, FlaskConical, Layers, Rocket, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  Empty, ErrorNote, InsightCard, Loading, RelevanceBar, ScenarioNote, ScenarioPicker, SectionTitle,
} from "@/components/fire/FireUi";
import {
  fetchCounts, fetchFlexOutcome, fetchInsights, fetchInvestigations, fmtRange,
  type Insight, type InvestigationList, type ScenarioQuery,
} from "@/lib/api/fireSafety";

function readQuery(): ScenarioQuery {
  if (typeof window === "undefined") return { scenario: "iss_nominal" };
  const p = new URLSearchParams(window.location.search);
  const o2 = p.get("o2_fraction"), kpa = p.get("pressure_kpa");
  if (o2 && kpa) return { o2_fraction: Number(o2), pressure_kpa: Number(kpa) };
  return { scenario: p.get("scenario") ?? "iss_nominal" };
}

function toSearch(q: ScenarioQuery): string {
  return q.o2_fraction !== undefined ? `?o2_fraction=${q.o2_fraction}&pressure_kpa=${q.pressure_kpa}` : `?scenario=${q.scenario ?? "iss_nominal"}`;
}

export default function FireSafetyDashboard() {
  const [query, setQuery] = useState<ScenarioQuery | null>(null);
  const [result, setResult] = useState<{ key: string; list: InvestigationList; insights: Insight[] } | null>(null);
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [documents, setDocuments] = useState<number | null>(null);
  const [modelScore, setModelScore] = useState<{ f1: number; base: number } | null>(null);
  useEffect(() => { queueMicrotask(() => setQuery(readQuery())); }, []);

  const key = query ? `${toSearch(query)}#${attempt}` : "";
  useEffect(() => {
    if (!query) return;
    window.history.replaceState(null, "", toSearch(query));
    let live = true;
    Promise.all([fetchInvestigations(query), fetchInsights(query)])
      .then(([l, i]) => { if (live) { setResult({ key, list: l, insights: i.items }); setFailure(null); } })
      .catch((e) => { if (live) setFailure({ key, message: e instanceof Error ? e.message : "The dashboard could not load." }); });
    return () => { live = false; };
  }, [query, key]);

  // The last good result stays on screen (dimmed) while a new scenario loads.
  const list = result?.list ?? null;
  const insights = result?.insights ?? null;
  const error = failure?.key === key ? failure.message : null;
  const loading = !query || (result?.key !== key && !error);

  useEffect(() => {
    fetchCounts().then((c) => setDocuments(c.documents)).catch(() => setDocuments(null));
    fetchFlexOutcome({ fuel: "Heptane", o2_fraction: 0.21, pressure_kpa: 101.3, co2_fraction: 0, he_fraction: 0, droplet_diameter_mm: 3 })
      .then((r) => setModelScore({ f1: r.model.primary_estimate.macro_f1.mean, base: r.model.primary_estimate.majority_baseline_macro_f1.mean }))
      .catch(() => setModelScore(null));
  }, []);

  const ranked = list?.items.filter((i) => i.rank) ?? [];
  const unranked = list?.items.filter((i) => !i.rank) ?? [];
  const scenarioSearch = query ? toSearch(query) : "";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-8">
      {/* Problem and value, in one screen */}
      <section className="flex flex-col gap-3">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--accent-ember)" }}>
          NASA Space Apps 2026 · Flame in Freefall
        </p>
        <h1 className="text-2xl font-bold leading-tight sm:text-3xl" style={{ color: "var(--text-primary)" }}>
          Which NASA microgravity fire experiments speak to <span style={{ color: "var(--accent-ember)" }}>your</span> spacecraft atmosphere?
        </h1>
        <p className="max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Moon and Mars vehicles plan to run at lower pressure and higher oxygen than the ISS, which makes materials burn more readily.
          Pick a cabin atmosphere: Flame in Freefall ranks NASA&apos;s flight investigations by how directly their data covers it,
          states what the flight tests measured there (each figure linked to the source row), estimates droplet-flame outcomes with a
          validated model, and says plainly what the data cannot tell you.
        </p>
      </section>

      <Card>
        <SectionTitle title="1 · Choose a cabin atmosphere" subtitle="Values quoted or derived from NASA/TM-2008-215260, or your own." />
        {list ? (
          <div className="flex flex-col gap-3">
            <ScenarioPicker scenarios={list.scenarios} value={query ?? {}} onChange={setQuery} />
            <ScenarioNote scenario={list.scenario} />
          </div>
        ) : loading ? <Loading label="Loading scenarios…" /> : null}
      </Card>

      {error && <ErrorNote message={error} onRetry={() => setAttempt((n) => n + 1)} />}

      {list && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { icon: Database, label: "Flight tests analysed", value: list.totals.flight_tests.toLocaleString(), note: `rows from ${list.totals.with_data} NASA PSI tables` },
            { icon: Layers, label: "Investigations with data", value: `${list.totals.with_data} of ${list.totals.investigations}`, note: `${list.not_acquired.length} more named by the challenge` },
            { icon: Rocket, label: "Documents in the corpus", value: documents === null ? "—" : String(documents), note: "NTRS reports + NASA metadata" },
            { icon: FlaskConical, label: "Outcome model macro-F1", value: modelScore ? modelScore.f1.toFixed(2) : "—",
              note: modelScore ? `vs ${modelScore.base.toFixed(2)} majority baseline · split by test day` : "model unavailable" },
          ].map(({ icon: Icon, label, value, note }) => (
            <div key={label} className="rounded-xl p-4" style={{ background: "var(--bg-card)", border: "1px solid var(--border-default)" }}>
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                <Icon className="h-3.5 w-3.5" aria-hidden="true" />{label}
              </div>
              <div className="mt-1 text-xl font-bold" style={{ fontFamily: "var(--font-mono)" }}>{value}</div>
              <div className="text-[11px]" style={{ color: "var(--text-dim)" }}>{note}</div>
            </div>
          ))}
        </div>
      )}

      <Card>
        <SectionTitle title="2 · Ranked investigations"
          subtitle="Evidence relevance to this atmosphere (not a risk score). Hover the bar for each weighted component."
          right={<details className="text-xs" style={{ color: "var(--text-muted)" }}><summary className="cursor-pointer">How is this scored?</summary>
            <p className="mt-2 max-w-md leading-relaxed">{list?.ranking_method}</p></details>} />
        {loading && !list ? <Loading label="Ranking investigations…" /> : ranked.length === 0 ? <Empty message="No investigation has ingested data yet. Run the ingest (see DEMO_RUNBOOK.md)." /> : (
          <ol className="flex flex-col gap-3">
            {ranked.map((inv) => (
              <li key={inv.investigation_id} className="rounded-xl p-4" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", opacity: loading ? 0.6 : 1 }}>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold"
                          style={{ background: inv.rank === 1 ? "rgba(59,130,246,0.2)" : "var(--bg-card)", border: "1px solid var(--border-default)", fontFamily: "var(--font-mono)" }}>
                      {inv.rank}
                    </span>
                    <div className="min-w-0">
                      <Link href={`/investigations/${inv.investigation_id}${scenarioSearch}`} className="text-sm font-semibold hover:underline">
                        {inv.acronym} · {inv.title}
                      </Link>
                      <p className="mt-0.5 text-xs" style={{ color: "var(--text-muted)" }}>
                        {inv.data.tests} flight tests · {inv.flight_platform ?? "platform not recorded"} · {inv.fire_safety_use.slice(0, 3).join(", ")}
                      </p>
                      <ul className="mt-2 list-disc pl-4 text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                        {inv.relevance?.explanation.map((e) => <li key={e}>{e}</li>)}
                      </ul>
                    </div>
                  </div>
                  <div className="w-full md:w-72 md:shrink-0">{inv.relevance && <RelevanceBar relevance={inv.relevance} />}</div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </Card>

      <Card>
        <SectionTitle title="3 · What the flight data says here"
          subtitle="Measured = computed from flight-test rows · Model estimate = validated FLEX model · Coverage gap = not covered. Click a test ID to see its source row." />
        {loading && !insights ? <Loading label="Computing insights…" /> : !insights?.length ? <Empty message="No insights for this atmosphere." /> : (
          <div className="grid gap-3 lg:grid-cols-2">{insights.map((i) => <InsightCard key={i.insight_id} insight={i} />)}</div>
        )}
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/explorer" className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold"
                style={{ background: "var(--accent-flame)", color: "white" }}>
            <Flame className="h-4 w-4" aria-hidden="true" /> Explore droplet-flame outcomes <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link href="/chat" className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}>
            Ask the NASA corpus a question
          </Link>
        </div>
      </Card>

      <Card>
        <SectionTitle title="4 · Compare investigations" subtitle="What each published table covers. “not recorded” means the table has no such column — never zero." />
        {!list ? <Loading label="Loading…" /> : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-xs">
              <thead style={{ color: "var(--text-muted)" }}>
                <tr>{["Investigation", "Tests", "O₂ fraction", "Pressure", "Flow", "Fuels / materials", "Outcome in table"].map((h) => (
                  <th key={h} className="px-2 py-2 font-semibold" scope="col">{h}</th>))}</tr>
              </thead>
              <tbody>
                {list.items.map((inv) => (
                  <tr key={inv.investigation_id} style={{ borderTop: "1px solid var(--border-default)" }}>
                    <th scope="row" className="px-2 py-2 font-semibold">
                      <Link href={`/investigations/${inv.investigation_id}${scenarioSearch}`} className="hover:underline">{inv.acronym}</Link>
                    </th>
                    <td className="px-2 py-2" style={{ fontFamily: "var(--font-mono)" }}>{inv.status === "ingested" ? inv.data.tests : "—"}</td>
                    <td className="px-2 py-2" style={{ fontFamily: "var(--font-mono)" }}>{inv.status === "ingested" ? fmtRange(inv.data.o2_fraction, 3) + (inv.data.o2_approximate ? " (approx.)" : "") : "no data yet"}</td>
                    <td className="px-2 py-2" style={{ fontFamily: "var(--font-mono)" }}>{inv.status === "ingested" ? fmtRange(inv.data.pressure_kpa, 0, "kPa") : "—"}</td>
                    <td className="px-2 py-2" style={{ fontFamily: "var(--font-mono)" }}>{inv.status === "ingested" ? fmtRange(inv.data.flow_velocity_m_s, 2, "m/s") : "—"}</td>
                    <td className="px-2 py-2">{inv.status === "ingested" ? `${inv.data.fuels_or_materials.slice(0, 3).map((f) => f.name).join(", ")}${(inv.data.distinct_fuels_or_materials ?? 0) > 3 ? ` +${(inv.data.distinct_fuels_or_materials ?? 0) - 3}` : ""}` : inv.key_variables.slice(0, 2).join(", ")}</td>
                    <td className="px-2 py-2">{inv.data.end_state_recorded ? "end state per test" : inv.data.duration_recorded ? "burn duration only" : inv.status === "ingested" ? "none (video/report only)" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {list && (
        <Card>
          <SectionTitle title="5 · Not covered yet" subtitle="Shown so nobody mistakes an absence of data for an absence of risk." />
          <ul className="flex flex-col gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
            {unranked.map((inv) => (
              <li key={inv.investigation_id} className="flex items-start gap-2">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
                <span><strong>{inv.acronym}</strong> ({inv.title}): registered, but its flight data has not been ingested yet.</span>
              </li>
            ))}
            {list.not_acquired.map((n) => (
              <li key={n.investigation_id} className="flex items-start gap-2">
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
                <span><strong>{n.acronym}</strong> ({n.title}): {n.note}</span>
              </li>
            ))}
            <li className="flex items-start gap-2">
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
              <span><strong>Partial gravity.</strong> Every flight test here ran in microgravity; lunar (1/6 g) and Martian (3/8 g) flame behaviour is not covered.</span>
            </li>
          </ul>
        </Card>
      )}
    </div>
  );
}
