from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.lexicon_phase_b.route_equivalence_manifest import (
    build_route_equivalence_manifest,
    write_route_equivalence_manifest,
)

_DEFAULT_REGISTRIES = [
    Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json"),
    Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json"),
]
_DEFAULT_OUT_DIR = Path("evals/sentence_routing_retrieval_falsification/artifacts/lexicon")


def _campaign_to_filename(campaign_id: str) -> str:
    return f"route_equivalence_{campaign_id.replace('-', '_').lower()}_v1.jsonl"


def _build_one(registry_path: Path, out_path: Path) -> int:
    records = build_route_equivalence_manifest(registry_path)
    write_route_equivalence_manifest(records, out_path)
    return len(records)


def _write_mode(out_dir: Path) -> int:
    for registry in _DEFAULT_REGISTRIES:
        campaign_id = f"longmont-c{registry.parent.name.split()[-1]}".lower()
        out_path = out_dir / _campaign_to_filename(campaign_id)
        count = _build_one(registry, out_path)
        print(f"wrote {out_path.as_posix()} ({count} records)")
    return 0


def _check_mode(out_dir: Path) -> int:
    had_mismatch = False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for registry in _DEFAULT_REGISTRIES:
            campaign_id = f"longmont-c{registry.parent.name.split()[-1]}".lower()
            name = _campaign_to_filename(campaign_id)
            generated = tmp_dir / name
            canonical = out_dir / name
            _build_one(registry, generated)
            if not canonical.exists() or generated.read_bytes() != canonical.read_bytes():
                print(f"MISMATCH {canonical.as_posix()}")
                had_mismatch = True
            else:
                print(f"OK {canonical.as_posix()}")
    return 1 if had_mismatch else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--out-dir", type=Path, default=_DEFAULT_OUT_DIR)
    args = parser.parse_args()

    try:
        if args.check:
            return _check_mode(args.out_dir)
        return _write_mode(args.out_dir)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
