"use client";

// Coverage verdict, flight envelope map and historical-scenario panels (contract 0.7.0, ADR-013).
// The verdict comes first so nobody reads a ranking as coverage: an atmosphere nobody flew is said so plainly,
// with the nearest real flight test and the size of the gap. Hand-drawn SVG, same tokens as SweepChart.

import Link from "next/link";
import { ArrowRight, BookOpen, CheckCircle2, ExternalLink, OctagonX, TriangleAlert } from "lucide-react";
import type { CitedSource, Coverage, Scenario, ScenarioHistory } from "@/lib/api/fireSafety";
import { EvidenceChips } from "@/components/fire/FireUi";

const VERDICT = {
  none: { color: "#EF4444", bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.45)", icon: OctagonX, label: "No flight data" },
  partial: { color: "#F59E0B", bg: "rgba(245,158,11,0.08)", border: "rgba(245,158,11,0.45)", icon: TriangleAlert, label: "Partial coverage" },
  covered: { color: "#22C55E", bg: "rgba(34,197,94,0.07)", border: "rgba(34,197,94,0.4)", icon: CheckCircle2, label: "Covered by flight data" },
} as const;

const GRAVITY_LABEL: Record<string, string> = { earth: "1 g (Earth)", lunar: "lunar gravity", martian: "Martian gravity", microgravity: "microgravity" };

export function CoverageVerdict({ coverage, scenario, acronyms = {} }: {
  coverage: Coverage;
  scenario: Scenario;
  /** investigation_id → acronym from the same response's items, so the nearest test reads "ACME CFI-G 21162A1". */
  acronyms?: Record<string, string>;
}) {
  const v = VERDICT[coverage.verdict];
  const Icon = v.icon;
  const near = coverage.nearest_test;
  return (
    <section aria-label="Flight-data coverage verdict" data-verdict={coverage.verdict}
             className="flex flex-col gap-3 rounded-xl p-4" style={{ background: v.bg, border: `1px solid ${v.border}` }}>
      <div className="flex flex-wrap items-center gap-2">
        <Icon className="h-5 w-5" style={{ color: v.color }} aria-hidden="true" />
        <span className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: v.color }}>{v.label}</span>
      </div>
      <p className="text-lg font-bold leading-snug" style={{ color: "var(--text-primary)" }}>{coverage.headline}</p>
      {coverage.reasons.length > 0 && (
        <ul className="list-disc pl-5 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          {coverage.reasons.map((r) => <li key={r}>{r}</li>)}
        </ul>
      )}
      {near && (
        <div className="flex flex-col gap-1.5 text-sm" style={{ color: "var(--text-secondary)" }}>
          <p>
            {coverage.verdict === "covered" ? "Closest flight test" : "The closest real flight test"}:{" "}
            <strong style={{ color: "var(--text-primary)" }}>{acronyms[near.investigation_id] ?? near.investigation_id} {near.test_id}</strong>{" "}
            at {(near.o2_fraction * 100).toFixed(0)}% O₂{near.pressure_kpa !== null && <>, {near.pressure_kpa.toFixed(1)} kPa</>}
            {near.end_state && <> (ended in {near.end_state.toLowerCase().replaceAll("_", " ")})</>}, flown in {coverage.gravity.flight_tests.join(" and ")}.
            {coverage.verdict !== "covered" && coverage.gap?.o2_ratio && coverage.gap.o2_ratio > 1.05 && (
              <> This atmosphere has <strong style={{ color: v.color }}>{coverage.gap.o2_ratio.toFixed(1)}×</strong> its oxygen
                {!coverage.gravity.covered && <> and is at <strong style={{ color: v.color }}>{GRAVITY_LABEL[scenario.gravity]}</strong></>}.</>
            )}
          </p>
          <EvidenceChips evidence={near.evidence.map((id) => ({ evidence_id: id }))} max={2} />
        </div>
      )}
      <details className="text-xs" style={{ color: "var(--text-muted)" }}>
        <summary className="cursor-pointer">How is the verdict decided?</summary>
        <p className="mt-1 leading-relaxed">{coverage.method}</p>
      </details>
    </section>
  );
}

/** O₂ (x, linear 0–100%) against total pressure (y, log 20–400 kPa): where flight tests exist and where this atmosphere sits. */
export function EnvelopeMap({ coverage, scenario, scenarios, alternative }: {
  coverage: Coverage;
  scenario: Scenario;
  scenarios: Scenario[];
  alternative?: Scenario | null;
}) {
  const W = 560, H = 270, L = 48, R = 16, T = 14, B = 38;
  const P0 = 20, P1 = 400;
  const x = (o2: number) => L + o2 * (W - L - R);
  const y = (kpa: number) => T + (1 - (Math.log(Math.min(Math.max(kpa, P0), P1)) - Math.log(P0)) / (Math.log(P1) - Math.log(P0))) * (H - T - B);
  const o2r = coverage.tested_range.o2_fraction, pr = coverage.tested_range.pressure_kpa;
  const v = VERDICT[coverage.verdict];
  const others = scenarios.filter((s) => s.scenario_id !== scenario.scenario_id && s.scenario_id !== alternative?.scenario_id);
  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
           aria-label={`Flight-test envelope: oxygen ${o2r ? `${o2r.min}–${o2r.max}` : "not recorded"}; this atmosphere at ${Math.round(scenario.o2_fraction * 100)}% oxygen and ${scenario.pressure_kpa.toFixed(0)} kPa`}>
        <rect x={L} y={T} width={W - L - R} height={H - T - B} fill="rgba(239,68,68,0.06)" />
        {o2r && pr && (
          <g>
            <rect data-testid="flown-envelope" x={x(o2r.min)} y={y(pr.max)} width={x(o2r.max) - x(o2r.min)} height={y(pr.min) - y(pr.max)}
                  fill="rgba(34,197,94,0.18)" stroke="#22C55E" strokeWidth={1.5} />
            <text x={x(o2r.max) + 4} y={y(pr.max) + 12} fontSize={10} fill="#22C55E">flown in microgravity</text>
          </g>
        )}
        {[20, 50, 100, 200, 400].map((p) => (
          <g key={p}>
            <line x1={L} x2={W - R} y1={y(p)} y2={y(p)} stroke="var(--border-default)" strokeWidth={0.6} />
            <text x={L - 6} y={y(p) + 3} textAnchor="end" fontSize={10} fill="var(--text-muted)">{p}</text>
          </g>
        ))}
        {[0, 0.21, 0.5, 1].map((o) => (
          <text key={o} x={x(o)} y={H - B + 14} textAnchor="middle" fontSize={10} fill="var(--text-muted)">{Math.round(o * 100)}%</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 6} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">O₂ (mole fraction)</text>
        <text x={12} y={(T + H - B) / 2} textAnchor="middle" fontSize={11} fill="var(--text-secondary)"
              transform={`rotate(-90 12 ${(T + H - B) / 2})`}>pressure (kPa, log)</text>
        {others.map((s) => (
          <circle key={s.scenario_id} cx={x(s.o2_fraction)} cy={y(s.pressure_kpa)} r={3.5} fill="var(--text-muted)">
            <title>{s.name}</title>
          </circle>
        ))}
        {alternative && (
          <g data-testid="envelope-alternative">
            <defs>
              <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#22C55E" />
              </marker>
            </defs>
            <line x1={x(scenario.o2_fraction) - 8} y1={y(scenario.pressure_kpa)} x2={x(alternative.o2_fraction) + 8} y2={y(alternative.pressure_kpa)}
                  stroke="#22C55E" strokeWidth={1.5} strokeDasharray="5 4" markerEnd="url(#arrow)" />
            <circle cx={x(alternative.o2_fraction)} cy={y(alternative.pressure_kpa)} r={6} fill="#22C55E" />
            <text x={x(alternative.o2_fraction)} y={y(alternative.pressure_kpa) + 20} textAnchor="middle" fontSize={10.5} fill="#22C55E">
              {alternative.name}
            </text>
          </g>
        )}
        <circle data-testid="envelope-scenario" cx={x(scenario.o2_fraction)} cy={y(scenario.pressure_kpa)} r={8} fill={v.color}
                stroke="var(--bg-card)" strokeWidth={2} />
        <text x={Math.min(x(scenario.o2_fraction), W - R - 4)} y={y(scenario.pressure_kpa) - 13} textAnchor={scenario.o2_fraction > 0.8 ? "end" : "middle"}
              fontSize={11} fontWeight={600} fill={v.color}>
          {scenario.name}{scenario.gravity !== "microgravity" ? ` · ${GRAVITY_LABEL[scenario.gravity]}` : ""}
        </text>
      </svg>
      <figcaption className="flex flex-wrap gap-3 text-[11px]" style={{ color: "var(--text-muted)" }}>
        <span className="inline-flex items-center gap-1"><span className="h-2 w-3 rounded-sm" style={{ background: "rgba(34,197,94,0.45)" }} />range of O₂ and pressure flown (all investigations)</span>
        <span className="inline-flex items-center gap-1"><span className="h-2 w-3 rounded-sm" style={{ background: "rgba(239,68,68,0.3)" }} />never flown: no estimate is made here</span>
        <span>grey dots: other preset atmospheres</span>
      </figcaption>
    </figure>
  );
}

function SourceLinks({ sources }: { sources: CitedSource[] }) {
  return (
    <span className="flex flex-wrap gap-1.5">
      {sources.map((s) => {
        const label = `${s.short_name ?? s.source_id.replace("FF-NTRS-", "NTRS ")}, p. ${s.page}`;
        const style = { fontFamily: "var(--font-mono)", background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--accent-ember)" };
        return s.evidence_id ? (
          <Link key={`${s.source_id}-${s.page}`} href={`/evidence?id=${s.evidence_id}`} title={s.title ?? s.source_id}
                className="rounded-md px-1.5 py-0.5 text-[11px]" style={style}>{label}</Link>
        ) : (
          <a key={`${s.source_id}-${s.page}`} href={s.access_url ? `${s.access_url}` : undefined} target="_blank" rel="noreferrer"
             title={`${s.title ?? s.source_id} (opens NASA NTRS)`} className="inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[11px]" style={style}>
            {label}<ExternalLink className="h-3 w-3" aria-hidden="true" />
          </a>
        );
      })}
    </span>
  );
}

export function HistoryPanels({ history, onShowAlternative }: { history: ScenarioHistory; onShowAlternative: (scenarioId: string) => void }) {
  const alt = history.alternative;
  return (
    <div className="flex flex-col gap-5">
      <blockquote data-testid="history-lesson" className="rounded-xl p-4 text-base leading-relaxed"
                  style={{ background: "rgba(239,68,68,0.06)", borderLeft: "4px solid #EF4444", color: "var(--text-primary)" }}>
        <p className="font-semibold">{history.lesson}</p>
        <footer className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>
          {history.lesson_sources.filter((s) => s.quote).map((s) => (
            <p key={`${s.source_id}-${s.page}`} className="mt-1">“{s.quote}” <SourceLinks sources={[s]} /></p>
          ))}
        </footer>
      </blockquote>

      <div>
        <h3 className="mb-1 flex items-center gap-2 text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          <BookOpen className="h-4 w-4" aria-hidden="true" /> What happened, and what changed after
        </h3>
        <p className="mb-3 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{history.story}</p>
        <ol data-testid="history-timeline" className="relative flex flex-col gap-3 border-l pl-4" style={{ borderColor: "var(--border-default)" }}>
          {history.timeline.map((e) => (
            <li key={`${e.date}-${e.title}`} className="relative">
              <span className="absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full" style={{ background: "var(--accent-ember)" }} />
              <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--accent-ember)" }}>{e.date}</p>
              <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{e.title}</p>
              <p className="mt-0.5 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{e.text}</p>
              <div className="mt-1"><SourceLinks sources={e.sources} /></div>
            </li>
          ))}
        </ol>
      </div>

      <section data-testid="history-alternative" className="flex flex-col gap-2 rounded-xl p-4"
               style={{ background: "rgba(34,197,94,0.07)", border: "1px solid rgba(34,197,94,0.4)" }}>
        <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: "#22C55E" }}>Where flight data does exist</p>
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{alt.headline}</p>
        <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{alt.rationale}</p>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <SourceLinks sources={alt.sources} />
          <button onClick={() => onShowAlternative(alt.scenario.scenario_id)}
                  className="inline-flex items-center gap-1.5 rounded-xl px-4 py-2 text-sm font-semibold"
                  style={{ background: "#16A34A", color: "white" }}>
            Show the flight data for {alt.scenario.name} <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </section>
    </div>
  );
}
