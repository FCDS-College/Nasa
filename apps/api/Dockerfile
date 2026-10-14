FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Tesseract for the OCR fallback on scanned PDF pages (M9); the `ocr` extra is its Python binding.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY apps/api /app/apps/api
COPY cv /app/cv
# Provider contracts, adapters and the router (M1 / 2H). Stdlib-only apart from optional extras.
COPY ai/providers /app/ai/providers
COPY ai/routing /app/ai/routing
# Flame's answer cache (CAG): only the cache module and the interfaces it implements.
COPY ai/interfaces.py /app/ai/interfaces.py
COPY ai/rag/__init__.py /app/ai/rag/__init__.py
COPY ai/rag/cache /app/ai/rag/cache
COPY ai/rag/retrieval/__init__.py /app/ai/rag/retrieval/__init__.py
COPY ai/rag/retrieval/fusion.py /app/ai/rag/retrieval/fusion.py
# The 3 registered NTRS reports (FF-NTRS-*) are small and committed, so they ship with the image.
COPY docs/research /app/docs/research
COPY docs/api/openapi.json /app/docs/api/openapi.json
COPY datasets/registry/source_registry.csv datasets/registry/source_registry.schema.json /app/datasets/registry/
COPY datasets/metadata/files.jsonl /app/datasets/metadata/files.jsonl
COPY datasets/samples/cv/manifest.jsonl /app/datasets/samples/cv/manifest.jsonl
WORKDIR /app/apps/api
RUN pip install '.[cv,ingestion,ocr,vector]'

EXPOSE 8000
CMD ["uvicorn", "flame_api.main:app", "--host", "0.0.0.0", "--port", "8000"]