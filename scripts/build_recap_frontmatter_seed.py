from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agent.recap_frontmatter_seed import build_frontmatter_seed, default_frontmatter_seed_path  # noqa: E402
from src.corpus.session_recap_paths import normalized_recap_relpath  # noqa: E402
from src.live_play.recap_derivative_provenance import (  # noqa: E402
    sha256_bytes,
    sha256_file,
    store_provenanced_artifact,
)
from src.live_play.recap_ingest_pipeline import inspect_recap_ingest_status  # noqa: E402
from src.live_play.recap_stage_paths import corpus_root  # noqa: E402


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a deterministic frontmatter_seed.md skeleton for a normalized recap."
    )
    parser.add_argument("--campaign", type=int, required=True, choices=(1, 2))
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--corpus-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--check", action="store_true", help="Fail if the target output differs.")
    parser.add_argument("--force", action="store_true", help="Archive and refresh a stale or unverified seed.")
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
    status = inspect_recap_ingest_status(
        campaign_id=f"longmont-c{args.campaign}",
        session=args.session,
        title=None,
        slug=None,
        corpus=root,
    )
    if "normalized_current" not in status.get("states", []):
        print("normalized recap is not verified against the current canonical source", file=sys.stderr)
        return 2
    if args.check:
        if not out_path.is_file():
            print(f"missing frontmatter seed: {out_path}", file=sys.stderr)
            return 1
        if "frontmatter_seed_current" not in status.get("states", []):
            print("frontmatter seed lineage is not verified against current inputs", file=sys.stderr)
            return 2
        existing = out_path.read_text(encoding="utf-8")
        if existing != seed:
            print(f"frontmatter seed differs: {out_path}", file=sys.stderr)
            return 1
        print(f"OK {out_path}")
        return 0
    seed_bytes = (seed if seed.endswith("\n") else seed + "\n").encode("utf-8")
    normalized = root / normalized_recap_relpath(
        campaign_number=args.campaign,
        session=args.session,
        corpus_root=root,
    )
    outcome, archived = store_provenanced_artifact(
        output_path=out_path,
        corpus_root=root,
        stage="frontmatter_seed",
        campaign_number=args.campaign,
        session=args.session,
        input_digests={
            "normalized_recap": sha256_file(normalized),
            "generated_seed": sha256_bytes(seed_bytes),
        },
        content=seed_bytes,
        force=args.force,
        allow_edited_current_inputs=True,
    )
    if outcome not in {"created", "refreshed", "reused", "edited_current_inputs"}:
        print(
            f"preserved existing seed with lineage state {outcome}; use --force only after review",
            file=sys.stderr,
        )
        return 2
    print(f"{outcome}: {out_path}")
    for item in archived:
        print(f"archived: {item['from']} -> {item['to']}")
    refreshed_status = inspect_recap_ingest_status(
        campaign_id=f"longmont-c{args.campaign}",
        session=args.session,
        title=None,
        slug=None,
        corpus=root,
    )
    for stage, details in refreshed_status.get("ingest_report", {}).get("derivative_stages", {}).items():
        if stage != "frontmatter_seed" and isinstance(details, dict) and details.get("state") not in {"current", "missing"}:
            print(f"downstream {stage}: {details.get('state')}", file=sys.stderr)
    for action in refreshed_status.get("next_actions", []):
        print(f"next: {action}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
