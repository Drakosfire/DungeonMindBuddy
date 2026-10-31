"""Manual occurrence verification consumes exact APP source and run-index bytes."""
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import psycopg
import pytest

from apps.live_control_server.services import graph_object_authoring_prepare as owner
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from apps.live_control_server.services.graph_run_registry import load_reviewable_extraction_data
from tests.test_graph_object_authoring_prepare import (
    FakeSourceAdmission, FakeWorldGraphAuthority, object_proposal, prepare_request,
)
from tests.test_graph_preview_runner import (
    FixtureClient, ProductionExtractionRequest, WORLDBUILDING_PLUMBING_PROFILE_ID,
    WORLDBUILDING_PLUMBING_PROFILE_VERSION, _admit_worldbuilding, _first_paragraph_span_id,
    run_production_extraction,
)

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def case(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv(owner.GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "synthetic-database-authoring")
    source = _admit_worldbuilding(tmp_path)
    result = run_production_extraction(ProductionExtractionRequest(
        repo_root=tmp_path, source=source, profile_id=WORLDBUILDING_PLUMBING_PROFILE_ID,
        profile_version=WORLDBUILDING_PLUMBING_PROFILE_VERSION, allow_llm=True,
        category_client=FixtureClient(span_ref=_first_paragraph_span_id(source))))
    assert result.failure_kind is None
    data = load_reviewable_extraction_data(tmp_path, result.run.run_id)
    resolved = SimpleNamespace(run_id=data.run.run_id, source_artifact=data.source_artifact,
        source_artifact_id=data.run.source_artifact_id, source_domain="worldbuilding",
        source_revision_id="sha256:" + data.source_artifact.content_sha256,
        campaign_id=data.run.campaign_id, world_id=data.source_artifact.world_id,
        source_span_index_path=tmp_path / data.run.components["source_span_index"].uri.removeprefix("repo://"),
        source_span_index_sha256=data.run.components["source_span_index"].sha256)
    request = prepare_request(campaignId=data.run.campaign_id, worldId=data.run.campaign_id,
        sourceRunId=data.run.run_id, proposals=[object_proposal(selection={
            "selectionKind":"text_span", "selectedText":"Mirathorn", "normalizedSelectedText":"Mirathorn",
            "sourceSpanRefId":data.span_index.spans[0].source_span_id})])
    assertions, _ = owner.build_assertions_from_proposals(request)
    admitted = Mock(return_value=SimpleNamespace(outcome="enough", content=source.source_text.strip()))
    monkeypatch.setattr("apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span", admitted)
    from apps.live_control_server.services.graph_object_authoring_binding import GraphReviewPublicationContext
    monkeypatch.setattr("apps.live_control_server.services.graph_object_authoring_binding.resolve_publication_context",
        lambda request, resolved, **_: GraphReviewPublicationContext(request.world_id, request.campaign_id))
    return SimpleNamespace(root=tmp_path, data=data, resolved=resolved, request=request,
        assertions=assertions, admitted=admitted)


def verify(case):
    return owner.verify_graph_review_assertion_spans(assertions=case.assertions, resolved_source=case.resolved,
        source_root=case.root, world_id=case.request.world_id, campaign_id=case.request.campaign_id)


def test_graph_review_reads_actual_database_after_all_mirror_loss(case, monkeypatch):
    for path in case.root.rglob("*"):
        if path.is_file():
            path.unlink()
    monkeypatch.setattr(Path, "read_bytes", lambda *a, **k: pytest.fail("manual verifier reopened file evidence"))
    proofs = verify(case)
    [proof] = proofs.values()
    assert proof.source_artifact_id == case.data.run.source_artifact_id
    assert proof.span_index_sha256 == hashlib.sha256(case.data.span_bytes).hexdigest()
    assert proof.span_content_sha256 == hashlib.sha256(case.data.source_bytes.strip()).hexdigest()
    case.admitted.assert_called_once()


@pytest.mark.parametrize("kind", ["source", "index"])
@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_database_failure_is_not_rescued_by_valid_mirrors(case, application_state_dsn, kind, damage):
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source":
            if damage == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
        elif damage == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind='source_span_index'", (case.data.run.run_id,))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='source_span_index'", (b"corrupt", case.data.run.run_id))
    with pytest.raises(owner.GraphObjectAuthoringError) as error:
        verify(case)
    assert error.value.code == "source_span_drift"
    case.admitted.assert_not_called()


@pytest.mark.parametrize("change", ["run", "digest"])
def test_current_run_binding_is_required(case, change):
    if change == "run":
        case.resolved.run_id = "missing-run"
    else:
        case.resolved.source_span_index_sha256 = "ab" * 32
    with pytest.raises(owner.GraphObjectAuthoringError) as error:
        verify(case)
    assert error.value.code == "source_span_drift"
    case.admitted.assert_not_called()


def test_actual_database_prepare_confirm_needs_no_mirrors(case):
    for path in case.root.rglob("*"):
        if path.is_file():
            path.unlink()
    authority, admission = FakeWorldGraphAuthority(), FakeSourceAdmission()
    prepared = owner.prepare_graph_object_authoring_write(case.request, corpus_root=case.root,
        authority=authority, source_admission=admission, resolved_source=case.resolved)
    request = owner.GraphObjectAuthoringCommitRequest.model_validate({
        **case.request.model_dump(mode="json", by_alias=True), "confirmToken":prepared.confirm_token})
    receipt = commit_graph_object_authoring_write(request, corpus_root=case.root,
        authority=authority, source_admission=admission, resolved_source=case.resolved)
    assert receipt.published_revision_id == "rev:d1"
    assert authority.publish_calls == 1
