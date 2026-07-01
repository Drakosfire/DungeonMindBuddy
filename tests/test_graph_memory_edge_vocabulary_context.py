from __future__ import annotations

from src.graph_memory.vocabulary import (
    ContainmentHint,
    ContextVocabularyPacket,
    DoNotMergeDecision,
    EvidenceRef,
    render_edge_vocabulary_context,
)


def _packet() -> ContextVocabularyPacket:
    return ContextVocabularyPacket(
        packet_id="packet:vocab:test-edge",
        scope="campaign",
        known_names=["Mireward Council", "North Gate Defense", "Mireward", "Captain Lysandra"],
        entry_aliases={"Captain Lysandra": ["Lysandra Ironveil"]},
        candidate_entry_aliases={"Captain Lysandra": ["The Captain"]},
        entry_labels={
            "vocab:place:mireward": "Mireward",
            "vocab:collective:mireward": "Mireward Council",
        },
        entry_kinds={
            "vocab:place:mireward": "place",
            "vocab:collective:mireward": "collective",
        },
        type_hints={
            "Mireward": "place",
            "Mireward Council": "collective",
            "North Gate Defense": "combat_encounter",
            "Captain Lysandra": "actor",
        },
        combat_encounter_hints=["North Gate Defense"],
        predicate_hints={"North Gate Defense": ["occurred_at", "involved"]},
        do_not_merge_hints=[
            DoNotMergeDecision(
                decision_id="dnm:mireward-place-council",
                left_vocab_id="vocab:place:mireward",
                right_vocab_id="vocab:collective:mireward",
                reason="city and council are distinct governance/place concepts",
                evidence_refs=[
                    EvidenceRef(source_artifact_id="artifact:test", quote="do not emit this quote")
                ],
            )
        ],
        containment_hints=[
            ContainmentHint(
                hint_id="contain:guard-mireward",
                child_label="Mireward Guard",
                parent_label="Mireward",
                evidence_refs=[
                    EvidenceRef(
                        source_artifact_id="artifact:test",
                        source_span_ref_id="source_span_secret",
                    )
                ],
            )
        ],
    )


def test_renders_compact_edge_context():
    context = render_edge_vocabulary_context(_packet()).context_text

    assert "Known names" in context
    assert "Mireward [place]" in context
    assert "Mireward Council [collective]" in context
    assert "North Gate Defense [combat_encounter]" in context
    assert "Captain Lysandra [actor]" in context
    assert "aliases: Lysandra Ironveil" in context
    assert "candidate aliases / review only: The Captain" in context
    assert "- Lysandra Ironveil [actor]" not in context
    assert "- The Captain [actor]" not in context
    assert "Combat encounter anchors" in context
    assert "Predicate hints" in context
    assert "occurred_at" in context
    assert "involved" in context
    assert "Mireward [place] must not merge with Mireward Council [collective]" in context
    assert "city and council are distinct governance/place concepts" in context
    assert "vocab:place:mireward != vocab:collective:mireward" not in context
    assert "Mireward Guard -> Mireward" in context


def test_excludes_evidence_and_source_text():
    context = render_edge_vocabulary_context(_packet()).context_text.lower()

    assert "quote" not in context
    assert "source_span" not in context


def test_deterministic_output():
    first = render_edge_vocabulary_context(_packet())
    second = render_edge_vocabulary_context(_packet())

    assert first.context_text == second.context_text
    assert first.diagnostics == second.diagnostics


def test_max_lines_trims_safely():
    rendered = render_edge_vocabulary_context(_packet(), max_lines=3)

    assert len(rendered.context_text.splitlines()) <= 3
    assert rendered.diagnostics["trimmed_line_count"] > 0
