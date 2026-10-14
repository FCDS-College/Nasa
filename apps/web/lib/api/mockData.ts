import { SystemHealth, ChatResponse, SearchResponse, EvidenceRecord, AnalysisResult, KnowledgeEntity, DashboardData, AnalysisSummary, ExperimentRecord, DocumentRecord } from "./types";

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
  corpus_status: { total_documents: 14502, indexed_chunks: 1250394, version: "2026-10-03" },
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

export const mockChatResponse: ChatResponse = {
  request_id: "req_123456",
  answer: "In microgravity, buoyancy-induced convection is nearly eliminated. This causes flames to become spherical and soot residence times to increase significantly, altering soot formation pathways and radiative heat loss. The CLD Flame experiment observed larger primary soot particles compared to 1g conditions.",
  sources: [
    { evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5", document_id: "doc_991", title: "Soot Formation in Microgravity", location: "p. 4, §2.1", url: "https://ntrs.nasa.gov/" }
  ],
  memory_used: true,
  cache_hit: false,
  model: { provider: "vllm", name: "Llama-3-8B-Instruct", version: "v1.0" },
  knowledge_version: "2026-10-03",
  warnings: []
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
    kind: "observed",
    citation: "Urban, D. L. et al. (2015). NASA NTRS",
    extraction_method: "semantic_chunking_v2",
    transformation_id: "tx_9921",
    review_status: "verified",
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

export const mockDocuments: DocumentRecord[] = [
  {
    document_id: "01J9Z3M2A7D4F6H8K0N2Q4S6T8",
    title: "Testing and Selection of Fire-Resistant Materials for Spacecraft Use",
    document_type: "technical_report",
    identifier: "NASA/TM-2000-209773",
    persistent_identifier: "https://ntrs.nasa.gov/citations/20000034017",
    source: {
      source_id: "FF-NTRS-20000034017",
      title: "Testing and Selection of Fire-Resistant Materials for Spacecraft Use",
      short_name: "NASA/TM-2000-209773",
      repository: "NASA NTRS",
      access_url: "https://ntrs.nasa.gov/citations/20000034017",
    },
    file: {
      file_id: "sha256:dc531270ffb646b2",
      sha256: "dc531270ffb646b26503955afb0c1df7bcc47482bbfed4a3d6b922de9629520d",
      original_filename: "20000034017.pdf",
      media_type: "application/pdf",
      size_bytes: 1297410,
      canonical_source_url: "https://ntrs.nasa.gov/api/citations/20000034017/downloads/20000034017.pdf",
    },
    page_count: 24,
    text_layer: "full",
    pages_without_text: [],
    evidence_count: 14,
    ingested_at: "2026-10-05T08:00:00Z",
    summary: "Investigation of flammability and fire-spread characteristics of selected spacecraft materials under microgravity and normal gravity conditions, focusing on convective flow rates and ambient oxygen concentration."
  },
  {
    document_id: "01J9Z3M3B8E5G7J9L1N3R5S7U9",
    title: "Microgravity Combustion Research: 2004 Program Overview",
    document_type: "publication",
    identifier: "NASA/TM-2004-213348",
    persistent_identifier: "https://ntrs.nasa.gov/citations/20040053557",
    source: {
      source_id: "FF-NTRS-20040053557",
      title: "Microgravity Combustion Research: 2004 Program Overview",
      short_name: "NASA/TM-2004-213348",
      repository: "NASA NTRS",
      access_url: "https://ntrs.nasa.gov/citations/20040053557",
    },
    file: {
      file_id: "sha256:88941f1737e3d1ac",
      sha256: "88941f1737e3d1acb7cbe3233860bb4a66a1a441dfdf5fa71295fc7469a9b3a7",
      original_filename: "20040053557.pdf",
      media_type: "application/pdf",
      size_bytes: 3418290,
      canonical_source_url: "https://ntrs.nasa.gov/api/citations/20040053557/downloads/20040053557.pdf",
    },
    page_count: 58,
    text_layer: "full",
    pages_without_text: [],
    evidence_count: 28,
    ingested_at: "2026-10-05T08:15:00Z",
    summary: "Comprehensive synthesis of laminar diffusion flame behavior, droplet combustion, soot formation mechanisms, and spacecraft fire safety research conducted aboard drop towers and the ISS."
  },
  {
    document_id: "01J9Z3M4C9F6H8K0M2P4T6V8W0",
    title: "Flammability Assessment of Materials in Microgravity and Low-Gravity Regimes",
    document_type: "technical_report",
    identifier: "NASA/TP-2008-215092",
    persistent_identifier: "https://ntrs.nasa.gov/citations/20080034883",
    source: {
      source_id: "FF-NTRS-20080034883",
      title: "Flammability Assessment of Materials in Microgravity and Low-Gravity Regimes",
      short_name: "NASA/TP-2008-215092",
      repository: "NASA NTRS",
      access_url: "https://ntrs.nasa.gov/citations/20080034883",
    },
    file: {
      file_id: "sha256:1a58c823098f921d",
      sha256: "1a58c823098f921da8c4e09f8742b781a8b7921a86b97607a8ffbd25e839e09d",
      original_filename: "20080034883.pdf",
      media_type: "application/pdf",
      size_bytes: 2189400,
      canonical_source_url: "https://ntrs.nasa.gov/api/citations/20080034883/downloads/20080034883.pdf",
    },
    page_count: 36,
    text_layer: "partial",
    pages_without_text: [14, 15],
    evidence_count: 9,
    ingested_at: "2026-10-05T08:30:00Z",
    summary: "Experimental results and comparative flammability thresholds across terrestrial 1g, lunar 0.16g, Martian 0.38g, and ISS microgravity environments. Pages 14-15 contain scanned test figures pending OCR."
  }
];
