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
