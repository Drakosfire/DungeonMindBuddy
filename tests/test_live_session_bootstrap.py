from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from apps.live_control_server.config import SESSION_DIR_ENV
from apps.live_control_server.main import create_app
from apps.live_control_server.schema_validation import validate_live_packet
from apps.live_control_server.session_store import load_session
from src.live_play.live_store import iter_jsonl, load_json
from src.live_play.projections import build_session_plan_projection
from src.live_play.session_bootstrap import (
    activate_session_workspace,
    bootstrap_session_workspace,
    build_live_packet,
)
from src.live_play.recap_ingestion import ingest_recap_markdown
from src.live_play.session_paths import live_sessions_root, resolve_allowed_output_dir

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "evals/c2_live_prep/live/schemas"
FIXTURE = ROOT / "tests/fixtures/live_bootstrap/session_22_fresh_recap.md"
CORPUS_PREP = ROOT / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/session_22"


def _validator(name: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def _pytest_workspace(tmp_path: Path, session: int = 23) -> Path:
    out = live_sessions_root() / "_pytest" / tmp_path.name / f"session_{session}"
    if out.exists():
        shutil.rmtree(out)
    return out


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    out = _pytest_workspace(tmp_path, session=23)
    bootstrap_session_workspace(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        session=23,
        output_dir=out,
        source_session=22,
        next_session_label="Session 23",
        force=False,
    )
    yield out
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    parent = out.parent
    if parent.exists() and not any(parent.iterdir()):
        parent.rmdir()


def test_bootstrap_creates_workspace_files(workspace: Path) -> None:
    for name in (
        "recap.md",
        "live_packet.json",
        "surface_layout.json",
        "event_log.jsonl",
        "job_queue.jsonl",
        "current_state.json",
    ):
        assert (workspace / name).is_file()


def test_bootstrap_recap_has_frontmatter_and_preserves_body(workspace: Path) -> None:
    recap = (workspace / "recap.md").read_text(encoding="utf-8")
    assert recap.startswith("---")
    assert "generated_by: \"session_bootstrap\"" in recap
    assert "Travel North" in recap


def test_bootstrapped_json_validates(workspace: Path) -> None:
    packet = load_json(workspace / "live_packet.json")
    layout = load_json(workspace / "surface_layout.json")
    state = load_json(workspace / "current_state.json")
    validate_live_packet(packet)
    _validator("live_surface_layout.schema.json").validate(layout)
    assert packet["known_roll_tables"] == []
    assert packet["roll_stack"] == []
    assert state["session"] == 23
    assert "timeline" in state["enabled_surface_modules"] or "timeline" in [
        row["module_id"] for row in layout["modules"] if row["enabled"]
    ]


def test_bootstrap_event_and_provenance(workspace: Path) -> None:
    events = iter_jsonl(workspace / "event_log.jsonl")
    assert len(events) == 1
    event = events[0]
    _validator("live_event.schema.json").validate(event)
    assert event["event_type"] == "state_note"
    assert event["derived_fields"]["command_type"] == "bootstrap_session_from_recap"
    assert event["provenance"]["source_paths"][0]["path"] == "recap.md"


def test_plan_view_from_bootstrapped_packet(workspace: Path) -> None:
    packet, _, events, jobs = load_session(workspace)
    projection = build_session_plan_projection(packet, events, jobs, generated_at="2026-05-29T00:00:00Z")
    _validator("plan_view.schema.json").validate(projection)
    assert len(projection["timeline"]) >= 2
    for row in projection["timeline"]:
        assert row["label"].strip()
        assert row["summary"].strip()
        assert not row["label"].startswith("corpus/")


def test_live_server_loads_bootstrapped_session(workspace: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(SESSION_DIR_ENV, str(workspace))
    client = TestClient(create_app())
    response = client.get("/api/live/plan-view")
    assert response.status_code == 200
    body = response.json()
    _validator("plan_view.schema.json").validate(body)
    assert body["session"] == 23
    assert body["timeline"]


def test_refuses_overwrite_without_force(tmp_path: Path) -> None:
    out = _pytest_workspace(tmp_path, session=23)
    try:
        bootstrap_session_workspace(
            recap_path=FIXTURE,
            campaign_id="longmont-c2",
            session=23,
            output_dir=out,
            source_session=22,
        )
        with pytest.raises(FileExistsError):
            bootstrap_session_workspace(
                recap_path=FIXTURE,
                campaign_id="longmont-c2",
                session=23,
                output_dir=out,
                source_session=22,
            )
    finally:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)


def test_force_overwrites_workspace(tmp_path: Path) -> None:
    out = _pytest_workspace(tmp_path, session=23)
    try:
        bootstrap_session_workspace(
            recap_path=FIXTURE,
            campaign_id="longmont-c2",
            session=23,
            output_dir=out,
            source_session=22,
        )
        (out / "stale.txt").write_text("stale", encoding="utf-8")
        bootstrap_session_workspace(
            recap_path=FIXTURE,
            campaign_id="longmont-c2",
            session=23,
            output_dir=out,
            source_session=22,
            force=True,
        )
        assert (out / "live_packet.json").is_file()
        packet = load_json(out / "live_packet.json")
        assert packet["session"] == 23
    finally:
        if out.exists():
            shutil.rmtree(out, ignore_errors=True)


def test_path_traversal_output_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="output directory must be under"):
        resolve_allowed_output_dir(tmp_path / "outside")


def test_missing_recap_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        bootstrap_session_workspace(
            recap_path=tmp_path / "missing.md",
            campaign_id="longmont-c2",
            session=23,
            output_dir=_pytest_workspace(tmp_path, session=23),
        )


def test_known_roll_tables_not_invented_from_recap() -> None:
    ingestion = ingest_recap_markdown(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        planning_session=23,
        source_session=22,
    )
    packet = build_live_packet(ingestion)
    assert packet["known_roll_tables"] == []
    assert packet["roll_stack"] == []


def test_no_retrieval_or_embedding_artifacts(workspace: Path) -> None:
    for path in workspace.rglob("*"):
        if path.is_file():
            assert "embedding" not in path.name.lower()
            assert path.suffix not in {".faiss", ".npy"}


def test_corpus_prep_files_untouched(workspace: Path) -> None:
    if not CORPUS_PREP.is_dir():
        pytest.skip("corpus prep dir not present in this checkout")
    before = {
        path: path.read_bytes()
        for path in CORPUS_PREP.glob("*.md")
        if path.is_file()
    }
    out24 = live_sessions_root() / "_pytest" / workspace.parent.name / "session_24"
    bootstrap_session_workspace(
        recap_path=FIXTURE,
        campaign_id="longmont-c2",
        session=24,
        output_dir=out24,
        force=True,
    )
    if out24.exists():
        shutil.rmtree(out24, ignore_errors=True)
    after = {
        path: path.read_bytes()
        for path in CORPUS_PREP.glob("*.md")
        if path.is_file()
    }
    assert before == after


def test_activate_copies_into_target(tmp_path: Path) -> None:
    source = _pytest_workspace(tmp_path, session=23)
    target = tmp_path / "live_active"
    try:
        bootstrap_session_workspace(
            recap_path=FIXTURE,
            campaign_id="longmont-c2",
            session=23,
            output_dir=source,
            source_session=22,
        )
        activate_session_workspace(source, target_dir=target)
        assert (target / "live_packet.json").is_file()
        assert load_json(target / "live_packet.json")["session"] == 23
    finally:
        if source.exists():
            shutil.rmtree(source, ignore_errors=True)


def test_allowed_output_under_live_root(tmp_path: Path) -> None:
    allowed_parent = tmp_path / "evals/c2_live_prep/live"
    allowed_parent.mkdir(parents=True)
    # Monkey-patch is unnecessary: resolve_allowed_output_dir only checks relative_to live root.
    # Use real live_sessions_root by placing under repo eval path in tmp via symlink trick —
    # simpler: use tmp_path under copied structure
    live_root = live_sessions_root()
    out = live_root / "_pytest_bootstrap" / "session_99"
    if out.exists():
        shutil.rmtree(out)
    try:
        bootstrap_session_workspace(
            recap_path=FIXTURE,
            campaign_id="longmont-c2",
            session=99,
            output_dir=out,
            source_session=22,
            force=True,
        )
        assert out.is_dir()
    finally:
        if out.exists():
            shutil.rmtree(out)
