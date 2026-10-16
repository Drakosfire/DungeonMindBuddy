"""Parent-owned Build evidence selection is exact, per target and per envelope."""
import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest

from apps.live_control_server.services import agent_turn_service as svc


def evidence_case(closures=(("assertion", "a:one", ("e:one", "e:two")),)):
    attempt = uuid4()
    auth = SimpleNamespace(kind="provider_attempt_authorized_v3", provider_attempt_id=attempt,
                           envelope_sha256="envelope")
    receipt = SimpleNamespace(context_receipt_sha256="receipt",
                              graph_authority=SimpleNamespace(graph_revision="revision"))
    turn = SimpleNamespace(graph_context_receipt=receipt,
                           graph_context_execution=SimpleNamespace(events=[auth]))
    support = svc._BuildClaimEvidence(attempt, "envelope", "receipt", "revision", closures)
    segment = {"kind": "graph_claim", "claim_id": "answer:one", "text": "Qualified fact.",
               "target_kind": "assertion", "target_id": "a:one"}
    return attempt, turn, support, segment


def test_model_selects_target_and_host_preserves_its_full_refs_without_event_union():
    attempt, turn, support, segment = evidence_case((
        ("assertion", "a:one", ("e:one", "e:two")),
        ("assertion", "a:other", ("e:unrelated",)),
    ))
    normalized = svc._normalize_build_graph_claim(segment, support, turn, attempt)
    assert normalized == {**segment, "graph_revision": "revision",
                          "evidence_ref_ids": ["e:one", "e:two"]}
    assert "graph_revision" not in segment and "evidence_ref_ids" not in segment


@pytest.mark.parametrize("field,value", [
    ("provider_attempt_id", uuid4()), ("envelope_sha256", "old-envelope"),
    ("context_receipt_sha256", "another-world-turn"), ("graph_revision", "old-revision"),
])
def test_evidence_from_another_attempt_envelope_turn_or_revision_cannot_normalize(field, value):
    attempt, turn, support, segment = evidence_case()
    with pytest.raises(ValueError, match="producing envelope"):
        svc._normalize_build_graph_claim(segment, replace(support, **{field: value}), turn, attempt)


@pytest.mark.parametrize("closures", [(),
    (("assertion", "a:other", ("e:one",)),),
    (("relationship", "a:one", ("e:one",)),),
    (("assertion", "a:one", ("e:one",)), ("assertion", "a:one", ("e:two",))),
])
def test_unknown_discovery_only_foreign_kind_or_conflicting_closure_rejects(closures):
    attempt, turn, support, segment = evidence_case(closures)
    with pytest.raises(ValueError, match="absent or ambiguous"):
        svc._normalize_build_graph_claim(segment, support, turn, attempt)


@pytest.mark.parametrize("field,value", [
    ("evidence_ref_ids", ["e:forged"]), ("graph_revision", "revision"),
    ("source_opened", True), ("source_read_ids", ["read:invented"]),
])
def test_model_cannot_supply_host_owned_metadata(field, value):
    attempt, turn, support, segment = evidence_case()
    with pytest.raises(ValueError, match="without evidence metadata"):
        svc._normalize_build_graph_claim({**segment, field: value}, support, turn, attempt)


def initial_case(rows):
    projection = {"claim_ledger": rows}
    bootstrap = SimpleNamespace(
        candidate_assertion_ids=("a:one", "a:two"), candidate_relationship_ids=(),
        candidate_evidence_ref_ids=("e:one", "e:two"),
        evidence_by_anchor_id={"anchor:one": "e:one", "anchor:two": "e:two"},
        assembler_version="agent_harness_final_request_v2",
        world_scope=SimpleNamespace(revision_id="revision"),
    )
    packet = {"candidates": [], "claimLedger": rows, "intentHint": None, "availableExpansions": []}
    view = {"payloadJson": json.dumps({"input": [{"content":
        "Turn capability policy (runtime-enforced; also required on tool calls):\n" +
        json.dumps({"initialClaimPacket": packet})}]})}
    return view, bootstrap, projection


def test_initial_packet_target_refs_are_exact_and_do_not_copy_neighbor_evidence():
    rows = [{"claim_id": target, "claim_kind": "attribute", "revision_id": "revision",
             "evidence_ref_ids": [ref], "support": {"source_anchor_ids": [anchor]}}
            for target, ref, anchor in [("a:one", "e:one", "anchor:one"),
                                        ("a:two", "e:two", "anchor:two")]]
    assert svc._build_initial_claim_evidence(*initial_case(rows)) == [
        ("assertion", "a:one", ("e:one",)), ("assertion", "a:two", ("e:two",))]
    rows[0]["revision_id"] = "old-revision"
    assert svc._build_initial_claim_evidence(*initial_case(rows)) == [
        ("assertion", "a:two", ("e:two",))]


def test_initial_declared_reference_without_admitted_anchor_cannot_get_a_closure():
    rows = [{"claim_id": "a:one", "claim_kind": "relationship", "revision_id": "revision",
             "evidence_ref_ids": ["e:one", "e:hidden"],
             "support": {"source_anchor_ids": ["anchor:one"]}}]
    assert svc._build_initial_claim_evidence(*initial_case(rows)) == []
