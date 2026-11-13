// Knowledge-graph client (contract 0.7.0, tag "Knowledge graph", ADR-007). Read-only, through the
// same-origin proxy (app/api/[...path]). The graph holds what NASA's PSI tables and ISA-Tab records
// state; every edge carries the evidence ID of the cell it was read from.
import { get } from "./fireSafety";

// platform/instrument and ran_on/measured_with come from the NLP graph (D1, roadmap 15); the contract has had them since
// 0.6.0. Every type the API can return must be listed here, or the Knowledge Graph page cannot label it.
export type GraphEntityType = "investigation" | "experiment" | "fuel" | "condition_variable" | "phenomenon" | "document"
  | "platform" | "instrument";
export type GraphPredicate = "part_of" | "uses_fuel" | "has_condition" | "observed" | "describes" | "ran_on" | "measured_with";
export type GraphReviewStatus = "unreviewed" | "human_verified" | "rejected";

export interface GraphEntity {
  entity_id: string;
  entity_type: GraphEntityType;
  canonical_name: string;
  display_name: string;
  aliases: string[];
  properties: Record<string, unknown>;
  source_id: string | null;
  evidence_ids: string[];
  review_status: GraphReviewStatus;
  merged_into: string | null;
  knowledge_version: string | null;
  depth?: number;
  relation_count?: number;
}

export interface GraphEdge {
  relation_id: string;
  subject_id: string;
  predicate: GraphPredicate;
  object_id: string;
  evidence_id: string | null;
  extraction_method: "table_parse" | "nlp_extraction" | "manual";
  extractor_version: string | null;
  confidence: number | null;
  review_status: GraphReviewStatus;
  properties: Record<string, unknown>;
}

export interface GraphEntityList {
  items: GraphEntity[];
  pagination: { page: number; page_size: number; total_items: number; total_pages: number };
}

export interface GraphEntityDetail {
  entity: GraphEntity;
  resolved_from: string | null;
  neighbourhood: {
    depth: number;
    predicates: GraphPredicate[];
    entities: GraphEntity[];
    edges: GraphEdge[];
    truncated: boolean;
    reachable_entities: number;
    reachable_by_type: Partial<Record<GraphEntityType, number>>;
  };
}

export const ENTITY_TYPES: { value: GraphEntityType; label: string }[] = [
  { value: "investigation", label: "Investigations" },
  { value: "phenomenon", label: "Outcomes" },
  { value: "fuel", label: "Fuels & materials" },
  { value: "condition_variable", label: "Conditions" },
  { value: "document", label: "NASA records" },
  { value: "experiment", label: "Flight tests" },
  { value: "platform", label: "Platforms" },
  { value: "instrument", label: "Instruments" },
];

export const TYPE_LABEL: Record<GraphEntityType, string> = {
  investigation: "Investigation", experiment: "Flight test", fuel: "Fuel / material",
  condition_variable: "Condition", phenomenon: "Outcome", document: "NASA record", platform: "Platform", instrument: "Instrument",
};

// How an edge reads from its subject to its object.
export const PREDICATE_LABEL: Record<GraphPredicate, string> = {
  part_of: "is part of", uses_fuel: "burned", has_condition: "recorded", observed: "ended in", describes: "describes",
  ran_on: "ran on", measured_with: "measured with",
};

export const ALL_PREDICATES: GraphPredicate[] = ["part_of", "uses_fuel", "has_condition", "observed", "describes", "ran_on", "measured_with"];

export function listEntities(query: { type?: GraphEntityType; q?: string; page?: number; page_size?: number }) {
  return get<GraphEntityList>("graph/entities", query);
}

export function getEntity(entityId: string, query: { depth?: number; predicate?: GraphPredicate[]; max_edges?: number } = {}) {
  return get<GraphEntityDetail>(`graph/entities/${encodeURIComponent(entityId)}`, query);
}

/** A flight test's display name is its ULID; show the investigation and test ID instead. */
export function entityLabel(entity: GraphEntity): string {
  if (entity.entity_type === "experiment") {
    const p = entity.properties as { investigation?: string; test_id?: string };
    if (p.investigation || p.test_id) return `${p.investigation ?? "Test"} ${p.test_id ?? ""}`.trim();
  }
  if (entity.entity_type === "document") {
    const title = (entity.properties as { title?: string }).title;
    if (title) return title;
  }
  return entity.display_name;
}

/** The value an edge carries (has_condition), as the table recorded it, SI first. */
export function edgeValue(edge: GraphEdge): string | null {
  if (edge.predicate !== "has_condition") return null;
  const p = edge.properties as { value_si?: number | null; unit_si?: string | null; value_text?: string | null;
                                 value_numeric?: number | null; unit_original?: string | null };
  if (p.value_si !== null && p.value_si !== undefined) return `${formatNumber(p.value_si)}${p.unit_si ? ` ${p.unit_si}` : ""}`;
  if (p.value_numeric !== null && p.value_numeric !== undefined)
    return `${formatNumber(p.value_numeric)}${p.unit_original ? ` ${p.unit_original}` : ""}`;
  if (p.value_text) return p.value_text;
  return null;
}

function formatNumber(value: number): string {
  if (value !== 0 && (Math.abs(value) < 1e-3 || Math.abs(value) >= 1e6)) return value.toExponential(3);
  return String(Number(value.toPrecision(6)));
}
