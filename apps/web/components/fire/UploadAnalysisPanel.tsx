"use client";

import { useEffect, useRef, useState } from "react";
import { Upload, Cpu, CheckCircle2, AlertTriangle, X } from "lucide-react";
import { submitAnalysis, fetchAnalysisStatus, UploadError } from "@/lib/api/client";

// The API's own limits (apps/api/flame_api/config.py): checked here first so a user is told at once.
const MAX_IMAGE_BYTES = 10 * 1024 * 1024;
const MAX_VIDEO_BYTES = 200 * 1024 * 1024;
const POLL_MS = 3000;
const PASSCODE_KEY = "flame.uploadPasscode";

type Phase =
  | { kind: "idle" }
  | { kind: "uploading" }
  | { kind: "running"; id: string; video: boolean; status: string; progress?: string }
  | { kind: "done"; id: string; video: boolean }
  | { kind: "error"; message: string };

function readStoredPasscode(): string {
  try {
    return window.sessionStorage.getItem(PASSCODE_KEY) ?? "";
  } catch {
    return "";
  }
}

function storePasscode(value: string | null) {
  try {
    if (value) window.sessionStorage.setItem(PASSCODE_KEY, value);
    else window.sessionStorage.removeItem(PASSCODE_KEY);
  } catch {
    /* storage blocked: the passcode is simply asked for again */
  }
}

function checkFile(file: File): string | null {
  const video = file.type.startsWith("video/");
  if (!video && file.type !== "image/png" && file.type !== "image/jpeg") {
    return "Choose a PNG or JPEG image, or a video file.";
  }
  const limit = video ? MAX_VIDEO_BYTES : MAX_IMAGE_BYTES;
  if (file.size > limit) return `This file is ${(file.size / 1048576).toFixed(1)} MB; the limit is ${limit / 1048576} MB for ${video ? "videos" : "images"}.`;
  return null;
}

/** Upload a flame image or video, wait for the CV worker, then open the result in the studio. */
export function UploadAnalysisPanel({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [passcode, setPasscode] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    queueMicrotask(() => setPasscode(readStoredPasscode()));
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  function poll(id: string, video: boolean) {
    timer.current = setTimeout(async () => {
      try {
        const s = await fetchAnalysisStatus(id);
        if (s.status === "completed") {
          setPhase({ kind: "done", id, video });
          window.location.assign(video ? `/analysis?video=${id}` : `/analysis?id=${id}`);
          return;
        }
        if (s.status === "failed" || s.status === "cancelled") {
          setPhase({ kind: "error", message: `The analysis ${s.status}${s.failure ? `: ${s.failure}` : "."}` });
          return;
        }
        setPhase({ kind: "running", id, video, status: s.status, progress: s.progress });
      } catch {
        // A dropped poll is retried; the analysis keeps running on the server either way.
      }
      poll(id, video);
    }, POLL_MS);
  }

  async function start() {
    if (!file) return;
    const problem = checkFile(file);
    if (problem) {
      setPhase({ kind: "error", message: problem });
      return;
    }
    if (!passcode.trim()) {
      setPhase({ kind: "error", message: "Enter the upload passcode." });
      return;
    }
    setPhase({ kind: "uploading" });
    try {
      const submitted = await submitAnalysis(file, passcode.trim());
      storePasscode(passcode.trim());
      const video = submitted.analysis_type === "flame_video";
      setPhase({ kind: "running", id: submitted.analysis_id, video, status: submitted.status });
      poll(submitted.analysis_id, video);
    } catch (e) {
      if (e instanceof UploadError && e.code === "UPLOAD_PASSCODE_INVALID") storePasscode(null);
      setPhase({ kind: "error", message: e instanceof Error ? e.message : "The upload failed." });
    }
  }

  const busy = phase.kind === "uploading" || phase.kind === "running" || phase.kind === "done";

  return (
    <section
      aria-labelledby="upload-title"
      className="rounded-2xl p-5 space-y-4 animate-fade-in-up"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border-default)", boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 id="upload-title" className="text-sm font-semibold flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
            <Upload className="h-4 w-4" style={{ color: "var(--accent-flame)" }} aria-hidden="true" />
            Analyse a flame image or video
          </h2>
          <p className="mt-1 text-xs" style={{ color: "var(--text-muted)" }}>
            PNG or JPEG up to 10 MB, or a video up to 200 MB. Measurements are in pixels unless a calibrated scale is known.
          </p>
        </div>
        <button onClick={onClose} disabled={phase.kind === "uploading"} aria-label="Close upload panel"
                className="rounded-lg p-1.5" style={{ color: "var(--text-muted)" }}>
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          File
          <input
            type="file"
            accept="image/png,image/jpeg,video/*"
            disabled={busy}
            onChange={(e) => { setFile(e.target.files?.[0] ?? null); setPhase({ kind: "idle" }); }}
            className="text-xs file:mr-3 file:rounded-lg file:border-0 file:px-3 file:py-1.5 file:text-xs file:font-semibold"
            style={{ color: "var(--text-primary)" }}
          />
        </label>
        <label className="flex flex-col gap-1.5 text-xs" style={{ color: "var(--text-secondary)" }}>
          Upload passcode
          <input
            type="password"
            autoComplete="off"
            value={passcode}
            disabled={busy}
            onChange={(e) => setPasscode(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") start(); }}
            className="rounded-lg px-3 py-2 text-sm"
            style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)", color: "var(--text-primary)" }}
          />
        </label>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={start}
          disabled={!file || busy}
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-50"
          style={{ background: "linear-gradient(135deg, var(--accent-flame), var(--accent-ember))", color: "#000" }}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          Upload and analyse
        </button>

        <div role="status" aria-live="polite" className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
          {phase.kind === "uploading" && (<><Cpu className="h-4 w-4 animate-spin" style={{ color: "var(--accent-flame)" }} /> Uploading…</>)}
          {phase.kind === "running" && (
            <>
              <Cpu className="h-4 w-4 animate-spin" style={{ color: "var(--accent-flame)" }} />
              {phase.status === "queued" ? "Queued for the CV worker…" : "Analysing…"}
              {phase.progress ? ` ${phase.progress}` : ""}
              <span style={{ fontFamily: "var(--font-mono)" }}>{phase.id}</span>
            </>
          )}
          {phase.kind === "done" && (<><CheckCircle2 className="h-4 w-4" style={{ color: "var(--accent-success)" }} /> Done, opening the result…</>)}
          {phase.kind === "error" && (
            <span className="flex items-center gap-2" style={{ color: "var(--accent-danger)" }}>
              <AlertTriangle className="h-4 w-4" aria-hidden="true" /> {phase.message}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}
