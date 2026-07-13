"""Unit tests for preview-union extracted node roster used by ingest diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from apps.live_control_server.services.recap_graph_preview_ingest import (
    _extracted_nodes_from_preview_union,
)


def test_extracted_nodes_from_preview_union_reads_kind_and_label(tmp_path: Path) -> None:
    store_rel = "out/preview_union_supergraph.json"
    store_path = tmp_path / store_rel
    store_path.parent.mkdir(parents=True)
    store_path.write_text(
        json.dumps(
            {
                "nodes": {
                    "character_stafl": {
                        "node_id": "character_stafl",
                        "kind": "character",
                        "label": "Stafl",
                    },
                    "location_gate": {
                        "node_id": "location_gate",
                        "kind": "location",
                        "label": "Mireward Gate",
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    rows = _extracted_nodes_from_preview_union(tmp_path, store_rel)

    assert rows == [
        {"node_id": "character_stafl", "kind": "character", "label": "Stafl"},
        {"node_id": "location_gate", "kind": "location", "label": "Mireward Gate"},
    ]


def test_extracted_nodes_from_preview_union_missing_path_is_empty(tmp_path: Path) -> None:
    assert _extracted_nodes_from_preview_union(tmp_path, None) == []
    assert _extracted_nodes_from_preview_union(tmp_path, "missing.json") == []
