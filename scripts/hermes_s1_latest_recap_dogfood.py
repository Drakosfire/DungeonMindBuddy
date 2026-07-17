#!/usr/bin/env python3
"""Deterministic read-only gate for Hermes S1 latest-recap comparison metadata.

The gate does not call an LLM and never writes corpus or graph state. It writes
one small JSON report by default so the result remains reviewable after the
terminal closes.

Usage:
  PYTHONPATH=src:. uv run python scripts/hermes_s1_latest_recap_dogfood.py
  PYTHONPATH=src:. uv run python scripts/hermes_s1_latest_recap_dogfood.py --root out --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(REPO_ROOT), str(REPO_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from apps.live_control_server.config import world_graph_root  # noqa: E402
from graph_memory.interaction.latest_recap import (  # noqa: E402
    resolve_latest_recap_change_context,
)
from graph_memory.world_supergraph.storage import load_current_world_graph  # noqa: E402

DEFAULT_OUTPUT = REPO_ROOT / "evals/graph_memory_layer/artifacts/last_s1_latest_recap_dogfood.json"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _output_path(value: str | None) -> Path:
    configured = value or os.environ.get("DUNGEONMIND_S1_DOGFOOD_OUTPUT")
    if not configured:
        return DEFAULT_OUTPUT
    candidate = Path(configured)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _head_revision_id(root: Path, world_id: str) -> str | None:
    try:
        head, _, _ = load_current_world_graph(root, world_id)
    except Exception:
        return None
    return head.head_revision_id


def build_report(
    *,
    repo_root: Path,
    graph_root: Path,
    world_id: str,
    campaign_id: str,
) -> dict[str, Any]:
    revision_id = _head_revision_id(graph_root, world_id)
    context = resolve_latest_recap_change_context(
        root=repo_root,
        graph_root=graph_root,
        world_id=world_id,
        campaign_id=campaign_id,
        graph_revision_id=revision_id,
    )
    context_payload = context.model_dump(mode="json", by_alias=True)
    boundary = context_payload.get("comparison_boundary") or {}
    latest = context_payload.get("latest_recap") or {}
    contract_checks = {
        "latest_recap_identified": bool(latest.get("session_id")),
        "comparison_boundary_pinned": bool(
            boundary.get("recap_session_id") and boundary.get("graph_revision_id")
        ),
        "outcome_classified": context_payload.get("outcome")
        in {"changed", "no_change", "memory_lag"},
        "memory_lag_disclosed": (
            context_payload.get("outcome") != "memory_lag"
            or context_payload.get("memory_lag") is True
        ),
        "no_durable_graph_or_corpus_writes": True,
    }
    return {
        "schema": "dmb_hermes_s1_latest_recap_dogfood_report_v1",
        "created_at": _utc_now(),
        "world_id": world_id,
        "campaign_id": campaign_id,
        "question": "What changed after the latest ingested recap?",
        "ok": all(contract_checks.values()),
        "cost_usd": 0.0,
        "contract_checks": contract_checks,
        "latest_recap_change": context_payload,
        "mutations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=world_graph_root())
    parser.add_argument("--world-id", default="eldyrwild")
    parser.add_argument("--campaign-id", default="longmont-c2")
    parser.add_argument("--output", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = build_report(
        repo_root=REPO_ROOT,
        graph_root=args.root.expanduser().resolve(),
        world_id=args.world_id,
        campaign_id=args.campaign_id,
    )
    output = _output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"ok={report['ok']}")
        print(f"artifact={output}")
        print(f"cost_usd={report['cost_usd']:.2f}")
        context = report["latest_recap_change"]
        print(f"outcome={context['outcome']}")
        print(f"latest_recap_session={context.get('latest_recap', {}).get('session_id')}")
        print(
            "graph_latest_session="
            f"{(context.get('comparison_boundary') or {}).get('graph_latest_session_id')}"
        )
    return 0 if report["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
