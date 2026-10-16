"""Citation capacity covers all actually included reads, never authority by count."""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from tests.application_state.test_agent_conversation_service import _source_admission_v3_fixture
from tests.application_state.test_agent_source_admission_v3_postgres import (
    _authorization, _provider, _read_event,
)


def _citation(count):
    return t.PlanWorldGraphCitationV2(
        claim_id="claim", target_kind="assertion", target_id="assertion-many",
        graph_revision="revision", evidence_ref_ids=["evidence"],
        source_read_ids=[f"read-{i:05}" for i in range(count)], source_opened=count > 0,
    )


@pytest.mark.parametrize("count", [8, 24, 64, 65])
def test_citation_keeps_all_included_read_ids_across_batches(count):
    citation = _citation(count)
    assert len(citation.source_read_ids) == count
    assert t.PlanWorldGraphCitationV2.model_validate_json(citation.model_dump_json()) == citation


def _included_reads(count=24):
    receipt, execution, origin, extension = _source_admission_v3_fixture()
    execution = execution.model_copy(update={"events": [origin, extension]})
    turn = SimpleNamespace(graph_context_execution=execution, world_id=extension.world_id)
    events = list(execution.events)
    reads = []
    for _ in range(count):
        authorization = _authorization(turn, extension.pins[0])
        events.append(authorization)
        turn.graph_context_execution = execution.model_copy(update={"events": list(events)})
        read, _ = _read_event(turn, authorization)
        events.append(read)
        reads.append(read)
        turn.graph_context_execution = execution.model_copy(update={"events": list(events)})
    attempt = _provider(turn, receipt, origin, reads)
    events.append(attempt)
    for outcome in ("sdk_entered", "response_received"):
        events.append(t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(events),
            kind="provider_outcome", provider_attempt_id=attempt.provider_attempt_id, outcome=outcome))
    execution = t.PlanWorldGraphExecutionV3.model_validate(execution.model_dump(mode="json", by_alias=True) | {
        "events": [event.model_dump(mode="json", by_alias=True) for event in events]})
    citation = t.PlanWorldGraphCitationV2(
        claim_id="claim", target_kind="assertion", target_id="assertion-many",
        graph_revision=extension.graph_revision, evidence_ref_ids=[extension.pins[0].evidence_ref_id],
        source_read_ids=sorted(read.receipts[0].source_read_id for read in reads), source_opened=True)
    citations = t.PlanWorldGraphCitationMapV2(context_receipt_sha256=receipt.context_receipt_sha256, entries=[citation])
    return execution, attempt, citations


@pytest.mark.parametrize("count", [24, 65])
def test_repeated_reads_for_one_ref_remain_bound_to_actual_producing_envelope(count):
    execution, attempt, citations = _included_reads(count)
    assert len(citations.entries[0].evidence_ref_ids) == 1
    assert len(citations.entries[0].source_read_ids) == count
    t.validate_graph_execution_source_citations(citations, execution, attempt.provider_attempt_id)


@pytest.mark.parametrize("failure", ["unknown", "omitted", "empty", "hash", "revision", "evidence"])
def test_larger_citation_does_not_admit_unproven_reads(failure):
    execution, attempt, citations = _included_reads()
    events = list(execution.events)
    read_index = next(i for i, event in enumerate(events) if event.kind == "validated_source_read_v2")
    if failure == "unknown":
        entry = citations.entries[0].model_copy(update={"source_read_ids": ["unknown-read"]})
        citations = citations.model_copy(update={"entries": [entry]})
    elif failure == "omitted":
        attempt = attempt.model_copy(update={"included_source_read_event_ids": attempt.included_source_read_event_ids[1:]})
        events = [attempt if event.event_id == attempt.event_id else event for event in events]
    else:
        field, value = {
            "empty": ("returned_chars", 0), "hash": ("content_sha256", None),
            "revision": ("source_revision_id", None), "evidence": ("evidence_ref_id", "foreign-evidence"),
        }[failure]
        bad = events[read_index].receipts[0].model_copy(update={field: value})
        events[read_index] = events[read_index].model_copy(update={"receipts": [bad]})
    execution = execution.model_copy(update={"events": events})
    with pytest.raises(ValueError, match="citation source"):
        t.validate_graph_execution_source_citations(citations, execution, attempt.provider_attempt_id)


@pytest.mark.parametrize("failure", ["duplicate", "unsorted"])
def test_citation_still_requires_unique_sorted_reads(failure):
    ids = ["read-a", "read-a"] if failure == "duplicate" else ["read-b", "read-a"]
    with pytest.raises(ValidationError, match="sorted and unique"):
        t.PlanWorldGraphCitationV2.model_validate(_citation(1).model_dump() | {"source_read_ids": ids})


def test_citation_outer_capacity_tracks_admitted_receipts_and_rejects_overflow():
    limit = t.MAX_CITATION_SOURCE_READ_IDS
    assert limit == t.MAX_INCLUDED_SOURCE_READ_EVENTS_V3 * t.MAX_RECEIPTS_PER_SOURCE_READ_EVENT
    assert len(_citation(limit).source_read_ids) == limit
    with pytest.raises(ValidationError, match="at most"):
        _citation(limit + 1)
