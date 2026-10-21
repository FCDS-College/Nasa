"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchAnalysis,
  submitFlameAnalysis,
  validateImageFile,
  artifactUrl,
} from "@/lib/api/client";
import { AnalysisResult, ApiErrorDetail } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  Flame,
  Upload,
  Eye,
  EyeOff,
  AlertTriangle,
  BarChart2,
  Cpu,
  X,
  FileImage,
  Sliders,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";

function AnalysisStudioContent() {
  const searchParams = useSearchParams();
  const queryId = searchParams.get("id");

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showMask, setShowMask] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Upload modal state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{ width: number; height: number; sizeFormatted: string } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiErrorDetail | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Calibration parameters
  const [experimentId, setExperimentId] = useState("");
  const [enableScale, setEnableScale] = useState(false);
  const [scalePxPerMm, setScalePxPerMm] = useState("12.5");
  const [scaleSource, setScaleSource] = useState("Burner nozzle diameter (10 mm)");
  const [requestInterpretation, setRequestInterpretation] = useState(false);
  const [notes, setNotes] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadCurrentAnalysis = async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const res = await fetchAnalysis(queryId || undefined);
      setAnalysis(res);
    } catch (err: any) {
      setLoadError(err?.message || "Failed to load analysis from Flame API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCurrentAnalysis();
  }, [queryId]);

  const handleFileSelect = async (file: File) => {
    setValidationError(null);
    setApiError(null);

    const validation = await validateImageFile(file);
    if (!validation.valid) {
      setValidationError(validation.error || "Invalid image file.");
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    setImageMeta({
      width: validation.dimensions?.width || 640,
      height: validation.dimensions?.height || 480,
      sizeFormatted: (file.size / 1024).toFixed(1) + " KB",
    });
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!selectedFile) {
      setValidationError("Please select a valid flame image first.");
      return;
    }

    if (enableScale && !scaleSource.trim()) {
      setValidationError("Spatial calibration source description is required when scale is provided.");
      return;
    }

    setIsSubmitting(true);
    setApiError(null);

    const formData = new FormData();
    formData.append("image", selectedFile);
    if (experimentId.trim()) formData.append("experiment_id", experimentId.trim());
    if (enableScale && scalePxPerMm) {
      formData.append("scale_px_per_mm", scalePxPerMm);
      formData.append("scale_source", scaleSource);
    }
    formData.append("request_interpretation", String(requestInterpretation));
    if (notes.trim()) formData.append("notes", notes.trim());

    const result = await submitFlameAnalysis(formData);
    setIsSubmitting(false);

    if (result.success && result.analysis) {
      setAnalysis(result.analysis);
      setIsModalOpen(false);
      setPreviewUrl(null);
      setSelectedFile(null);
    } else if (result.error) {
      // Contract Error state (Task B3: NEVER fabricate a simulated result)
      setApiError(result.error);
    }
  };

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
                <Flame className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
              </div>
              Flame Analysis Studio
            </h1>
            <Badge variant="default">OpenAPI 3.1 Contract</Badge>
          </div>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Submit microgravity flame imagery for deterministic computer vision segmentation, contour geometry, and calibrated physical measurements.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            id="upload-btn"
            type="button"
            onClick={() => setIsModalOpen(true)}
            className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold cursor-pointer active:scale-95 transition-all"
            style={{
              background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
              color: '#000',
              boxShadow: '0 0 16px rgba(59,130,246,0.25)',
            }}
          >
            <Upload className="h-4 w-4" />
            Upload Flame Image
          </button>
          <Link
            href="/history"
            className="rounded-xl px-4 py-2.5 text-sm font-medium transition-all"
            style={{
              background: 'var(--border-subtle)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
            }}
          >
            History
          </Link>
        </div>
      </div>

      {/* Main Studio Area */}
      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center text-center">
          <Cpu className="h-8 w-8 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          <p className="mt-3 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
            Connecting to Flame CV worker and retrieving analysis records...
          </p>
        </div>
      ) : loadError ? (
        <div className="rounded-2xl p-6 text-center space-y-3"
             style={{ background: 'rgba(239,68,68,0.05)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--accent-danger)' }}>
          <AlertTriangle className="h-8 w-8 mx-auto" />
          <h3 className="font-bold text-base">Analysis Service Unavailable</h3>
          <p className="text-xs max-w-md mx-auto" style={{ color: 'var(--text-secondary)' }}>
            {loadError}
          </p>
          <button
            onClick={loadCurrentAnalysis}
            className="mt-2 rounded-lg px-4 py-1.5 text-xs font-semibold cursor-pointer"
            style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--accent-danger)', border: '1px solid rgba(239,68,68,0.3)' }}
          >
            Retry
          </button>
        </div>
      ) : !analysis ? (
        <div className="rounded-2xl p-12 text-center space-y-4"
             style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl mx-auto"
               style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid var(--border-subtle)' }}>
            <Flame className="h-8 w-8" style={{ color: 'var(--accent-flame)', opacity: 0.8 }} />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">No Analyses Recorded Yet</h3>
            <p className="text-xs mt-1 max-w-md mx-auto" style={{ color: 'var(--text-muted)' }}>
              No completed flame analyses found. Upload a flame image from BASS-II or FLEX experiments to initiate computer vision processing.
            </p>
          </div>
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold cursor-pointer"
            style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)', border: '1px solid rgba(59,130,246,0.25)' }}
          >
            <Upload className="h-3.5 w-3.5" />
            Upload First Image
          </button>
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 animate-fade-in-up">
          {/* Visual Overlay / Image Box */}
          <div className="lg:col-span-2 rounded-2xl overflow-hidden flex flex-col"
               style={{
                 background: 'var(--bg-card)',
                 border: '1px solid var(--border-default)',
                 boxShadow: 'var(--shadow-card)',
               }}>
            <div className="flex items-center justify-between px-5 py-3.5"
                 style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-3">
                <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                  ID: {analysis.id}
                </span>
                <Badge variant={analysis.status === "completed" ? "success" : analysis.status === "failed" ? "danger" : "default"}>
                  {analysis.status.toUpperCase()}
                </Badge>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded"
                      style={{ background: 'var(--border-subtle)', color: 'var(--text-secondary)' }}>
                  Calibration: {analysis.calibration_state}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowMask(!showMask)}
                className="flex items-center gap-2 text-xs font-medium cursor-pointer"
                style={{ color: 'var(--text-muted)' }}
              >
                {showMask ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showMask ? "Hide Segmentation Overlay" : "Show Segmentation Overlay"}
              </button>
            </div>

            <div className="relative flex-1 flex items-center justify-center min-h-[420px] p-4 overflow-hidden"
                 style={{ background: 'rgba(0,0,0,0.15)' }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={artifactUrl(analysis.id, showMask ? "overlay" : "original")}
                alt={showMask ? "Flame segmentation overlay" : "Original flame capture"}
                className="max-h-[500px] w-full object-contain rounded-lg"
              />
            </div>

            <div className="p-4 flex flex-wrap items-center justify-between gap-3 text-xs"
                 style={{ borderTop: '1px solid var(--border-subtle)', background: 'rgba(0,0,0,0.05)' }}>
              <div className="flex items-center gap-4 text-[11px] font-mono" style={{ color: 'var(--text-dim)' }}>
                <span>Pipeline: {analysis.pipeline_version}</span>
                <span>Detector: {analysis.model_version}</span>
              </div>
              <div className="flex items-center gap-2">
                <a
                  href={artifactUrl(analysis.id, "mask")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] underline"
                  style={{ color: 'var(--accent-flame)' }}
                >
                  Download Binary Mask
                </a>
                <span style={{ color: 'var(--text-dim)' }}>•</span>
                <a
                  href={artifactUrl(analysis.id, "original")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[11px] underline"
                  style={{ color: 'var(--accent-flame)' }}
                >
                  Download Original
                </a>
              </div>
            </div>
          </div>

          {/* Measurements & Physics Table */}
          <div className="space-y-6">
            <div className="rounded-2xl p-6 space-y-4"
                 style={{
                   background: 'var(--bg-card)',
                   border: '1px solid var(--border-default)',
                   boxShadow: 'var(--shadow-card)',
                 }}>
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                  <BarChart2 className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                  Extracted Geometry & Physics
                </h3>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded"
                      style={{ background: 'var(--border-subtle)', color: 'var(--accent-flame)' }}>
                  Deterministic
                </span>
              </div>

              {analysis.measurements.length === 0 ? (
                <p className="text-xs py-4 text-center" style={{ color: 'var(--text-muted)' }}>
                  No quantitative measurements extracted from this frame.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {analysis.measurements.map((m, idx) => (
                    <div key={idx} className="flex items-center justify-between rounded-xl p-3"
                         style={{ background: 'var(--border-subtle)' }}>
                      <div>
                        <div className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                          {m.name}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded"
                                style={{
                                  background: m.observation_type === 'measured' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                                  color: m.observation_type === 'measured' ? 'var(--accent-success)' : 'var(--accent-warning)',
                                }}>
                            {m.observation_type}
                          </span>
                          {m.confidence != null && (
                            <span className="text-[10px] font-mono" style={{ color: 'var(--text-dim)' }}>
                              Conf: {(m.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-bold font-mono" style={{ color: 'var(--accent-flame)' }}>
                          {m.value.toFixed(2)}
                        </div>
                        <div className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                          {m.unit}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Calibration / Radiometric Warnings */}
              {analysis.warnings && analysis.warnings.length > 0 && (
                <div className="rounded-xl p-3.5 space-y-1.5"
                     style={{ background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }}>
                  <div className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: 'var(--accent-warning)' }}>
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Physical Calibration Warnings
                  </div>
                  {analysis.warnings.map((w, idx) => (
                    <p key={idx} className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                      • {w}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Upload & Calibration Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="relative w-full max-w-xl rounded-2xl overflow-hidden shadow-2xl animate-fade-in-up"
               style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}>
            <div className="flex items-center justify-between p-5" style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg"
                     style={{ background: 'rgba(59,130,246,0.1)', color: 'var(--accent-flame)' }}>
                  <Upload className="h-4 w-4" />
                </div>
                <h3 className="font-bold text-base text-white">Upload Flame Image for CV Analysis</h3>
              </div>
              <button
                type="button"
                onClick={() => { setIsModalOpen(false); setApiError(null); setValidationError(null); }}
                className="p-1 rounded-lg text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              {/* File Dropzone */}
              <div>
                <label className="block text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                  Select Image File (PNG or JPEG, max 10MB)
                </label>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  className="rounded-xl p-6 border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all"
                  style={{
                    borderColor: selectedFile ? 'var(--accent-flame)' : 'var(--border-subtle)',
                    background: selectedFile ? 'rgba(59,130,246,0.03)' : 'var(--border-subtle)',
                  }}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg"
                    className="hidden"
                    onChange={onFileInputChange}
                  />
                  <FileImage className="h-8 w-8 mb-2" style={{ color: selectedFile ? 'var(--accent-flame)' : 'var(--text-dim)' }} />
                  <span className="text-xs font-medium text-white">
                    {selectedFile ? selectedFile.name : "Click to select flame image"}
                  </span>
                  {imageMeta && (
                    <span className="text-[10px] mt-1 font-mono" style={{ color: 'var(--text-dim)' }}>
                      {imageMeta.width}x{imageMeta.height} px • {imageMeta.sizeFormatted}
                    </span>
                  )}
                </div>
              </div>

              {/* Spatial Calibration Section */}
              <div className="rounded-xl p-4 space-y-3" style={{ background: 'var(--border-subtle)' }}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sliders className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                    <span className="text-xs font-semibold text-white">Physical Spatial Scale (Optional)</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={enableScale}
                    onChange={(e) => setEnableScale(e.target.checked)}
                    className="rounded cursor-pointer"
                  />
                </div>

                {enableScale && (
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div>
                      <label className="text-[11px] block font-medium" style={{ color: 'var(--text-muted)' }}>
                        Scale (px / mm)
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        value={scalePxPerMm}
                        onChange={(e) => setScalePxPerMm(e.target.value)}
                        className="w-full rounded-lg px-2.5 py-1.5 text-xs font-mono mt-1"
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: '#fff' }}
                      />
                    </div>
                    <div>
                      <label className="text-[11px] block font-medium" style={{ color: 'var(--text-muted)' }}>
                        Scale Source
                      </label>
                      <input
                        type="text"
                        value={scaleSource}
                        onChange={(e) => setScaleSource(e.target.value)}
                        placeholder="e.g. Burner diameter"
                        className="w-full rounded-lg px-2.5 py-1.5 text-xs mt-1"
                        style={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', color: '#fff' }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Error Alert Box (Task B3: Error on upstream failure with Retry button) */}
              {validationError && (
                <div className="rounded-xl p-3 text-xs flex items-center gap-2"
                     style={{ background: 'rgba(239,68,68,0.1)', color: 'var(--accent-danger)', border: '1px solid rgba(239,68,68,0.25)' }}>
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>{validationError}</span>
                </div>
              )}

              {apiError && (
                <div className="rounded-xl p-4 space-y-2 text-xs"
                     style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: 'var(--accent-danger)' }}>
                  <div className="flex items-center justify-between font-bold">
                    <span className="flex items-center gap-1.5">
                      <AlertTriangle className="h-4 w-4" />
                      Upload Failed ({apiError.code})
                    </span>
                    {apiError.retryable && (
                      <span className="text-[10px] px-2 py-0.5 rounded font-mono" style={{ background: 'rgba(239,68,68,0.2)' }}>
                        Retryable
                      </span>
                    )}
                  </div>
                  <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                    {apiError.message}
                  </p>
                  <div className="pt-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleSubmit()}
                      className="rounded-lg px-3 py-1.5 text-xs font-semibold cursor-pointer active:scale-95"
                      style={{ background: 'var(--accent-danger)', color: '#fff' }}
                    >
                      Retry Upload
                    </button>
                  </div>
                </div>
              )}

              {/* Modal Actions */}
              <div className="flex items-center justify-end gap-3 pt-3" style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-xs font-medium cursor-pointer"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !selectedFile}
                  className="flex items-center gap-2 rounded-xl px-5 py-2 text-xs font-semibold cursor-pointer disabled:opacity-50"
                  style={{
                    background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
                    color: '#000',
                  }}
                >
                  {isSubmitting ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      Processing on Worker...
                    </>
                  ) : (
                    "Submit for Analysis"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<div className="p-8 text-zinc-400">Loading analysis studio...</div>}>
      <AnalysisStudioContent />
    </Suspense>
  );
}
