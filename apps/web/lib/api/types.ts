export interface SystemHealth {
  status: "ok" | "degraded" | "down";
  version: string;
  uptime: number;
  services: {
    [key: string]: {
      status: "up" | "down" | "degraded" | "unknown" | "disabled";
      latency_ms?: number;
      message?: string;
      version?: string;
      queue_depth?: number;
    };
  };
  metrics: {
    cache_hit_rate?: number;
    active_requests?: number;
    build_id?: string;
    release_id?: string;
  };
}

export interface ChatRequest {
  query: string;
  conversation_id?: string;
  filters?: { domain?: string[]; source_priority?: string[] };
  requested_model?: string;
  memory_scope?: string;
}

export interface ChatResponse {
  request_id: string;
  answer: string;
  sources: {
    evidence_id: string;
    document_id: string;
    title: string;
    location: string;
    url?: string;
  }[];
  memory_used: boolean;
  cache_hit: boolean;
  model: { provider: string; name: string; version: string };
  knowledge_version: string;
  warnings: string[];
}

export interface SearchResponse {
  request_id: string;
  retrieval: { mode: string; corpus_version: string };
  pagination: { page: number; total_items: number; total_pages: number };
  results: SearchResult[];
}

export interface SearchResult {
  result_id: string;
  result_type: "document" | "experiment" | "entity";
  score: number;
  title: string;
  snippet: string;
  evidence_id?: string;
  source: {
    repository: string;
    source_id: string;
    access_url?: string;
    short_name?: string;
  };
  locator?: { label: string; page?: string; section?: string };
}

// Enums copied from docs/api/openapi.json (contract 0.7.0). Keep them in step with the contract.
export const REVIEW_STATUSES = ["raw", "machine_extracted", "human_verified", "rejected"] as const;
export type ReviewStatus = (typeof REVIEW_STATUSES)[number];

export const ANALYSIS_STATUSES = ["queued", "processing", "completed", "failed", "cancelled"] as const;
export type AnalysisStatus = (typeof ANALYSIS_STATUSES)[number];

export interface EvidenceRecord {
  id: string;
  // EvidenceKind in the contract: document_passage, experiment_condition, dataset_file, image_measurement, video_measurement.
  kind: string;
  citation: string;
  extraction_method: string;
  transformation_id: string;
  review_status: ReviewStatus;
  excerpt?: string;
  value?: { text: string; unit: string };
  measurement_or_claim_type?: string;
  locator?: { type: string; label: string; section?: string };
  file?: { sha256: string; original_filename: string; size_bytes: number };
  source?: { repository: string; source_id: string; access_url: string };
}

export interface AnalysisResult {
  id: string;
  status: AnalysisStatus;
  failure_message?: string;
  image_id: string;
  pipeline_version: string;
  model_version: string;
  preprocessing_version: string;
  calibration_state: string;
  masks: { label: string; uri: string; checksum: string }[];
  measurements: {
    name: string;
    value: number;
    unit: string;
    confidence?: number;
    observation_type: "observed" | "measured" | "estimated" | "inferred" | "hypothesized";
  }[];
  warnings: string[];
  created_at: string;
}

export interface KnowledgeEntity {
  id: string;
  type: string;
  label: string;
  aliases: string[];
  definition: string;
  status: "verified" | "unverified";
  relations: {
    predicate: string;
    target_id: string;
    target_label: string;
    confidence: number;
    evidence_ids: string[];
  }[];
}

// A panel whose data has no API source yet is `null`: render "not available yet", never an empty list
// that reads as a measurement of zero.
export interface DashboardData {
  corpus_status: { total_documents: number; total_chunks: number; indexed_chunks: number; version: string };
  recent_research: { query: string; timestamp: string }[] | null;
  source_coverage: { source: string; percentage: number }[] | null;
  evaluation_snapshot: { metric: string; value: number; threshold: number }[] | null;
  ingestion_alerts: { id: string; message: string; severity: "info" | "warning" | "error" }[] | null;
}

export interface AnalysisSummary {
  analysis_id: string;
  analysis_type?: "flame_image" | "flame_video";
  original_filename: string;
  status: AnalysisStatus;
  flame_area_px?: number;
  calibration_state: string;
  created_at: string;
}

export interface ExperimentRecord {
  experiment_id: string;
  name: string;
  objective: string;
  platform: string;
  gravity_regime: string;
  conditions: {
    variable: string;
    value: number;
    unit: string;
    method: string;
  }[];
}
