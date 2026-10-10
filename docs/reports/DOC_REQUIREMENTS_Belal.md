# Documentation Requirements: Belal (Engineer 4, Frontend / Visualization)

| | |
|---|---|
| **Phase** | Phase 2: Advanced Scientific Intelligence Platform |
| **Issued** | 2026-10-10 by the Lead (Anas) |
| **Your branch** | `Belal` (branch fresh from `main` for each task) |
| **Basis** | [Phase 2 Plan](https://github.com/FCDS-College/Nasa/blob/main/docs/plan/PHASE2_PLAN.md): §2 carry-over item **M7**, **Workstream B** (Admin Dashboard), the §10 Admin modules, plus the graph exploration and video workspace UIs; **Sub-phase 2H, Task 8** (Phase 2 Plan §7A); MVP Plan §5.11, §13, §23 |
| **Reviewers** | Lead (Anas) for every document. Eman (E1) for citation and evidence presentation. Princess (E3) for overlay and measurement views. Ziad (E5) for evaluation and ranking views. |

---

## 1. Why this matters

The UI is where a scientist decides whether to trust a result, so every screen must show where its data comes from and how certain it is. The audit on 2026-10-10 found several gaps:
- Eight screens call the real API, but **Knowledge Explorer still returns `mockKnowledge`**.
- There is no document list or viewer, and there are no frontend tests.
- `docs/frontend/implementation-summary.md` describes behavior the code no longer has or never had: an automatic mock fallback and YOLOv8 results.

Phase 2 adds the Admin Dashboard, which includes destructive operations, so its flows and permissions must be specified before they are built.

## 2. Rules for every document you write

1. **Location and format:** Markdown at the path given in §3, **in English**. Team documents must be readable by every reviewer; an Arabic summary at the end is optional.
2. **Header block:** start every document with the table below.

   | Owner | Status | Version | Last updated | Plan items | Code paths |
   |---|---|---|---|---|---|
   | Belal | Draft / In review / Approved | 0.1.0 | YYYY-MM-DD | e.g. M7, B4 | e.g. `apps/web/app/knowledge/` |

3. **Evidence over claims:** every "screen works" statement names the endpoint it calls and links a test or a screenshot taken against the real API, with the date and the API commit. **Never describe mock data as real behavior.**
4. **Docs ship with code:** a PR that adds or changes a screen, API call or component updates E4-2 (screen inventory) in the same PR.
5. **Contract alignment:** the TypeScript types in `apps/web/lib/api/types.ts` must match `docs/api/openapi.json`. Document how they are kept in sync (generated or checked).
6. **Scientific display rules:** follow E4-3. Units, uncertainty, version IDs and the *observed / measured / estimated / inferred / hypothesized* labels are first-class UI elements. Never colour a hypothesis like a measurement.
7. **Limitations:** every document ends with **Known limitations**.
8. **Safety:** no API tokens or `.env` values in docs or screenshots. Blur any token in browser devtools captures.
9. **Diagrams and images:** Mermaid or ASCII for flows. Screenshots go in `docs/frontend/img/`, compressed (under 300 KB each).

## 3. Required documents

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E4-1 | Frontend architecture | `docs/frontend/architecture.md` (replaces `implementation-summary.md`) | M7, §13 | Week 1 |
| E4-2 | Screen inventory and API mapping | `docs/frontend/screens.md` | M7, B1 | Week 1, then updated every week |
| E4-3 | Scientific UI guidelines | `docs/frontend/scientific-ui-guidelines.md` | §13 rules | Week 2 |
| E4-4 | Admin Dashboard specification | `docs/frontend/admin-dashboard.md` | Workstream B, §10 | Week 2 (spec), Week 7 (as built) |
| E4-5 | Component library reference | `docs/frontend/components.md` | §13 | Week 3 |
| E4-6 | Frontend testing guide | `docs/frontend/testing.md` | M7, release gate | Week 3 |
| E4-7 | Graph exploration and video workspace UX | `docs/frontend/graph-and-video-ux.md` | B4, A4 | Week 5 |
| E4-8 | Accessibility and responsive report | `docs/frontend/accessibility.md` | Integrated release | Week 7 |
| E4-9 | Demo script (UI part) | `docs/frontend/demo-script.md` | MVP §23, Phase 2 release | Week 8 |

## 4. Required contents

### E4-1 Frontend architecture
- App Router structure, data-fetching approach, and the API proxy route `apps/web/app/api/[...path]/route.ts` (what it forwards, how auth headers are added, and that tokens never reach the browser).
- `lib/api/client.ts`: error handling, loading/empty/error states, retries.
- Environment variables (names and purpose only, no values) and how the Railway deployment sets them.
- State management (`ChatContext.tsx`), and what is client-side only versus server-backed (e.g. chat history vs. session MAG from M5).
- An explicit statement of where mock data is still used, removed once M7 is done.

### E4-2 Screen inventory and API mapping
One row per screen (dashboard, chat, search, evidence, experiments, analysis, history, status, knowledge, plus every Admin module). For each row give:
- the route, the endpoints called, and the fields displayed;
- loading, empty and error states, and the role required;
- the test file;
- a **data source column** with the value *real API* or *mock*. The target is no mock rows by the end of Week 3.

### E4-3 Scientific UI guidelines
- Visual treatment for each label class, with colour, icon and text so meaning never relies on colour alone.
- How units, aggregation windows, uncertainty, evidence IDs and model/corpus/pipeline versions are shown.
- The claim → evidence → document → page/section → source drill-down pattern (MVP §5.11).
- Cache-hit, memory-used and evidence-insufficient indicators (from M4 and M5).
- Contradictory-evidence display: show both sides, never hide one.

### E4-4 Admin Dashboard specification
For each of the 10 modules in Phase 2 §10:
- the purpose, the data shown, the backend endpoints (agree with the Lead), and the role required (read vs write);
- **destructive-action flows** (reprocess, merge entities, rebuild index, promote model): the confirmation step, the reason prompt, and the audit record created;
- original vs corrected value display for metadata corrections (B3);
- a wireframe (Mermaid, ASCII or an image) for each module.

### E4-5 Component library reference
Each shared component (`components/ui/*`, `components/layout/*` and new ones): its props, variants, usage example, and accessibility notes (keyboard, ARIA, focus).

### E4-6 Frontend testing guide
- The test stack, how to run it locally and in CI, and the commands.
- Which user flows are covered end-to-end (search → evidence drill-down, chat with citations, image upload → overlay, admin retry).
- How tests run against a seeded API versus fixtures, and the rule that fixtures must match the OpenAPI schema.

### E4-7 Graph exploration and video workspace UX
- Graph view: node and edge types shown, provenance on hover/click, conflict highlighting, limits for large neighbourhoods.
- Video workspace: timeline, frame scrubbing, overlay toggle, temporal charts with units and aggregation windows, and how "not estimable" metrics are displayed.

### E4-8 Accessibility and responsive report
WCAG 2.2 AA checklist results per screen, keyboard-only walkthrough results, contrast checks, and breakpoints tested. List open issues with owners.

### E4-9 Demo script (UI part)
The click path for the final demo, with the expected screen state at each step, plus fallback steps if a service is down (from the MVP §23 demo flow, extended with the video, graph and admin steps).

## 5. Existing documents to fix

| File | Problem found in the 2026-10-10 audit | Action |
|---|---|---|
| `docs/frontend/implementation-summary.md` | Arabic only; claims an automatic mock fallback and YOLOv8 segmentation, neither of which matches the code | Replace with E4-1 (English) and mark the old file superseded, or delete it |
| `docs/api/FRONTEND_API_CONTRACT.md` | May drift from `lib/api/types.ts` and `openapi.json` | Check it against both and document the sync method (E4-1) |
| `apps/web/lib/api/client.ts` (`fetchKnowledge`) | Returns `mockKnowledge` | Document it in E4-2 as *mock* until it is replaced (M7) |
| `apps/web/README.md` | Default template content | Rewrite it with setup, environment variables (names only), commands and links to E4 docs |
| `apps/web/AGENTS.md`, `apps/web/CLAUDE.md` | Tool-instruction files mixed with project docs | Keep them, but make sure `README.md` is the human entry point |

## 6. Recurring documentation

- **Weekly note**, `docs/reports/WEEKLY_Belal.md` (append a section each week): screens finished (with PR links and screenshots), mock rows remaining, blockers on API endpoints, and which documents changed.
- **PR description:** the screens affected, before/after screenshots, the documents updated, and the tests run.

## 7. Acceptance checklist (the Lead checks this before approving)

- [ ] Every document in §3 exists at its path, in English, with the header block and a changelog.
- [ ] E4-2 lists every screen, with no *mock* rows after Week 3.
- [ ] Every Admin destructive action has a confirmation and audit flow in E4-4.
- [ ] The scientific UI rules in E4-3 are applied on every screen that shows results.
- [ ] `implementation-summary.md` is replaced.
- [ ] Known limitations are stated in every document.

---

## 8. Sub-phase 2H: Hybrid AI Execution (added 2026-10-10)

The Phase 2 Plan now includes **Sub-phase 2H (§7A)**: Flame must keep working when the internet, cloud models or external AI services are unavailable. It has three execution modes: **Cloud-Preferred Hybrid**, **Local-First** and **Offline-Only**. The Lead owns the backend; **you own Task 8: the offline-aware frontend** (P1). Write the spec in Week 4; the as-built version is due in Week 7.

### 8.1 Additional required document

| ID | Document | Path | Covers | Due (Phase 2 week) |
|---|---|---|---|---|
| E4-10 | Offline-aware UX specification | `docs/frontend/offline-ux.md` | 2H Task 8 | Week 4 (spec), Week 7 (as built) |

**E4-10 must contain:**
- **Indicators**, each with its data source from the Lead's API contracts (H-4) and where it appears:
  - current mode;
  - internet connectivity;
  - cloud provider availability and local model availability;
  - the active model and execution provider;
  - local processing progress, and queued and failed jobs;
  - synchronization status;
  - limitations that affect the current result.
- **A screen × mode availability matrix:** for each screen, what still works in each of the three modes.
- **Exact UI text for degraded states:**
  - external search unavailable vs local retrieval failed;
  - task exceeds local resources;
  - capability missing or corrupt;
  - answer may be out of date since the last sync.
- A per-response **local vs remote** badge, showing provider, model and fallback used.
- **UX rules:**
  - never block the whole UI because a cloud provider is down;
  - never imply live external data while offline;
  - long jobs survive closing the browser tab.
- **Self-hosted fonts:** `apps/web/app/layout.tsx` currently loads Google Fonts at runtime. Document the fix, plus any other runtime request from the frontend to an external domain (there should be none in Offline-Only mode).

### 8.2 Updates to your existing documents

| Document | Add |
|---|---|
| E4-2 Screen inventory | A **"Works offline?"** column per screen |
| E4-4 Admin Dashboard | Execution-mode control in "Models and LLMs" (role, confirmation, audit record); connectivity and provider status in "Overview"; sync status in "System Operations" |
| E4-3 Scientific UI guidelines | How local vs remote generation and sync age are displayed |
| E4-6 Testing guide | UI tests for the offline states, run against a backend in Offline-Only mode |

### 8.3 Sign-offs you give

You review the Lead's **H-4** (provider API contracts and execution metadata) for every field the UI needs.

### 8.4 Acceptance (added to §7)

- [ ] E4-10 exists.
- [ ] With the backend in Offline-Only mode, users can see the mode and which operations still work.
- [ ] The browser makes no requests to external domains.
