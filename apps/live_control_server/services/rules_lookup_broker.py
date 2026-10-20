"""Parent-only Rules lookup kernel; no tool registration or dispatch authority.

The caller persists authorization before reading and observation before delivery.
Current-context references must come from the parent's actual prepared input.
Handles alone never grant inclusion authority in the producing request.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from application_state.agent_conversation.rules_authority_events import (
    RulesExecutionV1, RulesQueryObservedV1, RulesToolAuthorizedV1,
    normalized_question, query_identity, ref_map,
)
from application_state.agent_conversation.rules_authority_packet import (
    RulesBudgetDiagnosticV1, RulesPacketV1, append_observed_output,
)
from application_state.agent_conversation.rules_authority_types import (
    ClosedRulesModel, RulesSupportRefV1, RulesSupportV1, canonical_bytes, canonical_sha256,
)
from . import rules_lookup as reader

RULESET = "dnd_2024_srd_5_2_1"


class LookupRulesArguments(ClosedRulesModel):
    question: Annotated[str, Field(min_length=1, max_length=800)]
    ruleset_id: Literal["dnd_2024_srd_5_2_1"]

    @field_validator("question")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Enter a rules question")
        return value


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
    # Exercise the same closed whole-ledger invariants as the locked store.
    data = execution.model_dump(mode="json", by_alias=True)
    data["events"].append(event.model_dump(mode="json", by_alias=True))
    data["budget_use"]["calls"] += 1
    data["budget_use"]["distinct_questions"] = len({
        e.query_id for e in (*execution.events, event) if isinstance(e, RulesToolAuthorizedV1)
    })
    RulesExecutionV1.model_validate_json(json.dumps(data))
    return event


@dataclass(frozen=True)
class PreparedRulesLookup:
    raw_output: str
    observation: RulesQueryObservedV1
    new_supports: tuple[RulesSupportV1, ...]


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
                   current_context_refs: tuple[RulesSupportRefV1, ...] = ()) -> PreparedRulesLookup:
    """Read/reuse under a prior durable authorization; caller seals before delivery."""
    _check_scope(execution)
    arguments = LookupRulesArguments.model_validate(arguments)
    question = normalized_question(arguments.question)
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
            packet = reader.query_rules(execution.scope.corpus_sha256, arguments.question, 4)
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
    return PreparedRulesLookup(raw, RulesQueryObservedV1(kind="query_observed", event_id=uuid4(),
        sequence=len(execution.events), execution_id=execution.scope.execution_id,
        call_id=auth.call_id, query_id=auth.query_id, packet_sha256=sha256(raw.encode()).hexdigest(),
        presentation_utf8=len(raw.encode()), status=status, support_refs=refs,
        emitted_support_ids=tuple(s.support_id for s in emitted)), new)
