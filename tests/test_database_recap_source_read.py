"""Public native anchor resolution joined to actual disposable APP source storage."""
import hashlib

import pytest

from application_state.source import service as storage
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from apps.live_control_server.services.source_artifact_registry import _register_source_input
from dungeonmind.contracts.evidence import SourceDomain
from dungeonmind.contracts.graph import PublishRevisionCommand
from dungeonmind.infrastructure.memory import InMemorySourceRepository, InMemoryWorldGraphRepository
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.retrieval.models import WorldGraphEvidenceRequest, WorldGraphSourceAnchorReadRequest
from tests._cutover_direct_dungeonmind_read_helpers import (
    ANCHOR_CONTENT, ANCHOR_CONTENT_DIGEST, CAMPAIGN_ONE, NOW, WORLD_ID,
    _FakeBundle, _payload, _receipt, _seed_sources,
)

pytest_plugins = ("tests.application_state.conftest",)
pytestmark = pytest.mark.usefixtures("application_state_dsn")
ARTIFACT = "src:one-recap"
URI = "repo://corpus/world_lore.md"


def _fixture():
    sources = InMemorySourceRepository()
    original = _seed_sources()
    sources.put_artifact(original.get_artifact(ARTIFACT).model_copy(update={
        "source_domain_key":"buddy.recap", "source_domain":SourceDomain.SESSION_RECAP,
        "session_id":"session-9"}))
    sources.put_revision(original.get_revision("srcrev:one-recap-v1"))
    payload = _payload()
    payload["objects"] = payload["objects"][:1]
    payload["objects"][0]["assertion_metadata"]["campaign_scope"] = CAMPAIGN_ONE
    payload["relationships"] = []
    row = payload["evidence_refs"][0]
    span = "session-9:recap:paragraph:002"
    row.update(source_domain="session_recap", source_domain_key="buddy.recap",
        source_span_ref_id=span, locator=span, uri=URI, can_highlight_span=True)
    payload["evidence_refs"] = [row]
    graphs = InMemoryWorldGraphRepository()
    result = graphs.publish_revision(PublishRevisionCommand(
        world_id=WORLD_ID, parent_revision_id=None, expected_parent_revision_id=None,
        operation_ids=["op:database-recap-read"], graph_schema="dm_union_graph_v6",
        graph_payload=payload, created_at=NOW))
    services = direct.direct_services_from_bundle(
        _FakeBundle(graphs, sources, _receipt(WORLD_ID, result.revision_id)), WORLD_ID)
    context = dict(worldId=WORLD_ID, campaignId=CAMPAIGN_ONE,
        revisionPin=result.revision_id, scopeMode="campaign")
    evidence = direct.get_evidence_direct(services, WorldGraphEvidenceRequest.model_validate({
        "schema":"dmb_world_graph_evidence_request_v1", **context,
        "target":{"kind":"node", "id":"obj:tavern"}}))
    assert len(evidence.source_anchors) == 1
    request = WorldGraphSourceAnchorReadRequest.model_validate({
        "schema":"dmb_world_graph_source_anchor_read_request_v1", **context,
        "anchorId":evidence.source_anchors[0].anchor_id})
    return services, request


def _persist(root, *, markdown=ANCHOR_CONTENT, world=WORLD_ID, campaign=CAMPAIGN_ONE):
    artifact = GraphMemorySourceArtifact(source_artifact_id=ARTIFACT,
        source_domain="recap", world_id=world, campaign_id=campaign, session_id="session-9",
        uri=URI, content_sha256=hashlib.sha256(markdown.encode()).hexdigest())
    return _register_source_input(artifact, markdown)


@pytest.mark.parametrize("case", ["no_mirror", "wrong_mirror", "missing_body", "wrong_digest", "wrong_world", "wrong_campaign", "database_unavailable"])
def test_public_read_requires_exact_database_body_not_source_file(tmp_path, monkeypatch, case):
    services, request = _fixture()
    if case != "missing_body":
        _persist(tmp_path,
            markdown="Other source bytes." if case == "wrong_digest" else ANCHOR_CONTENT,
            world="other-world" if case == "wrong_world" else WORLD_ID,
            campaign="other-campaign" if case == "wrong_campaign" else CAMPAIGN_ONE)
    if case != "no_mirror":
        path = tmp_path / URI.removeprefix("repo://")
        path.parent.mkdir(parents=True)
        path.write_text("Obsolete mirror." if case == "wrong_mirror" else ANCHOR_CONTENT)
    if case == "database_unavailable":
        from application_state.errors import ApplicationStateUnavailableError
        def unavailable(**kwargs):
            raise ApplicationStateUnavailableError("synthetic database outage")
        monkeypatch.setattr(storage, "get_source_markdown", unavailable)
    result = direct.read_source_anchor_direct(services, request, repo_root=tmp_path)
    if case in {"no_mirror", "wrong_mirror"}:
        assert result.outcome == "enough"
        assert result.content == "The Prancing Tavern at the crossroads."
        assert result.content_sha256 == ANCHOR_CONTENT_DIGEST
        assert result.source_span_ref_id == "session-9:recap:paragraph:002"
    else:
        assert result.outcome == "unavailable"
        assert result.content is None
        assert result.content_sha256 is None
        expected = ("workspace_lineage_mismatch" if case in {"wrong_world", "wrong_campaign"}
            else "source_integrity_error" if case == "wrong_digest" else "source_unavailable")
        assert result.diagnostics[0].code == expected


def test_native_anchor_revision_and_campaign_checks_still_precede_body_read(tmp_path, monkeypatch):
    services, request = _fixture()
    _persist(tmp_path)
    calls = []
    def forbidden_read(**kwargs):
        calls.append(kwargs)
        raise AssertionError("an unauthorized anchor must never read APP source bytes")
    monkeypatch.setattr(storage, "get_source_markdown", forbidden_read)
    foreign = request.model_copy(update={"campaign_id":"other-campaign"})
    result = direct.read_source_anchor_direct(services, foreign, repo_root=tmp_path)
    assert result.outcome == "empty"
    stale = request.model_copy(update={"revision_pin":"rev:unknown"})
    with pytest.raises(direct.DirectWorldGraphReadError):
        direct.read_source_anchor_direct(services, stale, repo_root=tmp_path)
    assert calls == []
