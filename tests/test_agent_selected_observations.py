"""Selecting reviewed records preserves their complete pinned evidence."""

from dataclasses import replace
from types import SimpleNamespace
import os

import pytest
from pydantic import ValidationError

from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.services.hermes_graph_interaction_tools import (
    hermes_graph_interaction_tool_definitions,
)
from graph_memory.interaction.expansion_executor import ExpandGraphRetrievalRequest
from graph_memory.retrieval.models import (
    WorldGraphObjectRequest,
    WorldGraphRetrievalResult,
)
from tests.test_reviewed_source_observation_consumer import _observation, _anchor
from tests.test_recap_source_observation_followup import (
    observation_case as observation_case,
)
from tests.test_worldbuilding_source_observations import (
    test_native_confirm_retains_distinct_observations_sources_and_idempotency as native_witness,
)


def payload(**updates):
    return dict(
        retrievalSessionId="session",
        operation="object",
        targets=[dict(kind="node", id="npc:keeper")],
        **updates,
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"observationIds": ["x", "x"]},
        {"observationIds": [" "]},
        {"observationIds": [" x"]},
        {"observationIds": list(map(str, range(9)))},
        {"operation": "search", "observationIds": ["x"]},
    ],
)
def test_selector_rejects_invalid_or_nonobject_requests(updates):
    data = payload()
    data.update(updates)
    with pytest.raises(ValidationError):
        ExpandGraphRetrievalRequest.model_validate(data)


def test_model_visible_schema_explains_selection():
    tool = hermes_graph_interaction_tool_definitions()[0]["function"]
    assert "observationIds" in tool["parameters"]["properties"]
    assert "observationIds" in tool["description"]
    assert ExpandGraphRetrievalRequest.model_validate(
        payload(observationIds=["x"])
    ).observation_ids == ["x"]


@pytest.fixture
def bounded_case(monkeypatch):
    snapshot = SimpleNamespace(revision_id="rev:published")
    observations = tuple(
        replace(_observation(), assertion_id=f"obs:{i}", evidence_ref_ids=(f"ev:{i}",))
        for i in range(3)
    )
    anchors = [
        _anchor().model_copy(
            update={
                "anchor_id": f"a:{i}",
                "evidence_ref_id": f"ev:{i}",
                "supporting_assertion_ids": [f"obs:{i}"],
            }
        )
        for i in range(3)
    ]
    calls = []

    class Retrieval:
        def get_object_views(self, request, **kwargs):
            calls.append(request.revision_pin)
            return SimpleNamespace(
                bounded=SimpleNamespace(
                    snapshot=snapshot, found=True,
                    object=SimpleNamespace(object_id="npc:keeper"),
                ),
                complete=SimpleNamespace(
                    snapshot=snapshot, found=True,
                    object=SimpleNamespace(object_id="npc:keeper"),
                    reviewed_source_observations=observations,
                    anchors=(),
                    coverage=SimpleNamespace(gap_codes=(), missing_ids=()),
                ),
            )

    services = SimpleNamespace(
        object_read_wave=None,
        binding=direct.DirectAuthorityBinding(
            world_id="world:test",
            dungeonmind_first_revision_id="rev:published",
            dungeonmind_head_revision_id="rev:published",
            legacy_buddy_revision_id=None,
            genesis="reviewed_world_initialization",
        ),
        retrieval=Retrieval(),
    )
    monkeypatch.setattr(
        direct,
        "_object_result_view",
        lambda *_a, **_k: WorldGraphRetrievalResult(
            operation="object", outcome="enough"
        ),
    )
    monkeypatch.setattr(direct, "_source_anchor_views", lambda *_a, **_k: anchors)
    request = WorldGraphObjectRequest.model_validate(
        dict(
            schema="dmb_world_graph_object_request_v1",
            worldId="world:test",
            campaignId="one",
            revisionPin="rev:published",
            nodeId="npc:keeper",
            bounds={"maxSourceAnchors": 1},
        )
    )
    return services, request, calls


def test_selection_precedes_anchor_admission_and_reports_partial(bounded_case):
    services, request, calls = bounded_case
    unfiltered = direct._get_object_with_reviewed_sources_direct(services, request)
    assert [o.assertion_id for o in unfiltered[1]] == ["obs:0"]
    assert "reviewed_source_observation_anchor_bound" in unfiltered[2]
    selected = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=("obs:2",)
    )
    assert [o.assertion_id for o in selected[1]] == ["obs:2"]
    assert [a.evidence_ref_id for a in selected[0].source_anchors] == ["ev:2"]
    assert selected[2] == ["reviewed_source_observation_selection"]
    assert selected[0].outcome == "partial"
    assert calls == ["rev:published"] * 2


def test_unknown_or_foreign_subject_assertion_is_not_admitted(bounded_case):
    services, request, _ = bounded_case
    with pytest.raises(direct.DirectWorldGraphReadError) as error:
        direct._get_object_with_reviewed_sources_direct(
            services, request, observation_ids=("foreign:assertion",)
        )
    assert error.value.code == "selected_observation_unavailable"


@pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="unique disposable Core required",
)
@pytest.mark.parametrize("bind_first", [False, True])
def test_native_selected_records_preserve_exact_pins_and_openable_sources(
    observation_case, tmp_path, monkeypatch, bind_first
):
    # Reuse the actual registered-source -> reviewed native publication witness.
    # Intercept its readback to independently select each record from the real Core.
    original = direct.get_object_with_reviewed_sources_direct_v3
    checked = []

    def inspect(services, request):
        complete = original(services, request)
        assert len(complete.reviewed_source_observations) >= 2
        for row in complete.reviewed_source_observations:
            selected = original(services, request, observation_ids=(row.assertion_id,))
            assert selected.reviewed_source_observations == (row,)
            assert (
                "reviewed_source_observation_selection"
                in selected.observation_gap_codes
            )
            evidence = {
                a.evidence_ref_id
                for a in selected.result.source_anchors
                if row.assertion_id in a.supporting_assertion_ids
            }
            assert evidence == set(row.evidence_ref_ids)
            assert all(
                pin.graph_revision == request.revision_pin
                for pin in selected.source_pins
            )
            assert {pin.anchor_id for pin in selected.source_pins} == {
                a.anchor_id for a in selected.result.source_anchors if a.readable
            }
            checked.append(row.assertion_id)
        return complete

    monkeypatch.setattr(direct, "get_object_with_reviewed_sources_direct_v3", inspect)
    native_witness(observation_case, tmp_path, monkeypatch, bind_first)
    assert len(checked) >= 2


def test_missing_selected_evidence_rejects_without_partial_claim(bounded_case):
    services, request, _ = bounded_case
    original = services.retrieval.get_object_views

    def larger(*args, **kwargs):
        views = original(*args, **kwargs)
        native = views.complete
        native.reviewed_source_observations = (
            replace(
                native.reviewed_source_observations[0],
                evidence_ref_ids=("ev:0", "ev:missing"),
            ),
        )
        return views

    services.retrieval.get_object_views = larger
    with pytest.raises(direct.DirectWorldGraphReadError) as error:
        direct._get_object_with_reviewed_sources_direct(
            services, request, observation_ids=("obs:0",)
        )
    assert error.value.code == "projection_integrity_error"


def test_nongoverned_executor_rejects_selector_without_native_io(monkeypatch):
    from graph_memory.interaction.expansion_executor import _dispatch_expansion
    from apps.live_control_server.services.world_graph_retrieval import (
        WorldGraphRetrievalServiceError,
    )

    with pytest.raises(WorldGraphRetrievalServiceError) as error:
        _dispatch_expansion(
            request=ExpandGraphRetrievalRequest.model_validate(
                payload(observationIds=["obs:0"])
            ),
            session=None,
            ctx={},
            focus=None,
            node_ids=["npc:keeper"],
        )
    assert error.value.code == "selected_observations_unavailable"


def test_selected_record_over_bound_is_omitted_whole(bounded_case, monkeypatch):
    services, request, _ = bounded_case
    original = services.retrieval.get_object_views

    def larger(*args, **kwargs):
        views = original(*args, **kwargs)
        native = views.complete
        native.reviewed_source_observations = (
            replace(
                native.reviewed_source_observations[0],
                evidence_ref_ids=("ev:0", "ev:1"),
            ),
        )
        return views

    services.retrieval.get_object_views = larger
    anchors = [
        _anchor().model_copy(
            update={
                "anchor_id": f"a:{i}",
                "evidence_ref_id": f"ev:{i}",
                "supporting_assertion_ids": ["obs:0"],
            }
        )
        for i in range(2)
    ]
    monkeypatch.setattr(direct, "_source_anchor_views", lambda *_a, **_k: anchors)
    result, observations, gaps, *_ = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=("obs:0",)
    )
    assert not observations and not result.source_anchors
    assert gaps == ["reviewed_source_observation_anchor_bound"]
    assert result.outcome == "truncated"


def test_continuation_cannot_change_observation_selection():
    import json
    from uuid import uuid4
    from apps.live_control_server.services.graph_tool_presentation import (
        GraphToolPresentation,
    )
    from tests.test_graph_tool_transport import SCOPE, _raw

    args = dict(
        retrievalSessionId=SCOPE.retrieval_session_id,
        operation="object",
        targets=[dict(kind="node", id="npc:keeper")],
        observationIds=["obs:0"],
    )
    parent = GraphToolPresentation(SCOPE)
    first = json.loads(parent.present("expand_graph_retrieval", args, _raw(), uuid4()))
    token = first["detailPageToken"]
    assert parent.continuation(
        "expand_graph_retrieval", {**args, "resultPageToken": token}
    )
    with pytest.raises(ValueError):
        parent.continuation(
            "expand_graph_retrieval",
            {**args, "observationIds": ["obs:1"], "resultPageToken": token},
        )


def _canonical_saturation(monkeypatch, count=1):
    canonical = [_anchor().model_copy(update={
        'anchor_id': f'canonical:{i}', 'evidence_ref_id': f'canonical-ev:{i}',
        'supporting_assertion_ids': [f'canonical-claim:{i}'],
    }) for i in range(count)]
    monkeypatch.setattr(direct, '_object_result_view', lambda *_a, **_k:
        WorldGraphRetrievalResult(operation='object', outcome='enough', source_anchors=canonical))
    return canonical


def test_selected_evidence_displaces_saturated_canonical_anchors(bounded_case, monkeypatch):
    services, request, _ = bounded_case
    _canonical_saturation(monkeypatch)
    result, observations, gaps, *_ = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=('obs:2',))
    assert [row.assertion_id for row in observations] == ['obs:2']
    assert [row.evidence_ref_id for row in result.source_anchors] == ['ev:2']
    assert result.outcome == 'partial'
    assert 'source_anchors' in result.coverage.truncated_fields
    assert 'reviewed_source_observation_canonical_anchors_displaced' in gaps
    # The omitted canonical claim receives no supporting anchor in this packet.
    assert not any('canonical-claim:0' in a.supporting_assertion_ids for a in result.source_anchors)
    unselected = direct._get_object_with_reviewed_sources_direct(services, request)
    assert not unselected[1]
    assert unselected[0].source_anchors[0].anchor_id == 'canonical:0'


def test_selected_union_over_budget_admits_none(bounded_case, monkeypatch):
    services, request, _ = bounded_case
    _canonical_saturation(monkeypatch)
    result, observations, gaps, *_ = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=('obs:0', 'obs:1'))
    assert not observations
    assert [a.anchor_id for a in result.source_anchors] == ['canonical:0']
    assert result.outcome == 'truncated'
    assert 'reviewed_source_observation_anchor_bound' in gaps


def test_selected_records_share_evidence_budget(bounded_case, monkeypatch):
    services, request, _ = bounded_case
    _canonical_saturation(monkeypatch)
    original = services.retrieval.get_object_views
    def shared(*args, **kwargs):
        views = original(*args, **kwargs)
        native = views.complete
        native.reviewed_source_observations = tuple(
            replace(o, evidence_ref_ids=('ev:shared',)) for o in native.reviewed_source_observations)
        return views
    services.retrieval.get_object_views = shared
    monkeypatch.setattr(direct, '_source_anchor_views', lambda *_a, **_k: [
        _anchor().model_copy(update={'anchor_id': 'shared', 'evidence_ref_id': 'ev:shared',
                                    'supporting_assertion_ids': ['obs:0', 'obs:1', 'obs:2']})])
    result, observations, *_ = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=('obs:0', 'obs:1'))
    assert [o.assertion_id for o in observations] == ['obs:0', 'obs:1']
    assert len(result.source_anchors) == 1
    assert set(result.source_anchors[0].supporting_assertion_ids) == {'obs:0', 'obs:1', 'obs:2'}


def test_remaining_canonical_capacity_is_filled_deterministically(bounded_case, monkeypatch):
    services, request, _ = bounded_case
    _canonical_saturation(monkeypatch, 3)
    request = request.model_copy(update={'bounds': request.bounds.model_copy(update={'max_source_anchors': 3})})
    result, observations, *_ = direct._get_object_with_reviewed_sources_direct(
        services, request, observation_ids=('obs:2',))
    assert observations
    assert [a.anchor_id for a in result.source_anchors] == ['a:2', 'canonical:0', 'canonical:1']


@pytest.mark.parametrize("field,value", [
    ("revision_id", "rev:foreign"), ("head_revision_id", "rev:later"),
    ("projected_at", 2), ("found", False), ("object", None),
])
def test_combined_views_reject_disagreement_before_claims(bounded_case, field, value):
    services, request, calls = bounded_case
    original = services.retrieval.get_object_views

    def tampered(*args, **kwargs):
        views = original(*args, **kwargs)
        if field in ("found", "object"):
            setattr(views.complete, field, value)
        else:
            views.complete.snapshot = SimpleNamespace(**vars(views.complete.snapshot))
            setattr(views.complete.snapshot, field, value)
        return views

    services.retrieval.get_object_views = tampered
    with pytest.raises(direct.DirectWorldGraphReadError) as error:
        direct._get_object_with_reviewed_sources_direct(services, request)
    assert error.value.code == "projection_integrity_error"
    assert calls == ["rev:published"]
