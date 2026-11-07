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
    <div role="status" className="flex items-center gap-2 py-8 text-sm" style={{ color: "var(--text-muted)" }}>
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> {label}
    </div>
  );
}

export function ErrorNote({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="rounded-xl p-4 text-sm" style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.25)" }}>
      <p style={{ color: "var(--text-primary)" }}>{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="mt-2 rounded-lg px-3 py-1.5 text-xs font-semibold"
                style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}>
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
          return (
            <button key={s.scenario_id} role="radio" aria-checked={active} onClick={() => onChange({ scenario: s.scenario_id })}
                    className="rounded-xl px-3 py-2 text-left text-xs"
                    style={{ background: active ? "rgba(59,130,246,0.16)" : "var(--bg-elevated)",
                             border: `1px solid ${active ? "rgba(59,130,246,0.55)" : "var(--border-default)"}`,
                             color: "var(--text-primary)" }}>
              <span className="block font-semibold">{s.name}</span>
              <span className="block mt-0.5" style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                {Math.round(s.o2_fraction * 100)}% O₂ · {s.pressure_kpa.toFixed(1)} kPa
              </span>
            </button>
          );
        })}
        <button role="radio" aria-checked={custom} onClick={() => onChange({ o2_fraction: o2, pressure_kpa: p })}
                className="rounded-xl px-3 py-2 text-left text-xs"
                style={{ background: custom ? "rgba(59,130,246,0.16)" : "var(--bg-elevated)",
                         border: `1px solid ${custom ? "rgba(59,130,246,0.55)" : "var(--border-default)"}`, color: "var(--text-primary)" }}>
          <span className="block font-semibold">Custom atmosphere</span>
          <span className="block mt-0.5" style={{ color: "var(--text-muted)" }}>set O₂ and pressure</span>
        </button>
      </div>
      {custom && (
        <form className="flex flex-wrap items-end gap-3 text-xs" onSubmit={(e) => { e.preventDefault(); onChange({ o2_fraction: o2, pressure_kpa: p }); }}>
          <label className="flex flex-col gap-1" style={{ color: "var(--text-secondary)" }}>
            O₂ mole fraction
            <input type="number" min={0.05} max={1} step={0.01} value={o2} onChange={(e) => setO2(Number(e.target.value))}
                   className="w-28 rounded-lg px-2 py-1.5" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }} />
          </label>
          <label className="flex flex-col gap-1" style={{ color: "var(--text-secondary)" }}>
            Total pressure (kPa)
            <input type="number" min={5} max={400} step={0.5} value={p} onChange={(e) => setP(Number(e.target.value))}
                   className="w-28 rounded-lg px-2 py-1.5" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }} />
          </label>
          <button type="submit" className="rounded-lg px-3 py-1.5 font-semibold" style={{ background: "var(--accent-flame)", color: "white" }}>Apply</button>
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
              className="rounded-md px-1.5 py-0.5 text-[11px]"
              style={{ fontFamily: "var(--font-mono)", background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--accent-ember)" }}>
          {e.test_id ? `test ${e.test_id}` : e.evidence_id.slice(-8)}
        </Link>
      ))}
      {evidence.length > max && <span className="text-[11px]" style={{ color: "var(--text-dim)" }}>+{evidence.length - max} more</span>}
    </div>
  );
}

export function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className="flex flex-col gap-2.5 rounded-xl p-4" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
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
  const colors = ["#3B82F6", "#06B6D4", "#A78BFA", "#22C55E"];
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-2">
        <div className="flex h-2.5 w-full overflow-hidden rounded-full" style={{ background: "var(--border-default)" }}
             role="img" aria-label={`Relevance ${Math.round(relevance.score * 100)} of 100`}>
          {parts.map(([k, v], i) => (
            <div key={k} title={`${COMPONENT_LABELS[k]}: ${v.toFixed(2)} × weight ${relevance.weights[k]}`}
                 style={{ width: `${v * relevance.weights[k] * 100}%`, background: colors[i] }} />
          ))}
        </div>
        <span className="w-10 text-right text-sm font-semibold" style={{ fontFamily: "var(--font-mono)" }}>{Math.round(relevance.score * 100)}</span>
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
          <div className="h-3 flex-1 overflow-hidden rounded-full" style={{ background: "var(--border-default)" }}>
            <div style={{ width: `${probabilities[s] * 100}%`, background: END_STATE_COLORS[s], height: "100%" }} />
          </div>
          <span className="w-12 text-right font-semibold" style={{ fontFamily: "var(--font-mono)" }}>{pct(probabilities[s])}</span>
        </div>
      ))}
    </div>
  );
}

/** Estimated end-state probabilities across the flight-tested O2 range; gaps are outside the applicability domain. */
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
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="var(--border-default)" strokeWidth={1} />
            <text x={L - 6} y={y(v) + 4} textAnchor="end" fontSize={10} fill="var(--text-muted)">{v * 100}%</text>
          </g>
        ))}
        {points.filter((p) => !p.in_domain).map((p) => (
          <rect key={p.o2_fraction} x={x(p.o2_fraction) - 6} y={T} width={12} height={H - T - B} fill="rgba(245,158,11,0.08)" />
        ))}
        {END_STATES.map((s) => segments(s).map((pts, i) => (
          <polyline key={`${s}-${i}`} points={pts} fill="none" stroke={END_STATE_COLORS[s]} strokeWidth={2.5} strokeLinejoin="round" />
        )))}
        {marker !== undefined && marker >= x0 && marker <= x1 && (
          <line x1={x(marker)} x2={x(marker)} y1={T} y2={H - B} stroke="var(--text-secondary)" strokeDasharray="4 3" />
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
        <span className="inline-flex items-center gap-1"><span className="h-2 w-3 rounded-sm" style={{ background: "rgba(245,158,11,0.3)" }} />outside the flight-tested domain (no estimate)</span>
        {marker !== undefined && <span>dashed line: your O₂</span>}
      </figcaption>
    </figure>
  );
}

export function SectionTitle({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold" style={{ color: "var(--text-primary)" }}>{title}</h2>
        {subtitle && <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}
