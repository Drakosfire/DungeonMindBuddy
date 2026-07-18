#!/usr/bin/env python3
"""Promote a reviewed candidate-graph extract into a World Supergraph head.

Thin CLI over ``graph_memory.extract_promote_ops``. Prepare seals a proposal;
confirm verifies the seal and merges only when publication succeeds.

Defaults to a tmp world root. Live ``out/`` requires ``--allow-live-world``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT / "src", REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.extract_promote_ops import (
    DEFAULT_WORLD_ID,
    ExtractPromoteEmptySelectionError,
    ExtractPromoteLiveWorldError,
    ExtractPromoteWorldError,
    confirm_extract_promote,
    default_live_root,
    normalize_assertion_selection,
    prepare_extract_promote,
)
from graph_memory.extract_promote_proposal import PromoteProposalError

DEFAULT_LIVE_ROOT = default_live_root(repo_root=REPO_ROOT)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _copy_world_root(source_root: Path, dest_root: Path) -> None:
    src_gm = source_root / "graph_memory"
    if not src_gm.is_dir():
        raise SystemExit(f"source has no graph_memory/: {source_root}")
    dest_gm = dest_root / "graph_memory"
    if dest_gm.exists():
        raise SystemExit(f"destination already has graph_memory/: {dest_root}")
    dest_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_gm, dest_gm)


def cmd_prepare(args: argparse.Namespace) -> int:
    candidate_path = Path(args.candidate_graph).resolve()
    payload = _read_json(candidate_path)
    world_root = Path(args.world_root).resolve()
    if args.copy_from:
        _copy_world_root(Path(args.copy_from).resolve(), world_root)

    result = prepare_extract_promote(
        candidate_graph=payload,
        world_root=world_root,
        source_uri=args.source_uri,
        source_revision_id=args.source_revision_id,
        prepared_by=args.prepared_by,
        world_id=args.world_id,
        source_artifact_id=args.source_artifact_id,
        campaign_scope=args.campaign_scope,
        node_ids=tuple(args.node_ids) if args.node_ids else None,
        include_edges=not args.nodes_only,
        candidate_graph_path=str(candidate_path),
        repo_root=REPO_ROOT,
    )
    out = Path(args.output)
    _write_json(out, result.review_package)
    print(
        f"wrote sealed proposal {out} "
        f"proposal_id={result.proposal_id} "
        f"digest={result.proposal_digest[:16]}… "
        f"parent={result.parent_revision_id} "
        f"accepted_proposals={result.accepted_proposals_count} "
        f"unresolved={result.unresolved_mentions_count}"
    )
    return 0


def cmd_confirm(args: argparse.Namespace) -> int:
    package_path = Path(args.review_package)
    package = _read_json(package_path)
    world_root = (
        Path(args.world_root).resolve() if args.world_root else None
    )

    try:
        selected = normalize_assertion_selection(args.assertion_ids)
        result = confirm_extract_promote(
            review_package=package,
            world_root=world_root,
            confirming_principal=args.confirming_principal,
            assertion_ids=selected,
            dry_run=bool(args.dry_run),
            allow_live_world=bool(args.allow_live_world),
            allow_idempotent_noop=bool(args.allow_idempotent_noop),
            live_root=DEFAULT_LIVE_ROOT,
            repo_root=REPO_ROOT,
        )
    except ExtractPromoteEmptySelectionError as exc:
        raise SystemExit(str(exc)) from exc
    except ExtractPromoteLiveWorldError as exc:
        raise SystemExit(str(exc)) from exc
    except ExtractPromoteWorldError as exc:
        raise SystemExit(str(exc)) from exc
    except PromoteProposalError as exc:
        raise SystemExit(f"proposal verification failed: {exc}") from exc
    except CandidateGraphMappingError as exc:
        # Source re-verify or selection errors from confirm path.
        message = str(exc)
        if "source_revision" in message or "mismatch" in message:
            raise SystemExit(f"source revision verification failed: {exc}") from exc
        raise SystemExit(f"selection error: {exc}") from exc

    if result.dry_run:
        out = Path(args.output) if args.output else package_path.with_name(
            "accepted_contribution.dry_run.json"
        )
        _write_json(out, result.payload)
        print(f"dry-run wrote {out} (no merge)")
        return 0

    out = Path(args.output) if args.output else package_path.with_name(
        "promote_proof.json"
    )
    _write_json(out, result.payload)
    if not result.ok:
        merge = result.payload.get("merge") or {}
        print(
            f"publication incomplete published={result.payload.get('published')} "
            f"revision={result.payload.get('committed_revision_id') or merge.get('revision_id')} "
            f"verification={result.payload.get('post_publication_verification')} "
            f"reason={result.failure_reason} "
            f"retry={result.payload.get('retry_guidance')} proof={out}"
        )
        return 1

    merge = result.payload.get("merge") or {}
    print(
        f"published revision={result.payload.get('committed_revision_id') or merge.get('revision_id')} "
        f"accepted={len(merge.get('accepted_assertion_ids') or [])} "
        f"rebuild_ok={result.payload.get('rebuild_equivalent_to_head')} "
        f"proof={out}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Seal typed IR + identity gate into a proposal")
    prepare.add_argument("--candidate-graph", required=True)
    prepare.add_argument("--world-root", required=True, help="Kernel root (contains graph_memory/)")
    prepare.add_argument(
        "--copy-from",
        help="Copy graph_memory from this Kernel root into --world-root before prepare",
    )
    prepare.add_argument("--world-id", default=DEFAULT_WORLD_ID)
    prepare.add_argument("--source-revision-id", required=True)
    prepare.add_argument(
        "--source-uri",
        required=True,
        help="File path or repo:// URI whose bytes must hash to --source-revision-id",
    )
    prepare.add_argument("--source-artifact-id", default=None)
    prepare.add_argument("--campaign-scope", default=None)
    prepare.add_argument("--prepared-by", required=True)
    prepare.add_argument("--node-ids", nargs="*", default=None)
    prepare.add_argument("--nodes-only", action="store_true")
    prepare.add_argument("--output", required=True)
    prepare.set_defaults(func=cmd_prepare)

    confirm = sub.add_parser("confirm", help="Verify seal and merge accepted proposals")
    confirm.add_argument("--review-package", required=True)
    confirm.add_argument("--world-root", default=None)
    confirm.add_argument("--assertion-ids", nargs="*", default=None)
    confirm.add_argument("--confirming-principal", required=True)
    confirm.add_argument("--dry-run", action="store_true")
    confirm.add_argument("--allow-live-world", action="store_true")
    confirm.add_argument(
        "--allow-idempotent-noop",
        action="store_true",
        help="Treat Kernel idempotent_noop (published=False, already applied) as success",
    )
    confirm.add_argument("--output", default=None)
    confirm.set_defaults(func=cmd_confirm)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.func(args))
    except CandidateGraphMappingError as exc:
        raise SystemExit(f"mapping error: {exc}") from exc
    except PromoteProposalError as exc:
        raise SystemExit(f"proposal error: {exc}") from exc


if __name__ == "__main__":
    main()
