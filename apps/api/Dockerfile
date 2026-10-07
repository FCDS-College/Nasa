FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY apps/api /app/apps/api
COPY cv /app/cv
COPY docs/api/openapi.json /app/docs/api/openapi.json
WORKDIR /app/apps/api
RUN pip install '.[cv,ingestion]'

EXPOSE 8000
CMD ["uvicorn", "flame_api.main:app", "--host", "0.0.0.0", "--port", "8000"]