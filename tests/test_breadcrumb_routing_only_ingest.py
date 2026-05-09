from __future__ import annotations

import pytest

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    verify_global_text_equal,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_render import (
    inject_breadcrumb_tags,
    patch_inline_tag_counts,
    render_routing_only_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    BreadcrumbRouteAssignmentsV1,
    RouteTagAssignment,
    UnitRouteAssignment,
    validate_route_assignments,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    TAG_RE,
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.capture import (
    capture_sentence_unit_spans,
    capture_sentence_units,
)


_MINIMAL_FM = """\
source_recap_path: "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md"
campaign_id: longmont-c1
session:
  number: 13
counts_by_subject_type:
  inline_tags:
    PC: 0
    NPC: 0
    Location: 0
    Party: 0
    NewHubCandidate: 0
"""


def test_capture_spans_align_with_sentence_units() -> None:
    text = "# Title\n\nFirst. Second sentence.\n\n3: Ask something. 4.1: Keep spacing. Weird? Yes."
    path = "dummy.md"
    units = capture_sentence_units(recap_text=text, recap_relative_path=path)
    spans = capture_sentence_unit_spans(recap_text=text, recap_relative_path=path)
    assert [(u.unit_id, u.text) for u in units] == [(s.unit_id, s.text) for s in spans]
    for s in spans:
        assert text[s.body_start : s.body_end] == s.text


def test_inject_tags_preserves_source_text_after_tag_strip() -> None:
    recap_body = "# Title\n\n4.1: First unit. Second here."
    path = "x.md"
    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=path)
    uid_first = spans[0].unit_id
    suffix = {uid_first: "[PC][Longmont Campaign/Campaign 1/PCs/caelynn/]"}
    rendered = inject_breadcrumb_tags(recap_body, spans, suffix)
    assert TAG_RE.sub("", rendered) == recap_body


def test_verify_global_text_equal_passes_for_rendered_routing_only_body() -> None:
    # Exactly one capture unit on the recap body (see ``joint_normalized_from_units``):
    # multiple clause splits on one line drop inter-clause spaces from the joint.
    recap_body = "# Session\n\n4.1: Keep colon spacing.\n"
    path = "x.md"
    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=path)
    uid = spans[0].unit_id
    payload = BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path=path,
        assignments=[
            UnitRouteAssignment(
                unit_id=uid,
                tags=[
                    RouteTagAssignment(
                        tag_type="PC",
                        route="Longmont Campaign/Campaign 1/PCs/caelynn/",
                    )
                ],
            )
        ],
    )
    md = render_routing_only_breadcrumb_markdown(
        seed_frontmatter_yaml=_MINIMAL_FM,
        recap_body=recap_body,
        spans=spans,
        assignments=payload,
    )
    _fm, body = parse_frontmatter_and_body(md)
    assert body is not None
    verify_global_text_equal(breadcrumb_body=body, recap_body=recap_body)
    patched = patch_inline_tag_counts(
        _MINIMAL_FM,
        {"PC": 1, "NPC": 0, "Location": 0, "Party": 0, "NewHubCandidate": 0},
    )
    assert "PC: 1" in patched


def test_validate_route_assignments_unknown_unit() -> None:
    payload = BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path="a.md",
        assignments=[
            UnitRouteAssignment(
                unit_id="u-L9999-01",
                tags=[
                    RouteTagAssignment(
                        tag_type="PC",
                        route="Longmont Campaign/Campaign 1/PCs/caelynn/",
                    )
                ],
            )
        ],
    )
    allow = {"Longmont Campaign/Campaign 1/PCs/caelynn/"}
    with pytest.raises(BreadcrumbNormalizeError, match="unknown unit_id"):
        validate_route_assignments(
            payload,
            expected_source_recap_path="a.md",
            known_unit_ids={"u-L0001-01"},
            route_allowlist_normalized=allow,
        )


def test_validate_route_assignments_rejects_disallowed_route() -> None:
    payload = BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path="a.md",
        assignments=[
            UnitRouteAssignment(
                unit_id="u-L0001-01",
                tags=[
                    RouteTagAssignment(
                        tag_type="PC",
                        route="Longmont Campaign/Campaign 1/PCs/missing_slug/",
                    )
                ],
            )
        ],
    )
    allow = {"Longmont Campaign/Campaign 1/PCs/caelynn/"}
    with pytest.raises(BreadcrumbNormalizeError, match="not in frontmatter allowlist"):
        validate_route_assignments(
            payload,
            expected_source_recap_path="a.md",
            known_unit_ids={"u-L0001-01"},
            route_allowlist_normalized=allow,
        )


def test_validate_route_assignments_duplicate_unit_row() -> None:
    tag = RouteTagAssignment(
        tag_type="PC",
        route="Longmont Campaign/Campaign 1/PCs/caelynn/",
    )
    payload = BreadcrumbRouteAssignmentsV1(
        schema_discriminator="dmb_breadcrumb_route_assignments_v1",
        source_recap_path="a.md",
        assignments=[
            UnitRouteAssignment(unit_id="u-L0001-01", tags=[tag]),
            UnitRouteAssignment(unit_id="u-L0001-01", tags=[tag]),
        ],
    )
    allow = {"Longmont Campaign/Campaign 1/PCs/caelynn/"}
    with pytest.raises(BreadcrumbNormalizeError, match="duplicate assignments entry"):
        validate_route_assignments(
            payload,
            expected_source_recap_path="a.md",
            known_unit_ids={"u-L0001-01"},
            route_allowlist_normalized=allow,
        )
