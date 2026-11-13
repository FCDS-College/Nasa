"use client";

// Suppression Advisor (plan docs/plan/SUPPRESSION_ADVISOR_PLAN.md, D3): which ISS extinguisher, CO₂ or water mist,
// for this cabin. The decision comes from the API (deterministic, no language model); this page only presents it.
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FireExtinguisher, HelpCircle, Info, XCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { ErrorNote, Loading, SectionTitle } from "@/components/fire/FireUi";
import {
  fetchSuppressionAdvice, pct,
  type FireType, type HazardLevel, type SuppressionAdvice, type SuppressionAgent, type SuppressionInput,
} from "@/lib/api/fireSafety";

const FIRE_TYPES: { value: FireType; label: string; note: string }[] = [
  { value: "heptane", label: "Heptane (hydrocarbon liquid)", note: "flight-tested fuel" },
  { value: "methanol", label: "Methanol (alcohol liquid)", note: "flight-tested fuel" },
  { value: "other_liquid", label: "Other / unknown liquid", note: "relative comparison only" },
  { value: "electrical_battery", label: "Electrical / battery", note: "sourced rule only" },
  { value: "solid", label: "Solid material", note: "hazards and evidence only" },
];

const PRESETS: { label: string; input: Partial<SuppressionInput> }[] = [
  { label: "Example cabin (100 m³)", input: { cabin_volume_m3: 100 } },
  { label: "ISS airlock (31 m³, NASA)", input: { cabin_volume_m3: 31 } },
];

const DEFAULT: SuppressionInput = {
  fire_type: "heptane", cabin_volume_m3: 100, pressure_kpa: 101.3, o2_fraction: 0.21, co2_fraction: 0,
  zone: "well_mixed", local_zone_fraction: 0.1, delivery_fraction: 0.5,
};

const AGENT_LABEL = { co2: "CO₂ extinguisher", water_mist: "Water-mist extinguisher" } as const;

const LEVEL_STYLE: Record<HazardLevel, { color: string; bg: string; label: string }> = {
  red: { color: "var(--accent-danger)", bg: "rgba(239,68,68,0.10)", label: "Danger" },
  amber: { color: "var(--accent-warning)", bg: "rgba(245,158,11,0.10)", label: "Caution" },
  green: { color: "var(--accent-success)", bg: "rgba(34,197,94,0.10)", label: "Within limit" },
  info: { color: "var(--text-muted)", bg: "var(--bg-elevated)", label: "Info" },
};

function readQuery(): Partial<SuppressionInput> {
  if (typeof window === "undefined") return {};
  const p = new URLSearchParams(window.location.search);
  const out: Partial<SuppressionInput> = {};
  const fire = p.get("fire_type") as FireType | null;
  if (fire && FIRE_TYPES.some((f) => f.value === fire)) out.fire_type = fire;
  for (const key of ["o2_fraction", "pressure_kpa", "co2_fraction", "cabin_volume_m3"] as const) {
    const raw = p.get(key);
    const v = Number(raw);
    if (raw && Number.isFinite(v)) out[key] = v;
  }
  return out;
}

function Slider({ label, value, min, max, step, unit, format, onChange }: {
  label: string; value: number; min: number; max: number; step: number; unit?: string;
  format?: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
      <span className="flex justify-between">
        <span>{label}</span>
        <span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{format ? format(value) : value}{unit ? ` ${unit}` : ""}</span>
      </span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full" />
    </label>
  );
}

function Banner({ advice }: { advice: SuppressionAdvice }) {
  const agent = advice.recommended_agent;
  const tone = advice.outcome === "recommend" ? "var(--accent-success)" : "var(--accent-warning)";
  const headline = advice.outcome === "recommend" && agent
    ? `Use the ${AGENT_LABEL[agent].toLowerCase()}`
    : advice.outcome === "no_clear_winner" ? "No clear winner: follow the flight rule" : "No recommendation: follow the flight rule";
  const Icon = advice.outcome === "recommend" ? CheckCircle2 : HelpCircle;
  return (
    <div className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: `1px solid ${tone}` }} role="status" aria-live="polite">
      <div className="flex flex-wrap items-center gap-3">
        <Icon className="h-6 w-6" style={{ color: tone }} aria-hidden="true" />
        <h2 className="text-xl font-bold">{headline}</h2>
        <span className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wider"
              style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-secondary)" }}>
          confidence: {advice.confidence}
        </span>
        <span className="text-[11px]" style={{ color: "var(--text-muted)" }}>basis: {advice.basis.replaceAll("_", " ")}</span>
      </div>
      <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{advice.why[0]}</p>
    </div>
  );
}

function Estimate({ label, value, claim }: { label: string; value: number | null | undefined; claim: string }) {
  return (
    <div className="rounded-lg p-3" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
      <div className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{label}</div>
      <div className="mt-1 text-lg font-bold" style={{ fontFamily: "var(--font-mono)" }}>{value === null || value === undefined ? "—" : pct(value)}</div>
      <div className="text-[11px]" style={{ color: "var(--text-dim)" }}>claim class: {claim}</div>
    </div>
  );
}

function AgentCard({ a, recommended, explorerHref }: { a: SuppressionAgent; recommended: boolean; explorerHref: string | null }) {
  const zone = a.post_discharge.fire_zone;
  const cabin = a.post_discharge.cabin_after;
  const level = LEVEL_STYLE[a.hazard_level];
  return (
    <Card>
      <div className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="text-base font-semibold">{AGENT_LABEL[a.agent]}</h3>
            <p className="text-xs" style={{ color: "var(--text-muted)" }}>{a.extinguisher} · source {String(a.charge.source)}</p>
          </div>
          {recommended && (
            <span className="rounded-full px-2 py-0.5 text-[11px] font-semibold" style={{ background: "rgba(34,197,94,0.15)", color: "var(--accent-success)" }}>
              recommended
            </span>
          )}
        </div>

        <div className="grid grid-cols-2 gap-2">
          {a.flex_estimate && <Estimate label="Flight-data estimate" value={a.flex_estimate.p_extinction} claim="estimated" />}
          {a.thermal_estimate && <Estimate label="Thermal model" value={a.thermal_estimate.p_extinction} claim="computed" />}
        </div>
        {(a.flex_estimate || a.thermal_estimate) && (
          <p className="text-[11px]" style={{ color: "var(--text-muted)" }}>Chance the flame goes out after the discharge.</p>
        )}
        {a.flex_estimate?.applicability && !a.flex_estimate.applicability.in_domain && (
          <p className="text-xs" style={{ color: "var(--accent-warning)" }}>
            Flight-data estimate refused: {a.flex_estimate.applicability.reasons.join("; ")}
          </p>
        )}
        {a.withheld.map((w) => (
          <p key={w} className="flex items-start gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" /> {w}
          </p>
        ))}

        <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs" style={{ fontFamily: "var(--font-mono)" }}>
          <dt style={{ color: "var(--text-muted)" }}>Fire-zone O₂</dt><dd>{pct(zone.mole_fractions.O2, 1)}</dd>
          <dt style={{ color: "var(--text-muted)" }}>Fire-zone CO₂</dt><dd>{pct(zone.mole_fractions.CO2, 1)}</dd>
          <dt style={{ color: "var(--text-muted)" }}>Cabin ppCO₂</dt><dd>{cabin.ppco2_mmhg.toFixed(1)} mmHg</dd>
          <dt style={{ color: "var(--text-muted)" }}>Cabin pressure</dt><dd>{cabin.pressure_kpa.toFixed(1)} kPa</dd>
          {a.effective_enthalpy_kcal_per_mol_o2 !== null && (<>
            <dt style={{ color: "var(--text-muted)" }}>Heat sink</dt><dd>{a.effective_enthalpy_kcal_per_mol_o2.toFixed(1)} kcal/mol O₂</dd>
          </>)}
        </dl>

        <div className="flex flex-col gap-1.5">
          <p className="text-[11px] font-semibold uppercase tracking-wider" style={{ color: level.color }}>Crew safety: {level.label}</p>
          {a.hazards.filter((h) => h.level !== "info").map((h) => {
            const s = LEVEL_STYLE[h.level];
            return (
              <p key={h.hazard} className="rounded-lg px-2.5 py-1.5 text-xs leading-relaxed" style={{ background: s.bg, color: "var(--text-primary)" }}>
                <span className="font-semibold" style={{ color: s.color }}>{s.label}. </span>{h.statement}
                {h.sources?.length ? <span style={{ color: "var(--text-muted)" }}> ({h.sources.join("; ")})</span> : null}
              </p>
            );
          })}
        </div>

        {a.flex_estimate?.similar_tests?.length ? (
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
            Nearest real FLEX flight tests:{" "}
            {a.flex_estimate.similar_tests.map((t, i) => (
              <span key={t.experiment_id}>
                {i > 0 && ", "}
                {t.end_state_evidence_id
                  ? <Link href={`/evidence?id=${t.end_state_evidence_id}`} className="hover:underline" style={{ color: "var(--accent-ember)" }}>{t.test_id}</Link>
                  : t.test_id}
                {t.end_state ? ` (${t.end_state})` : ""}
              </span>
            ))}
          </p>
        ) : null}
        {explorerHref && (
          <Link href={explorerHref} className="text-xs font-semibold hover:underline" style={{ color: "var(--accent-ember)" }}>
            See this post-discharge atmosphere in the Flame Outcome Explorer →
          </Link>
        )}
      </div>
    </Card>
  );
}

function DeliverySlider({ value, crossover, onChange }: { value: number; crossover: number | null; onChange: (v: number) => void }) {
  return (
    <Card>
      <SectionTitle title="How much of the mist reaches the fire?"
        subtitle="Water removes about 3× more heat per kg than CO₂, but only the part that reaches the flame counts. Aim, distance and obstructions decide this share." />
      <div className="relative mt-2 h-3 w-full rounded-full" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
        {crossover !== null && (
          <>
            <div className="absolute inset-y-0 left-0 rounded-l-full" style={{ width: `${crossover * 100}%`, background: "rgba(59,130,246,0.25)" }} />
            <div className="absolute inset-y-0 right-0 rounded-r-full" style={{ width: `${(1 - crossover) * 100}%`, background: "rgba(34,197,94,0.25)" }} />
            <div className="absolute -top-1.5 h-6 w-0.5" style={{ left: `${crossover * 100}%`, background: "var(--text-primary)" }} aria-hidden="true" />
          </>
        )}
        <div className="absolute -top-1 h-5 w-5 -translate-x-1/2 rounded-full" style={{ left: `${value * 100}%`, background: "var(--accent-flame)", border: "2px solid white" }} aria-hidden="true" />
      </div>
      <div className="mt-2 flex justify-between text-[11px]" style={{ color: "var(--text-muted)" }}>
        <span>CO₂ removes more heat</span>
        {crossover !== null && <span style={{ color: "var(--text-primary)" }}>crossover {pct(crossover)}</span>}
        <span>Water mist removes more heat</span>
      </div>
      <div className="mt-3">
        <Slider label="Your assumed delivery (an assumption, not a measurement)" value={value} min={0} max={1} step={0.05}
                format={(v) => pct(v)} onChange={onChange} />
      </div>
    </Card>
  );
}

export default function SuppressionAdvisor() {
  const [input, setInput] = useState<SuppressionInput>(DEFAULT);
  const [advice, setAdvice] = useState<SuppressionAdvice | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [ready, setReady] = useState(false);
  const seq = useRef(0);

  useEffect(() => {
    queueMicrotask(() => { setInput((prev) => ({ ...prev, ...readQuery() })); setReady(true); });
  }, []);

  const run = useCallback(async (q: SuppressionInput) => {
    const n = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const r = await fetchSuppressionAdvice(q);
      if (n === seq.current) setAdvice(r);
    } catch (e) {
      if (n === seq.current) setError(e instanceof Error ? e.message : "The advisor could not be reached.");
    } finally {
      if (n === seq.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => run(input), 200);
    return () => clearTimeout(t);
  }, [input, ready, run]);

  const set = (patch: Partial<SuppressionInput>) => setInput((prev) => ({ ...prev, ...patch }));
  const flexFuel = input.fire_type === "heptane" ? "Heptane" : input.fire_type === "methanol" ? "Methanol" : null;
  const explorerHref = (a: SuppressionAgent) => {
    if (!flexFuel || a.agent !== "co2") return null;
    const z = a.post_discharge.fire_zone;
    const q = new URLSearchParams({ fuel: flexFuel, o2_fraction: z.mole_fractions.O2.toFixed(4),
      pressure_kpa: z.pressure_kpa.toFixed(2), co2_fraction: z.mole_fractions.CO2.toFixed(4) });
    return `/explorer?${q}`;
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-col gap-2">
        <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--accent-ember)" }}>
          <FireExtinguisher className="h-3.5 w-3.5" aria-hidden="true" /> Suppression Advisor
        </p>
        <h1 className="text-2xl font-bold">Which extinguisher for this cabin?</h1>
        <p className="max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Compares the ISS CO₂ extinguisher with the Fine Water Mist extinguisher for your cabin: what each discharge does to the air
          around the fire and to the air the crew breathes. It names a winner only when the evidence supports one.
        </p>
      </header>

      {error && <ErrorNote message={error} onRetry={() => run(input)} />}
      {!advice ? <Loading label="Working out the discharge…" /> : (
        <div style={{ opacity: loading ? 0.6 : 1, transition: "opacity 150ms" }}><Banner advice={advice} /></div>
      )}

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <Card>
          <SectionTitle title="Cabin and fire" />
          <div className="flex flex-col gap-4">
            <fieldset className="flex flex-col gap-1.5 text-xs">
              <legend className="mb-1 text-xs" style={{ color: "var(--text-secondary)" }}>What is burning?</legend>
              {FIRE_TYPES.map((f) => (
                <label key={f.value} className="flex cursor-pointer items-center justify-between gap-2 rounded-lg px-3 py-1.5"
                       style={{ background: input.fire_type === f.value ? "rgba(59,130,246,0.16)" : "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                  <span className="flex items-center gap-1.5">
                    <input type="radio" name="fire_type" checked={input.fire_type === f.value} onChange={() => set({ fire_type: f.value })} /> {f.label}
                  </span>
                  <span style={{ color: "var(--text-dim)" }}>{f.note}</span>
                </label>
              ))}
            </fieldset>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <button key={p.label} onClick={() => set(p.input)} className="rounded-lg px-2.5 py-1.5 text-[11px]"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}>
                  {p.label}
                </button>
              ))}
            </div>
            <Slider label="Cabin free volume" value={input.cabin_volume_m3} min={5} max={300} step={1} unit="m³" onChange={(v) => set({ cabin_volume_m3: v })} />
            <Slider label="Cabin pressure" value={input.pressure_kpa} min={40} max={160} step={0.5} unit="kPa" onChange={(v) => set({ pressure_kpa: v })} />
            <Slider label="O₂ mole fraction" value={input.o2_fraction} min={0.12} max={0.5} step={0.01} onChange={(v) => set({ o2_fraction: v })} />
            <Slider label="CO₂ already in the cabin" value={input.co2_fraction} min={0} max={0.02} step={0.0005} format={(v) => pct(v, 2)} onChange={(v) => set({ co2_fraction: v })} />
            <fieldset className="flex gap-2 text-xs">
              <legend className="mb-1 text-xs" style={{ color: "var(--text-secondary)" }}>Where the discharge goes</legend>
              {([["well_mixed", "Whole cabin"], ["local", "Aimed at the fire"]] as const).map(([z, label]) => (
                <label key={z} className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5"
                       style={{ background: input.zone === z ? "rgba(59,130,246,0.16)" : "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                  <input type="radio" name="zone" checked={input.zone === z} onChange={() => set({ zone: z })} /> {label}
                </label>
              ))}
            </fieldset>
            {input.zone === "local" && (
              <Slider label="Share of the cabin the discharge fills (assumption)" value={input.local_zone_fraction} min={0.02} max={1} step={0.01}
                      format={(v) => pct(v)} onChange={(v) => set({ local_zone_fraction: v })} />
            )}
            <p className="text-[11px] leading-relaxed" style={{ color: "var(--text-dim)" }}>
              “Whole cabin” is the cautious case. Crew safety is always judged on the whole cabin, because that is what the crew breathes.
            </p>
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          {advice && (
            <div className="grid gap-5 md:grid-cols-2">
              {(["co2", "water_mist"] as const).map((k) => (
                <AgentCard key={k} a={advice.agents[k]} recommended={advice.recommended_agent === k} explorerHref={explorerHref(advice.agents[k])} />
              ))}
            </div>
          )}

          {advice?.crossover_delivery_fraction && (
            <DeliverySlider value={input.delivery_fraction} crossover={advice.crossover_delivery_fraction.value}
                            onChange={(v) => set({ delivery_fraction: v })} />
          )}

          {advice && (
            <Card>
              <SectionTitle title="Why, and what would change it" />
              <ul className="list-disc pl-5 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {advice.why.map((w) => <li key={w}>{w}</li>)}
              </ul>
              <p className="mt-3 text-[11px] font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>What would change the answer</p>
              <ul className="list-disc pl-5 text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
                {advice.what_would_change_it.map((w) => <li key={w}>{w}</li>)}
                <li>A CO₂ discharge reaches the CO₂ danger level (IDLH) in a cabin smaller than {advice.co2_idlh_volume_m3.toFixed(0)} m³.</li>
              </ul>
            </Card>
          )}

          {advice && (
            <Card>
              <SectionTitle title="Evidence and assumptions" />
              <ul className="flex flex-col gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
                {advice.evidence.map((e) => (
                  <li key={e.id}><span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{e.id}</span> · {e.title}
                    <span style={{ color: "var(--text-dim)" }}> ({e.kind.replace("_", " ")})</span></li>
                ))}
              </ul>
              <ul className="mt-3 flex flex-col gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                {Object.entries(advice.assumptions).map(([k, v]) => <li key={k}><span className="font-semibold">{k.replaceAll("_", " ")}:</span> {v}</li>)}
              </ul>
              <p className="mt-3 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>{advice.scope}</p>
            </Card>
          )}
        </div>
      </div>

      <footer className="flex items-start gap-2 rounded-xl p-3 text-xs" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)", color: "var(--text-secondary)" }}>
        {advice?.outcome === "no_recommendation" ? <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" /> : <AlertTriangle className="h-4 w-4 shrink-0" style={{ color: "var(--accent-warning)" }} aria-hidden="true" />}
        <span>{advice?.disclaimer ?? "Decision support only. It does not replace flight rules or the emergency procedure."}</span>
      </footer>
    </div>
  );
}
