"""Step 1: Prove Canon Reads Right.

Loads hand-authored Mirathorn evidence + facts, runs them through the
canon projection reducer, validates schemas, and renders the projection
as a human-readable GM briefing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = Path(__file__).resolve().parent / "input"

sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.schema_validation import validate_many  # noqa: E402
from src.reducer.canon_projection import project_entity_state  # noqa: E402


ENTITY_DISPLAY_NAMES = {
    "ent_mirathorn": "Mirathorn (City)",
    "ent_shepherds_flock": "Shepherd's Flock (Faction)",
}


def load_json(name: str) -> list:
    path = INPUT_DIR / name
    with open(path) as f:
        return json.load(f)


def render_projection(projection: dict, evidence_by_id: dict) -> str:
    """Render the reducer projection as a GM-readable briefing."""
    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("  WORLD CANON PROJECTION — Mirathorn Vertical Slice")
    lines.append("=" * 70)
    lines.append("")

    campaign_id = projection["campaign_id"]
    lines.append(f"  Scope: {'World baseline' if campaign_id is None else f'Campaign: {campaign_id}'}")
    m = projection["metrics"]
    lines.append(f"  Entities: {m['projected_entities']}  |  "
                 f"Open conflicts: {m['open_conflicts']}  |  "
                 f"Resolved: {m['resolved_conflicts']}")
    lines.append("")

    for entity_id, entity_data in sorted(projection["entities"].items()):
        display = ENTITY_DISPLAY_NAMES.get(entity_id, entity_id)
        lines.append("-" * 70)
        lines.append(f"  {display}")
        lines.append("-" * 70)

        for attr, attr_data in sorted(entity_data["attributes"].items()):
            label = attr_data["value_label"] or "(no label)"
            layer = attr_data["source_layer"]
            evidence_ids = attr_data["provenance_evidence_ids"]

            attr_display = attr.replace("_", " ").title()
            lines.append(f"  {attr_display}:")
            lines.append(f"    {label}")
            lines.append(f"    [layer={layer}, fact={attr_data['selected_fact_id']}]")

            if attr_data["conflict_ids"]:
                lines.append(f"    ⚠ Conflicts: {', '.join(attr_data['conflict_ids'])}")

            for eid in evidence_ids:
                ev = evidence_by_id.get(eid)
                if ev:
                    section = " > ".join(ev.get("section_path", []))
                    lines.append(f"    ← {section} ({ev['document_title']})")

            lines.append("")

    if projection["conflicts"]:
        lines.append("-" * 70)
        lines.append("  CONFLICTS")
        lines.append("-" * 70)
        for conflict in projection["conflicts"]:
            status = conflict["status"].upper()
            lines.append(f"  [{status}] {conflict['conflict_id']}: "
                         f"entity={conflict['entity_id']} attr={conflict['attribute']} "
                         f"facts={conflict['fact_ids']}")
        lines.append("")

    lines.append("=" * 70)
    return "\n".join(lines)


def main() -> int:
    evidence_units = load_json("evidence_units.json")
    facts = load_json("facts.json")
    conflicts = load_json("conflicts.json")
    canon_decisions = load_json("canon_decisions.json")

    print("Validating schemas...")
    try:
        validate_many(evidence_units, "evidence_unit.schema.json")
        print(f"  ✓ {len(evidence_units)} evidence units valid")
    except Exception as e:
        print(f"  SCHEMA ERROR in evidence_units: {e}")
        return 1

    try:
        validate_many(facts, "fact.schema.json")
        print(f"  ✓ {len(facts)} facts valid")
    except Exception as e:
        print(f"  SCHEMA ERROR in facts: {e}")
        return 1

    evidence_by_id = {eu["evidence_id"]: eu for eu in evidence_units}

    print("\nRunning world projection (campaign_id=None)...")
    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=conflicts,
        canon_decisions=canon_decisions,
        campaign_id=None,
    )

    print()
    print(render_projection(projection, evidence_by_id))

    out_dir = Path(__file__).resolve().parent / "output"
    out_dir.mkdir(exist_ok=True)
    with open(out_dir / "world_projection.json", "w") as f:
        json.dump(projection, f, indent=2)
    print(f"\nRaw projection written to: {out_dir / 'world_projection.json'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
