"""Explicit one-time adoption of an exact recap into APP-STATE.

This is an operator/migration boundary, not a runtime read fallback. After
adoption, historical inspection and projection read ``source.revision`` only.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from apps.live_control_server.config import repo_root
from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    _component_by_kind,
    _resolve_repo_contained_uri,
    get_extraction_run,
)
from application_state.source import service as source_service
from application_state.source.types import SourceMarkdownRecord
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    normalize_content_digest,
)


def adopt_historical_recap_source(
    root: Path,
    *,
    run_id: str,
    world_id: str,
) -> SourceMarkdownRecord:
    """Adopt bytes for one exact recap run without changing the run lifecycle."""

    cleaned_world_id = world_id.strip()
    if not cleaned_world_id:
        raise GraphRunRegistryError("world_id is required for source adoption", status_code=422)
    run = get_extraction_run(root, run_id)
    if run.source_domain != "recap":
        raise GraphRunRegistryError(
            "source adoption is only supported for recap runs",
            status_code=422,
        )
    component = _component_by_kind(
        run.components,
        ExtractionRunComponentKind.SOURCE_ARTIFACT,
    )
    if component is None or not component.uri.strip():
        raise GraphRunRegistryError(
            "exact run does not record a source_artifact component",
            status_code=422,
        )
    expected_digest = normalize_content_digest(component.sha256)
    if not expected_digest:
        raise GraphRunRegistryError(
            "exact run source_artifact component has no content digest",
            status_code=422,
        )
    source_path = _resolve_repo_contained_uri(root, component.uri)
    if not source_path.is_file():
        raise GraphRunRegistryError(
            "exact recap source is not available for explicit adoption",
            status_code=404,
        )
    raw = source_path.read_bytes()
    actual_digest = hashlib.sha256(raw).hexdigest()
    if actual_digest != expected_digest:
        raise GraphRunRegistryError(
            "exact recap source digest does not match the ExtractionRun",
            status_code=422,
        )
    try:
        markdown = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GraphRunRegistryError(
            f"exact recap source is not valid UTF-8: {exc}",
            status_code=422,
        ) from exc

    return source_service.persist_source_markdown(
        source_artifact_id=run.source_artifact_id,
        source_domain=run.source_domain,
        campaign_id=run.campaign_id,
        session_id=run.session_id,
        world_id=cleaned_world_id,
        markdown=markdown,
        content_sha256=expected_digest,
        lineage={
            "adopted_from_run_id": run.run_id,
            "adopted_from_uri": component.uri,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Adopt one exact recap source into Buddy APP-STATE."
    )
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--world-id", required=True)
    args = parser.parse_args(argv)
    try:
        record = adopt_historical_recap_source(
            repo_root(),
            run_id=args.run_id,
            world_id=args.world_id,
        )
    except (GraphRunRegistryError, ValueError) as exc:
        print(str(exc))
        return 2
    print(
        f"adopted source_artifact_id={record.source_artifact_id} "
        f"source_revision_id={record.source_revision_id} "
        f"content_sha256=sha256:{record.content_sha256} world_id={record.world_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
