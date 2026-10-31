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


@pytest.fixture(autouse=True)
def _declared_local_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")


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
    return TestClient(create_app(), client=("127.0.0.1", 50000))


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


@pytest.mark.parametrize(
    "operation",
    ["stage_preview", "apply_normalize", "build_frontmatter_seed", "run_breadcrumb_ingest", "materialize_session_memory"],
)
def test_retired_ingest_operations_are_rejected(client: TestClient, operation: str) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": operation,
            "campaign_id": "longmont-c2",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "field",
    ["include_legacy_breadcrumb", "force_seed", "force_breadcrumb", "force_session_memory", "force_normalize", "check"],
)
def test_retired_ingest_request_flags_are_rejected(client: TestClient, field: str) -> None:
    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "inspect_status",
            "campaign_id": "longmont-c2",
            "session": 22,
            field: True,
        },
    )
    assert response.status_code == 422


def test_process_stops_on_staged_source_conflict_before_graph_extraction(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(recap_ingest_route, "_request_recap_context", lambda _body: object())
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    staged = corpus / "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md"
    staged.parent.mkdir(parents=True, exist_ok=True)
    existing = "Existing saved source must be preserved."
    staged.write_text(existing, encoding="utf-8")
    graph_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        recap_ingest_route,
        "build_recap_graph_preview_bundle",
        lambda **kwargs: (graph_calls.append(kwargs) or {"status": "candidate_validation_ready"}),
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": "Different pasted source must not be processed.",
            "slug": "Mireward Road and Lysandro",
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "staged_raw_notes_conflict" in body["states"]
    assert "staged_raw_notes_reused" in body["states"]
    assert body["status"] == "needs_reconciliation"
    assert "breadcrumb" not in str(body).lower()
    assert "session_memory" not in str(body).lower()
    assert graph_calls == []
    assert staged.read_text(encoding="utf-8") == existing
    assert not (corpus / str(body["paths"]["canonical_recap"])).exists()


def test_process_rejects_generic_recap_title_before_staging(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, isolated_session: Path
) -> None:
    calls: list[object] = []
    monkeypatch.setattr(
        recap_ingest_route,
        "run_pipeline",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "session": 22,
            "raw_text": "A recap with no useful title.",
            "title": "ingest",
            "include_graph_extraction": False,
        },
    )

    assert response.status_code == 422
    assert "non-generic slug or title" in response.json()["detail"]
    assert calls == []
    assert not list((isolated_session / "corpus/eldyrwild-markdown").rglob("*.md"))


def test_process_saves_normalizes_and_builds_graph_in_one_request(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    graph_calls: list[dict[str, object]] = []
    monkeypatch.setattr(recap_ingest_route, "_request_recap_context", lambda _body: object())
    monkeypatch.setattr(
        recap_ingest_route,
        "build_recap_graph_preview_bundle",
        lambda **kwargs: (
            graph_calls.append(kwargs)
            or {
                "status": "candidate_validation_ready",
                "extraction_run_id": "run-session-22-fixture",
                "candidate_node_count": 4,
                "candidate_edge_count": 3,
            }
        ),
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "raw_text": _raw_text(),
            "slug": "Mireward Road and Lysandro",
            "title": "Session 22 - Mireward Road and Lysandro",
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    graph_preview = body["ingest_report"]["graph_preview"]
    assert graph_preview["status"] == "candidate_validation_ready"
    assert graph_preview["extraction_run_id"] == "run-session-22-fixture"
    assert len(graph_calls) == 1
    canonical = corpus / str(body["paths"]["canonical_recap"])
    normalized = corpus / str(body["paths"]["normalized_recap"])
    assert canonical.is_file()
    assert normalized.is_file()
    assert graph_calls[0]["normalized_recap_path"] == str(normalized)
    assert "breadcrumb" not in str(body).lower()
    assert "session_memory" not in str(body).lower()


def test_process_builds_graph_context_without_breadcrumb_or_session_memory_operations(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = _write_current_normalized(Path(isolated_session / "corpus/eldyrwild-markdown"))
    graph_calls: list[dict[str, object]] = []
    monkeypatch.setattr(recap_ingest_route, "_request_recap_context", lambda _body: object())
    monkeypatch.setattr(
        recap_ingest_route,
        "build_recap_graph_preview_bundle",
        lambda **kwargs: (
            graph_calls.append(kwargs)
            or {
                "status": "candidate_validation_ready",
                "extraction_run_id": "run-session-22",
                "candidate_node_count": 3,
                "candidate_edge_count": 2,
            }
        ),
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "generate_recap_memory",
            "campaign_id": "longmont-c2",
            "managed_world_id": "elderwyld",
            "session": 22,
            "slug": "Mireward Road and Lysandro",
            "include_graph_extraction": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ingest_report"]["graph_preview"]["status"] == "candidate_validation_ready"
    assert len(graph_calls) == 1
    assert graph_calls[0]["normalized_recap_path"] == str(normalized)
    assert graph_calls[0]["extract_graph"] is True


def test_process_explicit_replacement_refreshes_normalized_source_before_graph_extraction(
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    normalized = _write_current_normalized(corpus)
    canonical = corpus / (
        "Longmont Campaign/Campaign 2/Session Recaps/"
        "Session 22 - Mireward Road and Lysandro.md"
    )
    old_normalized = normalized.read_text(encoding="utf-8")
    graph_calls: list[dict[str, object]] = []
    monkeypatch.setattr(recap_ingest_route, "_request_recap_context", lambda _body: object())
    monkeypatch.setattr(
        recap_ingest_route,
        "build_recap_graph_preview_bundle",
        lambda **kwargs: (
            graph_calls.append(kwargs)
            or {"status": "candidate_validation_ready", "candidate_node_count": 2, "candidate_edge_count": 1}
        ),
    )

    body = recap_ingest_route._generate_recap_memory_from_request(
        recap_ingest_route.RecapIngestRequest(
            operation="generate_recap_memory",
            campaign_id="longmont-c2",
            managed_world_id="elderwyld",
            session=22,
            raw_text="Session 22 — Mireward Road and Lysandro\n\nThe party now crosses the southern road.",
            slug="Mireward Road and Lysandro",
            title="Session 22 - Mireward Road and Lysandro",
            force_stage=True,
            force_recap=True,
            include_graph_extraction=True,
        ),
        corpus,
    )
    assert "canonical_recap_refreshed" in body["states"]
    assert "normalized_refreshed" in body["states"]
    assert canonical.read_text(encoding="utf-8") != "The group travels.\n"
    assert "The party now crosses the southern road." in canonical.read_text(encoding="utf-8")
    assert normalized.read_text(encoding="utf-8") != old_normalized
    assert len(graph_calls) == 1
    assert graph_calls[0]["normalized_recap_path"] == str(normalized)
    archived = body["ingest_report"]["archived_artifacts"]
    assert any(row["from"].endswith(normalized.name) for row in archived)


def test_api_never_writes_live_workspace_files(client: TestClient, isolated_session: Path) -> None:
    watched = {
        name: (isolated_session / name).read_bytes()
        for name in ("live_packet.json", "event_log.jsonl", "job_queue.jsonl", "current_state.json")
    }
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
    for name, value in watched.items():
        assert (isolated_session / name).read_bytes() == value


def test_api_never_writes_embedding_or_retrieval_indexes(client: TestClient, isolated_session: Path) -> None:
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
    assert "breadcrumb" not in str(body).lower()
    assert "session_memory" not in str(body).lower()
    assert recap.read_text(encoding="utf-8") == "canonical on disk"


def test_inspect_status_does_not_restore_the_retired_normalize_step(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        recap_ingest_route,
        "inspect_recap_graph_preview_status",
        lambda **_kwargs: {
            "status": "missing",
            "next_actions": ["apply_normalize", "build_graph_preview_bundle"],
        },
    )

    response = client.post(
        "/api/live/recap-ingest",
        json={"operation": "inspect_status", "campaign_id": "longmont-c2", "session": 22},
    )

    assert response.status_code == 200
    actions = response.json()["ingest_report"]["graph_preview"]["next_actions"]
    assert "Process recap" in actions
    assert "apply_normalize" not in actions


def test_inspect_status_verifies_generic_canonical_with_explicit_title_without_writes(
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    corpus = Path(isolated_session / "corpus/eldyrwild-markdown")
    session = 10
    title = "Session 10 - Festival Crafting Elementals"
    slug = "Festival Crafting Elementals"
    canonical_rel = "Longmont Campaign/Campaign 2/Session Recaps/Session 10 - Recap.md"
    canonical = corpus / canonical_rel
    canonical.parent.mkdir(parents=True, exist_ok=True)
    canonical.write_text(
        "---\ntitle: Session 10 - Recap:\nsession: 10\n---\n"
        "# Session 10 Recap\n\nThe festival elementals arrive.\n",
        encoding="utf-8",
    )
    normalized_rel = (
        f"Longmont Campaign/Campaign 2/Session Recaps/_normalized/{title}.md"
    )
    normalized = corpus / normalized_rel
    normalized.parent.mkdir(parents=True, exist_ok=True)
    normalized.write_text(
        _expected_normalized_content(
            corpus=corpus,
            canonical_recap_rel=canonical_rel,
            session=session,
            title=title,
            slug=slug,
        ),
        encoding="utf-8",
    )
    canonical_before = canonical.read_bytes()
    normalized_before = normalized.read_bytes()
    graph_paths: list[str | None] = []

    def inspect_graph(**kwargs: object) -> dict[str, object]:
        graph_paths.append(kwargs.get("normalized_recap_path"))  # type: ignore[arg-type]
        return {"status": "missing", "next_actions": []}

    monkeypatch.setattr(
        recap_ingest_route, "inspect_recap_graph_preview_status", inspect_graph
    )
    monkeypatch.setattr(recap_ingest_route, "_pipeline_corpus_root", lambda: corpus)
    body = recap_ingest_route.post_recap_ingest(
        recap_ingest_route.RecapIngestRequest(
            operation="inspect_status",
            campaign_id="longmont-c2",
            session=session,
            title=title,
            slug=slug,
        )
    )

    assert "normalized_current" in body["states"]
    assert "normalized_provenance_unknown" not in body["states"]
    assert graph_paths == [str(normalized)]
    assert canonical.read_bytes() == canonical_before
    assert normalized.read_bytes() == normalized_before


def test_graph_preview_requires_a_current_normalized_source(
    client: TestClient,
    isolated_session: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normalized = _write_current_normalized(Path(isolated_session / "corpus/eldyrwild-markdown"))
    states = ["normalized_reused", "normalized_stale"]
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

    states[:] = ["normalized_reused", "normalized_current"]
    current = client.post("/api/live/recap-ingest", json=payload)
    assert current.status_code == 200
    assert len(graph_calls) == 1
    assert len(context_calls) == 1
    assert current.json()["ingest_report"]["graph_preview"]["status"] == "source_span_bundle_ready"
