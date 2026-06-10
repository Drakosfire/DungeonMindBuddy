from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.statblock_draft_store import StoredStatblockDraftRecord
from src.live_play.live_store import load_json, write_json

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


def _snapshot_files(base: Path) -> dict[str, bytes]:
    if not base.exists():
        return {}
    return {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }


def _sample_artifact(client: TestClient) -> dict:
    response = client.get("/api/live/statblocks/workbench/sample")
    assert response.status_code == 200
    artifact = response.json()["artifact"]
    artifact["artifact_id"] = "statblock-view-test"
    artifact["structured_statblock"] = {
        **artifact["structured_statblock"],
        "challenge_rating": "3",
        "creature_type": "dragon",
    }
    artifact["combat_defaults"] = {
        **artifact["combat_defaults"],
        "armor_class": 15,
        "hit_points": 76,
        "primary_actions": ["Bite", "Geomantic Breath"],
    }
    return artifact


def _store_sample(client: TestClient, *, artifact_id: str = "statblock-view-test") -> dict:
    artifact = {**_sample_artifact(client), "artifact_id": artifact_id}
    response = client.post(
        "/api/live/statblocks/workbench/drafts",
        json={"artifact": artifact, "source": "workbench"},
    )
    assert response.status_code == 200
    return response.json()["record"]


def _promote_record(
    session_dir: Path,
    root: Path,
    record: dict,
    *,
    body: str = "# Geomantic Drake Juvenile\n\nArmor Class 15\nHit Points 76",
    write_file: bool = True,
) -> StoredStatblockDraftRecord:
    relpath = f"Longmont Campaign/Campaign 2/Statblocks/generated/{record['artifact_id']}.md"
    path = session_dir / "statblock_drafts" / f"{record['artifact_id']}.json"
    stored = StoredStatblockDraftRecord.model_validate(load_json(path))
    promoted_artifact = stored.artifact.model_copy(
        update={
            "lifecycle_state": "corpus_promoted",
            "corpus_status": "promotion_confirmed",
            "updated_at": "2026-06-09T00:00:00Z",
        }
    )
    promoted = stored.model_copy(
        update={
            "updated_at": "2026-06-09T00:00:00Z",
            "corpus_relpath": relpath,
            "corpus_display_path": f"corpus/eldyrwild-markdown/{relpath}",
            "corpus_written_at": "2026-06-09T00:00:00Z",
            "retrieval_status": "retrieval_verified",
            "retrieval_manifest_path": "statblock_retrieval/generated_statblocks_manifest.json",
            "retrieval_activated_at": "2026-06-09T00:01:00Z",
            "retrieval_verified_at": "2026-06-09T00:02:00Z",
            "retrieval_query": "Geomantic Drake Juvenile statblock",
            "retrieval_evidence_path": f"corpus/eldyrwild-markdown/{relpath}",
            "retrieval_evidence_score": 1.0,
            "artifact": promoted_artifact,
        }
    )
    write_json(path, promoted.model_dump(mode="json"))
    if write_file:
        corpus_path = root / "corpus" / "eldyrwild-markdown" / relpath
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        corpus_path.write_text(body, encoding="utf-8")
    return promoted


def test_generated_statblock_list_filters_promoted_and_reports_missing_file(
    tmp_path, monkeypatch
) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    _store_sample(client, artifact_id="not-promoted")
    promoted = _store_sample(client, artifact_id="promoted")
    missing = _store_sample(client, artifact_id="missing-file")
    _promote_record(session_dir, tmp_path, promoted)
    _promote_record(session_dir, tmp_path, missing, write_file=False)

    response = client.get("/api/live/statblocks/view/generated")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_generated_statblock_list_v1"
    ids = {item["artifact_id"] for item in body["statblocks"]}
    assert ids == {"promoted", "missing-file"}
    item = next(item for item in body["statblocks"] if item["artifact_id"] == "promoted")
    assert item["armor_class"] == 15
    assert item["hit_points"] == 76
    assert item["challenge_rating"] == "3"
    assert item["creature_type"] == "dragon"
    assert item["primary_actions"] == ["Bite", "Geomantic Breath"]
    assert item["retrieval_status"] == "retrieval_verified"
    assert "corpus_markdown" not in item
    assert any("missing-file: corpus file is missing" in diagnostic for diagnostic in body["diagnostics"])


def test_generated_statblock_detail_returns_markdown_metadata_and_is_read_only(
    tmp_path, monkeypatch
) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    record = _store_sample(client)
    _promote_record(session_dir, tmp_path, record)
    before_session = _snapshot_files(session_dir)
    before_corpus = _snapshot_files(tmp_path / "corpus")

    response = client.get("/api/live/statblocks/view/generated/statblock-view-test")

    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_generated_statblock_detail_v1"
    assert body["artifact_id"] == "statblock-view-test"
    assert "Geomantic Drake Juvenile" in body["corpus_markdown"]
    assert body["corpus_markdown_bytes"] == len(body["corpus_markdown"].encode("utf-8"))
    assert body["corpus_file_fingerprint"]
    assert body["combat_defaults"]["armor_class"] == 15
    assert body["warnings"] == body["stored_record"]["artifact"]["warnings"]
    assert body["provenance"] == body["stored_record"]["artifact"]["provenance"]
    assert body["breadcrumbs"] == body["stored_record"]["artifact"]["breadcrumbs"]
    assert body["source_refs"] == body["stored_record"]["artifact"]["source_refs"]
    assert body["retrieval"]["status"] == "retrieval_verified"
    add_action = next(action for action in body["available_actions"] if action["action_id"] == "add_to_combat")
    assert add_action["enabled"] is False
    assert _snapshot_files(session_dir) == before_session
    assert _snapshot_files(tmp_path / "corpus") == before_corpus


def test_generated_statblock_detail_rejects_non_promoted_missing_and_unsafe_ids(
    tmp_path, monkeypatch
) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    _store_sample(client, artifact_id="not-promoted")
    missing = _store_sample(client, artifact_id="missing-file")
    _promote_record(session_dir, tmp_path, missing, write_file=False)

    non_promoted = client.get("/api/live/statblocks/view/generated/not-promoted")
    unknown = client.get("/api/live/statblocks/view/generated/unknown")
    missing_file = client.get("/api/live/statblocks/view/generated/missing-file")
    unsafe = client.get("/api/live/statblocks/view/generated/.hidden")

    assert non_promoted.status_code == 409
    assert "not corpus-promoted" in non_promoted.json()["detail"]
    assert unknown.status_code == 404
    assert missing_file.status_code == 409
    assert "missing" in missing_file.json()["detail"]
    assert str(tmp_path) not in missing_file.text
    assert unsafe.status_code == 422


def test_generated_statblock_view_does_not_expose_internal_key(
    tmp_path, monkeypatch
) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("DUNGEONMIND_SERVER_URL", "https://example.invalid")
    client = TestClient(create_app())
    record = _store_sample(client)
    _promote_record(session_dir, tmp_path, record)

    responses = [
        client.get("/api/live/statblocks/view/generated"),
        client.get("/api/live/statblocks/view/generated/statblock-view-test"),
    ]

    for response in responses:
        assert response.status_code == 200
        assert "super-secret-test-key" not in response.text
        assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in response.text
        assert "DUNGEONMIND_SERVER_URL" not in response.text
        assert "X-DungeonBuddy-Internal-Key" not in response.text
