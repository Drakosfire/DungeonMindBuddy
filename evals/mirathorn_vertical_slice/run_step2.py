"""Step 2: Prove the Planning Layer Boundary.

Runs two projections from the same fixture set:
  1. World projection (campaign_id=None) — must match Step 1 output exactly.
  2. Campaign projection (campaign_id="longmont_01") — world canon + planning overlay.

Verifies:
  - World projection is unchanged from Step 1.
  - Campaign projection adds planning facts without mutating world canon.
  - At least one conflict detected (world vs. planning operational_status).
  - New entity (Brother Ashwood) appears only in campaign projection.
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
    "ent_brother_ashwood": "Brother Ashwood (NPC)",
}


def load_json(name: str) -> list:
    path = INPUT_DIR / name
    with open(path) as f:
        return json.load(f)


def render_projection(projection: dict, evidence_by_id: dict, title: str) -> str:
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

            attr_display = attr.replace("_", " ").title()
            lines.append(f"  {attr_display}:")
            lines.append(f"    {label}")
            layer_tag = f"layer={layer}"
            if campaign:
                layer_tag += f", campaign={campaign}"
            lines.append(f"    [{layer_tag}, fact={attr_data['selected_fact_id']}]")

            if attr_data["conflict_ids"]:
                lines.append(
                    f"    \u26a0 Conflicts: {', '.join(attr_data['conflict_ids'])}"
                )

            for eid in attr_data["provenance_evidence_ids"]:
                ev = evidence_by_id.get(eid)
                if ev:
                    section = " > ".join(ev.get("section_path", []))
                    lines.append(f"    \u2190 {section} ({ev['document_title']})")

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

    # --- Projection 1: World (campaign_id=None) ---
    print("\n--- Projection 1: World (campaign_id=None) ---")
    world_projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=None,
    )
    print(render_projection(world_projection, evidence_by_id, "WORLD PROJECTION"))

    # --- Projection 2: Campaign ---
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
            f"CAMPAIGN PROJECTION — {CAMPAIGN_ID}",
        )
    )

    # --- Gate checks ---
    print("\n" + "=" * 70)
    print("  GATE CHECKS")
    print("=" * 70)
    failures = 0

    # 1. World projection matches Step 1 output
    step1_path = OUTPUT_DIR / "world_projection.json"
    if step1_path.exists():
        with open(step1_path) as f:
            step1_output = json.load(f)
        if world_projection == step1_output:
            print("  \u2713 World projection identical to Step 1 output")
        else:
            print("  \u2717 World projection DIFFERS from Step 1 output")
            world_entities = set(world_projection["entities"].keys())
            step1_entities = set(step1_output["entities"].keys())
            if world_entities != step1_entities:
                print(f"    Entity diff: added={world_entities - step1_entities}, "
                      f"removed={step1_entities - world_entities}")
            for eid in world_entities & step1_entities:
                w_attrs = world_projection["entities"][eid]["attributes"]
                s_attrs = step1_output["entities"][eid]["attributes"]
                if w_attrs != s_attrs:
                    print(f"    Entity {eid} attributes differ")
            failures += 1
    else:
        print("  ? Step 1 output not found — skipping comparison")

    # 2. Campaign projection includes world + planning facts
    campaign_entities = set(campaign_projection["entities"].keys())
    world_entities = set(world_projection["entities"].keys())
    if world_entities.issubset(campaign_entities):
        print("  \u2713 Campaign projection includes all world canon entities")
    else:
        missing = world_entities - campaign_entities
        print(f"  \u2717 Campaign projection missing world entities: {missing}")
        failures += 1

    # 3. At least one conflict detected
    campaign_conflicts = campaign_projection["conflicts"]
    sf_conflicts = [
        c for c in campaign_conflicts
        if c["entity_id"] == "ent_shepherds_flock"
        and c["attribute"] == "operational_status"
    ]
    if sf_conflicts:
        print(
            f"  \u2713 Conflict detected for Shepherd's Flock operational_status: "
            f"{sf_conflicts[0]['conflict_id']} "
            f"(facts: {sf_conflicts[0]['fact_ids']})"
        )
    else:
        print("  \u2717 No conflict detected for Shepherd's Flock operational_status")
        failures += 1

    # 4. Brother Ashwood only in campaign projection
    ashwood_in_world = "ent_brother_ashwood" in world_projection["entities"]
    ashwood_in_campaign = "ent_brother_ashwood" in campaign_projection["entities"]
    if not ashwood_in_world and ashwood_in_campaign:
        print("  \u2713 Brother Ashwood appears only in campaign projection")
    else:
        print(
            f"  \u2717 Brother Ashwood: world={ashwood_in_world}, "
            f"campaign={ashwood_in_campaign}"
        )
        failures += 1

    # 5. World projection has no conflicts (unchanged from step 1)
    if world_projection["metrics"]["open_conflicts"] == 0:
        print("  \u2713 World projection has zero conflicts")
    else:
        print(
            f"  \u2717 World projection has {world_projection['metrics']['open_conflicts']} "
            f"unexpected conflicts"
        )
        failures += 1

    print()
    if failures == 0:
        print("  ALL GATES PASSED")
    else:
        print(f"  {failures} GATE(S) FAILED")
    print("=" * 70)

    # --- Write outputs ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    with open(OUTPUT_DIR / "world_projection_step2.json", "w") as f:
        json.dump(world_projection, f, indent=2)
    with open(OUTPUT_DIR / "campaign_projection.json", "w") as f:
        json.dump(campaign_projection, f, indent=2)
    print(f"\nOutputs written to: {OUTPUT_DIR}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
