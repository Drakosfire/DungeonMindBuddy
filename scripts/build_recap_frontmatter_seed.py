from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.recap_frontmatter_seed import build_frontmatter_seed, default_frontmatter_seed_path
from src.live_play.recap_stage_paths import corpus_root


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic frontmatter_seed.md skeleton for a normalized recap."
    )
    parser.add_argument("--campaign", type=int, required=True, choices=(1, 2))
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="Fail if the target output differs.")
    parser.add_argument("--stdout", action="store_true", help="Print seed instead of writing it.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    root = (args.corpus_root or corpus_root()).resolve()
    seed = build_frontmatter_seed(
        corpus_root=root,
        campaign_number=args.campaign,
        session=args.session,
    )
    if args.stdout:
        print(seed, end="" if seed.endswith("\n") else "\n")
        return 0
    out_path = (
        args.output.resolve()
        if args.output is not None
        else default_frontmatter_seed_path(
            corpus_root=root,
            campaign_number=args.campaign,
            session=args.session,
        ).resolve()
    )
    if args.check:
        if not out_path.is_file():
            print(f"missing frontmatter seed: {out_path}", file=sys.stderr)
            return 1
        existing = out_path.read_text(encoding="utf-8")
        if existing != seed:
            print(f"frontmatter seed differs: {out_path}", file=sys.stderr)
            return 1
        print(f"OK {out_path}")
        return 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(seed if seed.endswith("\n") else seed + "\n", encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
