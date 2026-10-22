"""Related-recap offers reuse exact metadata, never read authority or bodies."""

from copy import deepcopy
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from apps.live_control_server.services.agent_turn_service import _PolicyExecutionAdapter


def fixture():
    authority = NS(
        managed_world_id="managed:park",
        native_world_id="native:park",
        binding_version=1,
        graph_revision="rev:1",
        scope_mode="world",
        campaign_id=None,
        admissibility_version="gm-v1",
    )
    adapter = NS(_broker_receipt=lambda: NS(graph_authority=authority))

    def snapshot(projection):
        return NS(
            world_id=projection.world_id,
            campaign_id=None,
            scope_mode=projection.scope_mode,
            admissibility=projection.admissibility,
            focus=projection.focus,
            revision_id=projection.revision_pin,
        )

    observed = NS(index=None, evidence=None)

    def index(request):
        descriptor = NS(
            world_id=request.projection.world_id,
            graph_revision_id=request.projection.revision_pin,
            source_uri="repo://public-park-recap.md",
            source_artifact_id="artifact:park",
            source_revision_id="source:1",
            campaign_id="park-campaign",
            context_anchor_id="context:park",
            section_selector=NS(
                schema_version="dm_recap_context_section_selector_v2",
                kind="recap_section",
                policy="markdown-session-recap-v2",
            ),
        )
        observed.index = NS(
            status="complete",
            max_entries=512,
            eligible_count=1,
            entries=(descriptor,),
            snapshot=snapshot(request.projection),
        )
        return observed.index

    def evidence(projection, *, target, max_anchors):
        observed.evidence = NS(
            found=True,
            target=target,
            snapshot=snapshot(projection),
            coverage=NS(truncated_fields=(), gap_codes=(), missing_ids=()),
            anchors=(
                NS(
                    evidence_ref_id="ref:park",
                    source_artifact_id="artifact:park",
                    source_revision_id="source:1",
                ),
            ),
        )
        return observed.evidence

    native = NS(
        list_source_context_index=Mock(side_effect=index),
        get_evidence=Mock(side_effect=evidence),
    )

    def offer(*targets, refs=("ref:park",)):
        result = NS(
            attributes=[
                NS(assertion_id=key, evidence_ref_ids=list(refs)) for key in targets
            ],
            relationships=[],
        )
        return _PolicyExecutionAdapter._related_recap_offers(
            adapter, result, NS(retrieval=native)
        )

    return adapter, authority, native, observed, offer


def test_identical_and_overlapping_traversals_only_read_each_metadata_once():
    adapter, authority, native, observed, offer = fixture()
    first = offer("a", "b")
    second = offer("b", "c")
    assert [row["targetId"] for row in first] == ["a", "b"]
    assert [row["targetId"] for row in second] == ["b", "c"]
    assert offer("a", "b") == first
    assert native.list_source_context_index.call_count == 1
    assert native.get_evidence.call_count == 3
    # Traversal refs remain part of the evidence query identity.
    assert offer("a", refs=("ref:other",)) == []
    assert native.get_evidence.call_count == 4


@pytest.mark.parametrize(
    "field,value",
    [
        ("native_world_id", "native:other"),
        ("graph_revision", "rev:2"),
        ("binding_version", 2),
        ("managed_world_id", "managed:other"),
    ],
)
def test_changed_authority_never_reuses_prior_metadata(field, value):
    adapter, authority, native, observed, offer = fixture()
    assert offer("a")
    setattr(authority, field, value)
    assert offer("a")
    assert (
        native.list_source_context_index.call_count
        == native.get_evidence.call_count
        == 2
    )


def test_provider_and_consumer_mutations_cannot_change_frozen_metadata():
    adapter, authority, native, observed, offer = fixture()
    original = deepcopy(offer("a"))
    observed.index.entries[0].context_anchor_id = "foreign"
    observed.evidence.anchors[0].source_artifact_id = "foreign"
    changed = offer("a")
    changed[0]["evidenceRefIds"].append("foreign")
    assert offer("a") == original
    assert (
        native.list_source_context_index.call_count
        == native.get_evidence.call_count
        == 1
    )


@pytest.mark.parametrize(
    "fault", ["exception", "incomplete", "foreign", "duplicate", "selector"]
)
def test_failed_index_is_not_retried_or_used_to_open_evidence(fault):
    adapter, authority, native, observed, offer = fixture()
    original = native.list_source_context_index.side_effect

    def broken(request):
        if fault == "exception":
            raise RuntimeError("synthetic optional metadata failure")
        result = original(request)
        if fault == "incomplete":
            result.status = "overflow"
        elif fault == "foreign":
            result.snapshot.world_id = "foreign"
        elif fault == "duplicate":
            result.entries = (*result.entries, *result.entries)
            result.eligible_count = 2
        else:
            result.entries[0].section_selector.policy = "foreign"
        return result

    native.list_source_context_index.side_effect = broken
    assert offer("a") == offer("a", "b") == []
    assert native.list_source_context_index.call_count == 1
    assert native.get_evidence.call_count == 0


@pytest.mark.parametrize(
    "fault", ["exception", "missing", "foreign", "truncated", "target"]
)
def test_failed_exact_evidence_is_not_retried_or_used_as_an_offer(fault):
    adapter, authority, native, observed, offer = fixture()
    original = native.get_evidence.side_effect

    def broken(projection, **kwargs):
        if fault == "exception":
            raise RuntimeError("synthetic optional metadata failure")
        result = original(projection, **kwargs)
        if fault == "missing":
            result.found = False
        elif fault == "foreign":
            result.snapshot.revision_id = "foreign"
        elif fault == "truncated":
            result.coverage.truncated_fields = ("anchors",)
        else:
            result.target = NS(kind="assertion", target_id="foreign")
        return result

    native.get_evidence.side_effect = broken
    assert offer("a") == offer("a") == []
    assert (
        native.list_source_context_index.call_count
        == native.get_evidence.call_count
        == 1
    )


def test_cache_is_not_shared_between_parent_turns():
    first = fixture()
    second = fixture()
    assert first[-1]("a") == second[-1]("a")
    assert (
        first[2].list_source_context_index.call_count
        == second[2].list_source_context_index.call_count
        == 1
    )
