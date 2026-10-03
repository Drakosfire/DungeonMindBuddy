"""Strict wire contract for the surface-neutral Agent turn endpoint."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from application_state.agent_conversation.types import TurnProvenance


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
    client_work_state: Literal["none", "saved_clean", "saved_dirty", "new_unsaved"]
    graph_request: AgentTurnGraphRequest
    graph_selection: AgentTurnGraphSelection | None
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
