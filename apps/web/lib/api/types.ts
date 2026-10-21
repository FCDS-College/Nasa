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

export interface EvidenceRecord {
  id: string;
  kind: "observed" | "measured" | "estimated" | "inferred" | "hypothesized";
  citation: string;
  extraction_method: string;
  transformation_id: string;
  review_status: "verified" | "pending" | "rejected";
  excerpt?: string;
  value?: { text: string; unit: string };
  measurement_or_claim_type?: string;
  locator?: { type: string; label: string; section?: string };
  file?: { sha256: string; original_filename: string; size_bytes: number };
  source?: { repository: string; source_id: string; access_url: string };
}

export interface AnalysisResult {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
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
  imageUrl?: string;
  overlayUrl?: string;
  filename?: string;
}

export interface DocumentRecord {
  document_id: string;
  title: string;
  document_type: string;
  identifier: string | null;
  persistent_identifier?: string | null;
  source: {
    source_id: string;
    title: string;
    short_name?: string;
    repository: string;
    access_url?: string;
  };
  file?: {
    file_id: string;
    sha256: string;
    original_filename: string;
    media_type: string;
    size_bytes: number;
    canonical_source_url?: string | null;
  };
  page_count?: number | null;
  text_layer?: "full" | "partial" | "none" | "unknown";
  pages_without_text?: number[];
  evidence_count?: number;
  ingested_at?: string;
  summary?: string;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
  request_id?: string;
  retryable?: boolean;
  field_errors?: { field: string; message: string }[];
  details?: Record<string, unknown>;
}

export interface AnalysisCreateForm {
  image: File;
  experiment_id?: string;
  scale_px_per_mm?: number;
  scale_source?: string;
  request_interpretation?: boolean;
  notes?: string;
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

export interface DashboardData {
  corpus_status: { total_documents: number; indexed_chunks: number; version: string };
  recent_research: { query: string; timestamp: string }[];
  source_coverage: { source: string; percentage: number }[];
  evaluation_snapshot: { metric: string; value: number; threshold: number }[];
  ingestion_alerts: { id: string; message: string; severity: "info" | "warning" | "error" }[];
}

export interface AnalysisSummary {
  analysis_id: string;
  original_filename: string;
  status: "completed" | "processing" | "failed";
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
