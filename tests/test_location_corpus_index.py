from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.services.location_corpus_index import build_location_corpus_index

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


def test_build_location_corpus_index_includes_mireward_and_reach(tmp_path: Path) -> None:
    corpus_root = tmp_path / "corpus" / "eldyrwild-markdown"
    mireward = corpus_root / "Elderwyld/Cities and Towns/Mireward"
    mireward.mkdir(parents=True)
    (mireward / "README.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Mireward — location hub"',
                "document_class: reference",
                "subject_class: location",
                "subject_doc_kind: hub_index",
                "canon_layer: world",
                'table_note: "Hub in build."',
                "---",
                "",
                "# Mireward — Elderwyld (location hub)",
            ]
        ),
        encoding="utf-8",
    )
    (mireward / "Mireward_PLACE_BUILD_SCAFFOLD.md").write_text(
        "\n".join(
            [
                "---",
                'title: "Mireward — place build scaffold"',
                "document_class: planning",
                "subject_class: location",
                "subject_doc_kind: notes_aggregate",
                "---",
                "",
                "# Mireward — place build scaffold",
                "",
                "## F4. Edge support refugee wave — S23 north-gate crisis *(locked sketch)*",
                "Refugee apron detail.",
                "",
                "## F2. Anchor NPC — swamp escapee at the family inn *(working sketch; expand on the fly)*",
                "Inn detail.",
            ]
        ),
        encoding="utf-8",
    )
    journey = corpus_root / "Longmont Campaign/Campaign 2"
    journey.mkdir(parents=True)
    (journey / "Journey - Mireward Reach (Campaign 2).md").write_text(
        "\n".join(
            [
                "---",
                'title: "Journey — Mireward Reach (Campaign 2)"',
                "---",
                "",
                "# Journey — Mireward Reach (Campaign 2)",
            ]
        ),
        encoding="utf-8",
    )

    response = build_location_corpus_index(root=tmp_path)
    sections = {item.section for item in response.locations}
    ids = {item.index_id for item in response.locations}

    assert "mireward" in sections
    assert "reach_travel" in sections
    assert "mireward-hub-readme" in ids
    assert "mireward-place-scaffold" in ids
    assert "mireward-scaffold-f4-north-gate" in ids
    assert "reach-journey-tracker" in ids

    f4 = next(item for item in response.locations if item.index_id == "mireward-scaffold-f4-north-gate")
    assert f4.embed_start == "## F4. Edge support refugee wave"
    assert f4.embed_end == "## F2. Anchor NPC"


def test_location_corpus_index_endpoint_returns_json(tmp_path: Path, monkeypatch) -> None:
    _temp_live_session(tmp_path, monkeypatch)
    corpus_root = tmp_path / "corpus" / "eldyrwild-markdown"
    mireward = corpus_root / "Elderwyld/Cities and Towns/Mireward"
    mireward.mkdir(parents=True)
    (mireward / "README.md").write_text("# Mireward\n", encoding="utf-8")
    (mireward / "Mireward_PLACE_BUILD_SCAFFOLD.md").write_text(
        "# Scaffold\n\n## F4. Edge support refugee wave\nx\n\n## F2. Anchor NPC\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "apps.live_control_server.routes.live.repo_root",
        lambda: tmp_path,
    )

    client = TestClient(create_app())
    response = client.get("/api/live/locations/index")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "dmb_location_corpus_index_v1"
    assert isinstance(body["locations"], list)
    assert len(body["locations"]) >= 2
