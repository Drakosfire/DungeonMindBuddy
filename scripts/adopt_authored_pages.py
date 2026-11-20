#!/usr/bin/env python3
"""Offline pinned page adoption. Files are explicit migration inputs only.

Capture a digest-only manifest, review its exact SHA-256, then dry-run/apply.
Stop legacy writers and recapture pins before actual delivery. No boot imports.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, ValidationError

from application_state.content.import_pages import FrozenPage, adopt_pages
from application_state.content.pages import PageMetadata
from application_state.content.types import AuthoredPageObject, normalize_markdown, sha256_utf8
from application_state.errors import ApplicationStateError


class LegacyPage(BaseModel):
    """Only the predecessor's explicit page record; reject unrepresentable data."""
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["dmb_workspace_document_record_v1"]
    document_id: str
    title: str
    world_id: str
    campaign_id: str | None
    target_session: None = None
    kind: Literal["worldbuilding_source"]
    target_relpath: str | None
    status: Literal["active", "discarded"]
    content_status: Literal["draft", "committed"]
    connected_page_operation_id: str | None = None
    revision: int
    created_at: str
    updated_at: str
    source_domain: Literal["worldbuilding"]
    document_class: str | None
    authority_state: Literal["draft", "reviewed", "canonical"]
    visibility_state: Literal["internal", "player_safe"]

    def seed(self, markdown: str | None) -> FrozenPage:
        return FrozenPage(
            page=AuthoredPageObject(
                work_object_id=self.document_id, world_id=self.world_id,
                campaign_id=self.campaign_id, title=self.title,
                status=self.status, object_revision=self.revision,
                created_at=self.created_at, updated_at=self.updated_at,
            ),
            metadata=PageMetadata(document_class=self.document_class,
                                  authority_state=self.authority_state,
                                  visibility_state=self.visibility_state,
                                  connected_page_operation_id=self.connected_page_operation_id),
            content_status=self.content_status, markdown=markdown,
            content_sha256=sha256_utf8(markdown) if markdown is not None else None,
        )


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read(root_fd: int, relpath: str, *, absent_ok: bool = False) -> bytes | None:
    """Open only exact relative regular files, no symlink component or race redirect."""
    parts = PurePosixPath(relpath).parts
    if (not parts or PurePosixPath(relpath).is_absolute() or ".." in parts
            or str(PurePosixPath(relpath)) != relpath):
        raise ValueError("input path must be an exact relative path under the owned root")
    parent = os.dup(root_fd)
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            except FileNotFoundError:
                if absent_ok:
                    return None
                raise
            os.close(parent)
            parent = child
        try:
            fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        except FileNotFoundError:
            if absent_ok:
                return None
            raise
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError("input must be a regular file")
            raw = stream.read()
            after = os.fstat(stream.fileno())
            current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            def fingerprint(value):
                return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
            if fingerprint(before) != fingerprint(after) or fingerprint(after) != fingerprint(current):
                raise ValueError("input changed during capture")
            return raw
    finally:
        os.close(parent)


def freeze(root: Path, registry: str) -> tuple[dict, list[FrozenPage]]:
    """Read each declared body once; return metadata/digests and in-memory bodies."""
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        raw = _read(fd, registry)
        document = json.loads(raw)
        if (set(document) != {"schema_version", "records"}
                or document["schema_version"] != "dmb_workspace_document_registry_v1"
                or not isinstance(document["records"], list)):
            raise ValueError("expected the exact predecessor workspace registry")
        manifest, seeds, paths, identities, reservations = [], [], set(), set(), set()
        for record in document["records"]:
            if not isinstance(record, dict) or record.get("kind") not in {"plan", "runbook", "worldbuilding_source"}:
                raise ValueError("unrecognized workspace record")
            # Validate identity across the complete frozen inventory before
            # excluding kinds already owned by Content. UUID spelling is not
            # a second identity namespace (for example uppercase vs lowercase).
            if not isinstance(record.get("document_id"), str):
                raise ValueError("every workspace record requires a UUID identity")
            identity = UUID(record["document_id"])
            if identity in identities:
                raise ValueError("duplicate workspace identity")
            identities.add(identity)
            if record["kind"] != "worldbuilding_source":
                continue  # Plan/Runbook already have their separate Content owner.
            page = LegacyPage.model_validate(record)
            if page.connected_page_operation_id is not None:
                reservation = UUID(page.connected_page_operation_id)
                if reservation in reservations:
                    raise ValueError("duplicate connected reservation")
                reservations.add(reservation)
            body = None
            if page.target_relpath is not None:
                if page.target_relpath in paths or page.target_relpath == registry:
                    raise ValueError("duplicate page body path")
                paths.add(page.target_relpath)
                body = _read(fd, page.target_relpath, absent_ok=page.content_status == "draft")
            markdown = normalize_markdown(body.decode("utf-8")) if body is not None else None
            seed = page.seed(markdown)  # Also refuses missing committed bodies.
            seeds.append(seed)
            manifest.append({"record": page.model_dump(),
                             "raw_sha256": _digest(body) if body is not None else None,
                             "content_sha256": seed.content_sha256})
        # Detect registry changes during the complete capture as well.
        if _read(fd, registry) != raw:
            raise ValueError("registry changed during capture")
        return {"schema_version": "dmb_authored_page_adoption_v1", "registry": registry,
                "registry_sha256": _digest(raw), "pages": manifest}, seeds
    finally:
        os.close(fd)


def adopt_manifest(root: Path, manifest_path: Path, *, expected_sha256: str, apply: bool = False):
    raw = manifest_path.read_bytes()
    if _digest(raw) != expected_sha256:
        raise ValueError("adoption manifest differs from its reviewed SHA-256")
    reviewed = json.loads(raw)
    current, seeds = freeze(root, reviewed["registry"])
    if reviewed != current:
        raise ValueError("registry, page metadata or body differs from the reviewed manifest")
    return adopt_pages(seeds, dry_run=not apply)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    sub = parser.add_subparsers(dest="operation", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--registry", required=True)
    capture.add_argument("--output", type=Path, required=True)
    adopt = sub.add_parser("adopt")
    adopt.add_argument("--manifest", type=Path, required=True)
    adopt.add_argument("--expected-sha256", required=True)
    adopt.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.operation == "capture":
            manifest, _ = freeze(args.root, args.registry)
            inputs = [args.root / args.registry, *(args.root / item["record"]["target_relpath"]
                      for item in manifest["pages"] if item["record"]["target_relpath"] is not None)]
            if args.output.resolve() in {path.resolve() for path in inputs}:
                raise ValueError("manifest output cannot replace a migration input")
            # Exclusive output: never overwrite an original file or reviewed manifest.
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
            result = {"status": "captured", "pages": len(manifest["pages"]),
                      "manifest_sha256": _digest(args.output.read_bytes())}
        else:
            result = asdict(adopt_manifest(args.root, args.manifest,
                                          expected_sha256=args.expected_sha256, apply=args.apply))
    except (OSError, ValueError, KeyError, TypeError, ValidationError, ApplicationStateError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
