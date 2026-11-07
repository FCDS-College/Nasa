import {
  SystemHealth,
  ChatResponse,
  ChatRequest,
  SearchResponse,
  EvidenceRecord,
  AnalysisResult,
  KnowledgeEntity,
  DashboardData,
  AnalysisSummary,
  ExperimentRecord,
} from "./types";

// Every call goes through the same-origin /api proxy (app/api/[...path]), which
// holds the Flame API read token server-side.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

async function getJson(path: string): Promise<Json> {
  const res = await fetch(`${API_BASE}/api/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export function artifactUrl(analysisId: string, kind: "original" | "overlay" | "mask"): string {
  return `${API_BASE}/api/analyses/${analysisId}/artifacts/${kind}`;
}

export async function fetchHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
    // 503 still carries a full health body describing what is down.
    const body: Json = await res.json();
    const services: SystemHealth["services"] = {};
    for (const [name, s] of Object.entries<Json>(body.services ?? {})) {
      services[name] = {
        status: s.status,
        latency_ms: s.latency_ms ?? undefined,
        message: s.message ?? undefined,
        version: s.version ?? undefined,
      };
    }
    return {
      status: body.status === "healthy" ? "ok" : body.status === "unhealthy" ? "down" : "degraded",
      version: body.version?.api_version ?? "unknown",
      uptime: 0,
      services,
      metrics: { build_id: body.version?.build_id ?? undefined, release_id: body.version?.git_sha ?? undefined },
    };
  } catch {
    return { status: "down", version: "unknown", uptime: 0, services: { api: { status: "down", message: "Flame API is unreachable." } }, metrics: {} };
  }
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const counts = await getJson("dashboard/counts");
  return {
    corpus_status: {
      total_documents: counts.documents,
      total_chunks: counts.chunks,
      indexed_chunks: counts.indexed_chunks,
      version: counts.knowledge_version ?? "unversioned",
    },
    // No API serves these yet (query history, per-source coverage, evaluation runs, ingestion alerts).
    recent_research: null,
    source_coverage: null,
    evaluation_snapshot: null,
    ingestion_alerts: null,
  };
}

// Flame retrieves its own evidence and has AURA's model write the answer from it.
export async function submitChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: req.query, conversation_id: req.conversation_id }),
    cache: "no-store",
  });
  const body: Json = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(body?.error?.message ?? `Chat failed (${res.status})`);
    error.name = body?.error?.code ?? "CHAT_FAILED";
    throw error;
  }
  return body as ChatResponse;
}

export async function searchResearch(query: string, filters?: Record<string, unknown>): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query.trim(), domain: String(filters?.domain ?? "combustion") });
  const body = await getJson(`search?${params}`);
  return {
    request_id: body.meta?.request_id ?? "",
    retrieval: { mode: body.retrieval?.mode ?? "lexical", corpus_version: body.retrieval?.knowledge_version ?? "unversioned" },
    pagination: body.pagination,
    results: body.results.map((r: Json) => ({
      result_id: r.result_id,
      result_type: r.result_type,
      score: r.score,
      title: r.title,
      snippet: r.snippet,
      evidence_id: r.evidence_id ?? undefined,
      source: {
        repository: r.source?.repository,
        source_id: r.source?.source_id,
        access_url: r.source?.access_url ?? undefined,
        short_name: r.source?.short_name ?? undefined,
      },
      locator: r.locator ? { label: r.locator.label, page: r.locator.page ?? undefined, section: r.locator.section ?? undefined } : undefined,
    })),
  };
}

export async function fetchEvidence(id: string): Promise<EvidenceRecord | null> {
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;
  try {
    const { evidence: e } = await getJson(`evidence/${id}`);
    return {
      id: e.evidence_id,
      kind: e.kind,
      citation: e.source?.short_name || e.source?.title || e.source?.repository || "Unknown source",
      extraction_method: e.origin ?? "unknown",
      transformation_id: e.transformation_id ?? e.file?.file_id ?? "—",
      review_status: e.review_status ?? "pending",
      excerpt: e.excerpt ?? undefined,
      value: e.value?.numeric != null || e.value?.text ? { text: String(e.value.numeric ?? e.value.text), unit: e.value.unit ?? "" } : undefined,
      measurement_or_claim_type: e.measurement_or_claim_type ?? undefined,
      locator: e.locator ? { type: e.locator.type, label: e.locator.label, section: e.locator.section ?? undefined } : undefined,
      file: e.file ? { sha256: e.file.sha256, original_filename: e.file.original_filename, size_bytes: e.file.size_bytes } : undefined,
      source: e.source ? { repository: e.source.repository, source_id: e.source.source_id, access_url: e.source.access_url } : undefined,
    };
  } catch {
    return null;
  }
}

const MEASUREMENT_LABELS: Record<string, string> = {
  area: "Area", width: "Width", height: "Height", perimeter: "Perimeter",
  aspect_ratio: "Aspect ratio", circularity: "Circularity",
  mean_r: "Mean red", mean_g: "Mean green", mean_b: "Mean blue",
  mean_intensity: "Mean intensity", saturated_fraction: "Saturated fraction",
};

function flattenMeasurements(measurements: Json): AnalysisResult["measurements"] {
  const out: AnalysisResult["measurements"] = [];
  for (const [group, suffix] of [["geometry_px", " (px)"], ["geometry_physical", " (scaled)"], ["appearance", ""]] as const) {
    for (const [key, m] of Object.entries<Json>(measurements?.[group] ?? {})) {
      if (!m || typeof m !== "object" || typeof m.value !== "number") continue;
      out.push({ name: (MEASUREMENT_LABELS[key] ?? key) + suffix, value: m.value, unit: m.unit, observation_type: m.classification ?? "measured" });
    }
  }
  return out;
}

export async function fetchAnalysis(id?: string): Promise<AnalysisResult | null> {
  try {
    let analysisId = id;
    if (!analysisId) {
      // The studio renders image overlays, so pick the newest completed image analysis (videos are flame_video).
      const list = await getJson("analyses?status=completed&page_size=20");
      analysisId = list.items?.find((i: Json) => (i.analysis_type ?? "flame_image") === "flame_image")?.analysis_id;
      if (!analysisId) return null;
    }
    const { analysis: a } = await getJson(`analyses/${analysisId}`);
    return {
      id: a.analysis_id,
      status: a.status === "completed" ? "completed" : a.status === "failed" ? "failed" : "pending",
      image_id: a.input?.original_filename ?? a.analysis_id,
      pipeline_version: a.pipeline?.pipeline_version ?? "—",
      model_version: a.pipeline?.detector ? `${a.pipeline.detector.name} ${a.pipeline.detector.version}` : "—",
      preprocessing_version: a.pipeline?.preprocessing_version ?? "—",
      calibration_state: a.input?.calibration?.state ?? "absent",
      masks: [],
      measurements: flattenMeasurements(a.result?.measurements),
      warnings: (a.warnings ?? []).map((w: Json) => w.message),
      created_at: a.created_at,
    };
  } catch {
    return null;
  }
}

// The Flame API exposes no knowledge graph yet (docs/ai/graph-rag.md: Planned). Return nothing rather
// than sample entities, so the page never shows invented "verified" relations or citations.
export async function fetchKnowledge(): Promise<KnowledgeEntity[]> {
  return [];
}

export async function fetchAnalysesHistory(): Promise<AnalysisSummary[]> {
  try {
    const body = await getJson("analyses?page_size=50");
    return body.items.map((i: Json) => ({
      analysis_id: i.analysis_id,
      analysis_type: i.analysis_type ?? "flame_image",
      original_filename: i.original_filename,
      status: i.status === "completed" || i.status === "failed" ? i.status : "processing",
      flame_area_px: i.flame_area_px ?? undefined,
      calibration_state: i.calibration_state,
      created_at: i.created_at,
    }));
  } catch {
    return [];
  }
}

export async function fetchExperiments(): Promise<ExperimentRecord[]> {
  try {
    const search = await getJson("search?q=flame&type=experiment&domain=all&page_size=20");
    const ids: string[] = search.results.map((r: Json) => r.experiment_id).filter(Boolean);
    const details = await Promise.all(ids.map((id) => getJson(`experiments/${id}`)));
    return details.map(({ experiment: e }) => ({
      experiment_id: e.experiment_id,
      name: `${e.investigation ?? "Experiment"} ${e.test_id}`,
      objective: e.fuel_or_material ?? "—",
      platform: e.source?.short_name ?? e.source?.repository ?? "—",
      gravity_regime: e.gravity_regime ?? "unknown",
      conditions: (e.conditions ?? [])
        .filter((c: Json) => c.value_numeric != null)
        .map((c: Json) => ({ variable: c.variable, value: c.value_numeric, unit: c.unit_original ?? "", method: c.origin ?? "" })),
    }));
  } catch {
    return [];
  }
}
