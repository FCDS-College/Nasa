"""
verify_offline_env.py - Verifies local environment, dependencies, and model assets for offline execution.

Assets may carry an optional ``sha256``. Required assets fail verification when missing or invalid;
optional assets only produce warnings. When the manifest has ``offlinePackages``, the downloaded
wheels are compared with the checksum file (create it with ``--write-checksums``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_asset(root_dir: Path, asset: Dict[str, Any], required: bool) -> bool:
    fail_tag = "FAIL" if required else "WARN"
    asset_path = root_dir / asset["path"]
    min_size = asset.get("minSizeBytes", 0)

    if not asset_path.exists():
        print(f"  [{fail_tag}] Missing asset: {asset['name']} -> Path not found: {asset_path}")
        return False
    file_size = asset_path.stat().st_size
    if file_size < min_size:
        print(f"  [{fail_tag}] Asset size mismatch for {asset['name']}: got {file_size} bytes, expected at least {min_size} bytes")
        return False
    expected = asset.get("sha256")
    if expected and sha256_of(asset_path) != expected.lower():
        print(f"  [{fail_tag}] Checksum mismatch for {asset['name']}")
        return False
    print(f"  [PASS] {asset['name']} ({file_size} bytes)")
    return True


def _read_checksums(checksum_file: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for line in checksum_file.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            result[parts[1].lstrip("*")] = parts[0].lower()
    return result


def write_checksums(manifest_path: Path) -> Optional[Path]:
    """Record SHA-256 checksums of every file in the offline package directory."""
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cfg = data.get("offlinePackages")
    if not cfg:
        print("[ERROR] Manifest has no offlinePackages section.")
        return None
    root_dir = manifest_path.resolve().parents[2]
    pkg_dir = root_dir / cfg["directory"]
    if not pkg_dir.is_dir():
        print(f"[ERROR] Package directory not found: {pkg_dir}")
        return None
    out = root_dir / cfg["checksumFile"]
    lines = [f"{sha256_of(p)}  {p.name}" for p in sorted(pkg_dir.iterdir()) if p.is_file()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[*] Wrote {len(lines)} checksums to {out}")
    return out


def _check_packages(root_dir: Path, cfg: Dict[str, str]) -> bool:
    pkg_dir = root_dir / cfg["directory"]
    checksum_file = root_dir / cfg["checksumFile"]
    print(f"[*] Verifying offline packages in {cfg['directory']}...")
    if not pkg_dir.is_dir():
        print(f"  [FAIL] Package directory not found: {pkg_dir}")
        return False
    if not checksum_file.exists():
        print(f"  [FAIL] Checksum file not found: {checksum_file} (create it with --write-checksums)")
        return False
    expected = _read_checksums(checksum_file)
    present = {p.name: p for p in pkg_dir.iterdir() if p.is_file()}
    problems: List[str] = []
    for name, digest in expected.items():
        if name not in present:
            problems.append(f"missing {name}")
        elif sha256_of(present[name]) != digest:
            problems.append(f"checksum mismatch {name}")
    problems += [f"unlisted file {n}" for n in present if n not in expected]
    for problem in problems:
        print(f"  [FAIL] {problem}")
    if not problems:
        print(f"  [PASS] {len(expected)} packages match recorded checksums")
    return not problems


def verify_manifest(manifest_path: Path, check_packages: bool = False) -> bool:
    """Verify that required local assets exist and meet size/checksum criteria."""
    if not manifest_path.exists():
        print(f"[ERROR] Manifest file not found at: {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    root_dir = manifest_path.resolve().parents[2]
    required = data.get("requiredAssets", [])
    optional = data.get("optionalAssets", [])

    print(f"[*] Verifying {len(required)} required and {len(optional)} optional assets from manifest v{data.get('manifestVersion', '1.0.0')}...")
    success = True
    for asset in required:
        success = _check_asset(root_dir, asset, True) and success
    for asset in optional:
        _check_asset(root_dir, asset, False)

    if check_packages and data.get("offlinePackages"):
        success = _check_packages(root_dir, data["offlinePackages"]) and success
    return success


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Verify offline environment and assets.")
    parser.add_argument("--manifest", type=str, required=True, help="Path to the offline manifest JSON file.")
    parser.add_argument("--check-packages", action="store_true", help="Also verify downloaded wheels against the checksum file.")
    parser.add_argument("--write-checksums", action="store_true", help="Record checksums of the downloaded wheels and exit.")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    if args.write_checksums:
        sys.exit(0 if write_checksums(manifest_path) else 1)
    if not verify_manifest(manifest_path, args.check_packages):
        print("\n[ERROR] Offline environment verification FAILED. Missing or invalid assets detected.")
        sys.exit(1)
    print("\n[SUCCESS] Offline environment verification PASSED. Ready for air-gapped execution.")
    sys.exit(0)


if __name__ == "__main__":
    main()