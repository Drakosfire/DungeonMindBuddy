"""Session-memory ingestion: deterministic breadcrumb → records normalization.

Canonical implementations live in this package; ``evals.sentence_routing_retrieval_falsification``
modules re-export the same symbols for benchmark compatibility.
"""

from __future__ import annotations

from src.session_memory.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    NormalizedRecord,
    normalize_breadcrumb_artifact,
    write_records_jsonl,
)

__all__ = [
    "BreadcrumbNormalizeError",
    "NormalizedRecord",
    "normalize_breadcrumb_artifact",
    "write_records_jsonl",
]
