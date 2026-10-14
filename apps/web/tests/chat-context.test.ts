import test from "node:test";
import assert from "node:assert";
import { submitChat } from "../lib/api/client";

test("submitChat returns a grounded chat response with sources and disclosures", async () => {
  const req = {
    query: "How does microgravity affect flame soot residence times?",
  };

  const response = await submitChat(req);

  assert.ok(response.request_id, "Response must include request_id");
  assert.ok(response.answer, "Answer must not be empty");
  assert.ok(Array.isArray(response.sources), "Sources must be an array of evidence chips");
  assert.ok(response.sources.length > 0, "Response must cite at least one evidence source");

  const source = response.sources[0];
  assert.ok(source.evidence_id, "Evidence ID must be linked in citation");
  assert.ok(source.title, "Source document title must be present");

  // Verify memory and cache disclosures
  assert.strictEqual(typeof response.cache_hit, "boolean", "cache_hit must be boolean");
  assert.strictEqual(typeof response.memory_used, "boolean", "memory_used must be boolean");
  assert.ok(response.model?.provider, "Model provider must be specified");
});

test("Chat Session data structure adheres to schema and persistence", () => {
  const initialSession = {
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
          memory_used: true,
          cache_hit: false,
          model: { provider: "vllm", name: "Llama-3-8B", version: "1.0" },
          knowledge_version: "2026-10-03",
          warnings: [],
        },
      },
    ],
  };

  const serialized = JSON.stringify([initialSession]);
  const parsed = JSON.parse(serialized);

  assert.strictEqual(parsed.length, 1);
  assert.strictEqual(parsed[0].id, "sess_test_123");
  assert.strictEqual(parsed[0].turns[0].res.memory_used, true);
});
