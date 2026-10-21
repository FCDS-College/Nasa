import test from "node:test";
import assert from "node:assert";
import { submitFlameAnalysis, fetchAnalysis } from "../lib/api/client";

const originalFetch = global.fetch;

test("submitFlameAnalysis - success path with contract data stub", async () => {
  const mockAnalysisRecord = {
    analysis_id: "01J9Z3P7C2E4G6J8M0Q2S4V6X8",
    status: "completed",
    pipeline_version: "v1.2.0-baseline",
    input: {
      original_filename: "iss_flame_test.png",
      calibration: { state: "spatial_scale_provided" },
    },
    pipeline: {
      pipeline_version: "v1.2.0-baseline",
      detector: { name: "OtsuContours", version: "1.0" },
    },
    result: {
      measurements: {
        geometry_px: {
          area: { value: 14082, unit: "px²", classification: "measured", confidence: 0.95 },
        },
        geometry_physical: {
          area: { value: 90.1, unit: "mm²", classification: "estimated", confidence: 0.92 },
        },
      },
    },
    warnings: [],
    created_at: new Date().toISOString(),
  };

  // Stub fetch for POST /api/analyses
  global.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/analyses") && init?.method === "POST") {
      return new Response(JSON.stringify({ analysis: mockAnalysisRecord }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/api/analyses/01J9Z3P7C2E4G6J8M0Q2S4V6X8")) {
      return new Response(JSON.stringify({ analysis: mockAnalysisRecord }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const dummyFile = new File(["dummy png binary stream"], "iss_flame_test.png", {
      type: "image/png",
    });
    const formData = new FormData();
    formData.append("image", dummyFile);
    formData.append("scale_px_per_mm", "12.5");
    formData.append("scale_source", "Burner rim 10mm");

    const result = await submitFlameAnalysis(formData);
    assert.strictEqual(result.success, true, "Submission must succeed with contract stub");
    assert.strictEqual(result.analysisId, "01J9Z3P7C2E4G6J8M0Q2S4V6X8");
    assert.strictEqual(result.analysis?.status, "completed");

    // Fetch detail
    const detail = await fetchAnalysis("01J9Z3P7C2E4G6J8M0Q2S4V6X8");
    assert.ok(detail, "Detail must be parsed");
    assert.strictEqual(detail?.id, "01J9Z3P7C2E4G6J8M0Q2S4V6X8");
    assert.strictEqual(detail?.status, "completed");
    assert.ok(detail?.measurements.length && detail.measurements.length > 0);
  } finally {
    global.fetch = originalFetch;
  }
});

test("submitFlameAnalysis - failure path returns UPSTREAM_UNAVAILABLE (Task B3)", async () => {
  // Stub fetch to simulate upstream connection failure
  global.fetch = async () => {
    throw new Error("Connection refused to upstream Flame API");
  };

  try {
    const dummyFile = new File(["dummy png binary stream"], "iss_flame_test.png", {
      type: "image/png",
    });
    const formData = new FormData();
    formData.append("image", dummyFile);

    const result = await submitFlameAnalysis(formData);

    // Assert that NO fake/simulated completed result is returned!
    assert.strictEqual(result.success, false, "Must fail honestly when API is unreachable");
    assert.strictEqual(result.analysis, undefined, "Must NOT fabricate a simulated analysis");
    assert.strictEqual(result.error?.code, "UPSTREAM_UNAVAILABLE", "Must return UPSTREAM_UNAVAILABLE error code");
    assert.strictEqual(result.error?.retryable, true, "Failure must be marked retryable");
  } finally {
    global.fetch = originalFetch;
  }
});
