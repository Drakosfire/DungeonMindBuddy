"""Current-session fixtures explicitly supply complete scene choices and source identity."""
from uuid import UUID
from application_state.config import load_runtime_dsn
from application_state.unit_of_work import unit_of_work
from application_state.content.repository import get_work_revision_by_n
from application_state.errors import ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play.session_encounter_types import WorldSessionCreateRequest
from apps.live_control_server.services.play_run_edition_structure import structure_signature


def session_request(*,world_id,playable_artifact_id,expected_playable_revision,expected_playable_content_sha256):
    del world_id
    with unit_of_work(load_runtime_dsn()) as conn:
        revision=get_work_revision_by_n(conn,UUID(str(playable_artifact_id)),expected_playable_revision)
    if revision is None:
        raise ApplicationStateNotFoundError('Test source revision is missing')
    try:scenes=structure_signature(revision.markdown)['membership']['scenes']
    except ValueError as exc:
        raise ApplicationStateValidationError('New sessions require canonical v2 structure') from exc
    return WorldSessionCreateRequest(schema_version='dmb_world_session_create_v1',
        playable_artifact_id=playable_artifact_id,expected_playable_revision=expected_playable_revision,
        expected_playable_work_revision_id=revision.work_revision_id,
        expected_playable_content_sha256=expected_playable_content_sha256,
        entry_scene_id=scenes[0]['scene_id'] if scenes else None,
        encounters=[dict(scene_id=scene['scene_id'],template=None) for scene in scenes])


def historical_world_run(*,world_id,run_id,playable_artifact_id,expected_playable_revision,expected_playable_content_sha256):
    """Seed a pre-capture historical row to test retained readers/old migrations.

    This is a fixture writer, never a fresh product session creation route.
    """
    from application_state.play import repository as repo
    from application_state.play.service import _derive_manifest_document,EMPTY_PROGRESS
    from application_state.play.types import PlayRun,PlayRunManifest,WorldPlayRunAggregate
    from apps.live_control_server.services.play_run_registry import derive_v2_opening_beat_id
    with unit_of_work(load_runtime_dsn()) as conn:
        revision=get_work_revision_by_n(conn,UUID(str(playable_artifact_id)),expected_playable_revision)
        now=repo.now_utc();run_id=UUID(str(run_id));artifact_id=UUID(str(playable_artifact_id))
        manifest=_derive_manifest_document(revision.markdown,run_id=run_id,playable_artifact_id=artifact_id,
            playable_revision=expected_playable_revision,playable_content_sha256=expected_playable_content_sha256,sealed_at=now)
        progress=dict(EMPTY_PROGRESS)
        if manifest['schema_version']=='dmb_play_run_reference_manifest_v2':
            progress['current_beat_id']=derive_v2_opening_beat_id(revision.markdown)
        run=repo.insert_run(conn,PlayRun(run_id=run_id,campaign_id=None,world_id=world_id,
            playable_work_object_id=artifact_id,playable_revision_n=expected_playable_revision,
            playable_work_revision_id=revision.work_revision_id,playable_content_sha256=expected_playable_content_sha256,
            run_revision=1,progress=progress,created_at=now,updated_at=now))
        saved=repo.insert_manifest(conn,PlayRunManifest(run_id=run_id,playable_work_object_id=artifact_id,
            playable_revision_n=expected_playable_revision,playable_work_revision_id=revision.work_revision_id,
            playable_content_sha256=expected_playable_content_sha256,manifest=manifest,sealed_at=now))
        return WorldPlayRunAggregate(run=run,manifest=saved,world_id=world_id)
