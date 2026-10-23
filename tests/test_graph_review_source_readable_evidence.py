"""Graph Review passage selection is bound to registered current bytes."""

from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
    GraphObjectAuthoringError,
    GraphObjectAuthoringPrepareRequest,
    build_assertions_from_proposals,
    resolve_graph_review_source,
    verify_graph_review_assertion_spans,
    prepare_graph_object_authoring_write,
)
from apps.live_control_server.services.graph_object_authoring_commit import commit_graph_object_authoring_write
from apps.live_control_server.services.recap_artifacts import (
    RecapArtifactRecord,
    upsert_recap_artifact_record,
)
from tests.test_graph_object_authoring_published_recap_write import (
    DurableTestAuthority,
    RecapSourceAdmission,
    _commit_request,
    _recap_request,
)
from tests.test_graph_object_authoring_prepare import object_proposal, prepare_request


def _registered_recap(root: Path, text: str) -> Path:
    path = root / "recaps" / "session-2.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    digest = sha256(path.read_bytes()).hexdigest()
    upsert_recap_artifact_record(
        root,
        RecapArtifactRecord(
            artifact_id="longmont-c1/session-2",
            campaign_id="longmont-c1",
            session_id="session-2",
            source_recap_path="recaps/session-2.md",
            run_bundle_uri="",
            run_manifest_uri="",
            source_span_index_uri="",
            source_sha256=digest,
            registered_at="1970-01-01T00:00:00Z",
            updated_at="1970-01-01T00:00:00Z",
        ),
    )
    return path


def _verify(root: Path, *, omit_ordinal: bool = False):
    request = _recap_request(local_id="one", label="Duplicate object")
    if omit_ordinal:
        payload = request.model_dump(by_alias=True)
        payload["proposals"][0]["selection"]["paragraphOrdinal"] = None
        request = GraphObjectAuthoringPrepareRequest.model_validate(payload)
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    resolved = resolve_graph_review_source(request, authored_world="eldyrwild", source_root=root)
    return verify_graph_review_assertion_spans(
        assertions=assertions,
        resolved_source=resolved,
        source_root=root,
        world_id="eldyrwild",
        campaign_id="longmont-c1",
    )


def test_registered_recap_passage_is_readable(tmp_path: Path) -> None:
    _registered_recap(tmp_path, "# Published recap\nA duplicate label appears.\n")
    verified = next(iter(_verify(tmp_path).values()))
    assert verified.source_domain == "session_recap"
    assert verified.source_span_ref_id.endswith(":paragraph:1")
    assert verified.span_content_sha256 == sha256(
        b"# Published recap\nA duplicate label appears."
    ).hexdigest()


def test_registered_recap_body_drift_fails_closed(tmp_path: Path) -> None:
    path = _registered_recap(tmp_path, "# Published recap\nA duplicate label appears.\n")
    path.write_text("# Published recap\nA changed label appears.\n", encoding="utf-8")
    with pytest.raises(GraphObjectAuthoringError) as exc:
        _verify(tmp_path)
    assert exc.value.code == "source_inadmissible"


def test_ambiguous_recap_selection_fails_closed(tmp_path: Path) -> None:
    _registered_recap(
        tmp_path,
        "# Published recap\nA duplicate label appears.\n\nA duplicate label appears. Again.\n",
    )
    with pytest.raises(GraphObjectAuthoringError) as exc:
        _verify(tmp_path, omit_ordinal=True)
    assert exc.value.code == "source_span_unreadable"


def test_prepare_to_confirm_body_drift_prevents_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "span-drift-test-key")
    path = _registered_recap(tmp_path, "# Published recap\nA duplicate label appears.\n")
    request = _recap_request(local_id="one", label="Duplicate object")
    authority = DurableTestAuthority()
    prepare = prepare_graph_object_authoring_write(
        request,
        corpus_root=tmp_path,
        authority=authority,
        source_admission=RecapSourceAdmission(),
    )
    path.write_text("# Published recap\nA changed label appears.\n", encoding="utf-8")
    with pytest.raises(GraphObjectAuthoringError):
        commit_graph_object_authoring_write(
            _commit_request(prepare, request),
            corpus_root=tmp_path,
            authority=authority,
            source_admission=RecapSourceAdmission(),
        )
    assert authority.publish_calls == 0


def _worldbuilding_case(root: Path):
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
        source_span_index_path,
    )

    (root / "corpus/longmont-c1-markdown").mkdir(parents=True)
    document = create_workspace_document(
        root,
        title="Readable Graph Review source",
        campaign_id="longmont-c1",
        world_id="longmont-c1",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        root, document.document_id, expected_revision=document.revision
    )
    path = root / committed.target_relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Guild\n\nA named guild guards the road.\n", encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        root, document_id=committed.document_id, expected_revision=committed.revision
    )
    request = prepare_request(
        proposals=[object_proposal(selection={
            "selectionKind": "text_span",
            "selectedText": "A named guild guards the road.",
            "normalizedSelectedText": "A named guild guards the road.",
        })]
    )
    assertions, diagnostics = build_assertions_from_proposals(request)
    assert not diagnostics
    resolved = SimpleNamespace(
        source_artifact_id=artifact.source_artifact_id,
        source_revision_id="sha256:" + artifact.content_sha256,
        source_artifact=artifact,
    )
    # Current manual authoring resolves an exact extraction-run component, not
    # the registry's mutable canonical index. Give this verifier fixture a frozen copy.
    import json
    from graph_memory.source_span import source_span_index_from_dict
    canonical = source_span_index_path(root, artifact.source_artifact_id)
    frozen_index = root / "frozen-run-index.json"
    frozen_index.write_bytes(canonical.read_bytes())
    resolved.source_span_index_path = frozen_index
    resolved.source_span_index_sha256 = sha256(frozen_index.read_bytes()).hexdigest()
    index = source_span_index_from_dict(json.loads(frozen_index.read_text()))
    assertions[0].source_anchor.source_span_ref_id = next(
        span.source_span_id for span in index.spans
        if span.start_line == 3
    )
    return assertions, resolved, path, frozen_index


def test_worldbuilding_index_and_body_are_both_required(tmp_path: Path) -> None:
    assertions, resolved, path, index_path = _worldbuilding_case(tmp_path)
    kwargs = dict(
        assertions=assertions,
        resolved_source=resolved,
        source_root=tmp_path,
        world_id="longmont-c1",
        campaign_id="longmont-c1",
    )
    verified = next(iter(verify_graph_review_assertion_spans(**kwargs).values()))
    assert verified.source_domain == "worldbuilding"
    assert verified.span_index_sha256 == sha256(index_path.read_bytes()).hexdigest()
    index_path.unlink()
    with pytest.raises(GraphObjectAuthoringError):
        verify_graph_review_assertion_spans(**kwargs)


def test_worldbuilding_wrong_digest_and_scope_fail_closed(tmp_path: Path) -> None:
    assertions, resolved, path, _index_path = _worldbuilding_case(tmp_path)
    kwargs = dict(
        assertions=assertions,
        resolved_source=resolved,
        source_root=tmp_path,
        world_id="longmont-c1",
        campaign_id="longmont-c1",
    )
    with pytest.raises(GraphObjectAuthoringError) as scope:
        verify_graph_review_assertion_spans(**{**kwargs, "campaign_id": "another-campaign"})
    assert scope.value.code == "source_inadmissible"
    path.write_text("# Guild\n\nA changed guild guards the road.\n", encoding="utf-8")
    with pytest.raises(GraphObjectAuthoringError) as drift:
        verify_graph_review_assertion_spans(**kwargs)
    assert drift.value.code == "source_span_drift"


def test_worldbuilding_missing_selection_fails_closed(tmp_path: Path) -> None:
    assertions, resolved, _path, _index_path = _worldbuilding_case(tmp_path)
    missing = [item.model_copy(update={"source_anchor": None}) for item in assertions]
    with pytest.raises(GraphObjectAuthoringError) as exc:
        verify_graph_review_assertion_spans(
            assertions=missing,
            resolved_source=resolved,
            source_root=tmp_path,
            world_id="longmont-c1",
            campaign_id="longmont-c1",
        )
    assert exc.value.code == "source_span_unreadable"
