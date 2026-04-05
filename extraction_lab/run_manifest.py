from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_run_manifest(
    *,
    run_id: str,
    surface: str,
    store_path: Path,
    contract: dict[str, Any],
    entity_anchor_count: int,
    fact_anchor_count: int,
    entity_count: int,
    fact_count: int,
    started_at: str,
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "surface": surface,
        "started_at": started_at,
        "completed_at": _utc_now_iso(),
        "store_path": str(store_path),
        "pipeline_contract": contract,
        "counts": {
            "entity_anchors": entity_anchor_count,
            "fact_anchors": fact_anchor_count,
            "entities_in_store": entity_count,
            "facts_in_store": fact_count,
        },
    }
