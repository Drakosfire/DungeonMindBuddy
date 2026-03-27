"""Step 3: Prove Play Updates Don't Corrupt Lower Layers.

Runs two projections with play-layer (OBSERVED) facts from real session recaps:
  1. World projection (campaign_id=None) — must match Step 1 output exactly.
  2. Campaign projection (campaign_id="longmont_01") — world + planning + play.

Verifies:
  - World projection unchanged from Step 1.
  - OBSERVED facts supersede PREP facts (session ordering).
  - Brother Ashwood remains PREP-only (no play facts override him).
  - The Shepherd appears only in campaign projection (play-discovered entity).
  - Three truth_states visible in campaign projection: CANON, PREP, OBSERVED.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = Path(__file__).resolve().parent / "input"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.schema_validation import validate_many  # noqa: E402
from src.reducer.canon_projection import project_entity_state  # noqa: E402

CAMPAIGN_ID = "longmont_01"

ENTITY_DISPLAY_NAMES = {
    "ent_mirathorn": "Mirathorn (City)",
    "ent_shepherds_flock": "Shepherd's Flock (Faction)",
    "ent_brother_ashwood": "Brother Ashwood (NPC — PREP only)",
    "ent_the_shepherd": "The Shepherd (NPC — play-discovered)",
}


def load_json(name: str) -> list:
    path = INPUT_DIR / name
    with open(path) as f:
        return json.load(f)


def _get_fact_truth_state(fact_id: str, facts: list[dict]) -> str:
    for f in facts:
        if f["fact_id"] == fact_id:
            return f.get("truth_state", "?")
    return "?"


def render_projection(
    projection: dict,
    evidence_by_id: dict,
    facts: list[dict],
    title: str,
) -> str:
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append(f"  {title}")
    lines.append("=" * 70)
    lines.append("")

    campaign_id = projection["campaign_id"]
    scope = "World baseline" if campaign_id is None else f"Campaign: {campaign_id}"
    lines.append(f"  Scope: {scope}")
    m = projection["metrics"]
    lines.append(
        f"  Entities: {m['projected_entities']}  |  "
        f"Open conflicts: {m['open_conflicts']}  |  "
        f"Resolved: {m['resolved_conflicts']}"
    )
    lines.append("")

    for entity_id, entity_data in sorted(projection["entities"].items()):
        display = ENTITY_DISPLAY_NAMES.get(entity_id, entity_id)
        lines.append("-" * 70)
        lines.append(f"  {display}")
        lines.append("-" * 70)

        for attr, attr_data in sorted(entity_data["attributes"].items()):
            label = attr_data["value_label"] or "(no label)"
            layer = attr_data["source_layer"]
            campaign = attr_data.get("source_campaign_id")
            selected_id = attr_data["selected_fact_id"]
            truth = _get_fact_truth_state(selected_id, facts)

            attr_display = attr.replace("_", " ").title()
            lines.append(f"  {attr_display}:")
            lines.append(f"    {label}")
            layer_tag = f"layer={layer}, truth_state={truth}"
            if campaign:
                layer_tag += f", campaign={campaign}"
            lines.append(
                f"    [{layer_tag}, fact={selected_id}]"
            )

            if len(attr_data["fact_ids"]) > 1:
                lines.append(f"    competing facts: {attr_data['fact_ids']}")

            if attr_data["conflict_ids"]:
                lines.append(
                    f"    \u26a0 Conflicts: {', '.join(attr_data['conflict_ids'])}"
                )

            for eid in attr_data["provenance_evidence_ids"]:
                ev = evidence_by_id.get(eid)
                if ev:
                    section = " > ".join(ev.get("section_path", []))
                    session = ev.get("inferred_session")
                    session_tag = f", session {session}" if session else ""
                    lines.append(
                        f"    \u2190 {section} ({ev['document_title']}{session_tag})"
                    )

            lines.append("")

    if projection["conflicts"]:
        lines.append("-" * 70)
        lines.append("  CONFLICTS")
        lines.append("-" * 70)
        for conflict in projection["conflicts"]:
            status = conflict["status"].upper()
            lines.append(
                f"  [{status}] {conflict['conflict_id']}: "
                f"entity={conflict['entity_id']} attr={conflict['attribute']} "
                f"facts={conflict['fact_ids']}"
            )
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> int:
    evidence_units = load_json("evidence_units.json")
    facts = load_json("facts.json")
    conflicts = load_json("conflicts.json")
    canon_decisions = load_json("canon_decisions.json")

    # --- Schema validation ---
    print("Validating schemas...")
    try:
        validate_many(evidence_units, "evidence_unit.schema.json")
        print(f"  \u2713 {len(evidence_units)} evidence units valid")
    except Exception as e:
        print(f"  SCHEMA ERROR in evidence_units: {e}")
        return 1

    try:
        validate_many(facts, "fact.schema.json")
        print(f"  \u2713 {len(facts)} facts valid")
    except Exception as e:
        print(f"  SCHEMA ERROR in facts: {e}")
        return 1

    evidence_by_id = {eu["evidence_id"]: eu for eu in evidence_units}

    # --- Projection 1: World ---
    print("\n--- Projection 1: World (campaign_id=None) ---")
    world_projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=None,
    )
    print(render_projection(world_projection, evidence_by_id, facts, "WORLD PROJECTION"))

    # --- Projection 2: Campaign (all three layers) ---
    print(f"\n--- Projection 2: Campaign (campaign_id={CAMPAIGN_ID!r}) ---")
    campaign_projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=CAMPAIGN_ID,
    )
    print(
        render_projection(
            campaign_projection,
            evidence_by_id,
            facts,
            f"CAMPAIGN PROJECTION — {CAMPAIGN_ID} (canon + planning + play)",
        )
    )

    # --- Gate checks ---
    print("\n" + "=" * 70)
    print("  GATE CHECKS — Step 3")
    print("=" * 70)
    failures = 0

    # 1. World projection matches Step 1 output
    step1_path = OUTPUT_DIR / "world_projection.json"
    if step1_path.exists():
        with open(step1_path) as f:
            step1_output = json.load(f)
        if world_projection == step1_output:
            print("  \u2713 Gate 1: World projection identical to Step 1 output")
        else:
            print("  \u2717 Gate 1: World projection DIFFERS from Step 1 output")
            failures += 1
    else:
        print("  ? Gate 1: Step 1 output not found — skipping comparison")

    # 2. OBSERVED supersedes PREP for Shepherd's Flock operational_status
    sf_attrs = campaign_projection["entities"].get("ent_shepherds_flock", {}).get(
        "attributes", {}
    )
    sf_status = sf_attrs.get("operational_status", {})
    selected_status_fact = sf_status.get("selected_fact_id", "")
    selected_truth = _get_fact_truth_state(selected_status_fact, facts)
    if selected_truth == "OBSERVED":
        print(
            f"  \u2713 Gate 2: OBSERVED wins for Shepherd's Flock operational_status "
            f"(fact={selected_status_fact})"
        )
    else:
        print(
            f"  \u2717 Gate 2: Expected OBSERVED for Shepherd's Flock operational_status, "
            f"got {selected_truth} (fact={selected_status_fact})"
        )
        failures += 1

    # 3. Brother Ashwood is PREP-only — still in campaign, not in world
    ashwood_in_world = "ent_brother_ashwood" in world_projection["entities"]
    ashwood_in_campaign = "ent_brother_ashwood" in campaign_projection["entities"]
    if not ashwood_in_world and ashwood_in_campaign:
        ashwood_attrs = campaign_projection["entities"]["ent_brother_ashwood"]["attributes"]
        ashwood_truths = {
            attr: _get_fact_truth_state(data["selected_fact_id"], facts)
            for attr, data in ashwood_attrs.items()
        }
        all_prep = all(t == "PREP" for t in ashwood_truths.values())
        if all_prep:
            print(
                f"  \u2713 Gate 3: Brother Ashwood in campaign only, all facts PREP "
                f"({ashwood_truths})"
            )
        else:
            print(
                f"  \u2717 Gate 3: Brother Ashwood has non-PREP facts: {ashwood_truths}"
            )
            failures += 1
    else:
        print(
            f"  \u2717 Gate 3: Brother Ashwood: world={ashwood_in_world}, "
            f"campaign={ashwood_in_campaign}"
        )
        failures += 1

    # 4. The Shepherd appears only in campaign projection (play-discovered)
    shepherd_in_world = "ent_the_shepherd" in world_projection["entities"]
    shepherd_in_campaign = "ent_the_shepherd" in campaign_projection["entities"]
    if not shepherd_in_world and shepherd_in_campaign:
        shepherd_attrs = campaign_projection["entities"]["ent_the_shepherd"]["attributes"]
        shepherd_truths = {
            attr: _get_fact_truth_state(data["selected_fact_id"], facts)
            for attr, data in shepherd_attrs.items()
        }
        all_observed = all(t == "OBSERVED" for t in shepherd_truths.values())
        if all_observed:
            print(
                f"  \u2713 Gate 4: The Shepherd in campaign only, all facts OBSERVED "
                f"({shepherd_truths})"
            )
        else:
            print(
                f"  \u2717 Gate 4: The Shepherd has non-OBSERVED facts: {shepherd_truths}"
            )
            failures += 1
    else:
        print(
            f"  \u2717 Gate 4: The Shepherd: world={shepherd_in_world}, "
            f"campaign={shepherd_in_campaign}"
        )
        failures += 1

    # 5. Three truth_states visible in campaign projection
    all_truths_in_campaign: set[str] = set()
    for entity_data in campaign_projection["entities"].values():
        for attr_data in entity_data["attributes"].values():
            t = _get_fact_truth_state(attr_data["selected_fact_id"], facts)
            all_truths_in_campaign.add(t)
    expected_truths = {"CANON", "PREP", "OBSERVED"}
    if expected_truths.issubset(all_truths_in_campaign):
        print(
            f"  \u2713 Gate 5: All three truth_states present in campaign projection: "
            f"{sorted(all_truths_in_campaign)}"
        )
    else:
        print(
            f"  \u2717 Gate 5: Expected {expected_truths}, found {all_truths_in_campaign}"
        )
        failures += 1

    # 6. World projection has zero conflicts
    if world_projection["metrics"]["open_conflicts"] == 0:
        print("  \u2713 Gate 6: World projection has zero conflicts")
    else:
        print(
            f"  \u2717 Gate 6: World projection has "
            f"{world_projection['metrics']['open_conflicts']} unexpected conflicts"
        )
        failures += 1

    # 7. Shepherd's Flock operational_status has 3 competing facts in campaign
    sf_status_facts = sf_status.get("fact_ids", [])
    if len(sf_status_facts) == 3:
        fact_truths = [_get_fact_truth_state(fid, facts) for fid in sf_status_facts]
        print(
            f"  \u2713 Gate 7: Shepherd's Flock operational_status has 3 competing facts "
            f"({dict(zip(sf_status_facts, fact_truths))})"
        )
    else:
        print(
            f"  \u2717 Gate 7: Expected 3 competing facts for Shepherd's Flock "
            f"operational_status, got {len(sf_status_facts)}: {sf_status_facts}"
        )
        failures += 1

    print()
    if failures == 0:
        print("  ALL GATES PASSED — Step 3 complete")
    else:
        print(f"  {failures} GATE(S) FAILED")
    print("=" * 70)

    # --- Write outputs ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "world_projection_step3.json", "w") as f:
        json.dump(world_projection, f, indent=2)
    with open(OUTPUT_DIR / "campaign_projection_step3.json", "w") as f:
        json.dump(campaign_projection, f, indent=2)
    print(f"\nOutputs written to: {OUTPUT_DIR}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
