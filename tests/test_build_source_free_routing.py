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
