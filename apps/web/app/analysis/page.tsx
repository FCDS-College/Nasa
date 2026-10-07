"use client";

import { useState, useEffect } from "react";
import { fetchAnalysis, artifactUrl } from "@/lib/api/client";
import { AnalysisResult } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Flame, Upload, Eye, EyeOff, AlertTriangle, Crosshair, BarChart2, Cpu } from "lucide-react";

export default function AnalysisPage() {
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [showMask, setShowMask] = useState(true);

  useEffect(() => {
    fetchAnalysis().then((a) => {
      setAnalysis(a);
      setLoaded(true);
    });
  }, []);

  return (
    <div className="flex flex-col w-full p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start animate-fade-in-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2.5"
              style={{ color: 'var(--text-primary)' }}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                 style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <Flame className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
            </div>
            Flame Analysis Studio
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Secure upload, deterministic CV measurements, and physical calibration warnings.
          </p>
        </div>
        <button
          id="upload-btn"
          disabled
          title="Uploads require a write token and are not enabled in the dashboard yet"
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold"
          style={{
            background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
            color: '#000',
            boxShadow: '0 0 12px rgba(59,130,246,0.2)',
            transition: 'all var(--transition-fast)',
          }}
        >
          <Upload className="h-4 w-4" />
          Upload Image
        </button>
      </div>

      {loaded && !analysis ? (
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          No completed analyses are available yet.
        </p>
      ) : !analysis ? (
        <div className="flex items-center gap-3" style={{ color: 'var(--text-muted)' }}>
          <Cpu className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          Loading analysis studio...
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          {/* Image Viewer */}
          <div className="lg:col-span-2 rounded-2xl overflow-hidden flex flex-col"
               style={{
                 background: 'var(--bg-card)',
                 border: '1px solid var(--border-default)',
                 boxShadow: 'var(--shadow-card)',
               }}>
            <div className="flex items-center justify-between px-5 py-3"
                 style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-3">
                <span className="text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                  ID: {analysis.image_id}
                </span>
                <Badge variant={analysis.status === "completed" ? "success" : "default"}>
                  {analysis.status.toUpperCase()}
                </Badge>
              </div>
              <button
                onClick={() => setShowMask(!showMask)}
                className="flex items-center gap-2 text-xs font-medium"
                style={{ color: 'var(--text-muted)', transition: 'color var(--transition-fast)' }}
              >
                {showMask ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showMask ? "Hide Overlay" : "Show Overlay"}
              </button>
            </div>
            <div className="relative flex-1 flex items-center justify-center min-h-[400px] overflow-hidden"
                 style={{ background: 'rgba(0,0,0,0.05)' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={artifactUrl(analysis.id, showMask ? "overlay" : "original")}
                alt={showMask ? "Flame detection overlay" : "Original flame image"}
                className="max-h-[520px] w-full object-contain"
              />
            </div>
          </div>

          {/* Measurements & Metadata */}
          <div className="space-y-5">
            {/* Measurements */}
            <div className="rounded-2xl p-5 space-y-4"
                 style={{
                   background: 'var(--bg-card)',
                   border: '1px solid var(--border-default)',
                   boxShadow: 'var(--shadow-card)',
                 }}>
              <h3 className="text-sm font-semibold flex items-center gap-2"
                  style={{ color: 'var(--text-primary)' }}>
                <BarChart2 className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                Measurements
              </h3>
              <div className="space-y-3">
                {analysis.measurements.map((m, idx) => (
                  <div key={idx} className="rounded-xl p-3.5"
                       style={{
                         background: 'var(--border-subtle)',
                         border: '1px solid var(--border-subtle)',
                       }}>
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{m.name}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider"
                            style={{
                              background: m.observation_type === 'measured' ? 'rgba(16,185,129,0.08)' : 'rgba(59,130,246,0.08)',
                              color: m.observation_type === 'measured' ? 'var(--accent-success)' : 'var(--accent-flame)',
                              border: `1px solid ${m.observation_type === 'measured' ? 'rgba(16,185,129,0.15)' : 'rgba(59,130,246,0.15)'}`,
                            }}>
                        {m.observation_type}
                      </span>
                    </div>
                    <div className="flex items-end justify-between">
                      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}
                           className="text-lg font-bold">
                        {m.value.toLocaleString()}{" "}
                        <span className="text-xs" style={{ color: 'var(--text-dim)' }}>{m.unit}</span>
                      </div>
                      {m.confidence !== undefined && (
                        <div className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                          {(m.confidence * 100).toFixed(0)}% conf
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Pipeline Metadata */}
            <div className="rounded-2xl p-5 space-y-4"
                 style={{
                   background: 'var(--bg-card)',
                   border: '1px solid var(--border-default)',
                   boxShadow: 'var(--shadow-card)',
                 }}>
              <h3 className="text-sm font-semibold flex items-center gap-2"
                  style={{ color: 'var(--text-primary)' }}>
                <Crosshair className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                Pipeline Metadata
              </h3>
              <div className="space-y-2.5 text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                {[
                  ["CV Model", analysis.model_version],
                  ["Preprocessing", analysis.preprocessing_version],
                  ["Calibration", analysis.calibration_state],
                ].map(([label, value], idx) => (
                  <div key={idx} className="flex justify-between pb-2"
                       style={{ borderBottom: idx < 2 ? '1px solid var(--border-subtle)' : 'none' }}>
                    <span>{label}:</span>
                    <span style={{
                      color: label === "Calibration" && value === "uncalibrated"
                        ? 'var(--accent-warning)' : 'var(--text-secondary)'
                    }}>
                      {typeof value === 'string' ? value.toUpperCase() : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Warnings */}
            {analysis.warnings.length > 0 && (
              <div className="rounded-2xl p-4 space-y-2.5"
                   style={{
                     background: 'rgba(239,68,68,0.04)',
                     border: '1px solid rgba(239,68,68,0.15)',
                   }}>
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] flex items-center gap-1.5"
                    style={{ color: 'var(--accent-danger)' }}>
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Scientific Warnings
                </h3>
                <ul className="list-disc list-inside text-xs space-y-1"
                    style={{ color: 'rgba(239,68,68,0.7)' }}>
                  {analysis.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
