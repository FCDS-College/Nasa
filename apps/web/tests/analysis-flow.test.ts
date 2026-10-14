import test from "node:test";
import assert from "node:assert";
import { submitFlameAnalysis, fetchAnalysis } from "../lib/api/client";

test("submitFlameAnalysis builds correct payload and processes analysis", async () => {
  const dummyFile = new File(["dummy png binary stream"], "iss_flame_test.png", {
    type: "image/png",
  });

  const formData = new FormData();
  formData.append("image", dummyFile);
  formData.append("experiment_id", "01J9Z3P7C2E4G6J8M0Q2S4V6X8");
  formData.append("scale_px_per_mm", "15.0");
  formData.append("scale_source", "Burner rim 10mm");
  formData.append("request_interpretation", "false");

  const result = await submitFlameAnalysis(formData, "blob:preview-123");

  assert.strictEqual(result.success, true, "Analysis submission must succeed");
  assert.ok(result.analysisId, "Must return an analysis ID");
  assert.ok(result.analysis, "Analysis object must be populated");
  assert.strictEqual(result.analysis?.status, "completed");
  assert.strictEqual(result.analysis?.filename, "iss_flame_test.png");

  // Verify calibrated measurements
  const areaMeasurement = result.analysis?.measurements.find((m) =>
    m.name.includes("Area")
  );
  assert.ok(areaMeasurement, "Must contain area measurement");
  assert.strictEqual(areaMeasurement?.unit, "mm²", "Calibrated image must have mm² units");
  assert.strictEqual(areaMeasurement?.observation_type, "estimated");

  // Verify retrieval of the created analysis
  const retrieved = await fetchAnalysis(result.analysisId!);
  assert.strictEqual(retrieved.id, result.analysisId);
});
