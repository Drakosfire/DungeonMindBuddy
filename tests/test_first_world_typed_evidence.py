"""Current initializer mapping retains reviewed spans without compatibility paths."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind.first_world_typed_evidence import (
    map_first_world_typed_contribution,
)
from tests.test_worldbuilding_typed_extraction_evidence import fixture
from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
    ContributionMappingError,
)


def mapped(contribution, pairs):
    return map_first_world_typed_contribution(
        contribution,
        artifacts=[SimpleNamespace(source_artifact_id="source")],
        pair_to_dm=pairs,
        party_registry=False,
    )


def test_current_extraction_retains_all_spans():
    contribution, _store, pairs = fixture()
    result = mapped(contribution, pairs)
    assert result.schema_version == "dm_graph_contribution_v3"
    assert [ref.source_span_ref_id for ref in result.assertions[0].evidence_refs] == [
        "span:one",
        "span:two",
    ]
    assert all(
        ref.can_open_source and ref.can_highlight_span
        for ref in result.assertions[0].evidence_refs
    )
    assert mapped(contribution, pairs) == result


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_span_ref_id", None),
        ("source_artifact_id", "foreign"),
        ("source_domain", "session_recap"),
        ("source_revision_id", "sha256:" + "f" * 64),
        ("evidence_ref_id", "unclosed"),
    ],
)
def test_invalid_declared_bindings_cannot_be_inferred(field, value):
    contribution, _store, pairs = fixture()
    assertion = contribution.accepted_assertions[0]
    rows = [dict(row) for row in assertion.value["evidence"]]
    rows[0][field] = value
    assertion = assertion.model_copy(
        update={"value": {**assertion.value, "evidence": rows}}
    )
    with pytest.raises((ValueError, ContributionMappingError)):
        mapped(
            contribution.model_copy(update={"accepted_assertions": [assertion]}), pairs
        )


def test_source_commitment_includes_source_index_and_reviewed_quotes():
    from apps.live_control_server.services.first_world_graph_publication import (
        _source_evidence_commitment,
    )
    from graph_memory.source_span import build_source_span_index_for_text

    text = "A small bridge crosses the river."
    import hashlib

    index = build_source_span_index_for_text(
        source_artifact_id="source",
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )
    review = [
        SimpleNamespace(
            assertion_id="bridge",
            kind="object",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source",
                    source_span_ref_id=index.spans[0].source_span_id,
                    anchor_quotes=[text],
                ),
            ],
        )
    ]
    args = dict(source_prose=text, span_index=index, source_artifact_id="source")
    original = _source_evidence_commitment(review, **args)
    from apps.live_control_server.services.first_world_graph_publication import (
        ExtractPromoteError,
    )

    with pytest.raises(ExtractPromoteError):
        _source_evidence_commitment(
            review, **{**args, "source_prose": text + " Changed."}
        )
    assert original != _source_evidence_commitment(
        review, **{**args, "span_index": replace(index, spans=())}
    )
    other = [
        SimpleNamespace(
            assertion_id="bridge",
            kind="object",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source",
                    source_span_ref_id=index.spans[0].source_span_id,
                    anchor_quotes=["river"],
                ),
            ],
        )
    ]
    assert original != _source_evidence_commitment(other, **args)


def test_old_plan_models_require_fresh_review():
    from apps.live_control_server.models.extract_promote import FirstWorldGraphPlan
    from apps.live_control_server.models.recap_world_genesis import (
        RecapWorldGenesisPlan,
    )

    for model, schema in (
        (FirstWorldGraphPlan, "dmb_first_world_graph_plan_v2"),
        (RecapWorldGenesisPlan, "dmb_recap_world_genesis_plan_v1"),
    ):
        with pytest.raises(ValueError, match="out of date"):
            model.model_validate({"schema": schema})


def test_old_plan_cannot_reach_source_or_initialization(monkeypatch):
    from apps.live_control_server.services import (
        first_world_graph_publication as service,
    )

    monkeypatch.setattr(
        service.live_config,
        "world_graph_root",
        lambda: pytest.fail("stale plan touched authority"),
    )
    with pytest.raises(service.ExtractPromoteError) as error:
        service.confirm_first_world(
            SimpleNamespace(
                plan=SimpleNamespace(schema_="dmb_first_world_graph_plan_v2")
            )
        )
    assert error.value.code == "stale_review_plan"


def test_materialized_spans_must_match_the_verified_candidate():
    from apps.live_control_server.services.first_world_graph_publication import (
        _assert_materialized_evidence_matches_review,
        ExtractPromoteError,
    )

    contribution, _store, _pairs = fixture()
    assertion = contribution.accepted_assertions[0]
    review = [
        SimpleNamespace(
            assertion_id="candidate",
            evidence=[
                SimpleNamespace(
                    source_artifact_id="source", source_span_ref_id="span:one"
                ),
            ],
        )
    ]
    materialized = SimpleNamespace(
        effect={"candidate_effect_map": {"candidate": [assertion.assertion_id]}},
        contribution=contribution,
    )
    with pytest.raises(ExtractPromoteError):
        _assert_materialized_evidence_matches_review(materialized, review)


def test_registry_profile_cannot_drop_declared_extraction_evidence():
    contribution, _store, pairs = fixture()
    contribution = contribution.model_copy(update={"source_kind": "standing_context"})
    with pytest.raises(ValueError, match="discard"):
        map_first_world_typed_contribution(
            contribution,
            artifacts=[SimpleNamespace(source_artifact_id="source")],
            pair_to_dm=pairs,
            party_registry=True,
        )
