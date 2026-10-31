"""Reviewed and historical source proofs bind exact APP bytes, not mirrors."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import promotable_ingest_run as resolution
from apps.live_control_server.services import recap_source_subject_proof as history
from apps.live_control_server.services import reviewed_extract_confirmation as confirmation
from apps.live_control_server.services.candidate_graph_admission import canonical_candidate_digest
from tests.test_graph_preview_runner import FixtureClient, _run_recap_extraction

pytestmark = pytest.mark.usefixtures("application_state_dsn")


def _case(monkeypatch, root, *, custom_span=False):
    _, result = _run_recap_extraction(root, client=FixtureClient())
    data = registry.load_reviewable_extraction_data(root, result.run.run_id)
    if custom_span:
        from graph_memory.source_span import build_stable_source_span_id
        from tests._cutover_d3a_blocker_safe_fixtures import _reseal_extraction_component_digest
        index, candidate = json.loads(data.span_bytes), json.loads(data.candidate_bytes)
        span = index["spans"][0].copy()
        span["start_line"], span["end_line"] = 1, len(data.source_bytes.decode().splitlines())
        span["source_span_id"] = build_stable_source_span_id(
            source_artifact_id=data.run.source_artifact_id, content_sha256=data.source_artifact.content_sha256,
            start_line=span["start_line"], end_line=span["end_line"],
        )
        assert span["source_span_id"] not in {row["source_span_id"] for row in index["spans"]}
        index["spans"] = [span]
        for row in [*candidate["nodes"], *candidate["edges"]]:
            for ref in row["evidence_refs"]:
                ref["source_span_ref_id"] = span["source_span_id"]
        for kind, payload in (("candidate_graph", candidate), ("source_span_index", index)):
            raw = json.dumps(payload, sort_keys=True).encode()
            _reseal_extraction_component_digest(data.run.run_id, kind=kind,
                digest=sha256(raw).hexdigest(), payload=raw)
        data = registry.load_reviewable_extraction_data(root, data.run.run_id)
    resolved = resolution.resolve_promotable_ingest_run(data.run.run_id, root=root)
    raw = json.loads(data.candidate_bytes)
    selected = "selected:synthetic"
    refs = raw["nodes"][0]["evidence_refs"]
    review = SimpleNamespace(
        source_run_id=data.run.run_id, source_artifact_id=data.run.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        source_body_sha256=sha256(data.source_bytes).hexdigest(),
        source_span_index_sha256=sha256(data.span_bytes).hexdigest(),
        candidate_graph_sha256=sha256(data.candidate_bytes).hexdigest(),
        candidate_admission_digest=canonical_candidate_digest(raw), selected_assertion_ids=[selected],
    )
    package = {"effect": {
        "world_id": data.source_artifact.world_id,
        "source_artifact_id": data.run.source_artifact_id,
        "source_revision_id": resolved.source_revision_id,
        "candidate_admission": {"candidate_digest": canonical_candidate_digest(raw)},
        "contribution_meta": {"campaign_scope": data.run.campaign_id},
        "accepted_proposals": [{"assertion_id": selected, "value": {"evidence": refs}}],
    }}
    package = resolution.seal_extraction_run(package, data)
    context = SimpleNamespace(managed_world_id=data.source_artifact.world_id, native_world_id=data.source_artifact.world_id)
    return SimpleNamespace(data=data, resolved=resolved, review=review, package=package, context=context, root=root)


def _confirm_source(case):
    return confirmation._verify_run_bytes(case.review, case.package, context=case.context, repo_root=case.root)


@pytest.mark.parametrize("custom_span", [False, True])
def test_proofs_use_database_bytes_and_exact_run_spans_without_any_files(monkeypatch, tmp_path, custom_span):
    case = _case(monkeypatch, tmp_path, custom_span=custom_span)
    for path in tmp_path.rglob("*"):
        if path.is_file():
            path.unlink()
    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", lambda *_a, **_k: pytest.fail("source proof reopened a file mirror"))
        data, resolved, raw, typed = history._source_run(tmp_path, case.data.run.run_id)
        assert _confirm_source(case) == raw
    assert data == case.data and resolved == case.resolved
    assert typed.nodes and data.span_index == case.data.span_index
    assert {ref.source_span_ref_id for node in typed.nodes for ref in node.evidence_refs} <= {
        span.source_span_id for span in data.span_index.spans}


@pytest.mark.parametrize("kind", ["source_artifact", "candidate_graph", "source_span_index"])
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_database_failure_cannot_fall_back_to_valid_files(monkeypatch, tmp_path, application_state_dsn, kind, violation):
    case = _case(monkeypatch, tmp_path)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute("DELETE FROM source.revision WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
            else:
                conn.execute("UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s", (case.data.run.source_artifact_id,))
        elif violation == "missing":
            conn.execute("DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s", (case.data.run.run_id, kind))
        else:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s",
                         (b"corrupt", case.data.run.run_id, kind))
    with pytest.raises(confirmation.ReviewedExtractConfirmationError) as failure:
        _confirm_source(case)
    assert failure.value.code == "source_unavailable"
    with pytest.raises(history.SourceSubjectProofError):
        history._source_run(tmp_path, case.data.run.run_id)
    assert registry.get_extraction_run(tmp_path, case.data.run.run_id) == case.data.run


@pytest.mark.parametrize("pin", ["source_body_sha256", "candidate_graph_sha256", "source_span_index_sha256", "candidate_admission_digest"])
def test_review_pins_still_reject_drift(monkeypatch, tmp_path, pin):
    case = _case(monkeypatch, tmp_path)
    setattr(case.review, pin, "f" * 64)
    with pytest.raises(confirmation.ReviewedExtractConfirmationError) as failure:
        _confirm_source(case)
    assert failure.value.code == "source_digest_drift"


def test_resolved_foreign_scope_cannot_substitute_for_stored_run(monkeypatch, tmp_path):
    case = _case(monkeypatch, tmp_path)
    foreign = replace(case.resolved, world_id="foreign-world")
    monkeypatch.setattr(resolution, "resolve_promotable_ingest_run", lambda *_a, **_k: foreign)
    with pytest.raises(history.SourceSubjectProofError):
        history._source_run(tmp_path, case.data.run.run_id)
    case.context.native_world_id = "foreign-world"
    with pytest.raises(confirmation.ReviewedExtractConfirmationError) as failure:
        _confirm_source(case)
    assert failure.value.code == "source_digest_drift"


def test_selected_claim_still_requires_the_run_pinned_span(monkeypatch, tmp_path):
    case = _case(monkeypatch, tmp_path)
    case.package["effect"]["accepted_proposals"][0]["value"]["evidence"] = [{
        "source_artifact_id": case.review.source_artifact_id, "source_span_ref_id": "span:foreign",
    }]
    from graph_memory.extract_promote_proposal import compute_proposal_digest
    case.package["proposal_digest"] = compute_proposal_digest(case.package["effect"])
    with pytest.raises(confirmation.ReviewedExtractConfirmationError) as failure:
        _confirm_source(case)
    assert failure.value.code == "source_span_drift"


def test_nonreviewable_database_run_cannot_be_proven(monkeypatch, tmp_path):
    from tests._cutover_d3a_blocker_safe_fixtures import _patch_extraction_run
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus
    case = _case(monkeypatch, tmp_path)
    _patch_extraction_run(case.data.run.run_id, status=ExtractionRunStatus.VALIDATED)
    with pytest.raises(confirmation.ReviewedExtractConfirmationError) as failure:
        _confirm_source(case)
    assert failure.value.code == "source_unavailable"
    with pytest.raises(history.SourceSubjectProofError):
        history._source_run(tmp_path, case.data.run.run_id)
