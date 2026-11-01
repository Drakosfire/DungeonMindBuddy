"""Literal correction reads the exact stored parent, never its file mirrors."""
import json
from copy import deepcopy
from pathlib import Path

import psycopg
import pytest

from application_state.ingest import service as ingest
from apps.live_control_server.models.extract_promote import ExactRunEvidenceCorrectionRequest, ExactRunEvidenceQuoteCorrection
from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import extract_promote
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from tests._cutover_d3a_blocker_safe_fixtures import _reseal_extraction_component_digest
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction
from tests import test_build_recap_source as build_fixtures

build_source = build_fixtures.source
build_context = build_fixtures.context

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _deny_artifact_io(monkeypatch, root):
    """The public correction operation may use DB owners, never artifact files."""
    import tempfile
    original_open, original_mkdir = Path.open, Path.mkdir
    def checked_open(path, *args, **kwargs):
        assert not path.is_relative_to(root), f"artifact file opened: {path}"
        return original_open(path, *args, **kwargs)
    def checked_mkdir(path, *args, **kwargs):
        assert not path.is_relative_to(root), f"artifact directory created: {path}"
        return original_mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(Path, "mkdir", checked_mkdir)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", lambda *a, **k: pytest.fail("artifact temporary file written"))


def _false_quote_parent(monkeypatch, root, *, beat_id=None, beat_artifact=None):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    data = registry.load_reviewable_extraction_data(root, result.run.run_id)
    payload = json.loads(data.candidate_bytes)
    node = payload["nodes"][0]
    evidence = node["evidence_refs"][0]
    original = "Mirathorn was described in a nonexistent passage"
    evidence["anchor_quotes"][0] = original
    if beat_id is not None:
        beat_ref = deepcopy(evidence)
        beat_ref["anchor_quotes"][0] = "Mirathorn departed in a nonexistent episode"
        if beat_artifact is not None:
            beat_ref["source_artifact_id"] = beat_artifact
        payload["beats"].append({
            "beat_id": beat_id,
            "order": max((row["order"] for row in payload["beats"]), default=0) + 1,
            "title": "An unchanged episode",
            "summary": "A summary requiring separate semantic review.",
            "involved_node_ids": [node["node_id"]],
            "unresolved_thread_node_ids": [],
            "evidence_refs": [beat_ref],
            "proposed_action": "create",
        })
    candidate = correction._canonical_bytes(payload)
    # Explicit synthetic fixture: reviewable bytes with a false literal quote
    # are inspectable inputs to the correction capability, never published facts.
    _reseal_extraction_component_digest(result.run.run_id, kind="candidate_graph",
        digest=correction._sha(candidate), payload=candidate)
    # Preserve a custom run-pinned index rather than recomputing the canonical
    # full-source index. Every fixture node cites this selected paragraph.
    index = json.loads(data.span_bytes)
    index["spans"] = [row for row in index["spans"] if row["source_span_id"] == evidence["source_span_ref_id"]]
    assert len(index["spans"]) == 1
    custom_spans = correction._canonical_bytes(index)
    assert custom_spans != data.span_bytes
    _reseal_extraction_component_digest(result.run.run_id, kind="source_span_index",
        digest=correction._sha(custom_spans), payload=custom_spans)
    parent = registry.get_extraction_run(root, result.run.run_id)
    (root / parent.components["candidate_graph"].uri.removeprefix("repo://")).write_bytes(candidate)
    (root / parent.components["source_span_index"].uri.removeprefix("repo://")).write_bytes(custom_spans)
    monkeypatch.setattr(correction, "repo_root", lambda: root)
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: root)
    request = ExactRunEvidenceCorrectionRequest(parent_run_id=parent.run_id,
        parent_candidate_sha256=correction._sha(candidate), corrections=[ExactRunEvidenceQuoteCorrection(
            assertion_id=node["node_id"], evidence_index=0,
            source_span_ref_id=evidence["source_span_ref_id"], quote_index=0,
            original_quote=original, replacement_quote="Mirathorn")])
    if beat_id is not None:
        request.corrections.append(ExactRunEvidenceQuoteCorrection(
            assertion_id=beat_id, evidence_index=0,
            source_span_ref_id=evidence["source_span_ref_id"], quote_index=0,
            original_quote=beat_ref["anchor_quotes"][0], replacement_quote="Mirathorn"))
    return parent, request


def test_literal_correction_with_parent_files_removed(monkeypatch, tmp_path):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    before_source = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    _deny_artifact_io(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(request)
    assert response.semantic_state == "held"
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    assert child.source_bytes == before_source.source_bytes
    assert child.span_bytes == before_source.span_bytes
    assert child.run.components["source_span_index"] == parent.components["source_span_index"]
    assert correction.correct_recap_run_evidence(request) == response
    assessment = assess_recap_semantics(child.run, parent=parent,
        source_revision_id=parent.components["source_artifact"].sha256)
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    review = extract_promote.get_exact_run_review_package(child.run.run_id)
    assert review.inspection_status == "ready" and not review.promotable
    assert registry.get_extraction_run(tmp_path, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_literal_correction_cannot_use_valid_files_to_rescue_bad_database(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    before_rows = ingest.list_extraction_runs()
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (parent.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown=%s WHERE source_artifact_id=%s", ("corrupt", parent.source_artifact_id))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (parent.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", parent.run_id, kind))
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        correction.correct_recap_run_evidence(request)
    assert error.value.status_code == (500 if violation == "corrupt" and kind != "source_artifact" else 422)
    assert ingest.list_extraction_runs() == before_rows


def _check_child_storage_recovery(monkeypatch, root, dsn, parent, request, correct, kind, violation):
    from application_state.errors import ApplicationStateIntegrityError
    first = correct(request)
    child = registry.load_reviewable_extraction_data(root, first.run_id)
    payload = child.candidate_bytes if kind == "candidate_graph" else child.span_bytes
    ref = child.run.components[kind]
    # A valid old file is deliberately present; it grants no recovery authority.
    mirror = root / ref.uri.removeprefix("repo://")
    mirror.parent.mkdir(parents=True, exist_ok=True)
    mirror.write_bytes(payload)
    before = ingest.list_extraction_runs()
    with psycopg.connect(dsn) as conn:
        if violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (first.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s", (b"corrupt", first.run_id, kind))
    _deny_artifact_io(monkeypatch, root)
    if violation == "missing":
        # Existing owner permits exact referenced-byte restoration on explicit replay.
        assert correct(request) == first
        restored = registry.load_reviewable_extraction_data(root, first.run_id)
        assert restored.candidate_bytes == child.candidate_bytes
        assert restored.span_bytes == child.span_bytes
    else:
        with pytest.raises(ApplicationStateIntegrityError, match="stored extraction output differs"):
            correct(request)
    assert ingest.list_extraction_runs() == before
    assert registry.get_extraction_run(root, parent.run_id) == parent


@pytest.mark.parametrize("kind", ["candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_recap_child_payload_recovery_uses_only_database_owner(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    parent, request = _false_quote_parent(monkeypatch, tmp_path)
    _check_child_storage_recovery(monkeypatch, tmp_path, application_state_dsn, parent, request,
        correction.correct_recap_run_evidence, kind, violation)


def _project_last_beat(data):
    # Same typed record and exact projector used by native recap _intent.
    from graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
    beat = candidate_graph_preview_from_dict(json.loads(data.candidate_bytes)).beats[-1]
    return extract_promote.project_candidate_record_evidence(
        assertion_id=beat.beat_id, kind="object", label=beat.title, summary="",
        evidence_refs=beat.evidence_refs, source_prose=data.source_bytes.decode(),
        source_artifact_id=data.source_artifact.source_artifact_id, span_index=data.span_index)


def test_recap_beat_quote_correction_preserves_episode_and_source(monkeypatch, tmp_path):
    parent, request = _false_quote_parent(monkeypatch, tmp_path, beat_id="beat:retained")
    before = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    with pytest.raises(extract_promote.ExtractPromoteError, match="anchor quote"):
        _project_last_beat(before)
    _deny_artifact_io(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(request)
    assert response.semantic_state == "held"
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    assert child.source_bytes == before.source_bytes
    assert child.span_bytes == before.span_bytes
    assert child.run.components["source_artifact"] == parent.components["source_artifact"]
    assert child.run.components["source_span_index"] == parent.components["source_span_index"]
    expected = json.loads(before.candidate_bytes)
    expected["nodes"][0]["evidence_refs"][0]["anchor_quotes"][0] = "Mirathorn"
    expected["beats"][-1]["evidence_refs"][0]["anchor_quotes"][0] = "Mirathorn"
    assert json.loads(child.candidate_bytes) == expected
    projected = _project_last_beat(child)
    assert projected.assertion_id == "beat:retained"
    assert projected.evidence[0].anchor_quotes == ["Mirathorn"]
    assert not projected.evidence[0].invalid_anchor_quotes
    assert correction.correct_recap_run_evidence(request) == response
    assert registry.load_reviewable_extraction_data(tmp_path, parent.run_id) == before
    assessment = assess_recap_semantics(child.run, parent=parent,
        source_revision_id=parent.components["source_artifact"].sha256)
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256


@pytest.mark.parametrize("violation", [
    "missing", "ambiguous", "stale_quote", "quote_index", "evidence_index", "span", "nonliteral",
])
def test_recap_beat_invalid_correction_creates_no_child(monkeypatch, tmp_path, violation):
    parent, request = _false_quote_parent(monkeypatch, tmp_path, beat_id="beat:retained")
    if violation == "ambiguous":
        data = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
        payload = json.loads(data.candidate_bytes)
        payload["beats"][-1]["beat_id"] = payload["nodes"][0]["node_id"]
        candidate = correction._canonical_bytes(payload)
        _reseal_extraction_component_digest(parent.run_id, kind="candidate_graph",
            digest=correction._sha(candidate), payload=candidate)
        request.parent_candidate_sha256 = correction._sha(candidate)
        request.corrections[-1].assertion_id = payload["nodes"][0]["node_id"]
        # Avoid a duplicate request target: ambiguity is in the saved candidate.
        request.corrections = request.corrections[-1:]
    else:
        target = request.corrections[-1]
        if violation == "missing":
            target.assertion_id = "beat:missing"
        elif violation == "stale_quote":
            target.original_quote = "a stale quote"
        elif violation == "quote_index":
            target.quote_index = 4
        elif violation == "evidence_index":
            target.evidence_index = 4
        elif violation == "span":
            target.source_span_ref_id = "span:wrong"
        elif violation == "nonliteral":
            target.replacement_quote = "not in this source"
    before = registry.load_reviewable_extraction_data(tmp_path, parent.run_id)
    rows = ingest.list_extraction_runs()
    _deny_artifact_io(monkeypatch, tmp_path)
    with pytest.raises(extract_promote.ExtractPromoteError):
        correction.correct_recap_run_evidence(request)
    assert ingest.list_extraction_runs() == rows
    assert registry.load_reviewable_extraction_data(tmp_path, parent.run_id) == before


@pytest.mark.parametrize("violation", ["remaining_false_quote", "foreign_artifact", "missing_artifact"])
def test_held_recap_child_does_not_override_native_beat_evidence_gate(monkeypatch, tmp_path, violation):
    artifact = {"foreign_artifact": "artifact:foreign", "missing_artifact": ""}.get(violation)
    parent, request = _false_quote_parent(monkeypatch, tmp_path,
        beat_id="beat:retained", beat_artifact=artifact)
    if violation == "remaining_false_quote":
        request.corrections = request.corrections[:1]
    _deny_artifact_io(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(request)
    assert response.semantic_state == "held"
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    with pytest.raises(extract_promote.ExtractPromoteError):
        _project_last_beat(child)
    assert child.run.lineage["semantic_disposition"]["state"] == "held"


def _historical_quote_parent(monkeypatch, root, history):
    from apps.live_control_server.services import source_artifact_registry as sources
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
    from tests import test_graph_preview_runner as runner_fixtures

    def unscoped_source(path):
        text = "Mirathorn is a river city.\n\nGuards watch the gate.\n"
        digest = correction._sha(text.encode())
        artifact = GraphMemorySourceArtifact(
            source_artifact_id="artifact:recap:longmont-c2:session-24:" + digest[:12],
            source_domain="recap", campaign_id="longmont-c2", session_id="session-24",
            uri="object://retained-original", content_sha256=digest,
            artifact_kind="recap_markdown", document_class="recap", visibility_state="internal")
        sources._register_source_input(artifact=artifact, content=text)
        return runner_fixtures._normalized_from_artifact(path, artifact.source_artifact_id)

    monkeypatch.setattr(runner_fixtures, "_admit_recap", unscoped_source)
    monkeypatch.setattr(runner_fixtures, "_recap_run_lineage", lambda source: deepcopy(history))
    parent, request = _false_quote_parent(monkeypatch, root)
    unowned = registry.load_reviewable_extraction_data(root, parent.run_id)
    assert unowned.source_artifact.world_id is None
    # Actual source owner performs the permitted explicit NULL -> World assignment.
    sources._register_source_input(artifact=unowned.source_artifact.model_copy(
        update={"world_id": "world:elderwyld"}), content=unowned.source_bytes.decode())
    adopted = registry.load_reviewable_extraction_data(root, parent.run_id)
    assert adopted.source_artifact.world_id == "world:elderwyld"
    assert adopted.source_bytes == unowned.source_bytes
    assert adopted.run == unowned.run == parent
    assert adopted.source_artifact.source_artifact_id == unowned.source_artifact.source_artifact_id
    return parent, request, adopted


_HISTORICAL_CONTEXT = {
    "schema": "dm_world_campaign_ingest_context_v1", "managed_world_id": "earlier-managed",
    "native_world_id": "world:earlier", "campaign_id": "longmont-c2", "binding_version": 1,
    "head_revision_id": "rev:earlier", "graph_schema": "old-generation-schema",
    "graph_payload_sha256": "a" * 64,
}


@pytest.mark.parametrize("history", [
    {},
    {"native_world_id": "world:earlier", "campaign_id": "longmont-c2"},
    {"world_campaign_ingest_context": _HISTORICAL_CONTEXT},
])
def test_adopted_parent_correction_preserves_generation_history(monkeypatch, tmp_path, history):
    from application_state.source import service as sources
    parent, request, before = _historical_quote_parent(monkeypatch, tmp_path, history)
    source_before = sources.get_source_markdown(source_artifact_id=parent.source_artifact_id,
        content_sha256=parent.components["source_artifact"].sha256)
    _deny_artifact_io(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(request)
    child = registry.load_reviewable_extraction_data(tmp_path, response.run_id)
    assert response.semantic_state == "held"
    assert child.run.lineage["semantic_disposition"]["state"] == "held"
    for key in ("native_world_id", "campaign_id", "world_campaign_ingest_context"):
        if key in history:
            assert child.run.lineage[key] == history[key]
        else:
            assert key not in child.run.lineage
    assert child.run.components["source_artifact"] == parent.components["source_artifact"]
    assert child.source_bytes == before.source_bytes and child.span_bytes == before.span_bytes
    assert child.source_artifact.world_id == "world:elderwyld"
    assert sources.get_source_markdown(source_artifact_id=parent.source_artifact_id,
        content_sha256=parent.components["source_artifact"].sha256) == source_before
    expected = json.loads(before.candidate_bytes)
    expected["nodes"][0]["evidence_refs"][0]["anchor_quotes"][0] = "Mirathorn"
    assert json.loads(child.candidate_bytes) == expected
    assert correction.correct_recap_run_evidence(request) == response
    assert registry.load_reviewable_extraction_data(tmp_path, parent.run_id) == before


@pytest.mark.parametrize("history", [
    {"world_campaign_ingest_context": "not-an-object"},
    {"world_campaign_ingest_context": {"native_world_id": "world:earlier", "campaign_id": "longmont-c2"}},
    *({"world_campaign_ingest_context": {**_HISTORICAL_CONTEXT, key: value}} for key, value in [
        ("schema", "wrong-schema"), ("managed_world_id", ""), ("head_revision_id", ""),
        ("binding_version", True), ("binding_version", 0), ("binding_version", None),
        ("graph_payload_sha256", "bad-digest"), ("native_world_id", " world:earlier "),
    ]),
    {"world_campaign_ingest_context": {"native_world_id": ""}},
    {"world_campaign_ingest_context": {"native_world_id": "world:earlier", "campaign_id": "wrong-campaign"}},
    {"native_world_id": ""}, {"native_world_id": 23},
    {"native_world_id": "world:earlier", "campaign_id": "wrong-campaign"},
])
def test_malformed_supplied_context_is_not_repaired_or_retagged(monkeypatch, tmp_path, history):
    parent, request, before = _historical_quote_parent(monkeypatch, tmp_path, history)
    rows = ingest.list_extraction_runs()
    _deny_artifact_io(monkeypatch, tmp_path)
    with pytest.raises(extract_promote.ExtractPromoteError, match="invalid frozen World context"):
        correction.correct_recap_run_evidence(request)
    assert ingest.list_extraction_runs() == rows
    assert registry.load_reviewable_extraction_data(tmp_path, parent.run_id) == before


@pytest.mark.parametrize("violation", ["missing_context", "foreign_world", "foreign_campaign", "stale_body"])
def test_fresh_build_rejects_bad_input_before_generic_storage(
    monkeypatch, tmp_path, build_source, build_context, violation,
):
    from dataclasses import replace
    from uuid import uuid4
    from apps.live_control_server.models.build_recap_launch import BuildRecapLaunchRequest
    from apps.live_control_server.services import build_recap_launch
    from apps.live_control_server.services.source_artifact_registry import SourceArtifactRegistryError

    record, _, _, digest = build_source
    context = (None if violation == "missing_context" else
        replace(build_context, managed_world_id="foreign-managed") if violation == "foreign_world" else
        replace(build_context, campaign_id="foreign-campaign") if violation == "foreign_campaign" else build_context)
    monkeypatch.setattr(build_recap_launch, "read_recap_ingest_context", lambda **kw: context)
    monkeypatch.setattr(build_recap_launch, "create_extraction_run",
        lambda *a, **k: pytest.fail("invalid fresh input reached generic candidate storage"))
    monkeypatch.setattr(build_recap_launch, "run_recap_production_extraction",
        lambda *a, **k: pytest.fail("invalid fresh input reached inference"))
    request = BuildRecapLaunchRequest(request_id=uuid4(), document_id=record.document_id,
        expected_revision=record.revision, expected_content_sha256="0" * 64 if violation == "stale_body" else digest,
        managed_world_id="managed-a", campaign_id="longmont-c2", session=30)
    with pytest.raises(SourceArtifactRegistryError):
        build_recap_launch.launch_build_recap(tmp_path, request)
    assert ingest.list_extraction_runs() == []


def test_history_parser_does_not_relax_historical_source_binding():
    assert registry.validate_recap_run_generation_context(
        _HISTORICAL_CONTEXT, campaign_id="longmont-c2") == "world:earlier"
    with pytest.raises(registry.GraphRunRegistryError, match="does not match its exact"):
        registry.validate_recap_source_run_world_binding(source_world_id="world:current",
            campaign_id="longmont-c2", lineage={"world_campaign_ingest_context": _HISTORICAL_CONTEXT})
    assert registry.validate_recap_source_run_world_binding(source_world_id=None,
        campaign_id="longmont-c2", lineage={"world_campaign_ingest_context": "unscoped history"}) is None
