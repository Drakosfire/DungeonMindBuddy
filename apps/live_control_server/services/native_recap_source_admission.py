"""Ordinary fresh recap source intent, single-host executor and read-only status."""

from __future__ import annotations
import logging
import os
from datetime import UTC, datetime
from copy import deepcopy
from application_state.ingest import service as ingest
from application_state.source import service as sources
from graph_memory.ingestion.native_recap_source import (
    Record,
    Delivery,
    Opening,
    Resume,
    Status,
    KEY,
    PROFILE,
    SourceSelection,
)
from apps.live_control_server import config
from apps.live_control_server.services.graph_run_registry import create_extraction_run
from apps.live_control_server.services.source_artifact_registry import (
    get_source_artifact,
)
from apps.live_control_server.services.reviewed_corpus_publication_store import (
    PublicationProgressStore,
    ProgressConflict,
)
from apps.live_control_server.integrations.dungeonmind.native_recap_source_admission import (
    NativeRecapAuthority,
    NativeRecapError,
)

log = logging.getLogger(__name__)


def _now():
    return datetime.now(UTC)


def public_run(run):
    """Presentation only: never redact internal authority or persistence objects."""
    value = deepcopy(run.model_dump(mode="json") if hasattr(run, "model_dump") else run)
    if isinstance(value.get("lineage"), dict):
        value["lineage"].pop(KEY, None)
    return value


def _execution_mode():
    mode = os.environ.get("DMB_NATIVE_RECAP_EXECUTION_SCOPE", "")
    from apps.live_control_server.services import hosted_auth

    local = (
        hosted_auth.deployment_environment() in hosted_auth.LOCAL_ENVIRONMENTS
        and hosted_auth.auth_mode() == hosted_auth.LOCAL_MODE
    )
    if mode != "single_host_shared_root" and not (not mode and local):
        raise NativeRecapError(
            "native_recap_execution_topology_unsupported", status_code=503
        )


def _load(run_id, world, campaign, session):
    run = ingest.get_extraction_run(str(run_id))
    try:
        record = Record.model_validate(run.lineage.get(KEY))
        if (
            run.run_id != record.run_id
            or run.profile_id != PROFILE
            or run.components
            or record.managed_world_id != world
            or record.campaign_id != campaign
            or record.session_id != f"session-{session}"
            or run.source_artifact_id != record.app_source_artifact_id
            or run.campaign_id != campaign
            or run.session_id != record.session_id
        ):
            raise ValueError("Foreign source intent")
        source = _selected_source(
            SourceSelection(
                source_artifact_id=record.app_source_artifact_id,
                source_revision_id=record.app_source_revision_id,
                content_sha256=record.app_body_sha256,
            ),
            record,
            session,
        )
        if source.created_at != record.created_at:
            raise ValueError("Source snapshot timestamp changed")
        for command in record.commands:
            command.resolve(source.markdown)
    except ValueError as exc:
        raise NativeRecapError("native_recap_intent_invalid") from exc
    return run, record, source


def _safe_code(exc):
    if isinstance(exc, NativeRecapError):
        return exc.code
    return (
        "native_recap_integrity_error"
        if isinstance(exc, ValueError)
        else "native_recap_authority_unavailable"
    )


def _status(run, record, source, authority, *, busy=False):
    receipt = record.receipt
    opening = Opening(state="not_checked")
    failure = None
    try:
        authority.check_binding(record)
        observed = authority.receipt(record)
        if receipt is not None and observed != receipt:
            raise NativeRecapError("native_recap_receipt_changed")
        candidate = observed or receipt
        if candidate is not None:
            if record.command is None:
                raise NativeRecapError("native_recap_saved_command_missing")
            checked = Record.model_validate(
                {
                    **record.model_dump(mode="json"),
                    "receipt": candidate.model_dump(mode="json"),
                }
            )
            record, receipt = checked, candidate
            opening = authority.verify(record, source.markdown, receipt)
            if opening.state != "verified":
                failure = "native_recap_opening_unavailable"
    except Exception as exc:
        log.exception("Native recap read-only status failed run=%s", run.run_id)
        failure = _safe_code(exc)
        opening = Opening(
            state="integrity_error"
            if "mismatch" in failure
            or "invalid" in failure
            or "integrity" in failure
            or "changed" in failure
            else "unavailable"
        )
    command = record.command
    if failure:
        state = "unavailable"
    elif receipt and opening.state == "verified":
        state = "admitted"
    else:
        state = {
            "entered": "dispatching",
            "unknown": "unknown",
            "stale": "conflict",
            "reserved": "reserved",
            "committed": "unavailable",
        }[record.state]
    if failure is None:
        failure = (
            "native_recap_operation_busy"
            if busy
            else (
                command.deliveries[-1].failure_code
                if command and command.deliveries
                else record.preflight_failures[-1]
                if record.preflight_failures
                else None
            )
        )
    binding = receipt.bindings[0] if receipt and len(receipt.bindings) == 1 else None
    values = {
        k: getattr(record, k)
        for k in (
            "managed_world_id",
            "native_world_id",
            "binding_version",
            "campaign_id",
            "session_id",
            "app_source_artifact_id",
            "app_source_revision_id",
            "grouping_basis",
            "app_body_sha256",
        )
    }
    return Status(
        **values,
        state=state,
        run_id=run.run_id,
        run_revision=run.revision,
        admission_id=record.admission_id,
        origin={
            "namespace": "dungeonbuddy.app-recap-source.v1",
            "object_id": record.app_source_artifact_id,
            "revision_id": str(record.app_source_revision_id),
        },
        domain_ref=command.domain_ref if command else None,
        profile_ref=command.profile_ref if command else None,
        command_sha256=command.sha256 if command else None,
        expected_parent_revision_id=command.request["expected_parent_revision_id"]
        if command
        else None,
        native_receipt=receipt,
        published_revision_id=receipt.published_revision_id if receipt else None,
        source_artifact_id=receipt.source_artifact_id if receipt else None,
        source_revision_id=receipt.source_revision_id if receipt else None,
        evidence_ref_id=binding.evidence_ref_id if binding else None,
        opening=opening,
        failure_code=failure,
        admission_committed=receipt is not None,
        status_request={
            "method": "POST",
            "path": "/api/live/recap-ingest",
            "body": {
                "operation": "inspect_status",
                "native_recap_run_id": run.run_id,
                "managed_world_id": record.managed_world_id,
                "campaign_id": record.campaign_id,
                "session": int(record.session_id.removeprefix("session-")),
            },
        },
    )


def inspect(root, run_id, world, campaign, session):
    run, record, source = _load(run_id, world, campaign, session)
    return _status(
        run,
        record,
        source,
        NativeRecapAuthority(config.managed_world_data_root(root).resolve()),
    )


def _cas(run, record):
    return ingest.update_native_recap_source(
        run.run_id,
        expected_revision=run.revision,
        record=record.model_dump(mode="json"),
    )


def _settle(run, record, receipt):
    value = record.model_dump(mode="json")
    value["receipt"] = receipt.model_dump(mode="json")
    if (
        record.command
        and record.command.deliveries
        and record.command.deliveries[-1].state == "entered"
    ):
        value["commands"][-1]["deliveries"][-1].update(
            state="committed", failure_code=None
        )
    updated = Record.model_validate(value)
    return _cas(run, updated), updated


def _execute(root, run, record, source, actor, authority_basis, resume, authority):
    # Caller holds the same origin mutex for the complete execution/settlement interval.
    if resume is not None and (
        str(resume.run_id) != run.run_id
        or resume.expected_run_revision != run.revision
        or resume.command_sha256 != (record.command.sha256 if record.command else None)
    ):
        raise NativeRecapError("native_recap_resume_changed")
    authority.check_binding(record)
    receipt = authority.receipt(record)
    if record.receipt or receipt:
        if record.command is None:
            raise NativeRecapError("native_recap_saved_command_missing")
        if record.receipt is not None and receipt != record.receipt:
            raise NativeRecapError("native_recap_receipt_changed")
        if resume is not None and record.receipt is None:
            run, record = _settle(run, record, receipt)
        return _status(run, record, source, authority)
    if resume is None and (record.commands or record.preflight_failures):
        return _status(run, record, source, authority)
    if record.command is None or record.state == "stale":
        try:
            command = authority.prepare(record, source.markdown)
        except Exception as exc:
            value = Record.model_validate(
                {
                    **record.model_dump(mode="json"),
                    "preflight_failures": [*record.preflight_failures, _safe_code(exc)],
                }
            )
            run = _cas(run, value)
            return _status(run, value, source, authority)
        record = Record.model_validate(
            {
                **record.model_dump(mode="json"),
                "commands": [
                    *[c.model_dump(mode="json") for c in record.commands],
                    command.model_dump(mode="json"),
                ],
            }
        )
        run = _cas(run, record)
    # Each explicit POST is one entered delivery of the frozen command, not an automatic loop.
    value = record.model_dump(mode="json")
    value["commands"][-1]["deliveries"].append(
        Delivery(
            actor=actor, authority_basis=authority_basis, entered_at=_now()
        ).model_dump(mode="json")
    )
    record = Record.model_validate(value)
    run = _cas(run, record)
    try:
        receipt = authority.dispatch(record, source.markdown)
    except Exception as exc:
        # Exact Core typed stale-parent rejection is pre-write; every other failure stays unknown.
        from dungeonmind.application.vnext.errors import (
            KnowledgeStaleParentRevisionError,
        )

        value = record.model_dump(mode="json")
        value["commands"][-1]["deliveries"][-1].update(
            state="stale"
            if isinstance(exc, KnowledgeStaleParentRevisionError)
            else "unknown",
            failure_code="native_recap_prewrite_stale"
            if isinstance(exc, KnowledgeStaleParentRevisionError)
            else "native_recap_dispatch_unknown",
        )
        record = Record.model_validate(value)
        run = _cas(run, record)
        log.exception("Native recap delivery failed run=%s", run.run_id)
        return _status(run, record, source, authority)
    # Preserve the effect receipt before any opening can fail. CAS loss is recoverable by exact status.
    run, record = _settle(run, record, receipt)
    return _status(run, record, source, authority)


def resume_admission(
    root, *, resume: Resume, world, campaign, session, actor, authority_basis
):
    """Recover the exact saved intent; current corpus files cannot retarget it."""
    _execution_mode()
    managed_root = config.managed_world_data_root(root).resolve()
    root = config.artifact_data_root(root)
    run, record, source = _load(resume.run_id, world, campaign, session)
    authority = NativeRecapAuthority(managed_root)
    lock = PublicationProgressStore(root / "out/native_recap_source_locks")
    try:
        with lock.exclusive(record.admission_id):
            # Re-read under the mutex, then let the exact revision/hash gate and
            # winning CAS govern all reconciliation and dispatch.
            run, record, source = _load(resume.run_id, world, campaign, session)
            return _execute(
                root, run, record, source, actor, authority_basis, resume, authority
            )
    except ProgressConflict as exc:
        if str(exc) != "operation_busy":
            raise NativeRecapError(
                "native_recap_execution_unavailable", status_code=503
            ) from exc
        run, record, source = _load(resume.run_id, world, campaign, session)
        return _status(run, record, source, authority, busy=True)


def _selected_source(selection: SourceSelection, context, session):
    # APP owns the descriptor and immutable bytes; URI and body frontmatter are
    # never alternative selectors or scope authorities.
    descriptor = get_source_artifact(
        config.artifact_data_root(), selection.source_artifact_id
    )
    source = sources.get_source_markdown(
        source_artifact_id=selection.source_artifact_id,
        content_sha256=selection.content_sha256,
        source_revision_id=selection.source_revision_id,
    )
    if source is None:
        raise NativeRecapError("native_recap_source_snapshot_missing")
    if (
        descriptor.schema_version != "dmb_source_artifact_v1"
        or descriptor.source_domain != "recap"
        or descriptor.artifact_kind != "recap_markdown"
        or descriptor.status != "active"
        or source.source_domain != "recap"
        or source.media_type != "text/markdown"
        or source.encoding != "utf-8"
        or descriptor.source_artifact_id != source.source_artifact_id
        or descriptor.content_sha256 != source.content_sha256
        or source.content_sha256 != selection.content_sha256
        or source.source_revision_id != selection.source_revision_id
    ):
        raise NativeRecapError("native_recap_source_descriptor_mismatch")
    if (
        descriptor.world_id != context.native_world_id
        or source.world_id != context.native_world_id
    ):
        raise NativeRecapError("native_recap_source_world_mismatch")
    if (
        descriptor.campaign_id != context.campaign_id
        or source.campaign_id != context.campaign_id
        or descriptor.session_id != f"session-{session}"
        or source.session_id != f"session-{session}"
    ):
        raise NativeRecapError("native_recap_source_grouping_mismatch")
    return source


def admit(
    root, *, context, selection: SourceSelection, session: int, actor, authority_basis
):
    _execution_mode()
    managed_root = config.managed_world_data_root(root).resolve()
    root = config.artifact_data_root(root)
    source = _selected_source(selection, context, session)
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_source_identity,
    )

    current = resolve_managed_source_identity(
        context.managed_world_id, root=managed_root
    )
    if (current.native_world_id, current.binding_version) != (
        context.native_world_id,
        context.binding_version,
    ):
        raise NativeRecapError("native_recap_binding_changed")
    candidate = Record(
        managed_world_id=context.managed_world_id,
        native_world_id=context.native_world_id,
        binding_version=context.binding_version,
        campaign_id=context.campaign_id,
        session_id=source.session_id,
        app_source_artifact_id=source.source_artifact_id,
        app_source_revision_id=source.source_revision_id,
        app_body_sha256=source.content_sha256,
        created_by=actor,
        created_authority_basis=authority_basis,
        created_at=source.created_at,
    )
    authority = NativeRecapAuthority(managed_root)
    lock = PublicationProgressStore(root / "out/native_recap_source_locks")
    try:
        with lock.exclusive(candidate.admission_id):
            existing = ingest.get_extraction_run_optional(candidate.run_id)
            if existing is None:
                run = create_extraction_run(
                    root,
                    run_id=candidate.run_id,
                    source_artifact_id=source.source_artifact_id,
                    source_domain="recap",
                    campaign_id=source.campaign_id,
                    session_id=source.session_id,
                    profile_id=PROFILE,
                    lineage={
                        "native_world_id": context.native_world_id,
                        "campaign_id": context.campaign_id,
                        KEY: candidate.model_dump(mode="json"),
                    },
                )
                record = candidate
            else:
                run, record, source = _load(
                    existing.run_id,
                    context.managed_world_id,
                    context.campaign_id,
                    session,
                )
                if record.binding_version != candidate.binding_version:
                    raise NativeRecapError("native_recap_source_input_changed")
                return _status(run, record, source, authority)
            return _execute(
                root, run, record, source, actor, authority_basis, None, authority
            )
    except ProgressConflict as exc:
        if str(exc) != "operation_busy":
            raise NativeRecapError(
                "native_recap_execution_unavailable", status_code=503
            ) from exc
        if ingest.get_extraction_run_optional(candidate.run_id) is None:
            raise NativeRecapError("native_recap_operation_busy")
        run, record, source = _load(
            candidate.run_id,
            context.managed_world_id,
            context.campaign_id,
            session,
        )
        return _status(run, record, source, authority, busy=True)
