"""Parent-only Rules lookup kernel; no tool registration or dispatch authority.

The caller persists authorization before reading and observation before delivery.
Current-context references must come from the parent's actual prepared input.
Handles alone never grant inclusion authority in the producing request.
"""
from __future__ import annotations

from hashlib import sha256
import json
from uuid import UUID, uuid4


from application_state.agent_conversation.rules_authority_events import (
    RulesExecutionV1, RulesQueryObservedV1, RulesToolAuthorizedV1,
    RulesBuildToolAuthorizedV1, RulesPlanJevToolAuthorizedV1, build_rules_operation_id,
    normalized_question, query_identity, ref_map,
)
from application_state.agent_conversation.rules_authority_packet import (
    RulesBudgetDiagnosticV1, RulesPacketV1, append_observed_output,
)
from application_state.agent_conversation.rules_authority_types import (
    RulesSupportRefV1, RulesSupportV1, canonical_bytes, canonical_sha256,
)
from application_state.agent_conversation.rules_authority_runtime import RulesLookupPreparedV1
from . import rules_lookup as reader

from application_state.agent_conversation.rules_authority_policy import RULESET, LookupRulesArguments


def _check_scope(execution: RulesExecutionV1) -> None:
    if (execution.state != "active" or execution.scope.ruleset_id != RULESET
            or execution.scope.corpus_sha256 != reader.SEED_DIGEST):
        raise ValueError("Rules lookup requires the current admitted active scope")


def prepare_authorization(execution: RulesExecutionV1, call_id: str,
                          arguments: LookupRulesArguments) -> RulesToolAuthorizedV1:
    """Prepare only; locked durable append must succeed before any source read."""
    _check_scope(execution)
    arguments = LookupRulesArguments.model_validate(arguments)
    question = normalized_question(arguments.question)
    event = RulesToolAuthorizedV1(kind="tool_authorized", event_id=uuid4(),
        sequence=len(execution.events), execution_id=execution.scope.execution_id,
        call_id=call_id, query_id=query_identity(execution.scope, question),
        normalized_question=question, packet_limit=4)
    return _preflight_authorization(execution, event)


def prepare_build_authorization(execution: RulesExecutionV1, arguments: LookupRulesArguments, *,
        origin_provider_attempt_id: UUID, origin_request_envelope_sha256: str,
        decision_request_id: str, operation_index: int) -> RulesBuildToolAuthorizedV1:
    """Parent supplies an actually acknowledged typed decision, never a fake call."""
    _check_scope(execution)
    arguments = LookupRulesArguments.model_validate(arguments)
    question = normalized_question(arguments.question)
    query = query_identity(execution.scope, question)
    event = RulesBuildToolAuthorizedV1(kind="build_tool_authorized", event_id=uuid4(),
        sequence=len(execution.events), execution_id=execution.scope.execution_id,
        call_id=build_rules_operation_id(origin_provider_attempt_id, decision_request_id, operation_index, query),
        query_id=query, normalized_question=question, packet_limit=4,
        origin_provider_attempt_id=origin_provider_attempt_id,
        origin_request_envelope_sha256=origin_request_envelope_sha256,
        decision_request_id=decision_request_id, operation_index=operation_index)
    return _preflight_authorization(execution, event)


def _preflight_authorization(execution, event):
    # Exercise the same closed whole-ledger invariants as the locked store.
    data = execution.model_dump(mode="json", by_alias=True)
    data["events"].append(event.model_dump(mode="json", by_alias=True))
    data["budget_use"]["calls"] += 1
    data["budget_use"]["distinct_questions"] = len({
        e.query_id for e in (*execution.events, event) if isinstance(e, RulesToolAuthorizedV1)
    })
    RulesExecutionV1.model_validate_json(json.dumps(data))
    return event


def _support_for_hit(execution, bundle, hit):
    if not isinstance(hit, dict):
        raise ValueError("Rules reader returned a malformed hit")
    unit = next((u for u in bundle.units if u.unit_id == hit.get("unit_id")), None)
    if unit is None:
        raise ValueError("Rules hit has no admitted source unit")
    expected = reader._identity(execution.scope.corpus_sha256, bundle, unit)
    start, end, text = hit.get("excerpt_start"), hit.get("excerpt_end"), hit.get("excerpt")
    if (any(hit.get(k) != v for k, v in expected.items())
            or type(start) is not int or type(end) is not int
            or not 0 <= start < end <= len(unit.text)
            or not isinstance(text, str) or unit.text[start:end] != text
            or hit.get("excerpt_complete") is not (start == 0 and end == len(unit.text))
            or sha256(unit.text.encode()).hexdigest() != unit.text_sha256):
        raise ValueError("Rules hit differs from its admitted source proof")
    candidate = RulesSupportV1(schema="dmb_rules_support_v1", support_id=uuid4(),
        corpus_sha256=execution.scope.corpus_sha256, ruleset_id=bundle.ruleset_id,
        unit_id=unit.unit_id, full_text_sha256=unit.text_sha256,
        excerpt_start=start, excerpt_end=end, excerpt_text=text,
        excerpt_sha256=sha256(text.encode()).hexdigest(), source_title=unit.source_title,
        section=unit.section, source_uri=unit.source_uri, source_sha256=unit.source_sha256,
        page_fingerprint=unit.page_fingerprint, pdf_page_index=unit.pdf_page_index,
        printed_page=unit.printed_page)
    for stored in execution.supports.values():
        existing = stored.support
        if (existing.unit_id, existing.full_text_sha256, existing.excerpt_start,
            existing.excerpt_end, existing.excerpt_sha256) == (
            candidate.unit_id, candidate.full_text_sha256, candidate.excerpt_start,
            candidate.excerpt_end, candidate.excerpt_sha256):
            fields = candidate.model_dump(exclude={"support_id"})
            if fields != existing.model_dump(exclude={"support_id"}):
                raise ValueError("Rules source metadata changed within a frozen span")
            return existing
    return candidate


def prepare_lookup(execution: RulesExecutionV1, call_id: str,
                   arguments: LookupRulesArguments, *,
                   current_context_refs: tuple[RulesSupportRefV1, ...] = ()) -> RulesLookupPreparedV1:
    """Read/reuse under a prior durable authorization; caller seals before delivery."""
    arguments = LookupRulesArguments.model_validate(arguments)
    return _prepare_authorized_lookup(execution, call_id, arguments.question, current_context_refs)


def prepare_plan_lookup(execution: RulesExecutionV1, call_id: str, question: str, *,
                        current_context_refs: tuple[RulesSupportRefV1, ...] = ()) -> RulesLookupPreparedV1:
    """Read an exact host-selected Plan question, without fake native tool args."""
    if not any(isinstance(e, RulesPlanJevToolAuthorizedV1) and e.call_id == call_id for e in execution.events):
        raise ValueError("Direct Plan Rules read lacks its typed decision operation")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Direct Plan Rules read requires the complete nonblank question")
    return _prepare_authorized_lookup(execution, call_id, question, current_context_refs, plan_reader=True)


def _prepare_authorized_lookup(execution, call_id, raw_question, current_context_refs, *, plan_reader=False):
    _check_scope(execution)
    question = normalized_question(raw_question)
    auths = [e for e in execution.events if isinstance(e, RulesToolAuthorizedV1) and e.call_id == call_id]
    if (len(auths) != 1 or auths[0].normalized_question != question
            or any(isinstance(e, RulesQueryObservedV1) and e.call_id == call_id for e in execution.events)):
        raise ValueError("Rules read lacks a unique unsettled matching authorization")
    present = ref_map(current_context_refs)
    if len(present) > 16 or any(key not in execution.supports
            or execution.supports[key].support_sha256 != digest for key, digest in present.items()):
        raise ValueError("Current Rules context has a foreign or changed support")
    auth = auths[0]
    cached = next((e for e in execution.events if isinstance(e, RulesQueryObservedV1)
        and e.query_id == auth.query_id and e.status in {"evidence", "no_evidence"}), None)
    supports = ()
    status, diagnostic = "no_evidence", None
    if cached is not None:
        status = cached.status
        supports = tuple(execution.supports[ref.support_id].support for ref in cached.support_refs)
    else:
        try:
            packet = (reader.query_plan_rules(execution.scope.corpus_sha256, raw_question) if plan_reader
                else reader.query_rules(execution.scope.corpus_sha256, raw_question, 4))
            bundle = reader.admitted_bundle(execution.scope.corpus_sha256)
            if (packet.get("corpus") != execution.scope.corpus_sha256
                    or packet.get("ruleset_id") != execution.scope.ruleset_id
                    or packet.get("query_id") != auth.query_id
                    or packet.get("normalized_query") != question
                    or packet.get("status") not in {"evidence", "no_evidence"}
                    or not isinstance(packet.get("hits"), list) or len(packet["hits"]) > 4
                    or (packet["status"] == "evidence") != bool(packet["hits"])):
                raise ValueError("Rules reader result differs from its frozen query")
            supports = tuple(_support_for_hit(execution, bundle, hit) for hit in packet["hits"])
            if len({s.unit_id for s in supports}) != len(supports):
                raise ValueError("Rules reader repeated a source unit")
            status = packet["status"]
        except reader.RulesCorpusUnavailable:
            status, diagnostic = "unavailable", "corpus_unavailable"
    new = tuple(s for s in supports if s.support_id not in execution.supports)
    emitted = tuple(s for s in supports if s.support_id not in present)
    refs = tuple(RulesSupportRefV1(support_id=s.support_id, support_sha256=canonical_sha256(s)) for s in supports)
    result = RulesPacketV1(schema="dmb_rules_packet_v1", call_id=call_id, query_id=auth.query_id,
        normalized_question=question, corpus_sha256=execution.scope.corpus_sha256,
        ruleset_id=execution.scope.ruleset_id, status=status, support_refs=refs,
        emitted_support_ids=tuple(s.support_id for s in emitted),
        previous_support_ids=tuple(s.support_id for s in supports if s.support_id in present),
        support_capsules=emitted, diagnostic=diagnostic)
    raw = canonical_bytes(result).decode()
    over_budget = (execution.budget_use.presentation_utf8 + len(raw.encode()) > 64512
        or execution.budget_use.novel_excerpt_utf8 + sum(len(s.excerpt_text.encode()) for s in new) > 16384
        or len(execution.supports) + len(new) > 16)
    if not over_budget:
        prepared = _prepared(execution, auth, raw, status, refs, emitted, new)
        # Include the complete ledger envelope in the budget, not only excerpts.
        data = execution.model_dump(mode="json", by_alias=True)
        data["events"].append(prepared.observation.model_dump(mode="json", by_alias=True))
        data["budget_use"]["presentation_utf8"] += prepared.observation.presentation_utf8
        data["budget_use"]["novel_excerpt_utf8"] += sum(len(s.excerpt_text.encode()) for s in new)
        data["supports"].update({str(s.support_id): {"support": s.model_dump(mode="json", by_alias=True),
            "support_sha256": canonical_sha256(s)} for s in new})
        over_budget = len(canonical_bytes(data)) > execution.scope.budget.ledger_utf8
    if over_budget:
        raw = canonical_bytes(RulesBudgetDiagnosticV1(schema="dmb_rules_budget_diagnostic_v1",
            execution_id=execution.scope.execution_id, call_id=call_id, code="rules_budget_exhausted")).decode()
        prepared = _prepared(execution, auth, raw, "over_budget", (), (), ())
    append_observed_output(execution, prepared.observation, prepared.raw_output, prepared.new_supports)
    return prepared


def _prepared(execution, auth, raw, status, refs, emitted, new):
    return RulesLookupPreparedV1(raw_output=raw, observation=RulesQueryObservedV1(kind="query_observed", event_id=uuid4(),
        sequence=len(execution.events), execution_id=execution.scope.execution_id,
        call_id=auth.call_id, query_id=auth.query_id, packet_sha256=sha256(raw.encode()).hexdigest(),
        presentation_utf8=len(raw.encode()), status=status, support_refs=refs,
        emitted_support_ids=tuple(s.support_id for s in emitted)), new_supports=new)
