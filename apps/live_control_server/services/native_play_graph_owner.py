"""Parent-owned preparation for exact native Play Graph turns."""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid5

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_authority import (
    play_graph_execution_policy_digest,
    play_source_frame,
    validate_play_source_owner_join,
)


@dataclass(frozen=True)
class PreparedPlaySourceRead:
    reference_index: int
    catalog: Any
    excerpt: Any


@dataclass(frozen=True)
class PreparedPlayAuthoredSources:
    context: Any
    reads: tuple[PreparedPlaySourceRead, ...]

    def model_frame(self):
        from application_state.agent_conversation.native_corpus import model_body_frame_rows
        return model_body_frame_rows(self.context.authority,
            ((row, row.catalog) for row in self.reads),
            lambda row: 'r' + str(row.reference_index))


def prepare_authored_sources(request, principal, *, existing_turn=None, prepared=None):
    """Core opens exact human selections; this creates no APP/model read grant."""
    from application_state.agent_conversation.play_authored_sources import PlayAuthoredSourceContextV1, reads
    from application_state.agent_conversation.authored_graph_references import validate_selected_source_read
    from ..integrations.dungeonmind.native_corpus_source import prepare_native_source_context, read_authored_source
    refs = request.authored_references
    if refs is None:
        return None
    if request.surface.surface_id != 'play' or principal is None or principal.role != 'gm':
        raise ValueError('Play source references require the exact GM-owned Play request')
    if existing_turn is not None:
        receipt = existing_turn.graph_context_receipt
        frozen = getattr(receipt, 'authored_source_context', None)
        if frozen is None or frozen.references != refs:
            raise ValueError('Retained Play source references differ from their accepted input')
        captured = reads(existing_turn.graph_context_execution)
        if len(captured) != len(refs.references):
            raise ValueError('The interrupted source read is retained; submit a new request to acquire it again')
        # Reuse the original source identities and read events, while Core
        # refreshes current access to those exact original-revision members.
        from ..integrations.dungeonmind.native_corpus_source import read_native_corpus_member
        if prepared is None:
            prepared=prepare_native_source_context(managed_world_id=frozen.authority.managed_world_id,
                principal=principal,revision_id=frozen.authority.revision_id)
        for row in captured:
            body=read_native_corpus_member(authority=frozen.authority,member=row.catalog.source,
                principal=principal,prepared=prepared)
            extent=row.excerpt.section
            if body is None or body[extent.char_start:extent.char_end]!=row.excerpt.text:
                raise ValueError('Retained Play source is no longer readable at its original extent')
        return PreparedPlayAuthoredSources(frozen, tuple(PreparedPlaySourceRead(
            row.reference_index, row.catalog, row.excerpt) for row in captured))
    if prepared is None:
        prepared = prepare_native_source_context(managed_world_id=request.owner_scope.world_id,
            principal=principal)
    ctx = PlayAuthoredSourceContextV1(authority=prepared.authority, references=refs)
    rows = []
    for index, ref in enumerate(refs.references):
        catalog, excerpt = read_authored_source(prepared, ref)
        validate_selected_source_read(ref, catalog, excerpt, authority_sha256=ctx.authority_sha256)
        rows.append(PreparedPlaySourceRead(index, catalog, excerpt))
    return PreparedPlayAuthoredSources(ctx, tuple(rows))


def acquire_authored_sources(adapter):
    """Record the already Core-opened human reads under the accepted Play claim."""
    from uuid import uuid4
    from .native_authored_references import capture_input
    prepared = getattr(adapter.work, 'play_authored_sources', None)
    if prepared is None:
        return
    receipt = adapter.fence.turn.graph_context_receipt
    if receipt.authored_source_context != prepared.context:
        raise ValueError('Prepared Play sources differ from their accepted source context')
    from application_state.agent_conversation.play_authored_sources import validate_binding, validate_events, reads
    execution=adapter.fence.turn.graph_context_execution
    if execution.events:
        validate_binding(receipt,execution)
        validate_events(execution)
        retained=tuple(PreparedPlaySourceRead(row.reference_index,row.catalog,row.excerpt) for row in reads(execution))
        if retained!=prepared.reads or len(retained)!=len(prepared.context.references.references):
            raise ValueError('Retained Play sources differ from their prepared exact read prefix')
        adapter.turn=adapter.fence.turn
        return
    capture_input(adapter)
    for row in prepared.reads:
        expected = prepared.context.references.references[row.reference_index]
        def selected(ref, row=row, expected=expected):
            if ref != expected:
                raise ValueError('Play source read changed its accepted human selection')
            return row.catalog, row.excerpt
        adapter.turn, _ = adapter.fence.append('observe_native_authored_source', 'event_id', uuid4(),
            reference_index=row.reference_index, materialize=selected)


def prepare_play_sources(request: Any, work: Any) -> tuple[t.PlaySourceFrameV1, str]:
    """Build current Play source values from the independently resolved Run owner."""
    basis = None if work is None else work.play_context_receipt
    target = getattr(request, "play_target", None)
    primary = getattr(request, "primary_work", None)
    context = None if work is None else work.surface_context
    play = None if context is None else getattr(context, "current_play", None)
    if (not isinstance(basis, t.PlayRunTurnContextReceiptV2) or target is None
            or primary is None or primary.kind != "run" or play is None
            or basis.world_id != request.owner_scope.world_id
            or basis.run_id != primary.object_id or basis.run_revision != primary.expected_revision
            or target.beat_id != basis.beat_id or target.scene_id != basis.scene_id
            or target.marker_grammar_version != basis.marker_grammar_version
            or primary.play_content_basis != t.PlayContentBasis(
                edition_revision=basis.edition_revision,
                edition_revision_id=basis.edition_revision_id,
                content_sha256=basis.content_sha256,
            )):
        raise ValueError("Play target differs from the independently resolved Run owner")
    from apps.live_control_server.services.agent_play_surface_context import render_agent_play_surface_context
    from apps.live_control_server.services.agent_runtime import AgentSurfaceContext

    if not isinstance(context, AgentSurfaceContext):
        raise ValueError("Play source context is not owner-resolved")
    # Keep the selected Scene note as its own cited source instead of copying it
    # into the larger current-moment payload.
    from dataclasses import replace
    moment_context = replace(context, current_play=replace(play, saved_scene_note=None))
    moment = render_agent_play_surface_context(moment_context)
    if not isinstance(moment, str) or not moment.strip():
        raise ValueError("Play current moment is unavailable")
    locator = t.play_source_locator(basis)
    sources = [t.PlaySourcePayloadV1(source_kind="current_moment", locator=locator, text=moment)]
    if basis.scene_note is not None:
        sources.append(t.PlaySourcePayloadV1(source_kind="scene_note", locator=locator, text=basis.scene_note))
    frame = play_source_frame(tuple(sources))
    validate_play_source_owner_join(
        frame, basis, owner_resolved_current_moment_text=moment,
    )
    return frame, moment


def native_play_input_message(request: Any, frame: t.PlaySourceFrameV1, sessions=(), authored_sources=None) -> str:
    """Carrier included as the user message and tied to the accepted submission."""
    from application_state.agent_conversation.play_graph_input import NativePlayInputV6
    from application_state.agent_conversation.play_session_input import pack

    submission_id = uuid5(NAMESPACE_URL, f"dmb-agent-turn:{request.owner_scope.world_id}:{request.turn_id}")
    from application_state.agent_conversation.surface_evidence_answer import PLAN_INSTRUCTIONS, PLAN_POLICY, BODY_INSTRUCTIONS, BODY_POLICY
    frame_wire, session_wire = pack(frame,str(submission_id),list(sessions))
    carrier = NativePlayInputV6(
        submission_id=submission_id,
        message=request.message,
        source_frame=frame_wire,
        session_evidence=session_wire,
        native_body_evidence=authored_sources.model_frame() if authored_sources is not None else None,
        answer_policy=BODY_POLICY if authored_sources is not None else PLAN_POLICY,
        answer_instructions=BODY_INSTRUCTIONS if authored_sources is not None else PLAN_INSTRUCTIONS,
    )
    return json.dumps(carrier.model_dump(mode="json", by_alias=True), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False)


def freeze_play_receipt(
    request: Any,
    work: Any,
    bootstrap: Any,
    view: Mapping[str, Any],
    budget: Mapping[str, Any],
    *,
    included_history: tuple = (),
) -> tuple[t.PlayWorldGraphContextReceiptV1, t.PlayWorldGraphExecutionV1, tuple[list[str], list[str], list[str]]]:
    """Freeze an independently typed Play receipt and finite native ledger."""
    basis = None if work is None else work.play_context_receipt
    if not isinstance(basis, t.PlayRunTurnContextReceiptV2):
        raise ValueError("Native Play requires an exact saved Run edition")
    frame, moment = prepare_play_sources(request, work)
    packet = _initial_claim_packet(bootstrap, view)
    assertions, relationships, evidence = _initial_membership(packet, bootstrap)
    packet_included = bool((assertions or relationships) and evidence)
    coverage = bootstrap.retrieval_session.coverage.state == "ready"
    index = bootstrap.source_index_commitment
    if isinstance(index, Mapping) and index.get("schema") == "dmb_selected_source_anchor_index_commitment_v1":
        raise ValueError("Native Play source scope does not admit a selected-index Graph policy")
    selection_policy = (
        "parent_initial_retrieval_with_bounded_source_index_v1"
        if index is not None else "parent_initial_retrieval_v1"
    )
    retrieval_sha = t.canonical_sha256({
        "schema": "dmb_plan_retrieval_composite_v1",
        "selection_policy_version": selection_policy,
        "initial_claim_packet": packet,
        "source_index": index,
    }) if index is not None else t.canonical_sha256(packet)
    body = json.loads(view["payloadJson"])
    upper = view["payloadUtf8Bytes"] + 64 * (1 + _node_count(body))
    if upper + budget["outputReserveTokens"] > budget["contextLimitTokens"]:
        raise ValueError("Native Play provider request exceeds its context budget")
    graph_packet = t.PlayWorldGraphPacketV1(
        packet_serializer_version="canonical-json-utf8-v1",
        selection_policy_version=selection_policy,
        evidence_sufficiency_policy_version="accepted_fact_with_evidence_v1",
        retrieval_packet_sha256=retrieval_sha,
        candidate_assertion_ids=list(bootstrap.candidate_assertion_ids),
        candidate_relationship_ids=list(bootstrap.candidate_relationship_ids),
        candidate_evidence_ref_ids=list(bootstrap.candidate_evidence_ref_ids),
        retrieval_status="complete" if any((bootstrap.candidate_assertion_ids,
            bootstrap.candidate_relationship_ids, bootstrap.candidate_evidence_ref_ids)) else "empty",
        evidence_sufficiency_status="sufficient" if packet_included else "insufficient",
        result_limit=32, coverage_status="complete" if coverage else "incomplete",
        truncated=False, omission_reasons=[] if packet_included else ["insufficient_evidence"],
    )
    assembled = t.PlayWorldGraphAssembledInputV1(
        assembler_version=bootstrap.assembler_version,
        budget_policy_version="native_play_world_graph_budget_v1",
        provider_model_name=view["model"], provider_model_version=view["model"],
        tokenizer_name=budget["estimator"], tokenizer_version="v1",
        provider_envelope_input_tokens=upper,
        output_token_reserve=budget["outputReserveTokens"],
        context_window_limit=budget["contextLimitTokens"],
        packet_disposition="included" if packet_included else "omitted_insufficient",
        packet_disposition_reason=None if packet_included else "insufficient_evidence",
        dispatched_packet_sha256=t.canonical_sha256(packet) if packet_included else None,
        dispatched_assertion_ids=assertions if packet_included else [],
        dispatched_relationship_ids=relationships if packet_included else [],
        dispatched_evidence_ref_ids=evidence if packet_included else [],
        source_token_accounting=[t.PlayGraphSourceTokenAccountingV1(
            source_kind="message", source_id="final_provider_envelope", input_tokens=upper,
        )],
        included_history=[dict(turn_id=str(turn_id), answer_sha256=sha256(text.encode("utf-8")).hexdigest())
            for turn_id, text in included_history
            if text and text in _text_values(body)],
        assembled_input_sha256=view["payloadSha256"],
    )
    authority = t.PlanWorldGraphAuthorityV1(
        managed_world_id=basis.world_id,
        native_world_id=bootstrap.world_scope.world_id,
        binding_version=bootstrap.binding_version,
        scope_mode="world", campaign_id=None, admissibility_version="gm-v1",
        graph_revision=bootstrap.world_scope.revision_id,
    )
    receipt_payload = dict(
        receipt_serializer_version="canonical-json-utf8-v1",
        context_receipt_sha256="0" * 64,
        play_graph_policy=t.PlayGraphPolicyV1(),
        authored_source_context=work.play_authored_sources.context if getattr(work, 'play_authored_sources', None) is not None else None,
        play_basis=basis,
        play_sources=frame.manifest,
        play_source_frame_sha256=t.canonical_sha256(frame),
        retrieval_session_id=bootstrap.retrieval_session.id,
        graph_authority=authority,
        graph_packet=graph_packet,
        assembled_input=assembled,
        evidence_mode="metadata_only", source_opened=False,
    )
    provisional = t.PlayWorldGraphContextReceiptV1.model_construct(**receipt_payload)
    receipt = t.PlayWorldGraphContextReceiptV1.model_validate(provisional.model_copy(update={
        "context_receipt_sha256": t.canonical_sha256(provisional.model_dump(
            mode="json", by_alias=True, exclude={"context_receipt_sha256"},
        )),
    }).model_dump(mode="python", by_alias=True))
    anchors = [t.GraphSourceScopeAnchorV2.model_validate(anchor)
        for anchor in bootstrap.source_scope_anchors]
    scope = t.GraphSourceReadScopeV2(
        retrieval_session_id=bootstrap.retrieval_session.id,
        world_id=basis.world_id, campaign_id=None,
        graph_revision=bootstrap.world_scope.revision_id,
        admitted_anchors=anchors,
    )
    policy = t.PlayCorpusSourceSectionsPolicyV1(
        authored_source_context=work.play_authored_sources.context if getattr(work, 'play_authored_sources', None) is not None else None,
        corpus_source_policy="registered_corpus_sections_v1",
        native_source_section_policy="exact_native_source_sections_v1",
        allowed_graph_operations=["expand_graph_retrieval"],
        max_provider_attempts=64, max_graph_operations=512,
        max_results_per_operation=512,
        max_total_provider_input_tokens=None,
        max_total_provider_output_tokens=None,
        provider_input_accounting=t.GraphExecutionAccountingV1(
            kind="conservative_upper_bound", estimator=budget["estimator"],
        ),
        source_opened=False,
        source_read_scope=scope,
        source_read_accounting="settled_receipts_v1",
        # Initial discovery may have no anchors. Later exact scope extensions
        # admit reads; pin availability never changes this existing capacity.
        max_source_read_chars=96000,
        max_chars_per_source_read=12000,
    )
    execution = t.PlayWorldGraphExecutionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(receipt.context_receipt_sha256, policy),
        policy=policy, events=[],
    )
    return receipt, execution, (assertions, relationships, evidence)


def _initial_claim_packet(bootstrap: Any, view: Mapping[str, Any]) -> dict[str, Any]:
    from apps.live_control_server.services.agent_turn_service import _initial_claim_packet_from_view
    return _initial_claim_packet_from_view(
        type("RequestView", (), {"payload_json": view["payloadJson"], "api_mode": view.get("apiMode")})(),
        bootstrap,
    )


def _initial_membership(packet: Mapping[str, Any], bootstrap: Any) -> tuple[list[str], list[str], list[str]]:
    from apps.live_control_server.services.agent_turn_service import _initial_packet_membership
    return _initial_packet_membership(packet, bootstrap)


def _node_count(value: Any) -> int:
    if isinstance(value, Mapping):
        return 1 + sum(_node_count(item) for item in value.values())
    if isinstance(value, list):
        return 1 + sum(_node_count(item) for item in value)
    return 0


def _text_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, Mapping):
        return [text for item in value.values() for text in _text_values(item)]
    if isinstance(value, list):
        return [text for item in value for text in _text_values(item)]
    return []


def verify_play_input_message(view: Mapping[str, Any], request: Any, work: Any) -> t.PlaySourceFrameV1:
    """Check the exact current source carrier before claiming the provider attempt."""
    from application_state.agent_conversation.play_graph_input import NativePlayInputV6
    from application_state.agent_conversation.source_writer_output import strict_json
    from application_state.agent_conversation.play_graph_input import _user_texts

    expected_frame, _moment = prepare_play_sources(request, work)
    try:
        body = strict_json(view["payloadJson"])
        api_mode = view.get("apiMode")
        carriers = []
        for text in _user_texts(body, api_mode):
            try:
                candidate = strict_json(text)
            except (ValueError, TypeError):
                continue
            if isinstance(candidate, dict) and candidate.get("schema") == "dmb_native_play_input_v6":
                parsed = NativePlayInputV6.model_validate_json(json.dumps(candidate, ensure_ascii=False))
                expected_id = uuid5(NAMESPACE_URL, f"dmb-agent-turn:{request.owner_scope.world_id}:{request.turn_id}")
                if parsed.submission_id == expected_id:
                    carriers.append(parsed)
        selected = getattr(work, 'play_authored_sources', None)
        if len(carriers) == 1 and carriers[0].native_body_evidence != (selected.model_frame() if selected is not None else None):
            raise ValueError('Play selected sources differ from actual prepared Core reads')
        if len(carriers) == 1 and carriers[0].resolved_sessions() != list((work.session_evidence or {}).get("sessions", [])):
            raise ValueError("Play sessions differ from resolved frozen evidence")
        if len(carriers) != 1 or carriers[0].message != request.message or carriers[0].resolved_source_frame() != expected_frame:
            raise ValueError("Current Play source carrier differs from the exact Run/Scene target")
    except (KeyError, TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("Native Play provider request lacks its exact current-source carrier") from exc
    return expected_frame
