from __future__ import annotations

from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification.breadcrumb_normalize import (
    NormalizedRecord,
    RouteAttachment,
    normalize_breadcrumb_artifact,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_repair import (
    RepairPatch,
    apply_repair_patches,
    build_repair_prompt,
    candidates_to_jsonable,
    find_repair_candidates,
    parse_repair_response,
)

CORPUS_ROOT = Path("corpus/eldyrwild-markdown")
MANUAL_BASELINE = Path(
    "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md"
)


def _make_record(
    *,
    unit_id: str,
    line_start: int,
    text: str,
    routes: list[tuple[str, str]],
) -> NormalizedRecord:
    return NormalizedRecord(
        campaign_id="longmont-c2",
        session_number=20,
        source_recap_path="x.md",
        unit_id=unit_id,
        line_start=line_start,
        line_end=line_start,
        text_blake3="x",
        lexical_plain=text,
        routes=[
            RouteAttachment(
                subject_class=sc,
                normalized_route=nr,
                proposed=False,
                tag_kind="inline",
            )
            for sc, nr in routes
        ],
    )


def test_finder_flags_pronoun_unit_with_neighbor_subject() -> None:
    records = [
        _make_record(
            unit_id="u-A-1",
            line_start=10,
            text="Caelynn looks for Lysandra.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
                ("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"),
            ],
        ),
        _make_record(
            unit_id="u-A-2",
            line_start=10,
            text="She approaches the shelter and hears mumbling.",
            routes=[("Location", "Elderwyld/Cities and Towns/Mossford/")],
        ),
    ]
    candidates = find_repair_candidates(records)
    flagged_ids = [c.unit_id for c in candidates]
    assert flagged_ids == ["u-A-2"]
    assert "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/" in candidates[0].nearby_subject_routes


def test_finder_flags_when_unit_has_only_partial_subject_set() -> None:
    """u-A-2 already has Caelynn but is missing the Lysandra subject route from u-A-1."""
    records = [
        _make_record(
            unit_id="u-A-1",
            line_start=10,
            text="Caelynn looks for Lysandra.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
                ("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"),
            ],
        ),
        _make_record(
            unit_id="u-A-2",
            line_start=10,
            text="She approaches the shelter and hears mumbling.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
            ],
        ),
    ]
    candidates = find_repair_candidates(records)
    flagged = [c.unit_id for c in candidates]
    assert flagged == ["u-A-2"]
    target = next(c for c in candidates if c.unit_id == "u-A-2")
    # Only the Lysandra route is "missing" — Caelynn is already present so
    # nearby_subject_routes must only list the missing one.
    assert "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/" in target.nearby_subject_routes
    assert "Longmont Campaign/Campaign 2/PCs/caelynn/" not in target.nearby_subject_routes


def test_finder_skips_unit_when_all_neighbor_subjects_already_present() -> None:
    records = [
        _make_record(
            unit_id="u-A-1",
            line_start=10,
            text="Caelynn looks for Lysandra.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
            ],
        ),
        _make_record(
            unit_id="u-A-2",
            line_start=10,
            text="She approaches the shelter and hears mumbling.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
            ],
        ),
    ]
    flagged = [c.unit_id for c in find_repair_candidates(records)]
    assert flagged == []


def test_finder_skips_unrelated_paragraph() -> None:
    records = [
        _make_record(
            unit_id="u-P1-1",
            line_start=4,
            text="Caelynn watches Lysandra.",
            routes=[
                ("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"),
            ],
        ),
        # Paragraph break: line jump > 1
        _make_record(
            unit_id="u-P2-1",
            line_start=20,
            text="The other kids ask Bonogo to play with them.",
            routes=[
                ("PC", "Longmont Campaign/Campaign 2/PCs/bonogo/"),
            ],
        ),
        _make_record(
            unit_id="u-P2-2",
            line_start=20,
            text="He counts to twenty and leaves the warehouse.",
            routes=[
                ("Location", "Elderwyld/Cities and Towns/Mossford/Mossford_Location_Dossiers/Half-Burned Warehouse.md"),
            ],
        ),
    ]
    candidates = find_repair_candidates(records)
    flagged = [c.unit_id for c in candidates]
    # u-P2-2 should be flagged with Bonogo as nearby (same paragraph) but Lysandra
    # must NOT bleed across paragraphs.
    assert "u-P2-2" in flagged
    cand = next(c for c in candidates if c.unit_id == "u-P2-2")
    assert any("bonogo" in r for r in cand.nearby_subject_routes)
    assert not any(
        "captain_lysandra_ironveil" in r for r in cand.nearby_subject_routes
    )


def test_apply_repair_patches_dedupes_and_blocks_outside_candidates() -> None:
    records = [
        _make_record(
            unit_id="u-A-1",
            line_start=10,
            text="x",
            routes=[("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/")],
        ),
        _make_record(unit_id="u-A-2", line_start=10, text="y", routes=[]),
    ]
    patches = [
        RepairPatch(
            unit_id="u-A-1",
            add_routes=(
                ("PC", "Longmont Campaign/Campaign 2/PCs/caelynn/"),
                ("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"),
            ),
            reason="present + new",
        ),
        RepairPatch(
            unit_id="u-NOT-CANDIDATE",
            add_routes=(("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"),),
        ),
    ]
    report = apply_repair_patches(
        records,
        patches,
        candidate_unit_ids={"u-A-1"},
    )
    assert report.routes_added == 1
    assert report.units_touched == ["u-A-1"]
    rec = next(r for r in records if r.unit_id == "u-A-1")
    assert any(
        att.normalized_route
        == "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"
        for att in rec.routes
    )
    assert any(p["reason"] == "unit not in candidate set" for p in report.rejected_patches)


def test_apply_repair_patches_rejects_route_outside_allowed_list() -> None:
    records = [_make_record(unit_id="u-A-1", line_start=10, text="x", routes=[])]
    report = apply_repair_patches(
        records,
        [RepairPatch(
            unit_id="u-A-1",
            add_routes=(("NPC", "Some/Made/Up/Route/"),),
        )],
        candidate_unit_ids={"u-A-1"},
        allowed_routes_by_unit={"u-A-1": {"Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/"}},
    )
    assert report.routes_added == 0
    assert any(
        p.get("reason") == "route not in candidate allowed list"
        for p in report.rejected_patches
    )


def test_parse_repair_response_tolerates_fenced_block() -> None:
    text = (
        "Sure, here is the JSON:\n\n"
        "```json\n"
        '{"patches": [{"unit_id": "u-X-1", "add_routes": [{"subject_class": "NPC", "normalized_route": "x/"}], "reason": "ok"}]}\n'
        "```\n"
    )
    patches = parse_repair_response(text)
    assert len(patches) == 1
    assert patches[0].unit_id == "u-X-1"
    assert patches[0].add_routes == (("NPC", "x/"),)


def test_build_repair_prompt_includes_candidates_and_recap() -> None:
    records = [
        _make_record(
            unit_id="u-A-1",
            line_start=10,
            text="Caelynn watches Lysandra.",
            routes=[("NPC", "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/")],
        ),
        _make_record(
            unit_id="u-A-2",
            line_start=10,
            text="She approaches the shelter and hears mumbling.",
            routes=[],
        ),
    ]
    candidates = find_repair_candidates(records)
    system, user = build_repair_prompt(recap_body="...recap...", candidates=candidates)
    assert "repair adjudicator" in system
    assert "u-A-2" in user
    assert "captain_lysandra_ironveil" in user


@pytest.mark.parametrize("control_artifact_glob", [
    "evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-03/breadcrumb_tagging_variant--control_v1--run01.md",
    "evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-03/breadcrumb_tagging_variant--control_v1--run02.md",
    "evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-05-03/breadcrumb_tagging_variant--control_v1--run03.md",
])
def test_finder_flags_lysandra_paragraph_gaps_on_control_artifacts(control_artifact_glob: str) -> None:
    """At least one unit in the L0019 Lysandra paragraph must be flagged when the
    control output dropped a Lysandra co-tag."""
    artifact = Path(control_artifact_glob)
    if not artifact.is_file():
        pytest.skip(f"control artifact not present: {artifact}")
    text = artifact.read_text(encoding="utf-8")
    records, _meta = normalize_breadcrumb_artifact(
        artifact_text=text,
        corpus_root=CORPUS_ROOT.resolve(),
    )
    candidates = find_repair_candidates(records)
    flagged_ids = {c.unit_id for c in candidates}
    # Identify L0019 units that lack Lysandra in this artifact.
    by_unit = {r.unit_id: r for r in records}
    paragraph_l0019 = [
        u
        for u in by_unit
        if u.startswith("u-L0019-")
        and not any(
            "captain_lysandra_ironveil" in att.normalized_route
            for att in by_unit[u].routes
        )
    ]
    expected_flagged = [
        u
        for u in paragraph_l0019
        # only those that have either a durable object route OR a pronoun cue
        # are candidates by construction
        if find_repair_candidates([by_unit[u]] + [
            by_unit[v] for v in by_unit if v != u
        ])
    ]
    # We don't enumerate all expected_flagged in the deterministic test (it
    # depends on the run); we just require ≥1 L0019 unit to surface for repair
    # so the candidate finder gives the LLM something to fix.
    assert any(uid.startswith("u-L0019-") for uid in flagged_ids), (
        f"finder must flag at least one L0019 paragraph unit; got {sorted(flagged_ids)}"
    )
    # Whatever it flagged, those must list Lysandra as a missing nearby route.
    for cand in candidates:
        if cand.unit_id.startswith("u-L0019-") and any(
            "captain_lysandra_ironveil" in r for r in cand.nearby_subject_routes
        ):
            break
    else:
        raise AssertionError(
            "no L0019 candidate had Lysandra in nearby_subject_routes"
        )
    payload = candidates_to_jsonable(candidates)
    assert all("unit_id" in row for row in payload)
