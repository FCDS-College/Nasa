import test from "node:test";
import assert from "node:assert";
import { fetchDocuments, fetchDocument } from "../lib/api/client";

test("fetchDocuments returns registered P0 NTRS documents with cryptographic checksums", async () => {
  const docs = await fetchDocuments();

  assert.ok(Array.isArray(docs), "Must return array of DocumentRecord");
  assert.ok(docs.length >= 3, "P0 corpus must include the 3 registered NTRS technical publications");

  const tm2000 = docs.find((d) => d.identifier === "NASA/TM-2000-209773");
  assert.ok(tm2000, "NASA/TM-2000-209773 must be present in corpus");
  assert.strictEqual(tm2000?.document_type, "technical_report");
  assert.strictEqual(
    tm2000?.file?.sha256,
    "dc531270ffb646b26503955afb0c1df7bcc47482bbfed4a3d6b922de9629520d",
    "Real SHA-256 digest of 20000034017.pdf must match exactly"
  );
  assert.strictEqual(tm2000?.text_layer, "full");
});

test("fetchDocument retrieves individual document by ULID", async () => {
  const docId = "01J9Z3M2A7D4F6H8K0N2Q4S6T8";
  const doc = await fetchDocument(docId);

  assert.ok(doc, "Document should be found for valid ID");
  assert.strictEqual(doc?.document_id, docId);
  assert.ok(doc?.source.access_url, "Official NTRS landing URL must be present");
});
