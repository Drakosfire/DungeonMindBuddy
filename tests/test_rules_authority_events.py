"""Rules source exposure is causal, bounded and distinct from lookup handles."""

from hashlib import sha256
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.rules_authority_events import (
    RulesExecutionV1,
    RulesProviderAuthorizedV1,
    RulesQueryObservedV1,
    empty_execution,
    normalized_question,
    query_identity,
)
from application_state.agent_conversation.rules_authority_input import (
    verify_prepared_input,
)
from application_state.agent_conversation.rules_authority_packet import (
    verify_output_proof,
)
from application_state.agent_conversation.rules_authority_types import (
    RULES_BUDGET_V1,
    RulesScopeV1,
    RulesSupportV1,
    canonical_bytes,
    canonical_sha256,
)


def hashed(text):
    return sha256(text.encode("utf-8")).hexdigest()


def scope():
    return RulesScopeV1(
        schema="dmb_rules_scope_v1",
        execution_id=uuid4(),
        world_id="elderwyld",
        conversation_id=uuid4(),
        turn_id=uuid4(),
        product_attempt=1,
        ruleset_id="srd_2024",
        corpus_sha256="a" * 64,
        authorization_id=uuid4(),
        capability_policy_sha256="b" * 64,
        budget=RULES_BUDGET_V1,
    )


def capsule():
    text = "A tiny 🐉 cannot end its move here."
    return RulesSupportV1(
        schema="dmb_rules_support_v1",
        support_id=uuid4(),
        corpus_sha256="a" * 64,
        ruleset_id="srd_2024",
        unit_id="c" * 64,
        full_text_sha256=hashed(text),
        excerpt_start=0,
        excerpt_end=len(text),
        excerpt_text=text,
        excerpt_sha256=hashed(text),
        source_title="SRD",
        section="Occupancy",
        source_uri="https://example.invalid/srd.pdf",
        source_sha256="d" * 64,
        page_fingerprint="e" * 64,
        pdf_page_index=13,
        printed_page=14,
    )


def event(owner, sequence, kind, **fields):
    return dict(
        event_id=str(uuid4()),
        execution_id=str(owner.execution_id),
        sequence=sequence,
        kind=kind,
        **fields,
    )


def fixture():
    owner = scope()
    unit = capsule()
    digest = canonical_sha256(unit)
    ref = dict(support_id=str(unit.support_id), support_sha256=digest)
    query = query_identity(owner, "Occupied space?")
    raw = json.dumps(
        dict(
            schema="dmb_rules_packet_v1",
            call_id="call:1",
            query_id=query,
            normalized_question="occupied space?",
            corpus_sha256=owner.corpus_sha256,
            ruleset_id=owner.ruleset_id,
            status="evidence",
            support_refs=[ref],
            emitted_support_ids=[str(unit.support_id)],
            previous_support_ids=[],
            support_capsules=[unit.model_dump(mode="json", by_alias=True)],
            diagnostic=None,
        ),
        ensure_ascii=False,
        indent=2,
    )
    observed = event(
        owner,
        1,
        "query_observed",
        call_id="call:1",
        query_id=query,
        packet_sha256=hashed(raw),
        presentation_utf8=len(raw.encode()),
        status="evidence",
        support_refs=[ref],
        emitted_support_ids=[str(unit.support_id)],
    )
    auth = event(
        owner,
        0,
        "tool_authorized",
        call_id="call:1",
        query_id=query,
        normalized_question="occupied space?",
        packet_limit=4,
    )
    ledger = empty_execution(owner).model_dump(mode="json", by_alias=True)
    ledger.update(
        supports={
            str(unit.support_id): dict(
                support=unit.model_dump(mode="json", by_alias=True),
                support_sha256=digest,
            )
        },
        events=[auth, observed],
        budget_use=dict(
            calls=1,
            distinct_questions=1,
            novel_excerpt_utf8=len(unit.excerpt_text.encode()),
            presentation_utf8=len(raw.encode()),
            provider_requests=0,
        ),
    )
    return owner, unit, raw, ledger, ref


def parse(raw):
    return RulesExecutionV1.model_validate_json(json.dumps(raw, ensure_ascii=False))


def add_provider(owner, ledger, ref):
    producer = str(uuid4())
    envelope = "f" * 64
    outputs = [
        dict(call_id="call:1", packet_sha256=ledger["events"][1]["packet_sha256"])
    ]
    ledger["events"].append(
        event(
            owner,
            2,
            "provider_authorized",
            provider_attempt_id=producer,
            request_envelope_sha256=envelope,
            matched_outputs=outputs,
            declared_support_refs=[ref],
        )
    )
    ledger["events"].append(
        event(
            owner,
            3,
            "provider_included",
            provider_attempt_id=producer,
            request_envelope_sha256=envelope,
            matched_outputs=outputs,
            support_refs=[ref],
        )
    )
    ledger["events"].append(
        event(
            owner,
            4,
            "provider_outcome",
            provider_attempt_id=producer,
            request_envelope_sha256=envelope,
            status="answered",
        )
    )
    ledger["budget_use"]["provider_requests"] = 1
    return producer


def test_normalized_duplicate_queries_share_identity_but_not_calls():
    owner, unit, raw, ledger, ref = fixture()
    assert query_identity(owner, "  OCCUPIED\u3000SPACE? ") == query_identity(
        owner, "occupied space?"
    )
    assert normalized_question("Ｆoo  BAR") == "foo bar"
    auth = dict(
        ledger["events"][0], event_id=str(uuid4()), sequence=2, call_id="call:2"
    )
    result = dict(
        ledger["events"][1],
        event_id=str(uuid4()),
        sequence=3,
        call_id="call:2",
        emitted_support_ids=[],
    )
    ledger["events"] += [auth, result]
    ledger["budget_use"].update(calls=2, presentation_utf8=2 * len(raw.encode()))
    parsed = parse(ledger)
    assert parsed.budget_use.distinct_questions == 1
    assert parsed.budget_use.novel_excerpt_utf8 == len(unit.excerpt_text.encode())
    assert len(parsed.supports) == 1


def test_raw_proof_seals_actual_whitespace_and_utf8_not_reserialized_packet():
    owner, unit, raw, ledger, _ = fixture()
    parsed = parse(ledger)
    observed = parsed.events[1]
    verify_output_proof(owner, observed, parsed.supports, raw)
    assert observed.presentation_utf8 > len(raw)
    compact = json.dumps(json.loads(raw), ensure_ascii=False, separators=(",", ":"))
    with pytest.raises(ValueError, match="raw digest"):
        verify_output_proof(owner, observed, parsed.supports, compact)
    assert unit.excerpt_text not in canonical_bytes(observed).decode()


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(corpus_sha256="b" * 64),
        lambda d: d.update(call_id="other"),
        lambda d: d["support_capsules"][0].update(excerpt_text="forged"),
        lambda d: d.update(support_capsules=[]),
        lambda d: d.update(previous_support_ids=d["emitted_support_ids"]),
        lambda d: d.update(path="/private/source.pdf"),
    ],
)
def test_raw_proof_rejects_forged_scope_source_and_packet_fields(change):
    owner, unit, raw, ledger, _ = fixture()
    parsed = parse(ledger)
    packet = json.loads(raw)
    change(packet)
    changed = json.dumps(packet, ensure_ascii=False)
    obs = parsed.events[1].model_dump(mode="json", by_alias=True)
    obs.update(packet_sha256=hashed(changed), presentation_utf8=len(changed.encode()))
    observed = RulesQueryObservedV1.model_validate_json(json.dumps(obs))
    with pytest.raises(ValueError):
        verify_output_proof(owner, observed, parsed.supports, changed)


def test_duplicate_json_keys_rejected_even_with_matching_raw_hash():
    owner, unit, raw, ledger, _ = fixture()
    parsed = parse(ledger)
    raw = raw.replace('"call_id": "call:1"', '"call_id": "forged", "call_id": "call:1"')
    obs = parsed.events[1].model_dump(mode="json", by_alias=True)
    obs.update(packet_sha256=hashed(raw), presentation_utf8=len(raw.encode()))
    with pytest.raises(ValueError, match="duplicate JSON keys"):
        verify_output_proof(
            owner,
            RulesQueryObservedV1.model_validate_json(json.dumps(obs)),
            parsed.supports,
            raw,
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["events"][1].update(sequence=0),
        lambda d: d["events"][1].update(event_id=d["events"][0]["event_id"]),
        lambda d: d["events"][1].update(execution_id=str(uuid4())),
        lambda d: d["events"][1].update(call_id="other"),
        lambda d: d["events"][1].update(query_id="b" * 64),
        lambda d: d["events"][1].update(emitted_support_ids=[]),
        lambda d: d["events"][1]["support_refs"][0].update(support_sha256="b" * 64),
        lambda d: d["budget_use"].update(calls=0),
        lambda d: d["budget_use"].update(novel_excerpt_utf8=0),
        lambda d: d.update(state="unused"),
    ],
)
def test_ledger_rejects_uncausal_or_unaccounted_evidence(change):
    *_, ledger, ref = fixture()
    change(ledger)
    with pytest.raises(ValidationError):
        parse(ledger)


def test_producing_input_requires_matching_output_and_envelope():
    owner, unit, raw, ledger, ref = fixture()
    add_provider(owner, ledger, ref)
    assert parse(ledger).budget_use.provider_requests == 1
    ledger["events"][3]["request_envelope_sha256"] = "b" * 64
    with pytest.raises(ValidationError, match="matching current provider"):
        parse(ledger)


def test_cached_handle_is_not_actual_source_exposure():
    owner, unit, raw, ledger, ref = fixture()
    auth = dict(
        ledger["events"][0], event_id=str(uuid4()), sequence=2, call_id="call:2"
    )
    result = dict(
        ledger["events"][1],
        event_id=str(uuid4()),
        sequence=3,
        call_id="call:2",
        emitted_support_ids=[],
    )
    ledger["events"] += [auth, result]
    ledger["budget_use"].update(calls=2, presentation_utf8=2 * len(raw.encode()))
    producer = str(uuid4())
    output = [dict(call_id="call:2", packet_sha256=result["packet_sha256"])]
    ledger["events"] += [
        event(
            owner,
            4,
            "provider_authorized",
            provider_attempt_id=producer,
            request_envelope_sha256="f" * 64,
            matched_outputs=output,
            declared_support_refs=[ref],
        ),
        event(
            owner,
            5,
            "provider_included",
            provider_attempt_id=producer,
            request_envelope_sha256="f" * 64,
            matched_outputs=output,
            support_refs=[ref],
        ),
    ]
    ledger["budget_use"]["provider_requests"] = 1
    with pytest.raises(ValidationError, match="handles or cached"):
        parse(ledger)


def test_terminal_diagnostic_uses_reserved_bytes_without_source_authority():
    owner = scope()
    query = query_identity(owner, "occupied?")
    raw = json.dumps(
        dict(
            schema="dmb_rules_budget_diagnostic_v1",
            execution_id=str(owner.execution_id),
            call_id="last",
            code="rules_budget_exhausted",
        )
    )
    observed = RulesQueryObservedV1.model_validate_json(
        json.dumps(
            event(
                owner,
                1,
                "query_observed",
                call_id="last",
                query_id=query,
                packet_sha256=hashed(raw),
                presentation_utf8=len(raw.encode()),
                status="over_budget",
                support_refs=[],
                emitted_support_ids=[],
            )
        )
    )
    verify_output_proof(owner, observed, {}, raw)
    ledger = empty_execution(owner).model_dump(mode="json", by_alias=True)
    ledger.update(
        events=[
            event(
                owner,
                0,
                "tool_authorized",
                call_id="last",
                query_id=query,
                normalized_question="occupied?",
                packet_limit=4,
            ),
            observed.model_dump(mode="json", by_alias=True),
        ],
        budget_use=dict(
            calls=1,
            distinct_questions=1,
            novel_excerpt_utf8=0,
            presentation_utf8=len(raw.encode()),
            provider_requests=0,
        ),
    )
    assert parse(ledger).budget_use.presentation_utf8 == len(raw.encode())
    ledger["events"].append(
        event(
            owner,
            2,
            "tool_authorized",
            call_id="again",
            query_id=query,
            normalized_question="occupied?",
            packet_limit=4,
        )
    )
    ledger["budget_use"]["calls"] = 2
    with pytest.raises(ValidationError, match="exhausted"):
        parse(ledger)


def test_observed_append_is_exactly_idempotent_and_cannot_replace_source():
    from application_state.agent_conversation.rules_authority_packet import (
        append_observed_output,
    )

    owner, unit, raw, ledger, _ = fixture()
    expected = parse(ledger)
    obs = expected.events[1]
    initial = dict(
        ledger,
        supports={},
        events=ledger["events"][:1],
        budget_use=dict(
            ledger["budget_use"], novel_excerpt_utf8=0, presentation_utf8=0
        ),
    )
    execution = append_observed_output(parse(initial), obs, raw, (unit,))
    assert execution == expected
    assert append_observed_output(execution, obs, raw, (unit,)) is execution
    changed = obs.model_dump(mode="json", by_alias=True)
    changed["presentation_utf8"] += 1
    with pytest.raises(ValueError):
        append_observed_output(
            execution,
            RulesQueryObservedV1.model_validate_json(json.dumps(changed)),
            raw,
        )


def accepted_fixture():
    owner, unit, raw, ledger, ref = fixture()
    producer = add_provider(owner, ledger, ref)
    text = "The cited source prohibits this move."
    composition = dict(
        schema="dmb_answer_composition_v1",
        base_disposition="absent",
        ordered_refs=[dict(domain="rules", segment_index=0)],
        rules_segments=[
            dict(
                kind="rules_claim", claim_id="occupancy", text=text, support_refs=[ref]
            )
        ],
        assistant_text_sha256=hashed(text),
    )
    digest = canonical_sha256(composition)
    ledger.update(
        state="accepted",
        composition=composition,
        rules_completion=dict(
            schema="dmb_rules_completion_v1",
            execution_id=str(owner.execution_id),
            producing_provider_attempt_id=producer,
            request_envelope_sha256="f" * 64,
            composition_sha256=digest,
            claim_support_refs={"occupancy": [ref]},
            approved_support_refs=[ref],
        ),
    )
    ledger["events"].append(
        event(
            owner,
            5,
            "completion_bound",
            producing_provider_attempt_id=producer,
            composition_sha256=digest,
            assistant_text_sha256=hashed(text),
            accepted_binding_sha256="e" * 64,
            claim_support_refs={"occupancy": [ref]},
            accepted_turn_revision=3,
        )
    )
    return ledger


def test_accepted_rules_answer_has_acknowledged_exact_producing_input():
    ledger = accepted_fixture()
    assert parse(ledger).state == "accepted"


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["events"][4].update(status="unknown"),
        lambda d: d["rules_completion"].update(
            producing_provider_attempt_id=str(uuid4())
        ),
        lambda d: d["events"][5].update(assistant_text_sha256="b" * 64),
        lambda d: d["rules_completion"].update(approved_support_refs=[]),
        lambda d: d["events"][3].update(support_refs=[]),
        lambda d: d["rules_completion"].update(request_envelope_sha256="b" * 64),
        lambda d: d["events"].append(
            dict(d["events"][4], sequence=6, event_id=str(uuid4()))
        ),
    ],
)
def test_accepted_answer_rejects_unknown_producer_missing_exposure_and_mutation(change):
    ledger = accepted_fixture()
    change(ledger)
    with pytest.raises(ValidationError):
        parse(ledger)


def test_successful_query_cannot_be_reread_into_a_different_result():
    owner, unit, raw, ledger, ref = fixture()
    auth = dict(
        ledger["events"][0], event_id=str(uuid4()), sequence=2, call_id="call:2"
    )
    result = dict(
        ledger["events"][1],
        event_id=str(uuid4()),
        sequence=3,
        call_id="call:2",
        status="no_evidence",
        support_refs=[],
        emitted_support_ids=[],
    )
    ledger["events"] += [auth, result]
    ledger["budget_use"].update(calls=2, presentation_utf8=2 * len(raw.encode()))
    with pytest.raises(ValidationError, match="reuse its frozen result"):
        parse(ledger)


@pytest.mark.parametrize("limit", [4.0, True, "4"])
def test_tool_admission_requires_exact_integer_hit_limit(limit):
    owner, unit, raw, ledger, ref = fixture()
    ledger["events"][0]["packet_limit"] = limit
    with pytest.raises(ValidationError):
        parse(ledger)


def test_presentation_reserve_cannot_be_spent_on_normal_output():
    owner, unit, raw, ledger, ref = fixture()
    ledger["events"][1]["presentation_utf8"] = 64513
    ledger["budget_use"]["presentation_utf8"] = 64513
    with pytest.raises(ValidationError, match="reserved diagnostic"):
        parse(ledger)


def test_seventh_call_is_not_admitted_even_when_questions_repeat():
    owner, unit, raw, ledger, ref = fixture()
    for index in range(2, 8):
        ledger["events"] += [
            dict(
                ledger["events"][0],
                event_id=str(uuid4()),
                sequence=2 * (index - 1),
                call_id=f"call:{index}",
            ),
            dict(
                ledger["events"][1],
                event_id=str(uuid4()),
                sequence=2 * (index - 1) + 1,
                call_id=f"call:{index}",
                emitted_support_ids=[],
            ),
        ]
    ledger["budget_use"].update(calls=6, presentation_utf8=7 * len(raw.encode()))
    with pytest.raises(ValidationError, match="exhausted"):
        parse(ledger)


def prepared(mode="responses"):
    owner, unit, raw, ledger, ref = fixture()
    execution = parse(ledger)
    args = json.dumps(dict(question="Occupied space?", ruleset_id=owner.ruleset_id))
    if mode == "responses":
        body = dict(
            model="test",
            input=[
                dict(
                    type="function_call",
                    call_id="call:1",
                    name="lookup_rules",
                    arguments=args,
                ),
                dict(type="function_call_output", call_id="call:1", output=raw),
            ],
        )
    else:
        body = dict(
            model="test",
            messages=[
                dict(
                    role="assistant",
                    tool_calls=[
                        dict(
                            id="call:1",
                            type="function",
                            function=dict(name="lookup_rules", arguments=args),
                        )
                    ],
                ),
                dict(role="tool", tool_call_id="call:1", content=raw),
            ],
        )
    return owner, execution, body, raw, ref


def proof(owner, body, raw, ref):
    encoded = json.dumps(body, ensure_ascii=False, indent=2)
    auth = RulesProviderAuthorizedV1.model_validate_json(
        json.dumps(
            event(
                owner,
                2,
                "provider_authorized",
                provider_attempt_id=str(uuid4()),
                request_envelope_sha256=sha256(encoded.encode()).hexdigest(),
                matched_outputs=[
                    dict(
                        call_id="call:1", packet_sha256=sha256(raw.encode()).hexdigest()
                    )
                ],
                declared_support_refs=[ref],
            )
        )
    )
    return encoded, auth


@pytest.mark.parametrize("mode", ["responses", "chat"])
def test_both_actual_input_formats_bind_exact_parent_output_and_capsules(mode):
    owner, execution, body, raw, ref = prepared(mode)
    encoded, auth = proof(owner, body, raw, ref)
    verify_prepared_input(execution, auth, encoded)
    with pytest.raises(ValueError, match="serialized request"):
        verify_prepared_input(execution, auth, encoded + " ")


@pytest.mark.parametrize(
    "change",
    [
        lambda b: b["input"][0].update(name="another_tool"),
        lambda b: b["input"][0].update(
            arguments=json.dumps(dict(question="Different?", ruleset_id="srd_2024"))
        ),
        lambda b: b["input"][1].update(output="forged"),
        lambda b: b["input"][1].update(call_id="unknown"),
        lambda b: b["input"].append(dict(b["input"][0])),
        lambda b: b["input"].append(dict(b["input"][1])),
        lambda b: b.update(messages=[]),
        lambda b: b.update(input=[dict(role="user", content=b["input"][1]["output"])]),
    ],
)
def test_unknown_unmatched_forged_or_merely_quoted_results_cannot_authorize_sources(
    change,
):
    owner, execution, body, raw, ref = prepared()
    change(body)
    encoded, auth = proof(owner, body, raw, ref)
    with pytest.raises(ValueError):
        verify_prepared_input(execution, auth, encoded)


def test_fabricated_declared_sources_and_omitted_actual_sources_are_rejected():
    owner, execution, body, raw, ref = prepared()
    encoded, auth = proof(owner, body, raw, ref)
    fields = auth.model_dump(mode="python", by_alias=True)
    fields["declared_support_refs"] = ()
    with pytest.raises(ValueError, match="actual exposed"):
        verify_prepared_input(execution, RulesProviderAuthorizedV1(**fields), encoded)


def test_cached_query_can_retire_with_one_reserved_budget_diagnostic():
    owner, unit, raw, ledger, ref = fixture()
    raw = json.dumps(
        dict(
            schema="dmb_rules_budget_diagnostic_v1",
            execution_id=str(owner.execution_id),
            call_id="last",
            code="rules_budget_exhausted",
        )
    )
    ledger["events"] += [
        dict(ledger["events"][0], event_id=str(uuid4()), sequence=2, call_id="last"),
        event(
            owner,
            3,
            "query_observed",
            call_id="last",
            query_id=ledger["events"][0]["query_id"],
            packet_sha256=hashed(raw),
            presentation_utf8=len(raw.encode()),
            status="over_budget",
            support_refs=[],
            emitted_support_ids=[],
        ),
    ]
    ledger["budget_use"]["calls"] = 2
    ledger["budget_use"]["presentation_utf8"] += len(raw.encode())
    assert parse(ledger).budget_use.calls == 2
