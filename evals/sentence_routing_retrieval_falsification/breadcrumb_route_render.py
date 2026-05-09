"""Deterministic render: validated route assignments + recap body → breadcrumb markdown."""

from __future__ import annotations

import re
from collections import Counter
from typing import Sequence

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import BreadcrumbNormalizeError
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    BreadcrumbRouteAssignmentsV1,
    RouteTagAssignment,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import ALLOWED_TAG_TYPES
from evals.sentence_routing_retrieval_falsification.capture import SentenceUnitSpan


def count_inline_tags_by_type(payload: BreadcrumbRouteAssignmentsV1) -> dict[str, int]:
    c: Counter[str] = Counter()
    for row in payload.assignments:
        for t in row.tags:
            c[t.tag_type] += 1
    return {k: int(c.get(k, 0)) for k in ALLOWED_TAG_TYPES}


def patch_inline_tag_counts(frontmatter_yaml: str, counts: dict[str, int]) -> str:
    """Replace ``inline_tags`` integers in seed frontmatter (regex-safe YAML subset)."""
    out = frontmatter_yaml
    for subject in sorted(ALLOWED_TAG_TYPES):
        if subject not in counts:
            raise BreadcrumbNormalizeError(f"inline tag count missing for {subject!r}")
        n = counts[subject]
        pat = re.compile(rf"^(\s*{re.escape(subject)}:\s*)\d+(\s*)$", re.MULTILINE)
        new_out, nsub = pat.subn(lambda m, n=n: f"{m.group(1)}{n}{m.group(2)}", out)
        if nsub == 0:
            raise BreadcrumbNormalizeError(
                f"could not patch inline_tags.{subject} in seed frontmatter"
            )
        out = new_out
    return out


def _tag_suffix_for_unit(tags: Sequence[RouteTagAssignment]) -> str:
    return "".join(f"[{t.tag_type}][{t.route}]" for t in tags)


def tag_suffix_by_unit_id(payload: BreadcrumbRouteAssignmentsV1) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in payload.assignments:
        if not row.tags:
            continue
        suf = _tag_suffix_for_unit(row.tags)
        if row.unit_id in out:
            raise BreadcrumbNormalizeError(f"duplicate assignments row for unit_id={row.unit_id!r}")
        out[row.unit_id] = suf
    return out


def inject_breadcrumb_tags(
    recap_body: str,
    spans: Sequence[SentenceUnitSpan],
    suffix_by_unit_id: dict[str, str],
) -> str:
    """Insert tag suffixes after unit spans (right-to-left so offsets stay valid)."""
    endpoints: list[tuple[int, str]] = [
        (s.body_end, s.unit_id) for s in spans if s.unit_id in suffix_by_unit_id
    ]
    endpoints.sort(key=lambda x: x[0], reverse=True)
    out = recap_body
    for body_end, uid in endpoints:
        suf = suffix_by_unit_id[uid]
        out = out[:body_end] + suf + out[body_end:]
    return out


def render_routing_only_breadcrumb_markdown(
    *,
    seed_frontmatter_yaml: str,
    recap_body: str,
    spans: Sequence[SentenceUnitSpan],
    assignments: BreadcrumbRouteAssignmentsV1,
) -> str:
    """Full ``dmb_recap_breadcrumbs_v1`` markdown (frontmatter + body)."""
    counts = count_inline_tags_by_type(assignments)
    fm = patch_inline_tag_counts(seed_frontmatter_yaml.strip(), counts)
    suffixes = tag_suffix_by_unit_id(assignments)
    body = inject_breadcrumb_tags(recap_body, spans, suffixes)
    return "---\n" + fm + "\n---\n" + body
