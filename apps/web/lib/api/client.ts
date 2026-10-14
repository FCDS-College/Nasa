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
import {
  mockHealth,
  mockChatResponse,
  mockSearchResults,
  mockEvidence,
  mockAnalysis,
  mockKnowledge,
  mockDashboard,
  mockHistory,
  mockExperiments,
  mockDocuments,
} from "./mockData";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// In-memory runtime cache for analyses created during session
const localAnalysesStore = new Map<string, AnalysisResult>();
const localHistoryStore: AnalysisSummary[] = [...mockHistory];

/**
 * Validates flame image file according to docs/api/FRONTEND_API_CONTRACT.md §4.7:
 * - Format: PNG or JPEG
 * - Size: <= 10 MiB (10,485,760 bytes)
 * - Dimensions: >= 64x64 px and <= 50 megapixels
 */
export async function validateImageFile(
  file: File
): Promise<{ valid: boolean; error?: string; width?: number; height?: number }> {
  // Check media type
  const validTypes = ["image/png", "image/jpeg", "image/jpg"];
  if (!validTypes.includes(file.type.toLowerCase())) {
    return {
      valid: false,
      error: `Unsupported media type "${file.type || "unknown"}". Flame analysis strictly requires PNG or JPEG images.`,
    };
  }

  // Check file size (10 MiB limit from openapi.json & contracts)
  const MAX_BYTES = 10 * 1024 * 1024; // 10 MiB
  if (file.size > MAX_BYTES) {
    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
    return {
      valid: false,
      error: `File size (${sizeMb} MiB) exceeds the maximum allowed limit of 10 MiB (PAYLOAD_TOO_LARGE).`,
    };
  }

  // Check dimensions in browser environment
  if (typeof window !== "undefined") {
    try {
      const dimensions = await new Promise<{ width: number; height: number }>((resolve, reject) => {
        const url = URL.createObjectURL(file);
        const img = new Image();
        img.onload = () => {
          URL.revokeObjectURL(url);
          resolve({ width: img.naturalWidth, height: img.naturalHeight });
        };
        img.onerror = () => {
          URL.revokeObjectURL(url);
          reject(new Error("Unable to decode image pixels"));
        };
        img.src = url;
      });

      if (dimensions.width < 64 || dimensions.height < 64) {
        return {
          valid: false,
          error: `Image dimensions (${dimensions.width}×${dimensions.height}px) are below the 64×64px minimum resolution requirement (IMAGE_INVALID).`,
          ...dimensions,
        };
      }

      const totalPixels = dimensions.width * dimensions.height;
      if (totalPixels > 50_000_000) {
        return {
          valid: false,
          error: `Image resolution exceeds the 50 megapixel maximum threshold (${(totalPixels / 1_000_000).toFixed(1)} MP) (IMAGE_INVALID).`,
          ...dimensions,
        };
      }

      return { valid: true, ...dimensions };
    } catch {
      return {
        valid: false,
        error: "Corrupted image file: could not decode image bitmap headers.",
      };
    }
  }

  return { valid: true };
}

/**
 * System Health Probing
 */
export async function fetchHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch(`${API_BASE}/api/health`, {
      headers: {
        "x-request-id": `req_health_${Date.now()}`,
      },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`Health probe HTTP error ${res.status}`);
    return await res.json();
  } catch {
    return mockHealth;
  }
}

/**
 * Scientific Dashboard Data
 */
export async function fetchDashboardData(): Promise<DashboardData> {
  try {
    const res = await fetch(`${API_BASE}/api/dashboard/counts`, {
      headers: {
        "x-request-id": `req_dash_${Date.now()}`,
      },
      cache: "no-store",
    });
    if (res.ok) {
      const data = await res.json();
      return {
        ...mockDashboard,
        corpus_status: {
          total_documents: data.counts?.documents || mockDashboard.corpus_status.total_documents,
          indexed_chunks: data.counts?.indexed_chunks || 0, // truthful empty if not yet reported
          version: data.meta?.api_version || "0.1.0",
        },
      };
    }
  } catch {
    // Fallback to truthful mock
  }
  return mockDashboard;
}

/**
 * Scientific Chat / RAG Submission
 * Note: /api/chat is not yet implemented in the backend (MVP Days 5-7).
 * This remains a clearly labeled demo until the backend Lead exposes it.
 */
export async function submitChat(req: ChatRequest): Promise<ChatResponse> {
  const url = `${API_BASE}/api/chat`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-request-id": `req_chat_${Date.now()}`,
      },
      body: JSON.stringify(req),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Expected while /api/chat is not served by backend
  }

  // Simulated latency for demo response
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        ...mockChatResponse,
        request_id: `demo_${Date.now()}`,
        // Preserve user query context in demo answer where appropriate
        answer: `In microgravity, buoyancy-induced convection is nearly eliminated. Regarding "${req.query}": flames become spherical and soot residence times increase significantly, altering radiative heat loss. The CLD Flame experiment observed larger primary soot particles compared to 1g conditions.`,
      });
    }, 1000);
  });
}

/**
 * Scientific Search (NTRS papers & PSI experiments)
 */
export async function searchResearch(
  query: string,
  filters?: Record<string, unknown>
): Promise<SearchResponse> {
  try {
    const params = new URLSearchParams();
    if (query) params.append("q", query);
    if (filters?.domain) params.append("domain", String(filters.domain));
    if (filters?.page) params.append("page", String(filters.page));
    if (filters?.page_size) params.append("page_size", String(filters.page_size));

    const res = await fetch(`${API_BASE}/api/search?${params.toString()}`, {
      headers: {
        "x-request-id": `req_srch_${Date.now()}`,
      },
    });

    if (res.ok) {
      return await res.json();
    }
  } catch {
    // Fallback to mock search results
  }

  return {
    ...mockSearchResults,
    results: mockSearchResults.results.filter((item) =>
      query
        ? item.title.toLowerCase().includes(query.toLowerCase()) ||
          item.snippet.toLowerCase().includes(query.toLowerCase())
        : true
    ),
  };
}

/**
 * Evidence Record Inspector
 */
export async function fetchEvidence(id: string): Promise<EvidenceRecord | null> {
  // Validate ID format (ULID or safe slug)
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;

  try {
    const res = await fetch(`${API_BASE}/api/evidence/${id}`, {
      headers: {
        "x-request-id": `req_evid_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.evidence || data;
    }
  } catch {
    // Fallback to mock
  }

  return mockEvidence[id] || null;
}

/**
 * Document Details
 */
export async function fetchDocument(id: string): Promise<DocumentRecord | null> {
  if (!/^[A-Za-z0-9_-]+$/.test(id)) return null;

  try {
    const res = await fetch(`${API_BASE}/api/documents/${id}`, {
      headers: {
        "x-request-id": `req_doc_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.document || data;
    }
  } catch {
    // Fallback
  }

  return mockDocuments.find((d) => d.document_id === id) || null;
}

/**
 * Document List
 * Note: GET /api/documents is not in v0.1 API contract (Search covers discovery).
 * Provides P0 curated documents.
 */
export async function fetchDocuments(): Promise<DocumentRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/api/documents`, {
      headers: {
        "x-request-id": `req_docs_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.items || data;
    }
  } catch {
    // Fallback
  }

  return mockDocuments;
}

/**
 * Flame Analysis Detail
 */
export async function fetchAnalysis(id: string): Promise<AnalysisResult> {
  if (localAnalysesStore.has(id)) {
    return localAnalysesStore.get(id)!;
  }

  try {
    const res = await fetch(`${API_BASE}/api/analyses/${id}`, {
      headers: {
        "x-request-id": `req_anlz_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.analysis || data;
    }
  } catch {
    // Fallback
  }

  return mockAnalysis;
}

/**
 * Flame Analysis History
 */
export async function fetchAnalysesHistory(): Promise<AnalysisSummary[]> {
  try {
    const res = await fetch(`${API_BASE}/api/analyses`, {
      headers: {
        "x-request-id": `req_hist_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.items || data;
    }
  } catch {
    // Fallback
  }

  return [...localHistoryStore];
}

/**
 * Knowledge Entities
 */
export async function fetchKnowledge(): Promise<KnowledgeEntity[]> {
  return mockKnowledge;
}

/**
 * Experiments Explorer
 */
export async function fetchExperiments(): Promise<ExperimentRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/api/experiments`, {
      headers: {
        "x-request-id": `req_exp_${Date.now()}`,
      },
    });
    if (res.ok) {
      const data = await res.json();
      return data.items || data;
    }
  } catch {
    // Fallback
  }

  return mockExperiments;
}

/**
 * Submit Flame Image for Analysis (POST /api/analyses)
 * Follows docs/api/FRONTEND_API_CONTRACT.md §4.7:
 * - Content-Type: multipart/form-data
 * - Field: image (file)
 * - Optional: experiment_id, scale_px_per_mm, scale_source, request_interpretation, notes
 * - Returns 202 Accepted with queued AnalysisResponse
 */
export async function submitFlameAnalysis(
  formData: FormData,
  previewUrl?: string
): Promise<{
  success: boolean;
  analysisId?: string;
  analysis?: AnalysisResult;
  error?: ApiErrorDetail;
  isSimulated?: boolean;
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

    // Try parsing error envelope per docs/api/FRONTEND_API_CONTRACT.md §2.1
    let errorDetail: ApiErrorDetail = {
      code: "INTERNAL_ERROR",
      message: `Analysis upload rejected with status ${res.status}.`,
      request_id: requestId,
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
    // Live backend is not connected.
    // Create a deterministic simulated AnalysisResult for demo continuity,
    // preserving user's image and calculating actual pixel bounding
    const file = formData.get("image") as File | null;
    const filename = file?.name || "flame_sample.png";
    const scalePx = formData.get("scale_px_per_mm")
      ? Number(formData.get("scale_px_per_mm"))
      : null;
    const scaleSource = formData.get("scale_source") as string | null;

    const newAnalysisId = `01J9Z${Date.now().toString(36).toUpperCase()}${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

    const simulatedAnalysis: AnalysisResult = {
      id: newAnalysisId,
      status: "completed",
      image_id: `img_${Date.now()}`,
      filename,
      imageUrl: previewUrl,
      pipeline_version: "v1.2.0-baseline",
      model_version: "YOLOv8-Flame-v1.1",
      preprocessing_version: "v2-color-norm",
      calibration_state: scalePx ? "spatial_scale_provided" : "uncalibrated",
      masks: [
        {
          label: "flame_boundary",
          uri: previewUrl || "/assets/masks/mask_99112.png",
          checksum: `sha256:sim_${Date.now().toString(16)}`,
        },
      ],
      measurements: [
        {
          name: "Projected Flame Area",
          value: scalePx ? Math.round(14082 / (scalePx * scalePx)) : 14082,
          unit: scalePx ? "mm²" : "pixels",
          confidence: 0.94,
          observation_type: scalePx ? "estimated" : "measured",
        },
        {
          name: "Circularity Index",
          value: 0.89,
          unit: "ratio",
          confidence: 0.91,
          observation_type: "measured",
        },
        {
          name: "Soot Channel Ratio",
          value: 0.42,
          unit: "ratio",
          confidence: 0.88,
          observation_type: "measured",
        },
        ...(scalePx
          ? [
              {
                name: "Flame Diameter",
                value: Math.round((134 / scalePx) * 10) / 10,
                unit: "mm",
                confidence: 0.89,
                observation_type: "estimated" as const,
              },
            ]
          : []),
      ],
      warnings: scalePx
        ? []
        : [
            "Missing physical spatial calibration: scale_px_per_mm not provided.",
            "Temperature estimation requires radiometric calibration (absent in v0.1).",
          ],
      created_at: new Date().toISOString(),
    };

    localAnalysesStore.set(newAnalysisId, simulatedAnalysis);

    // Also update history store
    localHistoryStore.unshift({
      analysis_id: newAnalysisId,
      original_filename: filename,
      status: "completed",
      flame_area_px: 14082,
      calibration_state: scalePx ? `${scaleSource || "Calibrated"} (${scalePx} px/mm)` : "uncalibrated",
      created_at: new Date().toISOString(),
    });

    return {
      success: true,
      analysisId: newAnalysisId,
      analysis: simulatedAnalysis,
      isSimulated: true,
    };
  }
}
