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
