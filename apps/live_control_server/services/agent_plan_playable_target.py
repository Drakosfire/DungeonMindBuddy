"""Identity-only validation for a target in an exact committed Plan revision."""

from __future__ import annotations

from application_state.agent_conversation.types import (
    PlanPlayableTargetReceiptV1,
    SubmittedPlanPlayableTargetV1,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_play_run_reference_elements,
    derive_play_run_reference_elements_v2,
    detect_playable_grammar_version,
)


class AgentPlanPlayableTargetError(ValueError):
    """The selected identity is not uniquely admissible in the pinned Plan."""


def resolve_agent_plan_playable_target(
    target: SubmittedPlanPlayableTargetV1 | None,
    committed_markdown: str,
) -> PlanPlayableTargetReceiptV1 | None:
    """Validate one target against the existing pure v1/v2 marker scanners.

    This helper consumes only the exact Markdown already resolved for Plan Ask.
    It does not resolve a Run, create a manifest, or invoke Run admission.
    """
    if target is None:
        return None

    grammar_version = detect_playable_grammar_version(committed_markdown)
    try:
        if grammar_version == 1:
            membership = [
                (element.kind, element.element_id)
                for element in derive_play_run_reference_elements(committed_markdown)
            ]
        else:
            derived = derive_play_run_reference_elements_v2(committed_markdown)
            membership = [
                *(("beat", beat.beat_id) for beat in derived.beats),
                *(("scene", scene.scene_id) for scene in derived.scenes),
                *(("choice", choice.choice_id) for choice in derived.choices),
                *(("option", option.option_id) for option in derived.options),
            ]
    except PlayRunReferenceManifestError as exc:
        raise AgentPlanPlayableTargetError(
            f"The committed Plan Playable markers are not canonical: {exc}"
        ) from exc

    matches = [identity for identity in membership if identity == (target.kind, target.id)]
    if len(matches) != 1:
        raise AgentPlanPlayableTargetError(
            "The selected Playable target is absent or not unique in the committed Plan."
        )

    return PlanPlayableTargetReceiptV1(
        schema="dmb_plan_playable_target_receipt_v1",
        kind=target.kind,
        id=target.id,
        marker_grammar_version=f"v{grammar_version}",
    )
