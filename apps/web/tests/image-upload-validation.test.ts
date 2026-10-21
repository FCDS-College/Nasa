import test from "node:test";
import assert from "node:assert";
import { validateImageFile } from "../lib/api/client";

test("validateImageFile accepts valid PNG file within 10 MiB limit", async () => {
  const dummyPng = new File(["dummy png content"], "flame_01.png", {
    type: "image/png",
  });
  const result = await validateImageFile(dummyPng);
  assert.strictEqual(result.valid, true);
});

test("validateImageFile accepts valid JPEG file", async () => {
  const dummyJpg = new File(["dummy jpeg content"], "flame_02.jpg", {
    type: "image/jpeg",
  });
  const result = await validateImageFile(dummyJpg);
  assert.strictEqual(result.valid, true);
});

test("validateImageFile rejects unsupported media types per contract", async () => {
  const dummyWebp = new File(["dummy webp content"], "flame_03.webp", {
    type: "image/webp",
  });
  const result = await validateImageFile(dummyWebp);
  assert.strictEqual(result.valid, false);
  assert.match(result.error || "", /Unsupported/i);
});

test("validateImageFile rejects files exceeding the 10 MiB limit", async () => {
  const oversizedFile = {
    name: "large_flame.png",
    type: "image/png",
    size: 11 * 1024 * 1024,
  } as unknown as File;

  const result = await validateImageFile(oversizedFile);
  assert.strictEqual(result.valid, false);
  assert.match(result.error || "", /exceeds maximum allowed size/i);
});
