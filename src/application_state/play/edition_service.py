"""Durable Run-local editions. All operations serialize through the Run lock."""

from datetime import UTC, datetime
import hashlib
import json
from uuid import uuid4

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.content.playable_admission import (
    resolve_pinned_playable_revision,
)
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.play import edition_repository as editions
from application_state.play import repository as runs
from application_state.play.edition_types import (
    ContentCommit,
    ContentReceipt,
    EditionOrigin,
    RunContent,
)
from application_state.play.service import (
    _as_uuid,
    _require_world_id,
    _resolve_world_run_owner,
    require_persisted_aggregate_integrity,
)
from application_state.unit_of_work import unit_of_work


def sha(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


def request_digest(world_id, run_id, command_id, request: ContentCommit) -> str:
    payload = {
        "world_id": world_id,
        "run_id": str(run_id),
        "command_id": str(command_id),
        **request.model_dump(mode="json"),
    }
    return sha(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    )


def _origin(run) -> EditionOrigin:
    return EditionOrigin(
        playable_artifact_id=str(run.playable_work_object_id),
        playable_revision=run.playable_revision_n,
        playable_work_revision_id=str(run.playable_work_revision_id),
        playable_content_sha256=run.playable_content_sha256,
    )


def _structure(origin, candidate, manifest, *, persisted=False):
    from apps.live_control_server.services.play_run_edition_structure import (
        EditionStructureError,
        validate_edition_structure,
    )

    try:
        return validate_edition_structure(origin, candidate, manifest)
    except EditionStructureError as exc:
        error = (
            ApplicationStateIntegrityError
            if persisted
            else ApplicationStateValidationError
        )
        raise error(str(exc)) from exc


def _locked_state(conn, run_id, world_id):
    run = runs.lock_run(conn, run_id)
    if run is None:
        raise ApplicationStateNotFoundError("Play Run not found")
    _resolve_world_run_owner(conn, run, world_id=world_id)
    manifest = require_persisted_aggregate_integrity(
        run, runs.get_manifest(conn, run_id)
    )
    if manifest.manifest.get("schema_version") != "dmb_play_run_reference_manifest_v2":
        raise ApplicationStateValidationError(
            "Run content editions support World grammar v2 only"
        )
    pinned = resolve_pinned_playable_revision(
        conn,
        run.playable_work_object_id,
        run.playable_revision_n,
        run.playable_work_revision_id,
        run.playable_content_sha256,
        expected_world_id=world_id,
    )
    structure = _structure(
        pinned.markdown, pinned.markdown, manifest.manifest, persisted=True
    )
    edition = editions.get_edition(conn, run_id, lock=True)
    history = editions.revisions(conn, run_id)
    if edition is None:
        if history:
            raise ApplicationStateIntegrityError("Run edition history has no head")
        return run, manifest, pinned, structure, None, []
    if (
        edition["world_id"] != world_id
        or edition["origin_artifact_id"] != run.playable_work_object_id
        or edition["origin_revision_n"] != run.playable_revision_n
        or edition["origin_work_revision_id"] != run.playable_work_revision_id
        or edition["origin_content_sha256"] != run.playable_content_sha256
        or edition["grammar_version"] != 2
        or edition["structure_sha256"] != structure
        or edition["head_revision"] != len(history)
        or not history
    ):
        raise ApplicationStateIntegrityError("Run edition origin or head is corrupt")
    previous_sha = pinned.content_sha256
    for n, row in enumerate(history, 1):
        if (
            row["revision_n"] != n
            or row["previous_revision"] != (n - 1 if n > 1 else None)
            or row["expected_revision"] != n - 1
            or row["expected_sha256"] != previous_sha
            or row["content_sha256"] != sha(row["markdown"])
            or row["content_sha256"] == previous_sha
            or row["observed_run_revision"] > run.run_revision
        ):
            raise ApplicationStateIntegrityError(
                "Run edition chain or content hash is corrupt"
            )
        stored_request = ContentCommit(
            schema_version="dmb_world_play_run_content_commit_v1",
            expected_origin=_origin(run),
            expected_edition_revision=n - 1,
            expected_content_sha256=previous_sha,
            markdown=row["markdown"],
        )
        if row["request_sha256"] != request_digest(
            world_id, run_id, row["command_id"], stored_request
        ):
            raise ApplicationStateIntegrityError(
                "Run edition command digest is corrupt"
            )
        _structure(pinned.markdown, row["markdown"], manifest.manifest, persisted=True)
        previous_sha = row["content_sha256"]
    if edition["created_at"] != history[0]["committed_at"]:
        raise ApplicationStateIntegrityError("Run edition creation time is corrupt")
    return run, manifest, pinned, structure, edition, history


def _content(state, world_id, revision_n=None):
    run, _manifest, pin, structure, edition, history = state
    n = (
        (edition["head_revision"] if edition else 0)
        if revision_n is None
        else revision_n
    )
    if n < 0 or n > len(history):
        raise ApplicationStateNotFoundError("Run content revision not found")
    row = history[n - 1] if n else None
    return RunContent(
        world_id=world_id,
        run_id=str(run.run_id),
        origin=_origin(run),
        source="edition" if row else "pinned",
        edition_revision=n,
        edition_revision_id=str(row["revision_id"]) if row else None,
        markdown=row["markdown"] if row else pin.markdown,
        content_sha256=row["content_sha256"] if row else pin.content_sha256,
        committed_at=row["committed_at"] if row else pin.created_at,
        observed_run_revision=row["observed_run_revision"] if row else run.run_revision,
        structure_sha256=structure,
    )


def _receipt(run, world_id, row):
    return ContentReceipt(
        world_id=world_id,
        run_id=str(run.run_id),
        command_id=str(row["command_id"]),
        request_sha256=row["request_sha256"],
        origin=_origin(run),
        expected_edition_revision=row["expected_revision"],
        expected_content_sha256=row["expected_sha256"],
        accepted_edition_revision=row["revision_n"],
        accepted_edition_revision_id=str(row["revision_id"]),
        accepted_content_sha256=row["content_sha256"],
        committed_at=row["committed_at"],
        observed_run_revision=row["observed_run_revision"],
    )


def _coordinates(run_id, world_id):
    return _as_uuid(run_id, field_name="run_id"), _require_world_id(world_id)


def read_content(
    *, run_id: str, world_id: str, revision_n: int | None = None
) -> RunContent:
    run_id, world_id = _coordinates(run_id, world_id)
    if revision_n is not None and (type(revision_n) is not int or revision_n < 0):
        raise ApplicationStateValidationError(
            "revision_n must be a nonnegative integer"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return _content(_locked_state(conn, run_id, world_id), world_id, revision_n)


def read_command(*, run_id: str, world_id: str, command_id: str) -> ContentReceipt:
    run_id, world_id = _coordinates(run_id, world_id)
    command_id = _as_uuid(command_id, field_name="command_id")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        state = _locked_state(conn, run_id, world_id)
        row = next((row for row in state[-1] if row["command_id"] == command_id), None)
        if row is None:
            raise ApplicationStateNotFoundError(
                "Run content command not found at this read"
            )
        return _receipt(state[0], world_id, row)


def commit_content(
    *, run_id: str, world_id: str, command_id: str, request: ContentCommit
) -> ContentReceipt:
    run_id, world_id = _coordinates(run_id, world_id)
    command_id = _as_uuid(command_id, field_name="command_id")
    # Also enforce strict DTO admission for non-HTTP callers.
    request = ContentCommit.model_validate(request.model_dump())
    digest = request_digest(world_id, run_id, command_id, request)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        state = _locked_state(conn, run_id, world_id)
        run, manifest, pin, structure, edition, history = state
        replay = next((row for row in history if row["command_id"] == command_id), None)
        if replay is not None:
            if replay["request_sha256"] != digest:
                raise ApplicationStateConflictError(
                    "command_id already accepted a different request"
                )
            return _receipt(run, world_id, replay)
        current = _content(state, world_id)
        if request.expected_origin != current.origin:
            raise ApplicationStateConflictError(
                "expected origin does not match the Run pin"
            )
        if (
            request.expected_edition_revision != current.edition_revision
            or request.expected_content_sha256 != current.content_sha256
        ):
            raise ApplicationStateConflictError("Run content edition base is stale")
        content_hash = sha(request.markdown)
        if content_hash == current.content_sha256:
            raise ApplicationStateValidationError("Run content edit has no changes")
        _structure(pin.markdown, request.markdown, manifest.manifest)
        n = current.edition_revision + 1
        stamp = datetime.now(UTC)
        if edition is None:
            editions.insert_edition(
                conn,
                dict(
                    run_id=run_id,
                    world_id=world_id,
                    origin_artifact_id=run.playable_work_object_id,
                    origin_revision_n=run.playable_revision_n,
                    origin_work_revision_id=run.playable_work_revision_id,
                    origin_content_sha256=run.playable_content_sha256,
                    grammar_version=2,
                    structure_sha256=structure,
                    head_revision=n,
                    created_at=stamp,
                ),
            )
        row = dict(
            run_id=run_id,
            revision_n=n,
            revision_id=uuid4(),
            previous_revision=n - 1 if n > 1 else None,
            markdown=request.markdown,
            content_sha256=content_hash,
            committed_at=stamp,
            command_id=command_id,
            request_sha256=digest,
            expected_revision=current.edition_revision,
            expected_sha256=current.content_sha256,
            observed_run_revision=run.run_revision,
        )
        editions.insert_revision(conn, row)
        editions.advance_head(conn, run_id, n)
        return _receipt(run, world_id, row)
