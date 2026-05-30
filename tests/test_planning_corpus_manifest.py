from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from src.live_play.planning_corpus_manifest import (
    AUTHORITIES,
    SCHEMA_ID,
    SOURCE_ROLES,
    _AUTHORITY_BY_ROLE,
    build_planning_corpus_manifest,
    main,
    render_manifest_markdown,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/c2_live_prep/live/schemas/planning_corpus_manifest.schema.json"
ARTIFACT_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
CORPUS_ROOT = ROOT / "corpus/eldyrwild-markdown"
LIVE_WORKSPACE = ROOT / "evals/c2_live_prep/live/session_22"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _build_real() -> dict[str, Any]:
    return build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=23,
        source_sessions=[21, 22],
        corpus_root=CORPUS_ROOT,
        live_workspace_dir=LIVE_WORKSPACE,
    )


def _snapshot_tree(root: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _make_synthetic_corpus(tmp_path: Path, *, with_recap: bool) -> Path:
    root = tmp_path / "corpus"
    camp = root / "Longmont Campaign/Campaign 2"
    (camp / "_ingest_staging").mkdir(parents=True)
    (camp / "_ingest_staging/session_5_raw_notes.md").write_text("staged", encoding="utf-8")
    (camp / "Session Prep").mkdir(parents=True)
    if with_recap:
        recaps = camp / "Session Recaps"
        (recaps / "_normalized").mkdir(parents=True)
        (recaps / "Session 05 - Synthetic Slug.md").write_text("recap", encoding="utf-8")
        (recaps / "_normalized/Session 05 - Synthetic Slug.md").write_text(
            "recap", encoding="utf-8"
        )
    return root


# --- committed-artifact boundary -------------------------------------------------


def test_committed_artifact_validates_against_schema() -> None:
    manifest = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    _validator().validate(manifest)
    assert manifest["schema"] == SCHEMA_ID
    assert len(manifest["entries"]) > 0


def test_builder_output_validates_against_schema() -> None:
    _validator().validate(_build_real())


# --- role / authority correctness ------------------------------------------------


def test_every_entry_has_valid_role_and_authority() -> None:
    manifest = _build_real()
    for entry in manifest["entries"]:
        assert entry["source_role"] in SOURCE_ROLES
        assert entry["authority"] in AUTHORITIES
        assert entry["authority"] == _AUTHORITY_BY_ROLE[entry["source_role"]]
        assert entry["session_scope"], "session_scope must be non-empty"


def test_scaffold_and_roll_table_forbid_play_facts() -> None:
    manifest = _build_real()
    for entry in manifest["entries"]:
        if entry["source_role"] in ("prep_scaffold", "roll_table"):
            assert "play_facts" in entry["forbidden_uses"], entry["route"]


def test_table_notes_forbid_play_facts_only_after_recap_materializes() -> None:
    manifest = _build_real()
    recap_sessions = {
        min(e["session_scope"])
        for e in manifest["entries"]
        if e["source_role"] == "play_recap" and e["route_exists"]
    }
    table_notes = [e for e in manifest["entries"] if e["source_role"] == "table_notes"]
    assert table_notes, "expected staged table notes for the source sessions"
    for entry in table_notes:
        session = min(entry["session_scope"])
        if session in recap_sessions:
            assert "play_facts" in entry["forbidden_uses"], entry["route"]
        else:
            assert "play_facts" not in entry["forbidden_uses"], entry["route"]


def test_synthetic_table_notes_conditional_on_recap(tmp_path: Path) -> None:
    with_recap = build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=6,
        source_sessions=[5],
        corpus_root=_make_synthetic_corpus(tmp_path / "a", with_recap=True),
        live_workspace_dir=None,
    )
    without_recap = build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=6,
        source_sessions=[5],
        corpus_root=_make_synthetic_corpus(tmp_path / "b", with_recap=False),
        live_workspace_dir=None,
    )
    notes_with = next(e for e in with_recap["entries"] if e["source_role"] == "table_notes")
    notes_without = next(
        e for e in without_recap["entries"] if e["source_role"] == "table_notes"
    )
    assert "play_facts" in notes_with["forbidden_uses"]
    assert "play_facts" not in notes_without["forbidden_uses"]


# --- honest gaps -----------------------------------------------------------------


def test_missing_sources_recorded_not_dropped() -> None:
    manifest = _build_real()
    # Session 22 recap is not yet materialized: its derivative rows must be present
    # with route_exists=false, not silently dropped.
    s22_recap = [
        e
        for e in manifest["entries"]
        if e["source_role"] == "play_recap" and e["session_scope"] == [22]
    ]
    assert len(s22_recap) == 3
    assert all(e["route_exists"] is False for e in s22_recap)


def test_builder_does_not_raise_on_missing_files(tmp_path: Path) -> None:
    manifest = build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=6,
        source_sessions=[5],
        corpus_root=_make_synthetic_corpus(tmp_path, with_recap=False),
        live_workspace_dir=None,
    )
    recaps = [e for e in manifest["entries"] if e["source_role"] == "play_recap"]
    assert recaps and all(e["route_exists"] is False for e in recaps)


# --- determinism -----------------------------------------------------------------


def test_two_builds_produce_identical_entries() -> None:
    first = _build_real()
    second = _build_real()
    assert first["entries"] == second["entries"]
    # source_ids are unique within a build.
    ids = [e["source_id"] for e in first["entries"]]
    assert len(ids) == len(set(ids))


def test_entries_sorted_by_role_session_id() -> None:
    manifest = _build_real()
    keys = [
        (e["source_role"], min(e["session_scope"]), e["source_id"])
        for e in manifest["entries"]
    ]
    assert keys == sorted(keys)


# --- read-only invariant ---------------------------------------------------------


def test_build_writes_nothing_to_corpus(tmp_path: Path) -> None:
    corpus = _make_synthetic_corpus(tmp_path, with_recap=True)
    before = _snapshot_tree(corpus)
    build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=6,
        source_sessions=[5],
        corpus_root=corpus,
        live_workspace_dir=None,
    )
    assert _snapshot_tree(corpus) == before


def test_cli_writes_only_to_out_paths(tmp_path: Path) -> None:
    corpus = _make_synthetic_corpus(tmp_path, with_recap=True)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out_json = out_dir / "manifest.json"
    out_md = out_dir / "manifest.md"
    before_corpus = _snapshot_tree(corpus)

    code = main(
        [
            "--campaign-id",
            "longmont-c2",
            "--planning-session",
            "6",
            "--source-sessions",
            "5",
            "--corpus-root",
            str(corpus),
            "--out",
            str(out_json),
            "--markdown-out",
            str(out_md),
        ]
    )
    assert code == 0
    assert _snapshot_tree(corpus) == before_corpus
    assert set(p.name for p in out_dir.iterdir()) == {"manifest.json", "manifest.md"}
    _validator().validate(json.loads(out_json.read_text(encoding="utf-8")))


# --- bad inputs ------------------------------------------------------------------


def test_unknown_campaign_id_raises() -> None:
    with pytest.raises(ValueError):
        build_planning_corpus_manifest(
            campaign_id="bogus-campaign",
            planning_session=23,
            source_sessions=[21],
            corpus_root=CORPUS_ROOT,
            live_workspace_dir=None,
        )


def test_empty_source_sessions_raises() -> None:
    with pytest.raises(ValueError):
        build_planning_corpus_manifest(
            campaign_id="longmont-c2",
            planning_session=23,
            source_sessions=[],
            corpus_root=CORPUS_ROOT,
            live_workspace_dir=None,
        )


def test_cli_bad_input_returns_2(tmp_path: Path) -> None:
    code = main(
        [
            "--campaign-id",
            "bogus-campaign",
            "--planning-session",
            "23",
            "--source-sessions",
            "21",
            "--corpus-root",
            str(tmp_path),
        ]
    )
    assert code == 2


# --- markdown mirror -------------------------------------------------------------


def test_markdown_mirror_is_deterministic_and_route_only() -> None:
    manifest = _build_real()
    first = render_manifest_markdown(manifest)
    second = render_manifest_markdown(copy.deepcopy(manifest))
    assert first == second
    assert SCHEMA_ID in first
    # The mirror references routes; it must contain every entry's route token.
    for entry in manifest["entries"]:
        assert entry["route"] in first
