"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Database, FireExtinguisher, Flame, FlaskConical, Layers, Rocket, ShieldAlert } from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  Empty, ErrorNote, InsightCard, Loading, RelevanceBar, ScenarioNote, ScenarioPicker, SectionTitle, SweepChart,
} from "@/components/fire/FireUi";
import { CoverageVerdict, EnvelopeMap, HistoryPanels } from "@/components/fire/Coverage";
import { FlameOrb } from "@/components/fire/FlameOrb";
import {
  fetchCounts, fetchFlexOutcome, fetchInsights, fetchInvestigations, fetchScenarioHistory, fmtRange,
  type FlexOutcome, type Insight, type InvestigationList, type ScenarioHistory, type ScenarioQuery,
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

/** Counts up to a number once it arrives; strings (e.g. "—") render as they are. */
function CountUp({ value, decimals = 0 }: { value: number | string; decimals?: number }) {
  const [shown, setShown] = useState<number | null>(null);
  useEffect(() => {
    if (typeof value !== "number") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) { queueMicrotask(() => setShown(value)); return; }
    let frame = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const k = Math.min(1, (now - start) / 1100);
      setShown(value * (1 - Math.pow(1 - k, 4)));
      if (k < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);
  if (typeof value !== "number") return <>{value}</>;
  const n = shown ?? 0;
  return <>{decimals ? n.toFixed(decimals) : Math.round(n).toLocaleString()}</>;
}

const STAT_ACCENTS = ["#4F8CFF", "#22D3EE", "#A78BFA", "#FF8A4C"];
const PODIUM = ["79,140,255", "34,211,238", "167,139,250"];

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

  // Historical scenarios (Apollo 1) carry a cited story and a data-covered alternative; the sweep shows how far
  // the chosen O2 lies from the flight data. Both are per scenario and fail soft: the verdict above stands alone.
  const scenario = list?.scenario ?? null;
  const historicalId = scenario?.kind === "historical" ? scenario.scenario_id : null;
  const [history, setHistory] = useState<ScenarioHistory | null>(null);
  useEffect(() => {
    if (!historicalId) return;
    let live = true;
    fetchScenarioHistory(historicalId).then((h) => { if (live) setHistory(h); }).catch(() => { if (live) setHistory(null); });
    return () => { live = false; };
  }, [historicalId]);
  const shownHistory = history && history.scenario.scenario_id === historicalId ? history : null;
  const [sweep, setSweep] = useState<{ key: string; outcome: FlexOutcome } | null>(null);
  const sweepKey = scenario ? `${scenario.o2_fraction}:${scenario.pressure_kpa}` : "";
  useEffect(() => {
    if (!scenario) return;
    let live = true;
    fetchFlexOutcome({ fuel: "Heptane", o2_fraction: scenario.o2_fraction, pressure_kpa: scenario.pressure_kpa, co2_fraction: 0,
                       he_fraction: 0, droplet_diameter_mm: 3 })
      .then((r) => { if (live) setSweep({ key: sweepKey, outcome: r }); })
      .catch(() => { if (live) setSweep(null); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refetch only when the atmosphere itself changes
  }, [sweepKey]);
  const shownSweep = sweep?.key === sweepKey ? sweep.outcome : null;
  const alternative = shownHistory ? list?.scenarios.find((s) => s.scenario_id === shownHistory.alternative.scenario.scenario_id) ?? null : null;

  const ranked = list?.items.filter((i) => i.rank) ?? [];
  const unranked = list?.items.filter((i) => !i.rank) ?? [];
  const scenarioSearch = query ? toSearch(query) : "";

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-6 sm:px-6 sm:py-10">
      {/* Problem and value, in one screen: the question on the left, the chosen atmosphere burning on the right */}
      <section className="rise-in relative grid items-center gap-6 lg:grid-cols-[1.35fr_1fr]">
        <div className="flex flex-col gap-4">
          <p className="eyebrow flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="ping-ring absolute inline-flex h-full w-full rounded-full" style={{ background: "var(--accent-plasma)" }} />
              <span className="relative inline-flex h-2 w-2 rounded-full" style={{ background: "var(--accent-plasma)" }} />
            </span>
            NASA Space Apps 2026 · Flame in Freefall
          </p>
          <h1 className="text-3xl font-extrabold leading-[1.08] tracking-tight sm:text-[2.6rem]" style={{ color: "var(--text-primary)" }}>
            Which NASA microgravity fire experiments speak to <span className="text-gradient-soot">your</span>{" "}
            <span className="text-gradient-flame">spacecraft atmosphere?</span>
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed sm:text-[15px]" style={{ color: "var(--text-secondary)" }}>
            Moon and Mars vehicles plan to run at lower pressure and higher oxygen than the ISS, which makes materials burn
            more readily. Pick a cabin atmosphere: Flame in Freefall ranks NASA&apos;s flight investigations by how directly their data
            covers it, states what the flight tests measured there (each figure linked to the source row), estimates droplet-flame
            outcomes with a validated model, and says plainly what the data cannot tell you.
          </p>
          <div className="flex flex-wrap gap-2 pt-1 text-[11px]" style={{ fontFamily: "var(--font-mono)" }}>
            {["Every figure cited", "Refuses outside the data", "Validated outcome model"].map((t) => (
              <span key={t} className="rounded-full px-3 py-1" style={{ background: "rgba(124,180,255,0.06)", border: "1px solid var(--border-default)", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--accent-plasma)" }}>✓</span> {t}
              </span>
            ))}
          </div>
        </div>

        <div className="hud-card relative mx-auto flex w-full max-w-[400px] flex-col items-center rounded-3xl px-5 pb-4 pt-5">
          <span aria-hidden="true" className="hud-sheen" />
          <div className="flex w-full items-center justify-between text-[10px] uppercase tracking-[0.2em]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-dim)" }}>
            <span>Cabin atmosphere</span>
            <span style={{ color: scenario?.kind === "historical" ? "#F0527A" : "var(--accent-plasma)" }}>
              {scenario ? (scenario.kind === "historical" ? "Historical" : "Live") : "Standby"}
            </span>
          </div>
          <div className="w-full max-w-[280px]">
            <FlameOrb o2Fraction={scenario?.o2_fraction ?? 0.21} pressureKpa={scenario?.pressure_kpa ?? 101.3}
                      hazard={list?.coverage.verdict === "none"} />
          </div>
          <p className="-mt-1 truncate text-sm font-semibold" style={{ color: "var(--text-primary)", maxWidth: "100%" }}>{scenario?.name ?? "Loading scenario…"}</p>
          <dl className="mt-3 grid w-full grid-cols-3 gap-2 text-center">
            {[
              { k: "O₂", v: scenario ? `${(scenario.o2_fraction * 100).toFixed(0)}%` : "—" },
              { k: "Pressure", v: scenario ? `${scenario.pressure_kpa.toFixed(1)}` : "—", u: "kPa" },
              { k: "O₂ partial", v: scenario ? `${(scenario.o2_fraction * scenario.pressure_kpa).toFixed(1)}` : "—", u: "kPa" },
            ].map(({ k, v, u }) => (
              <div key={k} className="rounded-lg px-2 py-1.5" style={{ background: "rgba(124,180,255,0.05)", border: "1px solid var(--border-subtle)" }}>
                <dt className="text-[9.5px] uppercase tracking-[0.16em]" style={{ color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>{k}</dt>
                <dd className="text-[15px] font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>
                  {v}{u && <span className="ml-0.5 text-[10px] font-medium" style={{ color: "var(--text-muted)" }}>{u}</span>}
                </dd>
              </div>
            ))}
          </dl>
          <p className="mt-2.5 text-center text-[10px] leading-snug" style={{ color: "var(--text-dim)" }}>
            Illustration: a droplet flame burns as a sphere in microgravity. Glow and soot shell scale with O₂ partial pressure; not a model output.
          </p>
        </div>
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
            { icon: Database, label: "Flight tests analysed", value: list.totals.flight_tests as number | string, note: `rows from ${list.totals.with_data} NASA PSI tables` },
            { icon: Layers, label: "Investigations with data", value: `${list.totals.with_data} of ${list.totals.investigations}`, note: `${list.not_acquired.length} more named by the challenge` },
            { icon: Rocket, label: "Documents in the corpus", value: documents === null ? "—" : documents, note: "NTRS reports + NASA metadata" },
            { icon: FlaskConical, label: "Outcome model macro-F1", value: modelScore ? modelScore.f1 : "—", decimals: 2,
              note: modelScore ? `vs ${modelScore.base.toFixed(2)} majority baseline · split by test day` : "model unavailable" },
          ].map(({ icon: Icon, label, value, note, decimals }: { icon: typeof Database; label: string; value: number | string; note: string; decimals?: number }, i) => (
            <div key={label} className="panel panel-hover relative overflow-hidden rounded-2xl p-4 sm:p-5">
              <span aria-hidden="true" className="absolute inset-x-0 top-0 h-[2px]" style={{ background: `linear-gradient(90deg, ${STAT_ACCENTS[i]}, transparent 85%)` }} />
              <span aria-hidden="true" className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full"
                    style={{ background: `radial-gradient(circle, ${STAT_ACCENTS[i]}30, transparent 70%)` }} />
              <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                <span className="flex h-6 w-6 items-center justify-center rounded-md" style={{ background: `${STAT_ACCENTS[i]}1f`, border: `1px solid ${STAT_ACCENTS[i]}44` }}>
                  <Icon className="h-3.5 w-3.5" style={{ color: STAT_ACCENTS[i] }} aria-hidden="true" />
                </span>
                <span className="leading-tight">{label}</span>
              </div>
              <div className="mt-3 text-2xl font-bold tracking-tight sm:text-[28px]" style={{ fontFamily: "var(--font-mono)", textShadow: `0 0 28px ${STAT_ACCENTS[i]}66` }}>
                <CountUp value={value} decimals={decimals} />
              </div>
              <div className="mt-0.5 text-[11px]" style={{ color: "var(--text-dim)" }}>{note}</div>
            </div>
          ))}
        </div>
      )}

      {list && scenario && (
        <Card>
          <SectionTitle title="2 · Does any flight test cover this atmosphere?"
            subtitle="Asked before any ranking or estimate. Where nothing was flown, the system says so and does not guess." />
          <div className="flex flex-col gap-5" style={{ opacity: loading ? 0.6 : 1 }}>
            <CoverageVerdict coverage={list.coverage} scenario={scenario}
              acronyms={Object.fromEntries(list.items.flatMap((i) => (i.acronym ? [[i.investigation_id, i.acronym]] : [])))} />
            <div className="grid gap-5 lg:grid-cols-2">
              <div>
                <h3 className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>Where the flight data is</h3>
                <EnvelopeMap coverage={list.coverage} scenario={scenario} scenarios={list.scenarios} alternative={alternative} />
              </div>
              <div>
                <h3 className="mb-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
                  Heptane droplet outcomes as O₂ varies, at {scenario.pressure_kpa.toFixed(1)} kPa
                </h3>
                {shownSweep ? <SweepChart points={shownSweep.o2_sweep} marker={scenario.o2_fraction} /> : <Loading label="Loading the oxygen sweep…" />}
              </div>
            </div>
            {shownHistory && <HistoryPanels history={shownHistory} onShowAlternative={(id) => setQuery({ scenario: id })} />}
          </div>
        </Card>
      )}

      <Card>
        <SectionTitle title="3 · Ranked investigations"
          subtitle="Evidence relevance to this atmosphere (not a risk score). Hover the bar for each weighted component."
          right={<details className="text-xs" style={{ color: "var(--text-muted)" }}><summary className="cursor-pointer">How is this scored?</summary>
            <p className="mt-2 max-w-md leading-relaxed">{list?.ranking_method}</p></details>} />
        {loading && !list ? <Loading label="Ranking investigations…" /> : ranked.length === 0 ? <Empty message="No investigation has ingested data yet. Run the ingest (see DEMO_RUNBOOK.md)." /> : (
          <ol className="flex flex-col gap-3">
            {ranked.map((inv) => (
              <li key={inv.investigation_id} className="panel panel-hover relative overflow-hidden rounded-xl p-4"
                  style={{ opacity: loading ? 0.6 : 1,
                           borderColor: inv.rank && inv.rank <= 3 ? `rgba(${PODIUM[inv.rank - 1]},0.35)` : undefined,
                           background: inv.rank && inv.rank <= 3 ? `linear-gradient(100deg, rgba(${PODIUM[inv.rank - 1]},0.12), rgba(16,20,33,0.55) 45%)` : undefined }}>
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="flex min-w-0 items-start gap-3">
                    <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-sm font-bold"
                          style={inv.rank && inv.rank <= 3
                            ? { background: `linear-gradient(145deg, rgba(${PODIUM[inv.rank - 1]},0.45), rgba(${PODIUM[inv.rank - 1]},0.1))`,
                                border: `1px solid rgba(${PODIUM[inv.rank - 1]},0.6)`, boxShadow: `0 0 20px -4px rgba(${PODIUM[inv.rank - 1]},0.8)`,
                                fontFamily: "var(--font-mono)", color: "#fff" }
                            : { background: "rgba(6,7,12,0.5)", border: "1px solid var(--border-default)", fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                      {String(inv.rank).padStart(2, "0")}
                    </span>
                    <div className="min-w-0">
                      <Link href={`/investigations/${inv.investigation_id}${scenarioSearch}`} className="text-sm font-semibold transition-colors hover:text-cyan-300">
                        <span style={{ color: "var(--accent-ember)" }}>{inv.acronym}</span> · {inv.title}
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
        <SectionTitle title="4 · What the flight data says here"
          subtitle="Measured = computed from flight-test rows · Model estimate = validated FLEX model · Coverage gap = not covered. Click a test ID to see its source row." />
        {loading && !insights ? <Loading label="Computing insights…" /> : !insights?.length ? <Empty message="No insights for this atmosphere." /> : (
          <div className="grid gap-3 lg:grid-cols-2">{insights.map((i) => <InsightCard key={i.insight_id} insight={i} />)}</div>
        )}
        <div className="mt-4 flex flex-wrap gap-3">
          <Link href="/explorer" className="btn-primary inline-flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-sm font-semibold">
            <Flame className="h-4 w-4" aria-hidden="true" /> Explore droplet-flame outcomes <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <Link href={scenario ? `/suppression?o2_fraction=${scenario.o2_fraction}&pressure_kpa=${scenario.pressure_kpa}` : "/suppression"}
                className="btn-ghost inline-flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-sm font-semibold">
            <FireExtinguisher className="h-4 w-4" aria-hidden="true" /> Which extinguisher here?
          </Link>
          <Link href="/chat" className="btn-ghost inline-flex items-center gap-1.5 rounded-xl px-4 py-2.5 text-sm font-semibold">
            Ask the NASA corpus a question
          </Link>
        </div>
      </Card>

      <Card>
        <SectionTitle title="5 · Compare investigations" subtitle="What each published table covers. “not recorded” means the table has no such column — never zero." />
        {!list ? <Loading label="Loading…" /> : (
          <div className="overflow-x-auto">
            <table className="data-table w-full min-w-[720px] text-left text-xs">
              <thead style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                <tr>{["Investigation", "Tests", "O₂ fraction", "Pressure", "Flow", "Fuels / materials", "Outcome in table"].map((h) => (
                  <th key={h} className="px-2 py-2.5 text-[10px] font-semibold uppercase tracking-[0.12em]" scope="col"
                      style={{ borderBottom: "1px solid var(--border-strong)" }}>{h}</th>))}</tr>
              </thead>
              <tbody>
                {list.items.map((inv) => (
                  <tr key={inv.investigation_id} style={{ borderTop: "1px solid var(--border-default)" }}>
                    <th scope="row" className="px-2 py-2 font-semibold">
                      <Link href={`/investigations/${inv.investigation_id}${scenarioSearch}`} className="transition-colors hover:text-cyan-300" style={{ color: "var(--accent-ember)" }}>{inv.acronym}</Link>
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
          <SectionTitle title="6 · Not covered yet" subtitle="Shown so nobody mistakes an absence of data for an absence of risk." />
          <ul className="flex flex-col gap-2 text-sm" style={{ color: "var(--text-secondary)" }}>
            {unranked.map((inv) => (
              <li key={inv.investigation_id} className="flex items-start gap-2.5 rounded-lg px-3 py-2" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.14)" }}>
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
                <span><strong>{inv.acronym}</strong> ({inv.title}): registered, but its flight data has not been ingested yet.</span>
              </li>
            ))}
            {list.not_acquired.map((n) => (
              <li key={n.investigation_id} className="flex items-start gap-2.5 rounded-lg px-3 py-2" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.14)" }}>
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
                <span><strong>{n.acronym}</strong> ({n.title}): {n.note}</span>
              </li>
            ))}
            <li className="flex items-start gap-2.5 rounded-lg px-3 py-2" style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.14)" }}>
              <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />
              <span><strong>Partial gravity.</strong> Every flight test here ran in microgravity; lunar (1/6 g) and Martian (3/8 g) flame behaviour is not covered.</span>
            </li>
          </ul>
        </Card>
      )}
    </div>
  );
}
