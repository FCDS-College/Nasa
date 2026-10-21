"use client";

import { useEffect, useState } from "react";
import { fetchAnalysesHistory } from "@/lib/api/client";
import { AnalysisSummary } from "@/lib/api/types";
import { History, ArrowRight, CheckCircle2, Clock, AlertTriangle, Flame, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function HistoryPage() {
  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAnalysesHistory();
      setHistory(data);
    } catch (err: any) {
      setError(err?.message || "Failed to load analysis history.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start gap-4 animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <History className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Flame Analysis History
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Traceable archive of processed combustion image frames and pipeline executions from the live API.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/analysis"
            className="flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold cursor-pointer"
            style={{
              background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
              color: '#000',
            }}
          >
            <Flame className="h-3.5 w-3.5" />
            New Analysis
          </Link>
          <button
            onClick={loadHistory}
            className="flex h-9 w-9 items-center justify-center rounded-xl p-2 cursor-pointer transition-all"
            style={{
              background: 'var(--border-subtle)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
            }}
            title="Refresh history"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <Clock className="h-8 w-8 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          <p className="mt-3 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Retrieving analysis logs from Flame API...
          </p>
        </div>
      ) : error ? (
        <div className="rounded-2xl p-6 text-center space-y-3"
             style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-danger)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto" />
          <h3 className="font-bold text-base">Error Loading History</h3>
          <p className="text-xs">{error}</p>
          <button
            onClick={loadHistory}
            className="rounded-lg px-4 py-1.5 text-xs font-semibold cursor-pointer"
            style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-danger)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            Retry
          </button>
        </div>
      ) : history.length === 0 ? (
        <div className="rounded-2xl p-12 text-center space-y-4 animate-fade-in-up"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl mx-auto"
               style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid var(--border-subtle)' }}>
            <History className="h-7 w-7" style={{ color: 'var(--accent-flame)', opacity: 0.8 }} />
          </div>
          <div>
            <h3 className="font-bold text-white text-base">No Prior Analyses</h3>
            <p className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
              No historical analyses have been recorded on the live server yet. Start by uploading a flame image in the studio.
            </p>
          </div>
          <Link
            href="/analysis"
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold"
            style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)', border: '1px solid rgba(59,130,246,0.25)' }}
          >
            Launch Analysis Studio →
          </Link>
        </div>
      ) : (
        <div className="rounded-2xl overflow-hidden animate-fade-in-up"
             style={{
               animationDelay: '100ms',
               background: 'var(--bg-card)',
               border: '1px solid var(--border-default)',
               boxShadow: 'var(--shadow-card)',
             }}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', background: 'var(--border-subtle)' }}>
                  {["Analysis ID", "Source Image", "Status", "Flame Area (px²)", "Calibration", "Timestamp", ""].map((h) => (
                    <th key={h} className="px-5 py-4 text-[10px] font-bold uppercase tracking-[0.15em]"
                        style={{ color: 'var(--text-dim)', ...(h === "" ? { textAlign: 'right' as const } : {}) }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.analysis_id}
                      style={{
                        borderBottom: '1px solid var(--border-subtle)',
                        transition: 'background var(--transition-fast)',
                      }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--border-subtle)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
                  >
                    <td className="px-5 py-4 font-semibold"
                        style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-flame)' }}>
                      {item.analysis_id.slice(0, 10)}...
                    </td>
                    <td className="px-5 py-4 font-medium" style={{ color: 'var(--text-primary)' }}>
                      {item.original_filename}
                    </td>
                    <td className="px-5 py-4">
                      <span className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
                            style={{
                              background: item.status === "completed" ? 'rgba(16,185,129,0.08)' :
                                         item.status === "processing" ? 'rgba(59,130,246,0.08)' : 'var(--border-subtle)',
                              color: item.status === "completed" ? 'var(--accent-success)' :
                                     item.status === "processing" ? 'var(--accent-flame)' : 'var(--text-muted)',
                              border: `1px solid ${item.status === "completed" ? 'rgba(16,185,129,0.15)' :
                                      item.status === "processing" ? 'rgba(59,130,246,0.15)' : 'var(--border-subtle)'}`,
                            }}>
                        {item.status === "completed" && <CheckCircle2 className="h-3 w-3" />}
                        {item.status === "processing" && <Clock className="h-3 w-3 animate-spin" />}
                        {item.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-4"
                        style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                      {item.flame_area_px ? item.flame_area_px.toLocaleString() : "—"}
                    </td>
                    <td className="px-5 py-4">
                      <span style={{
                        color: item.calibration_state === "spatial_scale_provided"
                          ? 'var(--accent-success)' : 'var(--text-dim)'
                      }}>
                        {item.calibration_state === "spatial_scale_provided" ? "Calibrated" : "Uncalibrated"}
                      </span>
                    </td>
                    <td className="px-5 py-4" style={{ color: 'var(--text-dim)' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-4 text-right">
                      <Link
                        href={`/analysis?id=${item.analysis_id}`}
                        className="inline-flex items-center gap-1 text-xs font-medium"
                        style={{ color: 'var(--accent-flame)', transition: 'opacity var(--transition-fast)' }}
                      >
                        Inspect <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
