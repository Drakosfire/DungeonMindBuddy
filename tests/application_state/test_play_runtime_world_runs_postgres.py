from __future__ import annotations

from pathlib import Path
from uuid import UUID

import psycopg
import pytest

from application_state.content.service import (
    autosave_plan,
    commit_plan,
    commit_runbook,
    create_plan,
    create_world_plan,
    create_world_runbook,
    update_plan_metadata,
)
from application_state.errors import ApplicationStateError
from application_state.play.service import (
    create_play_run,
    create_world_play_run,
    get_world_play_run_aggregate,
    list_play_run_aggregates,
    list_world_play_run_aggregates,
    rebase_world_play_run,
    replace_world_play_run_progress,
)
from tests.application_state.play_runtime_helpers import (
    RUN_ID_A,
    RUN_ID_B,
    SOURCE_MARKDOWN,
    SURVIVING_TARGET_MARKDOWN,
    create_committed_runbook,
    create_run,
    fetch_play_runtime_state,
    gate_progress,
)

pytest_plugins = ["tests.application_state.conftest"]


def _create_world_runbook(world_id: str, *, markdown: str = SOURCE_MARKDOWN):
    created = create_world_runbook(
        title=f"World Runbook {world_id}", world_id=world_id
    )
    work_object, revision = commit_runbook(
        str(created.work_object_id),
        markdown,
        expected_revision=created.object_revision,
    )
    return work_object, revision


def _create_world_plan(world_id: str, *, markdown: str = SOURCE_MARKDOWN):
    created = create_world_plan(title=f"World Plan {world_id}", world_id=world_id)
    work_object, revision = commit_plan(
        str(created.work_object_id),
        markdown,
        expected_world_id=world_id,
        expected_revision=created.object_revision,
    )
    return work_object, revision


def _create_world_run(*, world_id: str = "demo-world-a", run_id: str = RUN_ID_A):
    work_object, revision = _create_world_runbook(world_id)
    run = create_world_play_run(
        world_id=world_id,
        run_id=run_id,
        playable_artifact_id=work_object.work_object_id,
        expected_playable_revision=revision.revision_n,
        expected_playable_content_sha256=revision.content_sha256,
    )
    return work_object, revision, run


def test_create_replay_list_and_campaign_inventory_are_owner_fenced(
    application_state_dsn: str, tmp_path: Path
) -> None:
    _world_object, _world_revision, created = _create_world_run()
    replayed = create_world_play_run(
        world_id="demo-world-a",
        run_id=RUN_ID_A,
        playable_artifact_id=created.run.playable_work_object_id,
        expected_playable_revision=created.run.playable_revision_n,
        expected_playable_content_sha256=created.run.playable_content_sha256,
    )
    assert replayed == created
    assert created.world_id == "demo-world-a"
    assert created.run.world_id == "demo-world-a"
    assert created.run.campaign_id is None

    listed = list_world_play_run_aggregates(world_id="demo-world-a")
    assert [item.run.run_id for item in listed] == [UUID(RUN_ID_A)]
    assert list_world_play_run_aggregates(world_id="demo-world-b") == []
    assert list_play_run_aggregates() == []

    campaign_snapshot = create_committed_runbook(
        tmp_path, name="world-run-inventory-campaign-control"
    )
    campaign_record = create_run(
        tmp_path,
        campaign_snapshot,
        run_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    )
    campaign_runs = list_play_run_aggregates()
    assert [item.run.run_id for item in campaign_runs] == [UUID(campaign_record.run_id)]


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("world_id", "demo-world-b"),
        ("playable_content_sha256", "f" * 64),
        ("playable_work_revision_id", "dddddddd-dddd-4ddd-8ddd-dddddddddddd"),
        ("playable_revision_n", 999),
    ],
)
def test_bad_owner_or_pin_fails_before_progress_mutation(
    application_state_dsn: str,
    column: str,
    value: str | int,
) -> None:
    _work_object, _revision, created = _create_world_run()
    before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
    with psycopg.connect(application_state_dsn, autocommit=True) as conn:
        conn.execute(
            f"UPDATE play.run SET {column} = %s WHERE run_id = %s",
            (value, RUN_ID_A),
        )

    with pytest.raises(ApplicationStateError):
        replace_world_play_run_progress(
            world_id="demo-world-a",
            run_id=RUN_ID_A,
            expected_run_revision=created.run.run_revision,
            progress=gate_progress().model_dump(mode="json"),
        )

    after = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
    assert after["run"]["run_revision"] == before["run"]["run_revision"]
    assert after["run"]["progress"] == before["run"]["progress"]
    assert after["manifest"] == before["manifest"]


def test_world_run_rebase_checks_same_owner_and_run_revision_cas(
    application_state_dsn: str,
) -> None:
    work_object, _first_revision, created = _create_world_run()
    progressed = replace_world_play_run_progress(
        world_id="demo-world-a",
        run_id=RUN_ID_A,
        expected_run_revision=created.run.run_revision,
        progress=gate_progress().model_dump(mode="json"),
    )
    target_work_object, target_revision = commit_runbook(
        str(work_object.work_object_id),
        SURVIVING_TARGET_MARKDOWN,
        expected_revision=work_object.object_revision,
    )
    assert target_work_object.world_id == "demo-world-a"
    rebased = rebase_world_play_run(
        world_id="demo-world-a",
        run_id=RUN_ID_A,
        expected_run_revision=progressed.run.run_revision,
        target_playable_revision=target_revision.revision_n,
        target_playable_content_sha256=target_revision.content_sha256,
    )
    assert rebased.world_id == "demo-world-a"
    assert rebased.run.run_revision == progressed.run.run_revision + 1
    assert rebased.run.playable_revision_n == target_revision.revision_n
    assert rebased.manifest.playable_work_revision_id == target_revision.work_revision_id

    before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)
    with pytest.raises(ApplicationStateError):
        rebase_world_play_run(
            world_id="demo-world-b",
            run_id=RUN_ID_A,
            expected_run_revision=rebased.run.run_revision,
            target_playable_revision=target_revision.revision_n,
            target_playable_content_sha256=target_revision.content_sha256,
        )
    assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before

    _, newer_revision = commit_runbook(
        str(work_object.work_object_id),
        SURVIVING_TARGET_MARKDOWN + "\nA newer pinned edit.\n",
        expected_revision=target_work_object.object_revision,
    )
    with pytest.raises(ApplicationStateError):
        rebase_world_play_run(
            world_id="demo-world-a",
            run_id=RUN_ID_A,
            expected_run_revision=1,
            target_playable_revision=newer_revision.revision_n,
            target_playable_content_sha256=newer_revision.content_sha256,
        )
    assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before


def test_detail_resolves_world_from_exact_committed_revision(
    application_state_dsn: str,
) -> None:
    _work_object, _revision, created = _create_world_run()
    loaded = get_world_play_run_aggregate(
        created.run.run_id, world_id="demo-world-a"
    )
    assert loaded.world_id == "demo-world-a"
    assert loaded.world_id == loaded.run.world_id


def test_world_plan_can_start_run_and_reopen_exact_pin_after_save_and_discard(
    application_state_dsn: str,
) -> None:
    world_id = "demo-world-plan-run"
    plan, first_revision = _create_world_plan(world_id)
    first = create_world_play_run(
        world_id=world_id,
        run_id=RUN_ID_A,
        playable_artifact_id=plan.work_object_id,
        expected_playable_revision=first_revision.revision_n,
        expected_playable_content_sha256=first_revision.content_sha256,
    )

    assert first.run.world_id == world_id
    assert first.run.campaign_id is None
    assert first.run.playable_work_object_id == plan.work_object_id
    assert first.run.playable_work_revision_id == first_revision.work_revision_id
    assert first.manifest.playable_work_revision_id == first_revision.work_revision_id
    assert first.manifest.playable_content_sha256 == first_revision.content_sha256

    changed_plan, second_revision = commit_plan(
        str(plan.work_object_id),
        SURVIVING_TARGET_MARKDOWN,
        expected_world_id=world_id,
        expected_revision=plan.object_revision,
    )
    with pytest.raises(ApplicationStateError):
        create_world_play_run(
            world_id=world_id,
            run_id=RUN_ID_B,
            playable_artifact_id=plan.work_object_id,
            expected_playable_revision=first_revision.revision_n,
            expected_playable_content_sha256=first_revision.content_sha256,
        )
    second = create_world_play_run(
        world_id=world_id,
        run_id=RUN_ID_B,
        playable_artifact_id=plan.work_object_id,
        expected_playable_revision=second_revision.revision_n,
        expected_playable_content_sha256=second_revision.content_sha256,
    )
    assert second.run.playable_work_revision_id == second_revision.work_revision_id

    discarded = update_plan_metadata(
        str(plan.work_object_id),
        status="discarded",
        expected_revision=changed_plan.object_revision,
    )
    assert discarded.status == "discarded"

    replayed = create_world_play_run(
        world_id=world_id,
        run_id=RUN_ID_A,
        playable_artifact_id=plan.work_object_id,
        expected_playable_revision=first_revision.revision_n,
        expected_playable_content_sha256=first_revision.content_sha256,
    )
    reopened = get_world_play_run_aggregate(RUN_ID_A, world_id=world_id)
    assert replayed == first
    assert reopened.run.playable_work_revision_id == first_revision.work_revision_id
    assert reopened.manifest == first.manifest


def test_world_plan_new_run_requires_clean_current_revision(
    application_state_dsn: str,
) -> None:
    world_id = "demo-world-plan-dirty"
    plan, revision = _create_world_plan(world_id)
    autosave_plan(
        str(plan.work_object_id),
        SOURCE_MARKDOWN + "\nUncommitted Plan edit.\n",
        expected_world_id=world_id,
        expected_revision=plan.object_revision,
    )

    with pytest.raises(ApplicationStateError, match="not committed"):
        create_world_play_run(
            world_id=world_id,
            run_id=RUN_ID_A,
            playable_artifact_id=plan.work_object_id,
            expected_playable_revision=revision.revision_n,
            expected_playable_content_sha256=revision.content_sha256,
        )


def test_campaign_run_admission_remains_runbook_only(
    application_state_dsn: str,
) -> None:
    plan = create_plan(title="Campaign Plan", campaign_id="campaign-plan-control")
    _plan, revision = commit_plan(
        str(plan.work_object_id),
        SOURCE_MARKDOWN,
        expected_revision=plan.object_revision,
    )

    with pytest.raises(ApplicationStateError, match="runbook"):
        create_play_run(
            run_id=RUN_ID_A,
            playable_artifact_id=plan.work_object_id,
            expected_playable_revision=revision.revision_n,
            expected_playable_content_sha256=revision.content_sha256,
        )


def test_world_plan_rebase_rejected_even_for_same_target_retry(
    application_state_dsn: str,
) -> None:
    world_id = "demo-world-plan-no-rebase"
    plan, revision = _create_world_plan(world_id)
    created = create_world_play_run(
        world_id=world_id,
        run_id=RUN_ID_A,
        playable_artifact_id=plan.work_object_id,
        expected_playable_revision=revision.revision_n,
        expected_playable_content_sha256=revision.content_sha256,
    )
    before = fetch_play_runtime_state(application_state_dsn, RUN_ID_A)

    with pytest.raises(ApplicationStateError, match="Plan-backed.*rebasing"):
        rebase_world_play_run(
            world_id=world_id,
            run_id=RUN_ID_A,
            expected_run_revision=created.run.run_revision,
            target_playable_revision=revision.revision_n,
            target_playable_content_sha256=revision.content_sha256,
        )

    assert fetch_play_runtime_state(application_state_dsn, RUN_ID_A) == before
