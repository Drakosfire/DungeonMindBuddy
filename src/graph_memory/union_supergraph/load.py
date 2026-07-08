from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph_memory.union_supergraph.model import UnionSupergraphStore

DEFAULT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[3]
    / "tests/fixtures/graph_memory/union_supergraph/longmont_c2_minimal_graph.json"
)


def load_union_supergraph_payload(path: Path = DEFAULT_FIXTURE_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_union_supergraph_store(payload: dict[str, Any]) -> UnionSupergraphStore:
    return UnionSupergraphStore.model_validate(payload)


def dump_union_supergraph_store(store: UnionSupergraphStore) -> dict[str, Any]:
    return store.model_dump(mode="json", by_alias=True)


def write_union_supergraph_store(path: Path, store: UnionSupergraphStore) -> None:
    payload = dump_union_supergraph_store(store)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def load_union_supergraph_store(
    path: Path = DEFAULT_FIXTURE_PATH,
) -> UnionSupergraphStore:
    return parse_union_supergraph_store(load_union_supergraph_payload(path))
