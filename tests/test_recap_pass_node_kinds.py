"""Recap role bounds at the actual pass-spec provider schema boundary."""
from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator, ValidationError

from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format_for_spec,
)
from src.graph_memory.extraction.extraction_profile import get_extraction_profile
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE


RECAP_NODE_PASSES = [
    spec
    for profile in (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
    )
    for spec in profile.node_passes
]


ROLES = {
    "actor_pass": ("character", "creature"),
    "location_pass": ("location",),
    "collective_pass": ("faction", "organization", "group"),
    "object_pass": ("item",),
    "thread_pass": (
        "event", "clue", "thread", "mystery", "warning", "promise", "debt",
        "rumor", "unknown_important",
    ),
}


def _payload(spec, kind):
    payload = {"observation_nodes": [{
        "node_id": "source:subject", "label": "Source subject", "node_type": kind,
        "description": "Explicit source description", "importance": "medium",
        "evidence_refs": [],
    }]}
    if spec.include_dispositions:
        payload.update(ignored_items=[], deferred_items=[])
    return payload


@pytest.mark.parametrize("spec", RECAP_NODE_PASSES, ids=lambda s: s.pass_id)
def test_provider_schema_accepts_owned_kinds_and_rejects_foreign_roles(spec):
    # This is the formatter used by BoundedRecapExecutor for actual pass_spec requests.
    schema = category_pass_text_format_for_spec(spec)["format"]["schema"]
    validator = Draft202012Validator(schema)
    for kind in ROLES[spec.pass_id]:
        validator.validate(_payload(spec, kind))
    for kind in {kind for kinds in ROLES.values() for kind in kinds} - set(ROLES[spec.pass_id]):
        with pytest.raises(ValidationError):
            validator.validate(_payload(spec, kind))
    for kind in ("quest", "combat_encounter", "invented_kind"):
        with pytest.raises(ValidationError):
            validator.validate(_payload(spec, kind))


def test_thread_dispositions_keep_their_existing_non_observation_kind_contract():
    spec = next(s for s in RECAP_EXTRACTION_PROFILE.node_passes if s.pass_id == "thread_pass")
    payload = _payload(spec, "warning")
    payload["deferred_items"] = [{
        "item_id": "deferred:actor", "label": "Ambiguous actor",
        "reason": "Identity unresolved", "node_type": "character",
        "evidence_refs": [], "suggested_next_step": None,
    }]
    Draft202012Validator(category_pass_text_format_for_spec(spec)["format"]["schema"]).validate(payload)
