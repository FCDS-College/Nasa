import test from "node:test";
import assert from "node:assert";
import { fetchDocuments, fetchDocument } from "../lib/api/client";

const originalFetch = global.fetch;

test("fetchDocuments - success path with contract data stub", async () => {
  global.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/search") && url.includes("type=document")) {
      return new Response(
        JSON.stringify({
          results: [
            {
              result_id: "doc_tm2000",
              title: "NASA/TM-2000-209773: Microgravity Combustion Synthesis",
              snippet: "Experimental results aboard the KC-135...",
              source: {
                source_id: "FF-NTRS-01",
                short_name: "NASA Glenn",
                repository: "NASA NTRS",
                access_url: "https://ntrs.nasa.gov/citations/20000034017",
              },
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      );
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const docs = await fetchDocuments();
    assert.strictEqual(docs.length, 1);
    assert.strictEqual(docs[0].document_id, "doc_tm2000");
    assert.strictEqual(docs[0].source.repository, "NASA NTRS");
  } finally {
    global.fetch = originalFetch;
  }
});

test("fetchDocuments - failure path returns empty array (never mockDocuments fallback)", async () => {
  global.fetch = async () => {
    throw new Error("Upstream unavailable");
  };

  try {
    const docs = await fetchDocuments();
    assert.deepStrictEqual(docs, []);
  } finally {
    global.fetch = originalFetch;
  }
});

test("fetchDocument - individual document success and not found paths", async () => {
  const mockDoc = {
    document: {
      document_id: "01J9Z3M2A7D4F6H8K0N2Q4S6T8",
      title: "Droplet Combustion in Microgravity",
      document_type: "paper",
      source: {
        source_id: "FF-PSI-69",
        title: "FLEX Investigation",
        repository: "NASA PSI",
        access_url: "https://psi.nasa.gov/",
      },
    },
  };

  global.fetch = async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("/api/documents/01J9Z3M2A7D4F6H8K0N2Q4S6T8")) {
      return new Response(JSON.stringify(mockDoc), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify({ error: { code: "NOT_FOUND" } }), { status: 404 });
  };

  try {
    const doc = await fetchDocument("01J9Z3M2A7D4F6H8K0N2Q4S6T8");
    assert.ok(doc);
    assert.strictEqual(doc?.document_id, "01J9Z3M2A7D4F6H8K0N2Q4S6T8");

    const missing = await fetchDocument("01J9Z3M2A7D4F6H8K0N2Q4S699");
    assert.strictEqual(missing, null);
  } finally {
    global.fetch = originalFetch;
  }
});
