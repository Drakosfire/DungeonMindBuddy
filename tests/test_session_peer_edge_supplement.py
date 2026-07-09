from __future__ import annotations

from pathlib import Path

from graph_memory.projection.recap_projection import build_recap_graph_projection
from graph_memory.union_supergraph.load import load_union_supergraph_store
from graph_memory.union_supergraph.merge_reconciliation import MergeAssertionPlan, SurvivorHydrationPlan
from graph_memory.union_supergraph.merge_reconciliation_apply import _rebuild_adjacency
from graph_memory.union_supergraph.session_peer_edge_supplement import (
    supplement_identity_cluster_edges_from_session_peers,
)


def test_supplement_imports_lysandra_edges_from_session_peer_store(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    current_source = (
        repo_root
        / "out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/preview_union_supergraph.json"
    )
    peer_source = (
        repo_root
        / "out/graph_memory/runs/longmont-c2/session-23/20260629T040935Z/preview_union_supergraph.json"
    )
    if not current_source.is_file() or not peer_source.is_file():
        return

    session_dir = tmp_path / "session-23"
    current_run = session_dir / "20260629T183113Z"
    peer_run = session_dir / "20260629T040935Z"
    current_run.mkdir(parents=True)
    peer_run.mkdir(parents=True)
    current_path = current_run / "preview_union_supergraph.json"
    (peer_run / "preview_union_supergraph.json").write_text(
        peer_source.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    current_path.write_text(current_source.read_text(encoding="utf-8"), encoding="utf-8")
    store = load_union_supergraph_store(current_path)
    survivor_id = "party:captain_lysandra_ironveil"
    store.edges = {
        edge_id: edge
        for edge_id, edge in store.edges.items()
        if edge.source_node_id != survivor_id and edge.target_node_id != survivor_id
    }

    assertion_plan = MergeAssertionPlan(
        assertion_id="assert-47d2fb92482330f6",
        survivor_node_id="party:captain_lysandra_ironveil",
        merged_away_original_refs=("node:lysandra", "character_captain_lysandra_ironveil"),
        merged_away_node_ids=("node:lysandra", "character_captain_lysandra_ironveil"),
        redirects=(),
        redirects_to_retract=(),
        aliases_to_union=("Captain Lysandra Ironveil", "Lysandra"),
        evidence_ref_ids_to_union=(),
        edges_to_rewire=(),
        survivor_hydration=SurvivorHydrationPlan(
            survivor_node_id="party:captain_lysandra_ironveil",
            create_survivor_if_missing=False,
            source_node_ids=("character_captain_lysandra_ironveil",),
            aliases_to_add=("Captain Lysandra Ironveil", "Lysandra"),
            evidence_ref_ids_to_add=(),
            source_domains_to_add=("recap",),
        ),
    )

    imported, diagnostics = supplement_identity_cluster_edges_from_session_peers(
        store,
        assertion_plan,
        union_store_path=current_path,
    )

    assert imported >= 4
    assert any(item.code == "merge_apply_imported_session_peer_edges" for item in diagnostics)
    store.adjacency = _rebuild_adjacency(store)

    projection = build_recap_graph_projection(store, session_id="session-23", markdown="")
    survivor = projection.node_views["party:captain_lysandra_ironveil"]
    assert len(survivor.adjacency) >= 4
    assert {item.label for item in survivor.adjacency} >= {
        "Inn (Mireward Reach)",
        "Bonogo",
        "Karsemine",
    }
