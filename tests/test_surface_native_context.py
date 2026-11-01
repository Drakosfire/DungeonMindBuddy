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
        runbook_content_sha256="a" * 64, beat_id="beat:one", scene_id="scene:one",
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


def provenance_for(work_context):
    supporting = []
    if isinstance(work_context, PlanWorkContextV1):
        basis = work_context.plan_basis
        primary = t.HistoricalReference(resolution="resolved", kind="plan",
            object_id=basis.document_id, object_revision=basis.object_revision,
            work_revision_id=basis.work_revision_id, revision_n=basis.revision_n,
            content_sha256=basis.content_sha256)
    elif isinstance(work_context, BuildWorkContextV1):
        basis = work_context.source_basis
        primary = t.HistoricalReference(resolution="resolved", kind="build",
            object_id=basis.document_id, revision=str(basis.registry_revision),
            content_sha256=basis.content_sha256)
        supporting = [t.HistoricalReference(resolution="resolved",
            kind="dmb_build_source_visibility_v1", object_id=basis.visibility, revision="1")]
    else:
        primary, supporting = t.encode_play_run_turn_context_references(work_context.play_basis)
    return t.TurnProvenance(world_id="world-one", surface_resolution="resolved",
        surface_id=work_context.surface_id, surface_instance_id=work_context.surface_id + ":test",
        primary_work=primary, supporting_work=supporting,
        selected_object=t.HistoricalReference(resolution="absent"))


def bound_context(surface):
    value = wire(surface)
    provenance = provenance_for(read(value).work_context)
    value["provenance_sha256"] = canonical_sha256(provenance)
    return read(seal(value)), provenance


def join(context, provenance, **kwargs):
    from application_state.agent_conversation.native_context import validate_work_context
    if "play_context_receipt" not in kwargs and isinstance(context.work_context, PlayWorkContextV1):
        kwargs["play_context_receipt"] = context.work_context.play_basis
    return validate_work_context(context, provenance, **kwargs)


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_shared_work_join_uses_real_owner_without_classic_graph_witnesses(surface):
    context, provenance = bound_context(surface)
    assert not any(r.kind == "world_graph_revision" for r in provenance.supporting_work)
    assert join(context, provenance) == context


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_resealed_provenance_cannot_change_frozen_work_revision(surface):
    context, provenance = bound_context(surface)
    primary = provenance.primary_work.model_dump(mode="json")
    if surface == "plan":
        primary["object_revision"] += 1
    else:
        primary["revision"] = str(int(primary["revision"]) + 1)
    provenance = provenance.model_copy(update={"primary_work": t.HistoricalReference.model_validate(primary)})
    value = context.model_dump(mode="json", by_alias=True)
    value["provenance_sha256"] = canonical_sha256(provenance)
    with pytest.raises(ValueError):
        join(read(seal(value)), provenance)


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_foreign_work_surface_refuses_even_after_resealing_root(surface):
    context, _ = bound_context(surface)
    provenance = provenance_for(work("plan" if surface != "plan" else "build"))
    value = context.model_dump(mode="json", by_alias=True)
    value["provenance_sha256"] = canonical_sha256(provenance)
    with pytest.raises(ValueError, match="actual work provenance"):
        join(read(seal(value)), provenance)


def test_build_visibility_remains_owned_by_build_work_validation():
    context, provenance = bound_context("build")
    visibility = provenance.supporting_work[0].model_copy(update={"object_id": "player_safe"})
    provenance = provenance.model_copy(update={"supporting_work": [visibility]})
    value = context.model_dump(mode="json", by_alias=True)
    value["provenance_sha256"] = canonical_sha256(provenance)
    with pytest.raises(ValueError, match="source visibility"):
        join(read(seal(value)), provenance)


@pytest.mark.parametrize("field", ["edition", "scene_note"])
def test_play_work_requires_exact_v2_run_snapshot_not_only_structural_witnesses(field):
    from hashlib import sha256
    context, provenance = bound_context("play")
    original = context.work_context.play_basis
    value = context.model_dump(mode="json", by_alias=True)
    basis = value["work_context"]["play_basis"]
    if field == "edition":
        basis.update(edition_revision=1, edition_revision_id=str(uuid4()), content_sha256="f" * 64)
    else:
        basis.update(scene_note="Retained note", scene_note_sha256=sha256(b"Retained note").hexdigest())
    changed = read(seal(value))
    # Existing structural references do not include these V2 snapshot fields.
    t.validate_play_context_receipt(changed.work_context.play_basis, "world-one", provenance)
    with pytest.raises(ValueError, match="exact retained Run snapshot"):
        join(changed, provenance, play_context_receipt=original)


def test_plan_work_cannot_smuggle_in_a_run_snapshot():
    context, provenance = bound_context("plan")
    with pytest.raises(ValueError, match="Non-Play"):
        join(context, provenance, play_context_receipt=work("play").play_basis)


def test_nested_work_mutation_cannot_bypass_root_revalidation():
    context, provenance = bound_context("plan")
    context.work_context.plan_basis.object_revision += 1
    with pytest.raises(ValueError, match="digest differs"):
        join(context, provenance)


def test_structural_provenance_view_is_not_accepted_as_a_work_join():
    from types import SimpleNamespace
    context, provenance = bound_context("plan")
    with pytest.raises(ValueError, match="concrete context and provenance"):
        join(context, SimpleNamespace(**provenance.model_dump()))


def test_reviewed_build_admission_is_not_a_fake_zero_token_provider_call():
    from application_state.agent_conversation.native_context import NativeReviewedActionInputV1
    value = wire("build")
    value["assembled_input"] = dict(assembler_version="reviewed_author_admission_v1",
        submitted_intent_sha256="f" * 64, assembled_input_sha256="e" * 64)
    context = read(seal(value))
    assert isinstance(context.assembled_input, NativeReviewedActionInputV1)
    assert not hasattr(context.assembled_input, "provider_model_name")
    assert not hasattr(context.assembled_input, "provider_envelope_input_tokens")


@pytest.mark.parametrize("surface", ["plan", "play"])
def test_reviewed_build_admission_cannot_select_another_surface(surface):
    value = wire(surface)
    value["assembled_input"] = dict(assembler_version="reviewed_author_admission_v1",
        submitted_intent_sha256="f" * 64, assembled_input_sha256="e" * 64)
    with pytest.raises(ValueError, match="actual Build work"):
        read(seal(value))


def test_model_free_admission_cannot_smuggle_provider_accounting():
    value = wire("build")
    value["assembled_input"] = dict(assembler_version="reviewed_author_admission_v1",
        submitted_intent_sha256="f" * 64, assembled_input_sha256="e" * 64,
        provider_model_name="not_dispatched", provider_envelope_input_tokens=0)
    with pytest.raises(ValueError, match="Extra inputs"):
        read(seal(value))
