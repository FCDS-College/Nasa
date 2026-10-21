# Flame in Freefall — Postman API Test Suite

This directory contains ready-to-use Postman collections and environment files for testing and verifying the **Flame in Freefall** API (NASA Space Apps Challenge).

---

## 1. Directory Contents

| File | Purpose |
|---|---|
| [`Flame_in_Freefall_API.postman_collection.json`](Flame_in_Freefall_API.postman_collection.json) | The complete Postman v2.1 collection containing 16 requests across 9 functional categories. |
| [`Flame_Local.postman_environment.json`](Flame_Local.postman_environment.json) | Environment file pre-configured for local development (`http://localhost:3000` web proxy & `http://localhost:8000` backend). |
| [`Flame_Production.postman_environment.json`](Flame_Production.postman_environment.json) | Environment template for cloud or staging deployments (e.g., Railway / Docker Swarm). |

---

## 2. Quick Start: Importing into Postman

1. Open the **Postman** desktop application or web workspace.
2. Click the **Import** button in the top-left navigation panel.
3. Select and drag all three files from this directory (`Flame_in_Freefall_API.postman_collection.json`, `Flame_Local.postman_environment.json`, and `Flame_Production.postman_environment.json`).
4. In the environment dropdown (top right), select **"Flame - Local Environment"**.
5. You are ready to start calling endpoints!

---

## 3. Collection Structure & Endpoints

The collection is organized into 9 folders:

1. **`1. System & Health`**:
   - `GET /api/health` (via proxy): System-wide status, vector index latency, and database connectivity.
   - `GET /api/health` (direct backend on `:8000`).
2. **`2. Dashboard & Telemetry`**:
   - `GET /api/dashboard/counts`: Total document count, vector chunk count, and experiment run count.
3. **`3. Scientific Search & Discovery`**:
   - `GET /api/search?q={{searchQuery}}&mode=hybrid`: Combined dense and sparse retrieval.
   - `GET /api/search?q={{searchQuery}}&type=document`: Publications filter.
   - `GET /api/search?q=BASS-II&type=experiment`: Experiment records filter.
4. **`4. Document Explorer`**:
   - `GET /api/documents/{{sampleDocId}}`: NASA/NTRS technical publication metadata, authors, and abstract.
5. **`5. Experiment Matrix`**:
   - `GET /api/experiments/{{sampleExperimentId}}`: Rig conditions (fuel, oxidizer %, chamber pressure, velocity).
6. **`6. Evidence & Provenance`**:
   - `GET /api/evidence/{{sampleEvidenceId}}`: Provenance passage with SHA-256 cryptographic checksum and confidence.
7. **`7. Flame Analysis Studio`**:
   - `POST /api/analyses`: Async image upload triggering computer vision segmentation (returns `202 Accepted`).
   - `GET /api/analyses`: Paginated history of prior flame analyses.
   - `GET /api/analyses/{{sampleAnalysisId}}`: Polling endpoint for analysis status and geometry (flame area mm², aspect ratio, centroid).
   - `GET /api/analyses/{{sampleAnalysisId}}/artifacts/original`: Raw image.
   - `GET /api/analyses/{{sampleAnalysisId}}/artifacts/mask`: Binary segmentation mask PNG.
   - `GET /api/analyses/{{sampleAnalysisId}}/artifacts/overlay`: Measurement overlay image PNG.
8. **`8. Research Chat (RAG)`**:
   - `POST /api/chat`: Evidence-grounded conversational RAG query with citations.
   - `POST /api/chat`: Droplet combustion inquiry.
9. **`9. Security & Error Edge Cases`**:
   - `POST /api/chat` (> 4 KB body): Tests proxy size guardrail (asserts HTTP 400).
   - `GET /api/analyses/{invalid_id}`: Tests 404 error envelope.
   - `DELETE /api/analyses/sample`: Tests rejection of unauthorized HTTP methods on proxy.

---

## 4. Environment Variables

| Variable | Description | Local Default |
|---|---|---|
| `baseUrl` | Origin of the Next.js server proxy | `http://localhost:3000` |
| `apiOrigin` | Origin of the FastAPI backend service | `http://localhost:8000` |
| `readToken` | Bearer token for read operations | `flame_read_dev_secret_token_2026` |
| `writeToken` | Bearer token for upload / write operations | `flame_write_dev_secret_token_2026` |
| `searchQuery` | Default scientific keyword query | `microgravity flame extinction BASS` |
| `sampleDocId` | Example document identifier | `doc_ntrs_20210012345` |
| `sampleExperimentId`| Example experiment identifier | `exp_bass2_run07` |
| `sampleEvidenceId` | Example evidence identifier | `evi_01J9Z3K8V5Q2N7X4M6R1T0W8YA` |
| `sampleAnalysisId` | Example analysis ULID | `01J9Z3Q9D3F5H7K9N1R3T5W7Y9` |

---

## 5. Running via CLI (Newman)

You can run automated end-to-end regression tests using **Newman** (Postman's CLI runner):

```bash
# Install Newman if not already installed
npm install -g newman

# Run the collection against the local environment
newman run postman/Flame_in_Freefall_API.postman_collection.json \
  -e postman/Flame_Local.postman_environment.json \
  --reporters cli
```
