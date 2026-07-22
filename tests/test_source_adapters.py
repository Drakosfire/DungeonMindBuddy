from __future__ import annotations

from src.graph_memory.extraction.recap_source_adapter import RecapSourceAdapter
from src.graph_memory.extraction.worldbuilding_source_adapter import WorldbuildingSourceAdapter


def test_recap_adapter_preserves_session_identity(tmp_path) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("First paragraph.\n\nSecond paragraph about Mirathorn.\n")
    source = RecapSourceAdapter(
        campaign_id="longmont-c2",
        session_id="session-24",
        recap_path=recap,
    ).normalize()
    assert source.source_domain == "recap"
    assert source.session_id == "session-24"
    assert source.campaign_id == "longmont-c2"
    assert source.source_artifact_id == "artifact:recap:longmont-c2:session-24"
    assert source.source_span_index["paragraph_span_count"] == 2
    assert source.source_span_index["session_id"] == "session-24"


def test_worldbuilding_adapter_keeps_session_null(tmp_path) -> None:
    path = tmp_path / "lore.md"
    path.write_text("Mirathorn is a river city.\n\nThe docks are crowded.\n")
    source = WorldbuildingSourceAdapter(
        source_artifact_id="artifact:worldbuilding:eldyrwild:doc-1",
        source_path=path,
        campaign_id="eldyrwild",
        document_class="lore",
    ).normalize()
    assert source.source_domain == "worldbuilding"
    assert source.session_id is None
    assert source.source_span_index["session_id"] is None
    assert source.source_span_index["paragraph_span_count"] == 2
    span_ids = [span["span_id"] for span in source.source_span_index["spans"]]
    assert all(span_id.startswith(source.source_artifact_id) for span_id in span_ids)
