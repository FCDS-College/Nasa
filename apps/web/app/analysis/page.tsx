"use client";

import { useState, useEffect, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchAnalysis,
  submitFlameAnalysis,
  validateImageFile,
} from "@/lib/api/client";
import { AnalysisResult, ApiErrorDetail } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import {
  Flame,
  Upload,
  Eye,
  EyeOff,
  AlertTriangle,
  Crosshair,
  BarChart2,
  Cpu,
  X,
  CheckCircle,
  FileImage,
  Sliders,
  RotateCcw,
  Sparkles,
} from "lucide-react";
import Link from "next/link";

function AnalysisStudio() {
  const searchParams = useSearchParams();
  const queryId = searchParams.get("id");

  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [showMask, setShowMask] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Upload state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageMeta, setImageMeta] = useState<{ width: number; height: number; sizeFormatted: string } | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiErrorDetail | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [isSimulatedResult, setIsSimulatedResult] = useState(false);

  // Form options
  const [experimentId, setExperimentId] = useState("01J9Z3P7C2E4G6J8M0Q2S4V6X8");
  const [enableScale, setEnableScale] = useState(false);
  const [scalePxPerMm, setScalePxPerMm] = useState("12.5");
  const [scaleSource, setScaleSource] = useState("Burner nozzle diameter (10 mm)");
  const [requestInterpretation, setRequestInterpretation] = useState(false);
  const [notes, setNotes] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const targetId = queryId || "job_8829";
    fetchAnalysis(targetId).then((res) => {
      setAnalysis(res);
      if (res.imageUrl) {
        setPreviewUrl(res.imageUrl);
      }
    });
  }, [queryId]);

  const handleFileSelect = async (file: File) => {
    setValidationError(null);
    setApiError(null);
    setUploadSuccess(false);

    // Validate using backend requirements
    const validation = await validateImageFile(file);
    if (!validation.valid) {
      setValidationError(validation.error || "Invalid image file.");
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
    setImageMeta({
      width: validation.width || 640,
      height: validation.height || 480,
      sizeFormatted: (file.size / 1024).toFixed(1) + " KB",
    });
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setValidationError("Please select a flame image first.");
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
    if (experimentId) formData.append("experiment_id", experimentId);
    if (enableScale && scalePxPerMm) {
      formData.append("scale_px_per_mm", scalePxPerMm);
      formData.append("scale_source", scaleSource);
    }
    formData.append("request_interpretation", String(requestInterpretation));
    if (notes) formData.append("notes", notes);

    const result = await submitFlameAnalysis(formData, previewUrl || undefined);
    setIsSubmitting(false);

    if (result.success && result.analysis) {
      setAnalysis(result.analysis);
      setIsSimulatedResult(Boolean(result.isSimulated));
      setUploadSuccess(true);
      setTimeout(() => {
        setIsModalOpen(false);
      }, 1200);
    } else if (result.error) {
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
            <Badge variant="default">v0.1.0 Contract</Badge>
            {isSimulatedResult && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
                    style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--accent-warning)', border: '1px solid rgba(245,158,11,0.2)' }}>
                Simulated Result (Live API Unreachable)
              </span>
            )}
          </div>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-muted)' }}>
            Submit flame imagery for deterministic computer vision segmentation, contour geometry, and physical calibration.
          </p>
        </div>

        <button
          id="upload-btn"
          type="button"
          onClick={() => setIsModalOpen(true)}
          className="flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold active:scale-95 cursor-pointer"
          style={{
            background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
            color: '#000',
            boxShadow: '0 0 16px rgba(59,130,246,0.25)',
            transition: 'all var(--transition-fast)',
          }}
        >
          <Upload className="h-4 w-4" />
          Upload & Analyze Image
        </button>
      </div>

      {/* Main Studio Display */}
      {!analysis ? (
        <div className="flex items-center gap-3 py-16" style={{ color: 'var(--text-muted)' }}>
          <Cpu className="h-5 w-5 animate-spin" style={{ color: 'var(--accent-flame)' }} />
          Loading analysis studio...
        </div>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3 animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          {/* Flame Image & Overlay Viewer */}
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
                  ID: {analysis.id}
                </span>
                <Badge variant={analysis.status === "completed" ? "success" : "default"}>
                  {analysis.status.toUpperCase()}
                </Badge>
                {analysis.filename && (
                  <span className="text-xs hidden sm:inline" style={{ color: 'var(--text-secondary)' }}>
                    {analysis.filename}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setShowMask(!showMask)}
                className="flex items-center gap-2 text-xs font-medium cursor-pointer"
                style={{ color: 'var(--text-muted)', transition: 'color var(--transition-fast)' }}
              >
                {showMask ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showMask ? "Hide Segmentation Overlay" : "Show Segmentation Overlay"}
              </button>
            </div>

            <div className="relative flex-1 flex items-center justify-center min-h-[440px] overflow-hidden"
                 style={{ background: 'rgba(0,0,0,0.2)' }}>
              {/* Background ambient lighting */}
              <div className="absolute inset-0 pointer-events-none"
                   style={{
                     background: 'radial-gradient(ellipse at center, rgba(59,130,246,0.1) 0%, transparent 75%)',
                   }} />

              {/* Flame Image Container */}
              <div className="relative max-w-full max-h-[500px] flex items-center justify-center p-4">
                {previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={previewUrl}
                    alt="Flame Image"
                    className="max-h-[400px] w-auto rounded-xl object-contain shadow-2xl"
                  />
                ) : (
                  /* Synthetic fallback flame visualization when no custom image is uploaded */
                  <div className="relative w-64 h-64 flex items-center justify-center">
                    <div className="absolute w-48 h-48 rounded-full animate-pulse-glow"
                         style={{ background: 'rgba(59,130,246,0.15)' }} />
                    <div className="absolute w-32 h-32 rounded-full"
                         style={{ background: 'rgba(251,146,60,0.25)', filter: 'blur(20px)' }} />
                    <div className="absolute w-16 h-16 rounded-full"
                         style={{ background: 'rgba(254,215,170,0.6)', filter: 'blur(8px)' }} />
                  </div>
                )}

                {/* Deterministic Segmentation Boundary Overlay */}
                {showMask && (
                  <div className="absolute inset-0 pointer-events-none flex items-center justify-center p-4">
                    <svg className="w-full h-full max-h-[400px] overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                      <path
                        d="M 50,15 C 68,15 82,32 82,50 C 82,68 68,85 50,85 C 32,85 18,68 18,50 C 18,32 32,15 50,15 Z"
                        fill="rgba(59,130,246,0.14)"
                        stroke="rgba(59,130,246,0.75)"
                        strokeWidth="1.2"
                        strokeDasharray="3 2"
                      />
                      <circle cx="50" cy="50" r="1.5" fill="var(--accent-flame)" />
                      <line x1="50" y1="46" x2="50" y2="54" stroke="var(--accent-flame)" strokeWidth="0.8" />
                      <line x1="46" y1="50" x2="54" y2="50" stroke="var(--accent-flame)" strokeWidth="0.8" />
                    </svg>
                  </div>
                )}
              </div>
            </div>

            {/* Viewer Footer Provenance */}
            <div className="flex flex-wrap items-center justify-between px-5 py-2.5 text-xs"
                 style={{ borderTop: '1px solid var(--border-subtle)', background: 'var(--border-subtle)' }}>
              <span style={{ color: 'var(--text-muted)' }}>
                Measurement Space: <code className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>original_oriented_px</code>
              </span>
              <div className="flex items-center gap-3">
                <Link
                  href="/history"
                  className="inline-flex items-center gap-1.5 text-xs font-medium"
                  style={{ color: 'var(--accent-flame)' }}
                >
                  View in History →
                </Link>
              </div>
            </div>
          </div>

          {/* Measurements & Pipeline Metadata Sidebar */}
          <div className="space-y-5">
            {/* Deterministic Measurements */}
            <div className="rounded-2xl p-5 space-y-4"
                 style={{
                   background: 'var(--bg-card)',
                   border: '1px solid var(--border-default)',
                   boxShadow: 'var(--shadow-card)',
                 }}>
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold flex items-center gap-2"
                    style={{ color: 'var(--text-primary)' }}>
                  <BarChart2 className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                  Flame Measurements
                </h3>
                <span className="text-[10px] uppercase font-bold tracking-wider" style={{ color: 'var(--text-dim)' }}>
                  Units Established
                </span>
              </div>

              <div className="space-y-3">
                {analysis.measurements.map((m, idx) => (
                  <div key={idx} className="rounded-xl p-3.5"
                       style={{
                         background: 'var(--border-subtle)',
                         border: '1px solid var(--border-subtle)',
                       }}>
                    <div className="flex justify-between items-start mb-1.5">
                      <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                        {m.name}
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider"
                            style={{
                              background: m.observation_type === 'measured'
                                ? 'rgba(16,185,129,0.08)'
                                : 'rgba(59,130,246,0.08)',
                              color: m.observation_type === 'measured'
                                ? 'var(--accent-success)'
                                : 'var(--accent-flame)',
                              border: `1px solid ${m.observation_type === 'measured'
                                ? 'rgba(16,185,129,0.15)'
                                : 'rgba(59,130,246,0.15)'}`,
                            }}>
                        {m.observation_type}
                      </span>
                    </div>
                    <div className="flex items-end justify-between">
                      <div style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}
                           className="text-lg font-bold">
                        {m.value.toLocaleString()}{" "}
                        <span className="text-xs font-normal" style={{ color: 'var(--text-dim)' }}>
                          {m.unit}
                        </span>
                      </div>
                      <div className="text-[11px]" style={{ color: 'var(--text-dim)' }}>
                        {(m.confidence * 100).toFixed(0)}% conf
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Pipeline Provenance */}
            <div className="rounded-2xl p-5 space-y-3"
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
              <div className="space-y-2 text-xs" style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                {[
                  ["CV Model", analysis.model_version],
                  ["Preprocessing", analysis.preprocessing_version],
                  ["Calibration", analysis.calibration_state],
                  ["Pipeline", analysis.pipeline_version],
                ].map(([label, value], idx) => (
                  <div key={idx} className="flex justify-between pb-1.5"
                       style={{ borderBottom: idx < 3 ? '1px solid var(--border-subtle)' : 'none' }}>
                    <span>{label}:</span>
                    <span style={{
                      color: label === "Calibration" && value === "uncalibrated"
                        ? 'var(--accent-warning)'
                        : 'var(--text-secondary)'
                    }}>
                      {String(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Scientific Warnings & Limitations */}
            {analysis.warnings.length > 0 && (
              <div className="rounded-2xl p-4 space-y-2"
                   style={{
                     background: 'rgba(239,68,68,0.04)',
                     border: '1px solid rgba(239,68,68,0.18)',
                   }}>
                <h3 className="text-xs font-bold uppercase tracking-[0.12em] flex items-center gap-1.5"
                    style={{ color: 'var(--accent-danger)' }}>
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Scientific Warnings
                </h3>
                <ul className="list-disc list-inside text-xs space-y-1"
                    style={{ color: 'rgba(239,68,68,0.8)' }}>
                  {analysis.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upload & Parameter Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-md animate-fade-in-up">
          <div
            className="relative w-full max-w-2xl rounded-2xl p-6 overflow-y-auto max-h-[90vh]"
            style={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border-default)',
              boxShadow: 'var(--shadow-glow-md)',
            }}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4"
                 style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg"
                     style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <Upload className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                </div>
                <div>
                  <h2 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                    Upload Flame Image
                  </h2>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    POST /api/analyses (PNG or JPEG, ≤ 10 MiB, ≥ 64×64 px)
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="p-1 rounded-lg text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-5 space-y-5">
              {/* Dropzone */}
              <div
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className="relative flex flex-col items-center justify-center rounded-xl p-6 text-center cursor-pointer border-2 border-dashed transition-all"
                style={{
                  background: selectedFile ? 'rgba(59,130,246,0.03)' : 'var(--border-subtle)',
                  borderColor: selectedFile ? 'rgba(59,130,246,0.4)' : 'var(--border-default)',
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/png,image/jpeg"
                  className="hidden"
                  onChange={onFileInputChange}
                />

                {previewUrl ? (
                  <div className="flex flex-col items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={previewUrl}
                      alt="Preview"
                      className="max-h-40 rounded-lg object-contain shadow-md"
                    />
                    <div className="flex items-center gap-2 text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                      <FileImage className="h-4 w-4" style={{ color: 'var(--accent-flame)' }} />
                      <span>{selectedFile?.name}</span>
                      {imageMeta && (
                        <span style={{ color: 'var(--text-dim)' }}>
                          ({imageMeta.width}×{imageMeta.height}px, {imageMeta.sizeFormatted})
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] underline" style={{ color: 'var(--accent-flame)' }}>
                      Click to choose a different image
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-2">
                    <Upload className="h-8 w-8 mb-1" style={{ color: 'var(--accent-flame)' }} />
                    <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                      Drag and drop flame image here, or click to browse
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      Supports PNG and JPEG formats up to 10 MiB
                    </p>
                  </div>
                )}
              </div>

              {/* Validation or API Errors */}
              {validationError && (
                <div className="rounded-xl p-3 flex items-start gap-2.5 text-xs"
                     style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: 'var(--accent-danger)' }}>
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-bold">Validation Error: </span>
                    {validationError}
                  </div>
                </div>
              )}

              {apiError && (
                <div className="rounded-xl p-3.5 space-y-2 text-xs"
                     style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: 'var(--accent-danger)' }}>
                  <div className="flex items-center gap-2 font-bold">
                    <AlertTriangle className="h-4 w-4" />
                    <span>API Error: {apiError.code}</span>
                  </div>
                  <p>{apiError.message}</p>
                  {apiError.field_errors && apiError.field_errors.length > 0 && (
                    <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                      {apiError.field_errors.map((fe, i) => (
                        <li key={i}>
                          <strong>{fe.field}:</strong> {fe.message}
                        </li>
                      ))}
                    </ul>
                  )}
                  {apiError.retryable && (
                    <div className="text-[10px] text-zinc-400">
                      Request ID: {apiError.request_id} • This error is retryable.
                    </div>
                  )}
                </div>
              )}

              {uploadSuccess && (
                <div className="rounded-xl p-3 flex items-center gap-2 text-xs"
                     style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.25)', color: 'var(--accent-success)' }}>
                  <CheckCircle className="h-4 w-4 shrink-0" />
                  <span>Analysis complete! Loading measurements into studio...</span>
                </div>
              )}

              {/* Calibration & Experiment Controls */}
              <div className="space-y-4 pt-2">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Experiment Selection */}
                  <div>
                    <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                      Associated Experiment
                    </label>
                    <select
                      value={experimentId}
                      onChange={(e) => setExperimentId(e.target.value)}
                      className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none"
                      style={{
                        background: 'var(--border-subtle)',
                        border: '1px solid var(--border-default)',
                        color: 'var(--text-primary)',
                      }}
                    >
                      <option value="01J9Z3P7C2E4G6J8M0Q2S4V6X8">BASS-II (Burning & Suppression of Solids - II)</option>
                      <option value="01J9Z3P8D3F5H7K9N1R3T5W7Y9">FLEX (Flame Extinction Experiment)</option>
                      <option value="">None / Standalone Test</option>
                    </select>
                  </div>

                  {/* Interpretation Request */}
                  <div className="flex flex-col justify-end">
                    <label className="flex items-center gap-2 text-xs cursor-pointer p-2 rounded-lg"
                           style={{ background: 'var(--border-subtle)' }}>
                      <input
                        type="checkbox"
                        checked={requestInterpretation}
                        onChange={(e) => setRequestInterpretation(e.target.checked)}
                        className="rounded"
                      />
                      <span style={{ color: 'var(--text-primary)' }}>Request AURA AI Interpretation</span>
                    </label>
                  </div>
                </div>

                {/* Spatial Calibration Toggle */}
                <div className="rounded-xl p-4 space-y-3"
                     style={{ background: 'var(--border-subtle)', border: '1px solid var(--border-subtle)' }}>
                  <div className="flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs font-semibold cursor-pointer"
                           style={{ color: 'var(--text-primary)' }}>
                      <input
                        type="checkbox"
                        checked={enableScale}
                        onChange={(e) => setEnableScale(e.target.checked)}
                        className="rounded"
                      />
                      <Sliders className="h-3.5 w-3.5" style={{ color: 'var(--accent-flame)' }} />
                      Provide Spatial Calibration (Enables mm / mm² units)
                    </label>
                    <span className="text-[10px]" style={{ color: 'var(--text-dim)' }}>
                      Data Dictionary §4
                    </span>
                  </div>

                  {enableScale && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                      <div>
                        <label className="block text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
                          Scale (pixels per mm):
                        </label>
                        <input
                          type="number"
                          step="0.1"
                          min="0.1"
                          value={scalePxPerMm}
                          onChange={(e) => setScalePxPerMm(e.target.value)}
                          placeholder="e.g. 12.5"
                          className="w-full rounded-lg px-3 py-1.5 text-xs font-mono focus:outline-none"
                          style={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border-default)',
                            color: 'var(--text-primary)',
                          }}
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] mb-1" style={{ color: 'var(--text-muted)' }}>
                          Scale Source / Reference:
                        </label>
                        <input
                          type="text"
                          value={scaleSource}
                          onChange={(e) => setScaleSource(e.target.value)}
                          placeholder="e.g. Known nozzle diameter 10mm"
                          className="w-full rounded-lg px-3 py-1.5 text-xs focus:outline-none"
                          style={{
                            background: 'var(--bg-card)',
                            border: '1px solid var(--border-default)',
                            color: 'var(--text-primary)',
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Notes */}
                <div>
                  <label className="block text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>
                    Analysis Notes (optional)
                  </label>
                  <input
                    type="text"
                    maxLength={2000}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="e.g. Test frame at t=2.4s after ignition"
                    className="w-full rounded-lg px-3 py-2 text-xs focus:outline-none"
                    style={{
                      background: 'var(--border-subtle)',
                      border: '1px solid var(--border-default)',
                      color: 'var(--text-primary)',
                    }}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-4"
                   style={{ borderTop: '1px solid var(--border-subtle)' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="rounded-xl px-4 py-2 text-xs font-semibold"
                  style={{ color: 'var(--text-muted)' }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!selectedFile || isSubmitting}
                  className="flex items-center gap-2 rounded-xl px-6 py-2.5 text-xs font-semibold active:scale-95 disabled:opacity-50 cursor-pointer"
                  style={{
                    background: 'linear-gradient(135deg, var(--accent-flame), var(--accent-ember))',
                    color: '#000',
                  }}
                >
                  {isSubmitting ? (
                    <>
                      <RotateCcw className="h-3.5 w-3.5 animate-spin" />
                      Running Deterministic Analysis...
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-3.5 w-3.5" />
                      Start Analysis (202 Queued)
                    </>
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
      <AnalysisStudio />
    </Suspense>
  );
}
