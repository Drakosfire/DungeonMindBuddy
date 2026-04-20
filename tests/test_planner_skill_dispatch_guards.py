"""Tests for the recap-write fail-closed dispatch guard."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.planner import build_corpus_path_ref_index
from src.agent.planner_skill_dispatch_guards import (
    SKILL_DISPATCH_GUARDS,
    compute_recap_write_read_allowlist,
    wrap_dispatch_for_skill,
)
from src.agent.recap_context import resolve_recap_context


def _seed_corpus(tmp_path: Path) -> Path:
    """Lay down a minimal Longmont C2 corpus shape that ``resolve_recap_context`` accepts."""
    hub = tmp_path / "Longmont Campaign" / "Campaign 2"
    recaps = hub / "Session Recaps"
    prep = hub / "Session Prep"
    recaps.mkdir(parents=True)
    prep.mkdir(parents=True)
    for n in (17, 18, 19):
        (recaps / f"Session {n} - Recap.md").write_text(
            f"---\nsession: {n}\ncampaign_id: longmont-c2\ntitle: Session {n} - Recap\n---\n\nbody\n",
            encoding="utf-8",
        )
    (prep / "session_20_outline.md").write_text(
        "---\nsession: 20\ncampaign_id: longmont-c2\ntitle: Session 20 prep\n---\nprep body\n",
        encoding="utf-8",
    )
    (tmp_path / "Lysandra" / "C2").mkdir(parents=True)
    (tmp_path / "Lysandra" / "C2" / "README.md").write_text("not a recap", encoding="utf-8")
    return tmp_path


def _record_dispatch():
    """Test double: record every (name, args) pair, return a stable success body."""
    calls: list[tuple[str, str]] = []

    def dispatch(name: str, raw_args: str) -> str:
        calls.append((name, raw_args))
        return f"OK:{name}"

    return dispatch, calls


def test_compute_allowlist_returns_recent_recaps_and_prep_doc(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    allowed, err = compute_recap_write_read_allowlist(corpus)
    assert err is None
    assert any("session 19 - recap.md" in p for p in allowed)
    assert any("session 18 - recap.md" in p for p in allowed)
    assert any("session 17 - recap.md" in p for p in allowed)
    assert any("session_20_outline.md" in p for p in allowed)
    assert not any("lysandra" in p for p in allowed)


def test_compute_allowlist_includes_extras(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    extras = ["Longmont Campaign/Campaign 2/NPCs/Mirathorn.md"]
    allowed, _err = compute_recap_write_read_allowlist(corpus, extras=extras)
    assert any("npcs/mirathorn.md" in p for p in allowed)


def test_compute_allowlist_returns_error_when_no_recaps(tmp_path: Path) -> None:
    allowed, err = compute_recap_write_read_allowlist(tmp_path)
    assert allowed == set()
    assert err and "recap_context resolution failed" in err


def test_compute_allowlist_uses_precomputed_recap_context_after_corpus_drift(
    tmp_path: Path,
) -> None:
    """Snapshot the resolver before any write; a later commit must not shift the allowlist.

    Mirrors the harness contract for multi-turn ingest: turn 1 reads sessions
    17-19 + the session-20 prep doc, then commits ``Session 20 - Recap.md``.
    A turn-2 dispatcher built without the snapshot would resolve
    ``max(session)=20`` post-commit and return a target=21 allowlist that no
    longer contains Session 17 / the session-20 prep — the very paths the
    model legitimately relied on. The snapshot path freezes the answer.
    """
    corpus = _seed_corpus(tmp_path)
    snapshot = resolve_recap_context(corpus)
    allowed_before, _ = compute_recap_write_read_allowlist(corpus)
    assert snapshot.target_session == 20
    assert any("session 17 - recap.md" in p for p in allowed_before)
    assert any("session_20_outline.md" in p for p in allowed_before)

    new_recap = (
        corpus
        / "Longmont Campaign"
        / "Campaign 2"
        / "Session Recaps"
        / "Session 20 - Recap.md"
    )
    new_recap.write_text(
        "---\nsession: 20\ncampaign_id: longmont-c2\ntitle: Session 20 - Recap\n---\n\nbody\n",
        encoding="utf-8",
    )

    allowed_live_after_drift, _ = compute_recap_write_read_allowlist(corpus)
    assert not any("session 17 - recap.md" in p for p in allowed_live_after_drift), (
        "live resolve after drift should have shifted the window forward (this is the bug)"
    )

    allowed_with_snapshot, err = compute_recap_write_read_allowlist(
        corpus, precomputed_recap_context=snapshot
    )
    assert err is None
    assert allowed_with_snapshot == allowed_before


def test_recap_write_guard_uses_precomputed_recap_context(tmp_path: Path) -> None:
    """The guard must honor the same snapshot as the grader, end-to-end."""
    corpus = _seed_corpus(tmp_path)
    snapshot = resolve_recap_context(corpus)
    new_recap = (
        corpus
        / "Longmont Campaign"
        / "Campaign 2"
        / "Session Recaps"
        / "Session 20 - Recap.md"
    )
    new_recap.write_text(
        "---\nsession: 20\ncampaign_id: longmont-c2\ntitle: Session 20 - Recap\n---\n\nbody\n",
        encoding="utf-8",
    )

    base, calls = _record_dispatch()
    guarded_no_snapshot = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out_no_snapshot = guarded_no_snapshot(
        "read_corpus_file",
        json.dumps(
            {"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Recap.md"}
        ),
    )
    assert out_no_snapshot.startswith("Error: recap-write skill blocked"), (
        "live-resolved guard should reject the now-out-of-window Session 17 read"
    )
    assert calls == []

    base2, calls2 = _record_dispatch()
    guarded_snapshot = wrap_dispatch_for_skill(
        base2,
        corpus_path=corpus,
        active_skill_id="recap-write",
        precomputed_recap_context=snapshot,
    )
    out_snapshot = guarded_snapshot(
        "read_corpus_file",
        json.dumps(
            {"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 17 - Recap.md"}
        ),
    )
    assert out_snapshot == "OK:read_corpus_file"
    assert len(calls2) == 1


def test_recap_write_guard_resolves_c_ref_before_allowlist(tmp_path: Path) -> None:
    """``c:<hex>`` must resolve to a corpus-relative path before allowlist check."""
    corpus = _seed_corpus(tmp_path)
    rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md"
    ref_index = build_corpus_path_ref_index(corpus.resolve())
    ref_tok = next(
        k for k, v in ref_index.items() if v.replace("\\", "/").lower() == rel.lower()
    )
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "read_corpus_file",
        json.dumps({"path": f"c:{ref_tok}"}),
    )
    assert out == "OK:read_corpus_file"
    assert len(calls) == 1
    assert f"c:{ref_tok}" in calls[0][1]


def test_recap_write_guard_blocks_unknown_c_ref(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "read_corpus_file",
        json.dumps({"path": "c:deadbeefdeadbeefdeadbeefdeadbeef"}),
    )
    assert out.startswith("Error: unknown corpus file ref")
    assert calls == []


def test_recap_write_guard_allows_in_allowlist_path(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "read_corpus_file",
        json.dumps({"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md"}),
    )
    assert out == "OK:read_corpus_file"
    assert calls == [
        (
            "read_corpus_file",
            json.dumps({"path": "Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md"}),
        )
    ]


def test_recap_write_guard_blocks_offlist_path(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "read_corpus_file",
        json.dumps({"path": "Lysandra/C2/README.md"}),
    )
    assert out.startswith("Error: recap-write skill blocked read_corpus_file")
    assert "Lysandra/C2/README.md" in out
    assert "recent_recaps" in out
    assert "assemble_recap_draft" in out  # nudges the model to the right tool
    assert calls == []  # base dispatcher was never invoked


def test_recap_write_guard_blocks_load_context_markdown(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "load_context_markdown",
        json.dumps({"path": "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md"}),
    )
    assert out.startswith("Error: recap-write skill blocked load_context_markdown")
    assert calls == []


def test_recap_write_guard_passes_through_non_path_tools(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("get_recap_context", "{}")
    assert out == "OK:get_recap_context"
    out2 = guarded(
        "assemble_recap_draft",
        json.dumps(
            {
                "raw_notes_path": "Longmont Campaign/Campaign 2/_ingest_staging/session_20_raw_notes.md",
                "target_session": 20,
                "campaign_id": "longmont-c2",
            }
        ),
    )
    assert out2 == "OK:assemble_recap_draft"
    assert [c[0] for c in calls] == ["get_recap_context", "assemble_recap_draft"]


def test_recap_write_guard_blocks_get_recap_context_with_campaign_id(
    tmp_path: Path,
) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("get_recap_context", json.dumps({"campaign_id": "longmont-c2"}))
    assert out.startswith("Error: recap-write skill blocked get_recap_context")
    assert "campaign_id='longmont-c2'" in out
    assert "auto-detects" in out
    assert calls == []


def test_recap_write_guard_blocks_get_recap_context_with_target_session(
    tmp_path: Path,
) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("get_recap_context", json.dumps({"target_session": 20}))
    assert out.startswith("Error: recap-write skill blocked get_recap_context")
    assert "target_session=20" in out
    assert calls == []


def test_recap_write_guard_blocks_get_recap_context_with_both_pins(
    tmp_path: Path,
) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "get_recap_context",
        json.dumps({"campaign_id": "longmont-c2", "target_session": 20}),
    )
    assert out.startswith("Error: recap-write skill blocked get_recap_context")
    assert "campaign_id='longmont-c2'" in out
    assert "target_session=20" in out
    assert calls == []


def test_recap_write_guard_allows_get_recap_context_with_empty_strings(
    tmp_path: Path,
) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded(
        "get_recap_context",
        json.dumps({"campaign_id": "", "target_session": ""}),
    )
    assert out == "OK:get_recap_context"
    assert calls == [("get_recap_context", json.dumps({"campaign_id": "", "target_session": ""}))]


def test_recap_write_guard_rejects_invalid_get_recap_context_json(
    tmp_path: Path,
) -> None:
    corpus = _seed_corpus(tmp_path)
    base, _calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("get_recap_context", "{not-json")
    assert out.startswith("Error: invalid JSON arguments for get_recap_context")


def test_recap_write_guard_returns_resolution_error_when_no_recaps(tmp_path: Path) -> None:
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=tmp_path, active_skill_id="recap-write"
    )
    out = guarded("read_corpus_file", json.dumps({"path": "Anything.md"}))
    assert out.startswith("Error: recap-write read-guard cannot enforce allowlist")
    assert "recap_context resolution failed" in out
    assert calls == []


def test_recap_write_guard_handles_missing_path_arg(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("read_corpus_file", "{}")
    assert out == "OK:read_corpus_file"
    assert calls == [("read_corpus_file", "{}")]


def test_recap_write_guard_rejects_invalid_json(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, _calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("read_corpus_file", "{not-json")
    assert out.startswith("Error: invalid JSON arguments for read_corpus_file")


def test_no_wrapping_for_unknown_skill(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="other-skill"
    )
    assert guarded is base
    out = guarded(
        "read_corpus_file", json.dumps({"path": "Lysandra/C2/README.md"})
    )
    assert out == "OK:read_corpus_file"
    assert len(calls) == 1


def test_no_wrapping_for_none_skill(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    base, _calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id=None
    )
    assert guarded is base


def test_recap_write_is_listed_in_registry() -> None:
    assert "recap-write" in SKILL_DISPATCH_GUARDS


@pytest.mark.parametrize(
    "path",
    [
        "longmont campaign/campaign 2/session recaps/session 19 - recap.md",
        "Longmont Campaign\\Campaign 2\\Session Recaps\\Session 19 - Recap.md",
        " Longmont Campaign/Campaign 2/Session Recaps/Session 19 - Recap.md ",
    ],
)
def test_recap_write_guard_normalizes_path_variants(tmp_path: Path, path: str) -> None:
    corpus = _seed_corpus(tmp_path)
    base, _calls = _record_dispatch()
    guarded = wrap_dispatch_for_skill(
        base, corpus_path=corpus, active_skill_id="recap-write"
    )
    out = guarded("read_corpus_file", json.dumps({"path": path}))
    assert out == "OK:read_corpus_file"
