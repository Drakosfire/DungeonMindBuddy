from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.statblock_corpus_index import (
    build_statblock_corpus_index,
)

ROOT = Path(__file__).resolve().parents[1]
LIVE_SESSION_FIXTURE = ROOT / "evals/c2_live_prep/live/session_22"
REAL_CORPUS_ROOT = ROOT / "corpus" / "eldyrwild-markdown"


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


def _write_generated_statblock(root: Path, *, name: str, title: str) -> Path:
    rel = Path("Longmont Campaign/Campaign 2/Statblocks/generated") / name
    path = root / "corpus" / "eldyrwild-markdown" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "document_class: statblock",
                "source_type: generated_statblock_draft",
                f'title: "{title}"',
                "creature_type: aberration",
                "challenge_rating: null",
                "---",
                "",
                f"# {title}",
                "",
                "Armor Class 16",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_flock_statblock(root: Path, *, name: str, title: str, cr: str) -> Path:
    rel = Path("Elderwyld/Shephards Flock/Statblocks and Tokens") / name
    path = root / "corpus" / "eldyrwild-markdown" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f'title: "{title}"',
                "document_class: world",
                "subject_doc_kind: statblock",
                "---",
                "",
                f"# {title.split(' — ')[0]}",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_build_statblock_corpus_index_includes_generated_without_draft_record(
    tmp_path: Path,
) -> None:
    _write_generated_statblock(tmp_path, name="gatekisser.md", title="Gatekisser")
    _write_generated_statblock(
        tmp_path, name="palisade_gnawer.md", title="Palisade Gnawer"
    )
    _write_flock_statblock(
        tmp_path,
        name="sewer_meat_creature_statblock_cr3.md",
        title="Sewer Meat Creature — statblock (CR 3)",
        cr="3",
    )

    response = build_statblock_corpus_index(root=tmp_path)

    assert response.schema_version == "dmb_statblock_corpus_index_v1"
    sections = {item.section for item in response.statblocks}
    assert sections == {"generated", "shepherds_flock"}
    titles = {item.title for item in response.statblocks}
    assert "Gatekisser" in titles
    assert "Palisade Gnawer" in titles
    paths = {item.corpus_display_path for item in response.statblocks}
    assert all(path.startswith("corpus/eldyrwild-markdown/") for path in paths)
    assert str(tmp_path.resolve()) not in " ".join(paths)


def test_statblock_corpus_index_endpoint_uses_repo_corpus(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    _write_generated_statblock(tmp_path, name="only_generated.md", title="Only Generated")

    client = TestClient(create_app())
    response = client.get("/api/live/statblocks/index")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_statblock_corpus_index_v1"
    assert any(item["title"] == "Only Generated" for item in body["statblocks"])
    assert str(tmp_path.resolve()) not in response.text


def test_statblock_corpus_index_endpoint_on_real_repo(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: ROOT)
    client = TestClient(create_app())

    response = client.get("/api/live/statblocks/index")

    assert response.status_code == 200
    body = response.json()
    generated_titles = {
        item["title"]
        for item in body["statblocks"]
        if item["section"] == "generated"
    }
    flock_count = sum(
        1 for item in body["statblocks"] if item["section"] == "shepherds_flock"
    )
    assert flock_count >= 8
    if (REAL_CORPUS_ROOT / "Longmont Campaign/Campaign 2/Statblocks/generated/gatekisser.md").is_file():
        assert "Gatekisser" in generated_titles


def test_statblock_corpus_index_does_not_expose_secrets(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    _write_generated_statblock(tmp_path, name="secret_safe.md", title="Secret Safe")

    client = TestClient(create_app())
    response = client.get("/api/live/statblocks/index")

    assert response.status_code == 200
    assert "super-secret-test-key" not in response.text
    assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in response.text
