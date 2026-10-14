# CPU Ollama for Railway (private network only; never give this service a public domain).
# The model is pulled on first start into the mounted volume, then reused across deploys.
FROM ollama/ollama:0.5.7

ENV OLLAMA_HOST=[::]:11434 \
    OLLAMA_KEEP_ALIVE=30m \
    OLLAMA_NUM_PARALLEL=1 \
    FLAME_OLLAMA_MODEL=qwen2.5:3b-instruct-q4_K_M

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
