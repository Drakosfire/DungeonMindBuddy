"""Play Runtime service: one UoW for create+manifest, CAS progress, and rebase."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content.playable_admission import admit_playable_revision
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.play import repository as repo
from application_state.play.types import PlayRun, PlayRunAggregate, PlayRunManifest
from application_state.unit_of_work import unit_of_work

EMPTY_PROGRESS: dict = {
    "current_scene_id": None,
    "current_beat_id": None,
    "resolved_beat_ids": [],
    "selections": {},
    "notes_by_element_id": {},
}


def _as_uuid(value: UUID | str, *, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        parsed = UUID(str(value))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ApplicationStateValidationError(f"{field_name} must be a UUID") from exc
    if str(value) != str(parsed):
        raise ApplicationStateValidationError(f"{field_name} must be a canonical UUID")
    return parsed


def _require_positive_revision(value: int, *, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ApplicationStateValidationError(f"{field_name} must be a positive integer")
    return value


def _iso_z(value: datetime) -> str:
    stamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _binding_matches(run: PlayRun, *, artifact_id: UUID, revision_n: int, sha256: str) -> bool:
    return (
        run.playable_work_object_id == artifact_id
        and run.playable_revision_n == revision_n
        and run.playable_content_sha256 == sha256
    )


def _require_coherent_manifest(run: PlayRun, manifest: PlayRunManifest | None) -> PlayRunManifest:
    if manifest is None:
        raise ApplicationStateIntegrityError(
            "READY Play Run is missing its required sealed manifest"
        )
    if (
        manifest.playable_work_object_id != run.playable_work_object_id
        or manifest.playable_revision_n != run.playable_revision_n
        or manifest.playable_work_revision_id != run.playable_work_revision_id
        or manifest.playable_content_sha256 != run.playable_content_sha256
    ):
        raise ApplicationStateIntegrityError(
            "play.run_manifest identity does not match the Run binding"
        )
    return manifest


def _derive_manifest_document(
    markdown: str,
    *,
    run_id: UUID,
    playable_artifact_id: UUID,
    playable_revision: int,
    playable_content_sha256: str,
    sealed_at: datetime,
) -> dict:
    from apps.live_control_server.services.play_run_reference_manifest import (
        PlayRunReferenceManifestError,
        derive_sealed_manifest,
    )

    try:
        manifest = derive_sealed_manifest(
            markdown,
            run_id=str(run_id),
            playable_artifact_id=str(playable_artifact_id),
            playable_revision=playable_revision,
            playable_content_sha256=playable_content_sha256,
            sealed_at=_iso_z(sealed_at),
        )
    except PlayRunReferenceManifestError as exc:
        raise ApplicationStateValidationError(str(exc), status_code=exc.status_code) from exc
    return manifest.model_dump(mode="json", exclude_none=True)


def _admit_progress_payload(
    progress: dict, manifest_payload: dict, *, run_id: UUID, status_code: int
) -> dict:
    canonical = {
        "current_scene_id": progress.get("current_scene_id"),
        "current_beat_id": progress.get("current_beat_id"),
        "resolved_beat_ids": sorted(set(progress.get("resolved_beat_ids") or [])),
        "selections": dict(progress.get("selections") or {}),
        "notes_by_element_id": dict(progress.get("notes_by_element_id") or {}),
    }
    if (
        canonical["current_scene_id"] is None
        and canonical["current_beat_id"] is None
        and canonical["resolved_beat_ids"] == []
        and canonical["selections"] == {}
        and canonical["notes_by_element_id"] == {}
    ):
        return canonical
    from apps.live_control_server.services.play_run_registry import (
        PlayRunProgress,
        PlayRunRegistryError,
        _admit_progress,
    )
    from apps.live_control_server.services.play_run_reference_manifest import (
        parse_manifest_payload,
    )

    parsed = parse_manifest_payload(manifest_payload, run_id=str(run_id))
    try:
        admitted = _admit_progress(
            PlayRunProgress.model_validate(progress),
            manifest=parsed,
            status_code=status_code,
        )
    except PlayRunRegistryError as exc:
        raise ApplicationStateConflictError(str(exc), status_code=exc.status_code) from exc
    return admitted.model_dump(mode="json")


def create_play_run(
    *,
    run_id: UUID | str,
    playable_artifact_id: UUID | str,
    expected_playable_revision: int,
    expected_playable_content_sha256: str,
) -> PlayRunAggregate:
    canonical_run_id = _as_uuid(run_id, field_name="run_id")
    artifact_id = _as_uuid(playable_artifact_id, field_name="playable_artifact_id")
    revision_n = _require_positive_revision(
        expected_playable_revision, field_name="expected_playable_revision"
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.get_run(conn, canonical_run_id)
        if existing is not None:
            manifest = _require_coherent_manifest(
                existing, repo.get_manifest(conn, canonical_run_id)
            )
            if _binding_matches(
                existing,
                artifact_id=artifact_id,
                revision_n=revision_n,
                sha256=expected_playable_content_sha256,
            ):
                return PlayRunAggregate(run=existing, manifest=manifest)
            raise ApplicationStateConflictError(
                "run_id is already bound to a different Playable revision"
            )
        admitted = admit_playable_revision(
            conn,
            artifact_id,
            revision_n,
            expected_playable_content_sha256,
            require_current=True,
            require_clean=True,
        )
        now = repo.now_utc()
        document = _derive_manifest_document(
            admitted.work_revision.markdown,
            run_id=canonical_run_id,
            playable_artifact_id=artifact_id,
            playable_revision=admitted.work_revision.revision_n,
            playable_content_sha256=admitted.work_revision.content_sha256,
            sealed_at=now,
        )
        run = repo.insert_run(
            conn,
            PlayRun(
                run_id=canonical_run_id,
                campaign_id=admitted.work_object.campaign_id,
                playable_work_object_id=artifact_id,
                playable_revision_n=admitted.work_revision.revision_n,
                playable_work_revision_id=admitted.work_revision.work_revision_id,
                playable_content_sha256=admitted.work_revision.content_sha256,
                run_revision=1,
                progress=dict(EMPTY_PROGRESS),
                created_at=now,
                updated_at=now,
            ),
        )
        manifest = repo.insert_manifest(
            conn,
            PlayRunManifest(
                run_id=canonical_run_id,
                playable_work_object_id=artifact_id,
                playable_revision_n=admitted.work_revision.revision_n,
                playable_work_revision_id=admitted.work_revision.work_revision_id,
                playable_content_sha256=admitted.work_revision.content_sha256,
                manifest=document,
                sealed_at=now,
            ),
        )
        return PlayRunAggregate(run=run, manifest=manifest)


def get_play_run_aggregate(run_id: UUID | str) -> PlayRunAggregate:
    canonical_run_id = _as_uuid(run_id, field_name="run_id")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.get_run(conn, canonical_run_id)
        if run is None:
            raise ApplicationStateNotFoundError(f"Play Run not found: {canonical_run_id}")
        manifest = _require_coherent_manifest(run, repo.get_manifest(conn, canonical_run_id))
        return PlayRunAggregate(run=run, manifest=manifest)


def get_play_run_manifest(run_id: UUID | str) -> PlayRunManifest:
    return get_play_run_aggregate(run_id).manifest


def replay_play_run_manifest(run_id: UUID | str) -> PlayRunManifest:
    """Idempotent proof/read of the already-sealed row. Never derives a missing manifest."""
    return get_play_run_manifest(run_id)


def list_play_run_aggregates(
    *,
    campaign_id: str | None = None,
    playable_artifact_id: UUID | str | None = None,
) -> list[PlayRunAggregate]:
    artifact = (
        None
        if playable_artifact_id is None
        else _as_uuid(playable_artifact_id, field_name="playable_artifact_id")
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        runs = repo.list_runs(
            conn,
            campaign_id=campaign_id,
            playable_work_object_id=artifact,
        )
        aggregates: list[PlayRunAggregate] = []
        for run in runs:
            manifest = _require_coherent_manifest(run, repo.get_manifest(conn, run.run_id))
            aggregates.append(PlayRunAggregate(run=run, manifest=manifest))
        return aggregates


def replace_play_run_progress(
    *,
    run_id: UUID | str,
    expected_run_revision: int,
    progress: dict,
) -> PlayRun:
    canonical_run_id = _as_uuid(run_id, field_name="run_id")
    expected = _require_positive_revision(
        expected_run_revision, field_name="expected_run_revision"
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.lock_run(conn, canonical_run_id)
        if run is None:
            raise ApplicationStateNotFoundError(f"Play Run not found: {canonical_run_id}")
        manifest = _require_coherent_manifest(run, repo.get_manifest(conn, canonical_run_id))
        admitted = _admit_progress_payload(
            progress, manifest.manifest, run_id=canonical_run_id, status_code=422
        )
        if expected == run.run_revision and admitted == run.progress:
            return run
        if expected == run.run_revision - 1 and admitted == run.progress:
            return run
        if expected != run.run_revision:
            raise ApplicationStateConflictError(
                "run_revision does not match the current Play Run"
            )
        updated = repo.cas_replace_progress(
            conn,
            run_id=canonical_run_id,
            expected_run_revision=expected,
            progress=admitted,
            updated_at=repo.now_utc(),
        )
        if updated is None:
            raise ApplicationStateConflictError(
                "run_revision does not match the current Play Run"
            )
        return updated


def rebase_play_run(
    *,
    run_id: UUID | str,
    expected_run_revision: int,
    target_playable_revision: int,
    target_playable_content_sha256: str,
) -> PlayRunAggregate:
    canonical_run_id = _as_uuid(run_id, field_name="run_id")
    expected = _require_positive_revision(
        expected_run_revision, field_name="expected_run_revision"
    )
    target_n = _require_positive_revision(
        target_playable_revision, field_name="target_playable_revision"
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.lock_run(conn, canonical_run_id)
        if run is None:
            raise ApplicationStateNotFoundError(f"Play Run not found: {canonical_run_id}")
        manifest = _require_coherent_manifest(run, repo.get_manifest(conn, canonical_run_id))
        same_target = (
            run.playable_revision_n == target_n
            and run.playable_content_sha256 == target_playable_content_sha256
        )
        if same_target:
            if run.run_revision == expected:
                return PlayRunAggregate(run=run, manifest=manifest)
            if (
                run.run_revision == expected + 1
                and run.rebased_from_run_revision == expected
            ):
                return PlayRunAggregate(run=run, manifest=manifest)
            raise ApplicationStateConflictError(
                "run_revision does not match the current Play Run"
            )
        if expected != run.run_revision:
            raise ApplicationStateConflictError(
                "run_revision does not match the current Play Run"
            )
        if target_n <= run.playable_revision_n:
            raise ApplicationStateConflictError(
                "target_playable_revision must be strictly newer than the current Playable revision"
            )
        admitted = admit_playable_revision(
            conn,
            run.playable_work_object_id,
            target_n,
            target_playable_content_sha256,
            require_current=False,
            require_clean=False,
        )
        if admitted.work_object.campaign_id != run.campaign_id:
            raise ApplicationStateConflictError(
                "workspace campaign_id does not match the Run campaign"
            )
        now = repo.now_utc()
        document = _derive_manifest_document(
            admitted.work_revision.markdown,
            run_id=canonical_run_id,
            playable_artifact_id=run.playable_work_object_id,
            playable_revision=admitted.work_revision.revision_n,
            playable_content_sha256=admitted.work_revision.content_sha256,
            sealed_at=now,
        )
        _admit_progress_payload(
            run.progress, document, run_id=canonical_run_id, status_code=409
        )
        updated = repo.update_run_binding(
            conn,
            run_id=canonical_run_id,
            expected_run_revision=expected,
            playable_revision_n=admitted.work_revision.revision_n,
            playable_work_revision_id=admitted.work_revision.work_revision_id,
            playable_content_sha256=admitted.work_revision.content_sha256,
            rebased_from_run_revision=run.run_revision,
            updated_at=now,
        )
        if updated is None:
            raise ApplicationStateConflictError(
                "run_revision does not match the current Play Run"
            )
        replaced = repo.replace_manifest(
            conn,
            PlayRunManifest(
                run_id=canonical_run_id,
                playable_work_object_id=run.playable_work_object_id,
                playable_revision_n=admitted.work_revision.revision_n,
                playable_work_revision_id=admitted.work_revision.work_revision_id,
                playable_content_sha256=admitted.work_revision.content_sha256,
                manifest=document,
                sealed_at=now,
            ),
        )
        return PlayRunAggregate(run=updated, manifest=replaced)
