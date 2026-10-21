import test from "node:test";
import assert from "node:assert";
import { searchResearch, fetchEvidence, fetchAnalysesHistory } from "../lib/api/client";

const originalFetch = global.fetch;

test("searchResearch - success path with contract data stub", async () => {
  const mockSearchResult = {
    meta: { request_id: "req_search_test" },
    retrieval: { mode: "hybrid", knowledge_version: "2026-10-05" },
    pagination: { page: 1, page_size: 20, total_items: 1, total_pages: 1 },
    results: [
      {
        result_id: "res_001",
        result_type: "document",
        score: 0.88,
        title: "BASS-II Solid Fuel Extinction",
        snippet: "Extinction occurred at low flow velocities...",
        evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
        source: {
          repository: "NASA PSI",
          source_id: "FF-PSI-25",
          short_name: "BASS-II",
          access_url: "https://psi.nasa.gov/",
        },
      },
    ],
  };

  global.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/search")) {
      return new Response(JSON.stringify(mockSearchResult), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const results = await searchResearch("extinction", { domain: "combustion" });
    assert.strictEqual(results.request_id, "req_search_test");
    assert.strictEqual(results.results.length, 1);
    assert.strictEqual(results.results[0].title, "BASS-II Solid Fuel Extinction");
    assert.strictEqual(results.results[0].evidence_id, "01J9Z3N5B8C1E3G5J7M9P1R3T5");
  } finally {
    global.fetch = originalFetch;
  }
});

test("searchResearch - failure path throws without returning mock data", async () => {
  global.fetch = async () => {
    return new Response(
      JSON.stringify({
        error: {
          code: "UPSTREAM_UNAVAILABLE",
          message: "The Flame API could not be reached.",
        },
      }),
      { status: 502, headers: { "Content-Type": "application/json" } }
    );
  };

  try {
    await assert.rejects(async () => {
      await searchResearch("microgravity");
    }, (err: any) => {
      assert.strictEqual(err.code, "UPSTREAM_UNAVAILABLE");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("fetchEvidence - success path with contract data stub", async () => {
  const mockEvidenceData = {
    evidence: {
      evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
      kind: "measured",
      origin: "experiment_condition",
      excerpt: "Peak flame temperature recorded at 1350 K",
      review_status: "verified",
      source: {
        source_id: "FF-PSI-25",
        short_name: "BASS-II",
        repository: "NASA PSI",
      },
      file: {
        file_id: "f_001",
        sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        original_filename: "BASS_table.csv",
        size_bytes: 4096,
      },
    },
  };

  global.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/evidence/01J9Z3N5B8C1E3G5J7M9P1R3T5")) {
      return new Response(JSON.stringify(mockEvidenceData), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const evidence = await fetchEvidence("01J9Z3N5B8C1E3G5J7M9P1R3T5");
    assert.ok(evidence);
    assert.strictEqual(evidence?.id, "01J9Z3N5B8C1E3G5J7M9P1R3T5");
    assert.strictEqual(evidence?.kind, "measured");
    assert.strictEqual(evidence?.citation, "BASS-II");
  } finally {
    global.fetch = originalFetch;
  }
});

test("fetchEvidence rejects malformed or path traversal IDs safely", async () => {
  const invalidId = "../../../etc/passwd";
  const result = await fetchEvidence(invalidId);
  assert.strictEqual(result, null, "Malformed IDs must be rejected safely without throwing");
});

test("fetchAnalysesHistory - success and failure paths", async () => {
  global.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/analyses?page_size=50")) {
      return new Response(
        JSON.stringify({
          items: [
            {
              analysis_id: "01J9Z3P7C2E4G6J8M0Q2S4V6X8",
              original_filename: "test.png",
              status: "completed",
              flame_area_px: 12000,
              calibration_state: "uncalibrated",
              created_at: new Date().toISOString(),
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const history = await fetchAnalysesHistory();
    assert.strictEqual(history.length, 1);
    assert.strictEqual(history[0].analysis_id, "01J9Z3P7C2E4G6J8M0Q2S4V6X8");
  } finally {
    global.fetch = originalFetch;
  }

  // Failure path returns empty array (never localAnalysesStore mock)
  global.fetch = async () => {
    throw new Error("Network error");
  };

  try {
    const history = await fetchAnalysesHistory();
    assert.deepStrictEqual(history, []);
  } finally {
    global.fetch = originalFetch;
  }
});
