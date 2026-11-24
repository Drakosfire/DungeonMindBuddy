"""Host-only provenance for a bounded neighborhood read."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NeighborhoodReplayHop(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relationship_id: str = Field(min_length=1, max_length=256)
    from_node_id: str = Field(min_length=1, max_length=256)
    to_node_id: str = Field(min_length=1, max_length=256)


class NeighborhoodReplay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    hops: list[NeighborhoodReplayHop] = Field(max_length=512)
    object_limit_pruned_ids: list[str] = Field(max_length=32)
    object_limit_pruned_count: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def validate_inventory(self):
        identities = [hop.relationship_id for hop in self.hops]
        pruned = self.object_limit_pruned_ids
        if len(identities) != len(set(identities)):
            raise ValueError("Duplicate discovery relationship")
        if len(pruned) != len(set(pruned)) or len(pruned) > self.object_limit_pruned_count:
            raise ValueError("Invalid neighborhood pruning sample")
        return self


class ExcludedReplayCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    handle: str = Field(min_length=1, max_length=256)
    label: str = Field(min_length=1, max_length=256)
    kind: str = Field(min_length=1, max_length=128)


class RetrievalExclusionReplay(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    candidates: list[ExcludedReplayCandidate] = Field(max_length=32)
    total: int = Field(strict=True, ge=0)


class ReplayExclusionStep(RetrievalExclusionReplay):
    sequence: int = Field(strict=True, ge=0)


def replay_exclusion_steps(execution, *, start, stop):
    """Read explicit selected-event metadata inside this trace's attempt."""
    if not isinstance(execution, dict):
        return []
    return [
        ReplayExclusionStep(sequence=event["sequence"], **event["exclusion_replay"])
        for event in execution.get("events", [])
        if event["kind"] in {
            "native_plan_opening_selected_v1", "native_retrieval_selected_v1",
            "native_retrieval_selected_v2", "plan_jev_retrieval_selected_v1",
        }
        and start <= event["sequence"] and (stop is None or event["sequence"] < stop)
        and event.get("exclusion_replay") is not None
    ]


class EffectiveRetrievalSelection(BaseModel):
    """Non-authoritative projection of a durable host selection."""
    model_config = ConfigDict(extra="forbid", frozen=True)
    sequence: int = Field(strict=True, ge=0)
    controller_attempt_id: str = Field(min_length=1, max_length=64)
    operation: str = Field(pattern=r"^(select_candidates|discover_more|finish_retrieval)$")
    selected_count: int = Field(strict=True, ge=0)


def effective_retrieval_selections(execution, *, start, stop):
    """Project actual selection events within one attempt, never model votes."""
    if not isinstance(execution, dict):
        return []
    return [
        EffectiveRetrievalSelection(
            sequence=event["sequence"],
            controller_attempt_id=str(event["controller_attempt_id"]),
            operation=event["operation"],
            selected_count=len(event["selected_handles"]),
        )
        for event in execution.get("events", [])
        if event.get("kind") in {"native_retrieval_selected_v1",
                                 "native_retrieval_selected_v2",
                                 "plan_jev_retrieval_selected_v1"}
        and start <= event["sequence"] and (stop is None or event["sequence"] < stop)
    ]
