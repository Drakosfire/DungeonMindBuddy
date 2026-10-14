"""Publication response profile validation/schema share the approved catalog."""

import pytest
from pydantic import TypeAdapter, ValidationError

from apps.live_control_server.models.extract_promote import (
    WorldbuildingPublicationProfile, WorldbuildingWritePlanResponse,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import (
    PUBLISHABLE_WORLDBUILDING_PROFILES,
)


@pytest.mark.parametrize("profile", sorted(PUBLISHABLE_WORLDBUILDING_PROFILES))
def test_exact_approved_profiles_validate_without_rewriting(profile):
    assert TypeAdapter(WorldbuildingPublicationProfile).validate_python(profile) == profile


@pytest.mark.parametrize("profile", [
    "worldbuilding_gazetteer_v1@2.0", "worldbuilding_plumbing_v0@0.1",
    "worldbuilding_gazetteer_v1", "worldbuilding_gazetteer_v1@1.2 ",
])
def test_other_registered_or_unknown_profiles_reject(profile):
    with pytest.raises(ValidationError):
        TypeAdapter(WorldbuildingPublicationProfile).validate_python(profile)


def test_actual_response_schema_admits_exactly_approved_publication_profiles():
    schema = WorldbuildingWritePlanResponse.model_json_schema(by_alias=True)
    enum = schema["properties"]["extractionProfile"]["enum"]
    assert set(enum) == set(PUBLISHABLE_WORLDBUILDING_PROFILES)
    field = WorldbuildingWritePlanResponse.model_fields["extraction_profile"]
    adapter = TypeAdapter(field.rebuild_annotation())
    for profile in enum:
        assert adapter.validate_python(profile) == profile
    with pytest.raises(ValidationError):
        adapter.validate_python("worldbuilding_plumbing_v0@0.1")
