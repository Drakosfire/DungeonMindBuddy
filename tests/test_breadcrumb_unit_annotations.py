from __future__ import annotations

import pytest

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    BreadcrumbNormalizeError,
    verify_global_text_equal,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_render import (
    render_routing_only_breadcrumb_markdown,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_route_schema import (
    RouteTagAssignment,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_smoke import (
    parse_frontmatter_and_body,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_compile import (
    compile_unit_annotations_artifacts,
    to_route_assignments,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_measurement import (
    evaluate_second_pass_need,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_prompt import (
    BEAT_BOUNDARY_EXPERIMENT_VARIANTS,
    PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST,
    PROMPT_VARIANT_BEAT_EXP_V_ALL,
    PROMPT_VARIANT_BEAT_POPULATION_V1,
    PROMPT_VARIANT_CONTROL,
    build_unit_annotations_prompt,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_schema import (
    BeatIndexEntry,
    LocationMention,
    PopulationMention,
    RecapUnitAnnotationsV1,
    UnitAnnotation,
    beat_id_matches_grammar,
    validate_unit_annotations,
)
from evals.sentence_routing_retrieval_falsification.capture import (
    capture_sentence_unit_spans,
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

_PC_ROUTE = "Longmont Campaign/Campaign 1/PCs/caelynn/"
_LOC_ROUTE = "Longmont Campaign/Campaign 1/Locations/stormspire_academy/"


def _sample_payload(*, unit_ids: list[str]) -> RecapUnitAnnotationsV1:
    beat = "c1s13-b001-council-chambers-exit"
    rows: list[UnitAnnotation] = []
    for i, uid in enumerate(unit_ids):
        rows.append(
            UnitAnnotation(
                unit_id=uid,
                beat_id=beat,
                tags=[
                    RouteTagAssignment(tag_type="PC", route=_PC_ROUTE),
                ]
                if i == 0
                else [],
                location_mentions=[
                    LocationMention(
                        location_route=_LOC_ROUTE,
                        presence_kind="explicit",
                    )
                ]
                if i == 0
                else [
                    LocationMention(
                        location_route=_LOC_ROUTE,
                        presence_kind="carried",
                    )
                ],
                population_mentions=[
                    PopulationMention(
                        entity_route=_PC_ROUTE,
                        subject_class="PC",
                        presence_kind="explicit" if i == 0 else "carried",
                        support_unit_ids=[unit_ids[0], uid] if i > 0 else [uid],
                    )
                ]
                if i <= 1
                else [],
            )
        )
    return RecapUnitAnnotationsV1(
        schema_discriminator="dmb_recap_unit_annotations_v1",
        source_recap_path="Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md",
        campaign_id="longmont-c1",
        session_number=13,
        beat_index=[BeatIndexEntry(beat_id=beat, summary="Exit council chambers.")],
        unit_annotations=rows,
    )


def test_beat_id_grammar_accepts_plan_example() -> None:
    assert beat_id_matches_grammar("c1s13-b004-stormspire-arrival")


def test_validate_shape_rejects_unit_order_mismatch() -> None:
    payload = _sample_payload(unit_ids=["u-L0001-01", "u-L0001-02"])
    payload.unit_annotations[0].unit_id = "u-L0001-02"
    payload.unit_annotations[1].unit_id = "u-L0001-01"
    allow = {_PC_ROUTE, _LOC_ROUTE}
    with pytest.raises(BreadcrumbNormalizeError, match="order mismatch"):
        validate_unit_annotations(
            payload,
            expected_source_recap_path=payload.source_recap_path,
            expected_campaign_id="longmont-c1",
            expected_session_number=13,
            known_unit_ids=["u-L0001-01", "u-L0001-02"],
            route_allowlist_normalized=allow,
            run_semantic=False,
        )


def test_validate_semantic_rejects_beat_reopen() -> None:
    payload = RecapUnitAnnotationsV1(
        schema_discriminator="dmb_recap_unit_annotations_v1",
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        beat_index=[
            BeatIndexEntry(beat_id="c1s13-b001-a", summary="a"),
            BeatIndexEntry(beat_id="c1s13-b002-b", summary="b"),
        ],
        unit_annotations=[
            UnitAnnotation(unit_id="u-L0001-01", beat_id="c1s13-b001-a"),
            UnitAnnotation(unit_id="u-L0001-02", beat_id="c1s13-b002-b"),
            UnitAnnotation(unit_id="u-L0001-03", beat_id="c1s13-b001-a"),
        ],
    )
    allow: set[str] = set()
    with pytest.raises(BreadcrumbNormalizeError, match="not contiguous"):
        validate_unit_annotations(
            payload,
            expected_source_recap_path="a.md",
            expected_campaign_id="longmont-c1",
            expected_session_number=13,
            known_unit_ids=["u-L0001-01", "u-L0001-02", "u-L0001-03"],
            route_allowlist_normalized=allow,
        )


def test_compile_location_beats_excludes_mentioned_only_from_present() -> None:
    payload = RecapUnitAnnotationsV1(
        schema_discriminator="dmb_recap_unit_annotations_v1",
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        beat_index=[BeatIndexEntry(beat_id="c1s13-b004-stormspire-arrival", summary="s")],
        unit_annotations=[
            UnitAnnotation(
                unit_id="u-L0001-01",
                beat_id="c1s13-b004-stormspire-arrival",
                location_mentions=[
                    LocationMention(location_route=_LOC_ROUTE, presence_kind="explicit")
                ],
                population_mentions=[
                    PopulationMention(
                        entity_route=_PC_ROUTE,
                        subject_class="PC",
                        presence_kind="mentioned_only",
                        support_unit_ids=["u-L0001-01"],
                    )
                ],
            )
        ],
    )
    artifacts = compile_unit_annotations_artifacts(payload)
    rows = artifacts["location_beat_rows"]
    assert len(rows) == 1
    assert rows[0]["entity_routes_present"] == []
    assert rows[0]["population_evidence"] == []


def test_to_route_assignments_renders_breadcrumb_body() -> None:
    recap_body = "# Session\n\n4.1: Keep colon spacing.\n"
    path = "x.md"
    spans = capture_sentence_unit_spans(recap_text=recap_body, recap_relative_path=path)
    uid = spans[0].unit_id
    payload = RecapUnitAnnotationsV1(
        schema_discriminator="dmb_recap_unit_annotations_v1",
        source_recap_path=path,
        campaign_id="longmont-c1",
        session_number=13,
        beat_index=[],
        unit_annotations=[
            UnitAnnotation(
                unit_id=uid,
                tags=[RouteTagAssignment(tag_type="PC", route=_PC_ROUTE)],
            )
        ],
    )
    md = render_routing_only_breadcrumb_markdown(
        seed_frontmatter_yaml=_MINIMAL_FM,
        recap_body=recap_body,
        spans=spans,
        assignments=to_route_assignments(payload),
    )
    _fm, body = parse_frontmatter_and_body(md)
    assert body is not None
    verify_global_text_equal(breadcrumb_body=body, recap_body=recap_body)


def test_build_unit_annotations_prompt_includes_beat_contract() -> None:
    prompt = build_unit_annotations_prompt(
        variant=PROMPT_VARIANT_BEAT_POPULATION_V1,
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        recap_body="Line.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
        units=[{"unit_id": "u-L0001-01", "text": "Line."}],
        allowed_routes=[_PC_ROUTE],
    )
    assert "dmb_recap_unit_annotations_v1" in prompt.system_text
    assert "retrieval-stable segment" in prompt.system_text
    assert "smallest" in prompt.system_text
    assert "party splits, rejoins" in prompt.system_text
    assert "BEAT / POPULATION EMPHASIS" in prompt.system_text
    assert "longmont-c1" in prompt.user_text


def test_build_unit_annotations_control_has_no_beat_emphasis_addendum() -> None:
    prompt = build_unit_annotations_prompt(
        variant=PROMPT_VARIANT_CONTROL,
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        recap_body="Line.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
        units=[{"unit_id": "u-L0001-01", "text": "Line."}],
        allowed_routes=[_PC_ROUTE],
    )
    assert "BEAT / POPULATION EMPHASIS" not in prompt.system_text


def test_beat_boundary_experiment_variants_include_isolated_and_combined() -> None:
    assert PROMPT_VARIANT_BEAT_POPULATION_V1 in BEAT_BOUNDARY_EXPERIMENT_VARIANTS
    assert PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST in BEAT_BOUNDARY_EXPERIMENT_VARIANTS
    assert PROMPT_VARIANT_BEAT_EXP_V_ALL in BEAT_BOUNDARY_EXPERIMENT_VARIANTS
    v1 = build_unit_annotations_prompt(
        variant=PROMPT_VARIANT_BEAT_EXP_V1_NO_LARGEST,
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        recap_body="Line.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
        units=[{"unit_id": "u-L0001-01", "text": "Line."}],
        allowed_routes=[_PC_ROUTE],
    )
    assert "smallest" in v1.system_text
    assert "LOCATION MENTIONS DO NOT LICENSE MERGING" not in v1.system_text
    v_all = build_unit_annotations_prompt(
        variant=PROMPT_VARIANT_BEAT_EXP_V_ALL,
        source_recap_path="a.md",
        campaign_id="longmont-c1",
        session_number=13,
        recap_body="Line.",
        frontmatter_yaml="schema: dmb_recap_breadcrumbs_v1",
        units=[{"unit_id": "u-L0001-01", "text": "Line."}],
        allowed_routes=[_PC_ROUTE],
    )
    assert "smallest" in v_all.system_text
    assert "LOCATION MENTIONS DO NOT LICENSE MERGING" in v_all.system_text
    assert "BEAT ROW SELF-CHECK" in v_all.system_text


def test_evaluate_second_pass_need_recommends_dominant_mode() -> None:
    out = evaluate_second_pass_need(
        {
            "dimension_pass_rates": {
                "beat_unit_membership": 0.5,
                "route_tag_recall": 0.9,
            },
            "failures_by_mode": {
                "population_carry": 8,
                "beat_boundary_drift": 1,
            },
            "route_tag_regression_vs_baseline": False,
        }
    )
    assert out["decision"] == "second_pass_recommended"
    assert out["failure_mode"] == "population_carry"


def test_evaluate_second_pass_need_blocks_on_route_regression() -> None:
    out = evaluate_second_pass_need(
        {
            "dimension_pass_rates": {"present_population": 0.4},
            "failures_by_mode": {"population_carry": 10},
            "route_tag_regression_vs_baseline": True,
        }
    )
    assert out["decision"] == "single_pass_sufficient"
    assert "route tagging regressed" in out["rationale"]
