"""Native projections cannot acquire source text from checkout sidecars."""
import json
from pathlib import Path

import pytest

from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services import world_graph_projection as product
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.infrastructure.memory import InMemorySourceRepository, InMemoryWorldGraphRepository
from graph_memory.projection.world_projection import WorldGraphProjectionRequest
from tests._cutover_direct_dungeonmind_read_helpers import (
    CAMPAIGN_ONE, NOW, WORLD_ID, _FakeBundle, _payload, _receipt, _seed_sources,
)

POISON = "UNVERIFIED SIDECAR TEXT MUST NEVER BECOME GRAPH EVIDENCE"


def _case(tmp_path, monkeypatch):
    payload = _payload()
    span = "span:synthetic:projection-sidecar"
    for evidence in payload["evidence_refs"]:
        evidence["source_span_ref_id"] = span
    graph = InMemoryWorldGraphRepository()
    revision = graph.publish_revision(PublishRevisionCommand(
        world_id=WORLD_ID, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["test:projection-sidecars"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=NOW))
    originals = _seed_sources()
    sources = InMemorySourceRepository()
    for artifact_id in {row["source_artifact_id"] for row in payload["evidence_refs"]}:
        artifact = originals.get_artifact(artifact_id)
        sources.put_artifact(artifact.model_copy(update={"uri": "repo://corpus/source.md"}))
        sources.put_revision(originals.get_revision(artifact.current_revision_id))
    services = direct.direct_services_from_bundle(_FakeBundle(graph, sources, _receipt(WORLD_ID, revision.revision_id)), WORLD_ID)
    monkeypatch.setenv(config.WORLD_GRAPH_AUTHORITY_ENV, config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused")
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "native-world"))
    monkeypatch.setattr(config, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(direct, "direct_services_from_config", lambda _: services)
    request = WorldGraphProjectionRequest(schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID, campaign_id=CAMPAIGN_ONE, revision_pin=revision.revision_id,
        admissibility="gm", scope_mode="campaign",
        focus={"kind": "session", "campaign_id": CAMPAIGN_ONE, "session_id": "session-9"},
        query_text="Tavern")
    sidecar = tmp_path / "corpus/source_span_index.json"
    sidecar.parent.mkdir()
    return request, sidecar, span


@pytest.mark.parametrize("shape", ["missing", "valid", "stale", "malformed", "symlink", "directory"])
def test_mounted_native_projection_ignores_every_sidecar_shape(tmp_path, monkeypatch, shape):
    request, sidecar, span = _case(tmp_path, monkeypatch)
    before = product.project_world_graph(request)
    content = json.dumps({"spans": [{"span_id": span, "paragraph_text": POISON}]})
    if shape in {"valid", "stale"}:
        sidecar.write_text(content if shape == "valid" else json.dumps({"spans": [{"span_id": "stale", "text": POISON}]}))
    elif shape == "malformed":
        sidecar.write_text("not JSON")
    elif shape == "symlink":
        outside = tmp_path / "unrelated.json"
        outside.write_text(content)
        sidecar.symlink_to(outside)
    elif shape == "directory":
        sidecar.mkdir()
    after = product.project_world_graph(request)
    assert after.model_dump() == before.model_dump()
    assert after.nodes and after.relationships and after.query_context
    for node in after.nodes:
        for adjacent in node.adjacency:
            assert adjacent.source_excerpt is None
            assert not adjacent.source_excerpt_is_full_paragraph
            assert adjacent.source_excerpt_highlight_spans == []
    assert POISON not in after.model_dump_json()


def test_projection_does_not_open_source_files(tmp_path, monkeypatch):
    request, sidecar, span = _case(tmp_path, monkeypatch)
    sidecar.write_text(json.dumps({"spans": [{"span_id": span, "text": POISON}]}))
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("projection opened a source or sidecar file"))
        projection = product.project_world_graph(request)
    assert projection.nodes and POISON not in projection.model_dump_json()


def test_alternate_world_root_still_fails_closed(tmp_path, monkeypatch):
    request, _, _ = _case(tmp_path, monkeypatch)
    with pytest.raises(product.WorldGraphProjectionServiceError):
        product.project_world_graph(request, root=tmp_path / "alternate-world")
