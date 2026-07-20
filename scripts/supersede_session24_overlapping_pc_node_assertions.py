#!/usr/bin/env python3
"""Governed catch-up: drop overlapping Session 24 PC node assertions.

Session 24 confirm published ``contribution:a01be11c6967afd9`` with full node
assertions for already-resolved PCs (Baergrom / Caelynn / Karsemine / Stafl).
Projection refused competing fingerprints. This script supersedes that
contribution with the same edges + new nodes, omitting those four PC node
asserts — no hand-edit of revision JSON.

Idempotent: if the old contribution is already ``superseded`` by a successor
that carries this script's own repair marker, prints current state and exits
0 without re-running the supersession.

Live world root requires ``--allow-live-world``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for path in (REPO_ROOT / "src", REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import graph_memory.kernel as kernel
from graph_memory.kernel.contribution_models import GraphContribution
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
DEFAULT_OLD_CONTRIBUTION_ID = "contribution:a01be11c6967afd9"
EXPECTED_CAMPAIGN_SCOPE = "longmont-c2"
EXPECTED_SOURCE_ARTIFACT_ID = "artifact:recap:longmont-c2:session-24"
EXPECTED_SOURCE_REVISION_ID = (
    "sha256:603c1590da3aca71d90c8b69abed59368219d5dc1e3d1adf83db1bf854b5cc95"
)
EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256 = (
    "4db10a0f169dcaffd63860a81d8fd15b580f4f198d60002f80a2256baaa4d6ef"
)
EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256 = (
    "c6663166cbaec4bced8dcf1eb11c431c598e3c9318708a3fc64d57260bd7c650"
)
REPAIR_DIAGNOSTIC_MARKER = "catchup:drop_overlapping_pc_node_assertions"
DROP_SUBJECTS = frozenset(
    {
        "pc:baergrom",
        "pc:caelynn",
        "pc:karsemine",
        "pc:stafl",
    }
)


def _is_live_world_root(root: Path, world_id: str) -> bool:
    """True when ``root`` is (or is configured as) the live product world store.

    Checked unconditionally against the *resolved* ``--root`` argument — not
    just the repo default — so pointing ``--root`` at another live world tree
    (e.g. via a symlink or an explicit absolute path) still trips the guard.
    """
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
    """Find the contribution that this script's own repair created, if any.

    A contribution merely being ``superseded`` is not proof this specific
    repair ran — any later supersession would set that status. Require the
    successor to both name ``old_contribution_id`` as
    ``supersedes_contribution_id`` and carry this script's diagnostic marker.
    """
    for record in list_contribution_records(root, world_id):
        if record.supersedes_contribution_id != old_contribution_id:
            continue
        if REPAIR_DIAGNOSTIC_MARKER in list(record.diagnostics):
            return record.contribution_id
    return None


def accepted_assertion_id_set_sha256(assertions: list[kernel.GraphContributionAssertion]) -> str:
    """SHA256 of sorted assertion_id lines (exact accepted set fingerprint)."""
    ids = sorted(assertion.assertion_id for assertion in assertions)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def accepted_assertions_dump_sha256(assertions: list[kernel.GraphContributionAssertion]) -> str:
    """SHA256 of canonical JSON dump for the full accepted_assertions list."""
    payload = [
        assertion.model_dump(mode="json", by_alias=True) for assertion in assertions
    ]
    return canonical_payload_sha256(payload)


def _validate_assertion_ids_match_bodies(
    assertions: list[kernel.GraphContributionAssertion],
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
    drop_subjects: frozenset[str],
) -> None:
    """Fail closed when ``old`` is not the Session 24 repair target."""
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
    _validate_assertion_ids_match_bodies(list(old.accepted_assertions))
    id_set_sha = accepted_assertion_id_set_sha256(list(old.accepted_assertions))
    if id_set_sha != expected_accepted_assertion_id_set_sha256:
        raise ValueError(
            "accepted_assertion_id_set_sha256 mismatch: "
            f"expected {expected_accepted_assertion_id_set_sha256!r}, got {id_set_sha!r}"
        )
    dump_sha = accepted_assertions_dump_sha256(list(old.accepted_assertions))
    if dump_sha != expected_accepted_assertions_dump_sha256:
        raise ValueError(
            "accepted_assertions_dump_sha256 mismatch: "
            f"expected {expected_accepted_assertions_dump_sha256!r}, got {dump_sha!r}"
        )
    present_subjects = {
        assertion.subject_node_id
        for assertion in old.accepted_assertions
        if assertion.assertion_kind == "node" and assertion.subject_node_id
    }
    missing = sorted(drop_subjects - present_subjects)
    if missing:
        raise ValueError(
            "expected node assertions missing for drop subjects: "
            + ", ".join(missing)
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
        help="Required campaign_scope on the contribution being repaired.",
    )
    parser.add_argument(
        "--expect-source-artifact-id",
        default=EXPECTED_SOURCE_ARTIFACT_ID,
        help="Required source_artifact_id on the contribution being repaired.",
    )
    parser.add_argument(
        "--expect-source-revision-id",
        default=EXPECTED_SOURCE_REVISION_ID,
        help="Required source_revision_id on the contribution being repaired.",
    )
    parser.add_argument(
        "--expect-accepted-assertion-id-set-sha256",
        default=EXPECTED_ACCEPTED_ASSERTION_ID_SET_SHA256,
        help="Required SHA256 of sorted accepted assertion_id lines.",
    )
    parser.add_argument(
        "--expect-accepted-assertions-dump-sha256",
        default=EXPECTED_ACCEPTED_ASSERTIONS_DUMP_SHA256,
        help="Required canonical SHA256 of accepted_assertions JSON dump.",
    )
    parser.add_argument(
        "--allow-live-world",
        action="store_true",
        help="Required when --root resolves under the live out/ world tree.",
    )
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
        _validate_repair_target(
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
            drop_subjects=DROP_SUBJECTS,
        )
    except ValueError as exc:
        print(f"Refusing repair: {exc}", file=sys.stderr)
        return 1

    kept = []
    dropped = []
    for assertion in old.accepted_assertions:
        subject = assertion.subject_node_id or ""
        if assertion.assertion_kind == "node" and subject in DROP_SUBJECTS:
            dropped.append(f"{assertion.assertion_id} {subject}")
        else:
            kept.append(assertion)

    summary = {
        "old_contribution_id": args.old_contribution_id,
        "head_before": head.head_revision_id,
        "dropped": dropped,
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
        authored_by="operator:pc_identity_catchup",
        accepted_assertions=kept,
        rejected_assertions=list(old.rejected_assertions),
        unresolved_mentions=list(old.unresolved_mentions),
        supersedes_contribution_id=args.old_contribution_id,
        diagnostics=[
            *list(old.diagnostics),
            REPAIR_DIAGNOSTIC_MARKER,
            f"supersedes:{args.old_contribution_id}",
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
