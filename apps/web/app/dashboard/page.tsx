"use client";

import { useEffect, useState } from "react";
import { fetchDashboardData, fetchHealth } from "@/lib/api/client";
import { DashboardData, SystemHealth } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  LayoutDashboard,
  Database,
  BarChart3,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Flame,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [dash, hlth] = await Promise.all([fetchDashboardData(), fetchHealth()]);
      setData(dash);
      setHealth(hlth);
    } catch (err: any) {
      setError(err?.message || "Failed to load dashboard data from Flame API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4 animate-fade-in-up">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
                style={{ color: 'var(--text-primary)' }}>
              <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                   style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
                <LayoutDashboard className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
              </div>
              Scientific Dashboard
            </h1>
            <Badge variant="default">MVP §13 / §23</Badge>
          </div>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Corpus status, evaluation scorecard snapshot, scientific source coverage, and subsystem health.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/chat"
            className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold"
            style={{
              background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
              color: '#000',
              boxShadow: 'var(--shadow-glow-sm)',
            }}
          >
            <Flame className="h-4 w-4" />
            Launch Research Chat
          </Link>
          <button
            onClick={loadData}
            title="Refresh dashboard metrics"
            className="flex h-9 w-9 items-center justify-center rounded-xl p-2 cursor-pointer transition-all"
            style={{
              background: 'var(--border-subtle)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <Activity className="h-8 w-8 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          <p className="mt-3 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Connecting to Flame API and retrieving corpus metrics...
          </p>
        </div>
      ) : error ? (
        <div className="rounded-2xl p-6 text-center space-y-3"
             style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-danger)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto" />
          <h3 className="font-bold text-base">Dashboard Metrics Unavailable</h3>
          <p className="text-xs max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
            {error}
          </p>
          <button
            onClick={loadData}
            className="mt-2 rounded-lg px-4 py-1.5 text-xs font-semibold cursor-pointer"
            style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-danger)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            Retry Connection
          </button>
        </div>
      ) : (
        <div className="space-y-6 animate-fade-in-up">
          {/* Top Metrics Cards */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-2xl p-5"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                <span>Total Documents</span>
                <Database className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
              </div>
              <div className="text-2xl font-bold mt-2" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {data?.corpus_status.total_documents?.toLocaleString() ?? "0"}
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                Curated NASA & NIST papers
              </p>
            </div>

            <div className="rounded-2xl p-5"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                <span>Indexed Chunks</span>
                <Layers className="h-4 w-4" style={{ color: 'var(--accent-cyan)' }} />
              </div>
              <div className="text-2xl font-bold mt-2" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {data?.corpus_status.indexed_chunks?.toLocaleString() ?? "0"}
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                Passages with vector embeddings
              </p>
            </div>

            <div className="rounded-2xl p-5"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                <span>API Health Status</span>
                <Activity className="h-4 w-4"
                          style={{ color: health?.status === "ok" ? 'var(--accent-success)' : health?.status === "degraded" ? 'var(--accent-warning)' : 'var(--text-dim)' }} />
              </div>
              <div className="text-2xl font-bold mt-2 flex items-center gap-2"
                   style={{ color: health?.status === "ok" ? 'var(--accent-success)' : health?.status === "degraded" ? 'var(--accent-warning)' : 'var(--text-muted)' }}>
                <span>{health?.status ? health.status.toUpperCase() : "UNKNOWN"}</span>
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                v{health?.version || "unknown"}
              </p>
            </div>

            <div className="rounded-2xl p-5"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between text-xs" style={{ color: 'var(--text-muted)' }}>
                <span>Corpus Version</span>
                <CheckCircle2 className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
              </div>
              <div className="text-2xl font-bold mt-2" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                {data?.corpus_status.version || "unversioned"}
              </div>
              <p className="text-[11px] mt-1" style={{ color: 'var(--text-dim)' }}>
                NTRS & PSI Grounded
              </p>
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Scientific Evaluation Scorecard (B5: honest state, no hardcoded passing numbers) */}
            <div className="rounded-2xl p-6 space-y-4"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                    <BarChart3 className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                    AI Evaluation Scorecard Snapshot
                  </h3>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                    Contract thresholds vs. benchmark metrics
                  </p>
                </div>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                      style={{ background: 'var(--border-subtle)', color: 'var(--text-muted)', border: '1px solid var(--border-subtle)' }}>
                  Evaluation Gate
                </span>
              </div>

              {/* Honest Evaluation State (Task B5) */}
              <div className="rounded-xl p-6 text-center space-y-2"
                   style={{ background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md"
                      style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-secondary)' }}>
                  Not evaluated yet
                </span>
                <p className="text-xs max-w-sm mx-auto pt-2" style={{ color: 'var(--text-dim)' }}>
                  Quantitative benchmark scorecards (Recall@5, Segmentation IoU, Factuality) have not been published by an evaluation endpoint yet.
                </p>
              </div>
            </div>

            {/* Subsystem Health Matrix */}
            <div className="rounded-2xl p-6 space-y-4"
                 style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', boxShadow: 'var(--shadow-card)' }}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                    <Activity className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                    Live Subsystem Connectivity
                  </h3>
                  <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                    Current status of backend service dependencies
                  </p>
                </div>
                <Link href="/status" className="text-xs font-semibold" style={{ color: 'var(--accent-flame)' }}>
                  Full Diagnostics →
                </Link>
              </div>

              <div className="space-y-2 pt-2">
                {health?.services && Object.keys(health.services).length > 0 ? (
                  Object.entries(health.services).map(([name, s]) => (
                    <div key={name} className="flex items-center justify-between rounded-xl px-3.5 py-2.5"
                         style={{ background: 'var(--border-subtle)' }}>
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full"
                              style={{
                                background: s.status === 'up' ? 'var(--accent-success)' : s.status === 'disabled' ? 'var(--text-dim)' : 'var(--accent-danger)',
                              }} />
                        <span className="text-xs font-semibold capitalize text-white">
                          {name.replace("_", " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs font-mono">
                        {s.latency_ms != null && (
                          <span style={{ color: 'var(--text-dim)' }}>{s.latency_ms.toFixed(1)}ms</span>
                        )}
                        <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                              style={{
                                background: s.status === 'up' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                                color: s.status === 'up' ? 'var(--accent-success)' : 'var(--accent-danger)',
                              }}>
                          {s.status}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-center py-4" style={{ color: 'var(--text-dim)' }}>
                    No subsystem health reported.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
