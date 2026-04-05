from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def promote_baseline(*, run_dir: Path, surface: str, baselines_root: Path) -> Path:
    target_dir = baselines_root / surface / "current"
    target_dir.mkdir(parents=True, exist_ok=True)

    required_files = ["aggregate_metrics.json", "pipeline_contract.json", "run_manifest.json"]
    for filename in required_files:
        src = run_dir / filename
        if not src.exists():
            raise FileNotFoundError(f"Missing required run artifact for promotion: {src}")
        shutil.copy2(src, target_dir / filename)

    record = {
        "promoted_at": _utc_now_iso(),
        "surface": surface,
        "source_run_dir": str(run_dir),
    }
    (target_dir / "promotion_record.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return target_dir


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote extraction lab run artifacts to baseline.")
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--surface", type=str, default="core_extraction")
    parser.add_argument("--baselines-root", type=Path, default=ROOT / "out" / "extraction_lab" / "baselines")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    target = promote_baseline(run_dir=args.run_dir, surface=args.surface, baselines_root=args.baselines_root)
    print(f"Promoted baseline to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
