from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import psycopg
import pytest
from tests.application_state.test_play_run_editions_postgres import create_source_run, read, WORLD, snapshot
from application_state.play.session_review import ReviewCommand, commit_review, read_review
from application_state.play.service import replace_world_play_run_progress
from application_state.play.lifecycle import set_world_play_session_trash
from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError


def request(run_id, action="end", revision=0, **extra):
    content = read(run_id)
    return ReviewCommand(action=action, expected_revision=revision, expected_run_revision=content.observed_run_revision,
                         expected_content_sha256=content.content_sha256, **extra)


def test_checkpoint_notes_draft_history_replay_and_plan_integrity(application_state_dsn):
    _, _, aggregate = create_source_run()
    run_id = str(aggregate.run.run_id)
    progress = dict(aggregate.run.progress)
    progress["notes_by_element_id"] = {"scene:gate": "Party saved a soldier; name uncertain."}
    replace_world_play_run_progress(world_id=WORLD, run_id=run_id, expected_run_revision=1, progress=progress)
    before = snapshot(application_state_dsn)
    command = str(uuid4()); body = request(run_id)
    ended = commit_review(world_id=WORLD, run_id=run_id, command_id=command, request=body)
    assert ended["status"] == "ended"
    assert ended["checkpoint"]["progress"] == progress
    assert "Party saved a soldier" in ended["draft_markdown"]
    assert read(run_id).markdown not in ended["draft_markdown"]
    assert commit_review(world_id=WORLD, run_id=run_id, command_id=command, request=body) == ended
    saved = commit_review(world_id=WORLD, run_id=run_id, command_id=str(uuid4()), request=request(run_id,"save",1,draft_markdown="# Reviewed draft\nThe soldier escaped."))
    assert saved["checkpoint"] == ended["checkpoint"]
    with pytest.raises(ApplicationStateConflictError):
        commit_review(world_id=WORLD, run_id=run_id, command_id=str(uuid4()), request=request(run_id,"save",1,draft_markdown="stale"))
    assert snapshot(application_state_dsn) == before
    reopened = commit_review(world_id=WORLD, run_id=run_id, command_id=str(uuid4()), request=request(run_id,"reopen",2))
    assert reopened["status"] == "playing" and reopened["draft_markdown"] == saved["draft_markdown"]
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM play.session_review_revision WHERE run_id=%s",(run_id,)).fetchone()[0] == 3
    assert read_review(world_id=WORLD,run_id=run_id)["review"] == reopened


def test_review_rejects_foreign_world_stale_source_and_duplicate_command_bytes(application_state_dsn):
    _,_,aggregate = create_source_run(); run_id=str(aggregate.run.run_id)
    assert read_review(world_id=WORLD,run_id=run_id)["review"] is None
    body=request(run_id); command=str(uuid4())
    with pytest.raises(ApplicationStateNotFoundError):read_review(world_id="other-world",run_id=run_id)
    with pytest.raises(ApplicationStateConflictError):
        commit_review(world_id=WORLD,run_id=run_id,command_id=command,request=body.model_copy(update={"expected_run_revision":999}))
    commit_review(world_id=WORLD,run_id=run_id,command_id=command,request=body)
    with pytest.raises(ApplicationStateConflictError):
        commit_review(world_id=WORLD,run_id=run_id,command_id=command,request=request(run_id,"save",1,draft_markdown="collision"))


def test_concurrent_end_commands_accept_only_one_checkpoint(application_state_dsn):
    _,_,aggregate=create_source_run();run_id=str(aggregate.run.run_id);body=request(run_id)
    def end():
        try:return commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=body)["revision"]
        except ApplicationStateConflictError:return "conflict"
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:end(),range(2)))
    assert sorted(map(str,results)) == ["1","conflict"]


def test_later_notes_do_not_rewrite_the_end_checkpoint_and_trash_blocks_review(application_state_dsn):
    _,_,aggregate=create_source_run();run_id=str(aggregate.run.run_id)
    ended=commit_review(world_id=WORLD,run_id=run_id,command_id=str(uuid4()),request=request(run_id))
    progress=dict(aggregate.run.progress);progress["notes_by_element_id"]={"scene:gate":"Later correction"}
    replace_world_play_run_progress(world_id=WORLD,run_id=run_id,expected_run_revision=1,progress=progress)
    observed=read_review(world_id=WORLD,run_id=run_id)
    assert observed["source_changed"] is True
    assert observed["review"]["checkpoint"]==ended["checkpoint"]
    set_world_play_session_trash(world_id=WORLD,run_id=aggregate.run.run_id,expected_revision=2,expected_content_revision=0,restore=False)
    with pytest.raises(ApplicationStateConflictError):read_review(world_id=WORLD,run_id=run_id)
