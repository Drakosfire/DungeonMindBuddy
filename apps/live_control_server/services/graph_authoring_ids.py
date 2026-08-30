"""Stable Graph Review authored object/edge ID helpers (CUTOVER D.3A).

Kept separate from overlay projection so mounted prepare/commit can import
IDs without pulling UnionSupergraph projection adapters.
"""

from __future__ import annotations

import hashlib


def authored_object_node_id(assertion_id: str) -> str:
    return f"authored:{assertion_id}"


def authored_manual_node_id(label: str, kind: str | None = None) -> str:
    key = f"{label.strip().lower()}|{(kind or '').strip().lower()}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"authored:manual:{digest}"


def authored_relationship_edge_id(assertion_id: str) -> str:
    return f"authored-rel:{assertion_id}"
