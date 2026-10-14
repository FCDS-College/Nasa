import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from cv.flame_cv import main as flame_main
from cv.utils.verify_offline_env import verify_manifest, write_checksums

REPO = Path(__file__).resolve().parents[2]
SCHEMA = REPO / "cv" / "contracts" / "video_analysis_result.schema.json"
FIXTURE = Path(__file__).parent / "fixtures" / "video_analysis_result.example.json"


def make_repo(tmp_path, with_optional=False, sha=None):
    (tmp_path / "cv" / "configs").mkdir(parents=True)
    (tmp_path / "cv" / "weights" / "offline_packages").mkdir(parents=True)
    (tmp_path / "cv" / "mod.py").write_text("x" * 50)
    asset = {"name": "Mod", "path": "cv/mod.py", "minSizeBytes": 10}
    if sha:
        asset["sha256"] = sha
    manifest = {
        "manifestVersion": "1.1.0",
        "requiredAssets": [asset],
        "optionalAssets": [{"name": "Opt", "path": "cv/opt.py", "minSizeBytes": 10}],
        "offlinePackages": {"directory": "cv/weights/offline_packages", "checksumFile": "cv/configs/pkgs.sha256"},
    }
    path = tmp_path / "cv" / "configs" / "m.json"
    path.write_text(json.dumps(manifest))
    return path


def test_repo_manifest_passes():
    assert verify_manifest(REPO / "cv" / "configs" / "offline_manifest.json")


def test_missing_optional_asset_only_warns(tmp_path):
    assert verify_manifest(make_repo(tmp_path))


def test_missing_required_asset_fails(tmp_path):
    manifest = make_repo(tmp_path)
    (tmp_path / "cv" / "mod.py").unlink()
    assert not verify_manifest(manifest)


def test_wrong_checksum_fails(tmp_path):
    assert not verify_manifest(make_repo(tmp_path, sha="0" * 64))


def test_package_checksums_roundtrip(tmp_path):
    manifest = make_repo(tmp_path)
    wheel = tmp_path / "cv" / "weights" / "offline_packages" / "a.whl"
    wheel.write_bytes(b"wheel")
    assert not verify_manifest(manifest, check_packages=True)
    assert write_checksums(manifest)
    assert verify_manifest(manifest, check_packages=True)
    wheel.write_bytes(b"tampered")
    assert not verify_manifest(manifest, check_packages=True)


def test_flame_cv_cli_synthetic(tmp_path, capsys):
    assert flame_main(["--out-dir", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "SUCCESS"
    assert (tmp_path / "analysis_result.json").exists()


def test_flame_cv_cli_missing_image_returns_error(tmp_path, capsys):
    assert flame_main([str(tmp_path / "nope.png"), "--out-dir", str(tmp_path)]) == 1
    assert "error" in json.loads(capsys.readouterr().out)


def test_verifier_cli_exit_code():
    proc = subprocess.run([sys.executable, "-m", "cv.utils.verify_offline_env", "--manifest",
                           str(REPO / "cv" / "configs" / "offline_manifest.json")], cwd=REPO, capture_output=True)
    assert proc.returncode == 0


def test_video_fixture_matches_schema():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_video_fixture_missing_required_field_rejected():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    bad = json.loads(FIXTURE.read_text(encoding="utf-8"))
    del bad["temporalSummary"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(bad)