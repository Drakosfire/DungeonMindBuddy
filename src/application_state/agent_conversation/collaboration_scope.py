"""Plan action scope derived from admitted execution, never from model intent."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from .collaboration import POLICY as COLLABORATION_POLICY

KEY = "collaboration_action_scope"
POLICY = "admitted_collaboration_actions_v1"


class ActionScope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy: Literal["admitted_collaboration_actions_v1"]
    allowed_step_kinds: list[Literal["discuss", "prepare_insertion"]]

    @model_validator(mode="after")
    def canonical_actions(self):
        if self.allowed_step_kinds not in (
            ["discuss"],
            ["discuss", "prepare_insertion"],
        ):
            raise ValueError("Plan actions must be a canonical admitted subset")
        return self


def derive(execution):
    policy = execution.policy
    if getattr(policy, "collaboration_output_policy", None) != COLLABORATION_POLICY:
        return None
    operations = policy.allowed_surface_operations
    if "answer_from_sources" not in operations:
        raise ValueError("Plan discussion requires its admitted response capability")
    kinds = ["discuss"]
    if "propose_build_insertion" in operations:
        if not policy.action_capability_sha256:
            raise ValueError("Plan insertion requires its admitted editor capability")
        kinds.append("prepare_insertion")
    return ActionScope(policy=POLICY, allowed_step_kinds=kinds).model_dump(mode="json")


def from_packet(packet):
    if KEY not in packet:
        return None
    if packet.get("collaboration_output_policy") != COLLABORATION_POLICY:
        raise ValueError("Plan action scope requires admitted collaboration")
    return ActionScope.model_validate(packet[KEY]).model_dump(mode="json")


def validate_packet(packet, execution, *, required=False):
    actual = from_packet(packet)
    expected = derive(execution)
    if actual is None and not required:
        return  # Historical producer inputs remain readable; no authority is inferred.
    if actual != expected:
        raise ValueError("Plan action scope differs from admitted execution")


def validate_plan(collaboration, scope):
    if scope is None or collaboration is None:
        return
    value = (
        collaboration.model_dump(mode="json")
        if hasattr(collaboration, "model_dump")
        else collaboration
    )
    if value.get("kind") == "plan" and any(
        step["kind"] not in scope["allowed_step_kinds"] for step in value["steps"]
    ):
        raise ValueError("Plan step is outside the admitted action scope")


def instructions(packet):
    scope = from_packet(packet)
    if scope is None:
        return ""
    text = "\ncollaboration_action_scope is the host-derived set of executable plan step kinds. Offer only those kinds; a plan cannot grant capabilities. "
    if "prepare_insertion" not in scope["allowed_step_kinds"]:
        text += (
            "Page placement is unavailable in this request. Do not offer a prepare_insertion step or promise that this conversation can stage writing. "
            "Explain that the author needs to open the page editor and choose a location before requesting placement. "
            "A discuss step or typed clarification can preserve the intended work. Missing placement is an application capability limit, not missing World evidence.\n"
        )
    else:
        text += "prepare_insertion stages a reversible current-page suggestion; Save and publication remain author actions.\n"
    return text
