"""Recap supplements reopen exact Play review versions, never copied files."""
import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import psycopg
import pytest

from application_state.errors import ApplicationStateUnavailableError
from application_state.play.lifecycle import set_world_play_session_trash
from application_state.play.session_review import commit_review
from apps.live_control_server.services import graph_preview_runner as producer
from apps.live_control_server.services import ingest_run_catalog as catalog
from apps.live_control_server.services import session_evidence as evidence
from tests.application_state.test_play_run_editions_postgres import WORLD
from tests.application_state.test_play_session_review_postgres import request
from tests.application_state.test_session_evidence_consumers import ended_session
from tests.test_bounded_recap_execution import _fixture_ingest_context
from tests.test_recap_managed_standing_context import seed_binding


@pytest.fixture
def selected(tmp_path, monkeypatch, application_state_dsn):
    run_id = ended_session()
    packet = evidence.read_session_evidence(world_id=WORLD, run_id=run_id, revision=1)
    pins = [{key: packet[key] for key in ("run_id", "review_revision", "sha256")}]
    bundle = evidence.resolve_evidence_refs(WORLD, pins)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    seed_binding(tmp_path, WORLD, "world:synthetic")
    source = tmp_path / "external-recap.md"
    source.write_text("The company crossed the damaged boardwalk.\n")
    context = replace(_fixture_ingest_context("longmont-c2"), managed_world_id=WORLD)

    def capture(supplement=bundle):
        return producer.run_recap_production_extraction(
            repo_root=tmp_path, campaign_id="longmont-c2", session_id="session-30",
            recap_path=source, profile="category_baseline", allow_llm=False,
            ingest_context=context, supplemental_evidence=supplement,
        )

    return SimpleNamespace(
        root=tmp_path, source=source, run_id=run_id, bundle=bundle, capture=capture,
        dsn=application_state_dsn,
    )


def test_preparation_and_reuse_need_no_supplement_file(selected, monkeypatch):
    original = selected.source.read_bytes()
    path_open = Path.open

    def deny_copy(path, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+") and path.suffix != ".lock":
            raise OSError("synthetic copy storage unavailable")
        return path_open(path, mode, *args, **kwargs)

    with monkeypatch.context() as guard:
        guard.setattr(Path, "open", deny_copy)
        result = selected.capture()
    saved = result.run.lineage["session_evidence"]
    assert set(saved) == {"sha256", "sources"}
    assert saved["sha256"] == selected.bundle["sha256"]
    assert "Players want more combat" not in json.dumps(saved)
    assert not list(selected.root.rglob("session_evidence.json"))
    assert selected.source.read_bytes() == original
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("reuse opened a file"))
    assert catalog._same_session_evidence(result.run, selected.bundle)


def historical_run(selected):
    run = selected.capture().run
    lineage = copy.deepcopy(run.lineage)
    raw = json.dumps(selected.bundle, sort_keys=True).encode()
    (selected.root / "old-session-evidence.json").write_bytes(raw)
    lineage["session_evidence"].update(
        uri="old-session-evidence.json", artifact_sha256=hashlib.sha256(raw).hexdigest(),
    )
    return run.model_copy(update={"lineage": lineage})


def test_exact_old_review_survives_new_review_trash_and_missing_copy(selected, monkeypatch):
    run = historical_run(selected)
    commit_review(
        world_id=WORLD, run_id=selected.run_id, command_id=str(uuid4()),
        request=request(selected.run_id, "save", 1, final_thoughts="Newer preferences."),
    )
    set_world_play_session_trash(
        world_id=WORLD, run_id=UUID(selected.run_id), expected_revision=2,
        expected_content_revision=0, restore=False,
    )
    (selected.root / "old-session-evidence.json").unlink()
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("old locator opened"))
    assert catalog._same_session_evidence(run, selected.bundle)
    assert evidence.resolve_evidence_refs(WORLD, run.lineage["session_evidence"]["sources"]) == selected.bundle


def test_requested_digest_mismatch_does_not_read_play_revisions(selected, monkeypatch):
    run = selected.capture().run
    monkeypatch.setattr(evidence, "resolve_evidence_refs", lambda *a, **k: pytest.fail("opened Play review"))
    assert not catalog._same_session_evidence(run, None)
    assert not catalog._same_session_evidence(run, {**selected.bundle, "sha256": "b" * 64})


@pytest.mark.parametrize("fault", [
    "world", "digest", "revision", "bool_revision", "missing_hash", "sources_type", "citation", "database_body",
])
def test_bad_saved_pins_fail_despite_valid_old_copy(selected, fault):
    run = historical_run(selected)
    lineage = copy.deepcopy(run.lineage)
    sources = lineage["session_evidence"]["sources"]
    if fault == "world":
        lineage["world_campaign_ingest_context"]["managed_world_id"] = "foreign-world"
    elif fault == "digest":
        sources[0]["sha256"] = "a" * 64
    elif fault == "revision":
        sources[0]["review_revision"] = 99999
    elif fault == "bool_revision":
        sources[0]["review_revision"] = True
    elif fault == "missing_hash":
        del sources[0]["sha256"]
    elif fault == "sources_type":
        lineage["session_evidence"]["sources"] = {}
    elif fault == "citation":
        sources[0]["citation_url"] = "/unrelated-source"
    else:
        with psycopg.connect(selected.dsn) as conn:
            conn.execute(
                "UPDATE play.session_review_revision SET payload = jsonb_set(payload, '{final_thoughts}', %s::jsonb) WHERE run_id=%s AND revision_n=1",
                (json.dumps("Tampered private notes."), selected.run_id),
            )
    changed = run.model_copy(update={"lineage": lineage})
    with pytest.raises(catalog.IngestRunCatalogError) as caught:
        catalog._same_session_evidence(changed, selected.bundle)
    assert (caught.value.code, caught.value.status_code) == (catalog.CODE_INTEGRITY, 409)
    assert "Tampered private notes" not in str(caught.value)


@pytest.mark.parametrize("fault", ["text", "extra", "digest", "nested_type"])
def test_supplied_bundle_must_equal_its_exact_owner_before_source_or_prompt(selected, monkeypatch, fault):
    bundle = copy.deepcopy(selected.bundle)
    if fault == "text":
        bundle["sessions"][0]["sources"][0]["text"] = "Forged private instructions."
    elif fault == "extra":
        bundle["unowned"] = "Forged private instructions."
    elif fault == "nested_type":
        bundle["sessions"][0]["checkpoint_run_revision"] = float(bundle["sessions"][0]["checkpoint_run_revision"])
    else:
        bundle["sha256"] = "b" * 64
    monkeypatch.setattr(producer, "create_recap_source_artifact", lambda *a, **k: pytest.fail("source registered"))
    monkeypatch.setattr(producer, "run_production_extraction", lambda *a, **k: pytest.fail("inference entered"))
    monkeypatch.setattr(evidence, "render_session_evidence", lambda *a, **k: pytest.fail("forged prompt rendered"))
    with pytest.raises(ValueError, match="pinned review revisions") as caught:
        selected.capture(bundle)
    assert "Forged private instructions" not in str(caught.value)


def test_database_unavailability_is_not_recovered_by_a_copy(selected, monkeypatch):
    run = historical_run(selected)
    def unavailable(**kwargs):
        raise ApplicationStateUnavailableError("synthetic database unavailable")
    monkeypatch.setattr(evidence, "read_session_evidence", unavailable)
    with pytest.raises(catalog.IngestRunCatalogError) as caught:
        catalog._same_session_evidence(run, selected.bundle)
    assert (caught.value.code, caught.value.status_code) == (catalog.CODE_UNAVAILABLE, 503)


def test_producer_reopens_owner_before_source_registration(selected, monkeypatch):
    from application_state.errors import ApplicationStateError

    def unavailable(**kwargs):
        raise ApplicationStateUnavailableError("synthetic database unavailable")

    monkeypatch.setattr(evidence, "read_session_evidence", unavailable)
    monkeypatch.setattr(producer, "create_recap_source_artifact", lambda *a, **k: pytest.fail("source registered"))
    with pytest.raises(ApplicationStateError) as caught:
        selected.capture()
    assert caught.value.status_code == 503
    assert str(caught.value) == "Pinned session supplement could not be reopened."
