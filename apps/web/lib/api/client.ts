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
  DocumentRecord,
  ApiErrorDetail,
} from "./types";

// Every browser call goes through the same-origin /api proxy (app/api/[...path]),
// which holds the Flame API read token server-side.
// The browser communicates with same-origin /api/... only.
const API_BASE = "";

type Json = Record<string, any>; // eslint-disable-line @typescript-eslint/no-explicit-any

async function getJson(path: string): Promise<Json> {
  const res = await fetch(`${API_BASE}/api/${path}`, { cache: "no-store" });
  if (!res.ok) {
    let errCode = "UPSTREAM_UNAVAILABLE";
    let message = `API request failed with status ${res.status}`;
    try {
      const errBody = await res.json();
      if (errBody?.error?.code) errCode = errBody.error.code;
      if (errBody?.error?.message) message = errBody.error.message;
    } catch {
      // ignore json parse error
    }
    const error: Error & { code?: string; status?: number } = new Error(message);
    error.code = errCode;
    error.status = res.status;
    throw error;
  }
  return res.json();
}

export function artifactUrl(analysisId: string, kind: "original" | "preprocessed" | "overlay" | "mask"): string {
  return `${API_BASE}/api/analyses/${analysisId}/artifacts/${kind}`;
}

export async function fetchHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { cache: "no-store" });
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
      metrics: {
        build_id: body.version?.build_id ?? undefined,
        release_id: body.version?.git_sha ?? undefined,
      },
    };
  } catch {
    return {
      status: "down",
      version: "unknown",
      uptime: 0,
      services: {
        api: { status: "down", message: "Flame API is unreachable." },
      },
      metrics: {},
    };
  }
}

export async function fetchDashboardData(): Promise<DashboardData> {
  const counts = await getJson("dashboard/counts");
  return {
    corpus_status: {
      total_documents: counts.documents ?? 0,
      indexed_chunks: counts.chunks ?? 0,
      version: counts.knowledge_version ?? "unversioned",
    },
    recent_research: [],
    source_coverage: [],
    evaluation_snapshot: [],
    ingestion_alerts: [],
  };
}

export async function submitChat(req: ChatRequest): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      query: req.query,
      conversation_id: req.conversation_id,
      filters: req.filters,
      requested_model: req.requested_model,
      memory_scope: req.memory_scope,
    }),
    cache: "no-store",
  });

  if (!res.ok) {
    let errCode = "UPSTREAM_UNAVAILABLE";
    let message = "Chat request could not be completed.";
    try {
      const errJson = await res.json();
      if (errJson?.error?.code) errCode = errJson.error.code;
      if (errJson?.error?.message) message = errJson.error.message;
    } catch {
      // response not JSON
    }
    const err: Error & { code?: string; status?: number } = new Error(message);
    err.code = errCode;
    err.status = res.status;
    throw err;
  }

  const data = await res.json();
  return {
    request_id: data.meta?.request_id ?? data.request_id ?? "",
    answer: data.answer ?? data.response ?? "",
    sources: data.sources ?? [],
    memory_used: data.memory_used ?? false,
    cache_hit: data.cache_hit ?? false,
    model: data.model ?? { provider: "AURA", name: "aura-reasoner", version: "3.0" },
    knowledge_version: data.knowledge_version ?? "unversioned",
    warnings: data.warnings ?? [],
  };
}

export async function searchResearch(query: string, filters?: Record<string, unknown>): Promise<SearchResponse> {
  const params = new URLSearchParams({
    q: query.trim(),
    domain: String(filters?.domain ?? "combustion"),
  });
  if (filters?.type) params.set("type", String(filters.type));
  if (filters?.page) params.set("page", String(filters.page));
  if (filters?.page_size) params.set("page_size", String(filters.page_size));

  const body = await getJson(`search?${params}`);
  return {
    request_id: body.meta?.request_id ?? "",
    retrieval: {
      mode: body.retrieval?.mode ?? "hybrid",
      corpus_version: body.retrieval?.knowledge_version ?? "unversioned",
    },
    pagination: body.pagination ?? { page: 1, total_items: 0, total_pages: 0 },
    results: (body.results ?? []).map((r: Json) => ({
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
      locator: r.locator
        ? { label: r.locator.label, page: r.locator.page ?? undefined, section: r.locator.section ?? undefined }
        : undefined,
    })),
  };
}

export async function fetchEvidence(id: string): Promise<EvidenceRecord | null> {
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;
  try {
    const { evidence: e } = await getJson(`evidence/${id}`);
    if (!e) return null;
    return {
      id: e.evidence_id,
      kind: e.kind,
      citation: e.source?.short_name || e.source?.title || e.source?.repository || "Unknown source",
      extraction_method: e.origin ?? "unknown",
      transformation_id: e.transformation_id ?? e.file?.file_id ?? "—",
      review_status: e.review_status ?? "verified",
      excerpt: e.excerpt ?? undefined,
      value:
        e.value?.numeric != null || e.value?.text
          ? { text: String(e.value.numeric ?? e.value.text), unit: e.value.unit ?? "" }
          : undefined,
      measurement_or_claim_type: e.measurement_or_claim_type ?? undefined,
      locator: e.locator ? { type: e.locator.type, label: e.locator.label, section: e.locator.section ?? undefined } : undefined,
      file: e.file
        ? { sha256: e.file.sha256, original_filename: e.file.original_filename, size_bytes: e.file.size_bytes }
        : undefined,
      source: e.source
        ? { repository: e.source.repository, source_id: e.source.source_id, access_url: e.source.access_url }
        : undefined,
    };
  } catch {
    return null;
  }
}

export async function fetchDocument(id: string): Promise<DocumentRecord | null> {
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;
  try {
    const data = await getJson(`documents/${id}`);
    const doc = data.document || data;
    if (!doc) return null;
    return {
      document_id: doc.document_id,
      title: doc.title,
      document_type: doc.document_type ?? "report",
      identifier: doc.identifier ?? null,
      persistent_identifier: doc.persistent_identifier ?? null,
      source: {
        source_id: doc.source?.source_id ?? "",
        title: doc.source?.title ?? "",
        short_name: doc.source?.short_name ?? undefined,
        repository: doc.source?.repository ?? "",
        access_url: doc.source?.access_url ?? undefined,
      },
      file: doc.file
        ? {
            file_id: doc.file.file_id ?? "",
            sha256: doc.file.sha256 ?? "",
            original_filename: doc.file.original_filename ?? "",
            media_type: doc.file.media_type ?? "application/pdf",
            size_bytes: doc.file.size_bytes ?? 0,
            canonical_source_url: doc.file.canonical_source_url ?? null,
          }
        : undefined,
      page_count: doc.page_count ?? null,
      text_layer: doc.text_layer ?? "unknown",
      pages_without_text: doc.pages_without_text ?? [],
      evidence_count: doc.evidence_count ?? (doc.chunks ? doc.chunks.length : 0),
      ingested_at: doc.ingested_at ?? undefined,
      summary: doc.summary ?? undefined,
    };
  } catch {
    return null;
  }
}

export async function fetchDocuments(): Promise<DocumentRecord[]> {
  try {
    const search = await getJson("search?type=document&domain=all&page_size=50");
    const results = search.results || [];
    return results.map((r: Json) => ({
      document_id: r.result_id,
      title: r.title,
      document_type: "paper",
      identifier: r.result_id,
      source: {
        source_id: r.source?.source_id ?? "",
        title: r.source?.short_name ?? r.source?.repository ?? "NASA",
        short_name: r.source?.short_name,
        repository: r.source?.repository ?? "NASA PSI",
        access_url: r.source?.access_url,
      },
      page_count: null,
      text_layer: "full",
      summary: r.snippet,
    }));
  } catch {
    return [];
  }
}

const MEASUREMENT_LABELS: Record<string, string> = {
  area: "Area",
  width: "Width",
  height: "Height",
  perimeter: "Perimeter",
  aspect_ratio: "Aspect ratio",
  circularity: "Circularity",
  mean_r: "Mean red",
  mean_g: "Mean green",
  mean_b: "Mean blue",
  mean_intensity: "Mean intensity",
  saturated_fraction: "Saturated fraction",
};

function flattenMeasurements(measurements: Json): AnalysisResult["measurements"] {
  const out: AnalysisResult["measurements"] = [];
  for (const [group, suffix] of [["geometry_px", " (px)"], ["geometry_physical", " (scaled)"], ["appearance", ""]] as const) {
    for (const [key, m] of Object.entries<Json>(measurements?.[group] ?? {})) {
      if (!m || typeof m !== "object" || typeof m.value !== "number") continue;
      out.push({
        name: (MEASUREMENT_LABELS[key] ?? key) + suffix,
        value: m.value,
        unit: m.unit,
        confidence: typeof m.confidence === "number" ? m.confidence : 0.9,
        observation_type: m.classification ?? "measured",
      });
    }
  }
  return out;
}

export async function fetchAnalysis(id?: string): Promise<AnalysisResult | null> {
  try {
    let analysisId = id;
    if (!analysisId) {
      const list = await getJson("analyses?status=completed&page_size=1");
      analysisId = list.items?.[0]?.analysis_id;
      if (!analysisId) return null;
    }
    const { analysis: a } = await getJson(`analyses/${analysisId}`);
    if (!a) return null;
    return {
      id: a.analysis_id,
      status: a.status === "completed" ? "completed" : a.status === "failed" ? "failed" : "pending",
      image_id: a.input?.original_filename ?? a.analysis_id,
      pipeline_version: a.pipeline?.pipeline_version ?? "—",
      model_version: a.pipeline?.detector ? `${a.pipeline.detector.name} ${a.pipeline.detector.version}` : "—",
      preprocessing_version: a.pipeline?.preprocessing_version ?? "—",
      calibration_state: a.input?.calibration?.state ?? "uncalibrated",
      masks: [],
      measurements: flattenMeasurements(a.result?.measurements),
      warnings: (a.warnings ?? []).map((w: Json) => (typeof w === "string" ? w : w.message)),
      created_at: a.created_at,
    };
  } catch {
    return null;
  }
}

// Knowledge extraction graph endpoint is not implemented in v0.1 backend contract.
// Returns empty array so UI renders honest "Not available yet" empty state per R3.
export async function fetchKnowledge(): Promise<KnowledgeEntity[]> {
  return [];
}

export async function fetchAnalysesHistory(): Promise<AnalysisSummary[]> {
  try {
    const body = await getJson("analyses?page_size=50");
    return (body.items ?? []).map((i: Json) => ({
      analysis_id: i.analysis_id,
      original_filename: i.original_filename,
      status: i.status === "completed" || i.status === "failed" ? i.status : "processing",
      flame_area_px: i.flame_area_px ?? undefined,
      calibration_state: i.calibration_state ?? "uncalibrated",
      created_at: i.created_at,
    }));
  } catch {
    return [];
  }
}

export async function fetchExperiments(): Promise<ExperimentRecord[]> {
  try {
    const search = await getJson("search?q=flame&type=experiment&domain=all&page_size=20");
    const ids: string[] = (search.results ?? []).map((r: Json) => r.experiment_id).filter(Boolean);
    const details = await Promise.all(ids.map((id) => getJson(`experiments/${id}`)));
    return details.map(({ experiment: e }) => ({
      experiment_id: e.experiment_id,
      name: `${e.investigation ?? "Experiment"} ${e.test_id}`,
      objective: e.fuel_or_material ?? "—",
      platform: e.source?.short_name ?? e.source?.repository ?? "—",
      gravity_regime: e.gravity_regime ?? "unknown",
      conditions: (e.conditions ?? [])
        .filter((c: Json) => c.value_numeric != null)
        .map((c: Json) => ({
          variable: c.variable,
          value: c.value_numeric,
          unit: c.unit_original ?? "",
          method: c.origin ?? "",
        })),
    }));
  } catch {
    return [];
  }
}

/**
 * Validate an image file according to contract specifications:
 * - Allowed media types: image/png, image/jpeg
 * - Max file size: 10 MB
 * - Min dimensions: 64x64
 * - Max total pixels: 16 MP (16,000,000)
 */
export async function validateImageFile(
  file: File
): Promise<{ valid: boolean; error?: string; dimensions?: { width: number; height: number } }> {
  const allowedTypes = ["image/png", "image/jpeg"];
  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      error: `Unsupported file type: ${file.type || "unknown"}. Only PNG and JPEG are accepted.`,
    };
  }

  const maxBytes = 10 * 1024 * 1024; // 10MB
  if (file.size > maxBytes) {
    return {
      valid: false,
      error: `Image exceeds maximum allowed size of 10 MB (size: ${(file.size / (1024 * 1024)).toFixed(2)} MB).`,
    };
  }

  if (typeof window !== "undefined" && typeof Image !== "undefined") {
    try {
      const dimensions = await new Promise<{ width: number; height: number }>((resolve, reject) => {
        const img = new Image();
        const url = URL.createObjectURL(file);
        img.onload = () => {
          URL.revokeObjectURL(url);
          resolve({ width: img.naturalWidth, height: img.naturalHeight });
        };
        img.onerror = () => {
          URL.revokeObjectURL(url);
          reject(new Error("Image decode failed."));
        };
        img.src = url;
      });

      if (dimensions.width < 64 || dimensions.height < 64) {
        return {
          valid: false,
          error: `Image dimensions (${dimensions.width}x${dimensions.height}) are too small. Minimum required is 64x64 px.`,
        };
      }

      const totalPixels = dimensions.width * dimensions.height;
      if (totalPixels > 16_000_000) {
        return {
          valid: false,
          error: `Image exceeds maximum limit of 16 megapixels (${(totalPixels / 1_000_000).toFixed(1)} MP).`,
        };
      }

      return { valid: true, dimensions };
    } catch {
      return { valid: false, error: "The uploaded file could not be decoded as a valid image." };
    }
  }

  return { valid: true };
}

/**
 * Submit Flame Image for Analysis (POST /api/analyses)
 * Follows OpenAPI contract:
 * - Content-Type: multipart/form-data
 * - Field: image (file)
 * - Returns 202 Accepted with queued AnalysisResponse
 * - On failure: NEVER returns a fake/simulated result. Returns clear UPSTREAM_UNAVAILABLE error.
 */
export async function submitFlameAnalysis(
  formData: FormData
): Promise<{
  success: boolean;
  analysisId?: string;
  analysis?: AnalysisResult;
  error?: ApiErrorDetail;
}> {
  const requestId = `req_upload_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  const idempotencyKey = `idem_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;

  try {
    const res = await fetch(`${API_BASE}/api/analyses`, {
      method: "POST",
      headers: {
        "x-request-id": requestId,
        "idempotency-key": idempotencyKey,
      },
      body: formData,
    });

    if (res.status === 202 || res.ok) {
      const body = await res.json();
      const analysisId = body.analysis?.analysis_id || body.id;
      return {
        success: true,
        analysisId,
        analysis: body.analysis,
      };
    }

    let errorDetail: ApiErrorDetail = {
      code: "UPSTREAM_UNAVAILABLE",
      message: `Analysis upload was rejected with HTTP ${res.status}.`,
      request_id: requestId,
      retryable: true,
    };

    try {
      const errorJson = await res.json();
      if (errorJson.error) {
        errorDetail = errorJson.error;
      }
    } catch {
      // Body not JSON
    }

    return {
      success: false,
      error: errorDetail,
    };
  } catch {
    return {
      success: false,
      error: {
        code: "UPSTREAM_UNAVAILABLE",
        message: "The Flame API could not be reached. Check upstream health or retry shortly.",
        request_id: requestId,
        retryable: true,
      },
    };
  }
}
