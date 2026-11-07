"use client";

import { useEffect, useState } from "react";
import { fetchAnalysesHistory } from "@/lib/api/client";
import { AnalysisSummary } from "@/lib/api/types";
import { History, ArrowRight, CheckCircle2, Clock } from "lucide-react";
import Link from "next/link";

export default function HistoryPage() {
  const [history, setHistory] = useState<AnalysisSummary[]>([]);

  useEffect(() => {
    fetchAnalysesHistory().then(setHistory);
  }, []);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
            style={{ color: 'var(--text-primary)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg"
               style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
            <History className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
          </div>
          Flame Analysis History
        </h1>
        <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
          Traceable archive of processed combustion image frames and pipeline executions.
        </p>
      </div>

      {/* Table */}
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
                      href={item.analysis_type === "flame_video" ? `/analysis?video=${item.analysis_id}` : `/analysis?id=${item.analysis_id}`}
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
    </div>
  );
}
