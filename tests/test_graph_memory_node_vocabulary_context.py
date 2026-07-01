from __future__ import annotations

import pytest

from src.graph_memory.vocabulary import (
    ContextVocabularyPacket,
    ContainmentHint,
    DoNotMergeDecision,
    EvidenceRef,
)
from src.graph_memory.vocabulary.node_context import render_node_vocabulary_context


def _packet() -> ContextVocabularyPacket:
    evidence = [
        EvidenceRef(
            source_artifact_id="artifact:secret",
            source_span_ref_id="source_span_secret",
            quote="do not emit this quote",
        )
    ]
    return ContextVocabularyPacket(
        packet_id="packet:vocab:node-context",
        scope="campaign",
        known_names=["Mireward", "Mireward Council", "North Gate Defense", "Captain Lysandra"],
        entry_aliases={"Captain Lysandra": ["Lysandra Ironveil"], "Mireward": ["City of Bells"]},
        candidate_entry_aliases={"Captain Lysandra": ["The Captain"]},
        entry_labels={
            "vocab:place:mireward": "Mireward",
            "vocab:collective:mireward": "Mireward Council",
            "vocab:actor:lysandra": "Captain Lysandra",
        },
        entry_kinds={
            "vocab:place:mireward": "place",
            "vocab:collective:mireward": "collective",
            "vocab:actor:lysandra": "actor",
        },
        type_hints={
            "Mireward": "place",
            "Mireward Council": "collective",
            "North Gate Defense": "combat_encounter",
            "Captain Lysandra": "actor",
        },
        combat_encounter_hints=["North Gate Defense"],
        predicate_hints={"North Gate Defense": ["involved", "occurred_at"]},
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:1",
                left_vocab_id="vocab:place:mireward",
                right_vocab_id="vocab:collective:mireward",
                reason="city and council are distinct governance/place concepts",
                evidence_refs=evidence,
            )
        ],
        containment_hints=[
            ContainmentHint(
                hint_id="contains:1",
                child_label="Mireward Guard",
                parent_label="Mireward",
                evidence_refs=evidence,
            )
        ],
    )


def test_renders_targeted_location_context():
    rendered = render_node_vocabulary_context(_packet(), pass_name="location_pass")

    assert "Mireward [place]" in rendered.context_text
    assert "- Mireward Council [collective]" not in rendered.context_text
    assert "North Gate Defense" not in rendered.context_text
    assert rendered.diagnostics["target_entity_kinds"] == ["place"]


def test_renders_aliases_under_canonical_names_for_matching_pass():
    rendered = render_node_vocabulary_context(_packet(), pass_name="actor_pass")

    assert "Captain Lysandra [actor]" in rendered.context_text
    assert "aliases: Lysandra Ironveil" in rendered.context_text
    assert "candidate aliases / review only: The Captain" in rendered.context_text
    assert "- Lysandra Ironveil [actor]" not in rendered.context_text


def test_irrelevant_aliases_do_not_render_for_unrelated_passes():
    location_context = render_node_vocabulary_context(_packet(), pass_name="location_pass").context_text

    assert "Captain Lysandra" not in location_context
    assert "Lysandra Ironveil" not in location_context
    assert "The Captain" not in location_context


def test_renders_targeted_collective_context():
    rendered = render_node_vocabulary_context(_packet(), pass_name="collective_pass")

    assert "Mireward Council [collective]" in rendered.context_text
    assert "- Mireward [place]\n" not in rendered.context_text


def test_renders_combat_encounter_in_thread_pass():
    rendered = render_node_vocabulary_context(_packet(), pass_name="thread_pass")

    assert "North Gate Defense [combat_encounter]" in rendered.context_text
    assert "Combat encounter names" in rendered.context_text
    assert "North Gate Defense: involved, occurred_at" in rendered.context_text


def test_do_not_merge_cautions_render_readable_labels():
    context_text = render_node_vocabulary_context(_packet(), pass_name="location_pass").context_text

    assert "Mireward [place] must not merge with Mireward Council [collective]" in context_text
    assert "city and council are distinct governance/place concepts" in context_text
    assert "vocab:place:mireward != vocab:collective:mireward" not in context_text


def test_excludes_evidence_quotes_and_source_text():
    context_text = render_node_vocabulary_context(_packet(), pass_name="location_pass").context_text

    assert "quote" not in context_text.lower()
    assert "source_span" not in context_text.lower()
    assert "do not emit this quote" not in context_text


def test_deterministic_output():
    first = render_node_vocabulary_context(_packet(), pass_name="thread_pass")
    second = render_node_vocabulary_context(_packet(), pass_name="thread_pass")

    assert first.context_text == second.context_text
    assert first.diagnostics == second.diagnostics


def test_max_lines_trims_safely():
    rendered = render_node_vocabulary_context(_packet(), pass_name="thread_pass", max_lines=3)

    assert len(rendered.context_text.splitlines()) <= 3
    assert rendered.diagnostics["trimmed_line_count"] > 0


def test_unknown_pass_fails_clearly():
    with pytest.raises(ValueError, match="pass_name"):
        render_node_vocabulary_context(_packet(), pass_name="bad_pass")
