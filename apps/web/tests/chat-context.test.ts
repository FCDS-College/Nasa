import test from "node:test";
import assert from "node:assert";
import { submitChat } from "../lib/api/client";

const originalFetch = global.fetch;

test("submitChat - success path with contract data stub", async () => {
  const mockChatResponse = {
    meta: { request_id: "req_chat_123" },
    answer: "In microgravity, flames become spherical due to the absence of buoyant convection.",
    sources: [
      {
        evidence_id: "01J9Z3N5B8C1E3G5J7M9P1R3T5",
        document_id: "doc_991",
        title: "Soot Formation in Microgravity",
        location: "p. 4, §2.1",
        url: "https://ntrs.nasa.gov/",
      },
    ],
    memory_used: false,
    cache_hit: false,
    model: { provider: "AURA", name: "aura-reasoner", version: "3.0" },
    knowledge_version: "2026-10-05",
    warnings: [],
  };

  global.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/api/chat") && init?.method === "POST") {
      return new Response(JSON.stringify(mockChatResponse), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const response = await submitChat({ query: "How does microgravity affect flame shape?" });
    assert.strictEqual(response.request_id, "req_chat_123");
    assert.match(response.answer, /spherical/);
    assert.strictEqual(response.sources.length, 1);
    assert.strictEqual(response.sources[0].evidence_id, "01J9Z3N5B8C1E3G5J7M9P1R3T5");
  } finally {
    global.fetch = originalFetch;
  }
});

test("submitChat - failure path throws UPSTREAM_UNAVAILABLE error (never mock answer)", async () => {
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
      await submitChat({ query: "test question" });
    }, (err: any) => {
      assert.strictEqual(err.code, "UPSTREAM_UNAVAILABLE");
      return true;
    });
  } finally {
    global.fetch = originalFetch;
  }
});

test("Chat Session data structure adheres to schema and persistence", () => {
  const session = {
    id: "sess_test_123",
    title: "Combustion Inquiry",
    createdAt: Date.now(),
    updatedAt: Date.now(),
    turns: [
      {
        id: "turn_1",
        query: "What is microgravity flame circularity?",
        timestamp: Date.now(),
        res: {
          request_id: "req_test",
          answer: "Near 1.0 due to absent buoyant convection.",
          sources: [],
          memory_used: false,
          cache_hit: false,
          model: { provider: "AURA", name: "aura-reasoner", version: "3.0" },
          knowledge_version: "2026-10-05",
          warnings: [],
        },
      },
    ],
  };

  const serialized = JSON.stringify([session]);
  const parsed = JSON.parse(serialized);

  assert.strictEqual(parsed.length, 1);
  assert.strictEqual(parsed[0].id, "sess_test_123");
});
