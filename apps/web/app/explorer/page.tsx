"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { CheckCircle2, Info, XCircle } from "lucide-react";
import { Card } from "@/components/ui/Card";
import {
  END_STATE_COLORS, END_STATE_LABELS, ErrorNote, Loading, ProbabilityBars, SectionTitle, SweepChart,
} from "@/components/fire/FireUi";
import { fetchFlexOutcome, pct, type FlexInput, type FlexOutcome } from "@/lib/api/fireSafety";

const PRESETS: { label: string; input: Partial<FlexInput> }[] = [
  { label: "ISS air (21% O₂, 101 kPa)", input: { o2_fraction: 0.21, pressure_kpa: 101.3 } },
  { label: "Pre-EVA (30% O₂, 70.3 kPa)", input: { o2_fraction: 0.30, pressure_kpa: 70.3 } },
  { label: "Lunar lander (34% O₂, 62.7 kPa)", input: { o2_fraction: 0.34, pressure_kpa: 62.7 } },
  { label: "Low O₂ (15%, 101 kPa)", input: { o2_fraction: 0.15, pressure_kpa: 101.3 } },
  { label: "Apollo 1 pad, 1967 (100% O₂, 115 kPa)", input: { o2_fraction: 1.0, pressure_kpa: 115.1, co2_fraction: 0, he_fraction: 0 } },   // pure O₂: no diluent
];

const DEFAULT: FlexInput = { fuel: "Heptane", o2_fraction: 0.21, pressure_kpa: 101.3, co2_fraction: 0, he_fraction: 0, droplet_diameter_mm: 3 };

function Slider({ label, value, min, max, step, unit, onChange }: {
  label: string; value: number; min: number; max: number; step: number; unit?: string; onChange: (v: number) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs" style={{ color: "var(--text-secondary)" }}>
      <span className="flex justify-between"><span>{label}</span><span style={{ fontFamily: "var(--font-mono)", color: "var(--text-primary)" }}>{value}{unit ? ` ${unit}` : ""}</span></span>
      <input type="range" min={min} max={max} step={step} value={value} onChange={(e) => onChange(Number(e.target.value))} className="w-full" />
    </label>
  );
}

export default function OutcomeExplorer() {
  const [input, setInput] = useState<FlexInput>(DEFAULT);
  const [result, setResult] = useState<FlexOutcome | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const seq = useRef(0);

  const run = useCallback(async (q: FlexInput) => {
    const n = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const r = await fetchFlexOutcome(q);
      if (n === seq.current) setResult(r);
    } catch (e) {
      if (n === seq.current) setError(e instanceof Error ? e.message : "The model could not be reached.");
    } finally {
      if (n === seq.current) setLoading(false);
    }
  }, []);

  // The Suppression Advisor links here with a post-discharge atmosphere in the query string.
  useEffect(() => {
    queueMicrotask(() => {
      const p = new URLSearchParams(window.location.search);
      const patch: Partial<FlexInput> = {};
      const fuel = p.get("fuel");
      if (fuel === "Heptane" || fuel === "Methanol") patch.fuel = fuel;
      for (const key of ["o2_fraction", "pressure_kpa", "co2_fraction"] as const) {
        const raw = p.get(key);
        if (raw && Number.isFinite(Number(raw))) patch[key] = Number(raw);
      }
      if (Object.keys(patch).length) setInput((prev) => ({ ...prev, ...patch }));
    });
  }, []);

  useEffect(() => {
    const t = setTimeout(() => run(input), 200);
    return () => clearTimeout(t);
  }, [input, run]);

  const advisorHref = `/suppression?${new URLSearchParams({
    fire_type: input.fuel.toLowerCase(), o2_fraction: String(input.o2_fraction), pressure_kpa: String(input.pressure_kpa),
    co2_fraction: String(input.co2_fraction),
  })}`;

  const set = (patch: Partial<FlexInput>) => setInput((prev) => ({ ...prev, ...patch }));
  const m = result?.model;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-6 sm:px-6 sm:py-8">
      <header className="flex flex-col gap-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--accent-ember)" }}>FLEX outcome model</p>
        <h1 className="text-2xl font-bold">Will a droplet flame put itself out?</h1>
        <p className="max-w-3xl text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          Trained on {m?.training_rows ?? 261} real FLEX droplet tests flown on the ISS. Set the atmosphere and droplet; the model estimates how
          the flame ends, shows the most similar real flight tests, and refuses to answer outside the conditions NASA actually flew.
        </p>
        <Link href={advisorHref} className="w-fit text-xs font-semibold hover:underline" style={{ color: "var(--accent-ember)" }}>
          Which extinguisher for this atmosphere? Open the Suppression Advisor →
        </Link>
      </header>

      <div className="grid gap-5 lg:grid-cols-[340px_1fr]">
        <Card>
          <SectionTitle title="Conditions" />
          <div className="flex flex-col gap-4">
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <button key={p.label} onClick={() => set(p.input)} className="rounded-lg px-2.5 py-1.5 text-[11px]"
                        style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}>
                  {p.label}
                </button>
              ))}
            </div>
            <fieldset className="flex gap-2 text-xs">
              <legend className="mb-1 text-xs" style={{ color: "var(--text-secondary)" }}>Fuel</legend>
              {(["Heptane", "Methanol"] as const).map((f) => (
                <label key={f} className="flex cursor-pointer items-center gap-1.5 rounded-lg px-3 py-1.5"
                       style={{ background: input.fuel === f ? "rgba(59,130,246,0.16)" : "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                  <input type="radio" name="fuel" checked={input.fuel === f} onChange={() => set({ fuel: f })} /> {f}
                </label>
              ))}
            </fieldset>
            <Slider label="O₂ mole fraction" value={input.o2_fraction} min={0.08} max={1} step={0.01} onChange={(v) => set({ o2_fraction: v })} />
            <Slider label="Total pressure" value={input.pressure_kpa} min={40} max={320} step={0.5} unit="kPa" onChange={(v) => set({ pressure_kpa: v })} />
            <Slider label="CO₂ diluent (mole fraction)" value={input.co2_fraction} min={0} max={0.7} step={0.01} onChange={(v) => set({ co2_fraction: v })} />
            <Slider label="He diluent (mole fraction)" value={input.he_fraction} min={0} max={0.5} step={0.01} onChange={(v) => set({ he_fraction: v })} />
            <Slider label="Initial droplet diameter" value={input.droplet_diameter_mm} min={1} max={5} step={0.05} unit="mm" onChange={(v) => set({ droplet_diameter_mm: v })} />
          </div>
        </Card>

        <div className="flex flex-col gap-5">
          {error && <ErrorNote message={error} onRetry={() => run(input)} />}
          <Card>
            <SectionTitle title="Estimated end state" subtitle="Claim class: estimated. Green = the flame self-extinguished (the fire-safe outcome)."
                          right={loading ? <span className="text-xs" style={{ color: "var(--text-muted)" }}>updating…</span> : undefined} />
            {!result ? <Loading label="Running the model…" /> : result.probabilities ? (
              <div className="flex flex-col gap-3">
                <ProbabilityBars probabilities={result.probabilities} />
                <p className="flex items-center gap-1.5 text-xs" style={{ color: "var(--accent-success)" }}>
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Inside the flight-tested domain
                  (nearest real test at distance {result.applicability.nearest_test_distance?.toFixed(2)}, limit {result.applicability.max_distance.toFixed(2)}).
                </p>
              </div>
            ) : (
              <div className="rounded-xl p-4 text-sm" style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.3)" }}>
                <p className="flex items-center gap-1.5 font-semibold" style={{ color: "var(--accent-warning)" }}>
                  <XCircle className="h-4 w-4" aria-hidden="true" /> No estimate: these conditions were never flown
                </p>
                <ul className="mt-2 list-disc pl-5 text-xs" style={{ color: "var(--text-secondary)" }}>
                  {result.applicability.reasons.map((r) => <li key={r}>{r}</li>)}
                </ul>
                <p className="mt-2 text-xs" style={{ color: "var(--text-muted)" }}>The model refuses to extrapolate. The nearest real flight tests are still listed below.</p>
              </div>
            )}
          </Card>

          {result && (
            <Card>
              <SectionTitle title="How oxygen changes the outcome" subtitle="Your other conditions held fixed; only O₂ varies across the flight-tested range (and out to your O₂ when it lies beyond it)." />
              <SweepChart points={result.o2_sweep} marker={input.o2_fraction} />
            </Card>
          )}

          {result && (
            <Card>
              <SectionTitle title="Most similar real flight tests" subtitle="What actually happened on the ISS. Click a test for its source row." />
              <div className="overflow-x-auto">
                <table className="w-full min-w-[560px] text-left text-xs">
                  <thead style={{ color: "var(--text-muted)" }}>
                    <tr>{["Test", "Fuel", "O₂", "Pressure", "CO₂", "He", "Droplet", "Recorded end state"].map((h) => <th key={h} scope="col" className="px-2 py-2">{h}</th>)}</tr>
                  </thead>
                  <tbody style={{ fontFamily: "var(--font-mono)" }}>
                    {result.similar_tests.map((t) => (
                      <tr key={t.experiment_id} style={{ borderTop: "1px solid var(--border-default)" }}>
                        <td className="px-2 py-1.5">
                          {t.end_state_evidence_id ? <Link href={`/evidence?id=${t.end_state_evidence_id}`} className="hover:underline" style={{ color: "var(--accent-ember)" }}>{t.test_id}</Link> : t.test_id}
                        </td>
                        <td className="px-2 py-1.5">{t.fuel_or_material}</td>
                        <td className="px-2 py-1.5">{t.o2_fraction?.toFixed(3)}</td>
                        <td className="px-2 py-1.5">{t.pressure_kpa?.toFixed(1)} kPa</td>
                        <td className="px-2 py-1.5">{t.co2_fraction?.toFixed(2)}</td>
                        <td className="px-2 py-1.5">{t.he_fraction?.toFixed(2)}</td>
                        <td className="px-2 py-1.5">{t.droplet_diameter_mm?.toFixed(2)} mm</td>
                        <td className="px-2 py-1.5">
                          {t.end_state && <span className="inline-flex items-center gap-1"><span className="h-2 w-2 rounded-full" style={{ background: END_STATE_COLORS[t.end_state] }} />{END_STATE_LABELS[t.end_state]}</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {m && (
            <Card>
              <SectionTitle title="How good is this model?" subtitle={`${m.model_version} · ${m.training_rows} tests on ${m.test_days} test days`} />
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                {[
                  ["Macro-F1", `${m.primary_estimate.macro_f1.mean.toFixed(2)} ± ${m.primary_estimate.macro_f1.sd.toFixed(2)}`, `majority-class baseline ${m.primary_estimate.majority_baseline_macro_f1.mean.toFixed(2)}`],
                  ["Extinction ROC-AUC", `${m.primary_estimate.extinction_roc_auc.mean.toFixed(2)} ± ${m.primary_estimate.extinction_roc_auc.sd.toFixed(2)}`, "self-extinguish vs not; 0.5 = chance"],
                  ["Balanced accuracy", `${pct(m.primary_estimate.balanced_accuracy.mean)}`, "3 classes; 33% = chance"],
                ].map(([k, v, n]) => (
                  <div key={k} className="rounded-lg p-3" style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}>
                    <div className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>{k}</div>
                    <div className="mt-1 text-lg font-bold" style={{ fontFamily: "var(--font-mono)" }}>{v}</div>
                    <div className="text-[11px]" style={{ color: "var(--text-dim)" }}>{n}</div>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
                <Info className="mr-1 inline h-3.5 w-3.5" aria-hidden="true" />
                {m.primary_estimate.method}: no test day is ever in both the training and the scoring set. Most important inputs (drop in macro-F1 when
                shuffled, on held-out days): {m.feature_importance.slice(0, 3).map((f) => `${f.label} ${f.mean_drop_in_macro_f1.toFixed(2)}`).join("; ")}.
                {" "}{result?.scope} Full report: <code>{m.report}</code>.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
