#!/usr/bin/env python3
"""Promote a reviewed candidate-graph extract into a World Supergraph head.

Prepare seals a proposal (typed IR + identity gate + digest). Confirm verifies
the seal and merges only when publication succeeds.

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
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
    verify_source_revision,
)
from graph_memory.extract_identity_gate import (
    IdentityGateResult,
    build_accepted_contribution_from_proposals,
    gate_candidate_graph_against_head,
)
from graph_memory.extract_promote_proposal import (
    PromoteProposalError,
    verify_promote_proposal,
)

DEFAULT_LIVE_ROOT = REPO_ROOT / "out"
DEFAULT_WORLD_ID = "eldyrwild"


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
    payload = _read_json(Path(args.candidate_graph))
    preview = load_typed_candidate_graph(payload)
    world_root = Path(args.world_root).resolve()
    if args.copy_from:
        _copy_world_root(Path(args.copy_from).resolve(), world_root)

    verified_revision = verify_source_revision(
        source_uri=args.source_uri,
        source_revision_id=args.source_revision_id,
        repo_root=REPO_ROOT,
    )

    node_ids = tuple(args.node_ids) if args.node_ids else None
    gate = gate_candidate_graph_against_head(
        preview,
        root=world_root,
        world_id=args.world_id,
        source_artifact_id=args.source_artifact_id,
        source_revision_id=verified_revision,
        campaign_scope=args.campaign_scope,
        source_uri=args.source_uri,
        node_ids=node_ids,
        include_edges=not args.nodes_only,
    )
    package = gate.to_review_package(
        prepared_by=args.prepared_by,
        world_root=str(world_root),
        candidate_graph_path=str(Path(args.candidate_graph).resolve()),
    )
    out = Path(args.output)
    _write_json(out, package)
    print(
        f"wrote sealed proposal {out} "
        f"proposal_id={package['proposal_id']} "
        f"digest={package['proposal_digest'][:16]}… "
        f"parent={gate.parent_revision_id} "
        f"accepted_proposals={len(gate.accepted_proposals)} "
        f"unresolved={len(gate.unresolved_mentions)}"
    )
    return 0


def _gate_from_verified(
    verified: dict[str, Any],
    package: dict[str, Any],
) -> IdentityGateResult:
    from graph_memory.kernel.contribution_models import GraphContribution

    contribution = GraphContribution.model_validate(package["contribution_candidate"])
    effect = verified["effect"]
    return IdentityGateResult(
        parent_revision_id=verified["parent_revision_id"],
        world_id=verified["world_id"],
        contribution=contribution,
        accepted_proposals=list(verified["accepted_proposals"]),
        unresolved_mentions=list(verified["unresolved_mentions"]),
        rejected_assertions=list(verified["rejected_assertions"]),
        scorer_report=dict(package.get("scorer_report") or {}),
        node_id_map=dict(verified["node_id_map"]),
        identity_outcome_snapshot=dict(verified["identity_outcome_snapshot"]),
        diagnostics=list(package.get("diagnostics") or []),
        candidate_preview_id=str(effect.get("candidate_preview_id") or ""),
        candidate_schema=str(effect.get("candidate_schema") or ""),
        candidate_version=str(effect.get("candidate_version") or ""),
        source_revision_id=verified["source_revision_id"],
        source_artifact_id=verified["source_artifact_id"],
        verified_source_uri=package.get("verified_source_uri"),
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

    world_id_hint = (
        (package.get("effect") or {}).get("world_id")
        or (package.get("contribution_candidate") or {}).get("world_id")
        or DEFAULT_WORLD_ID
    )
    head, _rev, _store = kernel.open_current_world_graph(
        world_root, str(world_id_hint)
    )

    try:
        verified = verify_promote_proposal(
            package,
            confirming_principal=args.confirming_principal,
            expected_parent_revision_id=head.head_revision_id,
            selected_assertion_ids=tuple(args.assertion_ids)
            if args.assertion_ids
            else None,
        )
    except PromoteProposalError as exc:
        raise SystemExit(f"proposal verification failed: {exc}") from exc

    # Re-verify sealed source revision against the sealed URI when present.
    source_uri = package.get("verified_source_uri")
    if source_uri:
        try:
            verify_source_revision(
                source_uri=str(source_uri),
                source_revision_id=verified["source_revision_id"],
                repo_root=REPO_ROOT,
            )
        except CandidateGraphMappingError as exc:
            raise SystemExit(f"source revision verification failed: {exc}") from exc

    gate = _gate_from_verified(verified, package)
    accepted_ids = tuple(args.assertion_ids) if args.assertion_ids else None
    try:
        contribution = build_accepted_contribution_from_proposals(
            gate,
            root=world_root,
            accepted_assertion_ids=accepted_ids,
            authored_by=args.authored_by,
            proposal_digest=verified["proposal_digest"],
        )
    except CandidateGraphMappingError as exc:
        raise SystemExit(f"selection error: {exc}") from exc

    if args.dry_run:
        out = Path(args.output) if args.output else package_path.with_name(
            "accepted_contribution.dry_run.json"
        )
        _write_json(
            out,
            {
                "schema": "dmb_accepted_extract_contribution_v1",
                "ok": True,
                "dry_run": True,
                "proposal_id": verified["proposal_id"],
                "proposal_digest": verified["proposal_digest"],
                "confirming_principal": verified["confirming_principal"],
                "world_root": str(world_root),
                "expected_parent_revision_id": gate.parent_revision_id,
                "contribution_id": contribution.contribution_id,
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

    published_ok = bool(result.published)
    if (
        not published_ok
        and args.allow_idempotent_noop
        and "idempotent_noop:contribution_already_applied" in (result.diagnostics or [])
    ):
        published_ok = True

    out = Path(args.output) if args.output else package_path.with_name(
        "promote_proof.json"
    )

    if not published_ok:
        proof = {
            "schema": "dmb_promote_extract_proof_v1",
            "ok": False,
            "world_root": str(world_root),
            "world_id": gate.world_id,
            "proposal_id": verified["proposal_id"],
            "proposal_digest": verified["proposal_digest"],
            "confirming_principal": verified["confirming_principal"],
            "parent_revision_id": gate.parent_revision_id,
            "merge": result.model_dump(mode="json"),
            "failure_reason": "merge_did_not_publish",
        }
        _write_json(out, proof)
        print(
            f"publication failed published={result.published} "
            f"revision={result.revision_id} proof={out}"
        )
        return 1

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
        "ok": True,
        "world_root": str(world_root),
        "world_id": gate.world_id,
        "proposal_id": verified["proposal_id"],
        "proposal_digest": verified["proposal_digest"],
        "confirming_principal": verified["confirming_principal"],
        "parent_revision_id": gate.parent_revision_id,
        "contribution_id": contribution.contribution_id,
        "merge": result.model_dump(mode="json"),
        "rebuild_diagnostics": list(rebuild.diagnostics),
        "rebuild_equivalent_to_head": "rebuild_equivalent_to_head" in rebuild.diagnostics,
        "projection_revision_id": projection.snapshot.revision_id,
        "projection_node_count": projection.summary.node_count,
        "projection_relationship_count": projection.summary.relationship_count,
    }
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
    confirm.add_argument("--authored-by", default="promote-extract-cli")
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
