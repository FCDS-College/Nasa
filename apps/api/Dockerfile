FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY apps/api /app/apps/api
COPY cv /app/cv
COPY docs/api/openapi.json /app/docs/api/openapi.json
COPY datasets/registry/source_registry.csv /app/datasets/registry/source_registry.csv
COPY datasets/metadata/files.jsonl /app/datasets/metadata/files.jsonl
WORKDIR /app/apps/api
RUN pip install '.[cv,ingestion]'

EXPOSE 8000
CMD ["uvicorn", "flame_api.main:app", "--host", "0.0.0.0", "--port", "8000"]