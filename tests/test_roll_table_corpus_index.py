from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.roll_table_corpus_index import (
    build_roll_table_corpus_index,
)

ROOT = Path(__file__).resolve().parents[1]
LIVE_SESSION_FIXTURE = ROOT / "evals/c2_live_prep/live/session_22"


def _temp_live_session(tmp_path: Path, monkeypatch) -> Path:
    session_dir = tmp_path / "session_22"
    session_dir.mkdir()
    for filename in (
        "live_packet.json",
        "surface_layout.json",
        "event_log.jsonl",
        "job_queue.jsonl",
    ):
        (session_dir / filename).write_bytes((LIVE_SESSION_FIXTURE / filename).read_bytes())
    monkeypatch.setenv(SESSION_DIR_ENV, str(session_dir))
    return session_dir


def _write_roll_table(
    root: Path,
    *,
    rel: Path,
    title: str,
    table_id: str,
    dice: str,
) -> Path:
    path = root / "corpus" / "eldyrwild-markdown" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{title}"',
                "document_class: planning",
                "canon_layer: campaign",
                "campaign_id: longmont-c2",
                "temporal_scope: session_specific",
                "session: 22",
                "source_class: roll_table",
                f"table_id: {table_id}",
                f"dice: {dice}",
                'table_note: "Fixture roll table."',
                "---",
                "",
                f"# {title}",
                "",
                f"| {dice} | Result |",
                "|---|---|",
                "| 1 | Fixture row |",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_mireward_scaffold(root: Path) -> Path:
    path = (
        root
        / "corpus"
        / "eldyrwild-markdown"
        / "Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                'title: "Mireward — place build scaffold"',
                "document_class: planning",
                "source_class: planning_document",
                "---",
                "",
                "# Mireward scaffold",
                "",
                "### On-the-fly marcher kit",
                "",
                "| d6 | Role |",
                "|----|------|",
                "| 1 | Fixture marcher |",
                "",
                "### Scene affordances",
                "",
                "Stop excerpt here.",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_build_roll_table_corpus_index_includes_allowlisted_tables(
    tmp_path: Path,
) -> None:
    _write_roll_table(
        tmp_path,
        rel=Path("Longmont Campaign/Campaign 2/Session Prep/session_22/test_gate_d6.md"),
        title="Test Gate Table",
        table_id="T-GATE",
        dice="d6",
    )
    _write_roll_table(
        tmp_path,
        rel=Path("Elderwyld/Roads/test_road_d100.md"),
        title="Test Road Table",
        table_id="T-ROAD",
        dice="d100",
    )
    _write_mireward_scaffold(tmp_path)

    response = build_roll_table_corpus_index(root=tmp_path)

    assert response.schema_version == "dmb_roll_table_corpus_index_v1"
    sections = {item.section for item in response.roll_tables}
    assert {"session_22", "roads", "mireward_scaffold"}.issubset(sections)
    titles = {item.title for item in response.roll_tables}
    assert "Test Gate Table" in titles
    assert "Test Road Table" in titles
    scaffold = next(item for item in response.roll_tables if item.section == "mireward_scaffold")
    assert scaffold.embed_start == "### On-the-fly marcher kit"
    assert scaffold.embed_end == "### Scene affordances"
    paths = {item.corpus_display_path for item in response.roll_tables}
    assert all(path.startswith("corpus/eldyrwild-markdown/") for path in paths)
    assert str(tmp_path.resolve()) not in " ".join(paths)


def test_roll_table_corpus_index_endpoint_uses_repo_corpus(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    _write_roll_table(
        tmp_path,
        rel=Path("Longmont Campaign/Campaign 2/Session Prep/session_22/only_dynamic_d12.md"),
        title="Only Dynamic Roll Table",
        table_id="T-ONLY",
        dice="d12",
    )
    _write_mireward_scaffold(tmp_path)

    client = TestClient(create_app())
    response = client.get("/api/live/roll-tables/index")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_roll_table_corpus_index_v1"
    assert any(
        item["title"] == "Only Dynamic Roll Table"
        for item in body["roll_tables"]
    )
    assert str(tmp_path.resolve()) not in response.text


def test_roll_table_corpus_index_endpoint_on_real_repo(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: ROOT)
    client = TestClient(create_app())

    response = client.get("/api/live/roll-tables/index")

    assert response.status_code == 200
    body = response.json()
    session_count = sum(
        1 for item in body["roll_tables"] if item["section"] == "session_22"
    )
    titles = {item["title"] for item in body["roll_tables"]}
    assert session_count >= 6
    assert "Session 22 — Mireward gate dilemma d6" in titles
    assert "North-Gate Refugee Improvisation Kit" in titles
    assert str(ROOT.resolve()) not in response.text


def test_roll_table_corpus_index_does_not_expose_secrets(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    _write_roll_table(
        tmp_path,
        rel=Path("Longmont Campaign/Campaign 2/Session Prep/session_22/secret_safe_d8.md"),
        title="Secret Safe Roll Table",
        table_id="T-SECRET",
        dice="d8",
    )
    _write_mireward_scaffold(tmp_path)

    client = TestClient(create_app())
    response = client.get("/api/live/roll-tables/index")

    assert response.status_code == 200
    assert "super-secret-test-key" not in response.text
    assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in response.text
