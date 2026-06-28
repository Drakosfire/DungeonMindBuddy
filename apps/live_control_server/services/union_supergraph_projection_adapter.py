from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from apps.live_control_server.config import repo_root
from graph_memory.projection import RecapGraphProjection, build_recap_graph_projection
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.preview_import import (
    CandidateGraphInput,
    build_preview_union_supergraph,
)

SESSION_22_ANCHOR_QUOTE_N3_RUN2_REL = (
    "evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26/"
    "anchor_quote_n3/session_22_gpt-5-4-mini_run2/candidate_output.json"
)
SESSION_22_RECAP_REL = (
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/"
    "_normalized/Session 22 - Mireward Road and Lysandro.md"
)
SESSION_23_GOLD_REL = (
    "evals/graph_memory_layer/examples/session_23_candidate_graph_gold/candidate_graph_gold.json"
)
SESSION_23_RECAP_REL = (
    "evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md"
)
TWO_SESSION_PREVIEW_SOURCE = "s22-anchor-quote-n3-s23-gold"


def build_plan_union_supergraph_projection(
    *,
    session_id: str,
    store_path: Path | None = None,
    preview_source: str | None = None,
) -> RecapGraphProjection:
    """Build a backend-neutral graph projection for a /plan session lens."""

    if preview_source:
        store = _build_preview_store(preview_source, focus_session_id=session_id)
        markdown = _load_focus_recap_markdown_from_store(store, session_id=session_id)
        return build_recap_graph_projection(store, session_id=session_id, markdown=markdown)

    resolved_store_path = store_path or DEFAULT_FIXTURE_PATH
    store = load_union_supergraph_store(resolved_store_path)
    markdown = _load_focus_recap_markdown_from_store(store, session_id=session_id)
    return build_recap_graph_projection(store, session_id=session_id, markdown=markdown)


def _load_focus_recap_markdown(*, session_id: str, store_path: Path) -> str | None:
    store = load_union_supergraph_store(store_path)
    return _load_focus_recap_markdown_from_store(store, session_id=session_id)


def _load_focus_recap_markdown_from_store(
    store: Any,
    *,
    session_id: str,
) -> str | None:
    recap_artifact = next(
        (
            artifact
            for artifact in store.source_artifacts.values()
            if artifact.source_domain == "recap" and artifact.session_id == session_id
        ),
        None,
    )
    if recap_artifact is None:
        return None

    root = repo_root()
    recap_path = getattr(recap_artifact, "recap_path", None)
    if recap_path:
        path = Path(str(recap_path).replace("\\", "/"))
        if not path.is_absolute():
            path = root / path
        return _strip_yaml_frontmatter(path.read_text(encoding="utf-8"))
    if not recap_artifact.ingest_run_bundle_uri:
        return None
    manifest_path = root / recap_artifact.ingest_run_bundle_uri
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    input_path = Path(str(manifest["source"]["input_path_record"]).replace("\\", "/"))
    if not input_path.is_absolute():
        input_path = root / input_path
    return _strip_yaml_frontmatter(input_path.read_text(encoding="utf-8"))


def _strip_yaml_frontmatter(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        return markdown
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1 :]).lstrip("\n")
    return markdown


def build_plan_union_supergraph_projection_payload(
    *,
    session_id: str,
    store_path: Path | None = None,
    preview_source: str | None = None,
) -> dict[str, Any]:
    """Build a JSON-safe projection payload for future API route integration."""

    projection = build_plan_union_supergraph_projection(
        session_id=session_id,
        store_path=store_path,
        preview_source=preview_source,
    )
    return projection.model_dump(mode="json")


def _build_preview_store(preview_source: str, *, focus_session_id: str) -> Any:
    if preview_source != TWO_SESSION_PREVIEW_SOURCE:
        raise ValueError(f"unknown union supergraph preview_source: {preview_source}")
    root = repo_root()
    payload = build_preview_union_supergraph(
        [
            CandidateGraphInput(
                path=root / SESSION_22_ANCHOR_QUOTE_N3_RUN2_REL,
                session_id="session-22",
                recap_path=root / SESSION_22_RECAP_REL,
            ),
            CandidateGraphInput(
                path=root / SESSION_23_GOLD_REL,
                session_id="session-23",
                recap_path=root / SESSION_23_RECAP_REL,
            ),
        ],
        focus_session_id=focus_session_id,
    )
    return parse_union_supergraph_store(payload)
