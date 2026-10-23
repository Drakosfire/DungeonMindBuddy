"""Exact frozen-run occurrence proof at the shared prepare/confirm boundary."""
import hashlib
import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, GraphObjectAuthoringCommitRequest,
    GraphObjectAuthoringError, build_assertions_from_proposals,
    prepare_graph_object_authoring_write, verify_graph_review_assertion_spans,
)
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from graph_memory.source_span import build_source_span_index_for_text, build_stable_source_span_id, source_span_index_to_dict
from tests.test_graph_object_authoring_prepare import (
    CAMPAIGN_ID, FakeSourceAdmission, FakeWorldGraphAuthority, fake_resolved_source,
    object_proposal, prepare_request,
)


@pytest.fixture
def frozen(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "synthetic-run-span-test")
    text = "Mara keeps the copper bell.\n\nOren works at the quarry.\n"
    body = tmp_path / "source.md"
    body.write_text(text)
    digest = hashlib.sha256(body.read_bytes()).hexdigest()
    resolved = fake_resolved_source()
    artifact = resolved.source_artifact
    artifact.uri = "repo://source.md"
    artifact.content_sha256 = digest
    resolved.source_revision_id = "sha256:" + digest
    resolved.source_domain = "worldbuilding"
    index = build_source_span_index_for_text(source_artifact_id=artifact.source_artifact_id,
                                            content_sha256=digest, text=text)
    path = tmp_path / "frozen-index.json"
    path.write_text(json.dumps(source_span_index_to_dict(index)))
    resolved.source_span_index_path = path
    proposal = object_proposal(selection={
        "selectionKind": "text_span", "selectedText": "Mara", "normalizedSelectedText": "Mara",
        "sourceSpanRefId": index.spans[0].source_span_id,
    })
    request = prepare_request(worldId=CAMPAIGN_ID, sourceRunId="synthetic-exact-run", proposals=[proposal])
    assertions, _ = build_assertions_from_proposals(request)
    reader = Mock(return_value=SimpleNamespace(outcome="enough", content="Mara keeps the copper bell."))
    monkeypatch.setattr("apps.live_control_server.services.worldbuilding_source_span_read.read_admitted_worldbuilding_span", reader)
    return SimpleNamespace(root=tmp_path, resolved=resolved, index=index, path=path, text=text,
                           request=request, assertions=assertions, reader=reader)


def verify(f):
    return verify_graph_review_assertion_spans(assertions=f.assertions, resolved_source=f.resolved,
        source_root=f.root, world_id=CAMPAIGN_ID, campaign_id=CAMPAIGN_ID)


def test_uses_run_pinned_index_and_seals_exact_bytes(frozen, monkeypatch):
    # A canonical registry index must never replace the selected run's component.
    monkeypatch.setattr("apps.live_control_server.services.source_artifact_registry.load_source_span_index",
                        Mock(side_effect=AssertionError("canonical index substituted")))
    proof = next(iter(verify(frozen).values()))
    assert proof.source_span_ref_id == frozen.index.spans[0].source_span_id
    assert proof.span_index_sha256 == hashlib.sha256(frozen.path.read_bytes()).hexdigest()
    assert proof.span_content_sha256 == hashlib.sha256(b"Mara keeps the copper bell.").hexdigest()
    assert frozen.reader.call_args.kwargs["source_span_ref_id"] == proof.source_span_ref_id


def test_canonical_only_span_is_not_a_member_of_selected_run(frozen):
    frozen.path.write_text(json.dumps(source_span_index_to_dict(replace(frozen.index, spans=frozen.index.spans[1:]))))
    with pytest.raises(GraphObjectAuthoringError, match="one current source passage"):
        verify(frozen)
    frozen.reader.assert_not_called()


@pytest.mark.parametrize("damage", ["missing", "escaped", "artifact", "digest", "duplicate", "overlap", "out_of_range", "fraction", "malformed"])
def test_bad_frozen_index_fails_before_registered_reader(frozen, damage):
    payload = source_span_index_to_dict(frozen.index)
    if damage == "missing":
        frozen.resolved.source_span_index_path = None
    elif damage == "escaped":
        frozen.resolved.source_span_index_path = frozen.root.parent / "outside.json"
    elif damage == "artifact":
        payload["source_artifact_id"] = "another-artifact"
    elif damage == "digest":
        payload["content_sha256"] = "ab" * 32
    elif damage == "duplicate":
        payload["spans"].append(payload["spans"][0])
    elif damage in {"overlap", "out_of_range"}:
        span = payload["spans"][1] if damage == "overlap" else payload["spans"][0]
        span["start_line"] = 1
        span["end_line"] = 3 if damage == "overlap" else 999
        span["source_span_id"] = build_stable_source_span_id(
            source_artifact_id=frozen.index.source_artifact_id,
            content_sha256=frozen.index.content_sha256, start_line=span["start_line"], end_line=span["end_line"])

    elif damage == "fraction":
        payload["spans"][0]["start_line"] = 1.5
    elif damage == "malformed":
        payload = []
    frozen.path.write_text(json.dumps(payload))
    with pytest.raises(GraphObjectAuthoringError) as error:
        verify(frozen)
    assert error.value.code == "source_span_drift"
    frozen.reader.assert_not_called()


def test_registered_reader_disagreement_is_not_published(frozen):
    frozen.reader.return_value.content = "Different admitted passage."
    with pytest.raises(GraphObjectAuthoringError, match="registered source passage changed"):
        verify(frozen)


def test_repeated_quote_inside_one_frozen_span_is_ambiguous(frozen):
    text = "Mara calls Mara.\n"
    (frozen.root / "source.md").write_text(text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    frozen.resolved.source_artifact.content_sha256 = digest
    frozen.resolved.source_revision_id = "sha256:" + digest
    index = build_source_span_index_for_text(source_artifact_id=frozen.index.source_artifact_id,
                                            content_sha256=digest, text=text)
    frozen.path.write_text(json.dumps(source_span_index_to_dict(index)))
    frozen.assertions[0].source_anchor.source_span_ref_id = index.spans[0].source_span_id
    with pytest.raises(GraphObjectAuthoringError, match="unique occurrence"):
        verify(frozen)
    frozen.reader.assert_not_called()


def test_worldbuilding_requires_explicit_frozen_span(frozen):
    frozen.assertions[0].source_anchor.source_span_ref_id = None
    with pytest.raises(GraphObjectAuthoringError, match="unique occurrence"):
        verify(frozen)


@pytest.mark.parametrize("change_index", [False, True])
def test_prepare_confirm_reverifies_frozen_index_before_native_append(frozen, change_index):
    authority, admission = FakeWorldGraphAuthority(), FakeSourceAdmission()
    prepared = prepare_graph_object_authoring_write(frozen.request, corpus_root=frozen.root,
        authority=authority, source_admission=admission, resolved_source=frozen.resolved)
    request = GraphObjectAuthoringCommitRequest.model_validate({**frozen.request.model_dump(mode="json", by_alias=True),
                                                              "confirmToken": prepared.confirm_token})
    if change_index:
        # Same selected passage, different frozen component bytes. No silent rebind.
        frozen.path.write_text(json.dumps(source_span_index_to_dict(frozen.index), indent=2))
        with pytest.raises(GraphObjectAuthoringError) as error:
            commit_graph_object_authoring_write(request, corpus_root=frozen.root, authority=authority,
                source_admission=admission, resolved_source=frozen.resolved)
        assert error.value.code == "confirmation_invalid"
        assert authority.publish_calls == 0
    else:
        receipt = commit_graph_object_authoring_write(request, corpus_root=frozen.root, authority=authority,
            source_admission=admission, resolved_source=frozen.resolved)
        assert receipt.published_revision_id == "rev:d1"
        assert authority.publish_calls == 1
