"""Finite producer schemas narrow choices without replacing host authorization."""

from copy import deepcopy
import hashlib
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.source_writer_output import (
    FINITE_SCHEMA_NAME,
    POLICY,
    SCHEMA_NAME,
    finite_output_schema,
    output_schema,
    validate_writer_format,
)
from apps.live_control_server.services import build_jev_writer as writer


def passage(text="Authored source passage."):
    fields = dict(
        text=text,
        source_class="opened_source_passage_not_graph_truth",
        source_artifact_id="source",
        source_revision_id="revision",
        line_start=1,
        line_end=1,
    )
    return dict(
        fields,
        handle="p"
        + hashlib.sha256(
            json.dumps(
                fields, sort_keys=True, ensure_ascii=False, separators=(",", ":")
            ).encode()
        ).hexdigest()[:24],
    )


def section():
    text = "Saved authored section."
    return dict(
        kind="validated_build_section_read_v1",
        event_id=str(uuid4()),
        sequence=0,
        read_id=str(uuid4()),
        source_basis=dict(
            world_id="world",
            document_id="doc",
            registry_revision=1,
            content_sha256="a" * 64,
            visibility="internal",
        ),
        source_class="saved_authored_source_not_played_truth",
        line_start=1,
        line_end=1,
        text=text,
        excerpt_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def packet():
    return dict(
        source_writer_output_policy=POLICY,
        opened_passages=[passage()],
        exposure={"saved_sections": [section()]},
        user_question="What does the source say?",
    )


def fmt(schema, name=FINITE_SCHEMA_NAME):
    return dict(type="json_schema", name=name, schema=schema, strict=True)


def staged(p):
    return writer.WriterProjection(
        json.dumps(p, sort_keys=True, separators=(",", ":")),
        0,
        "prior",
        source_bindings_json="{}",
        source_writer_output_policy=POLICY,
    )


def raw(s):
    return json.dumps(s.kwargs(), ensure_ascii=False, separators=(",", ":"))


def total(body):
    return (
        len(body.encode())
        + 64 * (1 + writer._json_nodes(json.loads(body)))
        + writer.OUTPUT_RESERVE
    )


def test_exact_sorted_enums_and_no_packet_mutation():
    p = packet()
    p["opened_passages"].append(passage("A second source."))
    p["exposure"]["saved_sections"].append(section())
    before = deepcopy(p)
    schema = finite_output_schema(p)
    assert p == before
    assert schema["$defs"]["PassageFact"]["properties"]["passage_handles"]["items"] == {
        "type": "string",
        "enum": sorted(x["handle"] for x in p["opened_passages"]),
    }
    assert schema["$defs"]["SavedFact"]["properties"]["section_read_ids"]["items"] == {
        "type": "string",
        "enum": sorted(x["read_id"] for x in p["exposure"]["saved_sections"]),
    }
    p["opened_passages"].reverse()
    p["exposure"]["saved_sections"].reverse()
    assert finite_output_schema(p) == schema
    assert (
        "enum"
        not in output_schema()["$defs"]["PassageFact"]["properties"]["passage_handles"][
            "items"
        ]
    )


@pytest.mark.parametrize("has_passages", [False, True])
@pytest.mark.parametrize("has_sections", [False, True])
def test_empty_selector_sets_remove_only_impossible_fact_variants(
    has_passages, has_sections
):
    p = packet()
    if not has_passages:
        p["opened_passages"] = []
    if not has_sections:
        p["exposure"]["saved_sections"] = []
    schema = finite_output_schema(p)
    defs = schema["$defs"]
    assert ("PassageFact" in defs) == has_passages
    assert ("SavedFact" in defs) == has_sections
    assert "Suggestion" in defs
    choices = schema["properties"]["answer_segments"]["items"]["anyOf"]
    assert {x["$ref"] for x in choices} == {f"#/$defs/{name}" for name in defs}
    assert '"enum": []' not in json.dumps(schema)
    assert (
        schema["properties"]["limitations"]
        == output_schema()["properties"]["limitations"]
    )


@pytest.mark.parametrize(
    "bad",
    [
        "duplicate_passage",
        "truncated_handle",
        "modified_text",
        "bad_class",
        "bad_range",
        "extra_identity",
        "duplicate_read",
        "duplicate_event",
        "bad_uuid",
        "bad_section_hash",
        "bad_policy",
    ],
)
def test_malformed_or_ambiguous_packet_identities_refuse(bad):
    p = packet()
    if bad == "duplicate_passage":
        p["opened_passages"] *= 2
    elif bad == "truncated_handle":
        p["opened_passages"][0]["handle"] = p["opened_passages"][0]["handle"][:-1]
    elif bad == "modified_text":
        p["opened_passages"][0]["text"] = "different body"
    elif bad == "bad_class":
        p["opened_passages"][0]["source_class"] = "played_truth"
    elif bad == "bad_range":
        p["opened_passages"][0]["line_start"] = True
    elif bad == "extra_identity":
        p["opened_passages"][0]["foreign"] = True
    elif bad == "duplicate_read":
        p["exposure"]["saved_sections"] *= 2
    elif bad == "duplicate_event":
        extra = deepcopy(p["exposure"]["saved_sections"][0])
        extra["read_id"] = str(uuid4())
        p["exposure"]["saved_sections"].append(extra)
    elif bad == "bad_uuid":
        p["exposure"]["saved_sections"][0]["read_id"] = "foreign"
    elif bad == "bad_section_hash":
        p["exposure"]["saved_sections"][0]["excerpt_sha256"] = "f" * 64
    else:
        p["source_writer_output_policy"] = "unknown"
    with pytest.raises(ValueError):
        finite_output_schema(p)


def test_exact_version_specific_schema_and_packet_drift():
    p = packet()
    finite = finite_output_schema(p)
    validate_writer_format(fmt(output_schema(), SCHEMA_NAME), p)
    validate_writer_format(fmt(finite), p)
    for wrong in [
        fmt(output_schema()),
        fmt(finite, SCHEMA_NAME),
        fmt(finite, "unknown"),
        dict(fmt(finite), strict=1),
    ]:
        with pytest.raises(ValueError):
            validate_writer_format(wrong, p)
    changed = deepcopy(p)
    changed["opened_passages"].append(passage("Another source"))
    with pytest.raises(ValueError):
        validate_writer_format(fmt(finite), changed)
    tampered = deepcopy(finite)
    tampered["$defs"]["PassageFact"]["properties"]["passage_handles"]["items"][
        "enum"
    ].append("invented")
    with pytest.raises(ValueError):
        validate_writer_format(fmt(tampered), p)


def test_actual_wire_schema_hash_and_enlarged_context_budget():
    p = packet()
    s = staged(p)
    body = raw(s)
    wire = json.loads(body)
    assert wire["text"]["format"] == fmt(finite_output_schema(p))
    assert wire["tools"] == [] and wire["stream"] is False
    writer.validate_body(body, s, budget=writer.role_budget())
    old = deepcopy(wire)
    old["text"]["format"] = fmt(output_schema(), SCHEMA_NAME)
    assert len(body.encode()) > len(json.dumps(old, separators=(",", ":")).encode())
    assert (
        hashlib.sha256(body.encode()).hexdigest()
        != hashlib.sha256(json.dumps(old).encode()).hexdigest()
    )
    with pytest.raises(ValueError, match="differs"):
        writer.validate_body(json.dumps(old), s, budget=writer.role_budget())
    # Include the full finite schema in the exact actual-wire boundary.
    p["user_question"] = ""
    base = total(raw(staged(p)))
    p["user_question"] = "x" * (128000 - base)
    s = staged(p)
    body = raw(s)
    assert total(body) == 128000
    writer.validate_body(body, s, budget=writer.role_budget())
    p["user_question"] += "x"
    with pytest.raises(ValueError, match="context allowance"):
        writer.validate_body(raw(staged(p)), staged(p), budget=writer.role_budget())
