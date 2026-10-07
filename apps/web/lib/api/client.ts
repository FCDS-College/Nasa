import { SystemHealth, ChatResponse, ChatRequest, SearchResponse, EvidenceRecord, AnalysisResult, KnowledgeEntity, DashboardData, AnalysisSummary, ExperimentRecord } from "./types";
import { mockHealth, mockChatResponse, mockSearchResults, mockEvidence, mockAnalysis, mockKnowledge, mockDashboard, mockHistory, mockExperiments } from "./mockData";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchHealth(): Promise<SystemHealth> {
  if (!API_BASE) return mockHealth;
  try {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("API error");
    return res.json();
  } catch {
    return mockHealth;
  }
}

export async function fetchDashboardData(): Promise<DashboardData> {
  if (!API_BASE) return mockDashboard;
  return mockDashboard; // Fallback
}

export async function submitChat(req: ChatRequest): Promise<ChatResponse> {
  if (!API_BASE) {
    return new Promise((resolve) => setTimeout(() => resolve(mockChatResponse), 1500));
  }
  return mockChatResponse;
}

export async function searchResearch(query: string, filters?: Record<string, unknown>): Promise<SearchResponse> {
  if (!API_BASE) return mockSearchResults;
  return mockSearchResults;
}

export async function fetchEvidence(id: string): Promise<EvidenceRecord | null> {
  if (!API_BASE) return mockEvidence[id] || null;
  return mockEvidence[id] || null;
}

export async function fetchAnalysis(id: string): Promise<AnalysisResult> {
  if (!API_BASE) return mockAnalysis;
  return mockAnalysis;
}

export async function fetchKnowledge(): Promise<KnowledgeEntity[]> {
  if (!API_BASE) return mockKnowledge;
  return mockKnowledge;
}

export async function fetchAnalysesHistory(): Promise<AnalysisSummary[]> {
  if (!API_BASE) return mockHistory;
  return mockHistory;
}

export async function fetchExperiments(): Promise<ExperimentRecord[]> {
  if (!API_BASE) return mockExperiments;
  return mockExperiments;
}
