#!/usr/bin/env python3
"""Governed repair: split Session 5 Stafl↔Baergrom label collision off coarse edge id.

Session 5 published ``contribution:400ffb3a229f2b13`` with edge assertion
``assertion:674c619a70a8688c`` (label ``heals``) on the same durable id as
Session 3's ``pulls net with`` observation
(``edge:pc:stafl:works_with:pc:baergrom``). Projection refuses competing
active edge labels.

This script supersedes the Session 5 contribution, rewriting only that edge
to ``edge:pc:stafl:works_with:pc:baergrom:heals`` via
``durable_edge_id_for_observation`` — no hand-edit of revision JSON.

Idempotent when a successor already carries this script's repair marker.
Live world root requires ``--allow-live-world``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT / "src", REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import graph_memory.kernel as kernel
from graph_memory.candidate_graph_to_contribution import durable_edge_id_for_observation
from graph_memory.kernel.contribution_models import GraphContribution, GraphContributionAssertion
from graph_memory.kernel.contributions import (
    canonical_payload_sha256,
    compute_assertion_id,
)
from graph_memory.world_supergraph.contribution_store import (
    list_contribution_records,
    load_contribution_record,
)

DEFAULT_ROOT = REPO_ROOT / "out"
DEFAULT_WORLD_ID = "eldyrwild"
DEFAULT_OLD_CONTRIBUTION_ID = "contribution:400ffb3a229f2b13"
EXPECTED_CAMPAIGN_SCOPE = "longmont-c1"
EXPECTED_SOURCE_ARTIFACT_ID = "artifact:recap:longmont-c1:session-5"
EXPECTED_SOURCE_REVISION_ID = (
    "sha256:857778650365589f24050e55fdc7d041f00d86dde00f0da8cdacdcaf1578c5b5"
)
EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256 = (
    "ca9a7219dffdc884f146f6b05538e3c09dd071cf5fbc394a94b24949ef59ea74"
)
EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256 = (
    "54e76f08c678177fa621b168eb790657ac8fdeb86f94459a519efa51374bd1cb"
)
REPAIR_DIAGNOSTIC_MARKER = "catchup:split_stafl_baergrom_heals_edge_id"
COLLIDING_COARSE_EDGE_ID = "edge:pc:stafl:works_with:pc:baergrom"
COLLIDING_ASSERTION_ID = "assertion:674c619a70a8688c"
COLLIDING_LABEL = "heals"
COLLIDING_SUBJECT = "pc:stafl"
COLLIDING_TARGET = "pc:baergrom"
COLLIDING_PREDICATE = "works_with"


def _is_live_world_root(root: Path, world_id: str) -> bool:
    if (root / "graph_memory" / "worlds" / world_id).exists():
        return True
    if root == DEFAULT_ROOT.resolve():
        return True
    try:
        from apps.live_control_server.config import live_world_graph_root

        if root == live_world_graph_root():
            return True
    except Exception:
        pass
    return False


def _repair_successor_contribution_id(
    root: Path, world_id: str, old_contribution_id: str
) -> str | None:
    for record in list_contribution_records(root, world_id):
        if record.supersedes_contribution_id != old_contribution_id:
            continue
        if REPAIR_DIAGNOSTIC_MARKER in list(record.diagnostics):
            return record.contribution_id
    return None


def accepted_assertion_id_set_sha256(
    assertions: list[GraphContributionAssertion],
) -> str:
    ids = sorted(assertion.assertion_id for assertion in assertions)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def accepted_assertions_dump_sha256(
    assertions: list[GraphContributionAssertion],
) -> str:
    payload = [
        assertion.model_dump(mode="json", by_alias=True) for assertion in assertions
    ]
    return canonical_payload_sha256(payload)


def _validate_assertion_ids_match_bodies(
    assertions: list[GraphContributionAssertion],
) -> None:
    for assertion in assertions:
        computed = compute_assertion_id(
            assertion_kind=assertion.assertion_kind,
            subject_node_id=assertion.subject_node_id,
            target_node_id=assertion.target_node_id,
            predicate=assertion.predicate,
            label=assertion.label,
            value=dict(assertion.value),
            campaign_scope=assertion.campaign_scope,
            temporal_scope=assertion.temporal_scope,
            epistemic_kind=assertion.epistemic_kind,
            visibility=assertion.visibility,
        )
        if computed != assertion.assertion_id:
            raise ValueError(
                "assertion_id does not match body for "
                f"{assertion.assertion_id!r}: computed {computed!r}"
            )


def _validate_repair_target(
    old: GraphContribution,
    *,
    expected_campaign_scope: str,
    expected_source_artifact_id: str,
    expected_source_revision_id: str,
    expected_accepted_assertion_id_set_sha256: str,
    expected_accepted_assertions_dump_sha256: str,
) -> GraphContributionAssertion:
    if old.campaign_scope != expected_campaign_scope:
        raise ValueError(
            "campaign_scope mismatch: "
            f"expected {expected_campaign_scope!r}, got {old.campaign_scope!r}"
        )
    if old.source_artifact_id != expected_source_artifact_id:
        raise ValueError(
            "source_artifact_id mismatch: "
            f"expected {expected_source_artifact_id!r}, got {old.source_artifact_id!r}"
        )
    if old.source_revision_id != expected_source_revision_id:
        raise ValueError(
            "source_revision_id mismatch: "
            f"expected {expected_source_revision_id!r}, got {old.source_revision_id!r}"
        )
    accepted = list(old.accepted_assertions)
    _validate_assertion_ids_match_bodies(accepted)
    id_set_sha = accepted_assertion_id_set_sha256(accepted)
    if id_set_sha != expected_accepted_assertion_id_set_sha256:
        raise ValueError(
            "accepted_assertion_id_set_sha256 mismatch: "
            f"expected {expected_accepted_assertion_id_set_sha256!r}, got {id_set_sha!r}"
        )
    dump_sha = accepted_assertions_dump_sha256(accepted)
    if dump_sha != expected_accepted_assertions_dump_sha256:
        raise ValueError(
            "accepted_assertions_dump_sha256 mismatch: "
            f"expected {expected_accepted_assertions_dump_sha256!r}, got {dump_sha!r}"
        )

    colliding: GraphContributionAssertion | None = None
    for assertion in accepted:
        edge_id = str((assertion.value or {}).get("edge_id") or "")
        if assertion.assertion_kind != "edge":
            continue
        if edge_id != COLLIDING_COARSE_EDGE_ID:
            continue
        if (assertion.label or "").strip().casefold() != COLLIDING_LABEL:
            continue
        if assertion.subject_node_id != COLLIDING_SUBJECT:
            continue
        if assertion.target_node_id != COLLIDING_TARGET:
            continue
        if (assertion.predicate or "").strip() != COLLIDING_PREDICATE:
            continue
        colliding = assertion
        break
    if colliding is None:
        raise ValueError(
            "expected colliding heals edge on "
            f"{COLLIDING_COARSE_EDGE_ID!r} not found"
        )
    if colliding.assertion_id != COLLIDING_ASSERTION_ID:
        raise ValueError(
            "colliding assertion_id mismatch: "
            f"expected {COLLIDING_ASSERTION_ID!r}, got {colliding.assertion_id!r}"
        )
    return colliding


def _rewrite_colliding_edge(
    assertion: GraphContributionAssertion,
) -> GraphContributionAssertion:
    new_edge_id = durable_edge_id_for_observation(
        subject_id=COLLIDING_SUBJECT,
        target_id=COLLIDING_TARGET,
        predicate=COLLIDING_PREDICATE,
        label=COLLIDING_LABEL,
    )
    if new_edge_id == COLLIDING_COARSE_EDGE_ID:
        raise ValueError(
            f"repair refused to mint a non-coarse edge id; got {new_edge_id!r}"
        )
    value = dict(assertion.value or {})
    value["edge_id"] = new_edge_id
    return kernel.build_assertion(
        assertion_kind=assertion.assertion_kind,
        acceptance_state=assertion.acceptance_state,
        contribution_id=assertion.contribution_id,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=value,
        evidence_ref_ids=list(assertion.evidence_ref_ids),
        source_artifact_id=assertion.source_artifact_id,
        source_revision_id=assertion.source_revision_id,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=assertion.temporal_scope,
        visibility=assertion.visibility,
        epistemic_kind=assertion.epistemic_kind,
        identity_resolution_outcome=assertion.identity_resolution_outcome,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--world-id", default=DEFAULT_WORLD_ID)
    parser.add_argument(
        "--old-contribution-id",
        default=DEFAULT_OLD_CONTRIBUTION_ID,
    )
    parser.add_argument(
        "--expect-campaign-scope",
        default=EXPECTED_CAMPAIGN_SCOPE,
    )
    parser.add_argument(
        "--expect-source-artifact-id",
        default=EXPECTED_SOURCE_ARTIFACT_ID,
    )
    parser.add_argument(
        "--expect-source-revision-id",
        default=EXPECTED_SOURCE_REVISION_ID,
    )
    parser.add_argument(
        "--expect-accepted-assertion-id-set-sha256",
        default=EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256,
    )
    parser.add_argument(
        "--expect-accepted-assertions-dump-sha256",
        default=EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256,
    )
    parser.add_argument("--allow-live-world", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if _is_live_world_root(root, args.world_id) and not args.allow_live_world:
        print(
            "Refusing live world mutation without --allow-live-world.",
            file=sys.stderr,
        )
        return 2

    old = load_contribution_record(root, args.world_id, args.old_contribution_id)
    head = kernel.open_world_graph_head(root, args.world_id)
    successor_contribution_id = _repair_successor_contribution_id(
        root, args.world_id, args.old_contribution_id
    )
    if old.status == "superseded" and successor_contribution_id is not None:
        print(
            json.dumps(
                {
                    "already_done": True,
                    "old_contribution_id": args.old_contribution_id,
                    "old_status": old.status,
                    "successor_contribution_id": successor_contribution_id,
                    "head_revision_id": head.head_revision_id,
                },
                indent=2,
            )
        )
        return 0

    try:
        colliding = _validate_repair_target(
            old,
            expected_campaign_scope=args.expect_campaign_scope,
            expected_source_artifact_id=args.expect_source_artifact_id,
            expected_source_revision_id=args.expect_source_revision_id,
            expected_accepted_assertion_id_set_sha256=(
                args.expect_accepted_assertion_id_set_sha256
            ),
            expected_accepted_assertions_dump_sha256=(
                args.expect_accepted_assertions_dump_sha256
            ),
        )
    except ValueError as exc:
        print(f"Refusing repair: {exc}", file=sys.stderr)
        return 1

    rewritten = _rewrite_colliding_edge(colliding)
    kept: list[GraphContributionAssertion] = []
    for assertion in old.accepted_assertions:
        if assertion.assertion_id == COLLIDING_ASSERTION_ID:
            kept.append(rewritten)
        else:
            kept.append(assertion)

    summary: dict[str, Any] = {
        "old_contribution_id": args.old_contribution_id,
        "head_before": head.head_revision_id,
        "rewritten_assertion_id": {
            "from": COLLIDING_ASSERTION_ID,
            "to": rewritten.assertion_id,
        },
        "rewritten_edge_id": {
            "from": COLLIDING_COARSE_EDGE_ID,
            "to": rewritten.value.get("edge_id"),
        },
        "kept_count": len(kept),
        "dry_run": args.dry_run,
    }
    if args.dry_run:
        print(json.dumps(summary, indent=2))
        return 0

    new = kernel.create_graph_contribution(
        world_id=args.world_id,
        source_kind=old.source_kind,
        source_artifact_id=old.source_artifact_id,
        source_revision_id=old.source_revision_id,
        extraction_profile=old.extraction_profile,
        campaign_scope=old.campaign_scope,
        authored_by="operator:edge_identity_collision_catchup",
        accepted_assertions=kept,
        rejected_assertions=list(old.rejected_assertions),
        unresolved_mentions=list(old.unresolved_mentions),
        supersedes_contribution_id=args.old_contribution_id,
        diagnostics=[
            *list(old.diagnostics),
            REPAIR_DIAGNOSTIC_MARKER,
            f"supersedes:{args.old_contribution_id}",
            (
                f"rewrote_edge:{COLLIDING_COARSE_EDGE_ID}->"
                f"{rewritten.value.get('edge_id')}"
            ),
        ],
    )
    result = kernel.supersede_graph_contribution(
        root,
        world_id=args.world_id,
        new_contribution=new,
        superseded_contribution_id=args.old_contribution_id,
        expected_parent_revision_id=head.head_revision_id,
    )
    summary.update(
        {
            "published": result.published,
            "new_contribution_id": new.contribution_id,
            "new_revision_id": result.revision_id,
            "parent_revision_id": result.parent_revision_id,
            "diagnostics": list(result.diagnostics or [])[:12],
        }
    )
    print(json.dumps(summary, indent=2))
    return 0 if result.published else 1


if __name__ == "__main__":
    raise SystemExit(main())
