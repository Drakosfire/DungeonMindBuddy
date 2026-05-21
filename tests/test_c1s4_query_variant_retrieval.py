from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.context_classification import is_admittable_planner_evidence
from evals.c1s4_preplanning_vertical_slice.query_variant_retrieval import (
    family_key_for_candidate,
    merge_variant_hits,
    select_required_family_alias_hits,
    stable_dedupe_hits,
)


def _literal_hit(idx: int) -> dict:
    return {"unit_id": f"literal:{idx}", "snippet": f"literal filler {idx}"}


def _alias_hit(
    unit_id: str,
    *,
    source_path: str = "",
    evidence_role: str = "evidence",
    source_kind: str = "npc_dossier",
) -> dict:
    return {
        "unit_id": unit_id,
        "source_path": source_path,
        "evidence_role": evidence_role,
        "source_kind": source_kind,
        "subject_class": "npc",
    }


def _records_by_unit_id(*hits: dict) -> dict[str, dict]:
    return {str(h["unit_id"]): dict(h) for h in hits}


def test_merge_variant_hits_preserves_required_npc_families_within_alias_slots() -> None:
    grishna = _alias_hit(
        "corpus:npc:grishna:summary",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/grishna_character_dossier.md",
    )
    pippa = _alias_hit(
        "corpus:npc:pippa:table-role",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/pippa_character_dossier.md",
    )
    bubbles = _alias_hit(
        "corpus:npc:bubbles_the_float_goat:bubbles-at-the-table",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/bubbles_the_float_goat_character_dossier.md",
    )
    filler_aliases = [_alias_hit(f"alias:filler:{i}", source_path=f"corpus/filler/{i}.md") for i in range(20)]
    alias_hits = filler_aliases[:18] + [grishna, pippa, bubbles]
    variant = {
        "variant_role": "npc_target_alias",
        "query": "Grishna River's Edge Pub",
    }
    records = _records_by_unit_id(grishna, pippa, bubbles, *filler_aliases)

    merged, diag = merge_variant_hits(
        literal_hits=[_literal_hit(i) for i in range(45)],
        alias_hits=alias_hits,
        literal_keep_n=40,
        alias_slot_n=10,
        candidate_depth=50,
        alias_hits_by_variant=[(variant, alias_hits)],
        records_by_unit_id=records,
    )

    merged_ids = [h["unit_id"] for h in merged]
    assert "corpus:npc:grishna:summary" in merged_ids
    assert "corpus:npc:pippa:table-role" in merged_ids
    assert "corpus:npc:bubbles_the_float_goat:bubbles-at-the-table" in merged_ids
    grishna_hit = next(h for h in merged if h["unit_id"] == "corpus:npc:grishna:summary")
    assert grishna_hit.get("merge_reason") == "required_npc_family_coverage"
    assert diag["required_family_slots_used"] == 3


def test_merge_variant_hits_counts_required_family_hits_against_alias_slot_budget() -> None:
    grishna = _alias_hit(
        "corpus:npc:grishna:summary",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/grishna_character_dossier.md",
    )
    filler_aliases = [_alias_hit(f"alias:filler:{i}") for i in range(15)]
    alias_hits = filler_aliases + [grishna]
    variant = {"variant_role": "npc_target_alias", "query": "Grishna River's Edge Pub"}
    records = _records_by_unit_id(grishna, *filler_aliases)

    merged, diag = merge_variant_hits(
        literal_hits=[_literal_hit(i) for i in range(40)],
        alias_hits=alias_hits,
        literal_keep_n=40,
        alias_slot_n=10,
        candidate_depth=50,
        alias_hits_by_variant=[(variant, alias_hits)],
        records_by_unit_id=records,
    )

    alias_ids = {h["unit_id"] for h in merged[40:]}
    assert "corpus:npc:grishna:summary" in alias_ids
    assert len(alias_ids) <= 10
    assert diag["required_family_slots_used"] == 1
    assert diag["remaining_alias_slots"] == 9


def test_merge_variant_hits_does_not_select_navigation_or_alias_records_for_family_coverage() -> None:
    navigation = _alias_hit(
        "corpus:npc:grishna:suggested-reads-in-order",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/README.md",
        evidence_role="navigation_only",
        source_kind="npc_hub",
    )
    summary = _alias_hit(
        "corpus:npc:grishna:summary",
        source_path="corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/grishna/grishna_character_dossier.md",
    )
    variant = {"variant_role": "npc_target_alias", "query": "Grishna River's Edge Pub"}
    records = _records_by_unit_id(navigation, summary)

    selected, _diag = select_required_family_alias_hits(
        alias_hits_by_variant=[(variant, [navigation, summary])],
        literal_head_unit_ids=set(),
        records_by_unit_id=records,
    )

    assert len(selected) == 1
    assert selected[0]["unit_id"] == "corpus:npc:grishna:summary"
    assert is_admittable_planner_evidence(records[selected[0]["unit_id"]])


def test_family_key_for_candidate_detects_c1s4_npc_families() -> None:
    assert family_key_for_candidate({"unit_id": "corpus:npc:grishna:summary"}) == "grishna"
    assert (
        family_key_for_candidate(
            {
                "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md"
            }
        )
        == "bubbles"
    )
    assert family_key_for_candidate({"unit_id": "corpus:npc:pippa:table-role"}) == "pippa"
    assert family_key_for_candidate({"unit_id": "corpus:location:stone_bridge:summary"}) is None


def test_stable_dedupe_hits_preserves_first_occurrence() -> None:
    hits = [{"unit_id": "a"}, {"unit_id": "b"}, {"unit_id": "a", "snippet": "second"}]
    out = stable_dedupe_hits(hits)
    assert [h["unit_id"] for h in out] == ["a", "b"]
    assert out[0].get("snippet") is None
