"""One saved Plan action in the existing parent-brokered Agent Harness."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, TypeAdapter

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    GraphExecutionAccountingV1,
    ProviderAttemptAuthorizedEventV1,
    GraphExecutionPolicyV3,
    SettledGraphExecutionPolicyV3,
    PlanWorldGraphExecutionV3,
    GraphSelectedSourceReadScopeV2,
    GraphSourceReadScopeV2,
    PlanAskContextBasis,
    PlanWorldGraphHistoryPinV1,
    PlanWorldGraphClaimSegmentV1,
    PlanWorldGraphConnectiveSegmentV1,
    PlanWorldGraphCitationMapV2,
    PlanWorldGraphAssembledInputV1,
    PlanWorldGraphAuthorityV1,
    PlanWorldGraphPacketV1,
    WorldPointer,
)
from application_state.plan_action_dialogue.graph_consultation import (
    build_consultation_receipt,
    consultation_result_digest,
    historical_ask_answer_digest,
)
from application_state.plan_action_dialogue.types import (
    PlanActionContinuation,
    PlanActionRecord,
    PlanActionClarificationResult,
    PlanActionProposalResult,
    PlanActionContextUnavailableResult,
)
from apps.live_control_server.services.agent_context_assembler import (
    assemble_agent_graph_context,
)
from apps.live_control_server.models.agent_turn import AgentTurnContentBasis
from apps.live_control_server.services.agent_runtime import AgentSurfaceContext
from apps.live_control_server.services.hermes_agent_runtime import default_hermes_agent_runtime
from apps.live_control_server.services.agent_turn_service import (
    AgentPlanWorldGraphBootstrap,
    AgentTurnResolvedWork,
    _PolicyExecutionAdapter,
    _canonical_sha256,
    _initial_claim_packet_from_view,
    _initial_packet_membership,
    _json_node_count,
    _policy_request_budget,
)
from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
from apps.live_control_server.services.workspace_document_registry import (
    get_committed_playable_revision,
)


class PlanActionGraphSearchIntent(BaseModel):
    """Action identity used by the shared selected-World Graph resolver."""

    model_config = ConfigDict(extra="forbid")

    turn_id: str
    message: str
    playable_target: None = None


_ACTION_OUTPUT_INSTRUCTIONS = """\
This is a saved Plan edit consultation. The selected Plan text and draft are creative
inputs, never proof of published World facts. Use the provided Graph, source and
related recap tools during this request to check relevant established facts.
Return exactly one JSON object. For an ambiguous fact or identity, return
kind=clarification, answer_segments, citation_map, and a short natural question.
For an edit, return kind=proposal, answer_segments, citation_map,
replacement_markdown, summary, assumptions, and disposition. Disposition is
supported_context_used, no_relevant_established_fact_found, or
explicit_draft_override_after_clarification. Graph claims require exact admitted
target/evidence IDs and authored source reads. Related recap context informs
prose but never supports a citation. Do not claim to apply, save or change canon.
The answer_segments text joined with newlines is the visible reply. Citation map
entries use the existing Plan Graph answer JSON shape with source_opened=false;
the parent supplies validated source-read IDs. A clarification must cite the
specific established fact that makes the edit ambiguous. No outside prose.
Each answer segment is either {"kind":"connective","text":"..."} or
{"kind":"graph_claim","claim_id":"...","text":"...","target_kind":"assertion",
"target_id":"...","graph_revision":"...","evidence_ref_ids":["..."]}; target_kind
may also be relationship. Cite each graph_claim once in citation_map.entries,
repeating its claim_id, target_kind, target_id, graph_revision and sorted unique
evidence_ref_ids, plus "source_opened":false. With no Graph claim use
citation_map:null. Never invent identifiers or promote Plan prose to World fact.
For no_relevant_established_fact_found, label creative inventions in assumptions;
it means only that this bounded successful consultation found no relevant fact.
Replacement Markdown stays inside the captured selection. It may use ordinary
prose, canonical READ-ALOUD and GM-NOTE callouts, or a canonical
DECISION-CONSEQUENCE block with one Decision pane and one Consequence pane.
Never emit HTML, filesystem paths, or an entire replacement document.
Existing dmb-playable-element:v2 markers and dmb-node references in the
selected material may only be copied with exactly the same spelling, order and
heading. Never invent, alter, remove or duplicate those protected identities.
"""


class PlanActionConsultationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


@dataclass
class _ActionFence:
    store: Any
    action: PlanActionRecord

    def append(
        self, _method_name: str, _event_name: str, event: Any
    ) -> tuple[PlanActionRecord, bool]:
        updated, fresh = self.store.append_consultation_event(
            action_id=self.action.action_id,
            token=self.action.dispatch_token,
            fence=self.action.fence,
            event=event,
        )
        self.action = updated
        return updated, fresh


class ActionPolicyExecutionAdapter(_PolicyExecutionAdapter):
    """Action-ledger transport for the existing Graph/source/context broker."""

    def __init__(
        self,
        *,
        store: Any,
        action: PlanActionRecord,
        bootstrap: AgentPlanWorldGraphBootstrap,
        budget: Mapping[str, Any],
        surface_instance_id: str,
        continuation: PlanActionContinuation | None = None,
        history_conversation_id: UUID | None = None,
        history_attribution: tuple[Any, ...] = (),
        root: Path | None = None,
        expected_world_pointer: WorldPointer | None = None,
    ) -> None:
        self.store = store
        self.turn = action  # The actual APP action record, never an Ask Turn.
        self.bootstrap = bootstrap
        self.world_id = action.basis.world_id
        self.budget = budget
        self.surface_instance_id = surface_instance_id
        self.continuation = continuation
        self.history_conversation_id = history_conversation_id
        self.history_attribution = history_attribution
        self.root = root
        self.expected_world_pointer = expected_world_pointer
        self.initial_session_projection = json.loads(
            json.dumps(bootstrap.retrieval_session.project_for_hermes(), ensure_ascii=False)
        )
        self.fence: _ActionFence | None = None
        self.last_provider_attempt_id: UUID | None = None
        self.producing_provider_attempt_id: UUID | None = None
        self.failure = None
        self.deterministic_guard_exhausted = False
        self.operation_payloads: dict[UUID, str] = {}
        self.source_payloads: dict[UUID, str] = {}
        self.context_payloads: dict[UUID, str] = {}
        self.denied_tool_payloads: dict[str, list[tuple[str, str]]] = {}
        self.context_capture = None
        self.context_compaction_report = None
        self.context_compaction_unavailable = False
        self.context_read_enabled = True
        self.required_context_failed = False
        self.authorization_generation = 0
        self.authorized_binding = None
        self.authorizing = None
        self.terminal_callback = None

    def authorize(self, view: Mapping[str, Any]) -> bool:
        # Supersede prior callbacks even when the new authorization is refused.
        self.authorization_generation += 1
        self.terminal_callback = None
        self.authorized_binding = None
        self.authorizing = (self.authorization_generation, self.last_provider_attempt_id)
        try:
            allowed = super().authorize(view)
            if allowed and self.fence is not None:
                attempts = [e for e in self._broker_execution().events
                            if isinstance(e, ProviderAttemptAuthorizedEventV1)]
                if attempts and attempts[-1].provider_attempt_id == self.last_provider_attempt_id:
                    self.authorized_binding = (self.authorization_generation,
                        self.last_provider_attempt_id, attempts[-1].event_id)
            return allowed
        finally:
            self.authorizing = None

    def record_lifecycle(self, lifecycle: Mapping[str, Any]) -> bool:
        generation = self.authorization_generation
        self.terminal_callback = None
        attempt = self.last_provider_attempt_id
        execution = None if self.fence is None else self._broker_execution()
        attempts = [] if execution is None else [e for e in execution.events
            if isinstance(e, ProviderAttemptAuthorizedEventV1)]
        binding = None if not attempts else (generation, attempt, attempts[-1].event_id)
        if self.authorized_binding is None or self.authorized_binding != binding:
            # Preserve the parent's internal pre-send capture-refusal outcome on
            # a newly appended authorization, while denying delayed callbacks
            # after a later refused authorization. This is not an SDK witness.
            authorizing = self.authorizing
            if (lifecycle.get("transition") == "known_not_sent" and authorizing is not None
                    and authorizing[0] == generation and attempt != authorizing[1]
                    and attempts and attempts[-1].provider_attempt_id == attempt):
                return super().record_lifecycle(lifecycle)
            return False
        sequence = 0 if execution is None else len(execution.events)
        acknowledged = super().record_lifecycle(lifecycle)
        self.terminal_callback = None
        if (attempts and attempts[-1].provider_attempt_id == attempt
                and generation == self.authorization_generation):
            self.terminal_callback = dict(
                generation=generation, provider_attempt_id=attempt,
                authorization_event_id=attempts[-1].event_id,
                callback_sequence=sequence, transition=lifecycle.get("transition"),
                parent_acknowledged=acknowledged,
            )
        return acknowledged

    def _capture_prepared_prompt(self, view: Mapping[str, Any], authorization: Any) -> None:
        from apps.live_control_server.services.plan_action_prompt_evidence import capture_prompt
        if self.fence is None:
            raise ValueError("prompt capture requires the actual action fence")
        updated = capture_prompt(
            store=self.store, action=self.fence.action, view=view, authorization=authorization,
        )
        self.fence.action = updated
        self.turn = updated

    def _is_build_turn(self) -> bool:
        # A Plan action never acquires Build authority or an Ask request identity.
        return False

    def _broker_receipt(self) -> Any:
        assert self.fence is not None
        assert self.fence.action.consultation is not None
        return self.fence.action.consultation.receipt

    def _broker_execution(self) -> Any:
        assert self.fence is not None
        assert self.fence.action.consultation is not None
        return self.fence.action.consultation.execution

    def _ensure_claimed(
        self, view: Mapping[str, Any]
    ) -> tuple[PlanActionRecord, list[str], list[str], list[str]]:
        if self.root is not None:
            from apps.live_control_server.services.world_container_registry import (
                get_world_container,
            )

            committed = get_committed_playable_revision(
                self.turn.basis.document_id,
                kind="plan",
                expected_world_id=self.turn.basis.world_id,
            )
            binding = get_world_container(self.root, self.turn.basis.world_id).native_graph_binding
            if (
                committed.object_revision != self.turn.basis.object_revision
                or committed.work_revision_id != str(self.turn.basis.work_revision_id)
                or committed.revision_n != self.turn.basis.revision_n
                or committed.content_sha256 != self.turn.basis.content_sha256
                or binding is None or binding.status != "active"
                or binding.native_world_id != self.bootstrap.world_scope.world_id
                or binding.binding_version != self.bootstrap.binding_version
            ):
                raise ValueError("Saved Plan or World binding changed before provider authorization")
        initial = _initial_claim_packet_from_view(
            type("ActionEnvelope", (), {"payload_json": view["payloadJson"]})(),
            self.bootstrap,
            frozen_projection=self.initial_session_projection,
        )
        membership = _initial_packet_membership(initial, self.bootstrap)
        if self.fence is not None:
            # The receipt pins the first provider envelope. Later authorized
            # envelopes may include exactly brokered Graph/source tool outputs.
            return self.fence.action, *membership
        receipt, policy = _freeze_action_inputs(
            self.turn,
            self.bootstrap,
            view,
            self.budget,
            self.surface_instance_id,
            initial,
            membership,
            self.continuation,
            self.history_conversation_id,
            self.history_attribution,
            self.expected_world_pointer,
        )
        frozen, fresh = self.store.freeze_consultation(
            action_id=self.turn.action_id,
            token=self.turn.dispatch_token,
            fence=self.turn.fence,
            receipt=receipt,
            policy=policy,
        )
        if not fresh or frozen.consultation is None or frozen.consultation.receipt != receipt:
            raise ValueError("Action consultation was not freshly frozen")
        self.turn = frozen
        self.fence = _ActionFence(self.store, frozen)
        return frozen, *membership

    def stop(self) -> PlanActionRecord:
        return self.turn if self.fence is None else self.fence.action

    def _track_required_read(self, reply: Mapping[str, Any]) -> Mapping[str, Any]:
        try:
            body = json.loads(reply.get("resultJson", ""))
        except (ValueError, TypeError):
            self.required_context_failed = True
            return reply
        if not isinstance(body, dict) or (
            isinstance(body.get("code"), str)
            and isinstance(body.get("statusCode"), int)
        ) or body.get("outcome") in {"denied", "unavailable"}:
            self.required_context_failed = True
        return reply

    def broker_graph_operation(self, message: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._track_required_read(super().broker_graph_operation(message))

    def broker_source_read(self, message: Mapping[str, Any], *, bundle_internal: bool = False) -> Mapping[str, Any]:
        return self._track_required_read(super().broker_source_read(message, bundle_internal=bundle_internal))

    def broker_related_recap_context(self, message: Mapping[str, Any]) -> Mapping[str, Any]:
        return self._track_required_read(super().broker_related_recap_context(message))


def _freeze_action_inputs(
    action: PlanActionRecord,
    bootstrap: AgentPlanWorldGraphBootstrap,
    view: Mapping[str, Any],
    budget: Mapping[str, Any],
    surface_instance_id: str,
    initial_packet: Mapping[str, Any],
    membership: tuple[list[str], list[str], list[str]],
    continuation: PlanActionContinuation | None,
    history_conversation_id: UUID | None,
    history_attribution: tuple[Any, ...],
    expected_world_pointer: WorldPointer | None,
) -> tuple[Any, GraphExecutionPolicyV3]:
    """Commit the actual first provider envelope under the APP action basis."""
    if expected_world_pointer is None or expected_world_pointer.active_conversation_id is None:
        raise ValueError("Sourced consultation requires an active World conversation")
    assertions, relationships, evidence = membership
    index = bootstrap.source_index_commitment
    selected = index is not None and index.get("schema") == "dmb_selected_source_anchor_index_commitment_v1"
    if selected:
        selection_policy = "parent_initial_retrieval_with_selected_source_index_v1"
        retrieval_sha = _canonical_sha256({
            "schema": "dmb_selected_retrieval_composite_v1",
            "selection_policy_version": selection_policy,
            "initial_claim_packet_sha256": _canonical_sha256(initial_packet),
            "selected_index": index,
            "source_pins": list(bootstrap.source_scope_anchors),
        })
    elif index is not None:
        selection_policy = "parent_initial_retrieval_with_bounded_source_index_v1"
        retrieval_sha = _canonical_sha256({
            "schema": "dmb_plan_retrieval_composite_v1",
            "selection_policy_version": selection_policy,
            "initial_claim_packet": initial_packet,
            "source_index": index,
        })
    else:
        selection_policy = "parent_initial_retrieval_v1"
        retrieval_sha = _canonical_sha256(initial_packet)
    body = json.loads(view["payloadJson"])
    upper_bound = view["payloadUtf8Bytes"] + 64 * (1 + _json_node_count(body))
    if upper_bound + budget["outputReserveTokens"] > budget["contextLimitTokens"]:
        raise ValueError("Action provider envelope exceeds its context budget")
    authority = PlanWorldGraphAuthorityV1(
        managed_world_id=action.basis.world_id,
        native_world_id=bootstrap.world_scope.world_id,
        binding_version=bootstrap.binding_version,
        scope_mode="world",
        campaign_id=None,
        admissibility_version="gm-v1",
        graph_revision=bootstrap.world_scope.revision_id,
    )
    graph_packet = PlanWorldGraphPacketV1(
        packet_serializer_version="canonical-json-utf8-v1",
        selection_policy_version=selection_policy,
        evidence_sufficiency_policy_version="accepted_fact_with_evidence_v1",
        retrieval_packet_sha256=retrieval_sha,
        candidate_assertion_ids=list(bootstrap.candidate_assertion_ids),
        candidate_relationship_ids=list(bootstrap.candidate_relationship_ids),
        candidate_evidence_ref_ids=list(bootstrap.candidate_evidence_ref_ids),
        retrieval_status="complete" if any(membership) else "empty",
        evidence_sufficiency_status="sufficient" if (assertions or relationships) and evidence else "insufficient",
        result_limit=32,
        coverage_status="complete" if bootstrap.retrieval_session.coverage.state == "ready" else "incomplete",
        truncated=False,
        omission_reasons=[] if (assertions or relationships) and evidence else ["insufficient_evidence"],
    )
    included = bool((assertions or relationships) and evidence)
    assembled = PlanWorldGraphAssembledInputV1(
        assembler_version="agent_harness_final_request_v1",
        budget_policy_version="plan_world_graph_budget_v1",
        provider_model_name=view["model"],
        provider_model_version=view["model"],
        tokenizer_name=budget["estimator"],
        tokenizer_version="v1",
        provider_envelope_input_tokens=upper_bound,
        output_token_reserve=budget["outputReserveTokens"],
        context_window_limit=budget["contextLimitTokens"],
        packet_disposition="included" if included else "omitted_insufficient",
        packet_disposition_reason=None if included else "insufficient_evidence",
        dispatched_packet_sha256=_canonical_sha256(initial_packet) if included else None,
        dispatched_assertion_ids=assertions if included else [],
        dispatched_relationship_ids=relationships if included else [],
        dispatched_evidence_ref_ids=evidence if included else [],
        source_token_accounting=[{
            "source_kind": "message", "source_id": "final_provider_envelope",
            "input_tokens": upper_bound,
        }],
        included_history=[PlanWorldGraphHistoryPinV1(
            turn_id=item.source_turn_id,
            answer_sha256=historical_ask_answer_digest(item),
        ) for item in history_attribution],
        assembled_input_sha256=view["payloadSha256"],
    )
    receipt = build_consultation_receipt(
        action=action,
        origin_conversation_id=expected_world_pointer.active_conversation_id,
        origin_pointer_revision=expected_world_pointer.revision,
        surface_instance_id=surface_instance_id,
        graph_authority=authority,
        graph_packet=graph_packet,
        assembled_input=assembled,
        continuation=continuation,
        history_conversation_id=history_conversation_id,
        history_attribution=history_attribution,
    )
    scope_fields = dict(
        retrieval_session_id=bootstrap.retrieval_session.id,
        world_id=action.basis.world_id,
        campaign_id=None,
        graph_revision=bootstrap.world_scope.revision_id,
        admitted_anchors=list(bootstrap.source_scope_anchors),
    )
    scope = (
        GraphSelectedSourceReadScopeV2(
            **scope_fields,
            initial_claim_packet_sha256=_canonical_sha256(initial_packet),
            selected_index_commitment=index,
        )
        if selected
        else GraphSourceReadScopeV2(**scope_fields)
    )
    policy = SettledGraphExecutionPolicyV3(
        source_read_accounting="settled_receipts_v1",
        policy_version=(
            ("world_graph_execution_selected_scope_uncapped_v1" if selected else "world_graph_execution_uncapped_v1")
            if budget["maxProviderAttempts"] is None else
            ("plan_world_graph_execution_selected_scope_v1" if selected else "plan_world_graph_execution_v1")
        ),
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=budget["maxProviderAttempts"],
        max_graph_operations=budget["maxGraphOperations"],
        max_results_per_operation=512,
        max_total_provider_input_tokens=None if budget["maxProviderAttempts"] is None else budget["contextLimitTokens"] * budget["maxProviderAttempts"],
        max_total_provider_output_tokens=None if budget["maxProviderAttempts"] is None else budget["outputReserveTokens"] * budget["maxProviderAttempts"],
        provider_input_accounting=GraphExecutionAccountingV1(
            kind="conservative_upper_bound", estimator=budget["estimator"]
        ),
        source_opened=False,
        source_read_scope=scope,
        max_source_read_chars=96_000,
        max_chars_per_source_read=12_000,
    )
    return receipt, policy


def _server_history(
    basis: Any,
) -> tuple[list[dict[str, str]], UUID | None, tuple[Any, ...]]:
    """Read only active, completed, exact-basis Ask pairs and keep their typed proof."""
    ask_basis = PlanAskContextBasis.model_validate(basis.model_dump(mode="python"))
    service = AgentConversationService()
    pairs = service.list_completed_plan_ask_context(basis.world_id, ask_basis, limit=6)
    if not isinstance(pairs, list) or len(pairs) > 6:
        raise ValueError("The exact Plan Ask history is unavailable")
    messages: list[dict[str, str]] = []
    attributed: list[Any] = []
    conversation_id: UUID | None = None
    for pair in pairs:
        messages.extend((
            {"role": "user", "content": pair.question[:4000]},
            {"role": "assistant", "content": pair.answer[:4000]},
        ))
        proof = pair.history_attribution
        if proof is not None:
            if proof.plan_basis != ask_basis:
                raise ValueError("Ask attribution differs from this Plan basis")
            if conversation_id is None:
                conversation_id = proof.source_conversation_id
            elif conversation_id != proof.source_conversation_id:
                raise ValueError("Ask attribution changed conversation")
            attributed.append(proof)
    return messages, conversation_id, tuple(attributed)


def _linked_clarification(
    *,
    store: Any,
    action: PlanActionRecord,
    predecessor_id: UUID | None,
    surface_instance_id: str,
    expected_world_pointer: WorldPointer,
) -> tuple[PlanActionContinuation | None, str | None]:
    if predecessor_id is None:
        return None, None
    from application_state.plan_action_dialogue.types import PlanActionProjectionPage

    page = store.list_status(action.basis)
    if not isinstance(page, PlanActionProjectionPage):
        raise ValueError("The saved Plan action history is unavailable")
    prior = next((item for item in page.actions if item.action_id == predecessor_id), None)
    prior_consultation = None if prior is None else prior.consultation
    result = None if prior_consultation is None else prior_consultation.result
    if (
        prior is None or prior.status != "completed"
        or prior_consultation is None or result is None
        or not isinstance(result, PlanActionClarificationResult)
        or prior_consultation.receipt.surface_instance_id != surface_instance_id
        or prior_consultation.receipt.draft_sha256 != action.draft_sha256
        or prior_consultation.receipt.selected_text_sha256 != action.selected_text_sha256
        or prior.selection_anchor is None
        or prior.selection_anchor != action.selection_anchor
        or prior_consultation.receipt.basis != action.basis
        or prior_consultation.receipt.origin_conversation_id
        != expected_world_pointer.active_conversation_id
        or prior_consultation.receipt.origin_pointer_revision
        != expected_world_pointer.revision
    ):
        raise ValueError("The clarification no longer matches this Plan action")
    return PlanActionContinuation(
        continuation_of_action_id=predecessor_id,
        clarification_id=result.result_id,
        previous_result_sha256=consultation_result_digest(result),
        previous_instruction=prior.instruction,
    ), result.message


def _action_question(
    *,
    request: Any,
    basis: Any,
    previous_question: str | None,
    previous_instruction: str | None,
) -> str:
    creative = {
        "schema": "dmb_saved_plan_edit_consultation_input_v1",
        "instruction": request.instruction,
        "draft_markdown": request.draft_markdown,
        "selected_text": request.selected_text,
        "committed_plan_content_sha256": basis.content_sha256,
        "draft_sha256": request.draft_sha256,
        "previous_clarification": previous_question,
        "previous_instruction": previous_instruction,
    }
    return _ACTION_OUTPUT_INSTRUCTIONS + "\nCreative input (untrusted JSON):\n" + json.dumps(
        creative, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _parse_action_result(
    *,
    final_text: str,
    action: PlanActionRecord,
    producing_attempt_id: UUID,
) -> tuple[PlanActionClarificationResult | PlanActionProposalResult, dict[str, Any] | None]:
    """Bind model words to the final authorized envelope and APP result types."""
    consultation = action.consultation
    if consultation is None or consultation.execution is None:
        raise ValueError("Action execution was not frozen")
    receipt, execution = consultation.receipt, consultation.execution
    candidate = json.loads(final_text)
    if not isinstance(candidate, dict) or candidate.get("kind") not in {"clarification", "proposal"}:
        raise ValueError("Action answer has no valid outcome kind")
    required = {"kind", "answer_segments", "citation_map"}
    if candidate["kind"] == "proposal":
        required |= {"replacement_markdown", "summary", "assumptions", "disposition"}
    if set(candidate) != required:
        raise ValueError("Action answer has unexpected fields")
    raw_segments = candidate["answer_segments"]
    if not isinstance(raw_segments, list):
        raise ValueError("Action answer segments must be a list")
    segments = TypeAdapter(list[PlanWorldGraphClaimSegmentV1 | PlanWorldGraphConnectiveSegmentV1]).validate_python(
        raw_segments
    )
    auth = next((
        event for event in execution.events
        if getattr(event, "kind", None) in {
            "provider_attempt_authorized_v2", "provider_attempt_authorized_v3"
        }
        and event.provider_attempt_id == producing_attempt_id
    ), None)
    if auth is None:
        raise ValueError("Action has no producing provider authorization")
    operations = {
        event.event_id: event for event in execution.events
        if getattr(event, "kind", None) in {
            "validated_graph_operation", "validated_graph_operation_v3"
        }
    }
    bindings: dict[str, list[UUID]] = {}
    for segment in segments:
        if not isinstance(segment, PlanWorldGraphClaimSegmentV1):
            continue
        initial_ids = (
            receipt.assembled_input.dispatched_assertion_ids
            if segment.target_kind == "assertion"
            else receipt.assembled_input.dispatched_relationship_ids
        )
        initial = (
            segment.target_id in initial_ids
            and set(segment.evidence_ref_ids).issubset(
                receipt.assembled_input.dispatched_evidence_ref_ids
            )
        )
        included = [
            event_id for event_id in auth.included_graph_event_ids
            if event_id in operations
            and segment.target_id in (
                operations[event_id].assertion_ids
                if segment.target_kind == "assertion"
                else operations[event_id].relationship_ids
            )
            and set(segment.evidence_ref_ids).issubset(
                operations[event_id].evidence_ref_ids
            )
        ]
        if not initial and not included:
            raise ValueError("Action Graph claim lacks producing-envelope support")
        if segment.graph_revision != receipt.graph_authority.graph_revision:
            raise ValueError("Action claim uses a different Graph revision")
        if segment.claim_id in bindings:
            raise ValueError("Action Graph claim IDs must be unique")
        bindings[segment.claim_id] = [] if initial else included[:1]
    raw_map = candidate["citation_map"]
    if raw_map is not None:
        if not isinstance(raw_map, dict) or set(raw_map) != {"entries"}:
            raise ValueError("Action citation map has invalid shape")
        included_reads = set(auth.included_source_read_event_ids)
        reads = [
            read for event in execution.events
            if getattr(event, "kind", None) == "validated_source_read_v2"
            and event.event_id in included_reads
            for read in event.receipts
            if read.outcome in {"enough", "partial", "truncated"}
            and read.content_sha256 is not None and read.returned_chars > 0
        ]
        entries: list[dict[str, Any]] = []
        for entry in raw_map["entries"]:
            if not isinstance(entry, dict) or set(entry) != {
                "claim_id", "target_kind", "target_id", "graph_revision",
                "evidence_ref_ids", "source_opened",
            } or entry["source_opened"] is not False:
                raise ValueError("Action model citation cannot claim source opening")
            refs = entry["evidence_ref_ids"]
            ids = sorted({
                read.source_read_id for read in reads
                if isinstance(refs, list) and read.evidence_ref_id in refs
            })
            entries.append({**entry, "source_opened": bool(ids), "source_read_ids": ids})
        raw_map = {
            "schema": "dmb_graph_citation_map_v2",
            "context_receipt_sha256": receipt.consultation_receipt_sha256,
            "entries": entries,
        }
    citation_map = None if raw_map is None else PlanWorldGraphCitationMapV2.model_validate(raw_map)
    if candidate["kind"] == "clarification" and (
        citation_map is None
        or not citation_map.entries
        or any(not entry.source_read_ids for entry in citation_map.entries)
    ):
        raise ValueError("A factual clarification requires opened authored source evidence")
    message = "\n".join(segment.text for segment in segments)
    common = dict(
        result_id=uuid4(),
        consultation_receipt_sha256=receipt.consultation_receipt_sha256,
        message=message,
        producing_provider_attempt_id=producing_attempt_id,
        answer_segments=segments,
        citation_map=citation_map,
        claim_graph_event_ids=bindings,
    )
    if candidate["kind"] == "clarification":
        return PlanActionClarificationResult(kind="clarification", **common), None
    replacement = candidate["replacement_markdown"]
    summary = candidate["summary"]
    assumptions = candidate["assumptions"]
    if (
        not isinstance(replacement, str) or not replacement.strip()
        or len(replacement) > 12_000
        or not isinstance(summary, str) or not summary.strip()
        or len(summary) > 500
        or not isinstance(assumptions, list) or len(assumptions) > 8
        or any(not isinstance(item, str) or len(item) > 500 for item in assumptions)
    ):
        raise ValueError("Action proposal content is empty or oversized")
    proposal = {
        "replacement_markdown": replacement.strip(),
        "summary": summary.strip(),
        "assumptions": [item.strip() for item in assumptions if item.strip()],
    }
    digest = _canonical_sha256(proposal)
    return PlanActionProposalResult(
        kind="proposal",
        disposition=candidate["disposition"],
        proposal_sha256=digest,
        **common,
    ), proposal


def _source_open_targets(action: PlanActionRecord) -> list[dict[str, Any]]:
    """Project openable cited anchors from this action's own frozen source scope."""
    consultation = action.consultation
    if consultation is None or consultation.execution is None:
        return []
    result = consultation.result
    if result is None or result.kind == "context_unavailable" or result.citation_map is None:
        return []
    receipt = consultation.receipt
    authority = receipt.graph_authority
    execution = consultation.execution
    scope = execution.policy.source_read_scope
    if authority is None or scope.world_id != authority.managed_world_id or scope.graph_revision != authority.graph_revision:
        return []
    pins_by_evidence: dict[str, list[Any]] = {}
    effective_pins = (
        execution.effective_source_pins().values()
        if isinstance(execution, PlanWorldGraphExecutionV3)
        else scope.admitted_anchors
    )
    for pin in effective_pins:
        pins_by_evidence.setdefault(pin.evidence_ref_id, []).append(pin)
    auth = next((
        event for event in execution.events
        if getattr(event, "kind", None) in {
            "provider_attempt_authorized_v2", "provider_attempt_authorized_v3"
        }
        and event.provider_attempt_id == result.producing_provider_attempt_id
    ), None)
    included_ids = set(auth.included_source_read_event_ids) if auth else set()
    reads = {
        read.source_read_id: read
        for event in execution.events
        if getattr(event, "kind", None) == "validated_source_read_v2"
        and event.event_id in included_ids
        for read in event.receipts
    }
    targets: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for citation in result.citation_map.entries:
        for evidence_id in citation.evidence_ref_ids:
            for pin in pins_by_evidence.get(evidence_id, []):
                key = (citation.claim_id, evidence_id, pin.anchor_id)
                if key in seen or len(targets) >= 64:
                    continue
                seen.add(key)
                matching = [
                    reads[read_id] for read_id in citation.source_read_ids
                    if read_id in reads
                    and reads[read_id].anchor_id == pin.anchor_id
                    and reads[read_id].evidence_ref_id == pin.evidence_ref_id
                    and reads[read_id].source_artifact_id == pin.source_artifact_id
                    and reads[read_id].source_revision_id == pin.source_revision_id
                    and reads[read_id].outcome in {"enough", "partial", "truncated"}
                ]
                read = matching[0] if len(matching) == 1 else None
                targets.append({
                    "schema": "dmb_agent_evidence_anchor_open_target_v1",
                    "kind": "evidence_anchor",
                    "claim_id": citation.claim_id,
                    "anchor_id": pin.anchor_id,
                    "evidence_ref_id": evidence_id,
                    "source_artifact_id": pin.source_artifact_id,
                    "source_revision_id": pin.source_revision_id,
                    "managed_world_id": authority.managed_world_id,
                    "native_world_id": authority.native_world_id,
                    "binding_version": authority.binding_version,
                    "graph_revision": authority.graph_revision,
                    "source_read_id": None if read is None else read.source_read_id,
                    "read_outcome": None if read is None else read.outcome,
                })
    return targets


def project_plan_action_source_targets(action: Any) -> list[dict[str, Any]]:
    """Public action-history projection; no source body or provider output is returned."""
    return _source_open_targets(action)


def _consultation_projection(action: PlanActionRecord) -> dict[str, Any]:
    consultation = action.consultation
    assert consultation is not None and consultation.result is not None
    return {
        "origin_conversation_id": str(consultation.receipt.origin_conversation_id),
        "origin_pointer_revision": consultation.receipt.origin_pointer_revision,
        "result": consultation.result.model_dump(mode="json", by_alias=True),
        "source_open_targets": _source_open_targets(action),
        "graph_revision": (
            None if consultation.receipt.graph_authority is None
            else consultation.receipt.graph_authority.graph_revision
        ),
    }


def execute_plan_action_consultation(
    *,
    root: Path,
    request: Any,
    action: PlanActionRecord,
    store: Any,
    expected_world_pointer: WorldPointer,
    runtime: Any | None = None,
) -> Any:
    """Run one already-reserved saved selection action through the shared Harness."""
    from apps.live_control_server.models.plan_document_edit_proposal import (
        WorldPlanDocumentEditProposalResponse,
        WorldPlanEditClarificationResponse,
    )
    from apps.live_control_server.routes.agent import _plan_context_resolver

    if action.dispatch_token is None or action.target_kind != "replace_selection":
        raise ValueError("A pending saved selection action is required")
    surface_instance_id = action.basis.document_id
    try:
        continuation, previous_question = _linked_clarification(
            store=store,
            action=action,
            predecessor_id=request.continuation_of_action_id,
            surface_instance_id=surface_instance_id,
            expected_world_pointer=expected_world_pointer,
        )
        history, history_conversation_id, history_attribution = _server_history(action.basis)
        if history_conversation_id is not None and history_conversation_id != expected_world_pointer.active_conversation_id:
            raise ValueError("Attributed Ask history belongs to another conversation")
        committed = get_committed_playable_revision(
            action.basis.document_id, kind="plan", expected_world_id=action.basis.world_id
        )
        if (
            committed.object_revision != action.basis.object_revision
            or committed.content_sha256 != action.basis.content_sha256
            or committed.work_revision_id != str(action.basis.work_revision_id)
            or committed.revision_n != action.basis.revision_n
        ):
            raise ValueError("The saved Plan changed before Graph consultation")
        question = _action_question(
            request=request, basis=action.basis, previous_question=previous_question,
            previous_instruction=(None if continuation is None else continuation.previous_instruction),
        )
        search = PlanActionGraphSearchIntent(
            turn_id=str(action.action_id),
            message=request.instruction + "\nSelected Plan passage: " + request.selected_text,
        )
        work = AgentTurnResolvedWork(
            kind="plan", object_id=action.basis.document_id,
            revision=action.basis.object_revision, changed_since_expected=False,
            owner_kind="world", owner_id=action.basis.world_id,
            world_id=action.basis.world_id, plan_markdown=committed.markdown,
            content_basis=AgentTurnContentBasis(
                world_id=action.basis.world_id,
                document_id=action.basis.document_id,
                object_revision=action.basis.object_revision,
                work_revision_id=str(action.basis.work_revision_id),
                revision_n=action.basis.revision_n,
                content_sha256=action.basis.content_sha256,
                committed_status="committed",
                has_divergent_working_copy=not action.draft_matches_basis,
            ),
        )
        bootstrap = _plan_context_resolver(
            search, {"kind": "world", "id": action.basis.world_id}, work, None
        )
        assembly = assemble_agent_graph_context(
            question=question, graph_envelope=bootstrap.graph_envelope,
            retrieval_session=bootstrap.retrieval_session,
            turn_id=str(action.action_id),
            conversation_history=history,
            surface_context=AgentSurfaceContext(
                surface_id="plan", surface_instance_id=surface_instance_id
            ),
        )
        budget = _policy_request_budget()
    except AgentTurnServiceError as exc:
        failure_code = exc.code if exc.code else "graph_unavailable"
        receipt = build_consultation_receipt(
            action=action, surface_instance_id=surface_instance_id,
            origin_conversation_id=expected_world_pointer.active_conversation_id,
            origin_pointer_revision=expected_world_pointer.revision,
            authority_failure_code=failure_code, continuation=continuation,
        )
        frozen, fresh = store.freeze_consultation(
            action_id=action.action_id, token=action.dispatch_token,
            fence=action.fence, receipt=receipt,
        )
        if not fresh:
            raise ValueError("The action authority failure was already frozen")
        result = PlanActionContextUnavailableResult(
            kind="context_unavailable", result_id=uuid4(),
            consultation_receipt_sha256=receipt.consultation_receipt_sha256,
            failure_code=failure_code,
            message="World knowledge could not be verified for this edit. Retry after the selected World is available.",
        )
        completed = store.finish_consultation(
            action_id=frozen.action_id, token=frozen.dispatch_token,
            fence=frozen.fence, result=result,
        )
        return WorldPlanEditClarificationResponse(
            action_id=completed.action_id, idempotency_key=request.idempotency_key,
            document_id=request.document_id, world_id=request.world_id,
            base_revision=request.base_revision,
            base_content_sha256=request.base_content_sha256,
            draft_sha256=request.draft_sha256,
            selected_text_sha256=action.selected_text_sha256,
            kind="context_unavailable", message=result.message,
            consultation=_consultation_projection(completed),
        )
    except ValueError as exc:
        store.finish(
            action_id=action.action_id, token=action.dispatch_token,
            fence=action.fence, status="failed",
            failure_code="plan_consultation_invalid",
        )
        raise PlanActionConsultationError(
            "plan_consultation_invalid",
            "The linked clarification or saved Plan basis no longer matches this edit.",
            status_code=409,
        ) from exc
    adapter = ActionPolicyExecutionAdapter(
        store=store, action=action, bootstrap=bootstrap, budget=budget,
        surface_instance_id=surface_instance_id, continuation=continuation,
        history_conversation_id=history_conversation_id,
        history_attribution=history_attribution,
        root=root,
        expected_world_pointer=expected_world_pointer,
    )
    selected_runtime = runtime or default_hermes_agent_runtime()
    run = getattr(selected_runtime, "run_with_provider_authorization", None)
    if not callable(run):
        raise ValueError("The Agent Harness cannot authorize provider requests")
    invocation = replace(assembly.invocation, plan_continuity_turn=True)
    options: dict[str, Any] = {
        "request_budget": budget,
        "on_graph_operation": adapter.broker_graph_operation,
        "on_provider_lifecycle": adapter.record_lifecycle,
        "context_read_enabled": True,
    }
    if bootstrap.source_scope_anchors:
        options["source_read_enabled"] = True
    result = run(invocation, adapter.authorize, **options)
    final_action = adapter.stop()
    if adapter.failure is not None or result.status != "ok":
        from apps.live_control_server.services.plan_action_terminal_diagnostic import retain_terminal_diagnostic
        final_action = retain_terminal_diagnostic(adapter, result)
    execution = None if final_action.consultation is None else final_action.consultation.execution
    outcome_unknown = execution is not None and any(
        getattr(event, "kind", None) == "provider_outcome"
        and event.outcome == "outcome_unknown"
        for event in execution.events
    )
    failed_required_read = execution is not None and any(
        (
            getattr(event, "kind", None) == "validated_source_read_v2"
            and any(read.outcome in {"denied", "unavailable"} for read in event.receipts)
        ) or (
            getattr(event, "kind", None) == "validated_related_recap_context_v2"
            and event.outcome == "unavailable"
        )
        for event in execution.events
    )
    if (failed_required_read or adapter.required_context_failed) and not outcome_unknown:
        receipt = final_action.consultation.receipt
        unavailable = PlanActionContextUnavailableResult(
            kind="context_unavailable", result_id=uuid4(),
            consultation_receipt_sha256=receipt.consultation_receipt_sha256,
            message="A required World source could not be read. No edit proposal was made.",
            failure_code="source_unavailable",
        )
        completed = store.finish_consultation(
            action_id=final_action.action_id, token=final_action.dispatch_token,
            fence=final_action.fence, result=unavailable,
        )
        return WorldPlanEditClarificationResponse(
            action_id=completed.action_id, idempotency_key=request.idempotency_key,
            document_id=request.document_id, world_id=request.world_id,
            base_revision=request.base_revision,
            base_content_sha256=request.base_content_sha256,
            draft_sha256=request.draft_sha256,
            selected_text_sha256=action.selected_text_sha256,
            kind="context_unavailable", message=unavailable.message,
            consultation=_consultation_projection(completed),
        )
    if (
        adapter.failure is not None or result.status != "ok"
        or not result.final_text
        or adapter.producing_provider_attempt_id is None
        or final_action.consultation is None
    ):
        if final_action.consultation is not None and not outcome_unknown:
            store.finish(
                action_id=final_action.action_id, token=final_action.dispatch_token,
                fence=final_action.fence, status="failed",
                failure_code="plan_context_delivery_failure",
            )
        raise ValueError("The sourced Plan edit could not be durably delivered")
    try:
        typed_result, proposal = _parse_action_result(
            final_text=result.final_text, action=final_action,
            producing_attempt_id=adapter.producing_provider_attempt_id,
        )
    except (ValueError, TypeError) as exc:
        store.finish(
            action_id=final_action.action_id, token=final_action.dispatch_token,
            fence=final_action.fence, status="failed",
            failure_code="proposal_output_invalid",
        )
        raise PlanActionConsultationError(
            "proposal_output_invalid",
            "The sourced Plan edit answer did not pass evidence validation.",
            status_code=502,
        ) from exc
    completed = store.finish_consultation(
        action_id=final_action.action_id, token=final_action.dispatch_token,
        fence=final_action.fence, result=typed_result,
    )
    projection = _consultation_projection(completed)
    if typed_result.kind == "clarification":
        return WorldPlanEditClarificationResponse(
            action_id=completed.action_id, idempotency_key=request.idempotency_key,
            document_id=request.document_id, world_id=request.world_id,
            base_revision=request.base_revision,
            base_content_sha256=request.base_content_sha256,
            draft_sha256=request.draft_sha256,
            selected_text_sha256=action.selected_text_sha256,
            kind="clarification", message=typed_result.message,
            consultation=projection,
        )
    assert proposal is not None
    return WorldPlanDocumentEditProposalResponse(
        action_id=completed.action_id, idempotency_key=request.idempotency_key,
        document_id=request.document_id, world_id=request.world_id,
        base_revision=request.base_revision,
        base_content_sha256=request.base_content_sha256,
        draft_sha256=request.draft_sha256,
        target_kind="replace_selection",
        selected_text_sha256=action.selected_text_sha256,
        replacement_markdown=proposal["replacement_markdown"],
        summary=proposal["summary"], assumptions=proposal["assumptions"],
        model=budget["model"], model_observed=False,
        model_latency_ms=0, wall_latency_ms=0, usage=None,
        consultation=projection,
    )
