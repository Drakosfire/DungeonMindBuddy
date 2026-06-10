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


def _sample_artifact(client: TestClient, *, artifact_id: str = "combat-statblock-test") -> dict:
    response = client.get("/api/live/statblocks/workbench/sample")
    assert response.status_code == 200
    artifact = response.json()["artifact"]
    artifact["artifact_id"] = artifact_id
    artifact["title"] = "Geomantic Drake Juvenile"
    artifact["combat_defaults"] = {
        **artifact["combat_defaults"],
        "name": "Geomantic Drake Juvenile",
        "armor_class": 15,
        "hit_points": 76,
        "primary_actions": ["Bite", "Geomantic Breath"],
    }
    return artifact


def _store_sample(client: TestClient, *, artifact_id: str = "combat-statblock-test") -> dict:
    response = client.post(
        "/api/live/statblocks/workbench/drafts",
        json={"artifact": _sample_artifact(client, artifact_id=artifact_id), "source": "workbench"},
    )
    assert response.status_code == 200
    return response.json()["record"]


def _promote_record(
    session_dir: Path,
    root: Path,
    record: dict,
    *,
    write_file: bool = True,
    retrieval_status: str | None = "retrieval_verified",
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
            "retrieval_status": retrieval_status,
            "retrieval_manifest_path": "statblock_retrieval/generated_statblocks_manifest.json",
            "retrieval_activated_at": "2026-06-09T00:01:00Z" if retrieval_status else None,
            "retrieval_verified_at": "2026-06-09T00:02:00Z" if retrieval_status == "retrieval_verified" else None,
            "retrieval_query": "Geomantic Drake Juvenile statblock" if retrieval_status else None,
            "retrieval_evidence_path": f"corpus/eldyrwild-markdown/{relpath}" if retrieval_status else None,
            "retrieval_evidence_score": 1.0 if retrieval_status == "retrieval_verified" else None,
            "artifact": promoted_artifact,
        }
    )
    write_json(path, promoted.model_dump(mode="json"))
    if write_file:
        corpus_path = root / "corpus" / "eldyrwild-markdown" / relpath
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        corpus_path.write_text("# Geomantic Drake Juvenile\n\nArmor Class 15\nHit Points 76", encoding="utf-8")
    return promoted


def test_current_combat_read_initializes_empty_without_writing(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    client = TestClient(create_app())

    response = client.get("/api/live/combat/current")

    assert response.status_code == 200
    body = response.json()
    packet = load_json(session_dir / "live_packet.json")
    assert body["schema"] == "dmb_combat_encounter_state_v1"
    assert body["campaign_id"] == packet["campaign_id"]
    assert body["session"] == packet["session"]
    assert body["entities"] == []
    assert not (session_dir / "combat" / "current_combat.json").exists()


def test_add_generated_statblock_creates_current_combat_file(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    record = _store_sample(client)
    promoted = _promote_record(session_dir, tmp_path, record)

    before = _snapshot_files(session_dir)
    response = client.post(
        "/api/live/statblocks/view/generated/combat-statblock-test/combat/add",
        json={"team": "enemy", "count": 1, "initiative": 12},
    )

    assert response.status_code == 200
    body = response.json()
    entity = body["added_entities"][0]
    assert entity["name"] == "Geomantic Drake Juvenile"
    assert entity["team"] == "enemy"
    assert entity["init"] == 12
    assert entity["ac"] == 15
    assert entity["hp"] == 76
    assert entity["max_hp"] == 76
    assert entity["source"] == "corpus"
    assert entity["statblock_artifact_id"] == "combat-statblock-test"
    assert entity["statblock_path"] == promoted.corpus_display_path
    assert entity["corpus_fingerprint"]
    assert entity["provenance"][0]["hydration_contract"] == "combat_defaults"
    state_path = session_dir / "combat" / "current_combat.json"
    assert state_path.exists()
    saved = load_json(state_path)
    assert saved["entities"][0]["id"] == entity["id"]
    after = _snapshot_files(session_dir)
    changed = {key for key, value in after.items() if before.get(key) != value} - {key for key in before if key not in after}
    assert changed == {"combat/current_combat.json"}


def test_add_multiple_copies_groups_and_distinguishes_names(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    record = _store_sample(client)
    _promote_record(session_dir, tmp_path, record)

    response = client.post(
        "/api/live/statblocks/view/generated/combat-statblock-test/combat/add",
        json={"count": 3},
    )

    assert response.status_code == 200
    body = response.json()
    names = [entity["name"] for entity in body["added_entities"]]
    ids = [entity["id"] for entity in body["added_entities"]]
    assert names == [
        "Geomantic Drake Juvenile A",
        "Geomantic Drake Juvenile B",
        "Geomantic Drake Juvenile C",
    ]
    assert len(set(ids)) == 3
    assert [entity["order"] for entity in body["encounter"]["entities"]] == [1, 2, 3]
    assert body["encounter"]["groups"][0]["member_ids"] == ids


def test_add_generated_statblock_supports_insert_and_overrides(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    first_record = _store_sample(client, artifact_id="first-statblock")
    second_record = _store_sample(client, artifact_id="second-statblock")
    _promote_record(session_dir, tmp_path, first_record)
    _promote_record(session_dir, tmp_path, second_record)
    first = client.post("/api/live/statblocks/view/generated/first-statblock/combat/add", json={}).json()["added_entities"][0]

    response = client.post(
        "/api/live/statblocks/view/generated/second-statblock/combat/add",
        json={
            "team": "ally",
            "initiative": 17,
            "insert_after_entity_id": first["id"],
            "name_override": "South Gate Drake",
            "hp_override": 42,
            "max_hp_override": 43,
            "notes": "Arrives from south gate.",
        },
    )

    assert response.status_code == 200
    entity = response.json()["added_entities"][0]
    assert entity["name"] == "South Gate Drake"
    assert entity["team"] == "ally"
    assert entity["init"] == 17
    assert entity["hp"] == 42
    assert entity["max_hp"] == 43
    assert entity["notes"] == "Arrives from south gate."
    assert [row["id"] for row in response.json()["encounter"]["entities"]] == [first["id"], entity["id"]]


def test_add_generated_statblock_rejects_invalid_states(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    client = TestClient(create_app())
    non_promoted = _store_sample(client, artifact_id="not-promoted")
    missing = _store_sample(client, artifact_id="missing-file")
    _promote_record(session_dir, tmp_path, missing, write_file=False)

    assert client.post("/api/live/statblocks/view/generated/unknown/combat/add", json={}).status_code == 404
    assert client.post("/api/live/statblocks/view/generated/.hidden/combat/add", json={}).status_code == 422
    assert client.post(f"/api/live/statblocks/view/generated/{non_promoted['artifact_id']}/combat/add", json={}).status_code == 409
    assert client.post("/api/live/statblocks/view/generated/missing-file/combat/add", json={}).status_code == 409
    assert client.post("/api/live/statblocks/view/generated/missing-file/combat/add", json={"count": 21}).status_code == 422
    assert client.post("/api/live/statblocks/view/generated/missing-file/combat/add", json={"team": "villain"}).status_code == 422


def test_combat_responses_do_not_expose_secret_environment(tmp_path, monkeypatch) -> None:
    session_dir = _temp_live_session(tmp_path, monkeypatch)
    monkeypatch.setattr("apps.live_control_server.routes.live.repo_root", lambda: tmp_path)
    monkeypatch.setenv("DUNGEONBUDDY_INTERNAL_API_KEY", "super-secret-test-key")
    monkeypatch.setenv("DUNGEONMIND_SERVER_URL", "https://example.invalid")
    client = TestClient(create_app())
    record = _store_sample(client)
    _promote_record(session_dir, tmp_path, record)

    read_text = client.get("/api/live/combat/current").text
    add_text = client.post("/api/live/statblocks/view/generated/combat-statblock-test/combat/add", json={}).text

    for text in (read_text, add_text):
        assert "super-secret-test-key" not in text
        assert "DUNGEONBUDDY_INTERNAL_API_KEY" not in text
        assert "DUNGEONMIND_SERVER_URL" not in text
        assert "X-DungeonBuddy-Internal-Key" not in text
