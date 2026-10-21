| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Belal | Approved | 0.1.0 | 2026-10-21 | M7, R1, R7 | `apps/web/tests/`, `apps/web/package.json`, `.github/workflows/ci.yml` |

# Frontend Testing & Quality Assurance Guide

This document describes the testing stack, quality validation commands, test suites, mock prevention strategies, and CI/CD automation pipeline for the **Flame in Freefall** web application.

---

## 1. Quality Assurance Stack & Tooling

The frontend testing ecosystem is designed for lightweight, high-performance execution without requiring heavyweight headless browser installations:

| Tool | Purpose | Configuration / Command |
|---|---|---|
| **Node.js Native Test Runner (`tsx --test`)** | Unit and integration test runner with TypeScript execution | `npm test` (`tsx --test tests/*.test.ts`) |
| **TypeScript Compiler (`tsc`)** | Static type checking and API contract conformance | `npm run typecheck` (`tsc --noEmit`) |
| **ESLint 9 (Flat Config)** | Code quality, React hooks rules, and architectural linting | `npm run lint` (`eslint .`) |
| **Next.js Production Compiler** | Full static page generation and bundle optimization | `npm run build` (`next build`) |
| **GitHub Actions** | Automated continuous integration release gate | `.github/workflows/ci.yml` |

---

## 2. Running Quality Checks Locally

All commands are executed from the `apps/web` directory:

```bash
cd apps/web

# 1. Run all unit and integration test suites
npm test

# 2. Run static type analysis across the entire project
npm run typecheck

# 3. Run ESLint code inspection
npm run lint

# 4. Verify Next.js production build and static export
npm run build
```

---

## 3. Test Suites & User Flows Covered

The project maintains **5 test suites** containing **17 unit and integration tests** located in `apps/web/tests/`:

### 3.1 `tests/image-upload-validation.test.ts`
- **File Type Constraints:** Validates that only `image/png` and `image/jpeg` MIME types are accepted. Rejects binary executables, plain text, and corrupt headers.
- **File Size Upper Bound:** Asserts rejection of files exceeding the 10 MB payload ceiling.
- **Resolution Boundaries:** Validates minimum dimensions (64×64 px) and maximum pixel limits (16 Megapixels) before initiating network transfer.
- **Error Propagation:** Ensures human-readable validation error messages are surfaced to the UI.

### 3.2 `tests/analysis-flow.test.ts`
- **Success Path:** Uses `global.fetch` stubs to verify that `submitFlameAnalysis` correctly parses valid OpenAPI-conforming `AnalysisRecord` responses.
- **Failure Path (Task B3, R5):** Asserts that when the upstream service returns HTTP 502 or network connection refused, the client throws/returns an error with code `UPSTREAM_UNAVAILABLE` and `retryable: true`.
- **Anti-Mock Assertion:** Explicitly verifies that no simulated analysis (such as the fake YOLOv8 14,082 px flame area) is returned when the backend fails.
- **Polling & History:** Verifies `fetchAnalysisById` and `fetchAnalyses` interact with `/api/analyses` without falling back to memory stores.

### 3.3 `tests/search-evidence-flow.test.ts`
- **Hybrid Search Flow:** Stubs `GET /api/search?q=microgravity` and validates parsing of faceted document and experiment results.
- **Evidence Provenance Drill-Down:** Stubs `GET /api/evidence/{id}` and verifies extraction of cryptographic SHA-256 hashes, source publication titles, and certainty scores.
- **Error Handling:** Asserts upstream failure produces a clean `UPSTREAM_UNAVAILABLE` error instead of synthetic placeholder documents.

### 3.4 `tests/document-viewer.test.ts`
- **Document Metadata:** Tests `fetchDocumentById` parsing of NTRS accession numbers, author lists, and section page ranges.
- **Dashboard Counts:** Tests `fetchDashboardCounts` against contract payloads (`{ documents: 142, chunks: 8500, experiments: 24 }`).
- **No Silent Fallback (Task B4):** Confirms that network failures throw authentic errors instead of swapping in `mockData.ts`.

### 3.5 `tests/chat-context.test.ts`
- **Inference Interaction (Task R2):** Stubs `POST /api/chat` and tests prompt transmission and response parsing.
- **Citation Chips:** Verifies parsing of citation metadata (`id`, `title`, `snippet`, `confidence`) attached to assistant messages.
- **Upstream Unavailable Handling:** Verifies that connection failures set error badges in the conversation thread with retry actions.
- **Payload Guardrail:** Verifies rejection of queries exceeding 4 KB.

---

## 4. Mock Prevention & Fetch Stubbing Strategy

Old tests frequently passed vacuously because the client code silently substituted mock data from `mockData.ts` whenever network calls failed.

To guarantee zero false positives, the new test suites enforce the following rules:

1. **Explicit `global.fetch` Stubs:** Tests mock `global.fetch` directly within the test harness to simulate both success contracts and upstream outages.
2. **Contract-Conforming Fixtures:** All success fixtures match the schema defined in `docs/api/openapi.json`.
3. **Dedicated Failure Scenarios:** Every test suite must contain an explicit failure test asserting that `UPSTREAM_UNAVAILABLE` is raised.
4. **No Codebase Imports of `mockData.ts`:** Production client code in `lib/api/client.ts` has zero imports of `mockData.ts`.

Example test stub pattern:
```typescript
// Testing Upstream Failure
const originalFetch = global.fetch;
global.fetch = async () => {
  return new Response(
    JSON.stringify({
      error: {
        code: "UPSTREAM_UNAVAILABLE",
        message: "Flame backend service is unreachable.",
        retryable: true
      }
    }),
    { status: 502, headers: { "Content-Type": "application/json" } }
  );
};

try {
  await client.submitFlameAnalysis(validFile);
  assert.fail("Should have thrown UPSTREAM_UNAVAILABLE");
} catch (err: any) {
  assert.strictEqual(err.code, "UPSTREAM_UNAVAILABLE");
  assert.strictEqual(err.retryable, true);
} finally {
  global.fetch = originalFetch;
}
```

---

## 5. Continuous Integration (CI) Workflow

The GitHub Actions workflow is defined in `.github/workflows/ci.yml`. It runs automatically on every pull request and push to `main` and `belal`:

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, belal]
  pull_request:
    branches: [main, belal]

jobs:
  web-checks:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/web
    steps:
      - uses: actions/checkout@v4
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: "npm"
          cache-dependency-path: apps/web/package-lock.json

      - name: Install Dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Run TypeScript Typecheck
        run: npm run typecheck

      - name: Run Unit Tests
        run: npm test

      - name: Build Next.js Production Bundle
        run: npm run build
```

---

## 6. Known Limitations

1. **End-to-End Browser Tests:** Playwright/Cypress end-to-end browser automation is scheduled for Phase 2 Week 7; current coverage focuses on TypeScript unit and integration tests with native Node.js runners.
2. **WebSocket Streaming:** Streaming token testing for live chat completion is tested via complete chunks; true streaming integration tests will be integrated when the backend streaming endpoint is stabilized.
