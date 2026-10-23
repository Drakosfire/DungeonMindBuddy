
from tests.application_state.session_encounter_helpers import session_request, historical_world_run
"""Owning persistence/concurrency evidence; every test gets a fresh fixture DB."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from alembic import command

from application_state.cli import alembic_config
from application_state.content.service import (
    autosave_plan,
    commit_plan,
    commit_runbook,
    create_world_plan,
    create_world_runbook,
    update_plan_metadata,
)
from application_state.errors import (
    ApplicationStateError,
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
)
from application_state.play import edition_repository
from application_state.play.edition_service import (
    commit_content,
    read_context_snapshot,
    read_command,
    read_content,
)
from application_state.play.edition_types import ContentCommit
from application_state.play.service import (
    create_world_play_run,
    get_world_play_run_aggregate,
    get_world_play_active_run,
    rebase_world_play_run,
    replace_world_play_run_progress,
    set_world_play_active_run,
)
from application_state.play.lifecycle import (
    list_trashed_world_play_sessions,
    set_world_play_session_trash,
)
from tests.application_state.play_runtime_helpers import V2_SOURCE_MARKDOWN
from apps.live_control_server.services.play_run_registry import get_world_play_run

WORLD = "edition-test-world"


def create_source_run(kind="plan", markdown=V2_SOURCE_MARKDOWN):
    create = create_world_plan if kind == "plan" else create_world_runbook
    commit = commit_plan if kind == "plan" else commit_runbook
    obj = create(title="Edition origin", world_id=WORLD)
    obj, revision = commit(
        str(obj.work_object_id), markdown, expected_revision=obj.object_revision
    )
    run = historical_world_run(run_id=str(uuid4()), world_id=WORLD, playable_artifact_id=obj.work_object_id, expected_playable_revision=revision.revision_n, expected_playable_content_sha256=revision.content_sha256)
    return obj, revision, run


def request_for(content, suffix="Live detail"):
    return ContentCommit(
        schema_version="dmb_world_play_run_content_commit_v1",
        expected_origin=content.origin,
        expected_edition_revision=content.edition_revision,
        expected_content_sha256=content.content_sha256,
        markdown=content.markdown + "\n" + suffix + "\n",
    )


def read(run_id, **kwargs):
    return read_content(run_id=str(run_id), world_id=WORLD, **kwargs)


def save(run_id, request, command_id=None):
    return commit_content(
        run_id=str(run_id),
        world_id=WORLD,
        command_id=command_id or str(uuid4()),
        request=request,
    )


def snapshot(dsn):
    with psycopg.connect(dsn) as conn:
        return {
            table: conn.execute(
                f"SELECT row_to_json(t) FROM {table} t ORDER BY 1::text"
            ).fetchall()
            for table in [
                "play.run",
                "play.run_manifest",
                "content.work_object",
                "content.work_revision",
                "content.working_copy",
            ]
        }


def test_context_snapshot_binds_run_progress_and_effective_edition(
    application_state_dsn,
):
    _, _, aggregate = create_source_run()
    run_id = aggregate.run.run_id
    progressed = replace_world_play_run_progress(
        world_id=WORLD,
        run_id=run_id,
        expected_run_revision=1,
        progress={
            "current_scene_id": "scene:gate",
            "current_beat_id": "beat:arrival",
            "resolved_beat_ids": [],
            "selections": {},
            "notes_by_element_id": {"scene:gate": "GM note bound to this Run revision."},
        },
    )
    pinned = read(run_id)
    accepted = save(run_id, request_for(pinned, "Saved session-copy context"))

    run, content = read_context_snapshot(run_id=str(run_id), world_id=WORLD)

    assert run.run_revision == progressed.run.run_revision
    assert run.progress["notes_by_element_id"]["scene:gate"] == "GM note bound to this Run revision."
    assert content.source == "edition"
    assert content.edition_revision == accepted.accepted_edition_revision
    assert content.edition_revision_id == accepted.accepted_edition_revision_id
    assert content.content_sha256 == accepted.accepted_content_sha256
    assert content.markdown.endswith("Saved session-copy context\n")


def test_world_play_trash_preserves_history_replay_and_requires_explicit_restore(
    application_state_dsn,
):
    _, _, aggregate = create_source_run()
    _, _, other = create_source_run()
    run_id = aggregate.run.run_id
    set_world_play_active_run(WORLD, run_id)
    initial = read(run_id)
    command_id = str(uuid4())
    request = request_for(initial, "Saved before trash")
    receipt = save(run_id, request, command_id)

    trashed = set_world_play_session_trash(
        world_id=WORLD, run_id=run_id, expected_revision=1,
        expected_content_revision=1, restore=False,
    )
    assert trashed["status"] == "trashed"
    assert trashed["revision"] == 2
    assert trashed["content_revision"] == 1
    assert list_trashed_world_play_sessions(world_id=WORLD)[0]["id"] == str(run_id)
    assert get_world_play_run(Path("."), world_id=WORLD, run_id=str(run_id)).lifecycle_status == "trashed"
    assert get_world_play_active_run(world_id=WORLD) is None
    assert read(run_id).markdown == request.markdown
    assert read_command(run_id=str(run_id), world_id=WORLD, command_id=command_id) == receipt
    assert save(run_id, request, command_id) == receipt
    with pytest.raises(ApplicationStateConflictError, match="Trash"):
        save(run_id, request_for(read(run_id), "Not admitted while trashed"))

    restored = set_world_play_session_trash(
        world_id=WORLD, run_id=run_id, expected_revision=2,
        expected_content_revision=1, restore=True,
    )
    assert restored["status"] == "active"
    assert restored["revision"] == 3
    assert list_trashed_world_play_sessions(world_id=WORLD) == []
    assert get_world_play_active_run(world_id=WORLD) is None


def test_world_play_trash_rejects_stale_heads_foreign_world_and_new_writes(
    application_state_dsn,
):
    _, _, aggregate = create_source_run()
    _, _, other = create_source_run()
    run_id = aggregate.run.run_id
    set_world_play_active_run(WORLD, other.run.run_id)
    initial = read(run_id)
    save(run_id, request_for(initial, "Advance head"))
    replace_world_play_run_progress(
        world_id=WORLD, run_id=run_id, expected_run_revision=1,
        progress={
            "current_scene_id": "scene:gate", "current_beat_id": "beat:arrival",
            "resolved_beat_ids": [], "selections": {}, "notes_by_element_id": {},
        },
    )
    current = get_world_play_run_aggregate(run_id, world_id=WORLD)
    assert current.run.run_revision == 2

    with pytest.raises(ApplicationStateConflictError, match="content revision"):
        set_world_play_session_trash(
            world_id=WORLD, run_id=run_id, expected_revision=2,
            expected_content_revision=0, restore=False,
        )
    with pytest.raises(ApplicationStateConflictError, match="revision changed"):
        set_world_play_session_trash(
            world_id=WORLD, run_id=run_id, expected_revision=1,
            expected_content_revision=1, restore=False,
        )
    with pytest.raises(ApplicationStateNotFoundError):
        set_world_play_session_trash(
            world_id="another-world", run_id=run_id, expected_revision=2,
            expected_content_revision=1, restore=False,
        )
    assert get_world_play_run_aggregate(run_id, world_id=WORLD).run.lifecycle_status == "active"
    assert get_world_play_active_run(world_id=WORLD).run_id == other.run.run_id

    trashed = set_world_play_session_trash(
        world_id=WORLD, run_id=run_id, expected_revision=2,
        expected_content_revision=1, restore=False,
    )
    with pytest.raises(ApplicationStateConflictError, match="Trash"):
        replace_world_play_run_progress(
            world_id=WORLD, run_id=run_id, expected_run_revision=trashed["revision"],
            progress={
                "current_scene_id": "scene:gate", "current_beat_id": "beat:arrival",
                "resolved_beat_ids": [], "selections": {}, "notes_by_element_id": {},
            },
        )
    with pytest.raises(ApplicationStateConflictError, match="Trash"):
        set_world_play_active_run(WORLD, run_id)
    assert get_world_play_active_run(world_id=WORLD).run_id == other.run.run_id


def test_original_pin_remains_readable_after_plan_is_discarded_and_zero_head_trash_restores(
    application_state_dsn,
):
    obj, pin, aggregate = create_source_run()
    update_plan_metadata(
        str(obj.work_object_id), status="discarded", expected_revision=obj.object_revision
    )
    assert read(aggregate.run.run_id).markdown == pin.markdown

    trashed = set_world_play_session_trash(
        world_id=WORLD, run_id=aggregate.run.run_id, expected_revision=1,
        expected_content_revision=0, restore=False,
    )
    assert trashed["content_revision"] == 0
    restored = set_world_play_session_trash(
        world_id=WORLD, run_id=aggregate.run.run_id, expected_revision=2,
        expected_content_revision=0, restore=True,
    )
    assert restored["content_revision"] == 0


def test_content_commit_racing_trash_serializes_on_run_lock(application_state_dsn):
    _, _, aggregate = create_source_run()
    run_id = aggregate.run.run_id
    basis = read(run_id)
    request = request_for(basis, "Racing content commit")
    start = Barrier(2)

    def commit():
        start.wait()
        try:
            return ("commit", save(run_id, request))
        except ApplicationStateConflictError:
            return ("commit_conflict", None)

    def trash():
        start.wait()
        try:
            return ("trash", set_world_play_session_trash(
                world_id=WORLD, run_id=run_id, expected_revision=1,
                expected_content_revision=0, restore=False,
            ))
        except ApplicationStateConflictError:
            return ("trash_conflict", None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(commit), pool.submit(trash)]
        outcomes = [future.result(timeout=10)[0] for future in results]

    assert sum(outcome in {"commit", "trash"} for outcome in outcomes) == 1
    if "trash" in outcomes:
        assert get_world_play_run_aggregate(run_id, world_id=WORLD).run.lifecycle_status == "trashed"
        assert read(run_id).markdown == basis.markdown
    else:
        assert get_world_play_run_aggregate(run_id, world_id=WORLD).run.lifecycle_status == "active"
        assert read(run_id).edition_revision == 1


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_pin_history_durable_replay_and_independent_progress(
    application_state_dsn, kind
):
    obj, pin, aggregate = create_source_run(kind)
    _, _, other = create_source_run(kind)
    run_id = aggregate.run.run_id
    progressed = replace_world_play_run_progress(
        world_id=WORLD,
        run_id=run_id,
        expected_run_revision=1,
        progress={
            "current_scene_id": "scene:gate",
            "current_beat_id": "beat:arrival",
            "resolved_beat_ids": [],
            "selections": {},
            "notes_by_element_id": {"scene:gate": "GM note"},
        },
    )
    # Advance originating Plan/legacy Runbook after the Run starts. Live must not follow it.
    commit = commit_plan if kind == "plan" else commit_runbook
    updated, _ = commit(
        str(obj.work_object_id),
        V2_SOURCE_MARKDOWN + "\nLater Plan detail\n",
        expected_revision=obj.object_revision,
    )
    if kind == "plan":
        autosave_plan(
            str(obj.work_object_id),
            "Uncommitted Plan text",
            expected_revision=updated.object_revision,
        )
    before = snapshot(application_state_dsn)
    initial = read(run_id)
    assert initial.source == "pinned" and initial.edition_revision == 0
    assert initial.markdown == pin.markdown
    req1 = request_for(initial)
    cmd1 = str(uuid4())
    receipt1 = save(run_id, req1, cmd1)
    assert receipt1.observed_run_revision == progressed.run.run_revision
    v1 = read(run_id)
    receipt2 = save(run_id, request_for(v1, "Second edition"))
    assert receipt2.accepted_edition_revision == 2
    assert read(run_id).edition_revision == 2
    assert read(run_id, revision_n=0).markdown == initial.markdown
    assert read(run_id, revision_n=1).markdown == req1.markdown
    assert save(run_id, req1, cmd1) == receipt1
    assert read_command(run_id=str(run_id), world_id=WORLD, command_id=cmd1) == receipt1
    assert read(other.run.run_id).edition_revision == 0
    assert snapshot(application_state_dsn) == before
    assert get_world_play_run_aggregate(run_id, world_id=WORLD) == progressed


@pytest.mark.parametrize("change", ["revision", "hash", "origin", "structure", "noop"])
def test_invalid_commit_is_atomic(application_state_dsn, change):
    _, _, run = create_source_run()
    run_id = run.run.run_id
    initial = read(run_id)
    req = request_for(initial)
    data = req.model_dump()
    if change == "revision":
        data["expected_edition_revision"] = 1
    if change == "hash":
        data["expected_content_sha256"] = "f" * 64
    if change == "origin":
        data["expected_origin"]["playable_revision"] = 9
    if change == "structure":
        data["markdown"] = req.markdown.replace("scene:gate", "scene:renamed")
    if change == "noop":
        data["markdown"] = initial.markdown
    before = snapshot(application_state_dsn)
    with pytest.raises(ApplicationStateError):
        save(run_id, ContentCommit.model_validate(data))
    assert read(run_id) == initial
    assert snapshot(application_state_dsn) == before
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT count(*) FROM play.run_edition").fetchone()[0] == 0
        assert (
            conn.execute("SELECT count(*) FROM play.run_edition_revision").fetchone()[0]
            == 0
        )


def test_command_mismatch_rollback_and_owner_fence(application_state_dsn, monkeypatch):
    _, _, run = create_source_run()
    run_id = run.run.run_id
    initial = read(run_id)
    cmd = str(uuid4())
    original = edition_repository.advance_head

    def fail(*args):
        raise RuntimeError("injected post-insert fault")

    monkeypatch.setattr(edition_repository, "advance_head", fail)
    with pytest.raises(RuntimeError, match="post-insert"):
        save(run_id, request_for(initial), cmd)
    assert read(run_id) == initial
    with pytest.raises(ApplicationStateError) as absent:
        read_command(run_id=str(run_id), world_id=WORLD, command_id=cmd)
    assert absent.value.status_code == 404
    monkeypatch.setattr(edition_repository, "advance_head", original)
    save(run_id, request_for(initial), cmd)
    with pytest.raises(ApplicationStateConflictError):
        save(run_id, request_for(initial, "Different"), cmd)
    for operation, kwargs in [
        (read_content, {}),
        (read_command, {"command_id": cmd}),
        (commit_content, {"command_id": cmd, "request": request_for(initial)}),
    ]:
        with pytest.raises(ApplicationStateError) as wrong:
            operation(run_id=str(run_id), world_id="wrong-world", **kwargs)
        assert wrong.value.status_code == 404


@pytest.mark.parametrize("same_command", [False, True])
def test_concurrent_first_edits_and_identical_command_replay(
    application_state_dsn, same_command
):
    _, _, run = create_source_run()
    initial = read(run.run.run_id)
    barrier = Barrier(2)
    cmd = str(uuid4())

    def worker(n):
        barrier.wait()
        try:
            return save(
                run.run.run_id,
                request_for(initial, "same" if same_command else str(n)),
                cmd if same_command else str(uuid4()),
            )
        except ApplicationStateError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [1, 2]))
    assert read(run.run.run_id).edition_revision == 1
    if same_command:
        assert results[0] == results[1]
    else:
        assert results.count(409) == 1


def test_progress_race_does_not_stale_content_cas(application_state_dsn):
    _, _, run = create_source_run()
    initial = read(run.run.run_id)
    barrier = Barrier(2)

    def content():
        barrier.wait()
        return save(run.run.run_id, request_for(initial))

    def progress():
        barrier.wait()
        return replace_world_play_run_progress(
            world_id=WORLD,
            run_id=run.run.run_id,
            expected_run_revision=1,
            progress={
                "current_scene_id": "scene:gate",
                "current_beat_id": "beat:arrival",
                "resolved_beat_ids": [],
                "selections": {},
                "notes_by_element_id": {"scene:gate": "Independent"},
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        a, b = pool.submit(content), pool.submit(progress)
        receipt, progressed = a.result(), b.result()
    assert receipt.observed_run_revision in (1, 2)
    assert progressed.run.run_revision == 2
    assert read(run.run.run_id).edition_revision == 1
    save(run.run.run_id, request_for(read(run.run.run_id)))


def test_rebase_and_first_edition_race_freezes_winning_origin(application_state_dsn):
    obj, _, run = create_source_run("runbook")
    initial = read(run.run.run_id)
    _, target = commit_runbook(
        str(obj.work_object_id),
        V2_SOURCE_MARKDOWN + "\nNew source\n",
        expected_revision=obj.object_revision,
    )
    barrier = Barrier(2)

    def worker(edit):
        barrier.wait()
        try:
            if edit:
                return save(run.run.run_id, request_for(initial))
            return rebase_world_play_run(
                world_id=WORLD,
                run_id=run.run.run_id,
                expected_run_revision=1,
                target_playable_revision=target.revision_n,
                target_playable_content_sha256=target.content_sha256,
            )
        except ApplicationStateError as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(worker, [True, False]))
    assert results.count(409) == 1
    current = read(run.run.run_id)
    if current.edition_revision == 0:
        assert current.origin.playable_revision == target.revision_n
        save(run.run.run_id, request_for(current))
    with pytest.raises(ApplicationStateConflictError, match="local content editions"):
        rebase_world_play_run(
            world_id=WORLD,
            run_id=run.run.run_id,
            expected_run_revision=get_world_play_run_aggregate(
                run.run.run_id, world_id=WORLD
            ).run.run_revision,
            target_playable_revision=target.revision_n,
            target_playable_content_sha256=target.content_sha256,
        )


@pytest.mark.parametrize(
    "table,column,value",
    [
        ("run_edition", "world_id", "wrong"),
        ("run_edition", "structure_sha256", "f" * 64),
        ("run_edition", "head_revision", 1),
        ("run_edition_revision", "content_sha256", "f" * 64),
        ("run_edition_revision", "request_sha256", "f" * 64),
        ("run_edition_revision", "expected_sha256", "f" * 64),
    ],
)
def test_corrupt_content_fails_closed_including_replay(
    application_state_dsn, table, column, value
):
    _, _, run = create_source_run()
    initial = read(run.run.run_id)
    cmd = str(uuid4())
    request = request_for(initial)
    save(run.run.run_id, request, cmd)
    save(run.run.run_id, request_for(read(run.run.run_id)))
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            f"UPDATE play.{table} SET {column} = %s WHERE run_id = %s",
            (value, run.run.run_id),
        )
    with pytest.raises(ApplicationStateError):
        read(run.run.run_id)
    with pytest.raises(ApplicationStateError):
        save(run.run.run_id, request, cmd)


def test_upgrade_preserves_old_run_and_downgrade_refuses_history(application_state_dsn):
    _, _, run = create_source_run()
    before = snapshot(application_state_dsn)
    command.downgrade(alembic_config(), "20261018_0034")
    command.upgrade(alembic_config(), "head")
    assert snapshot(application_state_dsn) == before
    initial = read(run.run.run_id)
    save(run.run.run_id, request_for(initial))
    with pytest.raises(RuntimeError, match="refusing to discard"):
        command.downgrade(alembic_config(), "20261018_0034")
    assert read(run.run.run_id).edition_revision == 1


def test_world_v1_unsupported_and_legacy_entry_cannot_rebase_editions(
    application_state_dsn,
):
    from application_state.play.service import rebase_play_run
    from tests.application_state.play_runtime_helpers import SOURCE_MARKDOWN

    _, _, v1 = create_source_run("runbook", markdown=SOURCE_MARKDOWN)
    with pytest.raises(ApplicationStateError, match="World grammar v2"):
        read(v1.run.run_id)
    obj, pin, run = create_source_run("runbook")
    first = read(run.run.run_id)
    save(run.run.run_id, request_for(first))
    before = snapshot(application_state_dsn)
    with pytest.raises(ApplicationStateError):
        rebase_play_run(
            run_id=run.run.run_id,
            expected_run_revision=1,
            target_playable_revision=pin.revision_n,
            target_playable_content_sha256=pin.content_sha256,
        )
    assert snapshot(application_state_dsn) == before
    assert read(run.run.run_id).edition_revision == 1


@pytest.mark.parametrize(
    "column,value",
    [
        ("playable_content_sha256", "f" * 64),
        ("world_id", "wrong"),
        ("playable_work_revision_id", "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
    ],
)
def test_pin_corruption_prevents_read_and_command_replay(
    application_state_dsn, column, value
):
    _, _, run = create_source_run()
    request = request_for(read(run.run.run_id))
    cmd = str(uuid4())
    save(run.run.run_id, request, cmd)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            f"UPDATE play.run SET {column} = %s WHERE run_id = %s",
            (value, run.run.run_id),
        )
    with pytest.raises(ApplicationStateError):
        read(run.run.run_id)
    with pytest.raises(ApplicationStateError):
        save(run.run.run_id, request, cmd)


def test_database_head_and_previous_revision_are_same_run_fenced(application_state_dsn):
    _, _, first = create_source_run()
    _, _, second = create_source_run()
    save(first.run.run_id, request_for(read(first.run.run_id)))
    with psycopg.connect(application_state_dsn) as conn:
        header = edition_repository.get_edition(conn, first.run.run_id)
        row = edition_repository.revisions(conn, first.run.run_id)[0]
    # Run B cannot use Run A's revision 1 as its own previous revision.
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with psycopg.connect(application_state_dsn) as conn:
            edition_repository.insert_edition(
                conn, {**header, "run_id": second.run.run_id, "head_revision": 2}
            )
            edition_repository.insert_revision(
                conn,
                {
                    **row,
                    "run_id": second.run.run_id,
                    "revision_n": 2,
                    "revision_id": uuid4(),
                    "previous_revision": 1,
                    "expected_revision": 1,
                },
            )
    assert read(second.run.run_id).edition_revision == 0
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute(
                "UPDATE play.run_edition SET head_revision = 2 WHERE run_id = %s",
                (first.run.run_id,),
            )


def test_fresh_process_recovers_exact_content_and_receipt(application_state_dsn):
    import json
    import os
    import subprocess
    import sys

    _, _, run = create_source_run()
    initial = read(run.run.run_id)
    command_id = str(uuid4())
    receipt = save(run.run.run_id, request_for(initial), command_id)
    save(run.run.run_id, request_for(read(run.run.run_id), "Later"))
    code = """import json,sys
from application_state.play.edition_service import read_content,read_command
print(json.dumps({"content":read_content(run_id=sys.argv[1],world_id=sys.argv[2],revision_n=1).model_dump(mode="json"),"receipt":read_command(run_id=sys.argv[1],world_id=sys.argv[2],command_id=sys.argv[3]).model_dump(mode="json")}))
"""
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
    result = subprocess.run(
        [sys.executable, "-c", code, str(run.run.run_id), WORLD, command_id],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    recovered = json.loads(result.stdout)
    assert recovered["receipt"] == receipt.model_dump(mode="json")
    assert recovered["content"] == read(run.run.run_id, revision_n=1).model_dump(
        mode="json"
    )


def test_exact_utf8_and_line_endings_survive_readback(application_state_dsn):
    _, _, run = create_source_run()
    first = read(run.run.run_id)
    exact = first.markdown.replace("\n", "\r\n") + "\r\nCafé 🧙\r\n"
    request = request_for(first).model_copy(update={"markdown": exact})
    receipt = save(run.run.run_id, request)
    content = read(run.run.run_id, revision_n=1)
    assert content.markdown.encode("utf-8") == exact.encode("utf-8")
    assert content.content_sha256 == receipt.accepted_content_sha256


def test_reviewed_scene_commit_checks_run_revision_atomically_but_replay_is_historical(application_state_dsn):
    _, _, aggregate = create_source_run()
    run = aggregate.run
    content = read(run.run_id)
    request = request_for(content, "Reviewed edit").model_copy(update={"expected_run_revision": run.run_revision})
    progressed = replace_world_play_run_progress(world_id=WORLD, run_id=run.run_id, expected_run_revision=run.run_revision,
        progress={**run.progress, "notes_by_element_id": {"scene:gate": "Changed after review"}})
    with pytest.raises(ApplicationStateConflictError, match="progress or notes"):
        save(run.run_id, request)
    assert read(run.run_id).edition_revision == 0
    fresh = request.model_copy(update={"expected_run_revision": progressed.run.run_revision})
    command_id = str(uuid4())
    receipt = save(run.run_id, fresh, command_id)
    assert receipt.observed_run_revision == progressed.run.run_revision
    replace_world_play_run_progress(world_id=WORLD, run_id=run.run_id, expected_run_revision=progressed.run.run_revision,
        progress={**progressed.run.progress, "notes_by_element_id": {"scene:gate": "Later note"}})
    assert save(run.run_id, fresh, command_id) == receipt
    assert read(run.run_id, revision_n=1).markdown.endswith("Reviewed edit\n")
