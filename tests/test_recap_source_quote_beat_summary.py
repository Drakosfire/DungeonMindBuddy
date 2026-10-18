from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest

from src.graph_memory.candidate_graph_preview import candidate_graph_preview_from_dict
from src.graph_memory.candidate_graph_to_contribution import candidate_graph_to_contribution
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionOptions,
    FixtureCategoryGraphPassClient,
    extract_category_candidate_graph,
)


ARTIFACT = "artifact:recap:synthetic:session-01"


def _source_index(source_text: str, *, include_full_text: bool = True) -> dict[str, Any]:
    spans: list[dict[str, Any]] = []
    if include_full_text:
        spans.append(
            {
                "kind": "full_text",
                "span_id": "session-01:recap:full_text",
                "source_span_ref_id": "session-01:recap:full_text",
                "line_start": 1,
                "line_end": max(1, len(source_text.splitlines())),
                "char_start": 0,
                "char_end": len(source_text),
                "ordinal": 0,
            }
        )
    cursor = 0
    for ordinal, paragraph in enumerate(source_text.split("\n\n"), start=1):
        if not paragraph:
            cursor += 2
            continue
        start = source_text.find(paragraph, cursor)
        end = start + len(paragraph)
        line_start = source_text.count("\n", 0, start) + 1
        line_end = source_text.count("\n", 0, max(start, end - 1)) + 1
        span_id = f"session-01:recap:paragraph:{ordinal:03d}"
        spans.append(
            {
                "kind": "paragraph",
                "span_id": span_id,
                "source_span_ref_id": span_id,
                "source_artifact_id": ARTIFACT,
                "line_start": line_start,
                "line_end": line_end,
                "char_start": start,
                "char_end": end,
                "ordinal": ordinal,
                # Locator metadata deliberately may disagree with source_text.
                "text": paragraph,
            }
        )
        cursor = end + 2
    return {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "source_artifact_id": ARTIFACT,
        "source_ref_id": f"{ARTIFACT}:text",
        "content_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
        "spans": spans,
    }


def _beat(
    span_id: str | None,
    quote: str | None,
    *,
    extra_quotes: list[str] | None = None,
    evidence_refs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    refs = evidence_refs
    if refs is None:
        ref: dict[str, Any] = {"anchor_quotes": [quote] if quote is not None else []}
        if span_id is not None:
            ref["source_span_ref_id"] = span_id
        if extra_quotes:
            ref["anchor_quotes"].extend(extra_quotes)
        refs = [ref]
    return {
        "beat_id": "beat:model-id",
        "order": 1,
        "title": "Ephanna casts Eldritch Blast",
        "summary": "Ephanna cast the spell and defeated the monster.",
        "involved_node_ids": ["npc:ephanna"],
        "evidence_refs": refs,
    }


def _extract(
    source_text: str | None,
    beats: list[dict[str, Any]],
    *,
    index: dict[str, Any] | None = None,
    with_node: bool = False,
):
    pinned_text = source_text if source_text is not None else ""
    span_index = index if index is not None else _source_index(pinned_text)
    node_pass: dict[str, Any] = {"observation_nodes": []}
    if with_node:
        first = next(
            span for span in span_index["spans"] if span.get("kind") == "paragraph"
        )
        node_pass["observation_nodes"] = [
            {
                "node_id": "loc:mireward",
                "label": "Mireward",
                "node_type": "location",
                "description": "A town.",
                "importance": "high",
                "evidence_refs": [
                    {
                        "source_span_ref_id": first["source_span_ref_id"],
                        "anchor_quotes": ["Mireward"],
                    }
                ],
            }
        ]
    passes = {
        "actor_pass": node_pass,
        "location_pass": {"observation_nodes": []},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {
            "observation_nodes": [],
            "ignored_items": [],
            "deferred_items": [],
        },
        "beat_pass": {"observation_beats": beats},
        "edge_pass": {"observation_edges": []},
    }
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="synthetic",
            session_id="session-01",
            session_number=None,
            source_span_index=span_index,
            source_text=source_text,
            source_artifact_id=ARTIFACT,
            source_ref_id=f"{ARTIFACT}:text",
            model_id="fixture-model",
        ),
        client=FixtureCategoryGraphPassClient(passes),
    )
    return result


@pytest.mark.parametrize(
    ("paragraph", "anchor"),
    [
        (
            "The recap explicitly says no spell was cast in the encounter. "
            "Ephanna will use Eldritch Blast if the monsters return.",
            "Ephanna will use Eldritch Blast",
        ),
        (
            "    Ephanna will use Eldritch Blast if the monsters return.",
            "Ephanna will use Eldritch Blast",
        ),
        (
            "Lysandra reports that Ephanna said she would try Eldritch Blast, "
            "but the recap does not confirm that she did.",
            "Ephanna said she would try Eldritch Blast",
        ),
        (
            "Ephanna attempts to cast Eldritch Blast, but the spell fizzles "
            "and hits nothing.",
            "attempts to cast Eldritch Blast",
        ),
        (
            "The group decides to stop and camp, intending to reach Edge "
            "during daylight.",
            "decides to stop and camp",
        ),
    ],
)
def test_recap_beat_uses_full_exact_source_excerpt_and_neutral_title(
    paragraph: str, anchor: str,
) -> None:
    index = _source_index(paragraph)
    span_id = next(s["source_span_ref_id"] for s in index["spans"] if s["kind"] == "paragraph")
    result = _extract(paragraph, [_beat(span_id, anchor)])

    assert len(result.candidate_graph["beats"]) == 1
    beat = result.candidate_graph["beats"][0]
    assert beat["summary"] == paragraph
    assert beat["title"] == "Source excerpt 1"
    assert len(beat["evidence_refs"]) == 1
    assert beat["evidence_refs"][0]["source_span_ref_id"] == span_id
    assert beat["evidence_refs"][0]["anchor_quotes"] == [paragraph.strip()]
    assert beat["evidence_refs"][0]["anchor_quote_matches"] == [
        {
            "quote": paragraph,
            "char_start": 0,
            "char_end": len(paragraph),
            "match_text": paragraph,
        }
    ]
    assert "Ephanna casts Eldritch Blast" not in beat["title"]
    assert "defeated the monster" not in beat["summary"]
    typed = candidate_graph_preview_from_dict(result.candidate_graph)
    assert typed.beats[0].summary == paragraph
    assert typed.beats[0].title == "Source excerpt 1"
    assert typed.beats[0].evidence_refs[0].anchor_quote_matches[0].match_text == paragraph


@pytest.mark.parametrize(
    ("case", "expected_code"),
    [
        ("missing_nomination", "missing_span_nomination"),
        ("forged_span", "forged_span_ref"),
        ("missing_anchor", "missing_anchor"),
        ("anchor_not_in_pinned_text", "anchor_not_found"),
        ("full_text_span", "non_paragraph_span"),
        ("multi_span", "multi_span_nomination"),
        ("invalid_bounds", "invalid_span_bounds"),
        ("missing_source_text", "missing_source_text"),
        ("missing_digest", "missing_source_digest"),
        ("stale_digest", "source_digest_mismatch"),
    ],
)
def test_invalid_recap_beat_nominations_defer_without_model_prose(
    case: str, expected_code: str,
) -> None:
    paragraph = "Ephanna will use Eldritch Blast if the monsters return."
    source_text = paragraph
    index = _source_index(source_text)
    span_id = next(s["source_span_ref_id"] for s in index["spans"] if s["kind"] == "paragraph")
    model_beat = _beat(span_id, "Ephanna will use Eldritch Blast")

    if case == "missing_nomination":
        model_beat["evidence_refs"] = []
    elif case == "forged_span":
        model_beat = _beat("forged:span:404", "Ephanna will use Eldritch Blast")
    elif case == "missing_anchor":
        model_beat = _beat(span_id, None)
    elif case == "anchor_not_in_pinned_text":
        index["spans"][-1]["text"] = "The model says Ephanna casts Eldritch Blast."
        model_beat = _beat(span_id, "The model says Ephanna casts Eldritch Blast")
    elif case == "full_text_span":
        full_text_span = index["spans"][0]
        model_beat = _beat(full_text_span["source_span_ref_id"], "Ephanna will use Eldritch Blast")
    elif case == "multi_span":
        model_beat["evidence_refs"] = [
            {"source_span_ref_id": span_id, "anchor_quotes": ["Ephanna will use"]},
            {"source_span_ref_id": span_id, "anchor_quotes": ["monsters return"]},
        ]
    elif case == "invalid_bounds":
        index["spans"][-1]["line_end"] = 99
        model_beat = _beat(span_id, "Ephanna will use Eldritch Blast")
    elif case == "missing_source_text":
        model_beat = _beat(span_id, "Ephanna will use Eldritch Blast")
    elif case == "missing_digest":
        index.pop("content_sha256")
    elif case == "stale_digest":
        index["content_sha256"] = "0" * 64

    result = _extract(None if case == "missing_source_text" else source_text, [model_beat], index=index)
    graph = result.candidate_graph
    assert graph["beats"] == []
    assert len(graph["deferred_items"]) == 1
    deferred = graph["deferred_items"][0]
    assert deferred["reason"] == f"recap_beat_excerpt_deferred:{expected_code}"
    assert deferred["evidence_refs"] == []
    serialized = json.dumps(graph)
    assert "Ephanna casts Eldritch Blast" not in serialized
    assert "defeated the monster" not in serialized


def test_repeated_anchor_across_paragraphs_is_ambiguous() -> None:
    source_text = "Thrin describes the signal.\n\nThrin describes the signal."
    index = _source_index(source_text)
    first_span = next(s["source_span_ref_id"] for s in index["spans"] if s.get("ordinal") == 1)
    result = _extract(source_text, [_beat(first_span, "Thrin describes the signal.")])

    assert result.candidate_graph["beats"] == []
    assert result.candidate_graph["deferred_items"][0]["reason"] == (
        "recap_beat_excerpt_deferred:ambiguous_anchor"
    )


def test_line_only_span_bounds_copy_indentation_and_line_endings_exactly() -> None:
    paragraph = "    Ephanna will cast Eldritch Blast if the monsters return."
    source_text = paragraph + "\r\n"
    index = _source_index(paragraph)
    index["content_sha256"] = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    span = next(s for s in index["spans"] if s.get("kind") == "paragraph")
    span.pop("char_start")
    span.pop("char_end")
    span["text"] = "a deliberately different index excerpt"
    span_id = span["source_span_ref_id"]

    result = _extract(source_text, [_beat(span_id, "Ephanna will cast Eldritch Blast")], index=index)

    beat = result.candidate_graph["beats"][0]
    assert beat["summary"] == paragraph
    assert beat["evidence_refs"][0]["anchor_quote_matches"][0]["match_text"] == paragraph


def test_anchors_that_resolve_to_different_paragraphs_are_deferred() -> None:
    source_text = "Ephanna will cast Eldritch Blast.\n\nThe group decides to camp."
    index = _source_index(source_text)
    spans = [s for s in index["spans"] if s.get("kind") == "paragraph"]
    result = _extract(
        source_text,
        [_beat(spans[0]["source_span_ref_id"], "Ephanna will cast", extra_quotes=["decides to camp"])],
    )

    assert result.candidate_graph["beats"] == []
    assert result.candidate_graph["deferred_items"][0]["reason"] == (
        "recap_beat_excerpt_deferred:span_mismatch"
    )


def test_recap_beat_excerpt_does_not_become_a_graph_event_assertion() -> None:
    source_text = "Mireward is the town where the group rests."
    index = _source_index(source_text)
    span_id = next(s["source_span_ref_id"] for s in index["spans"] if s.get("kind") == "paragraph")
    result = _extract(
        source_text,
        [_beat(span_id, "Mireward")],
        index=index,
        with_node=True,
    )
    typed = candidate_graph_preview_from_dict(result.candidate_graph)
    contribution = candidate_graph_to_contribution(
        typed,
        world_id="elderwyld",
        source_revision_id=hashlib.sha256(source_text.encode()).hexdigest(),
        source_artifact_id=ARTIFACT,
    )

    assert len(typed.beats) == 1
    assert len(contribution.candidate_assertions) == 1
    assert contribution.candidate_assertions[0].assertion_kind == "node"
    assert all(assertion.assertion_kind != "event" for assertion in contribution.candidate_assertions)
