from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from src.live_play.planning_corpus_manifest import (
    AUTHORITIES,
    DOGFOOD_FULL_SCHEMA_ID,
    SCHEMA_ID,
    SOURCE_ROLES,
    _AUTHORITY_BY_ROLE,
    build_dogfood_full_manifest,
    build_planning_corpus_manifest,
    main,
    render_manifest_markdown,
)
from src.live_play.session_bootstrap import bootstrap_session_workspace
from src.live_play.session_paths import live_sessions_root

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/c2_live_prep/live/schemas/planning_corpus_manifest.schema.json"
ARTIFACT_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json"
DOGFOOD_ARTIFACT_PATH = ROOT / "evals/c2_live_prep/benchmarks/c2s23_dogfood_full_manifest.json"
CORPUS_ROOT = ROOT / "corpus/eldyrwild-markdown"
LIVE_WORKSPACE = ROOT / "evals/c2_live_prep/live/session_23"
BOOTSTRAP_RECAP = ROOT / "tests/fixtures/live_bootstrap/session_22_fresh_recap.md"
PLAY_FACT_USE = "play_facts"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _build_real() -> dict[str, Any]:
    return build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=23,
        source_sessions=[21, 22, 23],
        corpus_root=CORPUS_ROOT,
        live_workspace_dir=LIVE_WORKSPACE,
    )


def _build_dogfood_full() -> dict[str, Any]:
    return build_dogfood_full_manifest(
        campaign_id="longmont-c2",
        planning_session=23,
        source_sessions=[21, 22, 23],
        corpus_root=CORPUS_ROOT,
        live_workspace_dir=LIVE_WORKSPACE,
    )


def _without_generated_at(manifest: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(manifest)
    out.pop("generated_at", None)
    return out


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


def _bootstrap_workspace(tmp_path: Path, *, session: int) -> Path:
    out = live_sessions_root() / "_pytest" / tmp_path.name / f"session_{session}"
    if out.exists():
        shutil.rmtree(out)
    bootstrap_session_workspace(
        recap_path=BOOTSTRAP_RECAP,
        campaign_id="longmont-c2",
        session=session,
        output_dir=out,
        source_session=session - 1,
        next_session_label=f"Session {session}",
        force=True,
    )
    return out


# --- committed-artifact boundary -------------------------------------------------


def test_committed_artifact_validates_against_schema() -> None:
    manifest = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    _validator().validate(manifest)
    assert manifest["schema"] == SCHEMA_ID
    assert len(manifest["entries"]) > 0


def test_builder_output_validates_against_schema() -> None:
    _validator().validate(_build_real())


def test_committed_artifact_matches_fresh_builder_output() -> None:
    committed = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
    fresh = _build_real()
    assert _without_generated_at(committed) == _without_generated_at(fresh)


# --- planning workspace session alignment ----------------------------------------


def test_manifest_uses_session_23_planning_live_workspace() -> None:
    manifest = _build_real()
    assert manifest["planning_session"] == 23
    assert manifest["planning_live_workspace_dir"] == "evals/c2_live_prep/live/session_23"
    live_entries = [
        e
        for e in manifest["entries"]
        if e["source_role"] in ("live_packet", "live_event", "fresh_recap")
    ]
    assert live_entries
    for entry in live_entries:
        assert entry["session_scope"] == [23]
        assert "/session_23/" in entry["route"]


def test_live_workspace_session_mismatch_raises_by_default(tmp_path: Path) -> None:
    workspace = _bootstrap_workspace(tmp_path, session=22)
    with pytest.raises(ValueError, match="live_packet.session \\(22\\)"):
        build_planning_corpus_manifest(
            campaign_id="longmont-c2",
            planning_session=23,
            source_sessions=[21, 22],
            corpus_root=CORPUS_ROOT,
            live_workspace_dir=workspace,
        )


def test_live_workspace_session_mismatch_escape_hatch(tmp_path: Path) -> None:
    workspace = _bootstrap_workspace(tmp_path, session=22)
    manifest = build_planning_corpus_manifest(
        campaign_id="longmont-c2",
        planning_session=23,
        source_sessions=[21, 22],
        corpus_root=CORPUS_ROOT,
        live_workspace_dir=workspace,
        allow_live_workspace_session_mismatch=True,
    )
    live_packet = next(e for e in manifest["entries"] if e["source_role"] == "live_packet")
    assert live_packet["session_scope"] == [23]
    assert "/session_22/" in live_packet["route"]


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
            assert PLAY_FACT_USE in entry["forbidden_uses"], entry["route"]


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
            assert PLAY_FACT_USE in entry["forbidden_uses"], entry["route"]
        else:
            assert PLAY_FACT_USE not in entry["forbidden_uses"], entry["route"]


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
    assert PLAY_FACT_USE in notes_with["forbidden_uses"]
    assert PLAY_FACT_USE not in notes_without["forbidden_uses"]


def test_non_materialized_entries_are_not_admissible_and_cannot_prove_play_facts() -> None:
    manifest = _build_real()
    missing = [e for e in manifest["entries"] if not e["route_exists"]]
    for entry in missing:
        assert entry["admissible"] is False
        assert entry["allowed_uses"] == []
        assert PLAY_FACT_USE in entry["forbidden_uses"], entry["source_id"]


def test_admissible_play_fact_candidates_exclude_non_existing_routes() -> None:
    manifest = _build_real()
    candidates = [
        e
        for e in manifest["entries"]
        if e["admissible"] and PLAY_FACT_USE in e["allowed_uses"]
    ]
    assert candidates
    for entry in candidates:
        assert entry["route_exists"] is True


# --- honest gaps -----------------------------------------------------------------


def test_session_22_recap_derivatives_are_materialized() -> None:
    manifest = _build_real()
    s22_recap = [
        e
        for e in manifest["entries"]
        if e["source_role"] == "play_recap" and e["session_scope"] == [22]
    ]
    assert len(s22_recap) == 3
    assert all(e["route_exists"] is True for e in s22_recap)


def test_session_23_recap_derivatives_are_materialized() -> None:
    manifest = _build_real()
    s23_recap = [
        e
        for e in manifest["entries"]
        if e["source_role"] == "play_recap" and e["session_scope"] == [23]
    ]
    assert len(s23_recap) == 3
    assert all(e["route_exists"] is True for e in s23_recap)
    assert any("session-23-mireward" in e["route"] for e in s23_recap)


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
    ids = [e["source_id"] for e in first["entries"]]
    assert len(ids) == len(set(ids))


def test_duplicate_roll_table_routes_are_deduped() -> None:
    manifest = _build_real()
    roll_tables = [e for e in manifest["entries"] if e["source_role"] == "roll_table"]
    routes = [e["route"] for e in roll_tables]
    assert routes
    assert len(routes) == len(set(routes))


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
    for entry in manifest["entries"]:
        assert entry["route"] in first


# --- dogfood-full manifest -------------------------------------------------------


def test_dogfood_full_manifest_validates_and_meets_entry_floor() -> None:
    manifest = _build_dogfood_full()
    _validator().validate(manifest)
    assert manifest["schema"] == DOGFOOD_FULL_SCHEMA_ID
    assert len(manifest["entries"]) >= 160
    s23_recap = [
        e
        for e in manifest["entries"]
        if e["source_role"] == "play_recap" and e["session_scope"] == [23]
    ]
    assert len(s23_recap) == 3
    assert all(e["route_exists"] is True for e in s23_recap)
    missing = [e for e in manifest["entries"] if not e["route_exists"]]
    assert not any("(uningested)" in e["route"] for e in missing)


def test_dogfood_full_includes_every_elderwyld_md_once() -> None:
    manifest = _build_dogfood_full()
    elderwyld_paths = {
        p.relative_to(CORPUS_ROOT).as_posix()
        for p in (CORPUS_ROOT / "Elderwyld").rglob("*.md")
    }
    world_routes = {
        e["route"].removeprefix("corpus/eldyrwild-markdown/")
        for e in manifest["entries"]
        if e["source_role"] == "world_evidence"
    }
    assert elderwyld_paths == world_routes


def test_dogfood_full_includes_c2_hub_satellites() -> None:
    manifest = _build_dogfood_full()
    hub_satellite_routes = {
        e["route"]
        for e in manifest["entries"]
        if e["source_role"] == "hub_evidence" and e["route"].endswith(".md") and not e["route"].endswith("README.md")
    }
    assert any("NPCs/thrin_branchborn/timeline.md" in r for r in hub_satellite_routes)
    assert any("PCs/karsemine/karsemine_statblock" in r for r in hub_satellite_routes)


def test_world_evidence_entries_forbid_play_facts_in_allowed_uses() -> None:
    manifest = _build_dogfood_full()
    for entry in manifest["entries"]:
        if entry["source_role"] != "world_evidence":
            continue
        assert PLAY_FACT_USE not in entry["allowed_uses"]
        assert PLAY_FACT_USE in entry["forbidden_uses"]


def test_committed_dogfood_artifact_matches_fresh_builder_output() -> None:
    if not DOGFOOD_ARTIFACT_PATH.is_file():
        pytest.skip("dogfood-full manifest artifact not committed yet")
    committed = json.loads(DOGFOOD_ARTIFACT_PATH.read_text(encoding="utf-8"))
    fresh = _build_dogfood_full()
    assert _without_generated_at(committed) == _without_generated_at(fresh)
