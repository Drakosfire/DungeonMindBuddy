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
        "graph_records": [{"kind": "assertion", "target_id": "assertion:pond", "evidence": ["e0"]}],
        "opened_passages": [{"passage_handle": "p-current", "evidence": "e0"}],
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
        "name": "plan_evidence_selectors_v3",
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


def test_graph_passages_join_exact_evidence_even_when_text_and_lines_match():
    f = frame()
    f["graph_records"] += [
        {"kind": "assertion", "target_id": "assertion:bridge", "evidence": ["e1"]},
        {"kind": "assertion", "target_id": "assertion:rail", "evidence": ["e0"]},
        {"kind": "relationship", "target_id": "edge:pond:bridge", "evidence": ["e1"]},
        {"kind": "assertion", "target_id": "assertion:unopened", "evidence": ["e2"]},
    ]
    f["opened_passages"] = [
        {"passage_handle": "p-current", "evidence": "e0", "text": "Same words.", "line_start": 1},
        {"passage_handle": "p-other", "evidence": "e1", "text": "Same words.", "line_start": 1},
        {"passage_handle": None, "evidence": "e2", "text": "Insufficient."},
    ]
    validator = Draft202012Validator(output_schema(f, rules()))
    for kind, target, allowed in [("assertion", "assertion:pond", "p-current"),
                                  ("assertion", "assertion:rail", "p-current"),
                                  ("assertion", "assertion:bridge", "p-other"),
                                  ("relationship", "edge:pond:bridge", "p-other"),
                                  ("assertion", "assertion:unopened", None)]:
        for handles in ([], ["p-current"], ["p-other"], ["p-current", "p-other"]):
            candidate = answer({"kind": "graph_claim", "claim_id": "one", "text": "Reported.",
                                "target_kind": kind, "target_id": target, "passage_handles": handles})
            assert validator.is_valid(candidate) == (not handles or handles == [allowed])
    validator.validate(answer({"kind": "source_passage_claim", "text": "Source reports.",
                               "passage_handles": ["p-current", "p-other"]}))


def test_ambiguous_target_closures_are_not_offered_but_equal_closures_coalesce():
    f = frame()
    f["graph_records"].append(deepcopy(f["graph_records"][0]))
    schema = output_schema(f, rules())
    graph = answer({"kind": "graph_claim", "claim_id": "one", "text": "Reported.",
                    "target_kind": "assertion", "target_id": "assertion:pond", "passage_handles": []})
    Draft202012Validator(schema).validate(graph)
    f["graph_records"][-1]["evidence"] = ["e-other"]
    with pytest.raises(ValidationError):
        Draft202012Validator(output_schema(f, rules())).validate(graph)


def test_retained_v2_format_is_exact_read_proof_not_current_dispatch():
    from pathlib import Path
    from application_state.agent_conversation.plan_writer_output_schema import verify_format
    frozen = json.loads((Path(__file__).parent / "fixtures/plan_writer_selector_v2_format.json").read_text())
    f = frozen["producer_frame"]
    body = {"text": {"format": frozen["producer_format"]}}
    verify_format(body, f, rules())
    assert output_format(f, rules())["name"] == "plan_evidence_selectors_v3"
    assert output_format(f, rules()) != frozen["producer_format"]
    changed = deepcopy(body)
    changed["text"]["format"]["schema"]["properties"]["answer_segments"]["minItems"] = 1
    with pytest.raises(ValueError): verify_format(changed, f, rules())


def test_legacy_schema_retains_its_existing_image_proposal_contract():
    candidate = answer({'kind': 'proposal', 'label': 'image_prompt', 'text': 'A visual prompt.'})
    Draft202012Validator(output_schema(frame(), rules())).validate(candidate)


def test_variant_writer_visible_reply_preserves_retained_edits_schema(monkeypatch):
    from application_state.agent_conversation import native_build_work_view
    from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
    from application_state.agent_conversation.native_writer import SCHEMA
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from application_state.agent_conversation.surface_evidence_answer import ASSERTION_POLICY

    monkeypatch.setattr(native_build_work_view, "variant_sources", lambda _: {"statblock0": {}})
    evidence = {
        "schema": SCHEMA,
        "answer_policy": ASSERTION_POLICY,
        "native_statements": {"statements": []},
        "native_body_evidence": {"excerpts": []},
        "native_assertions": None,
    }
    work = {"schema": NATIVE_WORK_SCHEMA, "artifact_under_edit": {"sections": []}}
    retained = native_output_format(evidence, rules(), work, build_local=True, format_version=4)
    current = native_output_format(evidence, rules(), work, build_local=True, format_version=5)

    assert retained["name"] == native_build_work_view.VARIANT_EDITS_FORMAT
    assert current["name"] == native_build_work_view.VARIANT_VISIBLE_REPLY_FORMAT
    expected = deepcopy(retained["schema"])
    assert "minItems" not in expected["properties"]["answer_segments"]
    expected["properties"]["answer_segments"]["minItems"] = 1
    assert current["schema"] == expected

    for has_draft in (False, True):
        witness_work = work | ({"working_draft_context": {"draft_markdown": "An exact condition.", "record_id": "4c63e929-fcec-4d8a-b787-4f908b3ce857"}} if has_draft else {})
        witnessed = native_output_format(evidence, rules(), witness_work, build_local=True, format_version=6)
        assert witnessed["name"] == native_build_work_view.VARIANT_WITNESS_FORMAT
        variant = witnessed["schema"]["properties"]["statblock_variant"]
        for field in ("add_rules", "replace_rules"):
            edit = variant["properties"][field]["items"]
            assert list(edit["properties"]) == ["authored_quotes", "rule"]
            assert edit["properties"]["authored_quotes"].get("maxItems") == (None if has_draft else 0)
            rule = edit["properties"]["rule"]
            assert "action → action" in edit["description"]
            assert "special only with trait or regional_effect" in edit["description"]
            variant["properties"][field]["items"] = rule
        assert witnessed["schema"] == native_output_format(evidence, rules(), witness_work, build_local=True, format_version=5)["schema"]

    work_with_draft = work | {
        "working_draft_context": {"draft_markdown": "Repeated.\n\nRepeated."},
    }
    current_version = native_build_work_view.variant_output_version(work_with_draft)
    assert current_version == 11
    current = native_output_format(evidence, rules(), work_with_draft, build_local=True,
                                   format_version=current_version)
    assert current["name"] == native_build_work_view.VARIANT_PASSAGE_WITNESS_FORMAT
    variant = current["schema"]["properties"]["statblock_variant"]["properties"]
    assert variant["passage_review"]["required"] == ["p1", "p2"]
    for field in ("add_rules", "replace_rules"):
        edit = variant[field]["items"]
        assert "authored_quotes" not in edit["properties"]
        assert edit["properties"]["authored_passages"]["items"]["enum"] == ["p1", "p2"]

    retained = native_output_format(evidence, rules(), work_with_draft, build_local=True, format_version=10)
    old_variant = retained["schema"]["properties"]["statblock_variant"]["properties"]
    assert "authored_quotes" in old_variant["add_rules"]["items"]["properties"]
    assert "authored_passages" not in old_variant["add_rules"]["items"]["properties"]
    assert old_variant["passage_review"]["required"] == ["p1", "p2"]


def test_anchored_discussion_schema_only_accepts_discussion_segments():
    from application_state.agent_conversation.build_primary_context import NATIVE_WORK_SCHEMA
    from application_state.agent_conversation.native_writer import SCHEMA
    from application_state.agent_conversation.plan_writer_output_schema import native_output_format
    from application_state.agent_conversation.surface_evidence_answer import ASSERTION_POLICY

    evidence = {
        "schema": SCHEMA,
        "answer_policy": ASSERTION_POLICY,
        "native_statements": {"statements": []},
        "native_body_evidence": {"excerpts": []},
        "native_assertions": None,
    }
    work = {
        "schema": NATIVE_WORK_SCHEMA,
        "artifact_under_edit": {"sections": []},
        "working_draft_context": {"record_id": "4c63e929-fcec-4d8a-b787-4f908b3ce857"},
    }
    ordinary = native_output_format(evidence, rules(), work, build_local=True)
    discussion = native_output_format(evidence, rules(), work, build_local=True, format_version=7)
    assert discussion["name"] == "surface_native_evidence_selectors_v7"
    old_items = ordinary["schema"]["properties"]["answer_segments"]["items"]
    items = discussion["schema"]["properties"]["answer_segments"]["items"]
    validator = Draft202012Validator(items)
    assert validator.is_valid({"kind": "discussion", "text": "One way to play this is a truce."})
    factual = {"kind": "draft_reference_claim", "text": "The draft sets a trigger.", "draft_record_id": "draft0"}
    assert Draft202012Validator(old_items).is_valid(factual)
    assert not validator.is_valid(factual)
