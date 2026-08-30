"""Audit revision-bound contribution source-payload digest authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_memory.interaction.schema_constants import DIGEST_AUDIT_SCHEMA
from apps.live_control_server.models.world_graph_contributions import compute_contribution_source_payload_sha256
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)
from graph_memory.world_supergraph.storage import load_current_world_graph

TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"


def audit_contribution_source_digests(
    root: Path,
    *,
    world_id: str = "eldyrwild",
    highlight_contribution_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return per-contribution digest coverage for the active world head."""
    head, revision, store = load_current_world_graph(root, world_id)
    index = load_contribution_index(root, world_id)
    failed = set(index.failed_contribution_ids)
    digests = store.contribution_source_payload_sha256 or {}
    revision_id = (
        getattr(store, "revision_id", None)
        or getattr(revision, "revision_id", None)
        or getattr(head, "head_revision_id", None)
    )
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    mismatched: list[str] = []
    for contribution_id in index.all_contribution_ids:
        if contribution_id in failed:
            rows.append(
                {
                    "contribution_id": contribution_id,
                    "status": "failed_skipped",
                    "expected": digests.get(contribution_id),
                    "actual": None,
                }
            )
            continue
        try:
            contrib = load_contribution_record(root, world_id, contribution_id)
        except FileNotFoundError:
            missing.append(contribution_id)
            rows.append(
                {
                    "contribution_id": contribution_id,
                    "status": "ledger_missing",
                    "expected": digests.get(contribution_id),
                    "actual": None,
                }
            )
            continue
        if contrib.status == "failed":
            rows.append(
                {
                    "contribution_id": contribution_id,
                    "status": "failed_skipped",
                    "expected": digests.get(contribution_id),
                    "actual": None,
                }
            )
            continue
        actual = compute_contribution_source_payload_sha256(contrib)
        expected = digests.get(contribution_id)
        if expected is None:
            missing.append(contribution_id)
            status = "missing_digest"
        elif expected != actual:
            mismatched.append(contribution_id)
            status = "mismatch"
        else:
            status = "ok"
        rows.append(
            {
                "contribution_id": contribution_id,
                "status": status,
                "expected": expected,
                "actual": actual,
            }
        )

    highlights = highlight_contribution_ids or [TRIPOD_CONTRIBUTION_ID]
    highlighted = {
        cid: next((row for row in rows if row["contribution_id"] == cid), None)
        for cid in highlights
    }
    complete = not missing and not mismatched
    return {
        "schema": DIGEST_AUDIT_SCHEMA,
        "world_id": world_id,
        "revision_id": revision_id,
        "complete": complete,
        "missing_contribution_ids": missing,
        "mismatched_contribution_ids": mismatched,
        "contribution_count": len(rows),
        "ok_count": sum(1 for row in rows if row["status"] == "ok"),
        "highlighted": highlighted,
        "rows": rows,
        "migration_guidance": (
            None
            if complete
            else (
                "rebuild_from_contributions(publish=True) then re-activate the Eldyrwild "
                "head so graph-data JSON-pointer anchors become readable."
            )
        ),
    }


__all__ = [
    "TRIPOD_CONTRIBUTION_ID",
    "audit_contribution_source_digests",
]
