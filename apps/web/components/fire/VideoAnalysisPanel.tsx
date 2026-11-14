"use client";

import { useEffect, useState } from "react";
import { Film } from "lucide-react";
import { Empty, ErrorNote, Loading } from "@/components/fire/FireUi";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

interface Frame { frame_index: number; timestamp_s: number; detection_status: string; pixel_area: number | null }
interface VideoAnalysis {
  analysis_id: string;
  input?: { original_filename?: string; experiment_id?: string | null };
  pipeline?: { pipeline_version?: string };
  result: {
    video: { fps: number; frame_count: number; duration_seconds: number; width: number | null; height: number | null };
    sampling: { sample_every_n_frames: number; frames_analyzed: number; frames_with_errors: number };
    frames: Frame[];
    temporal_summary: {
      persistence_rate: number | null;
      flicker_frequency_hz: number | null;
      flicker_status: string;
      flicker_note: string | null;
      area_change_rate_px2_per_s: { mean_abs: number | null; max_abs: number | null; pairs: number };
      tracking_note: string | null;
      method: string;
    };
  };
}

async function getJson(path: string) {
  const res = await fetch(`${API_BASE}/api/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`The Flame API answered ${res.status}.`);
  return res.json();
}

function AreaChart({ frames }: { frames: Frame[] }) {
  const pts = frames.filter((f) => f.pixel_area !== null) as (Frame & { pixel_area: number })[];
  if (pts.length < 2) return <Empty message="Too few frames with a detected flame to plot." />;
  const W = 560, H = 180, L = 52, R = 10, T = 10, B = 30;
  const t0 = pts[0].timestamp_s, t1 = pts[pts.length - 1].timestamp_s;
  const amax = Math.max(...pts.map((p) => p.pixel_area)) || 1;
  const x = (t: number) => L + ((t - t0) / (t1 - t0 || 1)) * (W - L - R);
  const y = (a: number) => T + (1 - a / amax) * (H - T - B);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Flame mask area in pixels over video time">
      {[0, 0.5, 1].map((f) => (
        <g key={f}>
          <line x1={L} x2={W - R} y1={y(f * amax)} y2={y(f * amax)} stroke="var(--border-default)" />
          <text x={L - 6} y={y(f * amax) + 4} textAnchor="end" fontSize={10} fill="var(--text-muted)">{Math.round(f * amax).toLocaleString()}</text>
        </g>
      ))}
      <polyline fill="none" stroke="#60A5FA" strokeWidth={2} points={pts.map((p) => `${x(p.timestamp_s).toFixed(1)},${y(p.pixel_area).toFixed(1)}`).join(" ")} />
      {pts.map((p) => <circle key={p.frame_index} cx={x(p.timestamp_s)} cy={y(p.pixel_area)} r={2.2} fill="#60A5FA" />)}
      <text x={L} y={H - 8} fontSize={10} fill="var(--text-muted)">{t0.toFixed(1)} s</text>
      <text x={W - R} y={H - 8} textAnchor="end" fontSize={10} fill="var(--text-muted)">{t1.toFixed(1)} s</text>
      <text x={(L + W) / 2} y={H - 8} textAnchor="middle" fontSize={11} fill="var(--text-secondary)">video time · flame area (px², measured)</text>
    </svg>
  );
}

export function VideoAnalysisPanel({ analysisId }: { analysisId?: string | null }) {
  const [analysis, setAnalysis] = useState<VideoAnalysis | null>(null);
  const [state, setState] = useState<"loading" | "empty" | "ready" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        let id = analysisId;
        if (!id) {
          const list = await getJson("analyses?status=completed&page_size=50");
          id = list.items?.find((i: { analysis_type?: string }) => i.analysis_type === "flame_video")?.analysis_id;
        }
        if (!id) { setState("empty"); return; }
        const { analysis } = await getJson(`analyses/${id}`);
        if (!analysis?.result?.temporal_summary) { setState("empty"); return; }
        setAnalysis(analysis);
        setState("ready");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not load the video analysis.");
        setState("error");
      }
    })();
  }, [analysisId]);

  return (
    <section className="rounded-2xl p-5" style={{ background: "var(--bg-card)", border: "1px solid var(--border-default)" }}>
      <h2 className="flex items-center gap-2 text-base font-semibold"><Film className="h-4 w-4" style={{ color: "var(--accent-flame)" }} aria-hidden="true" /> Video flame analysis</h2>
      <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
        Sampled frames of the video, measured in time order. Pixel units only: no temperature, and no physical size without a calibrated scale.
      </p>
      <div className="mt-4">
        {state === "loading" && <Loading label="Loading video analysis…" />}
        {state === "error" && <ErrorNote message={error} />}
        {state === "empty" && <Empty message="No completed video analysis yet. DEMO_RUNBOOK.md shows how to analyse the committed BASS-II clip." />}
        {state === "ready" && analysis && (() => {
          const r = analysis.result, s = r.temporal_summary;
          return (
            <div className="flex flex-col gap-4">
              <p className="text-xs" style={{ fontFamily: "var(--font-mono)", color: "var(--text-secondary)" }}>
                {analysis.input?.original_filename ?? analysis.analysis_id} · {r.video.width}×{r.video.height} · {r.video.fps.toFixed(1)} fps ·
                {" "}{r.video.duration_seconds.toFixed(1)} s · {r.sampling.frames_analyzed} frames analysed (every {r.sampling.sample_every_n_frames}th)
              </p>
              <AreaChart frames={r.frames} />
              <dl className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-3">
                <div className="rounded-lg p-3" style={{ background: "var(--bg-elevated)" }}>
                  <dt style={{ color: "var(--text-muted)" }}>Flame persistence</dt>
                  <dd className="mt-1 text-base font-semibold" style={{ fontFamily: "var(--font-mono)" }}>
                    {s.persistence_rate === null ? "—" : `${Math.round(s.persistence_rate * 100)}% of frames`}
                  </dd>
                </div>
                <div className="rounded-lg p-3" style={{ background: "var(--bg-elevated)" }}>
                  <dt style={{ color: "var(--text-muted)" }}>Flicker frequency</dt>
                  <dd className="mt-1 text-base font-semibold" style={{ fontFamily: "var(--font-mono)" }}>
                    {s.flicker_frequency_hz === null ? "not estimable" : `${s.flicker_frequency_hz.toFixed(2)} Hz`}
                  </dd>
                  {s.flicker_note && <dd className="mt-1" style={{ color: "var(--text-dim)" }}>{s.flicker_note}</dd>}
                </div>
                <div className="rounded-lg p-3" style={{ background: "var(--bg-elevated)" }}>
                  <dt style={{ color: "var(--text-muted)" }}>Mean |area change|</dt>
                  <dd className="mt-1 text-base font-semibold" style={{ fontFamily: "var(--font-mono)" }}>
                    {s.area_change_rate_px2_per_s.mean_abs === null ? "—" : `${Math.round(s.area_change_rate_px2_per_s.mean_abs).toLocaleString()} px²/s`}
                  </dd>
                </div>
              </dl>
              {s.tracking_note && <p className="text-xs" style={{ color: "var(--text-dim)" }}>Tracking: {s.tracking_note}</p>}
              <p className="text-[11px]" style={{ color: "var(--text-dim)" }}>Method: {s.method} · pipeline {analysis.pipeline?.pipeline_version ?? "—"}</p>
            </div>
          );
        })()}
      </div>
    </section>
  );
}
