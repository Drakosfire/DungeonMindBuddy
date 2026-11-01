"""Shared context substitution guards; these do not establish live admission."""
from copy import deepcopy
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_context import (
    BuildWorkContextV1, PlanWorkContextV1, PlayWorkContextV1,
    NativeProviderInputV1, SurfaceNativeContextReceiptV1,
)
from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
from application_state.agent_conversation.native_plan_assertions import NativePlanQueryV2
from application_state.agent_conversation.native_plan_statements import NativePlanQueryAuthorityV1
from application_state.agent_conversation.native_statement_input import NativeAuthorityRefV1
from application_state.agent_conversation.rules_authority_types import canonical_sha256


def work(surface):
    if surface == "build":
        return BuildWorkContextV1(source_basis=t.BuildSourceContextBasisV1(
            world_id="world-one", document_id="page-one", registry_revision=3,
            content_sha256="a" * 64, visibility="internal"))
    if surface == "plan":
        return PlanWorkContextV1(plan_basis=t.PlanAskContextBasis(
            world_id="world-one", document_id="plan-one", object_revision=4,
            work_revision_id=uuid4(), revision_n=2, content_sha256="a" * 64),
            plan_context_policy=t.PlanContextPolicyV2(policy="auto_plan_world",
                graph_source="reviewed_native_graph"), playable_target=None)
    return PlayWorkContextV1(play_basis=t.PlayRunTurnContextReceiptV2(
        world_id="world-one", run_id="run-one", run_revision=3,
        runbook_object_id="plan-one", runbook_object_revision=4,
        runbook_work_revision_id=uuid4(), runbook_revision_n=2,
        runbook_content_sha256="a" * 64, beat_id="beat:one", scene_id=None,
        edition_revision=0, edition_revision_id=None, content_sha256="a" * 64))


def seal(wire):
    wire = deepcopy(wire)
    wire.pop("context_receipt_sha256", None)
    wire["context_receipt_sha256"] = canonical_sha256(wire)
    return wire


def wire(surface="plan", *, unavailable=False):
    pins = dict(managed_world_id="world-one", native_world_id="native-one",
        binding_version=1, revision_id="rev:one", acquisition_epoch=7,
        domain_ref=NativeAuthorityRefV1(authority_id="domain", revision="1", descriptor_sha256="a" * 64),
        profile_ref=NativeAuthorityRefV1(authority_id="profile", revision="1", descriptor_sha256="b" * 64))
    source = NativeCorpusAuthorityV1(**pins)
    query = NativePlanQueryV2(authority=NativePlanQueryAuthorityV1(
        **pins, scope_mode="campaign", campaign_id="campaign-one"),
        question="What did the check reveal?", search_result_sha256="c" * 64,
        discovered_entity_ids=(), matches=(), assertion_matches=(), status="complete", gap_codes=())
    if unavailable:
        source = t.NativeCorpusUnavailableV1(managed_world_id="world-one",
            failure_code="native_source_head_unavailable")
        query = t.NativePlanQueryUnavailableV1(managed_world_id="world-one",
            reason="native_graph_head_unavailable")
    accounting = NativeProviderInputV1(provider_model_name="jev-1.14.0",
        provider_model_version="jev-1.14.0", tokenizer_name="test-counter",
        tokenizer_version="1", provider_envelope_input_tokens=120,
        output_token_reserve=200, context_window_limit=1000,
        included_history=(), assembled_input_sha256="d" * 64)
    provisional = SurfaceNativeContextReceiptV1.model_construct(
        context_receipt_sha256="0" * 64, provenance_sha256="e" * 64,
        work_context=work(surface), source_authority=source,
        native_query=query, assembled_input=accounting)
    return seal(provisional.model_dump(mode="json", by_alias=True))


def read(value):
    return SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
@pytest.mark.parametrize("unavailable", [False, True])
def test_one_context_codec_preserves_exact_real_work_family(surface, unavailable):
    original = wire(surface, unavailable=unavailable)
    context = read(original)
    assert context.model_dump(mode="json", by_alias=True) == original
    assert context.work_context.surface_id == surface
    assert not hasattr(context, "graph_authority")
    assert not hasattr(context, "plan_basis")
    # Whole-World source inspection does not narrow to the fact query campaign.
    if not unavailable:
        assert context.source_authority.scope == "gm_world_cross_campaign_source_inspection"
        assert context.native_query.authority.campaign_id == "campaign-one"


@pytest.mark.parametrize("field,value", [
    ("managed_world_id", "foreign-world"), ("native_world_id", "foreign-native"),
    ("binding_version", 2), ("revision_id", "rev:other"), ("acquisition_epoch", 8),
    ("domain_ref", dict(authority_id="domain", revision="2", descriptor_sha256="a" * 64)),
    ("profile_ref", dict(authority_id="profile", revision="2", descriptor_sha256="b" * 64)),
])
def test_recomputed_root_cannot_join_different_source_and_query_authorities(field, value):
    value_wire = wire()
    value_wire["native_query"]["authority"][field] = value
    with pytest.raises(ValidationError, match="Native capabilities differ|Native source and query commitments differ"):
        read(seal(value_wire))


@pytest.mark.parametrize("surface,basis", [("build", "source_basis"), ("plan", "plan_basis"), ("play", "play_basis")])
def test_recomputed_root_cannot_move_work_to_another_world(surface, basis):
    value = wire(surface)
    value["work_context"][basis]["world_id"] = "foreign-world"
    with pytest.raises(ValidationError, match="actual work World"):
        read(seal(value))


def test_surface_label_cannot_relabel_a_plan_basis_as_build_work():
    value = wire()
    value["work_context"]["surface_id"] = "build"
    with pytest.raises(ValidationError):
        read(seal(value))


@pytest.mark.parametrize("field", ["provenance_sha256", "assembled_input_sha256", "work_revision"])
def test_context_commitment_covers_work_provenance_and_actual_input(field):
    value = wire()
    if field == "assembled_input_sha256":
        value["assembled_input"][field] = "f" * 64
    elif field == "work_revision":
        value["work_context"]["plan_basis"]["object_revision"] += 1
    else:
        value[field] = "f" * 64
    with pytest.raises(ValidationError, match="digest differs"):
        read(value)


def test_context_cannot_manufacture_a_classic_graph_packet_or_authority():
    value = wire()
    value["graph_authority"] = {"graph_revision": "rev:one"}
    value["graph_packet"] = {}
    with pytest.raises(ValidationError, match="Extra inputs"):
        read(seal(value))


def test_actual_input_accounting_refuses_provider_context_overflow():
    value = wire()
    value["assembled_input"]["provider_envelope_input_tokens"] = 801
    with pytest.raises(ValidationError, match="context allowance"):
        read(seal(value))
