#!/usr/bin/env python3
"""Rebuild corpus breadcrumb markdown from normalized recap + session-memory records."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (  # noqa: E402
    BreadcrumbNormalizeError,
    normalize_breadcrumb_artifact,
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_render import (  # noqa: E402
    render_routing_only_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (  # noqa: E402
    BreadcrumbRouteAssignmentsV1,
    RouteTagAssignment,
    UnitRouteAssignment,
)
from evals.sentence_routing_retrieval_falsification.capture import (  # noqa: E402
    capture_sentence_unit_spans,
)
from src.corpus.session_recap_paths import (  # noqa: E402
    breadcrumbed_relpath,
    frontmatter_seed_relpath,
    normalized_recap_relpath,
    resolve_under_corpus,
)

_DEFAULT_CORPUS = _REPO_ROOT / "corpus" / "eldyrwild-markdown"


def _patch_source_recap_path(frontmatter_yaml: str, source_recap_path: str) -> str:
    return re.sub(
        r"^source_recap_path:\s*.*$",
        f'source_recap_path: "{source_recap_path}"',
        frontmatter_yaml,
        count=1,
        flags=re.MULTILINE,
    )


def rebuild_breadcrumb_markdown(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
    records_jsonl: Path,
    frontmatter_seed: Path | None = None,
    frontmatter_from: Path | None = None,
) -> str:
    norm_rel = normalized_recap_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    norm_path = resolve_under_corpus(corpus_root, norm_rel)
    recap_text = norm_path.read_text(encoding="utf-8")
    _, recap_body = parse_frontmatter_and_body(recap_text)

    if frontmatter_seed is not None:
        fm_yaml = frontmatter_seed.read_text(encoding="utf-8")
        _, fm_yaml = parse_frontmatter_and_body(fm_yaml)
        if fm_yaml is None:
            raise BreadcrumbNormalizeError(f"missing frontmatter in {frontmatter_seed}")
    elif frontmatter_from is not None:
        fm_text = frontmatter_from.read_text(encoding="utf-8")
        fm_yaml, _ = parse_frontmatter_and_body(fm_text)
        if fm_yaml is None:
            raise BreadcrumbNormalizeError(f"missing frontmatter in {frontmatter_from}")
    else:
        raise ValueError("frontmatter_seed or frontmatter_from required")

    fm_yaml = _patch_source_recap_path(fm_yaml, norm_rel)
    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=norm_rel)
    span_by_id = {s.unit_id: s for s in spans}

    assignments: list[UnitRouteAssignment] = []
    for line in records_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        routes = row.get("routes") or []
        if not routes:
            continue
        unit_id = str(row.get("unit_id") or "")
        if unit_id not in span_by_id:
            continue
        tags = [
            RouteTagAssignment(
                tag_type=str(r.get("subject_class") or ""),
                route=str(r.get("normalized_route") or ""),
            )
            for r in routes
        ]
        assignments.append(UnitRouteAssignment(unit_id=unit_id, tags=tags))

    payload = BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path=norm_rel,
        assignments=assignments,
    )
    return render_routing_only_breadcrumb_markdown(
        seed_frontmatter_yaml=fm_yaml,
        recap_body=recap_body,
        spans=spans,
        assignments=payload,
    )


def write_pilot_breadcrumb(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
    records_jsonl: Path,
    frontmatter_seed: Path | None = None,
    frontmatter_from: Path | None = None,
) -> Path:
    out_rel = breadcrumbed_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    out_path = resolve_under_corpus(corpus_root, out_rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    markdown = rebuild_breadcrumb_markdown(
        corpus_root=corpus_root,
        campaign_number=campaign_number,
        session=session,
        records_jsonl=records_jsonl,
        frontmatter_seed=frontmatter_seed,
        frontmatter_from=frontmatter_from,
    )
    normalize_breadcrumb_artifact(artifact_text=markdown, corpus_root=corpus_root)
    out_path.write_text(markdown, encoding="utf-8")
    return out_path


def copy_frontmatter_seed(
    *,
    corpus_root: Path,
    campaign_number: int,
    session: int,
    seed_src: Path,
) -> Path:
    out_rel = frontmatter_seed_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    out_path = resolve_under_corpus(corpus_root, out_rel)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    norm_rel = normalized_recap_relpath(
        campaign_number=campaign_number,
        session=session,
        corpus_root=corpus_root,
    )
    text = seed_src.read_text(encoding="utf-8")
    fm, body = parse_frontmatter_and_body(text)
    if fm is None:
        raise BreadcrumbNormalizeError(f"missing frontmatter in {seed_src}")
    fm = _patch_source_recap_path(fm, norm_rel)
    out_path.write_text("---\n" + fm + "\n---\n" + (body or ""), encoding="utf-8")
    return out_path
