"""Quote-only child correction never edits the frozen parent or World."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.models.extract_promote import (
    ExactRunEvidenceCorrectionRequest,
    ExactRunEvidenceQuoteCorrection,
)
from apps.live_control_server.services import (
    candidate_graph_admission,
    exact_run_evidence_correction as correction,
)
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, two_invalid: bool = False):
    source = tmp_path / "source.md"
    source.write_text("Torbin, who bought the strange seed, repaired the roof.\n")
    artifact_id = "artifact:worldbuilding:demo:r1:abc"
    span_id = f"{artifact_id}:span:abc:1-1"
    parent_payload = {
        "campaign_id": "demo",
        "session_id": None,
        "nodes": [{
            "node_id": "torbin",
            "node_type": "character",
            "label": "Torbin",
            "description": "Roof repairer",
            "evidence_refs": [{
                "source_artifact_id": artifact_id,
                "source_span_ref_id": span_id,
                "anchor_quotes": ["Torbin bought the strange seed"]
                + (["roof fixed by Torbin"] if two_invalid else []),
            }],
        }],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
    }
    parent_path = tmp_path / "parent.json"
    parent_bytes = json.dumps(parent_payload).encode()
    parent_path.write_bytes(parent_bytes)
    parent_sha = hashlib.sha256(parent_bytes).hexdigest()
    components = {
        kind.value: ExtractionRunComponentRef(kind=kind, uri=f"out/{kind.value}.json", sha256="a" * 64)
        for kind in (
            ExtractionRunComponentKind.SOURCE_ARTIFACT,
            ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            ExtractionRunComponentKind.CANDIDATE_GRAPH,
        )
    }
    parent = SimpleNamespace(
        run_id="parent", source_artifact_id=artifact_id, source_domain="worldbuilding",
        campaign_id="demo", session_id=None, profile_id=correction._PROFILE,
        components=components, status=ExtractionRunStatus.REVIEWABLE,
    )
    resolved = SimpleNamespace(
        run_id="parent", candidate_graph_path=parent_path,
        normalized_recap_path=source, source_artifact_id=artifact_id,
        campaign_id="demo", session_id=None, source_domain="worldbuilding",
        extraction_profile=correction._PROFILE, world_id="demo",
    )
    span_index = SimpleNamespace(spans=[
        SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1),
    ])
    child_store: dict[str, SimpleNamespace] = {}

    def get_run(_repo, run_id):
        if run_id == "parent":
            return parent
        if run_id in child_store:
            return child_store[run_id]
        raise GraphRunRegistryError("missing", status_code=404)

    def create_run(_repo, **kwargs):
        run = SimpleNamespace(
            run_id=kwargs["run_id"], status=kwargs["status"], revision=1,
            lineage=kwargs["lineage"], components=kwargs["components"],
            source_artifact_id=kwargs["source_artifact_id"],
        )
        child_store[run.run_id] = run
        return run

    def update_run(_repo, run_id, *, status, expected_revision):
        run = child_store[run_id]
        assert run.revision == expected_revision
        run.status = status
        run.revision += 1
        return run

    def typed(payload):
        nodes = []
        for item in payload["nodes"]:
            refs = [SimpleNamespace(**ref) for ref in item["evidence_refs"]]
            nodes.append(SimpleNamespace(
                node_id=item["node_id"], label=item["label"],
                description=item["description"], evidence_refs=refs,
            ))
        return SimpleNamespace(nodes=nodes, edges=[])

    monkeypatch.setattr(candidate_graph_admission, "validate_candidate_document_integrity", typed)
    monkeypatch.setattr(correction, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(correction, "resolve_promotable_ingest_run", lambda run_id, **_: resolved)
    monkeypatch.setattr(correction, "get_extraction_run", get_run)
    monkeypatch.setattr(correction, "create_extraction_run", create_run)
    monkeypatch.setattr(correction, "update_extraction_run_status", update_run)
    monkeypatch.setattr(correction, "_load_frozen_span_index_for_resolved_run", lambda _: span_index)
    monkeypatch.setattr(correction, "admit_managed_world", lambda *_: None)
    return parent, parent_bytes, parent_sha, span_id, child_store


def _request(sha: str, span_id: str, replacement: str = "who bought the strange seed"):
    return ExactRunEvidenceCorrectionRequest(
        parent_run_id="parent",
        parent_candidate_sha256=sha,
        corrections=[ExactRunEvidenceQuoteCorrection(
            assertion_id="torbin", evidence_index=0, source_span_ref_id=span_id,
            quote_index=0, original_quote="Torbin bought the strange seed",
            replacement_quote=replacement,
        )],
    )


def test_literal_child_is_reviewable_idempotent_and_parent_is_frozen(monkeypatch, tmp_path):
    parent, parent_bytes, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    response = correction.correct_exact_run_evidence(_request(sha, span_id))
    repeated = correction.correct_exact_run_evidence(_request(sha, span_id))

    assert response == repeated
    assert len(children) == 1
    assert children[response.run_id].status == ExtractionRunStatus.REVIEWABLE
    assert children[response.run_id].lineage["parent_candidate_sha256"] == sha
    assert parent.status == ExtractionRunStatus.REVIEWABLE
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    child_path = tmp_path / children[response.run_id].components["candidate_graph"].uri
    child_payload = json.loads(child_path.read_text())
    assert child_payload["nodes"][0]["evidence_refs"][0]["anchor_quotes"] == [
        "who bought the strange seed"
    ]
    assert child_payload["nodes"][0]["description"] == "Roof repairer"


@pytest.mark.parametrize("replacement", ["Torbin bought the strange seed", "elsewhere"])
def test_nonliteral_or_unchanged_replacement_cannot_seal(monkeypatch, tmp_path, replacement):
    _, _, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(_request(sha, span_id, replacement))
    assert not children


def test_stale_parent_sha_and_wrong_profile_fail_before_child(monkeypatch, tmp_path):
    parent, _, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(_request("0" * 64, span_id))
    parent.profile_id = "other"
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(_request(sha, span_id))
    assert not children


def test_duplicate_target_fails(monkeypatch, tmp_path):
    _, _, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    request = _request(sha, span_id)
    request.corrections.append(request.corrections[0])
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(request)
    assert not children


def test_partial_correction_and_stale_target_do_not_create_a_child(monkeypatch, tmp_path):
    _, _, sha, span_id, children = _fixture(monkeypatch, tmp_path, two_invalid=True)
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(_request(sha, span_id))
    assert not children
    request = _request(sha, span_id)
    request.corrections[0].original_quote = "a different quote"
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(request)
    assert not children


def test_recap_parent_rejected(monkeypatch, tmp_path):
    parent, _, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    parent.source_domain = "recap"
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_exact_run_evidence(_request(sha, span_id))
    assert not children


def test_interrupted_draft_is_not_reviewable_and_same_request_resumes(monkeypatch, tmp_path):
    _, _, sha, span_id, children = _fixture(monkeypatch, tmp_path)
    original_update = correction.update_extraction_run_status
    interrupted = False

    def stop_once(repo, run_id, *, status, expected_revision):
        nonlocal interrupted
        if status == ExtractionRunStatus.EXTRACTED and not interrupted:
            interrupted = True
            raise RuntimeError("simulated process interruption")
        return original_update(repo, run_id, status=status, expected_revision=expected_revision)

    monkeypatch.setattr(correction, "update_extraction_run_status", stop_once)
    with pytest.raises(RuntimeError, match="simulated process interruption"):
        correction.correct_exact_run_evidence(_request(sha, span_id))
    assert len(children) == 1
    only = next(iter(children.values()))
    assert only.status == ExtractionRunStatus.PREPARED
    monkeypatch.setattr(correction, "update_extraction_run_status", original_update)
    response = correction.correct_exact_run_evidence(_request(sha, span_id))
    assert children[response.run_id].status == ExtractionRunStatus.REVIEWABLE
