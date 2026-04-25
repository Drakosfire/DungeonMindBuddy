"""Offline tests for Stage A prompt-context assembly helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.session_events_extraction_vertical_slice.step1_session_events_run import (
    _ANCHOR_REPAIR_APPLY_TEXT_REWRITES,
    _SYSTEM_PROMPT,
    _apply_revised_event_text_if_supported,
    _merge_recap_evidence_span_into_source_anchors,
    AnchorRepairItem,
    AnchorRepairOutput,
    build_user_prompt,
    discover_campaign_pc_hub_dirs,
    load_pc_identity_hints,
    partition_weak_events_for_anchor_repair_prompt,
    _participant_evidence_in_span,
    _repair_weak_event_anchors,
    _tokenize_for_overlap,
)

# Static Stage A model instructions must not embed Session 20 gold/oracle vocabulary.
_STAGE_A_PROMPT_BANNED_ORACLE_SUBSTRINGS = (
    "Eldritch Blast",
    "Thunderwave",
    "Zephyr Strike",
    "scimitar",
    "dart",
    "red gnat",
    # C1 / benchmark proper names and places (must not appear in static Stage A system prompt)
    "kirfan",
    "pippa",
    "bubbles",
    "stonebridge",
    "river's edge",
    "wizard's tower",
    "glowkindle",
    "bonogo",
    "stafl",
    "marla",
    "baergrom",
    "tomas",
    "lysandra",
    "branwen",
    "sara_mirathorn",
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discover_campaign_pc_hub_dirs_prefers_same_campaign(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 1/PCs/c1_only/README.md",
        "---\ntitle: c1 only\n---\n",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/c2_a/README.md",
        "---\ntitle: c2 a\n---\n",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/c2_b/README.md",
        "---\ntitle: c2 b\n---\n",
    )

    hubs = discover_campaign_pc_hub_dirs(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
    )
    names = [p.name for p in hubs]
    assert names == ["c2_a", "c2_b"]


def test_discover_campaign_pc_hub_dirs_falls_back_when_target_missing(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 1/PCs/c1_only/README.md",
        "---\ntitle: c1 only\n---\n",
    )

    hubs = discover_campaign_pc_hub_dirs(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 99 - Recap.md",
    )
    assert [p.name for p in hubs] == ["c1_only"]


def test_load_pc_identity_hints_filters_to_known_character_slugs(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/caelynn/caelynn_character_dossier.md",
        """---
title: "Caelynn dossier"
campaign_id: longmont-c2
---

# Caelynn

**Caelynn** is a storm-flavored mage.

| Field | Detail |
|------|--------|
| **Species / class (corpus tokens)** | **Half Elf** **Sorcerer** |
""",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/caelynn/timeline.md",
        """---
title: "Caelynn timeline"
---

| Session | Beat (1-3 lines) | Recap / prep |
|--------|------------------|--------------|
| **Backstory** | Learned to channel storm magic in youth. | `Longmont Campaign/Campaign 2/Campaign 2 Notes.md` |
""",
    )
    _write(
        corpus_root / "Longmont Campaign/Campaign 2/PCs/bonogo/bonogo_character_dossier.md",
        """---
title: "Bonogo dossier"
---

# Bonogo

**Bonogo** is a rogue.
""",
    )

    user_message = (
        "Extract session events.\n\n"
        "Known character slugs: caelynn, captain_lysandra_ironveil"
    )
    hints = load_pc_identity_hints(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        user_message,
    )
    assert "caelynn" in hints
    assert "Half Elf Sorcerer" in hints
    assert "Backstory: Learned to channel storm magic in youth." in hints
    assert "bonogo" not in hints


def test_load_pc_identity_hints_noop_when_hubs_absent(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus"
    hints = load_pc_identity_hints(
        corpus_root,
        "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        "Known character slugs: caelynn",
    )
    assert hints == ""


def test_build_user_prompt_includes_fallback_guardrails_when_hints_present() -> None:
    msg = build_user_prompt(
        "Extract events",
        "Recap body here",
        "- caelynn: species/class=Half Elf Sorcerer",
    )
    assert "PC IDENTITY HINTS (fallback anchors)" in msg
    assert "Never let hints override explicit recap facts" in msg
    assert "- caelynn: species/class=Half Elf Sorcerer" in msg


def test_build_user_prompt_omits_hint_block_when_empty() -> None:
    msg = build_user_prompt("Extract events", "Recap body here", "")
    assert "PC IDENTITY HINTS (fallback anchors)" not in msg
    assert "0001: Recap body here" in msg


def test_build_user_prompt_numbers_multi_line_recap() -> None:
    msg = build_user_prompt("Extract", "alpha\nbeta", "")
    assert "0001: alpha" in msg
    assert "0002: beta" in msg
    assert "1-based line numbers" in msg


def test_merge_recap_evidence_span_into_source_anchors() -> None:
    rel = "Campaign/r.md"
    lines = ["first", "second", "third"]
    d: dict = {
        "recap_evidence_span": {"path": rel, "line_start": 2, "line_end": 3},
        "event_name": "x",
    }
    _merge_recap_evidence_span_into_source_anchors(
        d, recap_relative_path=rel, recap_lines=lines, commit_sha=""
    )
    assert "recap_evidence_span" not in d
    assert d["source_anchors"][0]["line_start"] == 2
    assert d["source_anchors"][0]["line_end"] == 3
    assert d["source_anchors"][0]["path"] == rel


def test_merge_recap_evidence_span_rejects_whole_file_placeholder() -> None:
    rel = "r.md"
    lines = ["a", "b", "c"]
    d = {"recap_evidence_span": {"path": rel, "line_start": 1, "line_end": 3}}
    _merge_recap_evidence_span_into_source_anchors(
        d, recap_relative_path=rel, recap_lines=lines, commit_sha=""
    )
    assert "source_anchors" not in d
    assert "recap_evidence_span" not in d


def test_system_prompt_contains_multi_participant_roster_completeness_clause() -> None:
    """Regression: clause added 2026-04-23 for Stage A participant-completeness flake on multi-PC roster sentences."""
    assert "MULTI-PARTICIPANT ROSTER COMPLETENESS" in _SYSTEM_PROMPT
    assert "every named character in that list belongs in" in _SYSTEM_PROMPT


def test_stage_a_system_prompt_excludes_benchmark_oracle_vocabulary() -> None:
    """Regression: model-facing Stage A instructions must not repeat gold/oracle terms."""
    blob = _SYSTEM_PROMPT.casefold()
    for term in _STAGE_A_PROMPT_BANNED_ORACLE_SUBSTRINGS:
        assert term.casefold() not in blob, term


def test_partition_weak_events_splits_when_budget_small() -> None:
    long_recap = [f"line {i} padding" for i in range(400)]
    weak = [
        {"event_index": j, "event_name": f"e{j}", "event_class": "combat", "participants": [], "outcomes": []}
        for j in range(5)
    ]
    chunks = partition_weak_events_for_anchor_repair_prompt(
        weak,
        recap_relative_path="Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        recap_lines=long_recap,
        char_budget=8000,
    )
    assert len(chunks) >= 2
    assert sum(len(c) for c in chunks) == len(weak)


def test_participant_evidence_in_span_requires_slug_surface_form() -> None:
    span_ok = "Captain Lysandra orders a full stop.".lower()
    span_bad = "The captain orders a full stop without a proper name.".lower()
    assert _participant_evidence_in_span(["captain_lysandra_ironveil"], span_ok)
    assert not _participant_evidence_in_span(["captain_lysandra_ironveil"], span_bad)
    assert _participant_evidence_in_span([], span_bad)


def test_participant_evidence_accepts_karesmine_for_karsemine_slug() -> None:
    """Corpus recap line uses variant spelling 'Karesmine' for PC slug karsemine."""
    span = (
        "Using her extensive tracking skills, Karesmine is able to estimate the distance."
    ).lower()
    assert _participant_evidence_in_span(["karsemine"], span)


def test_anchor_repair_keeps_original_outcomes_when_revised_introduces_unsupported_tokens() -> None:
    """Unsupported revised outcomes are dropped; anchor still applies (span-local lexical gate)."""
    original_outcomes = ["Karsemine fights the swarm with Eldritch Blast"]
    events_raw = [
        {
            "event_name": "Swarm fight",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": list(original_outcomes),
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine fires Eldritch Blast into the undead swarm.\n"
    # "fights" does not appear in the recap line — span-local gate rejects the full revised list.
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_outcomes=["Karsemine fights Eldritch Blast into the undead swarm"],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["outcomes"] == original_outcomes
    assert out[0]["source_anchors"][0].get("line_start") == 1
    assert stats["repaired"] == 1
    assert stats["unresolved"] == 0
    assert usage["input_tokens"] == 0


def test_anchor_repair_does_not_consume_benchmark_expected_events() -> None:
    """Repair path never reads grading.expected_events; text rewrites are not applied (honesty)."""
    events_raw = [
        {
            "event_name": "Swarm fight",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine fights the swarm with Eldritch Blast"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine fires Eldritch Blast into the undead swarm.\n"
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_outcomes=["Karsemine fires into the undead swarm"],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    # Span-grounded rewrites are ignored by default; original extraction (warts and all) stays.
    assert out[0]["outcomes"] == ["Karsemine fights the swarm with Eldritch Blast"]
    assert "Eldritch" in out[0]["outcomes"][0]
    assert stats["repaired"] == 1
    assert not _ANCHOR_REPAIR_APPLY_TEXT_REWRITES


def test_anchor_repair_ignores_span_grounded_revised_outcomes_by_default() -> None:
    """Even when revised outcomes are fully span-grounded, defaults preserve original extraction."""
    events_raw = [
        {
            "event_name": "Swarm fight",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine fights the swarm with Eldritch Blast"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine fires Eldritch Blast into the undead swarm.\n"
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_outcomes=["Karsemine fires Eldritch Blast into the undead swarm"],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["outcomes"] == ["Karsemine fights the swarm with Eldritch Blast"]
    assert out[0]["source_anchors"][0].get("line_start") == 1
    assert stats["repaired"] == 1
    assert stats["unresolved"] == 0


def test_lexical_subset_allows_role_action_swap_but_repair_skips_text_rewrites() -> None:
    """Falsification: span-local token subset is necessary, not sufficient.

    The same line can name two actors and two distinct actions; a repair can reuse
    only words from the span while swapping *who* did *what*. The lexical gate passes;
    default anchor repair still does not apply revised outcomes (benchmark honesty).
    """
    recap_text = (
        "Karsemine channels healing into the party line. "
        "Caelynn opens fire on the troll with Eldritch Blast.\n"
    )
    span_tokens = _tokenize_for_overlap(recap_text)
    bad_outcome = "Karsemine opens fire on the troll with Eldritch Blast."
    _a, outcomes_apply, _n, revised = _apply_revised_event_text_if_supported(
        item=AnchorRepairItem(
            event_index=0,
            status="anchored",
            line_start=1,
            line_end=1,
            revised_outcomes=[bad_outcome],
        ),
        span_tokens=span_tokens,
    )
    assert outcomes_apply
    assert revised == [bad_outcome]

    events_raw = [
        {
            "event_name": "Combat",
            "event_class": "combat",
            "participants": ["karsemine", "caelynn"],
            "outcomes": ["Karsemine channels healing into the party line."],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_outcomes=[bad_outcome],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["outcomes"] == ["Karsemine channels healing into the party line."]
    assert stats["repaired"] == 1


def test_anchor_repair_anchor_only_preserves_event_text() -> None:
    """Anchor repair with no revised name/outcomes still replaces weak anchors."""
    events_raw = [
        {
            "event_name": "Hold the line",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine keeps the bridge"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine holds the line at the bridge.\n"
    repair = AnchorRepairItem(event_index=0, status="anchored", line_start=1, line_end=1)
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["event_name"] == "Hold the line"
    assert out[0]["outcomes"] == ["Karsemine keeps the bridge"]
    assert out[0]["source_anchors"][0].get("line_start") == 1
    assert stats["repaired"] == 1


def test_anchor_repair_keeps_original_event_name_when_revised_name_unsupported() -> None:
    events_raw = [
        {
            "event_name": "Swarm fight",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine fires Eldritch Blast into the undead swarm"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine fires Eldritch Blast into the undead swarm.\n"
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_event_name="Dragon siege at Stonebridge",
        revised_outcomes=["Karsemine fires Eldritch Blast into the undead swarm"],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["event_name"] == "Swarm fight"
    assert out[0]["outcomes"] == ["Karsemine fires Eldritch Blast into the undead swarm"]
    assert out[0]["source_anchors"][0].get("line_start") == 1
    assert stats["repaired"] == 1


def test_anchor_repair_rejects_whole_revised_outcome_list_if_any_line_unsupported() -> None:
    """Conservative: either all revised outcomes are span-grounded or none replace the originals."""
    original = ["Karsemine fires Eldritch Blast into the undead swarm"]
    events_raw = [
        {
            "event_name": "Swarm fight",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": list(original),
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        }
    ]
    recap_text = "Karsemine fires Eldritch Blast into the undead swarm.\n"
    repair = AnchorRepairItem(
        event_index=0,
        status="anchored",
        line_start=1,
        line_end=1,
        revised_outcomes=[
            "Karsemine fires Eldritch Blast into the undead swarm",
            "Caelynn casts Thunderwave at the swarm",
        ],
    )
    raw_client = MagicMock()
    raw_client.responses.parse.return_value = MagicMock(
        output_parsed=AnchorRepairOutput(repairs=[repair]),
        usage=None,
    )
    out, stats, _usage = _repair_weak_event_anchors(
        client=raw_client,
        model_id="gpt-test",
        recap_relative_path="r.md",
        recap_text=recap_text,
        events_raw=events_raw,
    )
    assert out[0]["outcomes"] == original
    assert stats["repaired"] == 1


def test_anchor_repair_chunked_calls_merge_and_partial_failure_is_tolerated() -> None:
    events_raw = [
        {
            "event_name": "A",
            "event_class": "combat",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine holds the line"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        },
        {
            "event_name": "B",
            "event_class": "travel",
            "participants": ["karsemine"],
            "outcomes": ["Karsemine marches east"],
            "source_anchors": [{"source_type": "legacy_unanchored"}],
        },
    ]
    long_recap = [f"beat {i} with Karsemine" for i in range(300)]
    recap_joined = "\n".join(long_recap) + "\n"
    r2 = AnchorRepairItem(event_index=1, status="anchored", line_start=2, line_end=2, revised_outcomes=[])

    raw_client = MagicMock()

    def _parse(**_kwargs):
        # First batch fails; second returns one repair (simulates one chunk failing).
        if not hasattr(_parse, "n"):
            _parse.n = 0
        _parse.n += 1
        if _parse.n == 1:
            raise RuntimeError("transient API failure")
        return MagicMock(
            output_parsed=AnchorRepairOutput(repairs=[r2]),
            usage=None,
        )

    raw_client.responses.parse.side_effect = _parse

    with patch(
        "evals.session_events_extraction_vertical_slice.step1_session_events_run._ANCHOR_REPAIR_USER_CHAR_BUDGET",
        4000,
    ):
        out, stats, _usage = _repair_weak_event_anchors(
            client=raw_client,
            model_id="gpt-test",
            recap_relative_path="r.md",
            recap_text=recap_joined,
            events_raw=[dict(e) for e in events_raw],
        )
    assert stats.get("repair_chunks_failed") == 1
    assert out[1]["source_anchors"][0].get("line_start") == 2
    assert stats["repaired"] == 1
