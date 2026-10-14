import test from "node:test";
import assert from "node:assert";
import { searchResearch, fetchEvidence, fetchAnalysesHistory } from "../lib/api/client";

test("searchResearch returns filtered combustion results", async () => {
  const query = "microgravity";
  const results = await searchResearch(query, { domain: "combustion" });

  assert.ok(results.results, "Results array must be defined");
  assert.ok(results.pagination, "Pagination metadata must be defined");
  assert.strictEqual(results.retrieval.mode, "hybrid");
  assert.ok(results.results.length > 0, "Should return at least one result");

  const firstHit = results.results[0];
  assert.ok(firstHit.result_id, "Result ID must be present");
  assert.ok(firstHit.title, "Title must be present");
  assert.ok(firstHit.evidence_id, "Evidence ID must be linked");
});

test("fetchEvidence validates ID format and returns structured evidence record", async () => {
  const validId = "01J9Z3N5B8C1E3G5J7M9P1R3T5";
  const evidence = await fetchEvidence(validId);

  assert.ok(evidence, "Evidence must be returned for valid ID");
  assert.strictEqual(evidence.id, validId);
  assert.strictEqual(evidence.review_status, "verified");
  assert.ok(evidence.excerpt, "Excerpt quote must be present");
  assert.ok(evidence.file?.sha256, "Cryptographic file sha256 must be established");
  assert.ok(evidence.locator?.label, "Locator must identify page/section");
});

test("fetchEvidence rejects malformed or potentially malicious IDs", async () => {
  const invalidId = "../../../etc/passwd";
  const result = await fetchEvidence(invalidId);
  assert.strictEqual(result, null, "Malformed IDs must be rejected safely without throwing");
});

test("fetchAnalysesHistory returns valid history summaries with units", async () => {
  const history = await fetchAnalysesHistory();
  assert.ok(Array.isArray(history), "History must be an array");
  assert.ok(history.length > 0, "History should contain baseline records");

  const entry = history[0];
  assert.ok(entry.analysis_id, "analysis_id required");
  assert.ok(entry.original_filename, "original_filename required");
  assert.ok(entry.calibration_state, "calibration_state required");
});
