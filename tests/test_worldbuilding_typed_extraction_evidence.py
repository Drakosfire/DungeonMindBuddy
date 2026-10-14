"""Typed extraction preserves all declared spans and rejects conflicting evidence."""

from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    ContributionMappingError,
    map_worldbuilding_extraction_contribution_v3,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    VerifiedGraphReviewSpan,
    build_assertions_from_proposals,
    translate_assertions_to_contribution,
)
from tests.test_graph_object_authoring_prepare import prepare_request


def fixture():
    assertions, _ = build_assertions_from_proposals(prepare_request())
    verified = {
        item.assertion_id: VerifiedGraphReviewSpan(
            assertion_id=item.assertion_id, evidence_ref_id="evidence:one",
            source_artifact_id="source", source_revision_id="sha256:" + "a" * 64,
            source_domain="worldbuilding", source_span_ref_id="span:one",
            source_content_sha256="a" * 64, span_content_sha256="b" * 64,
            span_index_sha256="c" * 64, visibility_state="internal",
        ) for item in assertions
    }
    contribution = translate_assertions_to_contribution(
        world_id="world", campaign_id="world", actor="test",
        source_artifact_id="source", source_revision_id="sha256:" + "a" * 64,
        assertions=assertions, verified_spans=verified,
    ).model_copy(update={"source_kind": "source_extraction"})
    assertion = contribution.accepted_assertions[0]
    row = assertion.value["evidence"][0]
    rows = [row, {**row, "evidence_ref_id": "evidence:two", "source_span_ref_id": "span:two"}]
    assertion = assertion.model_copy(update={
        "evidence_ref_ids": [r["evidence_ref_id"] for r in rows],
        "value": {**assertion.value, "evidence": rows},
    })
    contribution = contribution.model_copy(update={"accepted_assertions": [assertion]})
    store = SimpleNamespace(evidence={
        r["evidence_ref_id"]: SimpleNamespace(
            evidence_ref_id=r["evidence_ref_id"], source_artifact_id="source",
            source_domain="worldbuilding", evidence_role="support",
            can_open_source=True, can_highlight_span=True,
            locator=r["source_span_ref_id"], uri="repo://source",
            source_span_ref_id=r["source_span_ref_id"],
        ) for r in rows
    })
    return contribution, store, {("source", "sha256:" + "a" * 64): "native-revision"}


def test_all_spans_survive_and_identity_is_replayable():
    contribution, store, pairs = fixture()
    mapped = map_worldbuilding_extraction_contribution_v3(store, contribution, pairs)
    assert mapped.schema_version == "dm_graph_contribution_v3"
    refs = mapped.assertions[0].evidence_refs
    assert [r.source_span_ref_id for r in refs] == ["span:one", "span:two"]
    assert all(r.source_revision_id == "native-revision" for r in refs)
    assert all(r.source_domain.value == "worldbuilding" for r in refs)
    assert len({r.evidence_ref_id for r in refs}) == 2
    assert mapped == map_worldbuilding_extraction_contribution_v3(store, contribution, pairs)


@pytest.mark.parametrize("field,value", [
    ("source_span_ref_id", ""), ("source_artifact_id", "wrong"),
    ("source_domain", "session_recap"), ("evidence_ref_id", "unknown"),
])
def test_conflicting_declaration_rejects(field, value):
    contribution, store, pairs = fixture()
    assertion = contribution.accepted_assertions[0]
    rows = [dict(row) for row in assertion.value["evidence"]]
    rows[0][field] = value
    assertion = assertion.model_copy(update={"value": {**assertion.value, "evidence": rows}})
    contribution = contribution.model_copy(update={"accepted_assertions": [assertion]})
    with pytest.raises(ContributionMappingError):
        map_worldbuilding_extraction_contribution_v3(store, contribution, pairs)


def test_missing_catalog_cannot_disguise_worldbuilding_as_recap():
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        WorldGraphWriteError, _recap_extraction_evidence_view,
    )
    contribution, _, pairs = fixture()
    with pytest.raises(WorldGraphWriteError) as rejected:
        _recap_extraction_evidence_view(contribution, pair_to_dm=pairs, sources=None)
    assert rejected.value.code == "source_not_admitted"


@pytest.mark.parametrize("suffix,accepted", [
    (":dm-extraction-v3:" + "a" * 64, True),
    (":dm-extraction-v3:garbage", False),
    (":dm-extraction-v3:" + "a" * 65, False),
])
def test_child_evidence_verifier_accepts_only_complete_export_identity(suffix, accepted):
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _evidence_id_on_child,
    )
    assert _evidence_id_on_child({"raw" + suffix}, "raw") is accepted
