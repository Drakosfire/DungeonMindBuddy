"""Explicit one-time input metadata adoption; never imported by product runtime.

The selected JSON export is only migration input. Bodies must already exist in
APP at the exact artifact/digest binding. No file locators are followed, no scope
is inferred, and no DungeonMind provenance or Graph facts are admitted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from application_state.source import service as sources
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact


def adopt(path: Path, *, apply: bool = False) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(document, dict)
            or document.get("schema_version") != "dmb_source_artifact_registry_v1"
            or not isinstance(document.get("records"), list)):
        raise ValueError("expected an explicitly selected source registry export")
    artifacts = [GraphMemorySourceArtifact.model_validate(row) for row in document["records"]]
    ids = [item.source_artifact_id for item in artifacts]
    if len(set(ids)) != len(ids):
        raise ValueError("export repeats a source artifact identity")
    checked = []
    # Validate the complete selected batch before the first write. Every write
    # repeats exact body/descriptor checks in its owning APP transaction.
    for artifact in artifacts:
        if not artifact.content_sha256:
            raise ValueError(f"missing exact digest: {artifact.source_artifact_id}")
        record = sources.get_source_markdown(source_artifact_id=artifact.source_artifact_id, content_sha256=artifact.content_sha256)
        if record is None:
            raise ValueError(f"database body unavailable: {artifact.source_artifact_id}")
        if (hashlib.sha256(record.markdown.encode("utf-8")).hexdigest() != record.content_sha256
                or record.media_type != "text/markdown" or record.encoding != "utf-8"):
            raise ValueError(f"invalid database body: {artifact.source_artifact_id}")
        sources.persist_source_markdown(
            source_artifact_id=artifact.source_artifact_id, source_domain=str(artifact.source_domain),
            campaign_id=artifact.campaign_id, session_id=artifact.session_id, world_id=artifact.world_id,
            markdown=record.markdown, content_sha256=artifact.content_sha256,
            input_descriptor=artifact.model_dump(mode="json"), dry_run=True,
        )
        checked.append((artifact, record))
    for artifact, record in checked:
        if apply:
            sources.persist_source_markdown(
                source_artifact_id=artifact.source_artifact_id, source_domain=str(artifact.source_domain),
                campaign_id=artifact.campaign_id, session_id=artifact.session_id, world_id=artifact.world_id,
                markdown=record.markdown, content_sha256=artifact.content_sha256,
                input_descriptor=artifact.model_dump(mode="json"),
            )
    return [{"source_artifact_id": artifact.source_artifact_id,
             "content_sha256": record.content_sha256,
             "status": "adopted" if apply else "verified_no_write"} for artifact, record in checked]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry-json", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(adopt(args.registry_json, apply=args.apply), indent=2))


if __name__ == "__main__":
    main()
