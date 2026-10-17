"""Strict wire contract for the surface-neutral Agent turn endpoint."""

from __future__ import annotations

from application_state.agent_conversation.identifier_limits import (
    GRAPH_EVIDENCE_REF_ID_MAX_CHARS,
    GRAPH_CLAIM_ID_MAX_CHARS,
)

import re
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from application_state.agent_conversation.context_trace import TurnContextTraceV1
from graph_memory.ingestion.selection_context import AgentKnowledgeSelection
from .build_document_proposal import BuildWriteCapability

from application_state.agent_conversation.types import (
    BuildGraphCompletionV1,
    BuildGraphContextReceiptV1,
    PlanWorldGraphCompletionV1,
    PlanWorldGraphCompletionV2,
    PlanWorldGraphContextReceiptV1,
    PlanContextPolicyV1,
    SubmittedPlanPlayableTargetV1,
    TurnProvenance,
    CommandResolutionRecordV1,
)


class AgentTurnSurface(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface_id: Literal["index", "plan", "play", "build", "ingest", "combat"]
    instance_id: str = Field(min_length=1, max_length=128)

    @field_validator("instance_id")
    @classmethod
    def normalize_instance_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("instance_id must be non-blank")
        return cleaned


class AgentTurnWorldOwner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["world"]
    world_id: str = Field(min_length=1, max_length=128)

    @field_validator("world_id")
    @classmethod
    def normalize_world_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("world_id must be non-blank")
        return cleaned


class AgentTurnCampaignOwner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["campaign"]
    campaign_id: str = Field(min_length=1, max_length=128)

    @field_validator("campaign_id")
    @classmethod
    def normalize_campaign_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("campaign_id must be non-blank")
        return cleaned


AgentTurnOwner = Annotated[
    AgentTurnWorldOwner | AgentTurnCampaignOwner,
    Field(discriminator="kind"),
]


class AgentTurnPrimaryWork(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["plan", "build", "run", "combat"]
    object_id: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(strict=True, ge=1)
    expected_revision_n: int | None = Field(default=None, strict=True, ge=1)
    expected_content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("object_id")
    @classmethod
    def normalize_object_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("object_id must be non-blank")
        return cleaned

    @model_validator(mode="after")
    def validate_plan_content_pin(self) -> AgentTurnPrimaryWork:
        if self.kind == "build":
            if self.expected_revision_n is not None or self.expected_content_sha256 is None:
                raise ValueError("Build work requires a saved digest and forbids Plan revision_n")
            return self

        has_revision_n = self.expected_revision_n is not None
        has_content_sha256 = self.expected_content_sha256 is not None
        if has_revision_n != has_content_sha256:
            raise ValueError(
                "committed Plan revision number and digest must be pinned together"
            )
        if self.kind != "plan" and (has_revision_n or has_content_sha256):
            raise ValueError("committed Plan pins are only valid for Plan work")
        return self


class AgentTurnGraphNone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["none"]


class AgentTurnGraphFocus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["none", "session"]
    session_id: str | None = Field(max_length=128)
    campaign_id: str | None = Field(max_length=128)

    @model_validator(mode="after")
    def validate_focus(self) -> AgentTurnGraphFocus:
        if self.kind == "none" and (
            self.session_id is not None or self.campaign_id is not None
        ):
            raise ValueError(
                "none graph focus cannot carry session or campaign identity"
            )
        if self.kind == "session" and not self.session_id:
            raise ValueError("session focus requires an exact session_id")
        if (
            self.kind == "session"
            and self.session_id is not None
            and not self.session_id.strip()
        ):
            raise ValueError("session focus requires a non-blank session_id")
        if self.campaign_id is not None and not self.campaign_id.strip():
            raise ValueError("focus campaign_id must be null or non-blank")
        return self


class AgentTurnGraphWorld(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["world"]
    world_id: str = Field(min_length=1, max_length=128)
    campaign_id: str | None
    revision_pin: str | None = Field(max_length=256)
    focus: AgentTurnGraphFocus

    @field_validator("world_id")
    @classmethod
    def normalize_world_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("world_id must be non-blank")
        return cleaned

    @field_validator("campaign_id")
    @classmethod
    def normalize_campaign_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("campaign_id must be null or non-blank")
        return cleaned


class AgentTurnGraphCampaign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["campaign"]
    campaign_id: str = Field(min_length=1, max_length=128)
    revision_pin: str | None = Field(max_length=256)
    focus: AgentTurnGraphFocus

    @field_validator("campaign_id")
    @classmethod
    def normalize_campaign_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("campaign_id must be non-blank")
        return cleaned


AgentTurnGraphRequest = Annotated[
    AgentTurnGraphNone | AgentTurnGraphWorld | AgentTurnGraphCampaign,
    Field(discriminator="mode"),
]


class AgentTurnGraphSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(min_length=1, max_length=256)

    @field_validator("node_id")
    @classmethod
    def normalize_node_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("node_id must be non-blank")
        return cleaned


class AgentTurnRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_turn_request_v1"] = Field(alias="schema")
    client_thread_id: str = Field(min_length=1, max_length=128)
    turn_id: str = Field(min_length=1, max_length=128)
    surface: AgentTurnSurface
    owner_scope: AgentTurnOwner | None
    primary_work: AgentTurnPrimaryWork | None
    playable_target: SubmittedPlanPlayableTargetV1 | None = None
    client_work_state: Literal["none", "saved_clean", "saved_dirty", "new_unsaved"]
    graph_request: AgentTurnGraphRequest
    graph_selection: AgentTurnGraphSelection | None
    selected_knowledge: AgentKnowledgeSelection | None = None
    build_write_capability: BuildWriteCapability | None = None
    plan_context_policy: PlanContextPolicyV1 | None = None
    message: str = Field(min_length=1, max_length=8000)

    @field_validator("client_thread_id", "turn_id", mode="before")
    @classmethod
    def require_identity_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("identity must be a non-blank string")
        return value.strip()

    @field_validator("message")
    @classmethod
    def reject_blank_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must be non-blank")
        return value

    @model_validator(mode="after")
    def reject_contradictory_unsaved_work(self) -> AgentTurnRequest:
        capability = self.build_write_capability
        if capability is not None:
            basis = capability.basis
            work = self.primary_work
            if (self.surface.surface_id != "build" or self.owner_scope is None
                    or self.owner_scope.kind != "world" or basis.world_id != self.owner_scope.world_id
                    or work is None or work.kind != "build" or work.object_id != basis.document_id
                    or work.expected_revision != basis.registry_revision
                    or work.expected_content_sha256 != basis.content_sha256
                    or self.graph_request.mode != "world"):
                raise ValueError("Build writing requires the exact saved Build and requested World Graph")
        if self.selected_knowledge is not None and (
            self.surface.surface_id != "ingest"
            or self.owner_scope is None or self.owner_scope.kind != "world"
            or self.selected_knowledge.context_request.expected_world_id != self.owner_scope.world_id
            or self.primary_work is not None or self.plan_context_policy is not None
        ):
            raise ValueError("Knowledge selection requires the matching World Ingest surface")
        if (
            self.client_work_state in {"saved_clean", "saved_dirty"}
            and self.primary_work is None
        ):
            raise ValueError("saved work state requires a primary_work locator")
        if self.primary_work is not None and self.client_work_state not in {
            "saved_clean",
            "saved_dirty",
        }:
            raise ValueError("primary_work requires saved_clean or saved_dirty state")
        if self.primary_work is not None and (
            (self.primary_work.kind == "build") != (self.surface.surface_id == "build")
        ):
            raise ValueError("Build source work requires the Build surface")
        if self.playable_target is not None and (
            self.surface.surface_id != "plan"
            or self.primary_work is None
            or self.primary_work.kind != "plan"
            or self.client_work_state not in {"saved_clean", "saved_dirty"}
            or self.graph_request.mode != "none"
            or self.graph_selection is not None
        ):
            raise ValueError(
                "Playable target requires a graphless saved Plan turn"
            )
        if self.plan_context_policy is not None and (
            self.plan_context_policy.policy != "auto_plan_world"
            or self.surface.surface_id != "plan"
            or self.owner_scope is None
            or self.owner_scope.kind != "world"
            or self.primary_work is None
            or self.primary_work.kind != "plan"
            or self.client_work_state not in {"saved_clean", "saved_dirty"}
            or self.primary_work.expected_revision_n is None
            or self.primary_work.expected_content_sha256 is None
            or self.graph_request.mode != "none"
            or self.graph_selection is not None
        ):
            raise ValueError(
                "auto_plan_world requires a saved, exactly pinned World Plan turn "
                "with generic Graph request disabled"
            )
        if (
            self.surface.surface_id == "plan"
            and self.primary_work is not None
            and self.primary_work.kind == "plan"
        ):
            if (
                self.primary_work.expected_revision_n is None
                or self.primary_work.expected_content_sha256 is None
            ):
                raise ValueError(
                    "Plan Agent turns require the exact committed content pin"
                )
            if self.graph_request.mode != "none":
                raise ValueError("Plan content turns require graph_request.mode=none")
        if self.surface.surface_id == "play" and self.primary_work is not None:
            if (
                self.primary_work.kind != "run"
                or self.owner_scope is None
                or self.owner_scope.kind != "world"
                or self.graph_selection is not None
            ):
                raise ValueError("Play Run turns require a World owner and no Graph selection")
            if self.graph_request.mode == "world" and (
                self.graph_request.world_id != self.owner_scope.world_id
                or self.graph_request.campaign_id is not None
                or self.graph_request.focus.kind != "none"
                or self.graph_request.revision_pin is not None
            ):
                raise ValueError("Play Run Graph requires the current owner World without narrative focus")
            if self.graph_request.mode not in {"none", "world"}:
                raise ValueError("Play Run Graph requires World scope")
        if (
            self.surface.surface_id == "play"
            and self.graph_request.mode != "none"
            and self.primary_work is None
        ):
            raise ValueError("Play Graph requires an exact saved Run")
        if self.primary_work is not None and self.primary_work.kind == "run" and self.surface.surface_id != "play":
            raise ValueError("Run work requires the Play surface")
        if self.graph_request.mode == "none":
            if self.graph_selection is not None:
                raise ValueError("graph selection requires an explicit graph request")
        return self


class AgentTurnSurfaceResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface_id: str
    instance_id: str
    status: Literal["resolved", "rejected", "unavailable"]


class AgentTurnOwnerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["absent", "resolved", "rejected", "unavailable"]
    kind: Literal["world", "campaign"] | None
    owner_id: str | None
    name: str | None


class AgentTurnContentBasis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    world_id: str = Field(min_length=1, max_length=128)
    document_id: str = Field(min_length=1, max_length=128)
    object_revision: int = Field(strict=True, ge=1)
    work_revision_id: str = Field(min_length=1, max_length=128)
    revision_n: int = Field(strict=True, ge=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    committed_status: Literal["committed"]
    has_divergent_working_copy: bool


class AgentTurnWorkResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "absent",
        "resolved",
        "changed_since_expected",
        "foreign",
        "removed",
        "unavailable",
    ]
    kind: str | None
    object_id: str | None
    revision_used: str | int | None
    expected_revision: int | None
    content_basis: AgentTurnContentBasis | None = None


class AgentTurnGraphResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "not_requested", "ready", "empty", "unavailable", "rejected", "replayed"
    ]
    world_id: str | None = None
    campaign_id: str | None = None
    scope_mode: Literal["world", "campaign"] | None = None
    revision_id: str | None = None
    focus: dict[str, object] | None = None
    selection_node_id: str | None = None
    selection_found: bool | None = None
    head_revision_id: str | None = None
    is_head: bool | None = None


class AgentTurnConversationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_thread_id: str
    turn_id: str
    pointer_status: Literal["absent", "accepted", "recovered", "rejected", "reused"]
    pointer_id: str | None
    conversation_id: UUID | None = None


class AgentTurnAnswerResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "error"]
    text: str | None
    code: str | None
    message: str | None
    graph_grounded: bool
    trace: dict[str, object]


class AgentTurnResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_turn_response_v1"] = Field(
        default="dmb_agent_turn_response_v1", alias="schema"
    )
    client_thread_id: str
    turn_id: str
    surface: AgentTurnSurfaceResult
    owner_scope: AgentTurnOwnerResult
    primary_work: AgentTurnWorkResult
    client_work_state_reported: Literal[
        "none", "saved_clean", "saved_dirty", "new_unsaved"
    ]
    graph: AgentTurnGraphResult
    conversation: AgentTurnConversationResult
    answer: AgentTurnAnswerResult


class AgentPlanWorldGraphExecutionProjectionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_plan_world_graph_execution_projection_v1"] = Field(
        default="dmb_agent_plan_world_graph_execution_projection_v1", alias="schema"
    )
    claimability: Literal[
        "safe_to_reclaim_without_dispatch",
        "explicit_new_attempt_required",
        "blocked_unknown_or_sent",
        "completed",
    ]
    authorization_state: Literal[
        "none", "authorized", "sdk_entered", "response_received",
        "known_not_sent", "outcome_unknown",
    ]
    automatic_redispatch: Literal[False] = False


class AgentSourceOpenFocusV1(BaseModel):
    """The frozen ordinary World Plan query has no session focus."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["none"] = "none"
    session_id: None = None
    campaign_id: None = None


class AgentSourceOpenAuthorityV1(BaseModel):
    """Exact historical authority for a user initiated source open."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1, max_length=GRAPH_CLAIM_ID_MAX_CHARS)
    source_artifact_id: str = Field(min_length=1, max_length=256)
    source_revision_id: str = Field(min_length=1, max_length=256)
    managed_world_id: str = Field(min_length=1, max_length=128)
    native_world_id: str = Field(min_length=1, max_length=128)
    binding_version: int = Field(strict=True, ge=1)
    scope_mode: Literal["world"] = "world"
    campaign_id: None = None
    focus: AgentSourceOpenFocusV1 = Field(default_factory=AgentSourceOpenFocusV1)
    admissibility: Literal["gm"] = "gm"
    graph_revision: str = Field(min_length=1, max_length=256)


class AgentEvidenceAnchorOpenTargetV1(AgentSourceOpenAuthorityV1):
    schema_: Literal["dmb_agent_evidence_anchor_open_target_v1"] = Field(
        default="dmb_agent_evidence_anchor_open_target_v1", alias="schema"
    )
    kind: Literal["evidence_anchor"] = "evidence_anchor"
    anchor_id: str = Field(min_length=1, max_length=256)
    evidence_ref_id: str = Field(min_length=1, max_length=GRAPH_EVIDENCE_REF_ID_MAX_CHARS)
    source_read_id: str | None = Field(default=None, min_length=1, max_length=128)
    read_outcome: Literal["enough", "partial", "truncated"] | None = None

    @model_validator(mode="after")
    def validate_read_audit(self) -> AgentEvidenceAnchorOpenTargetV1:
        if (self.source_read_id is None) != (self.read_outcome is None):
            raise ValueError("source-read audit ID and outcome must appear together")
        return self


class AgentRelatedRecapContextOpenTargetV2(AgentSourceOpenAuthorityV1):
    schema_: Literal["dmb_agent_related_recap_context_open_target_v2"] = Field(
        default="dmb_agent_related_recap_context_open_target_v2", alias="schema"
    )
    kind: Literal["related_recap_context"] = "related_recap_context"
    context_anchor_id: str = Field(pattern=r"^dm-context-anchor:v2:.+")
    provenance_evidence_ref_id: str = Field(min_length=1, max_length=GRAPH_EVIDENCE_REF_ID_MAX_CHARS)
    source_campaign_id: str | None = None
    source_uri: str = Field(min_length=1)
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_session_id: str = Field(pattern=r"^session-[1-9][0-9]*$")
    canonical_heading: str = Field(min_length=1)
    legacy_session_heading: str = Field(min_length=1)
    legacy_recap_marker: Literal["**Recap**:"]
    selector_schema: Literal["dm_recap_context_section_selector_v2"] = (
        "dm_recap_context_section_selector_v2"
    )
    selector_policy: Literal["markdown-session-recap-v2"] = "markdown-session-recap-v2"

    @model_validator(mode="after")
    def validate_context_selector(self) -> AgentRelatedRecapContextOpenTargetV2:
        match = re.fullmatch(r"session-([1-9][0-9]*)", self.expected_session_id)
        if (
            match is None
            or self.canonical_heading != f"# Session {match.group(1)} Recap"
            or self.legacy_session_heading != f"## Session {match.group(1)}:"
            or not self.source_uri.startswith("repo://")
            or (self.source_campaign_id is not None and not self.source_campaign_id.strip())
        ):
            raise ValueError("related recap context selector or source is invalid")
        return self


AgentSourceOpenTargetV2 = Annotated[
    AgentEvidenceAnchorOpenTargetV1 | AgentRelatedRecapContextOpenTargetV2,
    Field(discriminator="kind"),
]


class AgentEvidenceAnchorStatusV1(BaseModel):
    """Whether the bounded projection exposed every verified evidence opener."""

    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_evidence_anchor_status_v1"] = Field(
        default="dmb_agent_evidence_anchor_status_v1", alias="schema"
    )
    claim_id: str = Field(min_length=1, max_length=GRAPH_CLAIM_ID_MAX_CHARS)
    status: Literal["available", "no_anchor", "partial", "overflow"]
    target_count: int = Field(strict=True, ge=0, le=64)

    @model_validator(mode="after")
    def validate_target_count(self) -> AgentEvidenceAnchorStatusV1:
        valid = (
            self.target_count > 0 if self.status in {"available", "partial"}
            else self.target_count == 0
        )
        if not valid:
            raise ValueError("evidence anchor status and target count disagree")
        return self


class AgentRelatedRecapContextStatusV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_related_recap_context_status_v2"] = Field(
        default="dmb_agent_related_recap_context_status_v2", alias="schema"
    )
    claim_id: str = Field(min_length=1, max_length=GRAPH_CLAIM_ID_MAX_CHARS)
    status: Literal[
        "available", "multiple_choices", "no_context", "metadata_unavailable",
        "partial", "overflow",
    ]
    choice_count: int = Field(strict=True, ge=0, le=512)

    @model_validator(mode="after")
    def validate_choice_count(self) -> AgentRelatedRecapContextStatusV2:
        valid = (
            self.choice_count == 1 if self.status == "available" else
            self.choice_count > 1 if self.status == "multiple_choices" else
            self.choice_count > 0 if self.status == "partial" else
            self.choice_count >= 0 if self.status == "metadata_unavailable" else
            self.choice_count == 0
        )
        if not valid:
            raise ValueError("recap context status and choice count disagree")
        return self


class AgentPlanWorldGraphContextResponseV2(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_plan_world_graph_context_response_v2"] = Field(
        default="dmb_agent_plan_world_graph_context_response_v2", alias="schema"
    )
    receipt: PlanWorldGraphContextReceiptV1
    completion: PlanWorldGraphCompletionV1 | PlanWorldGraphCompletionV2 | None
    execution: AgentPlanWorldGraphExecutionProjectionV1 | None
    delivery_replay: bool
    source_open_targets: list[AgentSourceOpenTargetV2] = Field(default_factory=list)
    evidence_anchor_statuses: list[AgentEvidenceAnchorStatusV1] = Field(
        default_factory=list
    )
    related_recap_context_statuses: list[AgentRelatedRecapContextStatusV2] = Field(
        default_factory=list
    )


class AgentTurnResponseV2(AgentTurnResponse):
    schema_: Literal["dmb_agent_turn_response_v2"] = Field(
        default="dmb_agent_turn_response_v2", alias="schema"
    )
    plan_context: AgentPlanWorldGraphContextResponseV2


class AgentBuildGraphContextResponseV1(AgentPlanWorldGraphContextResponseV2):
    schema_: Literal["dmb_build_graph_context_response_v1"] = Field(
        default="dmb_build_graph_context_response_v1", alias="schema"
    )
    receipt: BuildGraphContextReceiptV1
    completion: BuildGraphCompletionV1 | None


class AgentBuildGraphTurnResponseV1(AgentTurnResponse):
    knowledge_context: AgentBuildGraphContextResponseV1


class AgentConversationHistoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: UUID
    sequence: int = Field(ge=1)
    lifecycle_status: Literal[
        "accepted", "running", "completed", "failed", "interrupted"
    ]
    user_text: str
    assistant_text: str | None
    provenance: TurnProvenance


class AgentConversationHistoryTurnV2(AgentConversationHistoryTurn):
    plan_context: AgentPlanWorldGraphContextResponseV2


class AgentConversationHistoryTurnV3(AgentConversationHistoryTurn):
    idempotency_key: UUID


class AgentConversationHistoryPlanTurnV3(AgentConversationHistoryTurnV3):
    plan_context: AgentPlanWorldGraphContextResponseV2


class AgentConversationHistoryBuildTurnV2(AgentConversationHistoryTurn):
    knowledge_context: AgentBuildGraphContextResponseV1


class AgentConversationHistoryBuildTurnV3(AgentConversationHistoryTurnV3):
    knowledge_context: AgentBuildGraphContextResponseV1


class AgentConversationHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_conversation_history_v1"] = Field(
        default="dmb_agent_conversation_history_v1", alias="schema"
    )
    world_id: str = Field(min_length=1, max_length=128)
    conversation_state: Literal["active", "absent"]
    conversation_id: UUID | None
    active_conversation_id: UUID | None
    pointer_revision: int = Field(ge=0)
    turns: list[AgentConversationHistoryTurn]
    next_before_sequence: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_conversation_state(self) -> "AgentConversationHistoryResponse":
        if self.conversation_state == "absent":
            if (
                self.conversation_id is not None
                or self.active_conversation_id is not None
                or self.turns
            ):
                raise ValueError("absent conversation state cannot carry a conversation or turns")
        elif (
            self.conversation_id is None
            or self.active_conversation_id != self.conversation_id
        ):
            raise ValueError("active conversation state requires matching active conversation IDs")
        return self


class AgentConversationHistoryResponseV2(AgentConversationHistoryResponse):
    schema_: Literal["dmb_agent_conversation_history_v2"] = Field(
        default="dmb_agent_conversation_history_v2", alias="schema"
    )
    turns: list[AgentConversationHistoryBuildTurnV2 | AgentConversationHistoryTurnV2 | AgentConversationHistoryTurn]


class AgentConversationHistoryResponseV3(AgentConversationHistoryResponse):
    schema_: Literal["dmb_agent_conversation_history_v3"] = Field(
        default="dmb_agent_conversation_history_v3", alias="schema"
    )
    turns: list[AgentConversationHistoryBuildTurnV3 | AgentConversationHistoryPlanTurnV3 | AgentConversationHistoryTurnV3]


class AgentTurnContextTraceResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)
    schema_: Literal["dmb_agent_turn_context_trace_response_v1"] = Field(
        default="dmb_agent_turn_context_trace_response_v1", alias="schema"
    )
    world_id: str
    turn_id: UUID
    attempts: list[TurnContextTraceV1]

    @model_validator(mode="after")
    def validate_trace_binding(self) -> "AgentTurnContextTraceResponseV1":
        if any(trace.world_id != self.world_id or trace.turn_id != self.turn_id for trace in self.attempts):
            raise ValueError("context trace belongs to a different World or turn")
        return self


class AgentNewConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_new_conversation_v1"] = Field(
        default="dmb_agent_new_conversation_v1", alias="schema"
    )
    command_id: UUID
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None


class AgentNewConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_: Literal["dmb_agent_new_conversation_response_v1"] = Field(
        default="dmb_agent_new_conversation_response_v1", alias="schema"
    )
    world_id: str
    conversation_id: UUID
    active_conversation_id: UUID | None
    pointer_revision: int = Field(ge=0)


class AgentNewConversationReceiptV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_: Literal["dmb_agent_new_conversation_receipt_v1"] = Field(default="dmb_agent_new_conversation_receipt_v1", alias="schema")
    conversation_id: UUID
    active_conversation_id: UUID
    pointer_revision: int = Field(ge=1)
    recorded_at: str


class AgentNewConversationStatusV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_: Literal["dmb_agent_new_conversation_status_v1"] = Field(default="dmb_agent_new_conversation_status_v1", alias="schema")
    world_id: str
    command_id: UUID
    command_kind: Literal["new"] = "new"
    expected_pointer_revision: int = Field(ge=0)
    expected_active_conversation_id: UUID | None
    request_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["confirmed", "absent"]
    receipt: AgentNewConversationReceiptV1 | None

    @model_validator(mode="after")
    def validate_receipt_binding(self) -> "AgentNewConversationStatusV1":
        if (self.status == "confirmed") != (self.receipt is not None):
            raise ValueError("status must match receipt presence")
        if self.receipt is not None and (
            self.receipt.active_conversation_id != self.receipt.conversation_id
            or self.receipt.conversation_id == self.expected_active_conversation_id
            or self.receipt.pointer_revision <= self.expected_pointer_revision
        ):
            raise ValueError("receipt must bind a committed fresh conversation")
        return self


class AgentCommandResolutionResponseV1(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_: Literal["dmb_agent_new_conversation_resolution_response_v1"] = Field(default="dmb_agent_new_conversation_resolution_response_v1", alias="schema")
    status: Literal["terminal", "absent"]
    record: CommandResolutionRecordV1 | None

    @model_validator(mode="after")
    def validate_presence(self) -> "AgentCommandResolutionResponseV1":
        if (self.status == "terminal") != (self.record is not None):
            raise ValueError("resolution response must match record presence")
        return self
