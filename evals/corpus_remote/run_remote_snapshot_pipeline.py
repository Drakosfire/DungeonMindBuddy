from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
try:
    from evals.corpus_remote.build_remote_inventory import (
        _collect_local_inventory,
        _collect_remote_inventory,
        generate_remote_artifacts,
    )
    from evals.corpus_remote.validate_remote_artifacts import validate_artifacts
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from evals.corpus_remote.build_remote_inventory import (
        _collect_local_inventory,
        _collect_remote_inventory,
        generate_remote_artifacts,
    )
    from evals.corpus_remote.validate_remote_artifacts import validate_artifacts


DEFAULT_OUT_DIR = Path(__file__).resolve().parents[2] / "out" / "evals" / "corpus_remote"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run remote corpus snapshot pipeline")
    parser.add_argument("--source-host", default="gpu_desktop")
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--local-root", default=None)
    parser.add_argument("--ssh-host", default=None)
    parser.add_argument("--remote-root", default=None)
    parser.add_argument("--ssh-username", default=None)
    parser.add_argument("--ssh-password", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)

    if args.local_root:
        records = _collect_local_inventory(Path(args.local_root))
    else:
        if not args.ssh_host or not args.remote_root:
            raise ValueError(
                "Use either --local-root, or provide both --ssh-host and --remote-root."
            )
        records = _collect_remote_inventory(
            ssh_host=str(args.ssh_host),
            remote_root=str(args.remote_root),
            ssh_username=str(args.ssh_username) if args.ssh_username else None,
            ssh_password=str(args.ssh_password) if args.ssh_password else None,
        )

    generate_remote_artifacts(
        source_host=str(args.source_host),
        records=records,
        sample_size=int(args.sample_size),
        out_dir=out_dir,
    )

    errors = validate_artifacts(
        inventory_path=out_dir / "remote_inventory.json",
        manifest_path=out_dir / "normalization_manifest.json",
        reproducibility_path=out_dir / "reproducibility_report.json",
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Snapshot pipeline succeeded. Artifacts at: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

