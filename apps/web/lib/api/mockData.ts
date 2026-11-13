import { SystemHealth, SearchResponse, EvidenceRecord, AnalysisResult, KnowledgeEntity, DashboardData, AnalysisSummary, ExperimentRecord } from "./types";

export const mockHealth: SystemHealth = {
  status: "ok",
  version: "1.0.0-MVP",
  uptime: 128450,
  services: {
    api: { status: "up", latency_ms: 12, version: "v1.0" },
    database: { status: "up", latency_ms: 5, queue_depth: 0 },
    vector_index: { status: "up", latency_ms: 18, version: "pgvector 0.5.1" },
    object_storage: { status: "up", latency_ms: 8 },
    cache: { status: "up", latency_ms: 2, version: "Redis 7.0" },
    cv_model: { status: "up", latency_ms: 150, version: "YOLOv8-Flame" },
    llm: { status: "up", latency_ms: 320, version: "vLLM-L40S" },
  },
  metrics: {
    cache_hit_rate: 0.84,
    active_requests: 12,
    build_id: "build-7f8a9b",
    release_id: "rel-MVP.1",
  }
};

export const mockDashboard: DashboardData = {
  corpus_status: { total_documents: 14502, total_chunks: 1250394, indexed_chunks: 1250394, version: "2026-10-03" },
  recent_research: [
    { query: "How does microgravity alter soot formation?", timestamp: "2 mins ago" },
    { query: "BASS-II fuel geometries", timestamp: "1 hour ago" },
  ],
  source_coverage: [
    { source: "NASA NTRS", percentage: 65 },
    { source: "NIST WebBook", percentage: 20 },
    { source: "Other Publ.", percentage: 15 },
  ],
  evaluation_snapshot: [
    { metric: "RAG Recall@5", value: 0.92, threshold: 0.85 },
    { metric: "CV IoU", value: 0.88, threshold: 0.80 },
    { metric: "Factuality", value: 0.96, threshold: 0.95 },
  ],
  ingestion_alerts: [
    { id: "A1", message: "NIST rate limit reached, retrying in 10m", severity: "warning" },
  ]
};

export const mockSearchResults: SearchResponse = {
  request_id: "sr_9911",
  retrieval: { mode: "hybrid", corpus_version: "2026-10-03" },
  pagination: { page: 1, total_items: 24, total_pages: 3 },
  results: [
    {
      result_id: "res_1",
      result_type: "document",
      score: 0.94,
      title: "Structure and Soot Properties of Laminar Jet Nonpremixed Flames",
      snippet: "Under microgravity conditions, the lack of buoyant acceleration leads to wider flames, lower strain rates, and consequently, enhanced soot volume fractions in the flame region...",
      evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
      source: { repository: "NTRS", source_id: "NTRS-20150001", short_name: "NASA GLENN" },
      locator: { label: "Page 12, Figure 4" }
    }
  ]
};

export const mockEvidence: Record<string, EvidenceRecord> = {
  "01J9Z3N5B8C1E3G5J7M9P1R3T5": {
    id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
    kind: "document_passage",
    citation: "Urban, D. L. et al. (2015). NASA NTRS",
    extraction_method: "semantic_chunking_v2",
    transformation_id: "tx_9921",
    review_status: "human_verified",
    excerpt: "Under microgravity conditions, the lack of buoyant acceleration leads to wider flames, lower strain rates, and consequently, enhanced soot volume fractions in the flame region.",
    locator: { type: "pdf_page", label: "Page 12", section: "2.1 Microgravity Effects" },
    file: { sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", original_filename: "ntrs-20150001.pdf", size_bytes: 4192000 },
    source: { repository: "NTRS", source_id: "NTRS-20150001", access_url: "https://ntrs.nasa.gov/" }
  }
};

export const mockAnalysis: AnalysisResult = {
  id: "job_8829",
  status: "completed",
  image_id: "img_99112",
  pipeline_version: "1.2.0",
  model_version: "YOLOv8-Flame-v1.1",
  preprocessing_version: "v2-color-norm",
  calibration_state: "uncalibrated",
  masks: [
    { label: "flame_boundary", uri: "/assets/masks/mask_99112.png", checksum: "8f7d..." }
  ],
  measurements: [
    { name: "Projected Area", value: 14082, unit: "pixels", confidence: 0.95, observation_type: "measured" },
    { name: "Circularity", value: 0.88, unit: "ratio", confidence: 0.92, observation_type: "measured" },
    { name: "Estimated Temperature", value: 1800, unit: "K", confidence: 0.45, observation_type: "estimated" }
  ],
  warnings: ["Missing physical calibration; temperature is estimated from RGB statistics.", "No scale reference found."],
  created_at: new Date().toISOString()
};

export const mockKnowledge: KnowledgeEntity[] = [
  {
    id: "ent_flame",
    type: "phenomenon",
    label: "Microgravity Spherical Flame",
    aliases: ["zero-g flame", "diffusion spherical flame"],
    definition: "A diffusion flame in a microgravity environment where buoyancy-induced convection is negligible, leading to spherical symmetry.",
    status: "verified",
    relations: [
      { predicate: "observed_in", target_id: "exp_bass2", target_label: "BASS-II", confidence: 0.98, evidence_ids: ["01J9Z3N5B8C1E3G5J7M9P1R3T5"] }
    ]
  }
];

export const mockHistory: AnalysisSummary[] = [
  {
    analysis_id: "job_8829",
    original_filename: "bass2_flame_frame001.jpg",
    status: "completed",
    flame_area_px: 14082,
    calibration_state: "uncalibrated",
    created_at: new Date().toISOString()
  }
];

export const mockExperiments: ExperimentRecord[] = [
  {
    experiment_id: "exp_bass2",
    name: "BASS-II",
    objective: "Burning and Suppression of Solids - II",
    platform: "ISS Microgravity Science Glovebox",
    gravity_regime: "microgravity",
    conditions: [
      { variable: "Oxygen Concentration", value: 21, unit: "%", method: "flow controller" },
      { variable: "Pressure", value: 1, unit: "atm", method: "cabin ambient" },
      { variable: "Flow Velocity", value: 5, unit: "cm/s", method: "anemometer" }
    ]
  }
];
