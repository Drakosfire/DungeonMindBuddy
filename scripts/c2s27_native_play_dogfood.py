#!/usr/bin/env python3
"""Prepare the exact C2 Session 27 Runbook for native Play dogfood.

This helper registers and commits one workspace Runbook through existing
workspace-document + Markdown-writer authority. It never creates a Play Run,
seals a manifest, or mutates Runtime progress.

Default is dry-run. Mutation requires ``--apply``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.live_control_server.services.tiptap_markdown_write import (  # noqa: E402
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (  # noqa: E402
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    get_workspace_document_snapshot,
    list_workspace_documents,
)

TITLE = "C2 Session 27 — Mireward Climax"
CAMPAIGN_ID = "longmont-c2"
TARGET_SESSION = 27
TARGET_RELPATH = (
    "evals/c2_live_prep/mireward-prep/content/tiptap/c2s27-mireward-climax-runbook.md"
)
EXPECTED_ARTIFACT_SHA256 = (
    "f0c5aec9c7473d0ea6322434bc90ab3f9dd3417c5964d3f58d0e5a9eff12e9e9"
)

SetupStatus = Literal[
    "would_create_and_commit",
    "created_and_committed",
    "would_commit_existing_draft",
    "committed_existing_draft",
    "ready_existing",
]


class DogfoodSetupError(RuntimeError):
    def __init__(self, code: str, message: str, **extra: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


def canonical_artifact_sha256(markdown: str) -> str:
    normalized = markdown.replace("\r\n", "\n").replace("\r", "\n")
    content = normalized.rstrip("\n") + "\n"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_canonical_artifact(root: Path) -> str:
    path = root / TARGET_RELPATH
    if not path.is_file():
        raise DogfoodSetupError(
            "missing_artifact",
            f"exact Session 27 artifact is missing: {TARGET_RELPATH}",
        )
    raw = path.read_text(encoding="utf-8")
    sha = canonical_artifact_sha256(raw)
    if sha != EXPECTED_ARTIFACT_SHA256:
        raise DogfoodSetupError(
            "sha_mismatch",
            "artifact SHA does not match the pinned Session 27 Runbook",
            observed_sha=sha,
            expected_sha=EXPECTED_ARTIFACT_SHA256,
        )
    return raw.rstrip("\n") + "\n"


def owners_of_target(root: Path) -> list[WorkspaceDocumentRecord]:
    return [
        record
        for record in list_workspace_documents(root, status=None)
        if record.target_relpath == TARGET_RELPATH
    ]


def _require_exact_metadata(record: WorkspaceDocumentRecord) -> None:
    conflicts: dict[str, Any] = {}
    if record.kind != "runbook":
        conflicts["kind"] = record.kind
    if record.campaign_id != CAMPAIGN_ID:
        conflicts["campaign_id"] = record.campaign_id
    if record.target_session != TARGET_SESSION:
        conflicts["target_session"] = record.target_session
    if record.title != TITLE:
        conflicts["title"] = record.title
    if record.target_relpath != TARGET_RELPATH:
        conflicts["target_relpath"] = record.target_relpath
    if conflicts:
        raise DogfoodSetupError(
            "metadata_conflict",
            "existing target owner does not match exact Session 27 Runbook metadata",
            document_id=record.document_id,
            conflicts=conflicts,
        )


def _result(
    *,
    status: SetupStatus,
    record: WorkspaceDocumentRecord,
    content_sha256: str,
    created_this_run: bool,
    committed_this_run: bool,
) -> dict[str, Any]:
    return {
        "status": status,
        "document_id": record.document_id,
        "campaign_id": record.campaign_id,
        "target_session": record.target_session,
        "target_relpath": record.target_relpath,
        "revision": record.revision,
        "content_status": record.content_status,
        "content_sha256": content_sha256,
        "created_this_run": created_this_run,
        "committed_this_run": committed_this_run,
    }


def _commit_existing(root: Path, record: WorkspaceDocumentRecord, markdown: str) -> WorkspaceDocumentRecord:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    if not prepared.writer_ok or not prepared.writer_confirm_token:
        raise DogfoodSetupError(
            "writer_prepare_failed",
            "existing Markdown writer refused prepare for the Session 27 Runbook",
            document_id=record.document_id,
            warnings=prepared.warnings,
            diagnostics=prepared.diagnostics,
        )
    committed = commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=record.revision,
        ),
    )
    return committed.committed_record


def _require_ready_snapshot(root: Path, document_id: str) -> tuple[WorkspaceDocumentRecord, str]:
    snapshot = get_workspace_document_snapshot(root, document_id)
    record = snapshot.record
    if record.status != "active":
        raise DogfoodSetupError(
            "not_active",
            "Session 27 Runbook is not active after setup",
            document_id=document_id,
            status=record.status,
        )
    if record.content_status != "committed":
        raise DogfoodSetupError(
            "not_committed",
            "Session 27 Runbook is not committed after setup",
            document_id=document_id,
            content_status=record.content_status,
        )
    if record.target_session != TARGET_SESSION:
        raise DogfoodSetupError(
            "session_mismatch",
            "committed Runbook target_session is not 27",
            document_id=document_id,
            target_session=record.target_session,
        )
    if snapshot.content_sha256 != EXPECTED_ARTIFACT_SHA256:
        raise DogfoodSetupError(
            "sha_mismatch",
            "committed snapshot SHA does not match the pinned Session 27 Runbook",
            document_id=document_id,
            observed_sha=snapshot.content_sha256,
            expected_sha=EXPECTED_ARTIFACT_SHA256,
        )
    return record, snapshot.content_sha256


def setup_c2s27_runbook(*, root: Path, apply: bool) -> dict[str, Any]:
    markdown = load_canonical_artifact(root)
    owners = owners_of_target(root)
    if len(owners) > 1:
        raise DogfoodSetupError(
            "multiple_owners",
            "multiple workspace records own the Session 27 Runbook path",
            document_ids=[owner.document_id for owner in owners],
        )
    if len(owners) == 1:
        owner = owners[0]
        if owner.status == "discarded":
            raise DogfoodSetupError(
                "discarded_owner",
                "Session 27 Runbook path is owned by a discarded record",
                document_id=owner.document_id,
            )
        _require_exact_metadata(owner)
        if owner.content_status == "committed":
            record, sha = _require_ready_snapshot(root, owner.document_id)
            return _result(
                status="ready_existing",
                record=record,
                content_sha256=sha,
                created_this_run=False,
                committed_this_run=False,
            )
        if not apply:
            return _result(
                status="would_commit_existing_draft",
                record=owner,
                content_sha256=EXPECTED_ARTIFACT_SHA256,
                created_this_run=False,
                committed_this_run=False,
            )
        committed = _commit_existing(root, owner, markdown)
        record, sha = _require_ready_snapshot(root, committed.document_id)
        return _result(
            status="committed_existing_draft",
            record=record,
            content_sha256=sha,
            created_this_run=False,
            committed_this_run=True,
        )

    if not apply:
        return {
            "status": "would_create_and_commit",
            "document_id": None,
            "campaign_id": CAMPAIGN_ID,
            "target_session": TARGET_SESSION,
            "target_relpath": TARGET_RELPATH,
            "revision": None,
            "content_status": None,
            "content_sha256": EXPECTED_ARTIFACT_SHA256,
            "created_this_run": False,
            "committed_this_run": False,
        }

    created = create_workspace_document(
        root,
        title=TITLE,
        campaign_id=CAMPAIGN_ID,
        kind="runbook",
        target_session=TARGET_SESSION,
        target_relpath=TARGET_RELPATH,
    )
    committed = _commit_existing(root, created, markdown)
    record, sha = _require_ready_snapshot(root, committed.document_id)
    return _result(
        status="created_and_committed",
        record=record,
        content_sha256=sha,
        created_this_run=True,
        committed_this_run=True,
    )


def _error_payload(exc: BaseException) -> dict[str, Any]:
    if isinstance(exc, DogfoodSetupError):
        payload = {
            "status": "error",
            "error_code": exc.code,
            "error": exc.message,
            **exc.extra,
        }
        return payload
    if isinstance(exc, (WorkspaceDocumentRegistryError, TiptapMarkdownWriteError)):
        return {
            "status": "error",
            "error_code": "writer_or_registry_error",
            "error": str(exc),
        }
    return {
        "status": "error",
        "error_code": "unexpected",
        "error": str(exc),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create/commit the exact Session 27 workspace Runbook. Default is dry-run.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root containing the Session 27 artifact and workspace registry.",
    )
    args = parser.parse_args(argv)
    try:
        result = setup_c2s27_runbook(root=args.root.resolve(), apply=args.apply)
    except Exception as exc:  # noqa: BLE001 — CLI must emit one JSON object even on failure
        print(json.dumps(_error_payload(exc), indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
