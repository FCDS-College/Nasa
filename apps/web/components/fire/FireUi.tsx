"use client";

import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, Calculator, FlaskConical, Loader2, MessageSquare, SearchX } from "lucide-react";
import type { EndState, Insight, InsightKind, Probabilities, Relevance, Scenario, ScenarioQuery } from "@/lib/api/fireSafety";
import { chatLink, pct } from "@/lib/api/fireSafety";

export const END_STATE_COLORS: Record<EndState, string> = {
  Extinction: "#22C55E",   // flame self-extinguished: the fire-safe outcome
  Disruption: "#F59E0B",   // droplet broke apart
  Completion: "#EF4444",   // burned until the fuel was consumed
};
export const END_STATE_LABELS: Record<EndState, string> = {
  Extinction: "Self-extinguished",
  Disruption: "Droplet disruption",
  Completion: "Burned to completion",
};
export const END_STATES: EndState[] = ["Extinction", "Disruption", "Completion"];

const KIND: Record<InsightKind, { label: string; color: string; bg: string; icon: typeof Calculator; help: string }> = {
  measured_statistic: { label: "Measured", color: "#22C55E", bg: "rgba(34,197,94,0.1)", icon: Calculator,
    help: "Computed directly from flight-test rows" },
  model_estimate: { label: "Model estimate", color: "#60A5FA", bg: "rgba(96,165,250,0.1)", icon: FlaskConical,
    help: "From the validated FLEX outcome model (claim class: estimated)" },
  coverage_gap: { label: "Coverage gap", color: "#F59E0B", bg: "rgba(245,158,11,0.1)", icon: AlertTriangle,
    help: "What the flight data does not cover" },
};

export function KindBadge({ kind }: { kind: InsightKind }) {
  const k = KIND[kind];
  const Icon = k.icon;
  return (
    <span title={k.help} className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold"
          style={{ color: k.color, background: k.bg, border: `1px solid ${k.color}33` }}>
      <Icon className="h-3 w-3" aria-hidden="true" /> {k.label}
    </span>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div role="status" className="flex items-center gap-3 py-8 text-sm" style={{ color: "var(--text-muted)" }}>
      <span className="relative flex h-6 w-6 items-center justify-center" aria-hidden="true">
        <span className="ping-ring absolute inset-1 rounded-full" style={{ border: "1px solid rgba(79,140,255,0.6)" }} />
        <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--accent-ember)" }} />
      </span>
      <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, letterSpacing: "0.04em" }}>{label}</span>
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl p-4 text-sm" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.25)" }}>
      <p style={{ color: "var(--text-primary)" }}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-ghost mt-2 rounded-lg px-3 py-1.5 text-xs font-semibold">
          Try again
        </button>
      )}
    </div>
  );
}

export function Empty({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2 py-6 text-sm" style={{ color: "var(--text-muted)" }}>
      <SearchX className="h-4 w-4" aria-hidden="true" /> {message}
    </div>
  );
}

export function ScenarioPicker({ scenarios, value, onChange }: {
  scenarios: Scenario[];
  value: ScenarioQuery;
  onChange: (q: ScenarioQuery) => void;
}) {
  const custom = value.o2_fraction !== undefined;
  const [o2, setO2] = useState(value.o2_fraction ?? 0.26);
  const [p, setP] = useState(value.pressure_kpa ?? 80);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Cabin atmosphere">
        {scenarios.map((s) => {
          const active = !custom && (value.scenario ?? "iss_nominal") === s.scenario_id;
          const historical = s.kind === "historical";
          const tint = historical ? "239,68,68" : "59,130,246";
          return (
            <button key={s.scenario_id} role="radio" aria-checked={active} onClick={() => onChange({ scenario: s.scenario_id })}
                    className="panel-hover relative min-w-[150px] overflow-hidden rounded-xl px-3.5 py-2.5 text-left text-xs"
                    style={{ background: active ? `linear-gradient(150deg, rgba(${tint},0.26), rgba(${tint},0.06))` : "rgba(19,24,38,0.7)",
                             border: `1px ${historical ? "dashed" : "solid"} ${active || historical ? `rgba(${tint},0.6)` : "var(--border-default)"}`,
                             boxShadow: active ? `0 0 26px -8px rgba(${tint},0.9), inset 0 1px 0 rgba(255,255,255,0.08)` : "none",
                             color: "var(--text-primary)", transition: "all var(--transition-default)" }}>
              {historical && (
                <span className="mb-0.5 block text-[10px] font-semibold uppercase tracking-wider" style={{ color: "#EF4444" }}>
                  Historical · never flown
                </span>
              )}
              <span className="block font-semibold">{s.name}</span>
              <span className="block mt-0.5" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                {Math.round(s.o2_fraction * 100)}% O₂ · {s.pressure_kpa.toFixed(1)} kPa
              </span>
              {/* O2 gauge: how far toward pure oxygen this atmosphere sits */}
              <span aria-hidden="true" className="mt-2 block h-[3px] w-full overflow-hidden rounded-full" style={{ background: "rgba(124,180,255,0.1)" }}>
                <span className="block h-full rounded-full" style={{ width: `${Math.min(100, s.o2_fraction * 100)}%`,
                  background: historical ? "var(--grad-soot)" : "var(--grad-flame)" }} />
              </span>
            </button>
          );
        })}
        <button role="radio" aria-checked={custom} onClick={() => onChange({ o2_fraction: o2, pressure_kpa: p })}
                className="panel-hover rounded-xl px-3.5 py-2.5 text-left text-xs"
                style={{ background: custom ? "linear-gradient(150deg, rgba(79,140,255,0.26), rgba(79,140,255,0.06))" : "rgba(19,24,38,0.4)",
                         border: `1px dashed ${custom ? "rgba(79,140,255,0.6)" : "var(--border-strong)"}`,
                         boxShadow: custom ? "0 0 26px -8px rgba(79,140,255,0.9)" : "none",
                         color: "var(--text-primary)", transition: "all var(--transition-default)" }}>
          <span className="block font-semibold">Custom atmosphere</span>
          <span className="block mt-0.5" style={{ color: "var(--text-muted)" }}>set O₂ and pressure</span>
        </button>
      </div>
      {custom && (
        <form className="flex flex-wrap items-end gap-3 text-xs" onSubmit={(e) => { e.preventDefault(); onChange({ o2_fraction: o2, pressure_kpa: p }); }}>
          <label className="flex flex-col gap-1" style={{ color: "var(--text-secondary)" }}>
            O₂ mole fraction
            <input type="number" min={0.05} max={1} step={0.01} value={o2} onChange={(e) => setO2(Number(e.target.value))}
                   className="w-28 rounded-lg px-2 py-1.5" style={{ background: "rgba(6,7,12,0.6)", border: "1px solid var(--border-strong)", color: "var(--text-primary)", fontFamily: "var(--font-mono)" }} />
          </label>
          <label className="flex flex-col gap-1" style={{ color: "var(--text-secondary)" }}>
            Total pressure (kPa)
            <input type="number" min={5} max={400} step={0.5} value={p} onChange={(e) => setP(Number(e.target.value))}
                   className="w-28 rounded-lg px-2 py-1.5" style={{ background: "rgba(6,7,12,0.6)", border: "1px solid var(--border-strong)", color: "var(--text-primary)", fontFamily: "var(--font-mono)" }} />
          </label>
          <button type="submit" className="btn-primary rounded-lg px-4 py-1.5 font-semibold">Apply</button>
        </form>
      )}
    </div>
  );
}

export function ScenarioNote({ scenario }: { scenario: Scenario }) {
  return (
    <p className="text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
      <span style={{ color: "var(--text-secondary)" }}>{scenario.name}:</span> {scenario.note}{" "}
      {scenario.citation && <>Source: {scenario.citation}{scenario.basis === "derived" ? " (total pressure derived on the normoxic curve)" : ""}.</>}
    </p>
  );
}

export function EvidenceChips({ evidence, max = 6 }: { evidence: { evidence_id: string; test_id?: string | null }[]; max?: number }) {
  if (!evidence.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[11px]" style={{ color: "var(--text-dim)" }}>Evidence:</span>
      {evidence.slice(0, max).map((e) => (
        <Link key={e.evidence_id} href={`/evidence?id=${e.evidence_id}`} title="Open the source row with its provenance"
              className="rounded-md px-1.5 py-0.5 text-[11px] transition-colors hover:border-cyan-400/60 hover:text-cyan-300"
              style={{ fontFamily: "var(--font-mono)", background: "rgba(79,140,255,0.08)", border: "1px solid rgba(79,140,255,0.22)", color: "var(--accent-ember)" }}>
          {e.test_id ? `test ${e.test_id}` : e.evidence_id.slice(-8)}
        </Link>
      ))}
      {evidence.length > max && <span className="text-[11px]" style={{ color: "var(--text-dim)" }}>+{evidence.length - max} more</span>}
    </div>
  );
}

export function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className="panel panel-hover relative flex flex-col gap-2.5 overflow-hidden rounded-xl p-4 pl-5">
      <span aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px]"
            style={{ background: KIND[insight.kind].color, boxShadow: `0 0 16px ${KIND[insight.kind].color}` }} />
      <span aria-hidden="true" className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full"
            style={{ background: `radial-gradient(circle, ${KIND[insight.kind].color}22, transparent 70%)` }} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{insight.title}</h3>
        <KindBadge kind={insight.kind} />
      </div>
      <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{insight.statement}</p>
      {insight.caveats.length > 0 && (
        <ul className="list-disc pl-5 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          {insight.caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
      )}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <EvidenceChips evidence={insight.evidence} />
        <Link href={chatLink(`Using NASA sources, explain this finding and what it means for spacecraft fire safety: ${insight.statement}`)}
              className="inline-flex items-center gap-1 text-xs font-semibold" style={{ color: "var(--accent-ember)" }}>
          <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" /> Explain with cited sources
        </Link>
      </div>
    </article>
  );
}

const COMPONENT_LABELS: Record<keyof Relevance["components"], string> = {
  oxygen_match: "O₂ match",
  pressure_match: "Pressure match",
  evidence_density: "Nearby tests",
  outcome_data: "Outcome data",
};

export function RelevanceBar({ relevance }: { relevance: Relevance }) {
  const parts = Object.entries(relevance.components) as [keyof Relevance["components"], number][];
  const colors = ["#4F8CFF", "#22D3EE", "#A78BFA", "#22C55E"];
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <div className="flex h-2.5 w-full gap-[2px] overflow-hidden rounded-full p-[1px]" style={{ background: "rgba(124,180,255,0.08)", boxShadow: "inset 0 1px 3px rgba(0,0,0,0.6)" }}
             role="img" aria-label={`Relevance ${Math.round(relevance.score * 100)} of 100`}>
          {parts.map(([k, v], i) => (
            <div key={k} title={`${COMPONENT_LABELS[k]}: ${v.toFixed(2)} × weight ${relevance.weights[k]}`}
                 className="rounded-full" style={{ width: `${v * relevance.weights[k] * 100}%`, background: colors[i], boxShadow: `0 0 10px ${colors[i]}aa` }} />
          ))}
        </div>
        <span className="w-10 text-right text-base font-bold text-gradient-flame" style={{ fontFamily: "var(--font-mono)" }}>{Math.round(relevance.score * 100)}</span>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px]" style={{ color: "var(--text-muted)" }}>
        {parts.map(([k, v], i) => (
          <span key={k} className="inline-flex items-center gap-1">
            <span className="h-2 w-2 rounded-full" style={{ background: colors[i] }} />{COMPONENT_LABELS[k]} {v.toFixed(2)}
          </span>
        ))}
      </div>
    </div>
  );
}

export function ProbabilityBars({ probabilities }: { probabilities: Probabilities }) {
  return (
    <div className="flex flex-col gap-2">
      {END_STATES.map((s) => (
        <div key={s} className="flex items-center gap-3 text-sm">
          <span className="w-44 shrink-0" style={{ color: "var(--text-secondary)" }}>{END_STATE_LABELS[s]}</span>
          <div className="h-3 flex-1 overflow-hidden rounded-full" style={{ background: "rgba(124,180,255,0.08)", boxShadow: "inset 0 1px 3px rgba(0,0,0,0.6)" }}>
            <div className="rounded-full" style={{ width: `${probabilities[s] * 100}%`, background: `linear-gradient(90deg, ${END_STATE_COLORS[s]}99, ${END_STATE_COLORS[s]})`,
              boxShadow: `0 0 12px ${END_STATE_COLORS[s]}88`, height: "100%", transition: "width 600ms var(--ease-out-expo)" }} />
          </div>
          <span className="w-12 text-right font-semibold" style={{ fontFamily: "var(--font-mono)" }}>{pct(probabilities[s])}</span>
        </div>
      ))}
    </div>
  );
}

/** Estimated end-state probabilities across the flight-tested O2 range (extended to a requested O2 beyond it);
 *  red zones are outside the applicability domain, where the model refuses to estimate. */
export function SweepChart({ points, marker }: {
  points: { o2_fraction: number; in_domain: boolean; probabilities: Probabilities | null }[];
  marker?: number;
}) {
  const W = 560, H = 220, L = 44, R = 12, T = 12, B = 34;
  if (!points.length) return null;
  const xs = points.map((p) => p.o2_fraction);
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const x = (v: number) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R);
  const y = (v: number) => T + (1 - v) * (H - T - B);
  const segments = (state: EndState) => {
    const out: string[] = [];
    let current: string[] = [];
    for (const p of points) {
      if (p.probabilities) current.push(`${x(p.o2_fraction).toFixed(1)},${y(p.probabilities[state]).toFixed(1)}`);
      else if (current.length) { out.push(current.join(" ")); current = []; }
    }
    if (current.length) out.push(current.join(" "));
    return out;
  };
  return (
    <figure className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
           aria-label="Estimated probability of each flame end state as oxygen fraction varies, other conditions fixed">
        <defs>
          <filter id="sweep-glow" x="-10%" y="-10%" width="120%" height="120%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--border-default)" strokeWidth={1} strokeDasharray={v === 0 ? undefined : "2 4"} />
            <text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="var(--text-muted)">{v * 100}%</text>
          </g>
        ))}
        {points.map((p, i) => {
          if (p.in_domain) return null;
          // Shade from the midpoint with each neighbour, so a run of refused points reads as one red zone.
          const left = i === 0 ? x(p.o2_fraction) - 6 : x((points[i - 1].o2_fraction + p.o2_fraction) / 2);
          const right = i === points.length - 1 ? x(p.o2_fraction) + 6 : x((points[i + 1].o2_fraction + p.o2_fraction) / 2);
          return <rect key={p.o2_fraction} data-testid="sweep-out-of-domain" x={left} y={T} width={Math.max(right - left, 2)}
                       height={H - T - B} fill="rgba(239,68,68,0.13)" />;
        })}
        {END_STATES.map((s) => segments(s).map((pts, i) => (
          <polyline key={`${s}-${i}`} points={pts} fill="none" stroke={END_STATE_COLORS[s]} strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" filter="url(#sweep-glow)" />
        )))}
        {marker !== undefined && marker >= x0 && marker <= x1 && (
          <g>
            <line x1={x(marker)} x2={x(marker)} y1={T} y2={H - B} stroke="var(--accent-plasma)" strokeDasharray="4 3" />
            <circle cx={x(marker)} cy={T} r={3.5} fill="var(--accent-plasma)" />
          </g>
        )}
        {[x0, (x0 + x1) / 2, x1].map((v) => (
          <text key={v} x={x(v)} y={H - B + 16} textAnchor="middle" fontSize={10} fill="var(--text-muted)">{v.toFixed(2)}</text>
        ))}
        <text x={(L + W - R) / 2} y={H - 4} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">O₂ mole fraction</text>
      </svg>
      <figcaption className="flex flex-wrap gap-3 text-[11px]" style={{ color: "var(--text-muted)" }}>
        {END_STATES.map((s) => (
          <span key={s} className="inline-flex items-center gap-1"><span className="h-2 w-3 rounded-sm" style={{ background: END_STATE_COLORS[s] }} />{END_STATE_LABELS[s]}</span>
        ))}
        <span className="inline-flex items-center gap-1"><span className="h-2 w-3 rounded-sm" style={{ background: "rgba(239,68,68,0.35)" }} />outside the flight-tested domain: no estimate</span>
        {marker !== undefined && <span>dashed line: your O₂</span>}
      </figcaption>
    </figure>
  );
}

/** A title written "3 · Ranked investigations" gets a glowing step chip; any other title renders as is. */
export function SectionTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  const step = /^(\d+)\s*·\s*(.+)$/.exec(title);
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="flex min-w-0 items-start gap-3">
        {step && <span className="step-chip mt-0.5 shrink-0" aria-hidden="true">{step[1].padStart(2, "0")}</span>}
        <div className="min-w-0">
          <h2 className="text-[17px] font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
            {step ? <><span className="sr-only">Step {step[1]}: </span>{step[2]}</> : title}
          </h2>
          {subtitle && <p className="mt-1 max-w-3xl text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{subtitle}</p>}
        </div>
      </div>
      {right}
    </div>
  );
}
