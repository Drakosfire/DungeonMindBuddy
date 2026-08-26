"""Explicit coherent legacy Play Runtime adoption. Not ordinary Runtime authority."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content.playable_admission import admit_playable_revision
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
)
from application_state.play import repository as repo
from application_state.play.types import PlayRun, PlayRunManifest, PlayRuntimeImportReport
from application_state.unit_of_work import unit_of_work


class FrozenPlayRuntime(BaseModel):
    run_id: UUID
    campaign_id: str
    playable_artifact_id: UUID
    playable_revision: int
    playable_content_sha256: str
    run_revision: int
    progress: dict
    rebased_from_run_revision: int | None = None
    created_at: datetime
    updated_at: datetime
    manifest: dict
    sealed_at: datetime


def _parse_iso_z(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def freeze_play_runtime_pair(*, run_payload: dict, manifest_payload: dict) -> FrozenPlayRuntime:
    from apps.live_control_server.services.play_run_registry import PlayRunRecord
    from apps.live_control_server.services.play_run_reference_manifest import (
        parse_manifest_payload,
    )

    record = PlayRunRecord.model_validate(run_payload)
    manifest = parse_manifest_payload(manifest_payload, run_id=record.run_id)
    if (
        manifest.playable_artifact_id != record.playable_artifact_id
        or manifest.playable_revision != record.playable_revision
        or manifest.playable_content_sha256 != record.playable_content_sha256
    ):
        raise ApplicationStateIntegrityError(
            "captured Run and manifest do not share the same Playable binding"
        )
    return FrozenPlayRuntime(
        run_id=UUID(record.run_id),
        campaign_id=record.campaign_id,
        playable_artifact_id=UUID(record.playable_artifact_id),
        playable_revision=record.playable_revision,
        playable_content_sha256=record.playable_content_sha256,
        run_revision=record.run_revision,
        progress=record.progress.model_dump(mode="json"),
        rebased_from_run_revision=record.rebased_from_run_revision,
        created_at=_parse_iso_z(record.created_at),
        updated_at=_parse_iso_z(record.updated_at),
        manifest=manifest.model_dump(mode="json", exclude_none=True),
        sealed_at=_parse_iso_z(manifest.sealed_at),
    )


def capture_legacy_play_runtime(root: Path) -> tuple[list[FrozenPlayRuntime], int]:
    """Recover pending intents, then freeze each Run JSON + matching manifest."""
    from apps.live_control_server.services.play_run_rebase import recover_legacy_rebase_intents
    from apps.live_control_server.services.play_run_registry import play_runs_dir
    from apps.live_control_server.services.play_run_reference_manifest import (
        play_run_reference_manifest_path,
    )
    from apps.live_control_server.services.registry_file_lock import registry_mutation_lock
    from src.live_play.live_store import load_json

    recovered = recover_legacy_rebase_intents(root)
    frozen: list[FrozenPlayRuntime] = []
    directory = play_runs_dir(root)
    if not directory.is_dir():
        return frozen, recovered
    for path in sorted(directory.glob("*.json")):
        run_id = path.stem
        manifest_path = play_run_reference_manifest_path(root, run_id)
        with registry_mutation_lock(path):
            with registry_mutation_lock(manifest_path):
                if not manifest_path.is_file():
                    raise ApplicationStateIntegrityError(
                        f"legacy Play Run is missing its sealed manifest: {run_id}"
                    )
                frozen.append(
                    freeze_play_runtime_pair(
                        run_payload=load_json(path),
                        manifest_payload=load_json(manifest_path),
                    )
                )
    return frozen, recovered


def import_play_runtime_from_snapshots(
    snapshots: list[FrozenPlayRuntime],
) -> PlayRuntimeImportReport:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    report = PlayRuntimeImportReport()
    for snapshot in snapshots:
        with unit_of_work(dsn) as conn:
            admitted = admit_playable_revision(
                conn,
                snapshot.playable_artifact_id,
                snapshot.playable_revision,
                snapshot.playable_content_sha256,
                require_current=False,
                require_clean=False,
            )
            existing = repo.get_run(conn, snapshot.run_id)
            if existing is not None:
                manifest = repo.get_manifest(conn, snapshot.run_id)
                if manifest is None:
                    raise ApplicationStateIntegrityError(
                        "READY Play Run is missing its required sealed manifest"
                    )
                if (
                    existing.playable_work_object_id != snapshot.playable_artifact_id
                    or existing.playable_revision_n != snapshot.playable_revision
                    or existing.playable_content_sha256 != snapshot.playable_content_sha256
                    or existing.run_revision != snapshot.run_revision
                    or existing.progress != snapshot.progress
                    or existing.rebased_from_run_revision != snapshot.rebased_from_run_revision
                    or manifest.manifest != snapshot.manifest
                ):
                    raise ApplicationStateConflictError(
                        "legacy Play Runtime import conflicts with an existing Run"
                    )
                report.noop += 1
                continue
            repo.insert_run(
                conn,
                PlayRun(
                    run_id=snapshot.run_id,
                    campaign_id=snapshot.campaign_id,
                    playable_work_object_id=snapshot.playable_artifact_id,
                    playable_revision_n=snapshot.playable_revision,
                    playable_work_revision_id=admitted.work_revision.work_revision_id,
                    playable_content_sha256=snapshot.playable_content_sha256,
                    run_revision=snapshot.run_revision,
                    progress=snapshot.progress,
                    rebased_from_run_revision=snapshot.rebased_from_run_revision,
                    created_at=snapshot.created_at,
                    updated_at=snapshot.updated_at,
                ),
            )
            repo.insert_manifest(
                conn,
                PlayRunManifest(
                    run_id=snapshot.run_id,
                    playable_work_object_id=snapshot.playable_artifact_id,
                    playable_revision_n=snapshot.playable_revision,
                    playable_work_revision_id=admitted.work_revision.work_revision_id,
                    playable_content_sha256=snapshot.playable_content_sha256,
                    manifest=snapshot.manifest,
                    sealed_at=snapshot.sealed_at,
                ),
            )
            report.imported += 1
            report.run_ids.append(str(snapshot.run_id))
    return report


def import_play_runtime_from_legacy_files(root: Path) -> PlayRuntimeImportReport:
    snapshots, recovered = capture_legacy_play_runtime(root)
    report = import_play_runtime_from_snapshots(snapshots)
    report.recovered_intents = recovered
    return report
