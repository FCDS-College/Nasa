# ai/

Evidence-first research intelligence. **Owner:** Engineer 1, with the Lead for deployment and router integration. **Status:** not started.

Planned sub-folders (MVP plan §14): `orchestration/`, `prompts/`, `context/`, `routing/`, `rag/`, `cag/`, `mag/`, `providers/`.

Rules:
- Answers cite only retrieved evidence IDs. When the evidence is inadequate, the system abstains.
- Application code depends on provider-neutral interfaces (Ollama/vLLM sit behind `providers/`).
- Memory is never treated as scientific evidence.
