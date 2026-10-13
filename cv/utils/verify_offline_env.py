"""
verify_offline_env.py - Verifies local environment, dependencies, and model assets for offline execution.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def verify_manifest(manifest_path: Path) -> bool:
    """Verify that all required local assets listed in the manifest exist and meet size criteria."""
    if not manifest_path.exists():
        print(f"[ERROR] Manifest file not found at: {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    root_dir = manifest_path.resolve().parents[2]
    assets = data.get("requiredAssets", [])
    
    success = True
    print(f"[*] Verifying {len(assets)} offline assets from manifest v{data.get('manifestVersion', '1.0.0')}...")

    for asset in assets:
        asset_path = root_dir / asset["path"]
        min_size = asset.get("minSizeBytes", 0)

        if not asset_path.exists():
            print(f"  [FAIL] Missing asset: {asset['name']} -> Path not found: {asset_path}")
            success = False
        else:
            file_size = asset_path.stat().st_size
            if file_size < min_size:
                print(f"  [FAIL] Asset size mismatch for {asset['name']}: got {file_size} bytes, expected at least {min_size} bytes")
                success = False
            else:
                print(f"  [PASS] {asset['name']} ({file_size} bytes)")

    return success


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify offline environment and assets.")
    parser.add_argument("--manifest", type=str, required=True, help="Path to the offline manifest JSON file.")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not verify_manifest(manifest_path):
        print("\n[ERROR] Offline environment verification FAILED. Missing or invalid assets detected.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Offline environment verification PASSED. Ready for air-gapped execution.")
        sys.exit(0)


if __name__ == "__main__":
    main()
