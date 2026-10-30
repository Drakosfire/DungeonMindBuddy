"""Source-capable Plan owner pins cannot masquerade as classic Graph receipts."""
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_source_context import capability_bases, require_graph
from tests.test_native_corpus_source_access import lane, admit, capture  # noqa: F401


def receipt_payload(lane):
    admit(lane)
    source = capture(lane)
    value = dict(schema="dmb_plan_source_context_receipt_v1",
        receipt_serializer_version="canonical-json-utf8-v1",
        plan_context_policy={"policy": "auto_plan_world"},
        plan_basis=dict(world_id="managed", document_id="plan:test", object_revision=1,
            work_revision_id=str(uuid4()), revision_n=1, content_sha256="a" * 64),
        playable_target=None, source_authority=source.authority.model_dump(mode="json"),
        graph_capability=None,
        assembled_input=dict(assembler_version="plan_source_jev_initial_v1",
            provider_model_name="jev-1.14.0", provider_model_version="jev-1.14.0",
            tokenizer_name="utf8_json_bytes_plus_64_per_node_v1", tokenizer_version="v1",
            provider_envelope_input_tokens=120, output_token_reserve=200,
            context_window_limit=1000, included_history=[], assembled_input_sha256="b" * 64))
    return rehash(value)


def rehash(value):
    value.pop("context_receipt_sha256", None)
    # Schema defaults are serialized in the receipt's actual canonical form.
    value["plan_context_policy"].setdefault("schema", "dmb_plan_context_policy_v1")
    value["context_receipt_sha256"] = t.canonical_sha256(value)
    return value


def test_source_receipt_has_no_graph_authority_and_roundtrips_exactly(lane):
    payload = receipt_payload(lane)
    receipt = t.PlanSourceContextReceiptV1.model_validate(payload)
    assert t.PlanSourceContextReceiptV1.model_validate_json(receipt.model_dump_json()) == receipt
    bases = capability_bases(receipt)
    assert bases.graph is None and bases.source == receipt.source_authority
    assert bases.plan_basis == receipt.plan_basis
    assert not hasattr(receipt, "graph_authority")
    with pytest.raises(ValueError, match="no authorized Graph"):
        require_graph(receipt)


def test_source_revision_cannot_be_submitted_as_graph_authority(lane):
    payload = receipt_payload(lane)
    payload["graph_authority"] = {"graph_revision": payload["source_authority"]["revision_id"]}
    with pytest.raises(ValidationError):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))


def test_foreign_source_world_refuses_even_with_recomputed_digest(lane):
    payload = receipt_payload(lane)
    payload["source_authority"]["managed_world_id"] = "another"
    with pytest.raises(ValidationError, match="actual Plan World"):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))


def test_changed_source_pin_cannot_reuse_receipt_digest(lane):
    payload = receipt_payload(lane)
    changed = deepcopy(payload)
    changed["source_authority"]["revision_id"] = "rev:changed"
    with pytest.raises(ValidationError, match="digest differs"):
        t.PlanSourceContextReceiptV1.model_validate(changed)


def test_unavailable_source_is_explicit_and_does_not_invent_graph(lane):
    payload = receipt_payload(lane)
    payload["source_authority"] = dict(schema="dmb_native_corpus_unavailable_v1",
        managed_world_id="managed", failure_code="native_source_head_unavailable")
    receipt = t.PlanSourceContextReceiptV1.model_validate(rehash(payload))
    bases = capability_bases(receipt)
    assert bases.graph is None
    assert bases.source.failure_code == "native_source_head_unavailable"
    assert not hasattr(bases.source, "revision_id")


def test_actual_provider_allowance_cannot_be_overrun(lane):
    payload = receipt_payload(lane)
    payload["assembled_input"]["provider_envelope_input_tokens"] = 900
    with pytest.raises(ValidationError, match="provider context allowance"):
        t.PlanSourceContextReceiptV1.model_validate(rehash(payload))
