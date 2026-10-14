#!/bin/sh
set -eu
export OLLAMA_HOST_CLIENT="127.0.0.1:11434"

# Ollama sizes its thread pool from the HOST's cores (it logged threads=48), but a container only gets
# its cgroup CPU allowance. Oversubscribing a throttled container makes generation crawl, so pin the
# thread count to the real allowance (override with OLLAMA_NUM_THREAD).
threads="${OLLAMA_NUM_THREAD:-}"
if [ -z "$threads" ] && [ -r /sys/fs/cgroup/cpu.max ]; then
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [ "${quota:-max}" != "max" ] && [ "${period:-0}" -gt 0 ]; then
    threads=$(( (quota + period - 1) / period ))
  fi
fi
[ -n "$threads" ] || threads=$(nproc)
[ "$threads" -le 8 ] || threads=8
echo "flame-ollama: cpu.max=$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo n/a) nproc=$(nproc) -> num_thread=$threads"

ollama serve &
server=$!
until OLLAMA_HOST="$OLLAMA_HOST_CLIENT" ollama list >/dev/null 2>&1; do sleep 1; done
if ! OLLAMA_HOST="$OLLAMA_HOST_CLIENT" ollama list | grep -q "^$FLAME_OLLAMA_MODEL"; then
  OLLAMA_HOST="$OLLAMA_HOST_CLIENT" ollama pull "$FLAME_OLLAMA_MODEL"
fi
# Re-create the same tag with the thread count baked in so Flame's model name does not change.
printf 'FROM %s\nPARAMETER num_thread %s\n' "$FLAME_OLLAMA_MODEL" "$threads" > /tmp/Modelfile
OLLAMA_HOST="$OLLAMA_HOST_CLIENT" ollama create "$FLAME_OLLAMA_MODEL" -f /tmp/Modelfile
wait "$server"
