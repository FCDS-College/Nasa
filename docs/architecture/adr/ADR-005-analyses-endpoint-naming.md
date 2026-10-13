# ADR-005: `/api/analyses` instead of `/api/analysis/image`

- **Status:** Accepted
- **Date:** 2026-10-12 (records an MVP decision that had no ADR)
- **Deciders:** Lead; Belal (E4) and Princess (E3) affected

## Context
MVP Plan §12 named the upload endpoint `POST /api/analysis/image`. The contract shipped `POST /api/analyses`, with `GET /api/analyses`, `GET /api/analyses/{analysis_id}` and `GET /api/analyses/{analysis_id}/artifacts/{artifact_kind}`. Phase 2 Workstream A adds video.

## Decision
Keep the collection resource `/api/analyses`, with `analysis_type` in the body (`flame_image` today; `flame_video` in Workstream A). Each analysis is one resource with one history, whatever its media type.

## Alternatives considered
- `/api/analysis/image` and `/api/analysis/video` as separate verbs. This splits history and pagination by media type, and it was never implemented. Rejected.

## Consequences
- No breaking change; the frontend already uses `/api/analyses`.
- Video (A4) adds an `analysis_type` value plus any new fields, not a new path family.

## Links
`docs/api/openapi.json` (`createAnalysis`, `listAnalyses`, `getAnalysis`, `getAnalysisArtifact`); MVP Plan §12.
