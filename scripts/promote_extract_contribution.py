#!/usr/bin/env python3
"""Promote a reviewed candidate-graph extract into a World Supergraph head.

Prepare writes a review package (identity gate + accepted proposals). Confirm
merges a selected accepted contribution with parent-revision fencing.

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

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_to_contribution import CandidateGraphMappingError
from graph_memory.extract_identity_gate import (
    IdentityGateResult,
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)

DEFAULT_LIVE_ROOT = REPO_ROOT / "out"
DEFAULT_WORLD_ID = "eldyrwild"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_candidate_graph(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema") == "dmb_portable_object_demo_candidate_v1":
        raise CandidateGraphMappingError(
            "phase4 portable demo JSON is not a candidate_graph; pass a "
            "candidate_graph.json from a preview/benchmark run"
        )
    if "nodes" not in payload:
        raise CandidateGraphMappingError(
            f"{path} does not look like a candidate_graph (missing nodes)"
        )
    return payload


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
    candidate_graph = _load_candidate_graph(Path(args.candidate_graph))
    world_root = Path(args.world_root).resolve()
    if args.copy_from:
        _copy_world_root(Path(args.copy_from).resolve(), world_root)

    node_ids = tuple(args.node_ids) if args.node_ids else None
    gate = gate_candidate_graph_against_head(
        candidate_graph,
        root=world_root,
        world_id=args.world_id,
        source_artifact_id=args.source_artifact_id,
        source_revision_id=args.source_revision_id,
        campaign_scope=args.campaign_scope,
        source_uri=args.source_uri,
        node_ids=node_ids,
        include_edges=not args.nodes_only,
    )
    package = gate.to_review_package()
    package["world_root"] = str(world_root)
    package["candidate_graph_path"] = str(Path(args.candidate_graph).resolve())
    out = Path(args.output)
    _write_json(out, package)
    print(
        f"wrote review package {out} "
        f"parent={gate.parent_revision_id} "
        f"accepted_proposals={len(gate.accepted_proposals)} "
        f"unresolved={len(gate.unresolved_mentions)}"
    )
    return 0


def _gate_from_package(package: dict[str, Any]) -> IdentityGateResult:
    from graph_memory.kernel.contribution_models import (
        ContributionIdentityMention,
        GraphContribution,
        GraphContributionAssertion,
    )

    contribution = GraphContribution.model_validate(package["contribution_candidate"])
    return IdentityGateResult(
        parent_revision_id=str(package["parent_revision_id"]),
        world_id=str(package["world_id"]),
        contribution=contribution,
        accepted_proposals=[
            GraphContributionAssertion.model_validate(item)
            for item in package.get("accepted_proposals") or []
        ],
        unresolved_mentions=[
            ContributionIdentityMention.model_validate(item)
            for item in package.get("unresolved_mentions") or []
        ],
        rejected_assertions=[
            GraphContributionAssertion.model_validate(item)
            for item in package.get("rejected_assertions") or []
        ],
        scorer_report=dict(package.get("scorer_report") or {}),
        node_id_map={str(k): str(v) for k, v in (package.get("node_id_map") or {}).items()},
        diagnostics=list(package.get("diagnostics") or []),
    )


def cmd_confirm(args: argparse.Namespace) -> int:
    package_path = Path(args.review_package)
    package = _read_json(package_path)
    world_root = Path(args.world_root or package.get("world_root") or "").resolve()
    if not world_root:
        raise SystemExit("--world-root is required when review package omits world_root")

    live_root = DEFAULT_LIVE_ROOT.resolve()
    if world_root == live_root and not args.allow_live_world:
        raise SystemExit(
            "refusing to mutate live out/ without --allow-live-world"
        )

    gate = _gate_from_package(package)
    accepted_ids = tuple(args.assertion_ids) if args.assertion_ids else None
    contribution = build_accepted_contribution_from_proposals(
        gate,
        accepted_assertion_ids=accepted_ids,
        authored_by=args.authored_by,
    )

    if args.dry_run:
        out = Path(args.output) if args.output else package_path.with_name(
            "accepted_contribution.dry_run.json"
        )
        _write_json(
            out,
            {
                "schema": "dmb_accepted_extract_contribution_v1",
                "world_root": str(world_root),
                "expected_parent_revision_id": gate.parent_revision_id,
                "contribution": contribution.model_dump(mode="json"),
            },
        )
        print(f"dry-run wrote {out} (no merge)")
        return 0

    result = kernel.merge_contribution_to_revision(
        world_root,
        world_id=gate.world_id,
        contribution=contribution,
        expected_parent_revision_id=gate.parent_revision_id,
    )
    rebuild = kernel.rebuild_from_contributions(
        world_root, world_id=gate.world_id, publish=False
    )
    from graph_memory.projection.world_projection import (
        PROJECTION_REQUEST_SCHEMA,
        WorldGraphProjectionFocus,
        WorldGraphProjectionRequest,
    )

    projection = kernel.project_world_graph(
        world_root,
        WorldGraphProjectionRequest(
            schema=PROJECTION_REQUEST_SCHEMA,
            world_id=gate.world_id,
            campaign_id=contribution.campaign_scope or "longmont-c2",
            focus=WorldGraphProjectionFocus(kind="none"),
            admissibility="gm",
        ),
    )
    proof = {
        "schema": "dmb_promote_extract_proof_v1",
        "world_root": str(world_root),
        "world_id": gate.world_id,
        "parent_revision_id": gate.parent_revision_id,
        "merge": result.model_dump(mode="json"),
        "rebuild_diagnostics": list(rebuild.diagnostics),
        "rebuild_equivalent_to_head": "rebuild_equivalent_to_head" in rebuild.diagnostics,
        "projection_revision_id": projection.snapshot.revision_id,
        "projection_node_count": projection.summary.node_count,
        "projection_relationship_count": projection.summary.relationship_count,
    }
    out = Path(args.output) if args.output else package_path.with_name(
        "promote_proof.json"
    )
    _write_json(out, proof)
    print(
        f"published revision={result.revision_id} "
        f"accepted={len(result.accepted_assertion_ids)} "
        f"rebuild_ok={proof['rebuild_equivalent_to_head']} "
        f"proof={out}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prepare = sub.add_parser("prepare", help="Map + identity-gate into a review package")
    prepare.add_argument("--candidate-graph", required=True)
    prepare.add_argument("--world-root", required=True, help="Kernel root (contains graph_memory/)")
    prepare.add_argument(
        "--copy-from",
        help="Copy graph_memory from this Kernel root into --world-root before prepare",
    )
    prepare.add_argument("--world-id", default=DEFAULT_WORLD_ID)
    prepare.add_argument("--source-revision-id", required=True)
    prepare.add_argument("--source-artifact-id", default=None)
    prepare.add_argument("--campaign-scope", default=None)
    prepare.add_argument("--source-uri", default=None)
    prepare.add_argument("--node-ids", nargs="*", default=None)
    prepare.add_argument("--nodes-only", action="store_true")
    prepare.add_argument("--output", required=True)
    prepare.set_defaults(func=cmd_prepare)

    confirm = sub.add_parser("confirm", help="Merge accepted proposals into the world head")
    confirm.add_argument("--review-package", required=True)
    confirm.add_argument("--world-root", default=None)
    confirm.add_argument("--assertion-ids", nargs="*", default=None)
    confirm.add_argument("--authored-by", default="promote-extract-cli")
    confirm.add_argument("--dry-run", action="store_true")
    confirm.add_argument("--allow-live-world", action="store_true")
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


if __name__ == "__main__":
    main()
