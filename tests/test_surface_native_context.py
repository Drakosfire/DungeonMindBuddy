"""Shared context substitution guards; these do not establish live admission."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
from hashlib import sha256
import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation.types import (
    ProviderAttemptAuthorizedEventV1, ProviderAttemptAuthorizedEventV5,
    ProviderOutcomeEventV1, CompletionBindingEventV1,
)
from application_state.agent_conversation.provider_execution import (
    _ProviderState, _advance, validate,
)
from application_state.agent_conversation.native_context import (
    BuildWorkContextV1, PlanWorkContextV1, PlayWorkContextV1,
    NativeProviderInputV1, SurfaceNativeContextReceiptV1,
)
from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
from application_state.agent_conversation.native_plan_assertions import NativePlanQueryV2
from application_state.agent_conversation.native_plan_statements import NativePlanQueryAuthorityV1
from application_state.agent_conversation.native_statement_input import NativeAuthorityRefV1
from application_state.agent_conversation.rules_authority_types import canonical_sha256


WORK_MARKDOWN = "# Work\n\nAn unplayed possibility.\n"


def work(surface):
    if surface == "build":
        return BuildWorkContextV1(source_basis=t.BuildSourceContextBasisV1(
            world_id="world-one", document_id="page-one", registry_revision=3,
            content_sha256="a" * 64, visibility="internal"))
    if surface == "plan":
        return PlanWorkContextV1(plan_basis=t.PlanAskContextBasis(
            world_id="world-one", document_id="plan-one", object_revision=4,
            work_revision_id=uuid4(), revision_n=2, content_sha256=sha256(WORK_MARKDOWN.encode()).hexdigest()),
            plan_context_policy=t.PlanContextPolicyV2(policy="auto_plan_world",
                graph_source="reviewed_native_graph"), playable_target=None)
    basis = t.PlayRunTurnContextReceiptV2(
        world_id="world-one", run_id="run-one", run_revision=3,
        runbook_object_id="plan-one", runbook_object_revision=4,
        runbook_work_revision_id=uuid4(), runbook_revision_n=2,
        runbook_content_sha256="a" * 64, beat_id="beat:one", scene_id="scene:one",
        edition_revision=0, edition_revision_id=None, content_sha256="a" * 64)
    from application_state.agent_conversation.play_graph_authority import play_source_frame
    frame = play_source_frame((t.PlaySourcePayloadV1(source_kind='current_moment',
        locator=t.play_source_locator(basis), text='Exact saved Play moment.'),))
    return PlayWorkContextV1(play_basis=basis, play_sources=frame.manifest,
        play_source_frame_sha256=canonical_sha256(frame))


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
    return t.TurnProvenance(world_id=(work_context.source_basis.world_id if isinstance(work_context,BuildWorkContextV1)
        else work_context.plan_basis.world_id if isinstance(work_context,PlanWorkContextV1) else work_context.play_basis.world_id), surface_resolution="resolved",
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


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_work_join_rejects_mutated_nested_authority_fields(surface):
    context, provenance = bound_context(surface)
    object.__setattr__(context.source_authority, "binding_version", 0)
    with pytest.raises(ValidationError) as error:
        join(context, provenance)
    assert any(item["loc"][-1] == "binding_version" for item in error.value.errors())


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_work_join_rejects_mutated_nested_provenance_fields(surface):
    context, provenance = bound_context(surface)
    object.__setattr__(provenance.primary_work, "resolution", "unverified")
    with pytest.raises(ValidationError) as error:
        join(context, provenance)
    assert any(item["loc"][-1] == "resolution" for item in error.value.errors())


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


def provider_ledger():
    """Lifecycle fixture only; this does not admit native reads or completions."""
    from types import SimpleNamespace
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    read = NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256="a" * 64, assertion_ids=("assertion-one",))
    provider = t.PlanNativeWriterAuthorizedV2(event_id=uuid4(), sequence=1,
        provider_attempt_id=uuid4(), envelope_sha256="b" * 64,
        serializer_version="openai-sdk-json-v1", provider="openai-api", model="synthetic", api_mode="responses",
        tool_schema_sha256="c" * 64, input_accounting_kind="exact_token_count", input_estimator="synthetic",
        input_tokens=12, output_token_reserve=10, included_assertion_ids=[], included_relationship_ids=[],
        included_evidence_ref_ids=[], included_graph_event_ids=[], included_source_read_event_ids=[],
        frame_sha256="d" * 64, included_source_reuse_event_ids=[],
        native_statement_read_event_ids=[], native_assertion_read_event_ids=[read.event_id])
    def outcome(sequence, value):
        return t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(), sequence=sequence,
            provider_attempt_id=provider.provider_attempt_id, outcome=value)
    completion = t.CompletionBindingEventV1(kind="completion_binding", event_id=uuid4(), sequence=4,
        provider_attempt_id=provider.provider_attempt_id, completion_sha256="e" * 64, claim_graph_event_ids={})
    # No classic Graph scope, operation menu, result budget or fabricated packet.
    policy = SimpleNamespace(provider_input_accounting=t.GraphExecutionAccountingV1(
        kind="exact_token_count", estimator="synthetic"), max_provider_attempts=1,
        max_total_provider_input_tokens=12, max_total_provider_output_tokens=10)
    return SimpleNamespace(policy=policy, events=[read, provider,
        outcome(2, "sdk_entered"), outcome(3, "response_received"), completion])


def test_provider_lifecycle_uses_native_event_positions_without_classic_graph_policy():
    ledger = provider_ledger()
    before = [event.model_dump_json() for event in ledger.events]
    t.validate_provider_execution(ledger)
    assert [event.model_dump_json() for event in ledger.events] == before


@pytest.mark.parametrize("change", ["sequence", "duplicate_id", "unknown_outcome", "unentered_sdk",
                                     "input_budget", "output_budget", "accounting"])
def test_provider_lifecycle_preserves_fail_closed_checks_on_native_records(change):
    ledger = provider_ledger()
    if change == "sequence":
        ledger.events[0] = ledger.events[0].model_copy(update={"sequence": 1})
    if change == "duplicate_id":
        ledger.events[0] = ledger.events[0].model_copy(update={"event_id": ledger.events[1].event_id})
    if change == "unknown_outcome":
        ledger.events[3] = ledger.events[3].model_copy(update={"outcome": "outcome_unknown"})
    if change == "unentered_sdk":
        ledger.events[2] = ledger.events[2].model_copy(update={"outcome": "response_received"})
    if change == "input_budget":
        ledger.policy.max_total_provider_input_tokens = 11
    if change == "output_budget":
        ledger.policy.max_total_provider_output_tokens = 9
    if change == "accounting":
        ledger.events[1] = ledger.events[1].model_copy(update={"input_estimator": "unapproved"})
    with pytest.raises(ValueError):
        t.validate_provider_execution(ledger)


def controller_writer_ledger():
    """Shared role ordering only; native read and output proof have other owners."""
    ledger = provider_ledger()
    writer = ledger.events[1].model_copy(update={"sequence": 3, "native_assertion_read_event_ids": []})
    controller_wire = writer.model_dump(exclude={"frame_sha256", "native_statement_read_event_ids",
        "native_assertion_read_event_ids", "included_source_reuse_event_ids"})
    controller_wire.update(kind="plan_jev_provider_authorized_v1", event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), provider="typesafe", model="jev-1.14.0", api_mode="decision",
        decision_request_id=uuid4(), parent_request_sha256="a" * 64)
    controller = t.PlanJevProviderAuthorizedV1.model_validate(controller_wire)
    def outcome(event, sequence, value):
        return t.ProviderOutcomeEventV1(kind="provider_outcome", event_id=uuid4(), sequence=sequence,
            provider_attempt_id=event.provider_attempt_id, outcome=value)
    ledger.policy.provider_roles = t.GraphControllerWriterRolesV1(
        controller=t.GraphProviderRoleTargetV1(provider="typesafe", model="jev-1.14.0", api_mode="decision"),
        writer=t.GraphProviderRoleTargetV1(provider=writer.provider, model=writer.model, api_mode=writer.api_mode))
    ledger.policy.max_provider_attempts = 2
    ledger.policy.max_total_provider_input_tokens = 24
    ledger.policy.max_total_provider_output_tokens = 20
    ledger.events = [controller, outcome(controller, 1, "sdk_entered"), outcome(controller, 2, "response_received"),
        writer, outcome(writer, 4, "sdk_entered"), outcome(writer, 5, "response_received"),
        ledger.events[-1].model_copy(update={"sequence": 6})]
    return ledger


def test_shared_role_ordering_uses_existing_native_records_without_classic_policy():
    ledger = controller_writer_ledger()
    t.validate_provider_execution(ledger)
    t.validate_controller_writer_execution(ledger)


@pytest.mark.parametrize("change", ["writer_first", "controller_after_writer", "second_writer",
                                     "completion_controller", "foreign_provider", "review_flag"])
def test_shared_role_ordering_keeps_one_writer_and_owner_review_boundaries(change):
    ledger = controller_writer_ledger()
    reviewed = None
    if change == "writer_first":
        ledger.events = ledger.events[3:]
    if change == "controller_after_writer":
        ledger.events.insert(-1, ledger.events[0].model_copy(update={"provider_attempt_id": uuid4()}))
    if change == "second_writer":
        ledger.events.insert(-1, ledger.events[3].model_copy(update={"provider_attempt_id": uuid4()}))
    if change == "completion_controller":
        ledger.events[-1] = ledger.events[-1].model_copy(update={
            "provider_attempt_id": ledger.events[0].provider_attempt_id})
    if change == "foreign_provider":
        ledger.events[0] = ledger.events[0].model_copy(update={"model": "unoffered-model"})
    if change == "review_flag":
        reviewed = True
    with pytest.raises(ValueError):
        t.validate_controller_writer_execution(ledger, reviewed_action=reviewed)


@pytest.mark.parametrize("surface",["build","plan","play"])
def test_semantic_initial_codec_belongs_only_to_actual_build_work(surface):
    value=wire(surface)
    value['assembled_input']['assembler_version']='native_build_semantic_initial_v2'
    value=seal(value)
    if surface=='build':
        from application_state.agent_conversation.native_context import NativeBuildProviderInputV2
        parsed=read(value)
        assert isinstance(parsed.assembled_input,NativeBuildProviderInputV2)
        assert read(parsed.model_dump(mode='json',by_alias=True))==parsed
    else:
        with pytest.raises(ValidationError,match='actual Build work'):
            read(value)


# Original predicate at f6e174e40; only test-relative imports are qualified.
# TEST ONLY, not a runtime fallback.
def _original_validate(execution) -> None:
    """Validate the actual typed record; never project native events to V1."""
    policy, events = execution.policy, execution.events
    if [event.sequence for event in events] != list(range(len(events))):
        raise ValueError("Graph execution events must have contiguous sequence numbers")
    if len({event.event_id for event in events}) != len(events):
        raise ValueError("Graph execution event IDs must be unique")
    attempts: dict[UUID, ProviderAttemptAuthorizedEventV1] = {}
    outcomes: dict[UUID, list[str]] = {}
    completion_bindings = 0
    for event in events:
        if isinstance(event, ProviderAttemptAuthorizedEventV1):
            if event.provider_attempt_id in attempts:
                raise ValueError("provider attempt ID was authorized more than once")
            if attempts:
                latest_attempt_id = next(reversed(attempts))
                prior_outcomes = outcomes[latest_attempt_id]
                if not prior_outcomes or prior_outcomes[-1] not in {"response_received", "known_not_sent"}:
                    raise ValueError("a new provider attempt requires a resolved prior attempt")
            if isinstance(event, ProviderAttemptAuthorizedEventV5):
                from application_state.agent_conversation.build_decision_context import validate_event
                validate_event(event, execution)
            from application_state.agent_conversation.build_decision_context import uses_role_accounting
            if uses_role_accounting(policy):
                from application_state.agent_conversation.build_decision_context import validate_accounting
                validate_accounting(event, execution, provider_index=len(attempts))
            elif (event.input_accounting_kind != policy.provider_input_accounting.kind
                    or event.input_estimator != policy.provider_input_accounting.estimator):
                raise ValueError("provider attempt accounting differs from accepted policy")
            attempts[event.provider_attempt_id] = event
            outcomes[event.provider_attempt_id] = []
        elif isinstance(event, ProviderOutcomeEventV1):
            if event.provider_attempt_id not in attempts:
                raise ValueError("provider outcome requires a prior authorization")
            prior = outcomes[event.provider_attempt_id]
            if event.outcome == "sdk_entered" and prior:
                raise ValueError("SDK entry must be the first provider outcome")
            if event.outcome == "known_not_sent" and prior:
                raise ValueError("known-not-sent must be recorded before SDK entry")
            if event.outcome not in {"sdk_entered", "known_not_sent", "outcome_unknown"} and not prior:
                raise ValueError("provider outcome requires observed SDK entry")
            if prior and prior[-1] in {"response_received", "known_not_sent", "outcome_unknown"}:
                raise ValueError("provider attempt already has a terminal outcome")
            prior.append(event.outcome)
        elif isinstance(event, CompletionBindingEventV1):
            completion_bindings += 1
            if completion_bindings > 1 or event.sequence != len(events) - 1:
                raise ValueError("completion binding must be unique and the final execution event")
            if event.provider_attempt_id not in attempts or outcomes[event.provider_attempt_id][-1:] != ["response_received"]:
                raise ValueError("completion binding requires a response-received attempt")
    if policy.max_provider_attempts is not None and len(attempts) > policy.max_provider_attempts:
        raise ValueError("provider attempt policy limit exceeded")
    input_total = sum(event.input_tokens for event in attempts.values())
    output_total = sum(event.output_token_reserve for event in attempts.values())
    if (
        policy.max_total_provider_input_tokens is not None
        and input_total > policy.max_total_provider_input_tokens
    ) or (
        policy.max_total_provider_output_tokens is not None
        and output_total > policy.max_total_provider_output_tokens
    ):
        raise ValueError("provider token budget exceeded")



def judgment(check, execution):
    try:
        check(execution)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        return type(exc).__name__, str(exc)
    return "PASS", None


@pytest.mark.parametrize("factory", [provider_ledger, controller_writer_ledger])
def test_every_valid_prefix_and_grouping_replays_the_same_fold(factory):
    ledger = factory()
    original = deepcopy(ledger)
    for size in range(len(ledger.events) + 1):
        prefix = SimpleNamespace(policy=ledger.policy, events=ledger.events[:size])
        assert judgment(validate, prefix) == judgment(_original_validate, prefix) == ("PASS", None)
        expected = _advance(_ProviderState(), prefix, prefix.events)
        # Every partition of this retained short lifecycle, not just singletons.
        for mask in range(1 << max(0, size - 1)):
            state = _ProviderState()
            start = 0
            for end in range(1, size + 1):
                if end == size or mask & (1 << (end - 1)):
                    state = _advance(state, prefix, prefix.events[start:end])
                    start = end
            assert state == expected
    assert ledger.policy == original.policy
    assert ledger.events == original.events


def test_group_failure_does_not_mutate_the_previously_accepted_provider_indexes():
    ledger = provider_ledger()
    prior = _advance(_ProviderState(), ledger, ledger.events[:2])
    before = deepcopy(prior)
    bad = ledger.events[2].model_copy(update={"outcome": "response_received"})
    with pytest.raises(ValueError, match="observed SDK entry"):
        _advance(prior, ledger, [bad])
    assert prior == before
    with pytest.raises(FrozenInstanceError):
        prior.event_count = 200
    assert isinstance(prior.event_ids, frozenset)
    assert all(isinstance(identity, UUID) and type(seen) is bool
               and (outcome is None or type(outcome) is str)
               for identity, seen, outcome in prior.attempts)


@pytest.mark.parametrize("mutation", [
    "sequence", "duplicate_id", "duplicate_attempt", "outcome_before_authorization",
    "sdk_twice", "known_not_sent_after_sdk", "response_before_sdk", "after_terminal",
    "unresolved_next_attempt", "completion_not_final", "completion_no_response",
    "attempt_budget", "input_budget", "output_budget", "accounting",
    "header_error_has_priority", "unknown_without_sdk", "known_not_sent_without_sdk",
])
def test_negative_history_parity_and_original_error_priority(mutation):
    ledger = provider_ledger()
    if mutation == "sequence":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"sequence": 100})
    elif mutation == "duplicate_id":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"event_id": ledger.events[0].event_id})
    elif mutation == "duplicate_attempt":
        ledger.events[-1] = ledger.events[1].model_copy(update={"sequence": 4, "event_id": uuid4()})
    elif mutation == "outcome_before_authorization":
        ledger.events[2] = ledger.events[2].model_copy(update={"provider_attempt_id": uuid4()})
    elif mutation == "sdk_twice":
        ledger.events[3] = ledger.events[3].model_copy(update={"outcome": "sdk_entered"})
    elif mutation == "known_not_sent_after_sdk":
        ledger.events[3] = ledger.events[3].model_copy(update={"outcome": "known_not_sent"})
    elif mutation in {"response_before_sdk", "header_error_has_priority"}:
        ledger.events[2] = ledger.events[2].model_copy(update={"outcome": "response_received"})
        if mutation == "header_error_has_priority":
            ledger.events[-1] = ledger.events[-1].model_copy(update={"sequence": 50})
    elif mutation == "after_terminal":
        ledger.events[-1] = ledger.events[3].model_copy(update={"sequence": 4, "event_id": uuid4()})
    elif mutation == "unresolved_next_attempt":
        ledger.events[2] = ledger.events[1].model_copy(update={"sequence": 2, "event_id": uuid4(),
            "provider_attempt_id": uuid4()})
    elif mutation == "completion_not_final":
        ledger.events.append(ledger.events[0].model_copy(update={"sequence": 5, "event_id": uuid4()}))
    elif mutation == "completion_no_response":
        ledger.events[-1] = ledger.events[-1].model_copy(update={"provider_attempt_id": uuid4()})
    elif mutation == "attempt_budget":
        ledger.policy.max_provider_attempts = 0
    elif mutation == "input_budget":
        ledger.policy.max_total_provider_input_tokens = 11
    elif mutation == "output_budget":
        ledger.policy.max_total_provider_output_tokens = 9
    elif mutation == "accounting":
        ledger.events[1] = ledger.events[1].model_copy(update={"input_estimator": "unaccepted"})
    elif mutation in {"unknown_without_sdk", "known_not_sent_without_sdk"}:
        ledger.events = ledger.events[:2] + [ledger.events[2].model_copy(update={
            "outcome": "outcome_unknown" if mutation == "unknown_without_sdk" else "known_not_sent"})]
    before = deepcopy(ledger)
    result = judgment(validate, ledger)
    assert result == judgment(_original_validate, ledger)
    assert (result[0] == "PASS") == (mutation in {"unknown_without_sdk", "known_not_sent_without_sdk"})
    assert ledger.policy == before.policy and ledger.events == before.events


def test_seeded_negative_and_partial_histories_match_frozen_provider_predicate():
    import random
    randomizer = random.Random(20261109)
    for _ in range(400):
        ledger = controller_writer_ledger()
        ledger.events = ledger.events[:randomizer.randrange(len(ledger.events) + 1)]
        if ledger.events:
            index = randomizer.randrange(len(ledger.events))
            event = ledger.events[index]
            change = randomizer.choice(["sequence", "event_id", "provider_attempt_id", "outcome", "budget", "input_type", "output_type"])
            if change == "sequence":
                ledger.events[index] = event.model_copy(update={"sequence": randomizer.randrange(9)})
            elif change == "event_id":
                ledger.events[index] = event.model_copy(update={"event_id": ledger.events[0].event_id})
            elif change == "provider_attempt_id" and hasattr(event, "provider_attempt_id"):
                ledger.events[index] = event.model_copy(update={"provider_attempt_id": uuid4()})
            elif change in {"input_type", "output_type"} and isinstance(event, t.ProviderAttemptAuthorizedEventV1):
                ledger.events[index] = event.model_copy(update={
                    "input_tokens" if change == "input_type" else "output_token_reserve": "bad"})
            elif change == "outcome" and isinstance(event, t.ProviderOutcomeEventV1):
                ledger.events[index] = event.model_copy(update={"outcome": randomizer.choice([
                    "sdk_entered", "response_received", "known_not_sent", "outcome_unknown", None, ""])})
            else:
                ledger.policy.max_total_provider_input_tokens = randomizer.choice([None, 0, 12, 24])
        assert judgment(validate, ledger) == judgment(_original_validate, ledger)


def test_completion_is_terminal_even_when_a_later_group_contains_only_nonprovider_events():
    ledger = provider_ledger()
    state = _advance(_ProviderState(), ledger, ledger.events)
    later = ledger.events[0].model_copy(update={"sequence": 5, "event_id": uuid4()})
    with pytest.raises(ValueError, match="unique and the final"):
        _advance(state, ledger, [later])


@pytest.mark.parametrize("semantic", [False, True])
def test_concrete_native_build_dispatch_and_role_accounting_remain_at_their_owner(semantic):
    from tests.test_surface_native_execution import component, controller, outcomes
    _, record = component("build", unavailable=True)
    first = controller("build", record.policy, semantic=semantic)
    second = controller("build", record.policy, sequence=3, semantic=not semantic)
    ledger = SimpleNamespace(policy=record.policy, events=[first, *outcomes(first, 1), second])
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == ("PASS", None)
    for index in (0, 3):
        bad = deepcopy(ledger)
        bad.events[index] = bad.events[index].model_copy(update={"input_estimator": "foreign-counter"})
        result = judgment(validate, bad)
        assert result == judgment(_original_validate, bad)
        assert result[0] == "ValueError"
    # Current concrete Build policies still reject a writer/foreign role in the
    # controller position; the fold does not reinterpret it as generic accounting.
    bad = deepcopy(ledger)
    bad.events[0] = first.model_copy(update={"provider": "foreign"})
    assert judgment(validate, bad) == judgment(_original_validate, bad)
    assert judgment(validate, bad)[0] == "ValueError"


def test_mutated_none_outcome_cannot_erase_observed_sdk_entry():
    ledger = provider_ledger()
    ledger.events = ledger.events[:3] + [
        ledger.events[3].model_copy(update={"sequence": 3, "outcome": None}),
        ledger.events[2].model_copy(update={"sequence": 4, "event_id": uuid4()}),
    ]
    expected = ("ValueError", "SDK entry must be the first provider outcome")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    state = _advance(_ProviderState(), ledger, ledger.events[:4])
    assert state.attempts[-1][1:] == (True, None)
    with pytest.raises(ValueError, match="SDK entry must be the first"):
        _advance(state, ledger, ledger.events[4:])


def test_structural_failure_precedes_mutated_numeric_arithmetic():
    ledger = provider_ledger()
    first = ledger.events[1].model_copy(update={"input_tokens": "bad"})
    next_attempt = first.model_copy(update={"sequence": 2, "event_id": uuid4(),
        "provider_attempt_id": uuid4()})
    ledger.events = [ledger.events[0], first, next_attempt]
    expected = ("ValueError", "a new provider attempt requires a resolved prior attempt")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    ledger.events = [ledger.events[0], first]
    ledger.policy.max_provider_attempts = 0
    expected = ("ValueError", "provider attempt policy limit exceeded")
    assert judgment(validate, ledger) == judgment(_original_validate, ledger) == expected
    ledger.policy.max_provider_attempts = 1
    assert judgment(validate, ledger) == judgment(_original_validate, ledger)
    assert judgment(validate, ledger)[0] == "TypeError"


# Resumed native Play: actual immutable work, not Plan identity or host model context.
from application_state.agent_conversation.native_play_work import project_work, validate_owner_locked
from application_state.agent_conversation.play_graph_authority import play_source_frame

def native_play_supplied(*, note=None):
    original=work('play')
    basis=original.play_basis
    if note is not None:
        from hashlib import sha256
        basis=type(basis).model_validate_json(basis.model_copy(update=dict(
            scene_note=note,scene_note_sha256=sha256(note.encode()).hexdigest())).model_dump_json(by_alias=True))
    sources=[t.PlaySourcePayloadV1(source_kind='current_moment',
        locator=t.play_source_locator(basis),text='Exact saved Play moment.')]
    if note is not None:
        sources.append(t.PlaySourcePayloadV1(source_kind='scene_note',
            locator=t.play_source_locator(basis),text=note))
    frame=play_source_frame(tuple(sources))
    context=PlayWorkContextV1(play_basis=basis,play_sources=frame.manifest,
        play_source_frame_sha256=canonical_sha256(frame))
    proof=dict(source_frame=frame.model_dump(mode='json',by_alias=True),
        session_evidence=[],dialogue=[dict(role='user',content='What is here?')])
    return context,provenance_for(context),proof


def test_projection_uses_existing_selector_frame_and_keeps_scene_note_separate():
    context,provenance,proof=native_play_supplied(note='A saved possibility.')
    frame=project_work(context,provenance,uuid4(),proof)
    assert frame['schema']=='dmb_native_play_work_v1'
    assert {s['source_kind'] for s in frame['source_frame']['sources']}=={'current_moment','scene_note'}
    assert all('text_blocks' in s and 'text' not in s for s in frame['source_frame']['sources'])
    assert frame['dialogue']==proof['dialogue'] and frame['session_evidence']==[]


def test_changed_body_cannot_reuse_frozen_manifest():
    context,provenance,proof=native_play_supplied()
    proof['source_frame']['sources'][0]['text']='Another scene.'
    with pytest.raises(ValueError):project_work(context,provenance,uuid4(),proof)


def test_same_world_foreign_run_cannot_borrow_provenance():
    context,provenance,proof=native_play_supplied()
    foreign=provenance.model_copy(update={'surface_instance_id':'play:foreign',
        'primary_work':provenance.primary_work.model_copy(update={'object_id':'another-run'})})
    with pytest.raises(ValueError):project_work(context,foreign,uuid4(),proof)


def test_unadmitted_session_packet_cannot_become_work_memory():
    context,provenance,proof=native_play_supplied()
    proof['session_evidence']=[dict(schema_version='dmb_session_evidence_v1',world_id='other',run_id='other')]
    with pytest.raises(ValueError):project_work(context,provenance,uuid4(),proof)


def test_recomputed_caller_commitment_still_needs_independent_owner(monkeypatch):
    from application_state.agent_conversation import play_graph_source_owner as owner
    context,provenance,proof=native_play_supplied()
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    changed=play_source_frame(tuple(s.model_copy(update={'text':'Invented scene.'}) for s in frame.sources))
    context=context.model_copy(update=dict(play_sources=changed.manifest,
        play_source_frame_sha256=canonical_sha256(changed)))
    proof['source_frame']=changed.model_dump(mode='json',by_alias=True)
    # Even structurally valid self-supplied hashes do not establish source ownership.
    project_work(context,provenance,uuid4(),proof)
    seen=[]
    monkeypatch.setattr(owner,'read_native_play_current_moment',lambda conn,basis,**kwargs: seen.append((basis,kwargs)) or 'Exact saved Play moment.')
    monkeypatch.setattr(owner,'resolve_play_work_sessions',lambda *args,**kwargs: pytest.fail('Moment mismatch must fail first'))
    with pytest.raises(ValueError,match='independent source owner'):
        validate_owner_locked(object(),context,provenance,proof)
    assert seen==[(context.play_basis,{'include_edition_revision':False})]


def test_locked_validation_adopts_both_existing_immutable_owners(monkeypatch):
    from application_state.agent_conversation import play_graph_source_owner as owner
    context,provenance,proof=native_play_supplied(note='Saved scene note.')
    conn=object(); seen=[]
    monkeypatch.setattr(owner,'read_native_play_current_moment',lambda c,b,**kwargs: seen.append(('moment',c,b,kwargs)) or 'Exact saved Play moment.')
    monkeypatch.setattr(owner,'resolve_play_work_sessions',lambda c,b,refs,sessions,**kw: seen.append(('sessions',c,b,refs,sessions,kw)))
    validate_owner_locked(conn,context,provenance,proof)
    assert seen[0]==('moment',conn,context.play_basis,{'include_edition_revision':False})
    assert seen[1]==('sessions',conn,context.play_basis,provenance.supporting_work,[],{'world_id':provenance.world_id})


def test_dropping_note_cannot_redefine_current_moment():
    context,provenance,proof=native_play_supplied(note='Saved note.')
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    no_note=play_source_frame(tuple(s for s in frame.sources if s.source_kind=='current_moment'))
    context=context.model_copy(update=dict(play_sources=no_note.manifest,
        play_source_frame_sha256=canonical_sha256(no_note)))
    proof['source_frame']=no_note.model_dump(mode='json',by_alias=True)
    with pytest.raises(ValueError,match='separate saved note'):
        project_work(context,provenance,uuid4(),proof)


def test_native_play_semantic_work_has_only_meaningful_text_and_local_aliases():
    from application_state.agent_conversation.native_play_work import semantic_frame
    context,provenance,proof=native_play_supplied(note='A saved possibility.')
    host=project_work(context,provenance,uuid4(),proof)
    before=deepcopy(host)
    view=semantic_frame(host)
    assert host==before
    assert set(view)=={'current_play','session_evidence','dialogue_reference'}
    assert [s['source_kind'] for s in view['current_play']]==[s['source_kind'] for s in host['source_frame']['sources']]
    assert {s['source_kind'] for s in view['current_play']}=={'current_moment','scene_note'}
    rows=[b for source in view['current_play'] for b in source['text_blocks']]
    assert [b['selection_id'] for b in rows]==['work0','work1']
    assert {s['source_kind']:''.join(b['text'] for b in s['text_blocks']) for s in view['current_play']}=={'current_moment':'Exact saved Play moment.','scene_note':'A saved possibility.'}
    raw=json.dumps(view)
    for value in (host['submission_id'],context.play_source_frame_sha256,
            str(context.play_basis.runbook_work_revision_id),context.play_basis.run_id):
        assert value not in raw
    changed=deepcopy(host);changed['source_frame']['sources'][1]['text_blocks'][0]['selection_id']=host['source_frame']['sources'][0]['text_blocks'][0]['selection_id']
    with pytest.raises(ValueError,match='repeats an authored selector'):
        semantic_frame(changed)


def test_native_play_semantic_projection_preserves_literal_identifier_like_text():
    from application_state.agent_conversation.native_play_work import semantic_frame
    literal='The author wrote run-one and sha256:abc literally; keep this note.'
    context,provenance,proof=native_play_supplied(note=literal)
    proof['dialogue']=[dict(role='user',content=literal)]
    view=semantic_frame(project_work(context,provenance,uuid4(),proof))
    note=next(s for s in view['current_play'] if s['source_kind']=='scene_note')
    assert ''.join(b['text'] for b in note['text_blocks'])==literal
    assert view['dialogue_reference']==proof['dialogue']
