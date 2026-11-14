// Fire-safety dashboard client (contract 0.7.0, tag "Fire safety"). Every call goes through the
// same-origin read-only proxy (app/api/[...path]); nothing here needs a write token.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export type InsightKind = "measured_statistic" | "model_estimate" | "coverage_gap";
export type EndState = "Completion" | "Disruption" | "Extinction";

export interface Scenario {
  scenario_id: string;
  name: string;
  o2_fraction: number;
  pressure_kpa: number;
  ppo2_kpa: number;
  basis: "quoted" | "derived" | "user" | "historical";
  note: string;
  citation: string | null;
  gravity: Gravity;
  kind: "mission" | "historical" | "custom";
}

export type Gravity = "microgravity" | "lunar" | "martian" | "earth";

// Scenario-level verdict (contract 0.7.0, ADR-013): does any flight test speak to this atmosphere?
export interface Coverage {
  verdict: "covered" | "partial" | "none";
  headline: string;
  tests_total: number;
  neighbourhood_tests: number;
  neighbourhood_by_investigation: Record<string, number>;
  gravity: { scenario: Gravity; flight_tests: string[]; covered: boolean };
  tested_range: { o2_fraction: ConditionRange | null; pressure_kpa: ConditionRange | null };
  nearest_test: {
    investigation_id: string;
    experiment_id: string;
    test_id: string;
    o2_fraction: number;
    pressure_kpa: number | null;
    end_state: string | null;
    evidence: string[];
  } | null;
  gap: { o2_delta: number; o2_ratio: number | null; pressure_ratio: number | null } | null;
  reasons: string[];
  method: string;
}

export interface CitedSource {
  source_id: string;
  page: number;
  quote: string | null;
  title: string | null;
  short_name: string | null;
  access_url: string | null;
  evidence_id: string | null;
}

export interface ScenarioHistory {
  scenario: Scenario;
  year: number;
  story: string;
  lesson: string;
  lesson_sources: CitedSource[];
  timeline: { date: string; title: string; text: string; sources: CitedSource[] }[];
  alternative: { scenario: Scenario; headline: string; rationale: string; sources: CitedSource[] };
  claim_class: "cited_history";
}

export interface ConditionRange { min: number; max: number; n: number }

export interface InvestigationData {
  tests: number;
  o2_fraction: ConditionRange | null;
  o2_approximate?: boolean;
  pressure_kpa: ConditionRange | null;
  flow_velocity_m_s: ConditionRange | null;
  fuels_or_materials: { name: string; tests: number }[];
  distinct_fuels_or_materials?: number;
  end_states?: Record<string, number> | null;
  end_state_recorded: boolean;
  duration_recorded: boolean;
  quality_flags?: Record<string, number>;
}

export interface Relevance {
  score: number;
  components: { oxygen_match: number; pressure_match: number; evidence_density: number; outcome_data: number };
  weights: Record<string, number>;
  neighbourhood_tests: number;
  not_recorded: string[];
  explanation: string[];
}

export interface CitedText { text: string; evidence_id: string }

export interface InvestigationSummary {
  investigation_id: string;
  acronym: string | null;
  title: string;
  status: "ingested" | "metadata_only";
  flight_platform: string | null;
  hardware: string | null;
  dates: string | null;
  persistent_identifier: string | null;
  license: string | null;
  access_url: string | null;
  fire_safety_use: string[];
  key_variables: string[];
  key_outputs: string[];
  objective: CitedText | null;
  data: InvestigationData;
  coverage_note: string | null;
  relevance: Relevance | null;
  rank?: number | null;
}

export interface EvidenceRef { evidence_id: string; experiment_id?: string | null; test_id?: string | null }

export interface Insight {
  insight_id: string;
  title: string;
  kind: InsightKind;
  investigations: string[];
  statement: string;
  numbers: Record<string, unknown>;
  evidence: EvidenceRef[];
  caveats: string[];
}

export interface FlightTestRef {
  experiment_id: string;
  test_id: string;
  fuel_or_material: string | null;
  o2_fraction: number | null;
  pressure_kpa: number | null;
  flow_velocity_m_s?: number | null;
  end_state: EndState | null;
  duration_s?: number | null;
  end_state_evidence_id: string | null;
  distance?: number;
  droplet_diameter_mm?: number;
  co2_fraction?: number;
  he_fraction?: number;
}

export interface InvestigationDetail extends InvestigationSummary {
  summary_sections: { heading: string; text: string; evidence_id: string }[];
  publications: string[];
  metadata_document_id: string | null;
  insights: Insight[];
  sample_tests: FlightTestRef[];
}

export interface InvestigationList {
  scenario: Scenario;
  scenarios: Scenario[];
  ranking_method: string;
  coverage: Coverage;
  items: InvestigationSummary[];
  not_acquired: { investigation_id: string; acronym: string; title: string; note: string }[];
  totals: { investigations: number; with_data: number; flight_tests: number };
}

export type Probabilities = Record<EndState, number>;

export interface FlexOutcome {
  input: Record<string, number | string>;
  probabilities: Probabilities | null;
  predicted_end_state: EndState | null;
  applicability: {
    in_domain: boolean;
    reasons: string[];
    nearest_test_distance: number | null;
    max_distance: number;
    checks: { feature: string; label: string; value: number; trained_min: number; trained_max: number; inside: boolean }[];
  };
  similar_tests: FlightTestRef[];
  similar_tests_end_states: Record<string, number>;
  o2_sweep: { o2_fraction: number; in_domain: boolean; probabilities: Probabilities | null }[];
  model: {
    model_version: string;
    model_kind: string;
    training_rows: number;
    test_days: number;
    class_counts: Record<string, number>;
    primary_estimate: {
      method: string;
      macro_f1: { mean: number; sd: number };
      balanced_accuracy: { mean: number; sd: number };
      extinction_roc_auc: { mean: number; sd: number };
      majority_baseline_macro_f1: { mean: number; sd: number };
    };
    holdout: { macro_f1: number; balanced_accuracy: number; extinction_roc_auc: number; accuracy: number };
    holdout_note: string;
    /** Since model 1.1.0: the probabilities are prior-corrected; grouped-CV figures, calibrated vs uncalibrated. */
    calibration?: {
      method: string;
      estimate: string;
      extinction_ece: { mean: number; sd: number };
      raw_extinction_ece: { mean: number; sd: number };
      log_loss: { mean: number; sd: number };
      raw_log_loss: { mean: number; sd: number };
      extinction_roc_auc: { mean: number; sd: number };
      most_likely_class_macro_f1: { mean: number; sd: number };
    } | null;
    feature_importance: { feature: string; label: string; mean_drop_in_macro_f1: number; sd: number }[];
    report: string;
  };
  claim_class: "estimated";
  scope: string;
}

export interface ScenarioQuery { scenario?: string; o2_fraction?: number; pressure_kpa?: number }

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// Shared by every client that goes through the read-only proxy. An array value repeats the parameter
// (`predicate=a&predicate=b`), as the contract's `explode: true` list parameters expect.
export async function get<T>(
  path: string,
  query: Record<string, string | number | readonly string[] | undefined> = {},
): Promise<T> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === "") continue;
    if (Array.isArray(v)) v.forEach((item) => params.append(k, item));
    else params.set(k, String(v));
  }
  const qs = params.toString();
  const res = await fetch(`${API_BASE}/api/${path}${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) {
    let message = `The Flame API answered ${res.status}.`;
    try {
      const body = await res.json();
      const err = body?.error;
      if (err?.field_errors?.length) message = err.field_errors.map((f: { message: string }) => f.message).join("; ");
      else if (err?.message) message = err.message;
      else if (err?.code === "API_NOT_CONFIGURED") message = "The dashboard is not connected to a Flame API (FLAME_API_ORIGIN is unset).";
      else if (err?.code === "UPSTREAM_UNAVAILABLE") message = "The Flame API could not be reached.";
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

const scenarioParams = (q: ScenarioQuery) =>
  q.o2_fraction !== undefined && q.pressure_kpa !== undefined
    ? { o2_fraction: q.o2_fraction, pressure_kpa: q.pressure_kpa }
    : { scenario: q.scenario };

export const fetchInvestigations = (q: ScenarioQuery) => get<InvestigationList>("investigations", scenarioParams(q));

export const fetchInvestigation = (id: string, q: ScenarioQuery) =>
  get<{ investigation: InvestigationDetail; scenario: Scenario }>(`investigations/${encodeURIComponent(id)}`, scenarioParams(q));

export const fetchInsights = (q: ScenarioQuery) => get<{ scenario: Scenario; items: Insight[] }>("insights", scenarioParams(q));

export interface FlexInput {
  fuel: "Heptane" | "Methanol";
  o2_fraction: number;
  pressure_kpa: number;
  co2_fraction: number;
  he_fraction: number;
  droplet_diameter_mm: number;
}

export const fetchScenarioHistory = (scenarioId: string) =>
  get<ScenarioHistory>(`scenarios/${encodeURIComponent(scenarioId)}/history`);

export const fetchFlexOutcome = (input: FlexInput) =>
  get<FlexOutcome>("insights/flex-outcome", input as unknown as Record<string, string | number>);

// Suppression Advisor (contract 0.8.0, ADR-014): CO₂ vs water-mist PFE for a cabin. Deterministic, no language model.
export type FireType = "heptane" | "methanol" | "other_liquid" | "electrical_battery" | "solid";
export type HazardLevel = "red" | "amber" | "green" | "info";

export interface SuppressionInput {
  fire_type: FireType;
  cabin_volume_m3: number;
  pressure_kpa: number;
  o2_fraction: number;
  co2_fraction: number;
  zone: "well_mixed" | "local";
  local_zone_fraction: number;
  delivery_fraction: number;
}

export interface SuppressionAtmosphere {
  pressure_kpa: number;
  mole_fractions: Record<string, number>;
  liquid_water_mol_per_mol_gas: number;
  ppo2_kpa: number;
  ppco2_mmhg: number;
}

export interface SuppressionHazard {
  hazard: string;
  level: HazardLevel;
  value?: number;
  before?: number;
  unit?: string;
  statement: string;
  claim_class: "reference" | "computed";
  sources?: string[];
}

export interface SuppressionAgent {
  agent: "co2" | "water_mist";
  extinguisher: string;
  charge: Record<string, string | number>;
  post_discharge: { agent: string; fire_zone: SuppressionAtmosphere; cabin_after: SuppressionAtmosphere };
  effective_enthalpy_kcal_per_mol_o2: number | null;
  hazards: SuppressionHazard[];
  hazard_level: HazardLevel;
  flex_estimate: {
    p_extinction: number | null;
    claim_class: "estimated";
    applicability: { in_domain: boolean; reasons: string[] } | null;
    similar_tests: { experiment_id: string; test_id: string; end_state: EndState | null; end_state_evidence_id: string | null }[];
  } | null;
  thermal_estimate: { p_extinction: number; claim_class: "computed"; model_version: string } | null;
  withheld: string[];
}

export interface SuppressionAdvice {
  input: Record<string, string | number>;
  assumptions: Record<string, string>;
  outcome: "recommend" | "no_clear_winner" | "no_recommendation";
  recommended_agent: "co2" | "water_mist" | null;
  confidence: "high" | "moderate" | "low" | "none";
  basis: "thermal_model_comparison" | "relative_only" | "hazard_veto" | "sourced_rule" | "out_of_scope";
  why: string[];
  what_would_change_it: string[];
  decision_sources: string[];
  crossover_delivery_fraction: { value: number | null; claim_class: "computed"; statement: string; basis?: string } | null;
  co2_idlh_volume_m3: number;
  agents: { co2: SuppressionAgent; water_mist: SuppressionAgent };
  gates: { water_probability_allowed: boolean; model_signal_ok: boolean };
  evidence: { id: string; title: string; kind: string }[];
  scope: string;
  disclaimer: string;
}

export const fetchSuppressionAdvice = (input: Partial<SuppressionInput>) =>
  get<SuppressionAdvice>("insights/suppression-advice", input as unknown as Record<string, string | number>);

export const fetchCounts = () =>
  get<{ documents: number; experiments: number; evidence: number; analyses?: number; chunks?: number; indexed_chunks?: number }>("dashboard/counts");

export function pct(x: number | null | undefined, digits = 0): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const v = x * 100;
  if (v > 0 && v < 1 && digits === 0) return "<1%";
  return `${v.toFixed(digits)}%`;
}

export function fmtRange(r: ConditionRange | null, digits = 2, unit = ""): string {
  if (!r) return "not recorded";
  const lo = r.min.toFixed(digits);
  const hi = r.max.toFixed(digits);
  return `${lo === hi ? lo : `${lo}–${hi}`}${unit ? ` ${unit}` : ""}`;
}

export function chatLink(question: string): string {
  return `/chat?q=${encodeURIComponent(question)}`;
}
