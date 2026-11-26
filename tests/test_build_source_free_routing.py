"""Trust-boundary controls for the new Build source observation protocol."""
import pytest
from pydantic import ValidationError

from application_state.agent_conversation.build_source_free import (
    BuildSourceBindingObservedV1, BuildSourceObservationV1,
)


def observation(**changes):
    return dict(managed_world_id="world-author", binding=None,
                requested_revision_id=None, observed_head_revision_id=None) | changes


def binding(world="world-author"):
    return BuildSourceBindingObservedV1(managed_world_id=world,
        native_world_id="native-observed", binding_version=1)


def test_missing_core_does_not_require_manufactured_source_authority():
    pending = BuildSourceObservationV1(**observation())
    assert pending.binding is None
    assert pending.requested_or_observed_revision is None
    assert BuildSourceObservationV1.model_validate_json(
        pending.model_dump_json(by_alias=True)) == pending


@pytest.mark.parametrize("forged", [
    {"domain_ref": {}}, {"profile_ref": {}}, {"acquisition_epoch": 1},
    {"verified": True}, {"readable": True}, {"role": "gm"},
    {"source_authority": {}}, {"scope": "gm_world_cross_campaign_source_inspection"},
])
def test_observation_rejects_authority_claims(forged):
    with pytest.raises(ValidationError):
        BuildSourceObservationV1(**(observation() | forged))


def test_an_unverified_requested_revision_can_be_recorded_without_a_head():
    pending = BuildSourceObservationV1(**observation(requested_revision_id="requested-only"))
    assert pending.requested_or_observed_revision == "requested-only"
    assert pending.observed_head_revision_id is None


def test_head_cannot_be_detached_from_its_observed_binding():
    with pytest.raises(ValidationError, match="requires its observed World binding"):
        BuildSourceObservationV1(**observation(observed_head_revision_id="observed"))
    with pytest.raises(ValidationError, match="another managed World"):
        BuildSourceObservationV1(**observation(binding=binding("world-foreign")))


def test_explicit_request_is_not_replaced_by_the_observed_head():
    pending = BuildSourceObservationV1(**observation(binding=binding(),
        requested_revision_id="explicit-historical", observed_head_revision_id="current-head"))
    assert pending.requested_or_observed_revision == "explicit-historical"
    assert pending.observed_head_revision_id == "current-head"


@pytest.mark.parametrize("changes", [
    {"managed_world_id": ""}, {"requested_revision_id": ""},
    {"requested_revision_id": 7}, {"observed_head_revision_id": False},
])
def test_observation_rejects_unusable_or_coerced_identities(changes):
    with pytest.raises(ValidationError):
        BuildSourceObservationV1(**observation(**changes))


class MetadataOnlyRepository:
    def __init__(self, head):
        self.head, self.calls = head, []

    def get_head(self, space_id):
        self.calls.append(("get_head", space_id))
        return self.head

    def __getattr__(self, name):
        raise AssertionError("Unexpected content/catalog owner: " + name)


def observe(*, repository=None, resolve=None, principal=None, revision=None):
    from types import SimpleNamespace as NS
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import observe_build_source_pointer
    return observe_build_source_pointer(managed_world_id="world-author",
        principal=principal if principal is not None else NS(role="gm", managed_world_id="world-author"),
        revision_id=revision, repository=repository,
        resolve_identity=resolve if resolve is not None else lambda _: binding())


def test_metadata_observer_reads_only_the_observed_world_head():
    from types import SimpleNamespace as NS
    repository = MetadataOnlyRepository(NS(space_id="native-observed", head_revision_id="head-only"))
    pending = observe(repository=repository)
    assert repository.calls == [("get_head", "native-observed")]
    assert pending.observed_head_revision_id == "head-only"
    assert pending.requested_revision_id is None


def test_requested_revision_does_not_probe_its_content_or_replace_it_with_head():
    repository = MetadataOnlyRepository(None)
    pending = observe(repository=repository, revision="requested-unverified")
    assert repository.calls == []
    assert pending.requested_or_observed_revision == "requested-unverified"
    assert pending.observed_head_revision_id is None


def test_missing_head_keeps_a_binding_without_inventing_a_revision():
    repository = MetadataOnlyRepository(None)
    pending = observe(repository=repository)
    assert repository.calls == [("get_head", "native-observed")]
    assert pending.binding == binding()
    assert pending.requested_or_observed_revision is None


@pytest.mark.parametrize("code", ["native_graph_binding_missing", "native_graph_binding_inactive"])
def test_missing_binding_does_not_open_core(code):
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    def missing(_):
        raise WorldGraphProjectionServiceError("fixture", code=code, status_code=409)
    repository = MetadataOnlyRepository(None)
    pending = observe(repository=repository, resolve=missing)
    assert pending.binding is None
    assert repository.calls == []


def test_unknown_world_or_access_failure_is_not_missing_source_context():
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    def forbidden(_):
        raise WorldGraphProjectionServiceError("fixture", code="managed_world_forbidden", status_code=403)
    with pytest.raises(WorldGraphProjectionServiceError):
        observe(repository=MetadataOnlyRepository(None), resolve=forbidden)


@pytest.mark.parametrize("principal", [("player", "world-author"), ("gm", "foreign-world")])
def test_observation_does_not_weaken_principal_scope(principal):
    from types import SimpleNamespace as NS
    repository = MetadataOnlyRepository(None)
    with pytest.raises(ValueError):
        observe(repository=repository, principal=NS(role=principal[0], managed_world_id=principal[1]))
    assert repository.calls == []


def test_observation_refuses_binding_changes_during_head_read():
    from types import SimpleNamespace as NS
    states = iter([binding(), BuildSourceBindingObservedV1(managed_world_id="world-author",
        native_world_id="different-native", binding_version=2)])
    with pytest.raises(ValueError, match="ownership changed"):
        observe(repository=MetadataOnlyRepository(NS(space_id="native-observed", head_revision_id="head")),
                resolve=lambda _: next(states))


def test_observation_refuses_a_head_returned_for_another_native_world():
    from types import SimpleNamespace as NS
    with pytest.raises(ValueError, match="another native World"):
        observe(repository=MetadataOnlyRepository(NS(space_id="foreign-native", head_revision_id="head")))



def pending_receipt_values(**changes):
    from uuid import uuid4
    from application_state.agent_conversation.types import BuildSourceContextBasisV1
    from application_state.agent_conversation.native_context import (
        BuildWorkContextV1, NativeBuildPendingProviderInputV3,
    )
    work = BuildWorkContextV1(source_basis=BuildSourceContextBasisV1(
        world_id="world-author", document_id=str(uuid4()), registry_revision=1,
        content_sha256="a" * 64, visibility="internal"))
    initial = NativeBuildPendingProviderInputV3(provider_model_name="test-model",
        provider_model_version="test-version", tokenizer_name="test-tokenizer",
        tokenizer_version="test-version", provider_envelope_input_tokens=10,
        output_token_reserve=20, context_window_limit=100, included_history=(),
        assembled_input_sha256="b" * 64)
    return dict(schema="dmb_build_pending_context_receipt_v1",
        receipt_serializer_version="canonical-json-utf8-v1", provenance_sha256="c" * 64,
        work_context=work.model_dump(mode="json"),
        source_observation=BuildSourceObservationV1(**observation()).model_dump(mode="json", by_alias=True),
        conversation_observation={'conversation_id': str(uuid4()), 'pointer_revision': 0},
        assembled_input=initial.model_dump(mode="json")) | changes


def seal_pending_receipt(values):
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    return BuildPendingContextReceiptV1.model_validate(dict(values,
        context_receipt_sha256=canonical_sha256(values)))


def test_pending_receipt_is_bound_to_its_actual_build_world_and_all_fields():
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    receipt = seal_pending_receipt(pending_receipt_values())
    wire = receipt.model_dump_json(by_alias=True)
    assert BuildPendingContextReceiptV1.model_validate_json(wire) == receipt
    forged = receipt.model_dump(mode="json", by_alias=True)
    forged["source_observation"]["requested_revision_id"] = "uncommitted-replacement"
    with pytest.raises(ValidationError, match="digest differs"):
        BuildPendingContextReceiptV1.model_validate(forged)


def test_recomputed_pending_receipt_cannot_borrow_a_foreign_world_observation():
    foreign = BuildSourceObservationV1(**observation(managed_world_id="foreign-world"))
    with pytest.raises(ValidationError, match="actual work World"):
        seal_pending_receipt(pending_receipt_values(
            source_observation=foreign.model_dump(mode="json", by_alias=True)))


@pytest.mark.parametrize("field", ["source_authority", "native_query", "domain_ref", "profile_ref"])
def test_recomputed_pending_receipt_cannot_become_a_source_receipt(field):
    with pytest.raises(ValidationError):
        seal_pending_receipt(pending_receipt_values(**{field: {}}))


def test_pending_receipt_cannot_use_a_historical_initial_assembler():
    values = pending_receipt_values()
    values["assembled_input"]["assembler_version"] = "native_build_semantic_initial_v2"
    with pytest.raises(ValidationError):
        seal_pending_receipt(values)


def test_pending_receipt_rejects_a_non_build_work_discriminator():
    values = pending_receipt_values()
    values["work_context"]["surface_id"] = "plan"
    with pytest.raises(ValidationError):
        seal_pending_receipt(values)



def settled_source(**changes):
    from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
    reference = dict(authority_id="test-descriptor", revision="test-revision", descriptor_sha256="d" * 64)
    return NativeCorpusAuthorityV1(**(dict(managed_world_id="world-author", native_world_id="native-observed",
        binding_version=1, provisioning_id=None, revision_id="observed-revision",
        domain_ref=reference, profile_ref=reference, acquisition_epoch=1) | changes))


def pending_with_binding(**changes):
    observed = BuildSourceObservationV1(**observation(binding=binding(),
        observed_head_revision_id="observed-revision", **changes))
    return seal_pending_receipt(pending_receipt_values(
        source_observation=observed.model_dump(mode="json", by_alias=True)))


def source_settlement(receipt, *, authority=None, query_world="world-author"):
    from uuid import uuid4
    from application_state.agent_conversation.native_execution import NativeBuildSourceSettledV1
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    return NativeBuildSourceSettledV1(event_id=uuid4(), sequence=3, admitted_from_revision=2,
        pending_context_receipt_sha256=receipt.context_receipt_sha256,
        work_event_id=uuid4(), source_authority=authority if authority is not None else settled_source(),
        native_query=NativePlanQueryUnavailableV1(managed_world_id=query_world,
            reason="native_graph_binding_unavailable"))


def test_source_settlement_joins_only_its_captured_observation():
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = pending_with_binding()
    original = receipt.model_dump_json(by_alias=True)
    event = source_settlement(receipt)
    assert validate_pending_source_settlement(receipt, event) is None
    assert receipt.model_dump_json(by_alias=True) == original


@pytest.mark.parametrize("changes", [
    {"managed_world_id": "foreign-world"}, {"native_world_id": "different-native"},
    {"binding_version": 2}, {"provisioning_id": "new-provisioning"},
    {"revision_id": "newer-head"},
])
def test_source_settlement_rejects_scope_substitution(changes):
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = pending_with_binding()
    source = settled_source(**changes)
    event = source_settlement(receipt, authority=source, query_world=source.managed_world_id)
    with pytest.raises(ValueError):
        validate_pending_source_settlement(receipt, event)


def test_unobserved_source_cannot_be_replaced_by_a_later_available_head():
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = seal_pending_receipt(pending_receipt_values())
    with pytest.raises(ValueError, match="Unobserved source scope"):
        validate_pending_source_settlement(receipt, source_settlement(receipt))


def test_explicit_historical_request_is_not_settled_as_the_observed_head():
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = pending_with_binding(requested_revision_id="explicit-historical")
    with pytest.raises(ValueError, match="requested or observed revision"):
        validate_pending_source_settlement(receipt, source_settlement(receipt))
    assert validate_pending_source_settlement(receipt, source_settlement(receipt,
        authority=settled_source(revision_id="explicit-historical"))) is None


def test_source_settlement_refuses_a_different_pending_receipt():
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = pending_with_binding()
    event = source_settlement(receipt).model_copy(update={"pending_context_receipt_sha256": "f" * 64})
    with pytest.raises(ValueError, match="pending receipt"):
        validate_pending_source_settlement(receipt, event)


def test_source_settlement_revalidates_constructed_or_copied_records():
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1
    receipt = pending_with_binding()
    event = source_settlement(receipt).model_copy(update={"native_query": NativePlanQueryUnavailableV1(
        managed_world_id="foreign-world", reason="native_graph_binding_unavailable")})
    with pytest.raises(ValidationError, match="another managed World"):
        validate_pending_source_settlement(receipt, event)
    bad_receipt = receipt.model_copy(update={"context_receipt_sha256": "f" * 64})
    with pytest.raises(ValidationError, match="digest differs"):
        validate_pending_source_settlement(bad_receipt, source_settlement(receipt))



def prepared_query(source, **authority_changes):
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryAuthorityV1
    authority = NativePlanQueryAuthorityV1(**({key: getattr(source, key) for key in (
        "managed_world_id", "native_world_id", "binding_version", "revision_id", "domain_ref",
        "profile_ref", "acquisition_epoch")} | dict(scope_mode="world", campaign_id=None) | authority_changes))
    return NativeGraphQueryV4(authority=authority, question="Test requested source question",
        search_result_sha256="e" * 64, discovered_entity_ids=(), matches=(), status="complete",
        gap_codes=(), assertion_matches=(), authored_targets=(), object_matches=())


def test_settlement_keeps_graph_query_and_source_authority_in_the_same_scope():
    from application_state.agent_conversation.native_execution import NativeBuildSourceSettledV1
    from application_state.agent_conversation.build_source_free import validate_pending_source_settlement
    receipt = pending_with_binding()
    original = source_settlement(receipt)
    values = original.model_dump(mode="python")
    values["native_query"] = prepared_query(original.source_authority)
    event = NativeBuildSourceSettledV1.model_validate(values)
    assert validate_pending_source_settlement(receipt, event) is None


@pytest.mark.parametrize("changes", [
    {"managed_world_id": "foreign-world"}, {"native_world_id": "foreign-native"},
    {"binding_version": 2}, {"revision_id": "other-revision"}, {"acquisition_epoch": 2},
    {"domain_ref": dict(authority_id="other-domain", revision="test-revision", descriptor_sha256="d" * 64)},
    {"profile_ref": dict(authority_id="other-profile", revision="test-revision", descriptor_sha256="d" * 64)},
    {"scope_mode": "campaign", "campaign_id": "different-scope"},
    {"campaign_id": "hidden-campaign"},
    {"campaign_id": "hidden-campaign", "session_id": "hidden-session"},
])
def test_settlement_refuses_a_graph_query_from_a_different_authority(changes):
    from application_state.agent_conversation.native_execution import NativeBuildSourceSettledV1
    receipt = pending_with_binding()
    original = source_settlement(receipt)
    values = original.model_dump(mode="python")
    values["native_query"] = prepared_query(original.source_authority, **changes)
    with pytest.raises(ValidationError, match="prepared source authority"):
        NativeBuildSourceSettledV1.model_validate(values)



def test_pending_settlement_does_not_smuggle_unselected_authored_targets():
    from application_state.agent_conversation.native_execution import NativeBuildSourceSettledV1
    from application_state.agent_conversation.native_plan_assertions import NativeAuthoredTargetV1
    receipt = pending_with_binding()
    original = source_settlement(receipt)
    query = prepared_query(original.source_authority).model_copy(update={"authored_targets": (
        NativeAuthoredTargetV1(node_id="unselected-node", selection_revision_id="unselected-revision",
            matches=(), assertion_matches=(), status="complete", gap_codes=()),)})
    values = original.model_dump(mode="python")
    values["native_query"] = query
    with pytest.raises(ValidationError, match="prepared source authority"):
        NativeBuildSourceSettledV1.model_validate(values)



def pending_policy_values():
    from tests.test_surface_native_execution import component
    _, execution = component("build")
    values = execution.policy.model_dump(mode="python", by_alias=True)
    for key in ("policy_version", "source_authority_sha256", "native_query_sha256"):
        values.pop(key)
    values["source_observation_sha256"] = "e" * 64
    return values


def test_pending_policy_commits_observation_without_fabricated_source_hashes():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    policy = BuildPendingExecutionPolicyV1.model_validate(pending_policy_values())
    wire = policy.model_dump_json(by_alias=True)
    assert BuildPendingExecutionPolicyV1.model_validate_json(wire) == policy
    assert "source_authority_sha256" not in type(policy).model_fields
    assert "native_query_sha256" not in type(policy).model_fields
    assert policy.action.related_page_catalog is None


@pytest.mark.parametrize("fields", [
    {"source_authority_sha256": "f" * 64}, {"native_query_sha256": "f" * 64},
    {"policy_version": "surface_native_execution_v1"},
    {"source_observation_sha256": "not-a-digest"},
])
def test_pending_policy_rejects_old_authority_or_policy_substitution(fields):
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    with pytest.raises(ValidationError):
        BuildPendingExecutionPolicyV1.model_validate(pending_policy_values() | fields)


def test_pending_policy_does_not_treat_an_empty_discovered_catalog_as_no_discovery():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = pending_policy_values()
    values["action"]["related_page_catalog"] = ()
    with pytest.raises(ValidationError, match="acquired related-page catalog"):
        BuildPendingExecutionPolicyV1.model_validate(values)


def test_pending_policy_keeps_the_actual_build_controller_role():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = pending_policy_values()
    values["provider_roles"]["controller"]["api_mode"] = "decision"
    with pytest.raises(ValidationError, match="roles differ"):
        BuildPendingExecutionPolicyV1.model_validate(values)


def test_pending_policy_keeps_the_actual_writer_budget_identity():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = pending_policy_values()
    values["provider_roles"]["writer"]["model"] = "different-writer"
    with pytest.raises(ValidationError):
        BuildPendingExecutionPolicyV1.model_validate(values)


@pytest.mark.parametrize("field", ["controller_continuation_accounting", "writer_context_budget"])
def test_pending_policy_cannot_omit_the_frozen_role_accounting(field):
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = pending_policy_values()
    values[field] = None
    with pytest.raises(ValidationError):
        BuildPendingExecutionPolicyV1.model_validate(values)



def estimated_pending_policy_values():
    values = pending_policy_values()
    counter = values["controller_continuation_accounting"]
    values["writer_context_budget"] = dict(schema="dmb_native_writer_estimated_budget_v1",
        provider="openai", model="gpt-6-luna", api_mode="responses",
        estimator=counter["policy"], tokenizer_version=counter["tokenizer_version"],
        context_limit_tokens=None, output_reserve_tokens=0)
    return values


def test_pending_policy_preserves_current_provider_owned_writer_allowance():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    policy = BuildPendingExecutionPolicyV1.model_validate(estimated_pending_policy_values())
    assert policy.writer_context_budget.context_limit_tokens is None
    assert policy.writer_context_budget.output_reserve_tokens == 0
    assert policy.writer_context_budget.estimator == policy.controller_continuation_accounting.policy


def test_pending_policy_rejects_a_different_writer_tokenizer():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = estimated_pending_policy_values()
    values["writer_context_budget"]["tokenizer_version"] = "different-tokenizer"
    with pytest.raises(ValidationError, match="writer accounting differs"):
        BuildPendingExecutionPolicyV1.model_validate(values)


def test_pending_policy_rejects_a_different_writer_and_controller_estimator():
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    values = estimated_pending_policy_values()
    values["controller_continuation_accounting"].update(
        policy="o200k_double_plus_4096_adaptive_context_v3", raw_wire_limit_bytes=256000)
    with pytest.raises(ValidationError, match="writer accounting differs"):
        BuildPendingExecutionPolicyV1.model_validate(values)


def pending_execution_pair(*, with_source=False, captured_case=None):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1
    from tests.test_surface_native_execution import component
    context, original = component('build') if captured_case is None else captured_case[:2]
    world = context.work_context.source_basis.world_id
    observed = BuildSourceObservationV1(managed_world_id=world,
        binding=BuildSourceBindingObservedV1(managed_world_id=world,
            native_world_id='native-observed', binding_version=1) if with_source else None,
        requested_revision_id=None, observed_head_revision_id='observed-revision' if with_source else None)
    from uuid import uuid4
    conversation = ({'conversation_id': str(uuid4()), 'pointer_revision': 0} if captured_case is None else {
        'conversation_id': str(captured_case[2].record.conversation_id),
        'pointer_revision': captured_case[2].record.expected_pointer_revision})
    receipt = seal_pending_receipt(pending_receipt_values(
        work_context=context.work_context.model_dump(mode='json'),
        conversation_observation=conversation,
        source_observation=observed.model_dump(mode='json', by_alias=True),
        assembled_input=pending_receipt_values()['assembled_input'] | {
            'provider_model_name': original.policy.provider_roles.controller.model,
            'tokenizer_name': original.policy.controller_continuation_accounting.policy,
            'provider_envelope_input_tokens': 120, 'output_token_reserve': 200,
            'context_window_limit': 128000, 'assembled_input_sha256': 'd' * 64}))
    values = original.policy.model_dump(mode='python', by_alias=True)
    for key in ('policy_version', 'source_authority_sha256', 'native_query_sha256'):
        values.pop(key)
    policy = BuildPendingExecutionPolicyV1.model_validate(values | {
        'source_observation_sha256': t.canonical_sha256(observed)})
    return receipt, policy


def pending_execution(receipt, policy, events=()):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.native_execution import BuildPendingExecutionV1
    data = dict(schema='dmb_build_pending_execution_v1',
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=policy.model_dump(mode='json', by_alias=True))
    import json
    return BuildPendingExecutionV1.model_validate_json(json.dumps(data | {
        'execution_policy_sha256': t.canonical_sha256(data),
        'events': [event.model_dump(mode='json', by_alias=True) for event in events]}))


def pending_work_prefix(policy, *, scope='source_lookup'):
    from tests.test_surface_native_execution import controller, outcomes, build_resolution
    from application_state.agent_conversation.build_intentional_response import resolution_for
    first = controller('build', policy)
    work = build_resolution(policy, first, 3)
    work = type(work).model_validate(work.model_dump(mode='python') | {
        'resolution': resolution_for(policy, 'discuss', source_scope=scope)})
    return [first, *outcomes(first, 1), work]


def pending_settlement(receipt, policy, work):
    from application_state.agent_conversation.native_execution import NativeBuildSourceSettledV1
    source = settled_source(managed_world_id=policy.action.intent.world_id)
    query = prepared_query(source).model_copy(update={'question': policy.action.intent.message})
    original = source_settlement(receipt, authority=source, query_world=source.managed_world_id)
    return NativeBuildSourceSettledV1.model_validate(original.model_dump(mode='python') | {
        'sequence': 4, 'work_event_id': work.event_id, 'native_query': query})


def test_pending_decision_without_core_does_not_manufacture_effective_source():
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair()
    execution = pending_execution(receipt, policy, pending_work_prefix(policy, scope='anchored'))
    assert effective_pending_source(receipt, execution) is None
    # Reopening this new prefix must not silently decode as the old authority-bearing pair.
    from application_state.agent_conversation.native_execution import SurfaceNativeExecutionV1
    with pytest.raises(ValidationError):
        SurfaceNativeExecutionV1.model_validate_json(execution.model_dump_json(by_alias=True))


def test_pending_settlement_exposes_only_its_exact_observed_authority_and_query():
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair(with_source=True)
    events = pending_work_prefix(policy)
    settled = pending_settlement(receipt, policy, events[-1])
    execution = pending_execution(receipt, policy, [*events, settled])
    assert effective_pending_source(receipt, execution) == (settled.source_authority, settled.native_query)
    assert receipt.source_observation.requested_or_observed_revision == 'observed-revision'


@pytest.mark.parametrize('mutation', ['anchored', 'wrong_work', 'wrong_context', 'different_question', 'duplicate'])
def test_pending_settlement_cannot_replace_the_selected_work_or_frozen_request(mutation):
    from uuid import uuid4
    receipt, policy = pending_execution_pair(with_source=True)
    events = pending_work_prefix(policy, scope='anchored' if mutation == 'anchored' else 'source_lookup')
    settled = pending_settlement(receipt, policy, events[-1])
    if mutation == 'wrong_work':
        settled = settled.model_copy(update={'work_event_id': uuid4()})
    if mutation == 'wrong_context':
        settled = settled.model_copy(update={'pending_context_receipt_sha256': 'f' * 64})
    if mutation == 'different_question':
        settled = settled.model_copy(update={'native_query': settled.native_query.model_copy(update={'question': 'Substituted question'})})
    extra = [settled.model_copy(update={'event_id': uuid4(), 'sequence': 5})] if mutation == 'duplicate' else []
    with pytest.raises(ValidationError):
        pending_execution(receipt, policy, [*events, settled, *extra])


def test_pending_effective_source_rejects_a_rehashed_new_revision():
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair(with_source=True)
    events = pending_work_prefix(policy)
    settled = pending_settlement(receipt, policy, events[-1])
    source = settled.source_authority.model_copy(update={'revision_id': 'later-head'})
    query = prepared_query(source).model_copy(update={'question': policy.action.intent.message})
    execution = pending_execution(receipt, policy, [*events, settled.model_copy(update={
        'source_authority': source, 'native_query': query})])
    with pytest.raises(ValueError, match='requested or observed revision'):
        effective_pending_source(receipt, execution)


def test_pending_prefix_refuses_a_complete_old_catalog_settlement():
    from uuid import uuid4
    from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1
    receipt, policy = pending_execution_pair()
    events = pending_work_prefix(policy)
    query = prepared_query(settled_source()).model_copy(update={'question': policy.action.intent.message})
    old = NativeBuildQuerySettledV1(event_id=uuid4(), sequence=4,
        controller_attempt_id=events[0].provider_attempt_id, query=query)
    with pytest.raises(ValidationError, match='union_tag_invalid'):
        pending_execution(receipt, policy, [*events, old])


def test_pending_prefix_keeps_provider_role_and_outcome_unknown_guards():
    from tests.test_surface_native_execution import native_writer, controller
    receipt, policy = pending_execution_pair()
    events = pending_work_prefix(policy)
    writer = native_writer('build', policy, sequence=4)
    with pytest.raises(ValidationError, match='union_tag_invalid'):
        pending_execution(receipt, policy, [*events, writer])
    changed = events[:3]
    changed[-1] = changed[-1].model_copy(update={'outcome': 'outcome_unknown'})
    second = controller('build', policy, sequence=3)
    with pytest.raises(ValidationError, match='resolved prior attempt'):
        pending_execution(receipt, policy, [*changed, second])


def test_pending_role_accounting_still_rejects_a_wrong_estimator():
    receipt, policy = pending_execution_pair()
    events = pending_work_prefix(policy)
    events[0] = events[0].model_copy(update={'input_estimator': 'borrowed-estimator'})
    with pytest.raises(ValidationError, match='accounting differs'):
        pending_execution(receipt, policy, events)


def test_pending_first_decision_keeps_complete_captured_draft_and_rejects_substitution():
    from hashlib import sha256
    from application_state.agent_conversation.build_source_free import effective_pending_source
    from tests.test_surface_native_build_work import case
    captured = case()
    receipt, policy = pending_execution_pair(captured_case=captured)
    events = captured[1].events[:5]
    execution = pending_execution(receipt, policy, events)
    assert execution.events[0].record.snapshot.draft_markdown == captured[2].record.snapshot.draft_markdown
    assert effective_pending_source(receipt, execution) is None
    changed = events[0].record.snapshot.model_copy(update={
        'draft_markdown': 'Substituted premise', 'draft_sha256': sha256(b'Substituted premise').hexdigest()})
    forged = events[0].model_copy(update={'record': events[0].record.model_copy(update={'snapshot': changed})})
    with pytest.raises(ValidationError, match='submitted first-decision context'):
        pending_execution(receipt, policy, [forged, *events[1:]])
    with pytest.raises(ValidationError, match='submitted draft capture first'):
        pending_execution(receipt, policy, [event.model_copy(update={'sequence': index})
            for index, event in enumerate(events[1:])])


def test_pending_observation_cannot_replace_a_rehashed_explicit_request_pin():
    from application_state.agent_conversation.build_source_free import effective_pending_source
    receipt, policy = pending_execution_pair(with_source=True)
    request = policy.action.intent.graph_request.model_copy(update={'revision_pin': 'explicit-other'})
    intent = policy.action.intent.model_copy(update={'graph_request': request})
    policy = policy.model_copy(update={'action': policy.action.model_copy(update={'intent': intent})})
    execution = pending_execution(receipt, policy)
    with pytest.raises(ValueError, match='explicitly requested revision'):
        effective_pending_source(receipt, execution)


def test_pending_work_closes_controller_phase_but_keeps_preselection_retries():
    from uuid import uuid4
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from tests.test_surface_native_execution import controller, outcomes, build_resolution
    receipt, policy = pending_execution_pair(with_source=True)
    events = pending_work_prefix(policy)
    late = controller('build', policy, sequence=4)
    settled = pending_settlement(receipt, policy, events[-1]).model_copy(update={'sequence': 5})
    with pytest.raises(ValidationError, match='precede work selection'):
        pending_execution(receipt, policy, [*events, late, settled])
    first = controller('build', policy)
    not_sent = t.ProviderOutcomeEventV1(kind='provider_outcome', event_id=uuid4(), sequence=1,
        provider_attempt_id=first.provider_attempt_id, outcome='known_not_sent')
    retry = controller('build', policy, sequence=2)
    selected = build_resolution(policy, retry, 5)
    selected = type(selected).model_validate(selected.model_dump(mode='python') | {
        'resolution': resolution_for(policy, 'discuss', source_scope='source_lookup')})
    settled = pending_settlement(receipt, policy, selected).model_copy(update={'sequence': 6})
    execution = pending_execution(receipt, policy, [first, not_sent, retry, *outcomes(retry, 3), selected, settled])
    assert execution.events[-1].work_event_id == selected.event_id


@pytest.mark.parametrize('explicit_limitation,bad_citation', [(False, False), (True, False), (False, True)])
def test_anchored_chat_draft_creative_warning_respects_writer(monkeypatch, explicit_limitation, bad_citation):
    """The real pending writer must not invent a retrieval warning for a chat draft."""
    import asyncio
    import json
    from contextlib import contextmanager
    import httpx
    from generationengine import GenerationEngineError
    from apps.live_control_server.services import build_jev_dispatch
    from tests import test_build_source_free_protocol as owner

    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    from application_state.agent_conversation import conversation_drafts
    drafts=[]
    monkeypatch.setattr(conversation_drafts, 'create_draft',
                        lambda conn, **kwargs: drafts.append(kwargs['markdown']))
    original = owner.pending_retained_runtime_case
    @contextmanager
    def draft_seed(monkeypatch, *, lore_page=False):
        with original(monkeypatch, lore_page=lore_page, chat_draft=True) as value:
            yield value
    monkeypatch.setattr(owner, 'pending_retained_runtime_case', draft_seed)

    def respond(request):
        body = json.loads(request.content)
        candidate = {'answer_segments': [{'kind': 'proposal', 'label': 'invented_idea',
            'text': 'Breezy Bee and Pocket Breeze.'}],
            'limitations': ['partial_retrieval'] if explicit_limitation else []}
        if bad_citation:
            candidate['answer_segments'].append({'kind': 'source_passage_claim',
                'text': 'Unsupported.', 'passage_handles': ['unbound']})
        if 'collaboration' in body['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_draft', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_draft', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})

    with owner.pending_writer_completion_case(monkeypatch) as (state, adapter, rules, writer, prepared):
        if bad_citation:
            with pytest.raises(GenerationEngineError):
                asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
            assert state.completions == 0
        else:
            completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
            assert completed.status == 'completed' and state.completions == 1
            assert drafts == [completed.assistant_text]
            warning = 'This answer uses partial retrieval and does not establish corpus completeness.'
            assert (warning in completed.assistant_text) is explicit_limitation
        assert state.materialized == 0


def test_old_chat_draft_projection_is_rejected_atomically_by_new_owner(monkeypatch):
    """A draft prepared under the old projection cannot partially commit after cutover."""
    from contextlib import contextmanager
    from tests import test_build_source_free_protocol as owner
    original = owner.pending_retained_runtime_case
    @contextmanager
    def draft_seed(monkeypatch, *, lore_page=False):
        with original(monkeypatch, lore_page=lore_page, chat_draft=True) as value:
            yield value
    monkeypatch.setattr(owner, 'pending_retained_runtime_case', draft_seed)
    owner.test_old_projection_rejected_atomically_by_new_acceptance_owner(monkeypatch)


def test_existing_chat_draft_with_old_warning_replays_unchanged(monkeypatch):
    """Already accepted pre-cutover drafts retain their original text and evidence."""
    from contextlib import contextmanager
    from application_state.agent_conversation import conversation_drafts
    from tests import test_build_source_free_protocol as owner
    original = owner.pending_retained_runtime_case
    @contextmanager
    def draft_seed(monkeypatch, *, lore_page=False):
        with original(monkeypatch, lore_page=lore_page, chat_draft=True) as value:
            yield value
    monkeypatch.setattr(owner, 'pending_retained_runtime_case', draft_seed)
    monkeypatch.setattr(conversation_drafts, 'create_draft', lambda conn, **kwargs: None)
    owner.test_pending_preexisting_creative_warning_replays_unchanged(monkeypatch, False)


@pytest.mark.parametrize('scope', ['source_lookup', 'uncertain'])
def test_chat_draft_with_unresolved_source_need_is_not_anchored(monkeypatch, scope):
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from application_state.agent_conversation.build_source_free import pending_retained_work
    from tests import test_build_source_free_protocol as owner
    with owner.pending_retained_runtime_case(monkeypatch, chat_draft=True) as (state, adapter, turns):
        execution = state.turn.graph_context_execution
        work, = [e for e in execution.events if type(e) is t.BuildRequestedWorkResolutionV1]
        revised = work.model_copy(update={'resolution': resolution_for(execution.policy, 'draft_in_conversation', source_scope=scope)})
        changed = owner.pending_execution(state.turn.graph_context_receipt, execution.policy,
            [revised if e.event_id == work.event_id else e for e in execution.events])
        assert pending_retained_work(changed) is None

@pytest.mark.parametrize('label', ['change_mechanics', 'build_encounter', 'place_map_coordinates',
                                    'save_page', 'publish_relationships', 'other_creation'])
def test_unavailable_action_completes_capability_reply_without_acquisition(monkeypatch, label):
    """An unavailable executor is not a reason to acquire World sources."""
    import asyncio
    import json
    import httpx
    from tests import test_build_source_free_protocol as owner
    from apps.live_control_server.services import build_jev_dispatch
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    def respond(request):
        body = json.loads(request.content)
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': 'I cannot perform that action here.'}], 'limitations': []}
        if 'collaboration' in body['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_unavailable', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_unavailable', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    with owner.pending_writer_completion_case(monkeypatch, source_free_work=label, source_scope='anchored') as (state, adapter, rules, writer, prepared):
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and state.completions == 1
        assert 'cannot perform' in completed.assistant_text
        assert state.retained_reads == 0 and state.materialized == 0


def test_unavailable_action_harness_skips_native_retrieval(monkeypatch):
    from types import SimpleNamespace
    from tests import test_build_source_free_protocol as owner
    from application_state.agent_conversation import types as t
    from apps.live_control_server.services import (build_jev_dispatch, build_jev_writer_selection,
        build_pending_native_retrieval, plan_jev_rules_runtime, plan_jev_writer)
    from apps.live_control_server.services.build_jev_harness import BuildJevHarness
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    with owner.pending_writer_runtime_case(monkeypatch, source_free_work='other_creation', source_scope='anchored') as (state, adapter, selector, turns):
        work = next(row for row in state.turn.graph_context_execution.events if type(row) is t.BuildRequestedWorkResolutionV1)
        def forbidden(*args, **kwargs):
            raise AssertionError('An unavailable executor must not open native retrieval')
        monkeypatch.setattr(build_pending_native_retrieval, 'run_pending_native_retrieval', forbidden)
        class Rules:
            def __init__(self, *args): pass
            def restore_pending(self): pass
        monkeypatch.setattr(plan_jev_rules_runtime, 'PlanRulesRuntime', Rules)
        class Selection:
            catalog = ()
            def __init__(self, actual_adapter, driver, terminal):
                assert terminal == {'status': 'ready', 'reason': 'pending_source_free_other_creation'}
            def settle_empty(self): pass
        monkeypatch.setattr(build_jev_writer_selection, 'WriterSelectionDriver', Selection)
        result = object()
        class Writer:
            call = None
            output_limit_exceeded = False
            failure_stage = 'capture'
            def __init__(self, *args, **kwargs): pass
            async def run(self, **kwargs): return result
        monkeypatch.setattr(plan_jev_writer, 'PlanJevWriter', Writer)
        adapter.build_frozen_history = ()
        adapter.stop = lambda: None
        harness = BuildJevHarness()
        harness.calls, harness.rules_capability, harness.writer_transport = [], None, None
        assert harness._native_completion(adapter, SimpleNamespace(operation=work.operation, selection=work)) is result
        assert state.retained_reads == 0 and state.materialized == 0


def test_unavailable_terminal_requires_acknowledged_valid_barrier(monkeypatch):
    from tests import test_build_source_free_protocol as owner
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_source_free import pending_source_free_terminal
    from apps.live_control_server.services import build_jev_dispatch
    from application_state.agent_conversation import native_execution
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    with owner.pending_writer_runtime_case(monkeypatch, source_free_work='other_creation', source_scope='anchored') as (state, adapter, selector, turns):
        execution = state.turn.graph_context_execution
        events = list(execution.events)
        work_index = next(i for i, row in enumerate(events) if type(row) is t.BuildRequestedWorkResolutionV1)
        work = events[work_index]
        events[work_index] = work.model_copy(update={'resolution': work.resolution | {'barrier': None}})
        with pytest.raises(ValueError):
            pending_source_free_terminal(execution.model_copy(update={'events': events}))
        events = list(execution.events)
        outcome_index = max(i for i, row in enumerate(events) if type(row) is t.ProviderOutcomeEventV1 and row.provider_attempt_id == work.controller_attempt_id)
        events[outcome_index] = events[outcome_index].model_copy(update={'outcome': 'failed'})
        assert pending_source_free_terminal(execution.model_copy(update={'events': events})) is None

        monkeypatch.setattr(native_execution, 'native_read_event_ids', lambda events: ['prior-read'])
        assert pending_source_free_terminal(execution) is None


@pytest.mark.parametrize('scope', ['source_lookup'])
def test_unavailable_terminal_does_not_skip_required_or_uncertain_source(monkeypatch, scope):
    from tests import test_build_source_free_protocol as owner
    from application_state.agent_conversation import types as t
    from application_state.agent_conversation.build_source_free import pending_source_free_terminal
    from application_state.agent_conversation.build_intentional_response import resolution_for
    from apps.live_control_server.services import build_jev_dispatch
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    with owner.pending_writer_runtime_case(monkeypatch, source_free_work='other_creation', source_scope='anchored') as (state, adapter, selector, turns):
        execution = state.turn.graph_context_execution
        events = list(execution.events)
        index = next(i for i, row in enumerate(events) if type(row) is t.BuildRequestedWorkResolutionV1)
        events[index] = events[index].model_copy(update={'resolution': resolution_for(execution.policy, 'other_creation', source_scope=scope)})
        assert pending_source_free_terminal(execution.model_copy(update={'events': events})) is None


def test_unavailable_uncertain_action_completes_capability_reply_without_acquisition(monkeypatch):
    import asyncio
    import json
    import httpx
    from tests import test_build_source_free_protocol as owner
    from apps.live_control_server.services import build_jev_dispatch
    monkeypatch.setattr(build_jev_dispatch, 'MODEL', 'jev-1.14.0')
    def respond(request):
        body = json.loads(request.content)
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': 'I cannot schedule reminders here.'}], 'limitations': []}
        if 'collaboration' in body['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_uncertain', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{
                'type': 'message', 'id': 'msg_uncertain', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    with owner.pending_writer_completion_case(monkeypatch, source_free_work='other_creation', source_scope='uncertain') as (state, adapter, rules, writer, prepared):
        completed = asyncio.run(writer.run(transport=httpx.MockTransport(respond), api_key='synthetic'))
        assert completed.status == 'completed' and state.completions == 1
        assert 'cannot schedule' in completed.assistant_text
        assert state.retained_reads == 0 and state.materialized == 0
