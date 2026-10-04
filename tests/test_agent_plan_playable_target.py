from __future__ import annotations

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.types import SubmittedPlanPlayableTargetV1
from apps.live_control_server.services.agent_plan_playable_target import (
    AgentPlanPlayableTargetError,
    resolve_agent_plan_playable_target,
)


V1_PLAN = """# Plan

<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->
## Arrival
<!-- dmb-playable-element:v1 kind=choice id=choice:door -->
### Door
<!-- dmb-playable-element:v1 kind=option id=option:knock -->
#### Knock
"""

V2_PLAN = """# Plan

<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=spine -->
## Arrival
<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->
### Gate
<!-- dmb-playable-element:v2 kind=choice id=choice:enter scene=scene:gate -->
### Enter
<!-- dmb-playable-element:v2 kind=option id=option:knock -->
- Knock
"""


def target(kind: str, element_id: str) -> SubmittedPlanPlayableTargetV1:
    return SubmittedPlanPlayableTargetV1(
        schema="dmb_plan_playable_target_v1",
        kind=kind,
        id=element_id,
    )


@pytest.mark.parametrize(
    ("markdown", "kind", "element_id", "grammar"),
    [
        (V1_PLAN, "choice", "choice:door", "v1"),
        (V2_PLAN, "option", "option:knock", "v2"),
    ],
)
def test_resolves_target_kind_id_and_grammar_from_pinned_markdown(
    markdown: str, kind: str, element_id: str, grammar: str
) -> None:
    resolved = resolve_agent_plan_playable_target(target(kind, element_id), markdown)

    assert resolved is not None
    assert resolved.kind == kind
    assert resolved.id == element_id
    assert resolved.marker_grammar_version == grammar


def test_no_target_does_not_scan_or_change_the_ordinary_ask_path() -> None:
    assert resolve_agent_plan_playable_target(None, "unmarked Plan prose") is None


@pytest.mark.parametrize(
    ("markdown", "kind", "element_id"),
    [
        (V1_PLAN, "scene", "scene:missing"),
        (V1_PLAN, "scene", "scene:door"),
        (
            V1_PLAN
            + "\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Duplicate\n",
            "scene",
            "scene:arrival",
        ),
        (
            V1_PLAN.replace("v1 kind=choice", "v9 kind=choice"),
            "choice",
            "choice:door",
        ),
    ],
)
def test_rejects_missing_wrong_kind_duplicate_or_malformed_targets(
    markdown: str, kind: str, element_id: str
) -> None:
    with pytest.raises(AgentPlanPlayableTargetError):
        resolve_agent_plan_playable_target(target(kind, element_id), markdown)


def test_target_envelope_rejects_unknown_version_fields_and_kind_id_mismatch() -> None:
    with pytest.raises(ValidationError):
        SubmittedPlanPlayableTargetV1.model_validate(
            {"schema": "dmb_plan_playable_target_v9", "kind": "scene", "id": "scene:a"}
        )
    with pytest.raises(ValidationError):
        SubmittedPlanPlayableTargetV1.model_validate(
            {
                "schema": "dmb_plan_playable_target_v1",
                "kind": "scene",
                "id": "scene:a",
                "marker_grammar_version": "v1",
            }
        )
    with pytest.raises(ValidationError, match="prefix must match"):
        SubmittedPlanPlayableTargetV1(
            schema="dmb_plan_playable_target_v1", kind="scene", id="choice:a"
        )
