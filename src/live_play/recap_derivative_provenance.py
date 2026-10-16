"""Lineage and reversible replacement helpers for recap-derived artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.agent.corpus_writer import is_writable_corpus_path

SCHEMA = "dmb_recap_derivative_provenance_v1"


def record_archived_artifacts(
    report: dict[str, Any], artifacts: list[dict[str, str]]
) -> None:
    """Append each archived stage artifact once to a cumulative ingest report."""
    if not artifacts:
        return
    existing = report.setdefault("archived_artifacts", [])
    if not isinstance(existing, list):
        existing = []
        report["archived_artifacts"] = existing
    known = {
        (str(item.get("from")), str(item.get("to")))
        for item in existing
        if isinstance(item, dict)
    }
    for artifact in artifacts:
        identity = (str(artifact.get("from")), str(artifact.get("to")))
        if identity not in known:
            existing.append(artifact)
            known.add(identity)


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def provenance_path(output_path: Path) -> Path:
    return output_path.with_name(f"{output_path.name}.provenance.json")


def read_provenance_state(
    *,
    output_path: Path,
    corpus_root: Path,
    stage: str,
    campaign_number: int,
    session: int,
    input_digests: dict[str, str],
) -> tuple[str, dict[str, Any] | None]:
    """Return current, edited_current_inputs, stale, unknown, or corrupt."""
    sidecar = provenance_path(output_path)
    if not output_path.is_file():
        return ("corrupt", None) if sidecar.exists() else ("missing", None)
    if not sidecar.is_file():
        return "unknown", None
    try:
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return "corrupt", None
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        return "corrupt", None
    try:
        relpath = output_path.resolve().relative_to(corpus_root.resolve()).as_posix()
    except ValueError:
        return "corrupt", payload
    if (
        payload.get("stage") != stage
        or payload.get("campaign_number") != campaign_number
        or payload.get("session") != session
        or payload.get("output_path") != relpath
    ):
        return "corrupt", payload
    if payload.get("input_digests") != input_digests:
        return "stale", payload
    if payload.get("output_sha256") != sha256_file(output_path):
        return "edited_current_inputs", payload
    return "current", payload


def provenance_payload(
    *,
    output_path: Path,
    corpus_root: Path,
    stage: str,
    campaign_number: int,
    session: int,
    input_digests: dict[str, str],
    output_bytes: bytes,
) -> dict[str, Any]:
    relpath = output_path.resolve().relative_to(corpus_root.resolve()).as_posix()
    return {
        "schema": SCHEMA,
        "stage": stage,
        "campaign_number": campaign_number,
        "session": session,
        "output_path": relpath,
        "input_digests": dict(sorted(input_digests.items())),
        "output_sha256": sha256_bytes(output_bytes),
    }


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_provenance(path: Path, payload: dict[str, Any]) -> None:
    content = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    atomic_write_bytes(path, content)


def store_provenanced_artifact(
    *,
    output_path: Path,
    corpus_root: Path,
    stage: str,
    campaign_number: int,
    session: int,
    input_digests: dict[str, str],
    content: bytes,
    force: bool,
    allow_edited_current_inputs: bool = False,
) -> tuple[str, list[dict[str, str]]]:
    """Create/reuse/refresh a derived file without silently replacing it."""
    state, _payload = read_provenance_state(
        output_path=output_path,
        corpus_root=corpus_root,
        stage=stage,
        campaign_number=campaign_number,
        session=session,
        input_digests=input_digests,
    )
    if state == "current" and not force:
        return "reused", []
    if state == "edited_current_inputs" and allow_edited_current_inputs and not force:
        return state, []
    if state != "missing" and not force:
        return state, []

    sidecar_path = provenance_path(output_path)
    for path in (output_path, sidecar_path):
        relpath = path.resolve().relative_to(corpus_root.resolve()).as_posix()
        allowed, reason = is_writable_corpus_path(relpath, "create")
        if not allowed:
            raise ValueError(f"provenance artifact path is not writable: {relpath}: {reason}")
    archived = archive_existing(paths=[output_path, sidecar_path], corpus_root=corpus_root) if force else []
    payload = provenance_payload(
        output_path=output_path,
        corpus_root=corpus_root,
        stage=stage,
        campaign_number=campaign_number,
        session=session,
        input_digests=input_digests,
        output_bytes=content,
    )
    atomic_write_bytes(output_path, content)
    write_provenance(sidecar_path, payload)
    return ("refreshed" if archived else "created"), archived


def archive_existing(
    *,
    paths: list[Path],
    corpus_root: Path,
) -> list[dict[str, str]]:
    """Move existing artifacts into collision-safe sibling _archive folders."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archived: list[dict[str, str]] = []
    for path in paths:
        if not path.exists():
            continue
        resolved = path.resolve()
        try:
            rel = resolved.relative_to(corpus_root.resolve())
        except ValueError as exc:
            raise ValueError(f"refusing to archive path outside corpus: {path}") from exc
        archive_dir = path.parent / "_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        base = f"{path.name}.{stamp}.archived"
        target = archive_dir / base
        suffix = 1
        while target.exists():
            target = archive_dir / f"{base}.{suffix}"
            suffix += 1
        shutil.move(str(path), str(target))
        archived.append(
            {
                "from": rel.as_posix(),
                "to": target.resolve().relative_to(corpus_root.resolve()).as_posix(),
            }
        )
    return archived
