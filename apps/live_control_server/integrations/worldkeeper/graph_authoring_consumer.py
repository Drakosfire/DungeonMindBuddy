"""Bounded Buddy proposal mapping into the generic WorldKeeper service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from pydantic import ValidationError
from worldkeeper.application import (
    AssertionMetadata,
    CreateFact,
    CreateObject,
    CreateRelationship,
    DurableObjectRef,
    LiteralFactValue,
    PreparedWorldChange,
    ResultOf,
    ScopeBinding,
    TemporalScope,
    TermRefFactValue,
    VerifiedCommittedChange,
    Visibility,
    WorldChangeIntent,
    WorldChangeService,
)

from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringNewObjectPayload,
    GraphObjectAuthoringObjectRefPayload,
    GraphObjectAuthoringProposalPayload,
)
from graph_memory.vnext.domain_runtime import CAMPAIGN_SCOPE_AXIS, GM_LABEL

_LOCAL_TERM = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$", re.ASCII)
_FIXED_PREDICATES = frozenset({"dnd5e:located_in", "dungeonbuddy:allied_with"})
_KINDS = {
    "npc": "dnd5e:npc",
    "location": "dnd5e:location",
    "faction": "dungeonbuddy:faction",
    "organization": "dungeonbuddy:organization",
}
_DEFAULT_SCOPES = frozenset({"recap_graph", "campaign_memory_graph"})


class PlayAuthoringMappingError(ValueError):
    """Buddy proposal cannot be represented in the PLAY-1 subset."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class PlayAuthoringContext:
    space_id: str
    campaign_id: str
    evidence_ref_ids: tuple[str, ...]
    producer: str = "dungeonbuddy:con-ready-play"


def _required(value: str | None, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PlayAuthoringMappingError(code)
    return value


def _metadata(context: PlayAuthoringContext) -> AssertionMetadata:
    return AssertionMetadata(
        scope=(ScopeBinding(CAMPAIGN_SCOPE_AXIS, context.campaign_id),),
        visibility=Visibility(kind="labels_any", labels=(GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        evidence_ref_ids=tuple(context.evidence_ref_ids),
        temporal_scope=TemporalScope(),
    )


def _validate_proposal_common(proposal: GraphObjectAuthoringProposalPayload) -> None:
    if proposal.status != "staged_local":
        raise PlayAuthoringMappingError("unsupported_proposal_status")
    if proposal.visibility.visibility != "gm_private" or (
        proposal.visibility.reveal_state != "unrevealed"
        or proposal.visibility.visibility_note
    ):
        raise PlayAuthoringMappingError("unsupported_visibility")
    if (
        len(proposal.graph_scopes) != len(_DEFAULT_SCOPES)
        or set(proposal.graph_scopes) != _DEFAULT_SCOPES
    ):
        raise PlayAuthoringMappingError("unsupported_graph_scope")


def _object(
    proposal: GraphObjectAuthoringProposalPayload,
    metadata: AssertionMetadata,
) -> CreateObject:
    if proposal.operation not in (None, "create"):
        raise PlayAuthoringMappingError("unsupported_object_operation")
    if proposal.object_ref is None:
        raise PlayAuthoringMappingError("missing_object_ref")
    try:
        value = GraphObjectAuthoringNewObjectPayload.model_validate(proposal.object_ref)
    except ValidationError as exc:
        raise PlayAuthoringMappingError("invalid_object_ref") from exc
    if value.aliases or (value.role or "").strip():
        raise PlayAuthoringMappingError("unsupported_alias_or_role")
    label = _required(value.label, "blank_object_label")
    facts: list[CreateFact] = [
        CreateFact(
            client_op_id=f"{proposal.local_proposal_id}.fact.name",
            predicate="dnd5e:name",
            value=LiteralFactValue.from_json(label),
            metadata=metadata,
        )
    ]
    if value.kind is not None:
        kind = _KINDS.get(value.kind)
        if kind is None:
            raise PlayAuthoringMappingError("unknown_object_kind")
        facts.append(
            CreateFact(
                client_op_id=f"{proposal.local_proposal_id}.fact.classification",
                predicate="dnd5e:classification",
                value=TermRefFactValue(kind),
                metadata=metadata,
            )
        )
    if value.summary is not None and value.summary.strip():
        facts.append(
            CreateFact(
                client_op_id=f"{proposal.local_proposal_id}.fact.summary",
                predicate="dnd5e:summary",
                value=LiteralFactValue.from_json(value.summary),
                metadata=metadata,
            )
        )
    return CreateObject(client_op_id=proposal.local_proposal_id, facts=tuple(facts))


def _endpoint(
    payload: dict[str, object] | None,
    object_ids: set[str],
    *,
    field: str,
) -> DurableObjectRef | ResultOf:
    if payload is None:
        raise PlayAuthoringMappingError(f"missing_{field}")
    try:
        ref = GraphObjectAuthoringObjectRefPayload.model_validate(payload)
    except ValidationError as exc:
        raise PlayAuthoringMappingError(f"invalid_{field}") from exc
    if ref.ref_kind == "existing_graph_node":
        if ref.local_proposal_id is not None:
            raise PlayAuthoringMappingError("ambiguous_existing_endpoint")
        return DurableObjectRef(_required(ref.node_id, "blank_durable_object_id"))
    if ref.ref_kind == "local_proposal":
        if ref.node_id is not None:
            raise PlayAuthoringMappingError("ambiguous_local_endpoint")
        local_id = _required(ref.local_proposal_id, "blank_local_endpoint")
        if local_id not in object_ids:
            raise PlayAuthoringMappingError("unresolved_local_endpoint")
        return ResultOf(local_id)
    raise PlayAuthoringMappingError("unsupported_endpoint_kind")


def _predicate(value: str | None) -> str:
    term = _required(value, "blank_relationship_type")
    if term in _FIXED_PREDICATES:
        return term
    if _LOCAL_TERM.fullmatch(term):
        return f"dungeonbuddy.custom:{term}"
    raise PlayAuthoringMappingError("invalid_relationship_type")


def _relationship(
    proposal: GraphObjectAuthoringProposalPayload,
    object_ids: set[str],
    metadata: AssertionMetadata,
) -> CreateRelationship:
    if proposal.operation not in (None, "create"):
        raise PlayAuthoringMappingError("unsupported_relationship_operation")
    if proposal.direction not in (None, "directed"):
        raise PlayAuthoringMappingError("unsupported_relationship_direction")
    if (proposal.relationship_label or "").strip() or (proposal.summary or "").strip():
        raise PlayAuthoringMappingError("unsupported_relationship_detail")
    return CreateRelationship(
        client_op_id=proposal.local_proposal_id,
        source=_endpoint(
            proposal.source_object_ref, object_ids, field="source_endpoint"
        ),
        predicate=_predicate(proposal.relationship_type),
        target=_endpoint(
            proposal.target_object_ref, object_ids, field="target_endpoint"
        ),
        metadata=metadata,
    )


class WorldKeeperGraphAuthoringConsumer:
    """Translate only the accepted PLAY-1 subset, then delegate lifecycle work."""

    def __init__(self, service: WorldChangeService) -> None:
        self._service = service

    def build_intent(
        self,
        *,
        context: PlayAuthoringContext,
        proposals: Sequence[GraphObjectAuthoringProposalPayload],
    ) -> WorldChangeIntent:
        space_id = _required(context.space_id, "blank_space_id")
        _required(context.campaign_id, "blank_campaign_id")
        producer = _required(context.producer, "blank_producer")
        evidence_ids = context.evidence_ref_ids
        if (
            not evidence_ids
            or any(
                not isinstance(item, str) or not item.strip() for item in evidence_ids
            )
            or len(evidence_ids) != len(set(evidence_ids))
        ):
            raise PlayAuthoringMappingError("invalid_evidence_ref_ids")
        if not proposals:
            raise PlayAuthoringMappingError("empty_proposals")
        proposal_ids = [
            _required(item.local_proposal_id, "blank_local_proposal_id")
            for item in proposals
        ]
        if len(proposal_ids) != len(set(proposal_ids)):
            raise PlayAuthoringMappingError("duplicate_local_proposal_id")
        object_ids = {
            item.local_proposal_id
            for item in proposals
            if item.proposal_kind == "object"
        }
        metadata = _metadata(context)
        operations: list[CreateObject | CreateRelationship] = []
        for proposal in proposals:
            _validate_proposal_common(proposal)
            if proposal.proposal_kind == "object":
                operations.append(_object(proposal, metadata))
            elif proposal.proposal_kind == "relationship":
                operations.append(_relationship(proposal, object_ids, metadata))
            else:
                raise PlayAuthoringMappingError("unsupported_proposal_kind")
        all_ids = [
            item.client_op_id
            for operation in operations
            for item in (
                (operation, *operation.facts)
                if isinstance(operation, CreateObject)
                else (operation,)
            )
        ]
        if len(all_ids) != len(set(all_ids)):
            raise PlayAuthoringMappingError("duplicate_client_op_id")
        return WorldChangeIntent(
            space_id=space_id, producer=producer, operations=tuple(operations)
        )

    def prepare(
        self,
        *,
        context: PlayAuthoringContext,
        proposals: Sequence[GraphObjectAuthoringProposalPayload],
    ) -> PreparedWorldChange:
        return self._service.prepare_change(
            self.build_intent(context=context, proposals=proposals)
        )

    def commit(
        self,
        prepared: PreparedWorldChange,
        *,
        confirmed_by: str,
    ) -> VerifiedCommittedChange:
        return self._service.commit_prepared_change(prepared, confirmed_by)
