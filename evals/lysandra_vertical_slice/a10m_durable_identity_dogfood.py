"""Thin runner for A10m Lysandra durable identity dogfood (test is source of truth).

Runnable from repo root::

    uv run python evals/lysandra_vertical_slice/a10m_durable_identity_dogfood.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.test_a10m_lysandra_durable_identity_dogfood import (  # noqa: E402
    MERGED_AWAY_NODE_ID,
    SURVIVOR_NODE_ID,
    _run_lysandra_durable_identity_pipeline,
)


def main() -> int:
    _store, _plan, applied_store, _apply_result, projection = (
        _run_lysandra_durable_identity_pipeline()
    )
    survivor = projection.node_views[SURVIVOR_NODE_ID]
    redirects = [
        f"{redirect.from_node_id} -> {redirect.to_node_id}"
        for redirect in applied_store.identity_redirects
        if redirect.status == "active"
    ]
    summary = {
        "survivor_node_id": SURVIVOR_NODE_ID,
        "merged_away_absent": MERGED_AWAY_NODE_ID not in projection.node_views,
        "redirects": redirects,
        "survivor_alias_count": len(survivor.aliases),
        "survivor_evidence_count": len(survivor.evidence_badges),
        "survivor_adjacency_count": len(survivor.adjacency),
        "diagnostics": [item.model_dump() for item in projection.union_identity_diagnostics],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
