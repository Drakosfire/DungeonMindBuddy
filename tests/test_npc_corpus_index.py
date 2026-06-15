from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.npc_corpus_index import build_npc_corpus_index

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


def _write_npc_hub(
    root: Path,
    *,
    rel: Path,
    title: str,
    table_note: str,
    campaign_id: str | None,
    primary_name: str = "character_seed.md",
) -> Path:
    hub = root / "corpus" / "eldyrwild-markdown" / rel
    hub.mkdir(parents=True, exist_ok=True)
    campaign_value = "null" if campaign_id is None else campaign_id
    (hub / "README.md").write_text(
        "\n".join(
            [
                "---",
                f'title: "{title}"',
                "document_class: reference",
                "subject_class: npc",
                "subject_doc_kind: hub_index",
                "canon_layer: campaign" if campaign_id else "canon_layer: world",
                f"campaign_id: {campaign_value}",
                "temporal_scope: campaign_stateful" if campaign_id else "temporal_scope: evergreen",
                f'table_note: "{table_note}"',
                "---",
                "",
                f"# {title}",
            ]
        ),
        encoding="utf-8",
    )
    (hub / primary_name).write_text(
        "\n".join(
            [
                "---",
                f'title: "{title} — primary"',
                "document_class: reference",
                "subject_class: npc",
                "subject_doc_kind: seed",
                "---",
                "",
                f"# {title}",
            ]
        ),
        encoding="utf-8",
    )
    return hub


def test_build_npc_corpus_index_includes_allowlisted_hubs(tmp_path: Path) -> None:
    _write_npc_hub(
        tmp_path,
        rel=Path("Elderwyld/Cities and Towns/Mireward/NPCs/test_mireward_face"),
        title="Test Mireward Face — setting hub",
        table_note="Useful at the gate.",
        campaign_id=None,
    )
    _write_npc_hub(
        tmp_path,
        rel=Path("Longmont Campaign/Campaign 2/NPCs/test_campaign_face"),
        title="Test Campaign Face — Campaign 2",
        table_note="Recurring table voice.",
        campaign_id="longmont-c2",
        primary_name="test_campaign_face_character_dossier.md",
    )

    response = build_npc_corpus_index(root=tmp_path)

    assert response.schema_version == "dmb_npc_corpus_index_v1"
    sections = {item.section for item in response.npcs}
    assert sections == {"mireward_setting", "campaign_2"}
    titles = {item.title for item in response.npcs}
    assert "Test Mireward Face — setting hub" in titles
    assert "Test Campaign Face — Campaign 2" in titles
    paths = " ".join(
        path
        for item in response.npcs
        for path in (
            item.hub_path,
            item.primary_doc_path or "",
            item.seed_path or "",
            item.dossier_path or "",
            item.timeline_path or "",
        )
    )
    assert "corpus/eldyrwild-markdown/" in paths
    assert str(tmp_path.resolve()) not in paths


def test_npc_corpus_index_endpoint_uses_repo_corpus(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    _write_npc_hub(
        tmp_path,
        rel=Path("Elderwyld/Cities and Towns/Mireward/NPCs/only_dynamic_npc"),
        title="Only Dynamic NPC — setting hub",
        table_note="Endpoint fixture.",
        campaign_id=None,
    )

    client = TestClient(create_app())
    response = client.get("/api/live/npcs/index")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_npc_corpus_index_v1"
    assert any(item["title"] == "Only Dynamic NPC — setting hub" for item in body["npcs"])
    assert str(tmp_path.resolve()) not in response.text


def test_npc_corpus_index_endpoint_on_real_repo(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: ROOT)
    client = TestClient(create_app())

    response = client.get("/api/live/npcs/index")

    assert response.status_code == 200
    body = response.json()
    mireward_count = sum(1 for item in body["npcs"] if item["section"] == "mireward_setting")
    campaign_titles = {
        item["title"] for item in body["npcs"] if item["section"] == "campaign_2"
    }
    assert mireward_count >= 9
    assert "Captain Lysandra Ironveil — Campaign 2" in campaign_titles
    assert str(ROOT.resolve()) not in response.text


def test_npc_corpus_index_does_not_expose_secrets(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    _write_npc_hub(
        tmp_path,
        rel=Path("Elderwyld/Cities and Towns/Mireward/NPCs/secret_safe_npc"),
        title="Secret Safe NPC — setting hub",
        table_note="No env leakage.",
        campaign_id=None,
    )

    client = TestClient(create_app())
    response = client.get("/api/live/npcs/index")

    assert response.status_code == 200
    assert "super-secret-test-key" not in response.text
    assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in response.text
