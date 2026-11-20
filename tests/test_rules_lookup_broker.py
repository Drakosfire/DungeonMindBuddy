"""Parent packet proof, actual reader counts and context-sensitive deduplication."""
from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.rules_authority_events import empty_execution, RulesExecutionV1
from application_state.agent_conversation.rules_authority_packet import append_observed_output, RulesPacketV1
from application_state.agent_conversation.rules_authority_types import RULES_BUDGET_V1, RulesScopeV1, RulesSupportRefV1
from apps.live_control_server.services import rules_lookup as reader
from apps.live_control_server.services import rules_lookup_broker as broker


def execution():
    return empty_execution(RulesScopeV1(schema="dmb_rules_scope_v1", execution_id=uuid4(),
        world_id="elderwyld", conversation_id=uuid4(), turn_id=uuid4(), product_attempt=1,
        ruleset_id=broker.RULESET, corpus_sha256=reader.SEED_DIGEST, authorization_id=uuid4(),
        capability_policy_sha256="b" * 64, budget=RULES_BUDGET_V1))


def args(question="Can I end my move in an occupied space?"):
    return broker.LookupRulesArguments(question=question, ruleset_id=broker.RULESET)


def authorize(owner, call_id, arguments):
    event = broker.prepare_authorization(owner, call_id, arguments)
    data = owner.model_dump(mode="json", by_alias=True)
    data["events"].append(event.model_dump(mode="json", by_alias=True))
    data["budget_use"]["calls"] += 1
    data["budget_use"]["distinct_questions"] = len({e["query_id"] for e in data["events"] if e["kind"] == "tool_authorized"})
    return RulesExecutionV1.model_validate_json(json.dumps(data))


def lookup(owner, call_id="call:1", arguments=None, present=()):
    arguments = arguments or args()
    owner = authorize(owner, call_id, arguments)
    result = broker.prepare_lookup(owner, call_id, arguments, current_context_refs=present)
    updated = append_observed_output(owner, result.observation, result.raw_output, result.new_supports)
    return updated, result


def packet(result):
    return RulesPacketV1.model_validate_json(result.raw_output)


def count_reader(monkeypatch):
    calls = []
    actual = reader.query_rules
    def query(*a, **kw):
        calls.append((a, kw))
        return actual(*a, **kw)
    monkeypatch.setattr(reader, "query_rules", query)
    return calls


def test_real_admitted_source_produces_exact_sealed_packet():
    owner, result = lookup(execution())
    value = packet(result)
    assert value.status == "evidence" and len(value.support_capsules) == 1
    support = value.support_capsules[0]
    unit = reader.admitted_bundle(reader.SEED_DIGEST).units[0]
    assert support.excerpt_text == unit.text[support.excerpt_start:support.excerpt_end]
    assert support.full_text_sha256 == sha256(unit.text.encode()).hexdigest()
    assert owner.budget_use.calls == 1
    assert owner.budget_use.presentation_utf8 == len(result.raw_output.encode())
    assert owner.budget_use.novel_excerpt_utf8 == len(support.excerpt_text.encode())


def test_equivalent_query_reuses_read_and_support_but_counts_presentation(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution())
    present = packet(first).support_refs
    owner, second = lookup(owner, "call:2", args("  CAN I END MY MOVE IN AN OCCUPIED SPACE?  "), present)
    assert len(calls) == 1
    assert second.new_supports == ()
    assert packet(second).support_refs == present
    assert packet(second).support_capsules == ()
    assert packet(second).previous_support_ids == tuple(ref.support_id for ref in present)
    assert owner.budget_use.calls == 2 and owner.budget_use.distinct_questions == 1
    assert owner.budget_use.presentation_utf8 == sum(len(r.raw_output.encode()) for r in (first, second))


def test_compaction_rehydrates_exact_text_without_read_or_novel_support(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution())
    owner, second = lookup(owner, "call:2", present=packet(first).support_refs)
    owner, third = lookup(owner, "call:3")
    assert len(calls) == 1 and third.new_supports == ()
    assert packet(third).support_capsules == packet(first).support_capsules
    assert packet(second).support_capsules == ()
    assert packet(third).previous_support_ids == ()
    assert owner.budget_use.novel_excerpt_utf8 == len(packet(first).support_capsules[0].excerpt_text.encode())


def test_overlapping_queries_reuse_span_identity(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution())
    owner, second = lookup(owner, "call:2", args("What is an occupied space?"))
    assert len(calls) == 2
    assert packet(second).support_refs == packet(first).support_refs
    assert second.new_supports == () and len(owner.supports) == 1


def test_successful_empty_result_is_cached(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution(), arguments=args("xyzzyquux"))
    owner, second = lookup(owner, "call:2", args(" XYZ ZY ".replace(" ", "") + "quux"))
    assert packet(first).status == packet(second).status == "no_evidence"
    assert len(calls) == 1 and not owner.supports


def test_unavailable_does_not_become_a_successful_cache(monkeypatch):
    calls = []
    actual = reader.query_rules
    def query(*a, **kw):
        calls.append(1)
        if len(calls) == 1:
            raise reader.RulesCorpusUnavailable
        return actual(*a, **kw)
    monkeypatch.setattr(reader, "query_rules", query)
    owner, first = lookup(execution())
    owner, second = lookup(owner, "call:2")
    assert packet(first).status == "unavailable" and packet(first).diagnostic == "corpus_unavailable"
    assert packet(second).status == "evidence" and len(calls) == 2


@pytest.mark.parametrize("value", ["", "  ", "a" * 801, None, 42])
def test_invalid_questions_do_not_gain_read_authority(value):
    with pytest.raises(ValidationError):
        args(value)


def test_ruleset_and_extra_selectors_are_closed():
    with pytest.raises(ValidationError):
        broker.LookupRulesArguments(question="occupancy", ruleset_id="private_phb")
    with pytest.raises(ValidationError):
        broker.LookupRulesArguments(question="occupancy", ruleset_id=broker.RULESET, path="/private")


def test_read_requires_matching_unique_durable_authorization(monkeypatch):
    calls = count_reader(monkeypatch)
    owner = execution()
    with pytest.raises(ValueError, match="authorization"):
        broker.prepare_lookup(owner, "call:1", args())
    owner = authorize(owner, "call:1", args())
    with pytest.raises(ValueError, match="authorization"):
        broker.prepare_lookup(owner, "call:1", args("changed question"))
    owner, result = lookup(execution())
    with pytest.raises(ValueError, match="authorization"):
        broker.prepare_lookup(owner, "call:1", args())
    assert len(calls) == 1


@pytest.mark.parametrize("change", [
    lambda hit: hit.update(excerpt="forged"),
    lambda hit: hit.update(source_title="forged"),
    lambda hit: hit.update(excerpt_start=True),
    lambda hit: hit.update(text_sha256="c" * 64),
    lambda hit: hit.update(excerpt_complete=1),
])
def test_changed_r1_hit_proof_is_rejected(monkeypatch, change):
    actual = reader.query_rules
    def query(*a, **kw):
        value = actual(*a, **kw)
        change(value["hits"][0])
        return value
    monkeypatch.setattr(reader, "query_rules", query)
    with pytest.raises(ValueError, match="proof"):
        lookup(execution())


def test_foreign_context_reference_is_not_used_as_a_dedup_hint(monkeypatch):
    calls = count_reader(monkeypatch)
    owner = authorize(execution(), "call:1", args())
    with pytest.raises(ValueError, match="foreign"):
        broker.prepare_lookup(owner, "call:1", args(), current_context_refs=(
            RulesSupportRefV1(support_id=uuid4(), support_sha256="a" * 64),))
    assert calls == []


def test_cache_never_crosses_attempts(monkeypatch):
    calls = count_reader(monkeypatch)
    first, result1 = lookup(execution())
    second, result2 = lookup(execution())
    assert len(calls) == 2
    assert packet(result1).support_refs != packet(result2).support_refs


def test_six_calls_are_hard_limit_even_when_same_query_is_cached(monkeypatch):
    calls = count_reader(monkeypatch)
    owner = execution()
    for i in range(6):
        owner, result = lookup(owner, f"call:{i}")
    with pytest.raises(ValueError, match="budget"):
        authorize(owner, "call:7", args())
    assert len(calls) == 1 and owner.budget_use.calls == 6


def test_near_presentation_limit_uses_reserved_terminal_diagnostic(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution())
    padded = first.raw_output + " " * (64500 - len(first.raw_output.encode()))
    data = owner.model_dump(mode="json", by_alias=True)
    data["events"][-1].update(packet_sha256=sha256(padded.encode()).hexdigest(), presentation_utf8=64500)
    data["budget_use"]["presentation_utf8"] = 64500
    owner = RulesExecutionV1.model_validate_json(json.dumps(data))
    owner, terminal = lookup(owner, "call:2")
    diagnostic = json.loads(terminal.raw_output)
    assert diagnostic["schema"] == "dmb_rules_budget_diagnostic_v1"
    assert terminal.observation.status == "over_budget" and terminal.new_supports == ()
    assert terminal.observation.support_refs == () and len(terminal.raw_output.encode()) <= 1024
    assert owner.budget_use.presentation_utf8 == 64500 + len(terminal.raw_output.encode())
    with pytest.raises(ValueError, match="budget"):
        authorize(owner, "call:3", args())
    assert len(calls) == 1


def test_cached_handles_alone_cannot_claim_actual_source_exposure():
    from application_state.agent_conversation.rules_authority_events import RulesProviderAuthorizedV1, RulesOutputRefV1
    from application_state.agent_conversation.rules_authority_input import verify_prepared_input
    owner, first = lookup(execution())
    owner, second = lookup(owner, "call:2", present=packet(first).support_refs)
    def proof(results, declared):
        items = []
        refs = []
        for result in results:
            cid = result.observation.call_id
            items.extend([dict(type="function_call", call_id=cid, name="lookup_rules",
                arguments=args().model_dump_json()), dict(type="function_call_output", call_id=cid, output=result.raw_output)])
            refs.append(RulesOutputRefV1(call_id=cid, packet_sha256=result.observation.packet_sha256))
        raw = json.dumps(dict(input=items))
        event = RulesProviderAuthorizedV1(kind="provider_authorized", event_id=uuid4(),
            sequence=len(owner.events), execution_id=owner.scope.execution_id, provider_attempt_id=uuid4(),
            request_envelope_sha256=sha256(raw.encode()).hexdigest(), matched_outputs=tuple(refs), declared_support_refs=declared)
        verify_prepared_input(owner, event, raw)
    # Exact original text retained in the actual request establishes exposure.
    proof((first, second), packet(first).support_refs)
    # A cached handle without that text establishes no source exposure.
    proof((second,), ())
    with pytest.raises(ValueError, match="support declarations"):
        proof((second,), packet(first).support_refs)


def test_frozen_scope_and_call_identity_are_required_before_reads(monkeypatch):
    calls = count_reader(monkeypatch)
    owner = execution()
    data = owner.model_dump(mode="json", by_alias=True)
    data["scope"]["corpus_sha256"] = "a" * 64
    foreign = RulesExecutionV1.model_validate_json(json.dumps(data))
    with pytest.raises(ValueError, match="admitted active scope"):
        broker.prepare_authorization(foreign, "call:1", args())
    owner = authorize(owner, "call:1", args())
    with pytest.raises(ValueError):
        broker.prepare_authorization(owner, "call:1", args())
    assert calls == []


def test_nfkc_question_identity_reuses_lookup_without_ascii_only_assumption(monkeypatch):
    calls = count_reader(monkeypatch)
    owner, first = lookup(execution(), arguments=args("Occupied space?"))
    owner, second = lookup(owner, "call:2", args("Ｏｃｃｕｐｉｅｄ\u3000ｓｐａｃｅ？"))
    assert len(calls) == 1 and owner.budget_use.distinct_questions == 1
    assert packet(first).support_refs == packet(second).support_refs
