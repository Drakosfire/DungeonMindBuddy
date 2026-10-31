"""Retired file locators remain provenance metadata and cannot deliver bytes."""
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.infrastructure.memory import InMemorySourceRepository, InMemoryWorldGraphRepository
from graph_memory.retrieval.models import WorldGraphEvidenceRequest, WorldGraphSourceAnchorReadRequest
from tests._cutover_direct_dungeonmind_read_helpers import (
    CAMPAIGN_ONE, NOW, WORLD_ID, _FakeBundle, _payload, _receipt, _seed_sources,
)
from tests.test_recap_source_read_continuity import _anchor


def _file_case(tmp_path, kind, path_shape):
    raw = b"# Fixture\nFile-backed text must not become an answer.\n" if kind == "heading" else b'{"fact":"File-backed text must not become an answer."}'
    target = tmp_path / "payload"
    target.write_bytes(raw)
    if path_shape == "symlink":
        link = tmp_path / "link"
        link.symlink_to(target)
        relative = "link"
    elif path_shape == "traversal":
        root = tmp_path / "root"
        root.mkdir()
        relative = "../payload"
    else:
        relative = "payload"
    root = tmp_path / "root" if path_shape == "traversal" else tmp_path
    uri = ("repo://" if kind == "heading" else "graph-data://") + relative
    locator = "heading:Fixture" if kind == "heading" else "jsonptr:/fact"
    original = _seed_sources()
    sources = InMemorySourceRepository()
    artifact = original.get_artifact("src:one-recap")
    sources.put_artifact(artifact.model_copy(update={"uri": uri}))
    sources.put_revision(original.get_revision(artifact.current_revision_id).model_copy(update={
        "content_sha256": hashlib.sha256(raw).hexdigest()}))
    payload = _payload()
    payload["objects"] = payload["objects"][:1]
    payload["objects"][0]["assertion_metadata"]["campaign_scope"] = CAMPAIGN_ONE
    payload["relationships"] = []
    row = payload["evidence_refs"][0]
    row.update(locator=locator, source_span_ref_id=None, uri=uri)
    payload["evidence_refs"] = [row]
    graph = InMemoryWorldGraphRepository()
    published = graph.publish_revision(PublishRevisionCommand(
        world_id=WORLD_ID, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["test:retired-file-locator"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=NOW))
    services = direct.direct_services_from_bundle(_FakeBundle(graph, sources, _receipt(WORLD_ID, published.revision_id)), WORLD_ID)
    common = dict(worldId=WORLD_ID, campaignId=CAMPAIGN_ONE, revisionPin=published.revision_id, scopeMode="campaign")
    evidence = direct.get_evidence_direct(services, WorldGraphEvidenceRequest.model_validate({
        "schema": "dmb_world_graph_evidence_request_v1", **common, "target": {"kind": "node", "id": "obj:tavern"}}))
    anchor = evidence.source_anchors[0]
    request = WorldGraphSourceAnchorReadRequest.model_validate({"schema": "dmb_world_graph_source_anchor_read_request_v1", **common,
        "anchorId": anchor.anchor_id})
    return services, request, anchor, root


@pytest.mark.parametrize("kind", ["heading", "json_pointer"])
@pytest.mark.parametrize("path_shape", ["matching", "traversal", "symlink"])
def test_native_anchor_cannot_read_a_file_even_when_its_digest_matches(tmp_path, kind, path_shape):
    services, request, anchor, root = _file_case(tmp_path, kind, path_shape)
    result = direct.read_source_anchor_direct(services, request, repo_root=root)
    assert result.content is None
    assert result.outcome == "partial"
    assert result.diagnostics[0].code == "unsupported_locator"
    assert result.locator_kind == "unsupported"
    assert not anchor.readable
    assert result.source_artifact_id == anchor.source_artifact_id == "src:one-recap"
    assert result.evidence_ref_id == anchor.evidence_ref_id
    # Historical wire decoding remains available; it grants no read authority.
    old_wire = {**result.model_dump(), "locator_kind": kind}
    assert type(result).model_validate(old_wire).content is None


@pytest.mark.parametrize("kind", ["heading", "json_pointer"])
def test_retired_anchor_never_opens_a_file(tmp_path, monkeypatch, kind):
    services, request, _, root = _file_case(tmp_path, kind, "matching")
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *a, **k: pytest.fail("retired source read opened a file"))
        result = direct.read_source_anchor_direct(services, request, repo_root=root)
    assert result.content is None and result.locator_kind == "unsupported"


@pytest.mark.parametrize("domain,span", [
    ("unknown", "artifact:source:span:" + "a" * 12 + ":1-2"),
    ("player_notes", "opaque-span"), ("session_recap", "opaque-span"),
    ("session_recap", "heading:Fixture"),
])
def test_unknown_domains_and_span_shapes_do_not_gain_read_authority(domain, span):
    anchor = _anchor(domain="worldbuilding", source_span_ref_id=span, locator_identity=span,
        uri="repo://looks-safe.md")
    # Native schema admission rejects unknown domains too. Even if a malformed
    # adapter record arrives here, it cannot gain file/body read authority.
    anchor = replace(anchor, evidence=anchor.evidence.model_copy(update={"source_domain": domain}))
    assert direct._classify_locator_kind(anchor) == "unsupported"
