"""Paths to archived graph-memory report docs (2026-06-28 cleanup)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_MEMORY_REPORT_ARCHIVE = (
    REPO_ROOT / "Docs" / "Reports" / "archive" / "2026-06-28" / "graph-memory"
)


def archived_graph_memory_report(filename: str) -> Path:
    return GRAPH_MEMORY_REPORT_ARCHIVE / filename
