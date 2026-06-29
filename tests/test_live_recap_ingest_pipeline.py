from __future__ import annotations

import io
from pathlib import Path

import pytest

from src.corpus.session_recap_paths import (
    is_generic_recap_tail,
    normalized_basename_from_disk,
)
from src.live_play.recap_ingest_pipeline import PipelineOptions, inspect_recap_ingest_status, run_pipeline

ROOT = Path(__file__).resolve().parents[1]
RAW_FIXTURE = ROOT / "tests/fixtures/live_recap_ingest/session_22_raw_recap.md"


def _seed_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus/eldyrwild-markdown"
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    prep = campaign / "Session Prep/session_22"
    prep.mkdir(parents=True, exist_ok=True)
    (prep / "session_22_travel.md").write_text("prep", encoding="utf-8")
    npcs = campaign / "NPCs/captain_lysandra_ironveil"
    npcs.mkdir(parents=True, exist_ok=True)
    (npcs / "timeline.md").write_text("| Session | Beat (short) | Recap / prep |\n", encoding="utf-8")
    return corpus


def _opts(**kwargs: object) -> PipelineOptions:
    base: dict[str, object] = {
        "campaign_id": "longmont-c2",
        "session": 22,
        "raw_path": RAW_FIXTURE,
        "raw_stdin": False,
        "title": None,
        "slug": None,
        "stage": True,
        "preview": True,
        "apply": False,
        "normalize": False,
        "materialize_session_memory": False,
        "check": False,
        "force_stage": False,
        "force_recap": False,
        "json_output": False,
    }
    base.update(kwargs)
    return PipelineOptions(**base)


def test_stage_preview_reports_ingest_details(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(_opts(), corpus=corpus)
    assert status["status"] == "breadcrumb_required"
    assert "staged_raw_notes_created" in status["states"]
    assert "recap_preview_created" in status["states"]
    ingest = status["ingest_report"]
    assert ingest["title_line_stripped"] is True
    assert ingest["paragraph_count_in"] >= 5
    assert ingest["duplicates_detected"] == 0


def test_stage_reuses_existing_notes_as_review_gate_without_force(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.write_text("old raw notes", encoding="utf-8")
    status = run_pipeline(_opts(), corpus=corpus)
    assert status["status"] == "breadcrumb_required"
    assert "staged_raw_notes_conflict" in status["states"]
    assert any("force-stage" in msg for msg in status["next_actions"])
    assert staged.read_text(encoding="utf-8") == "old raw notes"


def test_stage_overwrites_with_force_stage(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.write_text("old raw notes", encoding="utf-8")
    status = run_pipeline(_opts(force_stage=True), corpus=corpus)
    assert status["status"] == "breadcrumb_required"
    assert staged.read_text(encoding="utf-8").startswith("Session 22 Recap")


def test_pipeline_returns_reconciliation_state_for_duplicate_normalized_recaps(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    norm_dir = corpus / "Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    (norm_dir / "Session 22 - Mireward Road and Lysandro.md").write_text("canon", encoding="utf-8")
    (norm_dir / "Session 22 - Mireward.md").write_text("partial duplicate", encoding="utf-8")

    status = run_pipeline(
        _opts(
            stage=False,
            preview=False,
            apply=False,
            normalize=False,
            materialize_session_memory=True,
            slug="Mireward Road and Lysandro",
        ),
        corpus=corpus,
    )

    assert status["status"] == "needs_reconciliation"
    assert "normalized_recap_duplicates" in status["states"]
    assert "expected exactly one normalized recap" not in " ".join(status["errors"])


def test_normalized_basename_prefers_single_non_generic_over_numeric_duplicate(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    norm_dir = corpus / "Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    (norm_dir / "Session 24 - Mireward Gate Battle.md").write_text("canon", encoding="utf-8")
    (norm_dir / "Session 24 - 4.md").write_text("numeric duplicate", encoding="utf-8")

    assert is_generic_recap_tail("Session 24 - 4") is True
    assert (
        normalized_basename_from_disk(corpus, campaign_number=2, session=24)
        == "Session 24 - Mireward Gate Battle"
    )


def test_apply_requires_non_generic_slug_or_title(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(_opts(apply=True), corpus=corpus)
    assert status["status"] == "error"
    assert "recap_apply_blocked_slug_required" in status["states"]


def test_apply_writes_canonical_recap_path(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(_opts(apply=True, slug="Mireward Road and Lysandro"), corpus=corpus)
    recap_path = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    assert status["status"] == "breadcrumb_required"
    assert "recap_applied" in status["states"]
    text = recap_path.read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "# Session 22 Recap" in text
    assert not text.split("# Session 22 Recap", 1)[1].lstrip().startswith("Session 22 Recap")


def test_apply_reuses_existing_recap_without_force(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    recap_path = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    recap_path.write_text("existing", encoding="utf-8")
    status = run_pipeline(_opts(apply=True, slug="Mireward Road and Lysandro"), corpus=corpus)
    assert status["status"] == "breadcrumb_required"
    assert "recap_reused" in status["states"]
    assert recap_path.read_text(encoding="utf-8") == "existing"


def test_normalize_reuses_existing_normalized(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    recap_path = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    normalized = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text(
        "---\ntitle: Session 22 - Mireward Road and Lysandro\n---\n# Session 22 Recap\n",
        encoding="utf-8",
    )
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text("existing normalized", encoding="utf-8")
    status = run_pipeline(
        _opts(apply=True, normalize=True, slug="Mireward Road and Lysandro"),
        corpus=corpus,
    )
    assert status["status"] == "breadcrumb_required"
    assert "normalized_reused" in status["states"]
    assert normalized.read_text(encoding="utf-8") == "existing normalized"


def test_inspect_status_reports_disk_progress(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    recap_path = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    normalized = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    breadcrumb = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    )
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text("canonical", encoding="utf-8")
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text("normalized", encoding="utf-8")
    breadcrumb.parent.mkdir(parents=True, exist_ok=True)
    breadcrumb.write_text("breadcrumb", encoding="utf-8")

    status = inspect_recap_ingest_status(
        campaign_id="longmont-c2",
        session=22,
        title="Session 22 - Mireward Road and Lysandro",
        slug="Mireward Road and Lysandro",
        corpus=corpus,
    )
    assert status["status"] == "recap_applied"
    assert "ingest_status_inspected" in status["states"]
    assert "recap_reused" in status["states"]
    assert "normalized_reused" in status["states"]
    assert "breadcrumb_found" in status["states"]
    assert any("Materialize Session Memory" in item for item in status["next_actions"])


def test_inspect_status_reports_frontmatter_seed_without_breadcrumb(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    normalized = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    seed = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.frontmatter_seed.md"
    )
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text("normalized", encoding="utf-8")
    seed.parent.mkdir(parents=True, exist_ok=True)
    seed.write_text("---\n---\n", encoding="utf-8")

    status = inspect_recap_ingest_status(
        campaign_id="longmont-c2",
        session=22,
        title="Session 22 - Mireward Road and Lysandro",
        slug="Mireward Road and Lysandro",
        corpus=corpus,
    )

    assert status["status"] == "breadcrumb_required"
    assert "frontmatter_seed_found" in status["states"]
    assert "frontmatter_seed_required" not in status["states"]
    assert status["paths"]["frontmatter_seed"].endswith(
        "Session 22 - Mireward Road and Lysandro.frontmatter_seed.md"
    )
    assert any("breadcrumb_query_run --ingest-routing-only" in item for item in status["next_actions"])


def test_apply_force_recap_overwrites_target_only(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    recap_path = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    recap_path.write_text("existing", encoding="utf-8")
    prep_path = corpus / "Longmont Campaign/Campaign 2/Session Prep/session_22/session_22_travel.md"
    prep_before = prep_path.read_text(encoding="utf-8")
    status = run_pipeline(
        _opts(apply=True, slug="Mireward Road and Lysandro", force_recap=True),
        corpus=corpus,
    )
    assert status["status"] == "breadcrumb_required"
    assert recap_path.read_text(encoding="utf-8").startswith("---")
    assert prep_path.read_text(encoding="utf-8") == prep_before


def test_normalize_creates_target_file(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(
        _opts(apply=True, normalize=True, slug="Mireward Road and Lysandro"),
        corpus=corpus,
    )
    normalized = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    assert status["status"] == "breadcrumb_required"
    assert "normalized_created" in status["states"]
    assert "frontmatter_seed_required" in status["states"]
    assert "frontmatter_seed" in status["paths"]
    assert any("build_recap_frontmatter_seed.py" in item for item in status["next_actions"])
    assert normalized.is_file()


def test_materialize_requires_breadcrumb(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(
        _opts(
            apply=True,
            normalize=True,
            slug="Mireward Road and Lysandro",
            materialize_session_memory=True,
        ),
        corpus=corpus,
    )
    assert status["status"] == "breadcrumb_required"
    assert "session_memory_skipped" in status["states"]
    assert any("build_recap_frontmatter_seed.py" in item for item in status["next_actions"])
    assert any("breadcrumb_query_run --ingest-routing-only" in item for item in status["next_actions"])


def test_materialize_runs_when_breadcrumb_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = _seed_corpus(tmp_path)
    breadcrumb = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    )
    breadcrumb.parent.mkdir(parents=True, exist_ok=True)
    breadcrumb.write_text("---\n---\n", encoding="utf-8")

    called: dict[str, bool] = {"materialize": False, "check": False}

    def _fake_materialize_one(**_kwargs: object) -> dict[str, object]:
        called["materialize"] = True
        return {"record_count": 7}

    def _fake_check_one(**_kwargs: object) -> bool:
        called["check"] = True
        return True

    monkeypatch.setattr("src.live_play.recap_ingest_pipeline._materialize_one", _fake_materialize_one)
    monkeypatch.setattr("src.live_play.recap_ingest_pipeline._check_one", _fake_check_one)

    status = run_pipeline(
        _opts(
            slug="Mireward Road and Lysandro",
            materialize_session_memory=True,
            check=True,
            apply=False,
            preview=False,
            stage=False,
        ),
        corpus=corpus,
    )
    assert called["materialize"] is True
    assert called["check"] is True
    assert status["status"] == "ready_for_planning_activation"
    assert "session_memory_materialized" in status["states"]
    assert status["ingest_report"]["session_memory_record_count"] == 7


def test_materialize_uses_disk_breadcrumb_when_slug_mismatches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = _seed_corpus(tmp_path)
    recap = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    )
    normalized = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    breadcrumb = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    )
    recap.parent.mkdir(parents=True, exist_ok=True)
    recap.write_text("---\ntitle: Session 22 - Mireward Road and Lysandro\n---\n# Session 22 Recap\n", encoding="utf-8")
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text("---\ntitle: Session 22 - Mireward Road and Lysandro\n---\n# Session 22 Recap\n", encoding="utf-8")
    breadcrumb.parent.mkdir(parents=True, exist_ok=True)
    breadcrumb.write_text("---\n---\n", encoding="utf-8")

    called: dict[str, bool] = {"materialize": False}

    def _fake_materialize_one(**_kwargs: object) -> dict[str, object]:
        called["materialize"] = True
        return {"record_count": 3}

    monkeypatch.setattr("src.live_play.recap_ingest_pipeline._materialize_one", _fake_materialize_one)
    monkeypatch.setattr("src.live_play.recap_ingest_pipeline._check_one", lambda **_kwargs: True)

    status = run_pipeline(
        _opts(
            slug="Wrong Slug Entirely",
            materialize_session_memory=True,
            check=True,
            apply=False,
            preview=False,
            stage=False,
        ),
        corpus=corpus,
    )
    assert called["materialize"] is True
    assert status["status"] == "ready_for_planning_activation"
    assert "breadcrumb_found" in status["states"]
    assert "slug_mismatch_used_disk_breadcrumb" in status["warnings"]
    assert status["paths"]["breadcrumbed_recap"].endswith("Mireward Road and Lysandro.breadcrumbed.md")


def test_status_includes_authority_and_spelling_audit(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(_opts(), corpus=corpus)
    assert status["authority"]["canonical_recap"] == "canon_play"
    assert status["entity_spelling_audit"]
    assert "entity spelling variants detected; review_only" in status["warnings"]


def test_invalid_utf8_raw_path_fails(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe")
    status = run_pipeline(_opts(raw_path=bad), corpus=corpus)
    assert status["status"] == "error"
    assert status["errors"]


def test_empty_raw_text_fails(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    empty = tmp_path / "empty.md"
    empty.write_text(" \n", encoding="utf-8")
    status = run_pipeline(_opts(raw_path=empty), corpus=corpus)
    assert status["status"] == "error"
    assert any("empty" in item for item in status["errors"])


def test_path_traversal_raw_path_rejected(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(
        _opts(raw_path=Path("../outside.md")),
        corpus=corpus,
    )
    assert status["status"] == "error"
    assert any("traversal" in item for item in status["errors"])


def test_raw_stdin_input_works(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(
        _opts(raw_path=None, raw_stdin=True),
        corpus=corpus,
        stdin=io.StringIO(RAW_FIXTURE.read_text(encoding="utf-8")),
    )
    assert status["status"] == "breadcrumb_required"
    assert "raw_text_received" in status["states"]


def test_default_safe_mode_does_not_create_embeddings_or_live_files(tmp_path: Path) -> None:
    corpus = _seed_corpus(tmp_path)
    status = run_pipeline(_opts(), corpus=corpus)
    assert status["status"] == "breadcrumb_required"
    files = [p for p in corpus.rglob("*") if p.is_file()]
    for path in files:
        lower = path.name.lower()
        assert "embedding" not in lower
        assert path.suffix not in {".faiss", ".npy"}
        assert path.name not in {
            "live_packet.json",
            "event_log.jsonl",
            "job_queue.jsonl",
            "current_state.json",
        }
