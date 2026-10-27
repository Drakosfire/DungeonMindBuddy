"""Finite current writer syntax, independent of host evidence acceptance."""

from copy import deepcopy
import json
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator, ValidationError
from generationengine.utils.schema_utils import make_schema_strict
from application_state.agent_conversation.plan_writer_output_schema import (
    output_format,
    output_schema,
)
from application_state.agent_conversation.rules_authority_plan_packet import (
    PlanRulesEvidenceFrameV1,
)
from application_state.agent_conversation.surface_evidence_answer import PLAN_POLICY as SELECTOR_POLICY


def frame():
    return {
        "answer_policy": SELECTOR_POLICY,
        "graph_records": [{"kind": "assertion", "target_id": "assertion:pond"}],
        "opened_passages": [{"passage_handle": "p-current"}],
        "committed_plan_blocks": [
            {"selection_id": "a-current", "text": "Saved preparation."}
        ],
        "session_evidence": [
            {
                "sources": [
                    {"text_blocks": [{"selection_id": "a-note", "text": "Saved note."}]}
                ]
            }
        ],
        "native_source_sections": {"sections": [{"section_handle": "n-current"}]},
    }


def rules(*, lookup=False, support=False):
    return PlanRulesEvidenceFrameV1.model_validate_json(
        json.dumps(
            {
                "schema": "dmb_plan_rules_evidence_v1",
                "ruleset": "synthetic",
                "lookups": [
                    {
                        "lookup": 0,
                        "status": "evidence" if support else "no_evidence",
                        "diagnostic": None,
                    }
                ]
                if lookup
                else [],
                "supports": [
                    {
                        "support_id": str(uuid4()),
                        "source_title": "Synthetic rules",
                        "section": "Travel",
                        "source_uri": "https://example.invalid/rules",
                        "printed_page": None,
                        "excerpt_text": "Synthetic rule.",
                    }
                ]
                if support
                else [],
            }
        )
    )


def answer(segment):
    return {
        "schema": SELECTOR_POLICY,
        "answer_segments": [segment],
        "limitations": [],
        "requested_detail_gaps": [],
    }


@pytest.mark.parametrize(
    "segment",
    [
        {
            "kind": "source_passage_claim",
            "text": "A source claim.",
            "passage_handles": [],
        },
        {
            "kind": "source_passage_claim",
            "text": "A source claim.",
            "passage_handles": ["p-stale"],
        },
        {
            "kind": "native_source_claim",
            "text": "A source claim.",
            "section_handles": [],
        },
        {
            "kind": "native_source_claim",
            "text": "A source claim.",
            "section_handles": ["n-stale"],
        },
        {"kind": "authored_excerpt", "selection_id": "a-stale"},
        {
            "kind": "graph_claim",
            "claim_id": "one",
            "text": "A claim.",
            "target_kind": "assertion",
            "target_id": "assertion:stale",
            "passage_handles": [],
        },
        {"kind": "proposal", "label": "played_fact", "text": "A suggestion."},
    ],
)
def test_empty_or_stale_evidence_and_invented_shapes_are_not_output_options(segment):
    with pytest.raises(ValidationError):
        Draft202012Validator(output_schema(frame(), rules())).validate(answer(segment))


def test_graph_without_opened_passages_remains_legal_and_unopened():
    f = frame()
    f["opened_passages"] = []
    candidate = answer(
        {
            "kind": "graph_claim",
            "claim_id": "one",
            "text": "An admitted fact.",
            "target_kind": "assertion",
            "target_id": "assertion:pond",
            "passage_handles": [],
        }
    )
    Draft202012Validator(output_schema(f, rules())).validate(candidate)


@pytest.mark.parametrize(
    "domain,kind",
    [
        ("passages", "source_passage_claim"),
        ("native", "native_source_claim"),
        ("authored", "authored_excerpt"),
        ("graph", "graph_claim"),
    ],
)
def test_empty_exposure_removes_only_its_impossible_variant(domain, kind):
    f = frame()
    if domain == "passages":
        f["opened_passages"] = []
    elif domain == "native":
        f["native_source_sections"]["sections"] = []
    elif domain == "authored":
        f["committed_plan_blocks"] = []
        f["session_evidence"] = []
    else:
        f["graph_records"] = []
    variants = output_schema(f, rules())["properties"]["answer_segments"]["items"][
        "anyOf"
    ]
    kinds = {v["properties"]["kind"]["const"] for v in variants}
    assert kind not in kinds and "proposal" in kinds
    expected = {"graph_claim", "source_passage_claim", "native_source_claim",
                "authored_excerpt", "session_summary", "proposal"} - {kind}
    if domain == "authored": expected.remove("session_summary")
    assert kinds == expected


def test_schema_is_exact_strict_and_does_not_mutate_or_add_prose_limits():
    f = frame()
    r = rules(lookup=True, support=True)
    before = deepcopy(f)
    schema = output_schema(f, r)
    assert f == before and schema == make_schema_strict(schema)
    Draft202012Validator.check_schema(schema)
    assert output_format(f, r) == {
        "type": "json_schema",
        "name": "plan_evidence_selectors_v2",
        "schema": schema,
        "strict": True,
    }
    assert "maxLength" not in str(schema)
    candidate = {
        "schema": "dmb_rules_mixed_answer_v1",
        "base_output": answer({"kind": "authored_excerpt", "selection_id": "a-note"}),
        "rules_segments": [
            {
                "kind": "rules_claim",
                "text": "A rule.",
                "support_ids": [str(r.supports[0].support_id)],
            }
        ],
        "ordered_refs": [
            {"domain": "base", "segment_index": None},
            {"domain": "rules", "segment_index": 0},
        ],
    }
    Draft202012Validator(schema).validate(candidate)
    candidate["rules_segments"][0]["support_ids"] = []
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(candidate)
    candidate["rules_segments"][0]["support_ids"] = [str(uuid4())]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(candidate)


def test_rules_without_support_have_context_but_no_claim_variant():
    schema = output_schema(frame(), rules(lookup=True))
    variants = schema["properties"]["rules_segments"]["items"]["anyOf"]
    assert [v["properties"]["kind"]["const"] for v in variants] == ["rules_context"]


@pytest.mark.parametrize("gaps", [["pond"], [{"question_phrase": "pond", "offset": 0}]])
def test_gaps_have_only_the_current_typed_shape(gaps):
    candidate = answer(
        {"kind": "proposal", "label": "image_prompt", "text": "A visual prompt."}
    )
    candidate["requested_detail_gaps"] = gaps
    with pytest.raises(ValidationError):
        Draft202012Validator(output_schema(frame(), rules())).validate(candidate)


def test_ineligible_passage_text_does_not_offer_a_source_claim():
    f = frame()
    f["opened_passages"] = [
        {"passage_handle": None, "text": "Truncated context.", "truncated": True}
    ]
    variants = output_schema(f, rules())["properties"]["answer_segments"]["items"][
        "anyOf"
    ]
    assert not any(
        v["properties"]["kind"]["const"] == "source_passage_claim" for v in variants
    )


def test_session_summary_schema_cannot_select_plan_or_unexposed_sources():
    schema = output_schema(frame(), rules())
    accepted = answer({"kind":"session_summary", "text":"Saved notes suggest a route remains open.", "selection_ids":["a-note"]})
    Draft202012Validator(schema).validate(accepted)
    for selections in ([], ["a-current"], ["foreign"]):
        rejected = deepcopy(accepted)
        rejected["answer_segments"][0]["selection_ids"] = selections
        with pytest.raises(ValidationError): Draft202012Validator(schema).validate(rejected)
    f = frame(); f["session_evidence"] = []
    with pytest.raises(ValidationError): Draft202012Validator(output_schema(f,rules())).validate(accepted)


def test_retained_v4_producer_format_is_verified_without_becoming_a_current_execution_option():
    from pathlib import Path
    from application_state.agent_conversation.plan_writer_output_schema import verify_format
    frozen=json.loads((Path(__file__).parent/'fixtures/plan_writer_selector_v1_format.json').read_text())
    f=frozen['producer_frame'];body={'text':{'format':frozen['producer_format']}}
    verify_format(body,f,rules())
    with pytest.raises(ValueError): output_format(f,rules())
    changed=deepcopy(body)
    changed['text']['format']['schema']['properties']['answer_segments']['items']['anyOf'].append(
        {'type':'object','properties':{'kind':{'const':'session_summary'}}})
    with pytest.raises(ValueError): verify_format(changed,f,rules())
    current=frame()
    with pytest.raises(ValueError): verify_format(body,current,rules())
