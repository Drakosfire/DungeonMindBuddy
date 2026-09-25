"""DungeonBuddy-owned construction of the generic DungeonMind vNext read runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dungeonmind.application.vnext import (
    KnowledgeProvenanceSnapshot,
    KnowledgeReadContext,
    ParsedAssertion,
    ParsedKnowledgeRevision,
)
from dungeonmind.application.vnext.ports import KnowledgeSourceReader
from dungeonmind.contracts.vnext import (
    DomainContractDescriptor,
    FocusRef,
    KnowledgeStanding,
    ProjectionRequest,
    ScopeBinding,
    ScopeSelector,
    SemanticProfileDescriptorV2,
)

DUNGEONBUDDY_DOMAIN_ID = "dungeonbuddy.world"
DUNGEONBUDDY_DOMAIN_REVISION = "2"
DUNGEONBUDDY_POLICY_ID = "dungeonbuddy.admission:world_v1"
DUNGEONBUDDY_PROFILE_ID = "dungeonbuddy.dnd5e"
DUNGEONBUDDY_PROFILE_REVISION = "1"
DUNGEONBUDDY_DOMAIN_DIGEST = (
    "d12f3a517a37d29a2ba52455d9ae1691bc5e4ff3fd6853b701a9e28e46ec65cd"
)
DUNGEONBUDDY_PROFILE_DIGEST = (
    "51ea47ff45bc86ea158939c34a5769e7ee56de3911278d473570e3795edb7e14"
)

CAMPAIGN_SCOPE_AXIS = "dungeonbuddy.scope:campaign"
CAMPAIGN_FOCUS_KIND = "dungeonbuddy.focus:campaign"
SESSION_FOCUS_KIND = "dungeonbuddy.focus:session"
PLAYER_LABEL = "dungeonbuddy.visibility:player"
GM_LABEL = "dungeonbuddy.visibility:gm"

_PLAYER_STANDING = (KnowledgeStanding.ESTABLISHED.value,)
_GM_STANDING = (
    KnowledgeStanding.ESTABLISHED.value,
    KnowledgeStanding.PROVISIONAL.value,
)
_ALLOWED_GM_STANDING = frozenset(_GM_STANDING)


@dataclass(frozen=True, slots=True)
class DungeonBuddyVNextProjectionInput:
    """The complete Buddy-owned input surface for a generic vNext read request."""

    world_id: str
    scope_mode: Literal["campaign", "world"]
    role: Literal["gm", "player"]
    campaign_id: str | None = None
    session_id: str | None = None
    standing_selector: tuple[str, ...] | None = None
    revision_id: str | None = None


def _require_nonblank(value: str | None, field_name: str) -> str:
    if value is None or not value.strip():
        raise ValueError(f"{field_name} must be nonblank")
    return value


def _standing_for(projection_input: DungeonBuddyVNextProjectionInput) -> list[str]:
    requested = projection_input.standing_selector
    if requested is None:
        return list(_PLAYER_STANDING if projection_input.role == "player" else _GM_STANDING)
    if not requested or len(requested) != len(set(requested)):
        raise ValueError("standing_selector must be nonempty and unique")
    requested_set = set(requested)
    if projection_input.role == "player" and requested_set != set(_PLAYER_STANDING):
        raise ValueError("player standing_selector must be exactly established")
    if projection_input.role == "gm" and not requested_set <= _ALLOWED_GM_STANDING:
        raise ValueError("gm standing_selector may contain established and provisional only")
    return list(requested)


def build_dungeonbuddy_projection_request(
    projection_input: DungeonBuddyVNextProjectionInput,
) -> ProjectionRequest:
    """Map exact Buddy semantics into one generic DungeonMind request."""
    world_id = _require_nonblank(projection_input.world_id, "world_id")
    if projection_input.role not in {"gm", "player"}:
        raise ValueError(f"unknown DungeonBuddy role: {projection_input.role!r}")
    if projection_input.scope_mode not in {"campaign", "world"}:
        raise ValueError(
            f"unknown DungeonBuddy scope mode: {projection_input.scope_mode!r}"
        )
    if projection_input.revision_id is not None:
        _require_nonblank(projection_input.revision_id, "revision_id")

    campaign_id = projection_input.campaign_id
    if projection_input.scope_mode == "campaign":
        campaign_id = _require_nonblank(campaign_id, "campaign_id")
        scope = ScopeSelector(
            include_unscoped=True,
            bindings=[ScopeBinding(axis=CAMPAIGN_SCOPE_AXIS, value=campaign_id)],
        )
    else:
        if campaign_id is not None:
            campaign_id = _require_nonblank(campaign_id, "campaign_id")
        scope = ScopeSelector(
            include_unscoped=True,
            wildcard_axes=[CAMPAIGN_SCOPE_AXIS],
        )

    focus: list[FocusRef] = []
    if projection_input.session_id is not None:
        session_id = _require_nonblank(projection_input.session_id, "session_id")
        campaign_id = _require_nonblank(campaign_id, "campaign_id")
        focus = [
            FocusRef(kind=CAMPAIGN_FOCUS_KIND, id=campaign_id),
            FocusRef(kind=SESSION_FOCUS_KIND, id=session_id),
        ]

    audience_labels = (
        [PLAYER_LABEL]
        if projection_input.role == "player"
        else [GM_LABEL, PLAYER_LABEL]
    )
    return ProjectionRequest(
        space_id=world_id,
        revision_id=projection_input.revision_id,
        scope_selector=scope,
        audience_labels=audience_labels,
        standing_selector=_standing_for(projection_input),
        focus=focus,
        domain_context=[],
    )


def dungeonbuddy_world_domain_contract() -> DomainContractDescriptor:
    """Construct the immutable Buddy revision-2 domain declaration from code."""
    return DomainContractDescriptor(
        domain_id=DUNGEONBUDDY_DOMAIN_ID,
        domain_revision=DUNGEONBUDDY_DOMAIN_REVISION,
        admission_policy_id=DUNGEONBUDDY_POLICY_ID,
        scope_axes=[CAMPAIGN_SCOPE_AXIS],
        visibility_labels=[GM_LABEL, PLAYER_LABEL],
        claim_modes=[
            "dungeonbuddy.claim:belief",
            "dungeonbuddy.claim:fact",
            "dungeonbuddy.claim:observed_event",
            "dungeonbuddy.claim:plan",
            "dungeonbuddy.claim:rumor",
        ],
        temporal_extension_schemas=["dungeonbuddy.time:fictional_anchor_v1"],
        domain_metadata_schemas=[
            "dungeonbuddy.domain_metadata:world_context_v1"
        ],
        source_annotation_schemas=[
            "dungeonbuddy.source:context_v1",
            "dungeonbuddy.domain_metadata:world_context_v1",
        ],
    )


def dungeonbuddy_dnd5e_semantic_profile() -> SemanticProfileDescriptorV2:
    """Construct the immutable accepted Buddy semantic profile from code."""
    return SemanticProfileDescriptorV2.model_validate(
        {
            "profile_id": DUNGEONBUDDY_PROFILE_ID,
            "profile_revision": DUNGEONBUDDY_PROFILE_REVISION,
            "term_namespaces": ["dnd5e", "dungeonbuddy"],
            "classification_terms": [
                "dnd5e:location",
                "dnd5e:npc",
                "dungeonbuddy:faction",
                "dungeonbuddy:organization",
            ],
            "predicates": [
                {
                    "term": "dnd5e:classification",
                    "allowed_value_kinds": ["term_ref"],
                    "literal_schema": None,
                },
                {
                    "term": "dnd5e:name",
                    "allowed_value_kinds": ["literal"],
                    "literal_schema": {"type": "string"},
                },
                {
                    "term": "dnd5e:summary",
                    "allowed_value_kinds": ["literal"],
                    "literal_schema": {"type": "string"},
                },
                {
                    "term": "dnd5e:located_in",
                    "allowed_value_kinds": ["entity_ref"],
                    "literal_schema": None,
                },
                {
                    "term": "dungeonbuddy:allied_with",
                    "allowed_value_kinds": ["entity_ref"],
                    "literal_schema": None,
                },
                {
                    "term": "dungeonbuddy:source_classification",
                    "allowed_value_kinds": ["term_ref"],
                    "literal_schema": None,
                },
            ],
        }
    )


@dataclass(frozen=True, slots=True)
class DungeonBuddyWorldAdmissionPolicy:
    """The explicit non-widening Buddy hook after generic Kernel gates."""

    policy_id: str = DUNGEONBUDDY_POLICY_ID

    def narrow(
        self,
        *,
        assertion: ParsedAssertion,
        request: ProjectionRequest,
        domain_contract: DomainContractDescriptor,
        semantic_profile: SemanticProfileDescriptorV2,
        provenance: KnowledgeProvenanceSnapshot,
    ) -> bool:
        del assertion, request, domain_contract, semantic_profile, provenance
        return True


def build_dungeonbuddy_read_context(
    *,
    parsed_revision: ParsedKnowledgeRevision,
    projection_input: DungeonBuddyVNextProjectionInput,
    source_reader: KnowledgeSourceReader,
) -> KnowledgeReadContext:
    """Assemble the pinned generic context without selecting production authority."""
    domain_contract = dungeonbuddy_world_domain_contract()
    policy = DungeonBuddyWorldAdmissionPolicy()
    if policy.policy_id != domain_contract.admission_policy_id:
        raise ValueError("DungeonBuddy policy identity does not match DomainContract")
    return KnowledgeReadContext(
        parsed=parsed_revision,
        request=build_dungeonbuddy_projection_request(projection_input),
        domain_contract=domain_contract,
        semantic_profile=dungeonbuddy_dnd5e_semantic_profile(),
        domain_policy=policy,
        source_reader=source_reader,
    )
