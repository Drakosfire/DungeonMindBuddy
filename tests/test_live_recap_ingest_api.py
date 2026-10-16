from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.routes import recap_ingest as recap_ingest_route
from src.corpus.session_recap_paths import normalized_recap_relpath
from src.live_play.recap_ingest_pipeline import _expected_normalized_content

ROOT = Path(__file__).resolve().parents[1]
SEED_SESSION = ROOT / "evals/c2_live_prep/live/session_22"
CORPUS_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"


def _seed_corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus/eldyrwild-markdown"
    campaign = corpus / "Longmont Campaign/Campaign 2"
    (campaign / "_ingest_staging").mkdir(parents=True, exist_ok=True)
    (campaign / "Session Recaps").mkdir(parents=True, exist_ok=True)
    return corpus


@pytest.fixture
def isolated_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(SEED_SESSION / name, tmp_path / name)
    (tmp_path / "event_log.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(tmp_path))
    corpus = _seed_corpus(tmp_path)
    monkeypatch.setenv(CORPUS_ENV, str(corpus))
    return tmp_path


@pytest.fixture
def client(isolated_session: Path) -> TestClient:
    return TestClient(create_app())


def _raw_text() -> str:
    return (
        "Session 22 Recap\n\n"
        "The group turns their focus toward the Reach road.\n\n"
        "After another failed attempt to contact Mirathorn, Caeylynn keeps watch."
    )


def _write_current_normalized(corpus: Path, *, session: int = 22) -> Path:
    title = "Mireward Road and Lysandro"
    canonical_rel = f"Longmont Campaign/Campaign 2/Session Recaps/Session {session} - {title}.md"
    canonical = corpus / canonical_rel
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        f"---\ntitle: Session {session} - {title}\nsession: {session}\n---\nThe group travels.\n",
        encoding="utf-8",
    )
    normalized = corpus / normalized_recap_relpath(
        campaign_number=2, session=session, title=title
    )
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(
        _expected_normalized_content(corpus=corpus, canonical_recap_rel=canonical_rel),
        encoding="utf-8",
    )
    return normalized


def test_stage_preview_accepts_raw_text_and_returns_status_schema(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_raw_recap_ingest_status_v1"
    assert body["campaign_id"] == "longmont-c2"
    assert "recap_preview_created" in body["states"]
    assert body["authority"]["canonical_recap"] == "canon_play"
    assert isinstance(body["entity_spelling_audit"], list)


def test_stage_preview_stages_and_previews_only(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    staged = corpus / str(body["paths"]["staged_raw_notes"])
    canonical = corpus / str(body["paths"]["canonical_recap"])
    assert staged.is_file()
    assert not canonical.exists()


def test_stage_preview_reuses_existing_staged_notes_as_review_gate(
    client: TestClient, isolated_session: Path
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.write_text("Existing staged notes are the review source.", encoding="utf-8")

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "Different pasted notes should not overwrite without force.",
            "slug": "Mireward Road and Lysandro",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "breadcrumb_required"
    assert "staged_raw_notes_reused" in body["states"]
    assert "staged_raw_notes_conflict" in body["states"]
    assert "recap_preview_created" in body["states"]
    assert "staged raw notes already exists; pasted raw text was not used" in body["warnings"]
    assert staged.read_text(encoding="utf-8") == "Existing staged notes are the review source."
    assert (
        "Review the preview generated from the existing staged notes, "
        "or enable --force-stage to overwrite them with the pasted text."
    ) in body["next_actions"]


def test_stage_preview_rejects_empty_raw_text(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "   ",
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


def test_stage_preview_rejects_raw_path_input(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "raw_path": "/tmp/notes.md",
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


def test_apply_normalize_requires_non_generic_slug_or_title(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Recap",
        },
    )
    assert response.status_code == 422


def test_apply_normalize_rejects_tool_shaped_ingest_slug(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 23,
            "slug": "ingest",
        },
    )
    assert response.status_code == 422
    assert "non-generic slug or title" in response.json()["detail"]

    response_with_title = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 23,
            "slug": "ingest",
            "title": "Session 23 - Mireward Gate Battle",
        },
    )
    assert response_with_title.status_code == 422
    assert "non-generic slug or title" in response_with_title.json()["detail"]


def test_apply_normalize_reuses_staged_raw_and_returns_breadcrumb_required(
    client: TestClient, isolated_session: Path
) -> None:
    stage = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert stage.status_code == 200
    apply = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "apply_normalize",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert apply.status_code == 200
    body = apply.json()
    assert body["status"] == "breadcrumb_required"
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    canonical = corpus / str(body["paths"]["canonical_recap"])
    assert canonical.exists()


def test_materialize_session_memory_returns_breadcrumb_required_when_missing(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "materialize_session_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
            "check": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "breadcrumb_required"
    assert "session_memory_skipped" in body["states"]


def test_build_frontmatter_seed_writes_reviewable_seed(
    client: TestClient,
    isolated_session: Path,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_frontmatter_seed",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )

    assert response.status_code == 200
    body = response.json()
    seed = corpus / str(body["paths"]["frontmatter_seed"])
    assert seed.is_file()
    assert seed.with_name(f"{seed.name}.provenance.json").is_file()
    assert "frontmatter_seed_built" in body["states"]
    assert "frontmatter_seed_found" in body["states"]
    assert "breadcrumb_required" in body["states"]


def test_reviewed_seed_is_preserved_and_explicit_refresh_archives_it(
    client: TestClient,
    isolated_session: Path,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)
    payload = {
        "operation": "build_frontmatter_seed",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }
    initial = client.post("/api/live/recap-ingest", json=payload)
    assert initial.status_code == 200
    seed = corpus / str(initial.json()["paths"]["frontmatter_seed"])
    reviewed_bytes = b"---\nreviewed: true\n---\nReviewed routing seed\n"
    seed.write_bytes(reviewed_bytes)

    preserved = client.post("/api/live/recap-ingest", json=payload)
    assert preserved.status_code == 200
    assert "frontmatter_seed_edited_current_inputs" in preserved.json()["states"]
    assert seed.read_bytes() == reviewed_bytes

    refreshed = client.post(
        "/api/live/recap-ingest", json={**payload, "force_seed": True}
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert "frontmatter_seed_refreshed" in body["states"]
    assert "frontmatter_seed_current" in body["states"]
    assert seed.read_bytes() != reviewed_bytes
    archived = body["ingest_report"]["archived_artifacts"]
    assert len(archived) == 2
    archived_seed = next(row for row in archived if row["from"].endswith(".frontmatter_seed.md"))
    assert (corpus / archived_seed["to"]).read_bytes() == reviewed_bytes


def test_run_breadcrumb_ingest_writes_artifact_without_materializing(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)
    seed = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.frontmatter_seed.md"
    )
    seed.parent.mkdir(parents=True, exist_ok=True)
    build_seed_response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_frontmatter_seed",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert build_seed_response.status_code == 200

    def _fake_run_breadcrumb(**kwargs: object) -> dict[str, object]:
        out_path = kwargs["out_path"]
        assert isinstance(out_path, Path)
        out_path.write_text(
            "---\n"
            'source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"\n'
            "campaign_id: longmont-c2\n"
            "session:\n"
            "  number: 22\n"
            "---\n"
            "The group travels.\n",
            encoding="utf-8",
        )
        return {"artifact_path": str(out_path), "cost_usd": 0.0}

    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest._run_routing_only_breadcrumb",
        _fake_run_breadcrumb,
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "run_breadcrumb_ingest",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )

    assert response.status_code == 200
    body = response.json()
    breadcrumb = corpus / str(body["paths"]["breadcrumbed_recap"])
    assert breadcrumb.is_file()
    assert "breadcrumb_ingest_ran" in body["states"]
    assert "breadcrumb_found" in body["states"]
    assert "session_memory_materialized" not in body["states"]


@pytest.mark.parametrize(
    ("invalid_mutation", "expected_detail"),
    [
        ("wrong_source", "source_recap_path does not match"),
        ("body_mismatch", "breadcrumb plain text"),
    ],
)
def test_invalid_refreshed_breadcrumb_preserves_current_artifact_and_lineage(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
    invalid_mutation: str,
    expected_detail: str,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)
    seed_response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_frontmatter_seed",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert seed_response.status_code == 200

    correct_source = (
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    generated = {
        "content": (
            "---\n"
            f'source_recap_path: "{correct_source}"\n'
            "campaign_id: longmont-c2\n"
            "session:\n"
            "  number: 22\n"
            "---\n"
            "The group travels.\n"
        )
    }

    def _fake_run_breadcrumb(**kwargs: object) -> dict[str, object]:
        out_path = kwargs["out_path"]
        assert isinstance(out_path, Path)
        out_path.write_text(generated["content"], encoding="utf-8")
        return {"artifact_path": str(out_path), "cost_usd": 0.0}

    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest._run_routing_only_breadcrumb",
        _fake_run_breadcrumb,
    )
    payload = {
        "operation": "run_breadcrumb_ingest",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }
    created = client.post("/api/live/recap-ingest", json=payload)
    assert created.status_code == 200
    breadcrumb = corpus / str(created.json()["paths"]["breadcrumbed_recap"])
    sidecar = breadcrumb.with_name(f"{breadcrumb.name}.provenance.json")
    previous_breadcrumb = breadcrumb.read_bytes()
    previous_sidecar = sidecar.read_bytes()

    if invalid_mutation == "wrong_source":
        generated["content"] = generated["content"].replace(
            correct_source, "Longmont Campaign/Campaign 2/Session Recaps/wrong.md"
        )
    else:
        generated["content"] = generated["content"].replace(
            "The group travels.", "The party waits."
        )
    rejected = client.post(
        "/api/live/recap-ingest",
        json={**payload, "force_breadcrumb": True},
    )

    assert rejected.status_code == 422
    assert expected_detail in rejected.json()["detail"]
    assert breadcrumb.read_bytes() == previous_breadcrumb
    assert sidecar.read_bytes() == previous_sidecar
    assert not (breadcrumb.parent / "_archive").exists()


def test_legacy_breadcrumb_is_not_rerun_until_explicit_refresh(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)
    seed_response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_frontmatter_seed",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert seed_response.status_code == 200
    breadcrumb = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/"
        "Session 22 - Mireward Road and Lysandro.breadcrumbed.md"
    )
    breadcrumb.write_text("legacy output that must be preserved", encoding="utf-8")
    calls: list[Path] = []

    def _fake_run_breadcrumb(**kwargs: object) -> dict[str, object]:
        out_path = kwargs["out_path"]
        assert isinstance(out_path, Path)
        calls.append(out_path)
        out_path.write_text(
            "---\n"
            'source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"\n'
            "campaign_id: longmont-c2\n"
            "session:\n"
            "  number: 22\n"
            "---\n"
            "The group travels.\n",
            encoding="utf-8",
        )
        return {"artifact_path": str(out_path), "cost_usd": 0.0}

    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest._run_routing_only_breadcrumb",
        _fake_run_breadcrumb,
    )
    payload = {
        "operation": "run_breadcrumb_ingest",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }

    blocked = client.post("/api/live/recap-ingest", json=payload)
    assert blocked.status_code == 200
    assert blocked.json()["status"] == "needs_reconciliation"
    assert "breadcrumb_provenance_unknown" in blocked.json()["states"]
    assert calls == []
    assert breadcrumb.read_text(encoding="utf-8") == "legacy output that must be preserved"

    refreshed = client.post(
        "/api/live/recap-ingest", json={**payload, "force_breadcrumb": True}
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert "breadcrumb_ingest_refreshed" in body["states"]
    assert "breadcrumb_current" in body["states"]
    assert 'source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"' in breadcrumb.read_text(encoding="utf-8")
    assert len(calls) == 1
    archived = body["ingest_report"]["archived_artifacts"]
    assert len(archived) == 1
    assert (corpus / archived[0]["to"]).read_text(encoding="utf-8") == "legacy output that must be preserved"


def test_materialize_preserves_drift_until_explicit_refresh(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _write_current_normalized(corpus)
    seed = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "build_frontmatter_seed",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert seed.status_code == 200

    def _fake_run_breadcrumb(**kwargs: object) -> dict[str, object]:
        out_path = kwargs["out_path"]
        assert isinstance(out_path, Path)
        out_path.write_text(
            "---\n"
            'source_recap_path: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md"\n'
            "campaign_id: longmont-c2\n"
            "session:\n"
            "  number: 22\n"
            "---\n"
            "The group travels.\n",
            encoding="utf-8",
        )
        return {"artifact_path": str(out_path), "cost_usd": 0.0}

    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest._run_routing_only_breadcrumb",
        _fake_run_breadcrumb,
    )
    breadcrumb = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "run_breadcrumb_ingest",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert breadcrumb.status_code == 200
    materialize_request = {
        "operation": "materialize_session_memory",
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }
    first = client.post("/api/live/recap-ingest", json=materialize_request)
    assert first.status_code == 200
    assert "session_memory_current" in first.json()["states"]

    memory_jsonl = corpus / str(first.json()["paths"]["session_memory_jsonl"])
    previous_jsonl = b"reviewed memory bytes\n"
    memory_jsonl.write_bytes(previous_jsonl)
    preserved = client.post("/api/live/recap-ingest", json=materialize_request)
    assert preserved.status_code == 200
    assert preserved.json()["status"] == "needs_reconciliation"
    assert "session_memory_stale" in preserved.json()["states"]
    assert memory_jsonl.read_bytes() == previous_jsonl

    refreshed = client.post(
        "/api/live/recap-ingest",
        json={**materialize_request, "force_session_memory": True},
    )
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert "session_memory_current" in body["states"]
    assert memory_jsonl.read_bytes() != previous_jsonl
    archived = body["ingest_report"]["archived_artifacts"]
    assert len(archived) == 2
    archived_jsonl = next(row for row in archived if row["from"].endswith(".records_meta.jsonl"))
    assert (corpus / archived_jsonl["to"]).read_bytes() == previous_jsonl


def test_generate_recap_memory_refreshes_lineage_chain_and_reports_every_archive(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    normalized = _write_current_normalized(corpus)
    base_request = {
        "campaign_id": "longmont-c2",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }
    seed_response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "build_frontmatter_seed", **base_request},
    )
    assert seed_response.status_code == 200
    seed_path = corpus / str(seed_response.json()["paths"]["frontmatter_seed"])

    def _fake_run_breadcrumb(**kwargs: object) -> dict[str, object]:
        out_path = kwargs["out_path"]
        assert isinstance(out_path, Path)
        out_path.write_text(
            "---\n"
            f'source_recap_path: "{normalized.relative_to(corpus).as_posix()}"\n'
            "campaign_id: longmont-c2\n"
            "session:\n"
            "  number: 22\n"
            "---\n"
            "The group travels.\n",
            encoding="utf-8",
        )
        return {"artifact_path": str(out_path), "cost_usd": 0.0}

    monkeypatch.setattr(
        "apps.live_control_server.routes.recap_ingest._run_routing_only_breadcrumb",
        _fake_run_breadcrumb,
    )
    first_breadcrumb = client.post(
        "/api/live/recap-ingest",
        json={"operation": "run_breadcrumb_ingest", **base_request},
    )
    assert first_breadcrumb.status_code == 200
    first_memory = client.post(
        "/api/live/recap-ingest",
        json={"operation": "materialize_session_memory", **base_request},
    )
    assert first_memory.status_code == 200
    paths = first_memory.json()["paths"]
    breadcrumb_path = corpus / str(paths["breadcrumbed_recap"])
    previous_breadcrumb = breadcrumb_path.read_bytes()
    memory_jsonl = corpus / str(paths["session_memory_jsonl"])

    reviewed_seed = b"---\nreviewed: true\n---\nReviewed routing targets\n"
    seed_path.write_bytes(reviewed_seed)
    drifted_memory = b"reviewed memory that explicit refresh must archive\n"
    memory_jsonl.write_bytes(drifted_memory)

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            **base_request,
            "include_graph_extraction": False,
            "include_legacy_breadcrumb": True,
            "force_seed": True,
            "force_breadcrumb": True,
            "force_session_memory": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_planning_activation"
    assert "session_memory_current" in body["states"]
    assert "derivative_reconciliation_required" not in body["states"]
    assert seed_path.read_bytes() != reviewed_seed
    assert memory_jsonl.read_bytes() != drifted_memory

    archived = body["ingest_report"]["archived_artifacts"]
    assert len(archived) == 6
    archived_from = {row["from"] for row in archived}
    assert any(path.endswith(".frontmatter_seed.md") for path in archived_from)
    assert any(path.endswith(".frontmatter_seed.md.provenance.json") for path in archived_from)
    assert any(path.endswith(".breadcrumbed.md") for path in archived_from)
    assert any(path.endswith(".breadcrumbed.md.provenance.json") for path in archived_from)
    assert any(path.endswith(".records_meta.jsonl") for path in archived_from)
    assert any(path.endswith(".records_meta.json") for path in archived_from)
    by_source = {row["from"]: row for row in archived}
    seed_archive = next(path for path in archived_from if path.endswith(".frontmatter_seed.md"))
    memory_archive = next(path for path in archived_from if path.endswith(".records_meta.jsonl"))
    breadcrumb_archive = next(path for path in archived_from if path.endswith(".breadcrumbed.md"))
    assert (corpus / by_source[seed_archive]["to"]).read_bytes() == reviewed_seed
    assert (corpus / by_source[memory_archive]["to"]).read_bytes() == drifted_memory
    assert (corpus / by_source[breadcrumb_archive]["to"]).read_bytes() == previous_breadcrumb


def test_api_never_writes_live_workspace_files(client: TestClient, isolated_session: Path) -> None:
    watched = {
        name: (isolated_session / name).read_bytes()
        for name in ("live_packet.json", "event_log.jsonl", "job_queue.jsonl", "current_state.json")
    }
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    for name, value in watched.items():
        assert (isolated_session / name).read_bytes() == value


def test_api_never_writes_embedding_or_retrieval_indexes(client: TestClient, isolated_session: Path) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "stage_preview",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    for file in corpus.rglob("*"):
        if not file.is_file():
            continue
        assert "embedding" not in file.name.lower()
        assert file.suffix not in {".faiss", ".npy"}


def test_invalid_operation_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "not_valid",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


def _seed_duplicate_normalized(corpus: Path) -> tuple[Path, Path]:
    norm_dir = corpus / "Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    canonical = norm_dir / "Session 23 - Mireward Gate Battle.md"
    generic = norm_dir / "Session 23 - ingest.md"
    canonical.write_text(
        "---\ntitle: Session 23 - Mireward Gate Battle\n---\nThe gate battle.\n",
        encoding="utf-8",
    )
    generic.write_text(
        "---\ntitle: Session 23 - ingest\n---\nTool-shaped duplicate.\n",
        encoding="utf-8",
    )
    return canonical, generic


def test_inspect_status_flags_duplicate_normalized_recaps(
    client: TestClient, isolated_session: Path
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _seed_duplicate_normalized(corpus)
    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "inspect_status", "campaign_id": "longmont-c2", "session": 23},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_reconciliation"
    assert "derivative_reconciliation_required" in body["states"]
    assert "normalized_recap_duplicates" in body["states"]
    candidates = body["ingest_report"]["normalized_recap_candidates"]
    assert {row["basename"] for row in candidates} == {
        "Session 23 - Mireward Gate Battle",
        "Session 23 - ingest",
    }
    recommended = [row for row in candidates if row["recommended"]]
    assert len(recommended) == 1
    assert recommended[0]["basename"] == "Session 23 - Mireward Gate Battle"
    generic_row = next(row for row in candidates if row["basename"] == "Session 23 - ingest")
    assert generic_row["is_generic"] is True


def test_reconcile_normalized_recap_archives_rejected_duplicate(
    client: TestClient, isolated_session: Path
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    canonical, generic = _seed_duplicate_normalized(corpus)
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "reconcile_normalized_recap",
            "campaign_id": "longmont-c2",
            "session": 23,
            "keep_basename": "Session 23 - Mireward Gate Battle",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "normalized_recap_reconciled" in body["states"]
    assert "normalized_recap_duplicates" not in body["states"]
    assert canonical.is_file()
    assert not generic.exists()
    archive_dir = generic.parent / "_archive"
    archived = list(archive_dir.glob("Session 23 - ingest__*.md"))
    assert len(archived) == 1
    assert body["ingest_report"]["reconciled_kept_basename"] == "Session 23 - Mireward Gate Battle"


def test_reconcile_rejects_generic_keep_basename(
    client: TestClient, isolated_session: Path
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    _seed_duplicate_normalized(corpus)
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "reconcile_normalized_recap",
            "campaign_id": "longmont-c2",
            "session": 23,
            "keep_basename": "Session 23 - ingest",
        },
    )
    assert response.status_code == 422
    assert "generic" in response.json()["detail"]


def test_reconcile_requires_more_than_one_candidate(
    client: TestClient, isolated_session: Path
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    norm_dir = corpus / "Longmont Campaign/Campaign 2/Session Recaps/_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)
    (norm_dir / "Session 23 - Mireward Gate Battle.md").write_text("solo", encoding="utf-8")
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "reconcile_normalized_recap",
            "campaign_id": "longmont-c2",
            "session": 23,
            "keep_basename": "Session 23 - Mireward Gate Battle",
        },
    )
    assert response.status_code == 422


def test_inspect_status_is_read_only_and_reports_disk(client: TestClient, isolated_session: Path) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    recap = corpus / "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md"
    recap.parent.mkdir(parents=True, exist_ok=True)
    recap.write_text("canonical on disk", encoding="utf-8")
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "inspect_status",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "dmb_raw_recap_ingest_status_v1"
    assert "ingest_status_inspected" in body["states"]
    assert "recap_reused" in body["states"]
    assert "corpus_impact" in body["ingest_report"]
    assert recap.read_text(encoding="utf-8") == "canonical on disk"


def test_graph_preview_requires_current_normalized_source_but_not_legacy_derivatives(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = _write_current_normalized(Path(isolated_session / "corpus/eldyrwild-markdown"))
    states = ["normalized_reused", "normalized_stale", "derivative_reconciliation_required"]
    graph_calls: list[dict[str, object]] = []
    context_calls: list[object] = []

    def _status() -> dict[str, object]:
        return {
            "schema": "dmb_raw_recap_ingest_status_v1",
            "campaign_id": "longmont-c2",
            "session": 22,
            "status": "needs_reconciliation",
            "states": list(states),
            "paths": {"normalized_recap": str(normalized)},
            "authority": {"normalized_recap": "canon_play_prepared"},
            "warnings": [],
            "errors": [],
            "next_actions": [],
            "ingest_report": {},
            "entity_spelling_audit": [],
        }

    monkeypatch.setattr(
        recap_ingest_route,
        "_request_recap_context",
        lambda body: (context_calls.append(body) or None),
    )
    monkeypatch.setattr(recap_ingest_route, "inspect_recap_ingest_status", lambda **_kwargs: _status())
    monkeypatch.setattr(
        recap_ingest_route,
        "build_recap_graph_preview_bundle",
        lambda **kwargs: (graph_calls.append(kwargs) or {"status": "source_span_bundle_ready", "next_actions": []}),
    )
    payload = {
        "operation": "build_graph_preview_bundle",
        "campaign_id": "longmont-c2",
        "managed_world_id": "elderwyld",
        "session": 22,
        "slug": "Mireward Road and Lysandro",
    }

    stale = client.post("/api/live/recap-ingest", json=payload)
    assert stale.status_code == 200
    assert stale.json()["status"] == "needs_reconciliation"
    assert "normalized_stale" in stale.json()["states"]
    assert graph_calls == []
    assert context_calls == []

    states[:] = ["normalized_reused", "normalized_current", "frontmatter_seed_stale", "derivative_reconciliation_required"]
    current = client.post("/api/live/recap-ingest", json=payload)
    assert current.status_code == 200
    assert len(graph_calls) == 1
    assert len(context_calls) == 1
    assert "frontmatter_seed_stale" in current.json()["states"]
    assert current.json()["ingest_report"]["graph_preview"]["status"] == "source_span_bundle_ready"


def test_generate_rerun_continues_explicit_derivative_refresh_after_normalize(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = _write_current_normalized(Path(isolated_session / "corpus/eldyrwild-markdown"))
    stages: list[str] = []

    def _status(states: list[str], status: str = "needs_reconciliation") -> dict[str, object]:
        return {
            "schema": "dmb_raw_recap_ingest_status_v1",
            "campaign_id": "longmont-c2",
            "session": 22,
            "status": status,
            "states": list(states),
            "paths": {"normalized_recap": str(normalized)},
            "authority": {"normalized_recap": "canon_play_prepared"},
            "warnings": [],
            "errors": [],
            "next_actions": [],
            "ingest_report": {},
            "entity_spelling_audit": [],
        }

    initial = _status([
        "recap_reused", "normalized_reused", "normalized_stale",
        "frontmatter_seed_found", "breadcrumb_found", "session_memory_materialized",
        "derivative_reconciliation_required",
    ])
    normalized_status = _status([
        "recap_reused", "normalized_reused", "normalized_current", "normalized_refreshed",
        "frontmatter_seed_found", "frontmatter_seed_stale", "breadcrumb_found",
        "breadcrumb_stale", "session_memory_stale", "derivative_reconciliation_required",
    ])
    seed_status = _status([
        "recap_reused", "normalized_current", "frontmatter_seed_found", "frontmatter_seed_current",
        "breadcrumb_found", "breadcrumb_stale", "session_memory_stale", "derivative_reconciliation_required",
    ])
    breadcrumb_status = _status([
        "recap_reused", "normalized_current", "frontmatter_seed_found", "frontmatter_seed_current",
        "breadcrumb_found", "breadcrumb_current", "session_memory_stale", "derivative_reconciliation_required",
    ])
    ready_status = _status([
        "recap_reused", "normalized_current", "frontmatter_seed_current", "breadcrumb_current",
        "session_memory_materialized", "session_memory_current", "ready_for_planning_activation",
    ], status="ready_for_planning_activation")

    def _run_pipeline(options: object, **_kwargs: object) -> dict[str, object]:
        if getattr(options, "normalize", False):
            stages.append("normalize")
            return normalized_status
        stages.append("session_memory")
        return ready_status

    monkeypatch.setattr(recap_ingest_route, "inspect_recap_ingest_status", lambda **_kwargs: initial)
    monkeypatch.setattr(recap_ingest_route, "run_pipeline", _run_pipeline)
    monkeypatch.setattr(
        recap_ingest_route,
        "_build_frontmatter_seed_from_request",
        lambda *_args, **_kwargs: (stages.append("seed") or seed_status),
    )
    monkeypatch.setattr(
        recap_ingest_route,
        "_run_breadcrumb_ingest_from_request",
        lambda *_args, **_kwargs: (stages.append("breadcrumb") or breadcrumb_status),
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
            "include_graph_extraction": False,
            "include_legacy_breadcrumb": True,
            "force_normalize": True,
            "force_seed": True,
            "force_breadcrumb": True,
            "force_session_memory": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_planning_activation"
    assert stages == ["normalize", "seed", "breadcrumb", "session_memory"]
