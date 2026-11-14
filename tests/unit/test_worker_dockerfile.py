"""apps/api/Dockerfile.worker must stay the API image with only the start command swapped.

Railway ignores railway.json on `railway up` uploads, so flame-worker gets its RQ start command
from its own Dockerfile (RAILWAY_DOCKERFILE_PATH=apps/api/Dockerfile.worker). A dependency or COPY
added to one file and not the other would ship a worker that cannot import what the API enqueues.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API = ROOT / "apps" / "api" / "Dockerfile"
WORKER = ROOT / "apps" / "api" / "Dockerfile.worker"


def _instructions(path: Path) -> list[str]:
    """Non-comment, non-blank lines; continuation lines kept as they are."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_worker_dockerfile_matches_api_except_cmd():
    api, worker = _instructions(API), _instructions(WORKER)
    assert api[-1].startswith("CMD ") and worker[-1].startswith("CMD ")
    assert worker[:-1] == api[:-1], "Dockerfile.worker drifted from apps/api/Dockerfile"


def test_worker_cmd_recovers_then_runs_rq_on_the_analysis_queue():
    cmd = _instructions(WORKER)[-1]
    assert "python -m flame_api.worker recover" in cmd
    assert "exec rq worker" in cmd
    assert "$FLAME_REDIS_URL" in cmd
    assert cmd.rstrip('"]').endswith("flame-analysis")
