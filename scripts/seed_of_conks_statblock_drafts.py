#!/usr/bin/env python3
"""Seed Of Conks threat mechanics as workbench StatblockDraftArtifact records.

Tree + Guardian: copied from gold Appendix A (do not LLM-generate).
Caretakers: bind published MM Twig Blight (MM 32) — not a new invented block.

Usage (API must be up on this worktree):
  uv run python scripts/seed_of_conks_statblock_drafts.py
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

API = "http://127.0.0.1:8000"

NOW = datetime.now(UTC).isoformat().replace("+00:00", "Z")

# Classic MM property-line markdown (same shape as workbench-generated corpus sheets).
GROTESQUE_TREE_MD = """# Grotesque Tree
*Huge plant, unaligned*

**Armor Class** 11 (natural armor)
**Hit Points** 39 (6d8+12)
**Speed** —

|STR|DEX|CON|INT|WIS|CHA|
|---:|---:|---:|---:|---:|---:|
|17 (+3)|9 (−1)|15 (+2)|7 (−2)|10 (+0)|10 (+0)|

**Damage Immunities** piercing
**Damage Resistances** bludgeoning
**Damage Vulnerabilities** fire
**Condition Immunities** charmed
**Senses** blindsight 600 ft. (blind beyond this radius), passive Perception 10
**Languages** —
**Challenge** 1 (200 XP)

## Actions
**Branch.** *Melee Weapon Attack:* +5 to hit, reach 60 ft., one target. *Hit:* 5 (1d4 + 3) slashing damage.
**Rock.** *Ranged Weapon Attack:* +1 to hit, range 30/120 ft., one target. *Hit:* 4 (1d6 + 1) bludgeoning damage.
**Snare.** When the grotesque tree hits a creature with its branch attack, it can use a bonus action to snare that creature. The creature must make a DC 13 Dexterity or Strength saving throw. On a failed save, the grotesque tree grapples the target and suspends it in mid air at a height of 20 ft. At the start of its turn, the grotesque tree can pull a grappled target 10 ft. closer to its stem. The grotesque tree can grapple two targets at a time.
**Sling.** The grotesque tree throws a creature that it has grappled 60 ft. away. The thrown creature must make a DC 13 Dexterity saving throw. On a failed save, the thrown creature takes 10 (3d6) bludgeoning damage, or half that amount on a successful save.

## Description
Attacks anyone within 30 feet; retaliates against ranged; nearest target; ceases when not threatened.
"""

GUARDIAN_MD = """# Guardian
*Large plant, unaligned*

**Armor Class** 11 (natural armor)
**Hit Points** 39 (6d6+18)
**Speed** 40 ft.

|STR|DEX|CON|INT|WIS|CHA|
|---:|---:|---:|---:|---:|---:|
|15 (+2)|12 (+1)|17 (+3)|10 (+0)|15 (+2)|10 (+0)|

**Saving Throws** Str +4, Con +5
**Skills** Perception +4
**Damage Vulnerabilities** fire
**Damage Resistances** piercing
**Condition Immunities** charmed
**Senses** darkvision 60 ft., passive Perception 14
**Languages** —
**Challenge** 1 (200 XP)

## Traits
**Limited Iron Spikes.** The guardian has four iron spikes. Used spikes regrow after a long rest.

## Actions
**Multiattack.** The guardian makes two melee attacks.
**Iron Spike.** *Melee Weapon Attack:* +4 to hit, reach 5 ft., one target. *Hit:* 5 (1d6 + 2) piercing damage. When the guardian hits a creature with its iron spike, it tries to pin it to the ground. The target must succeed on a DC 7 Dexterity saving throw or its movement speed is reduced to 0 and the spike is detached. At the start of its turn, the target can attempt a DC 10 Strength check to remove the spike and shake this effect.
**Adamantine Helix Barrage (Recharge 5–6).** Hundreds of fine adamantine needles shoot from the body of the guardian in every direction. All creatures in a 15 ft. radius around the guardian must make a DC 13 Dexterity saving throw. On a failed save, the creatures take 5 (1d10) piercing damage, or half as much on a successful one. Each time the guardian uses this feature, its AC is decreased by 1 until it finishes a long rest.
"""

# Published Monster Manual Twig Blight (MM 32) — bind for Caretakers; do not invent a new block.
TWIG_BLIGHT_MD = """# Caretakers (Twig Blight)
*Small plant, unaligned*

> Bind for Of Conks **Caretakers**: use this published Twig Blight sheet (MM 32). Do not invent a new caretaker statblock.
> Encounter: **20** total, roam in **groups of 5**. Afraid of fire. Strike hours after the surface tree dies.

**Armor Class** 13 (natural armor)
**Hit Points** 4 (1d6+1)
**Speed** 20 ft.

|STR|DEX|CON|INT|WIS|CHA|
|---:|---:|---:|---:|---:|---:|
|6 (−2)|13 (+1)|12 (+1)|4 (−3)|8 (−1)|3 (−4)|

**Skills** Stealth +3
**Damage Vulnerabilities** fire
**Condition Immunities** blinded, deafened
**Senses** blindsight 60 ft. (blind beyond this radius), passive Perception 9
**Languages** understands Common but can't speak
**Challenge** 1/8 (25 XP)

## Traits
**False Appearance.** While the twig blight remains motionless, it is indistinguishable from a dead shrub.

## Actions
**Claws.** *Melee Weapon Attack:* +3 to hit, reach 5 ft., one target. *Hit:* 3 (1d4 + 1) piercing damage.
"""


def _artifact(
    *,
    artifact_id: str,
    title: str,
    markdown: str,
    structured: dict[str, Any],
    combat_defaults: dict[str, Any],
    mode: str,
    note: str,
) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "draft_id": f"draft-{artifact_id}",
        "title": title,
        "markdown": markdown.strip() + "\n",
        "structured_statblock": structured,
        "combat_defaults": combat_defaults,
        "warnings": [],
        "provenance": {
            "mode": mode,
            "generator": "of_conks_gold_seed",
            "generated_at": NOW,
            "source_refs": [
                {
                    "source_type": "of_conks_gold",
                    "source_id": artifact_id,
                    "title": title,
                    "excerpt": note,
                }
            ],
            "generation_info": {
                "campaign_id": "of-conks-cons",
                "import_policy": note,
            },
        },
        "review_status": "approved",
        "lifecycle_state": "combat_ready",
        "storage_status": "not_stored",
        "corpus_status": "not_promoted",
        "source_refs": [
            {
                "source_type": "of_conks_gold",
                "source_id": artifact_id,
                "title": title,
                "excerpt": note,
            }
        ],
        "breadcrumbs": [
            {"label": "Of Conks & Cons", "source": "campaign:of-conks-cons"},
            {"label": "Hempholm one-shot", "source": "playable"},
        ],
        "created_by": "human",
        "created_at": NOW,
        "updated_at": NOW,
    }


DRAFTS: list[dict[str, Any]] = [
    _artifact(
        artifact_id="of-conks-grotesque-tree",
        title="Grotesque Tree",
        markdown=GROTESQUE_TREE_MD,
        structured={
            "name": "Grotesque Tree",
            "size": "Huge",
            "type": "plant",
            "alignment": "unaligned",
            "armor_class": 11,
            "hit_points": 39,
            "speed": "—",
            "challenge_rating": "1",
            "actions": [
                {"name": "Branch", "description": "+5 to hit, reach 60 ft., 5 (1d4+3) slashing"},
                {"name": "Rock", "description": "+1 to hit, range 30/120 ft., 4 (1d6+1) bludgeoning"},
                {"name": "Snare", "description": "Bonus after Branch; DC 13 grapple suspend"},
                {"name": "Sling", "description": "Throw grappled 60 ft.; DC 13 Dex, 10 (3d6) bludgeoning"},
            ],
        },
        combat_defaults={
            "name": "Grotesque Tree",
            "armor_class": 11,
            "hit_points": 39,
            "initiative_bonus": -1,
            "passive_perception": 10,
            "speed": "—",
            "speed_summary": "—",
            "senses_summary": "blindsight 600 ft. (blind beyond)",
            "primary_actions": ["Branch", "Rock", "Snare", "Sling"],
            "suggested_tactics": [
                "Attack anyone within 30 ft.",
                "Retaliate against ranged",
                "Nearest target; cease when not threatened",
            ],
        },
        mode="generate_from_source_statblock",
        note="copy_from_source_do_not_generate · Appendix A Grotesque Tree",
    ),
    _artifact(
        artifact_id="of-conks-guardian",
        title="Guardian",
        markdown=GUARDIAN_MD,
        structured={
            "name": "Guardian",
            "size": "Large",
            "type": "plant",
            "alignment": "unaligned",
            "armor_class": 11,
            "hit_points": 39,
            "speed": "40 ft.",
            "challenge_rating": "1",
            "actions": [
                {"name": "Multiattack", "description": "Two melee attacks"},
                {"name": "Iron Spike", "description": "+4 to hit, 5 (1d6+2) piercing; pin DC 7 Dex"},
                {
                    "name": "Adamantine Helix Barrage",
                    "description": "Recharge 5–6; 15 ft. radius DC 13 Dex; 5 (1d10) piercing; −1 AC",
                },
            ],
        },
        combat_defaults={
            "name": "Guardian",
            "armor_class": 11,
            "hit_points": 39,
            "initiative_bonus": 1,
            "passive_perception": 14,
            "speed": "40 ft.",
            "speed_summary": "40 ft.",
            "senses_summary": "darkvision 60 ft.",
            "primary_actions": ["Multiattack", "Iron Spike", "Adamantine Helix Barrage"],
            "suggested_tactics": [
                "Marrow fight with 2 caretakers",
                "Four iron spikes; pin on hit",
                "Helix Barrage lowers AC by 1 until long rest",
            ],
        },
        mode="generate_from_source_statblock",
        note="copy_from_source_do_not_generate · Appendix A Guardian",
    ),
    _artifact(
        artifact_id="of-conks-caretakers-twig-blight",
        title="Caretakers (Twig Blight)",
        markdown=TWIG_BLIGHT_MD,
        structured={
            "name": "Twig Blight",
            "size": "Small",
            "type": "plant",
            "alignment": "unaligned",
            "armor_class": 13,
            "hit_points": 4,
            "speed": "20 ft.",
            "challenge_rating": "1/8",
            "mm_reference": "twig blight (MM 32)",
            "encounter_quantity": 20,
            "encounter_group_size": 5,
            "actions": [
                {"name": "Claws", "description": "+3 to hit, reach 5 ft., 3 (1d4+1) piercing"},
            ],
        },
        combat_defaults={
            "name": "Caretaker (Twig Blight)",
            "armor_class": 13,
            "hit_points": 4,
            "initiative_bonus": 1,
            "passive_perception": 9,
            "speed": "20 ft.",
            "speed_summary": "20 ft.",
            "senses_summary": "blindsight 60 ft. (blind beyond)",
            "primary_actions": ["Claws"],
            "suggested_tactics": [
                "20 total in groups of 5",
                "Hours after surface tree dies",
                "Afraid of fire; flee after ~15 dead",
            ],
        },
        mode="generate_from_source_statblock",
        note="use_mm_twig_blight_do_not_invent · MM 32 bind for Caretakers",
    ),
]


def _post_draft(artifact: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps({"source": "workbench", "artifact": artifact}).encode("utf-8")
    req = urllib.request.Request(
        f"{API}/api/live/statblocks/workbench/drafts",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print(f"Seeding {len(DRAFTS)} Of Conks workbench statblock drafts via {API}")
    for artifact in DRAFTS:
        try:
            result = _post_draft(artifact)
        except urllib.error.URLError as exc:
            print(f"FAIL {artifact['artifact_id']}: {exc}")
            print("Is live-control API running on :8000 from this worktree?")
            return 1
        record = result.get("record") or {}
        print(
            f"OK {artifact['artifact_id']} → stored as {record.get('storage_path')} "
            f"(campaign={record.get('campaign_id')} session={record.get('session')})"
        )
    print("Open /statblocks — Of Conks drafts should appear under Workbench drafts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
