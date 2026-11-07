// Fire-safety dashboard client (contract 0.5.0, tag "Fire safety"). Every call goes through the
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
  basis: "quoted" | "derived" | "user";
  note: string;
  citation: string | null;
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

async function get<T>(path: string, query: Record<string, string | number | undefined> = {}): Promise<T> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== "") params.set(k, String(v));
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

export const fetchFlexOutcome = (input: FlexInput) =>
  get<FlexOutcome>("insights/flex-outcome", input as unknown as Record<string, string | number>);

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
