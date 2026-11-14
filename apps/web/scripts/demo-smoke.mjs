// End-to-end demo smoke test: walks the judge journey in a real browser against a running stack.
//
//   node apps/web/scripts/demo-smoke.mjs [http://localhost:3000] [screenshot-dir]
//
// Needs Playwright with Chromium (`npx playwright install chromium` once). Exits non-zero on any failed
// step, browser console error or failed /api/ request. Screenshots are written when a directory is given.
import { createRequire } from "node:module";

// require() also resolves a globally installed Playwright (NODE_PATH), which ESM imports do not.
const { chromium } = createRequire(import.meta.url)("playwright");

const BASE = (process.argv[2] ?? "http://localhost:3000").replace(/\/$/, "");
const SHOTS = process.argv[3];
const failures = [];

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await context.newPage();
// "Failed to load resource" console lines duplicate the response check below, which knows the URL and lets
// the documented 503 CHAT_UNAVAILABLE (no language model deployed; the UI falls back to evidence) through.
page.on("console", (m) => {
  if (m.type() === "error" && !m.text().startsWith("Failed to load resource")) failures.push(`console: ${m.text()}`);
});
page.on("pageerror", (e) => failures.push(`page error: ${e.message}`));
page.on("response", (r) => {
  if (r.url().includes("/api/") && r.status() >= 400 && !r.url().endsWith("/api/chat")) failures.push(`HTTP ${r.status()} ${r.url()}`);
});

async function step(name, fn) {
  const started = Date.now();
  try {
    await fn();
    if (SHOTS) await page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: true });
    console.log(`PASS ${name} (${Date.now() - started} ms)`);
  } catch (e) {
    failures.push(`${name}: ${e.message.split("\n")[0]}`);
    console.log(`FAIL ${name}: ${e.message.split("\n")[0]}`);
  }
}

const visible = (text, timeout = 20000) => page.getByText(text, { exact: false }).first().waitFor({ timeout });

await step("01-dashboard", async () => {
  await page.goto(`${BASE}/`);
  await visible("Ranked investigations");
  await visible("FLEX · Flame Extinguishment Experiment");
  await visible("Lower oxygen, more self-extinguishing droplet flames");
  // ISS air first: the system solves (pitch order: success before refusal).
  // The count comes from the ingested data (ai/fire_safety/investigations.py headline), so match any count.
  await visible(/of the \d+ flight tests lie near this atmosphere/);
});

await step("02-lunar-scenario", async () => {
  await page.getByRole("radio", { name: /Lunar lander/ }).click();
  await visible("scenario pressure 62.7 kPa is outside the tested range");
  await visible("Solid-material burns and enriched oxygen");
});

// Apollo 1 (ADR-013): the system knows when not to answer, says why, and shows where data does exist.
await step("02b-apollo1-refusal", async () => {
  await page.getByRole("radio", { name: /Apollo 1/ }).click();
  await visible(/None of the \d+ flight tests cover this atmosphere\./);
  await visible("this scenario is at 1 g (Earth)");
  await page.locator('[data-verdict="none"]').waitFor();
  await page.locator('[data-testid="sweep-out-of-domain"]').first().waitFor();   // red zone out to 100% O2
  await page.locator('[data-testid="history-timeline"] li').nth(5).waitFor();    // at least 6 cited events
  const uncited = await page.locator('[data-testid="history-timeline"] li').evaluateAll(
    (items) => items.filter((li) => !li.querySelector('a[href^="https://ntrs.nasa.gov/"], a[href^="/evidence?id="]')).length);
  if (uncited) throw new Error(`${uncited} timeline event(s) without a source link`);
  await visible("extremely hazardous");
  await page.locator('[data-testid="history-alternative"]').waitFor();
});

await step("02c-apollo1-alternative", async () => {
  await page.getByRole("button", { name: /Show the flight data for/ }).click();
  await page.locator('[data-verdict="covered"]').waitFor({ timeout: 20000 });
  await page.getByRole("radio", { name: /Orion/, checked: true }).waitFor();
  await visible("Outcome model estimate for this atmosphere");
});

await step("03-investigation", async () => {
  await page.getByRole("link", { name: /FLEX · Flame Extinguishment Experiment/ }).first().click();
  await visible("Summary, in NASA's words");
  await visible("Objective");
});

await step("04-evidence", async () => {
  await page.getByRole("link", { name: "source" }).first().click();
  await page.waitForURL(/\/evidence\?id=/);
  await visible("FLEX");
});

await step("05-explorer", async () => {
  await page.goto(`${BASE}/explorer`);
  await visible("Most similar real flight tests");
  await visible("Inside the flight-tested domain");
  await page.getByRole("button", { name: /Lunar lander/ }).click();
  await visible("No estimate: these conditions were never flown");
  await page.getByRole("button", { name: /Apollo 1 pad/ }).click();
  await visible("O₂ mole fraction 1 is outside the flight-tested range");
});

await step("06-chat", async () => {
  await page.goto(`${BASE}/chat?q=${encodeURIComponent("How does oxygen concentration affect flame spread in exploration atmospheres?")}`);
  const box = page.locator("textarea, input[type=text]").last();
  await box.waitFor();
  await page.waitForFunction(() => [...document.querySelectorAll("textarea, input[type=text]")].some((el) => el.value.length > 10));
  await box.press("Enter");
  await page.locator('a[href^="/evidence?id="]').first().waitFor({ timeout: 180000 });
});

await step("07-analysis-video", async () => {
  await page.goto(`${BASE}/analysis`);
  await visible("Video flame analysis");
  await visible("Flame persistence");
});

await step("08-knowledge-graph", async () => {
  await page.goto(`${BASE}/knowledge`);
  await page.getByRole("button", { name: /^FLEX/ }).first().click();
  await visible("is part of");
  // FLEX -> one of its flight tests -> the outcome that test ended in, then two hops to the fuels burned.
  await page.getByRole("button", { name: "Outcomes" }).click();
  await page.getByRole("button", { name: /^Extinction/ }).first().click();
  await page.getByRole("button", { name: "2", exact: true }).click();
  await page.getByRole("button", { name: "ended in" }).click();
  await page.getByRole("button", { name: "burned" }).click();
  await page.getByRole("button", { name: /^Show all/ }).first().click();   // the "burned" group comes first
  await visible("Heptane");
  await visible("Methanol");
});

await step("09-status", async () => {
  await page.goto(`${BASE}/status`);
  await visible("database");
});

await browser.close();
if (failures.length) {
  console.log(`\n${failures.length} problem(s):\n- ${failures.join("\n- ")}`);
  process.exit(1);
}
console.log("\nDemo journey passed.");
