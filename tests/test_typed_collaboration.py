"""Closed producer output and historical format separation."""

import copy
import json
from uuid import uuid4
import pytest
from pydantic import TypeAdapter, ValidationError
from application_state.agent_conversation.collaboration import (
    Collaboration,
    POLICY,
    FORMAT,
)
from application_state.agent_conversation.build_draft_answer import (
    normalize,
    output_schema,
)
from application_state.agent_conversation.source_writer_output import (
    validate_writer_format,
)
from generationengine.utils.schema_utils import make_schema_strict


def packet():
    return {
        "user_question": "Plan a shop.",
        "source_writer_output_policy": "cited_facts_host_limitations_v1",
        "requested_detail_gap_policy": "exact_question_phrase_selected_excerpts_v1",
        "working_draft_context": {"record_id": str(uuid4())},
        "collaboration_output_policy": POLICY,
    }


def answer(collaboration):
    return {
        "answer_context_status": "creative_proposal",
        "answer_segments": [
            {"kind": "suggestion", "text": "Let’s build this together."}
        ],
        "limitations": [],
        "requested_detail_gaps": [],
        "collaboration": collaboration,
    }


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "plan", "steps": []},
        {"kind": "plan", "steps": [{"text": "Create the shop", "kind": "create_page"}]},
        {"kind": "plan", "steps": [{"text": "  ", "kind": "discuss"}]},
        {
            "kind": "plan",
            "steps": [{"text": "Read it", "kind": "discuss", "done": True}],
        },
        {"kind": "questions", "questions": [{"text": " "}]},
        {
            "kind": "questions",
            "questions": [{"text": "Which route?", "answer": "invented"}],
        },
        {
            "kind": "plan",
            "steps": [{"text": "Read it", "kind": "discuss"}],
            "execute": True,
        },
    ],
)
def test_model_cannot_invent_executor_completion_or_author_answers(value):
    with pytest.raises(ValidationError):
        TypeAdapter(Collaboration).validate_python(value)


def test_exact_strict_schema_and_normalization_keep_work_separate_from_acknowledgment():
    p = packet()
    collaboration = {
        "kind": "plan",
        "steps": [
            {"text": "Discuss the existing names.", "kind": "discuss"},
            {"text": "Prepare page prose.", "kind": "prepare_insertion"},
        ],
    }
    result = normalize(json.dumps(answer(collaboration)), p)
    assert result["collaboration"] == collaboration
    assert result["answer_segments"] == [
        {"kind": "connective", "text": "Suggestion: Let’s build this together."}
    ]
    schema = output_schema(p)
    assert make_schema_strict(schema) == schema
    validate_writer_format(
        {"type": "json_schema", "name": FORMAT, "strict": True, "schema": schema}, p
    )
    with pytest.raises(ValueError):
        validate_writer_format(
            {
                "type": "json_schema",
                "name": "build_working_draft_answer_v1",
                "strict": True,
                "schema": schema,
            },
            p,
        )
    historical = copy.deepcopy(p)
    historical.pop("collaboration_output_policy")
    with pytest.raises(ValidationError):
        normalize(json.dumps(answer(collaboration)), historical)
    legacy = answer(None)
    legacy.pop("collaboration")
    assert "collaboration" not in normalize(json.dumps(legacy), historical)
    with pytest.raises(ValidationError):
        normalize(json.dumps(legacy), p)


def test_connected_review_schema_is_exact_and_binds_a_unique_actual_excerpt():
    from application_state.agent_conversation.collaboration import (
        CONNECTED_POLICY,
        CONNECTED_FORMAT,
    )

    p = packet()
    p["connected_page_review_policy"] = CONNECTED_POLICY
    rid = str(uuid4())
    body = "| Name | Task |\n| Copper | Repair a hook |\n"
    p["related_authored_pages"] = {
        "pages": [
            {
                "read_id": rid,
                "markdown": body,
                "page": {
                    "document_id": str(uuid4()),
                    "registry_revision": 3,
                    "content_sha256": "a" * 64,
                },
            }
        ]
    }
    proposal = {
        "kind": "connected_page",
        "title": "Copper Forge",
        "read_id": rid,
        "quote": "Copper | Repair",
        "person_label": None,
        "relationships": [],
        "instructions": "Useful workshop",
    }
    schema = output_schema(p)
    assert make_schema_strict(schema) == schema
    validate_writer_format(
        {
            "type": "json_schema",
            "name": CONNECTED_FORMAT,
            "strict": True,
            "schema": schema,
        },
        p,
    )
    assert normalize(json.dumps(answer(proposal)), p)["collaboration"] == proposal
    for patch in [{"read_id": str(uuid4())}, {"quote": "missing"}, {"quote": "|"}]:
        with pytest.raises(ValueError):
            normalize(json.dumps(answer({**proposal, **patch})), p)
    historical = copy.deepcopy(p)
    historical.pop("connected_page_review_policy")
    with pytest.raises(ValidationError):
        normalize(json.dumps(answer(proposal)), historical)


def test_live_source_claim_omission_remains_rejected_without_repair():
    from application_state.agent_conversation.build_draft_answer import (
        source_claim_limitations,
    )

    p = packet()
    p["retrieval_disposition"] = {
        "status": "provisionally_supported",
        "coverage_status": "heuristic_partial",
    }
    raw = answer(None)
    raw["answer_segments"].insert(
        0,
        {
            "kind": "saved_source_claim",
            "text": "The saved page names Mara Vell.",
            "section_read_ids": [str(uuid4())],
        },
    )
    original = json.dumps(raw)
    assert source_claim_limitations(p) == {"partial_retrieval"}
    with pytest.raises(
        ValueError, match="omitted the related-source retrieval qualification"
    ):
        normalize(original, p)
    assert json.dumps(raw) == original
    raw["limitations"] = ["partial_retrieval"]
    assert (
        normalize(json.dumps(raw), p)["answer_context_status"]
        == "source_grounded_partial"
    )
    assert (
        normalize(json.dumps(answer(None)), p)["answer_context_status"]
        == "creative_proposal"
    )
    p["retrieval_disposition"]["status"] = "unresolved_conflict"
    assert source_claim_limitations(p) == {"partial_retrieval", "unresolved_conflict"}
    p["retrieval_disposition"] = {
        "status": "provisionally_supported",
        "coverage_status": "catalog_exhausted",
    }
    assert source_claim_limitations(p) == set()


@pytest.mark.parametrize(
    "kind,selector,identity,quote",
    [
        ("saved_source_claim", "section_read_ids", "current", "Copper House scaffold"),
        (
            "source_passage_claim",
            "passage_handles",
            "world",
            "Mara operates the workshop",
        ),
        ("related_page_claim", "read_id", "related", "A rack holds practice bells"),
    ],
)
def test_quote_witness_is_bound_to_exact_family_and_source(
    kind, selector, identity, quote
):
    from application_state.agent_conversation.source_quote_binding import (
        POLICY as QP,
        validate_and_project,
    )

    p = packet()
    p.update(
        source_quote_binding_policy=QP,
        connected_page_review_policy="typed_connected_page_review_v1",
        artifact_under_edit={
            "sections": [{"read_id": "current", "text": "Copper House scaffold"}]
        },
        opened_passages=[{"handle": "world", "text": "Mara operates the workshop"}],
        related_authored_pages={
            "pages": [
                {
                    "read_id": "related",
                    "markdown": "A rack holds practice bells",
                    "page": {"title": "Workshop"},
                }
            ]
        },
    )
    selected = identity if kind == "related_page_claim" else [identity]
    raw = {
        "answer_segments": [
            {
                "kind": kind,
                "text": "A factual claim",
                selector: selected,
                "supporting_quotes": [quote],
            }
        ]
    }
    original = copy.deepcopy(raw)
    result = validate_and_project(raw, p)
    assert "supporting_quotes" not in result["answer_segments"][0]
    assert raw == original
    for bad in [[], ["wrong page text"], [" "], [quote, quote]]:
        wrong = copy.deepcopy(raw)
        wrong["answer_segments"][0]["supporting_quotes"] = bad
        with pytest.raises(ValueError):
            validate_and_project(wrong, p)
    wrong = copy.deepcopy(raw)
    wrong["answer_segments"][0].pop("supporting_quotes")
    with pytest.raises(ValueError):
        validate_and_project(wrong, p)
    wrong = copy.deepcopy(raw)
    wrong["answer_segments"][0][selector] = (
        "current" if kind == "related_page_claim" else ["related"]
    )
    with pytest.raises(ValueError):
        validate_and_project(wrong, p)
    historical = copy.deepcopy(p)
    historical.pop("source_quote_binding_policy")
    assert validate_and_project(raw, historical) == raw
    p["source_quote_binding_policy"] = "unknown"
    with pytest.raises(ValueError):
        validate_and_project(raw, p)


def test_quote_schema_is_versioned_and_cannot_upgrade_historical_format():
    from application_state.agent_conversation.source_quote_binding import (
        POLICY as QP,
        FORMAT as QF,
    )

    p = packet()
    p.update(
        connected_page_review_policy="typed_connected_page_review_v1",
        source_quote_binding_policy=QP,
    )
    rid = str(uuid4())
    p["related_authored_pages"] = {
        "pages": [
            {
                "read_id": rid,
                "markdown": "A rack holds practice bells",
                "page": {"title": "Workshop"},
            }
        ]
    }
    schema = output_schema(p)
    assert make_schema_strict(schema) == schema
    assert "supporting_quotes" in schema["$defs"]["RelatedPageDraftClaim"]["required"]
    validate_writer_format(
        {"type": "json_schema", "name": QF, "strict": True, "schema": schema}, p
    )
    for name in ["build_working_draft_answer_v3", "build_working_draft_answer_v2"]:
        with pytest.raises(ValueError):
            validate_writer_format(
                {"type": "json_schema", "name": name, "strict": True, "schema": schema},
                p,
            )
    old = copy.deepcopy(p)
    old.pop("source_quote_binding_policy")
    assert (
        "supporting_quotes"
        not in output_schema(old)["$defs"]["RelatedPageDraftClaim"]["properties"]
    )
    with pytest.raises(ValueError):
        validate_writer_format(
            {"type": "json_schema", "name": QF, "strict": True, "schema": schema}, old
        )
    value = answer(None)
    value["answer_segments"] = [
        {
            "kind": "related_page_claim",
            "text": "The page describes practice bells.",
            "read_id": rid,
            "supporting_quotes": ["A rack holds practice bells"],
        }
    ]
    assert normalize(json.dumps(value), p)["answer_segments"][0] == {
        k: v for k, v in value["answer_segments"][0].items() if k != "supporting_quotes"
    }
    with pytest.raises(ValidationError):
        normalize(json.dumps(value), old)


def test_multi_source_quotes_cannot_be_swapped_between_valid_selectors():
    from application_state.agent_conversation.source_quote_binding import (
        POLICY as QP,
        validate_and_project,
    )

    p = {
        "source_quote_binding_policy": QP,
        "connected_page_review_policy": "typed_connected_page_review_v1",
        "opened_passages": [
            {"handle": "one", "text": "Mara owns the shop"},
            {"handle": "two", "text": "Oren keeps the bell"},
        ],
    }
    value = {
        "answer_segments": [
            {
                "kind": "source_passage_claim",
                "text": "A mixed claim",
                "passage_handles": ["one", "two"],
                "supporting_quotes": ["Mara owns the shop", "Oren keeps the bell"],
            }
        ]
    }
    assert (
        "supporting_quotes" not in validate_and_project(value, p)["answer_segments"][0]
    )
    value["answer_segments"][0]["supporting_quotes"].reverse()
    with pytest.raises(ValueError, match="absent from its selected source"):
        validate_and_project(value, p)
