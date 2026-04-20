---
title: "Juvenile Geomantic Drake — statblock seed (generator drop-in)"
document_class: world
canon_layer: world
campaign_id: null
temporal_scope: evergreen
session: null
origin_session: null
last_updated_session: null
source_class: seed_reference
table_note: "Pairs with `pre_era_conical_hills_d20_find.md` entry 15. JSON block is structured for ingestion; trim keys your generator does not use."
---

# Juvenile Geomantic Drake

Draconic-adjacent **monstrosity** bred (or evolved) to **ride** and **dump** excess **geomantic** charge through **molting** and **nesting** on **conical** high points, **wells**, and **ward anchors**. True dragons find them **beneath notice**; scholars argue whether they are **pre-era** **bioservitors**, **fey** experiments, or **natural** parasites on old magic.

---

## Read-aloud

A **knot** of **muscle** and **shimmer** the size of a **big dog**, low to the ground like a **monitor lizard** wearing **storm-light**. Its scales are **thin plates** — **oil-slick** blue-green one moment, **bone** matte the next — each edge **too regular** to be wild. Heat **radiates** from them as if the creature were a **stone** left in noon sun. Its eyes are **milky** with **flecks** that track **nothing** you can see, and its breath smells like **ozone** and **wet clay**. When it **scratches** earth, the dirt **rings** faintly, like tapping a **hollow** pot.

---

## Behavior and encounter design

- **Activity (time of day):** **Crepuscular** by default — **dawn** and **dusk** are peak movement, **foraging**, and **nest repair**. **Midday** often finds them **dozing** in **sun-warmed** scrapes (still **alert** to vibrations). **Night** is **quiet** unless **storms**, **thunder**, or **spellcasting** nearby **wakes** them (feeds **Capacitance**). Adjust if your region has **weird** sun/magic (e.g. **owl**-shifted valley).
- **Default stance:** **Territorial** around a **nest** or **charge sink**, not **hungry** for a TPK. It **postures**, **hisses**, and **spits** to **push** intruders **downslope**; it **fights** hard if the nest is **disturbed** or if it is **cornered** on **“its”** cone.
- **Geomantic hunger:** It is **drawn** to **buried workings** like a moth to **heat**. On a **pre-era** hill it may be **drowsy** and **friendly** until someone **pries** at the **wrong** stone.
- **Loot:** **Shed scales** (1d4 useful as **arcane focus** components or **50 gp** alchemical bundles if sold to the right buyer); **no** automatic hoard. **Eggshell** chips are **interesting**, not **valuable**, unless your table wants a **fey** **debt**.

---

## Fun mechanics summary (for the table)

| Hook | Effect |
|------|--------|
| **Grounded power** | On **engineered** or **warded** earth, the drake **grounds** lightning/thunder — see **Geomantic Grounding**. |
| **Spell snack** | Nearby casting **feeds** it — see **Capacitance**. |
| **Slope fight** | High ground on a **cone** makes it **slippery** — see **Coneborn**. |
| **Oh no it molted** | At **bloodied**, it **sheds** — see **Molt Surge** reaction. |

---

## JSON — paste into statblock generator

*Adjust **challenge_rating**, **hit_points**, and DCs for party tier. Juvenile default **CR 2**.*

```json
{
  "name": "Juvenile Geomantic Drake",
  "size": "Small",
  "type": "monstrosity",
  "subtype": "geomantic",
  "alignment": "typically neutral",
  "armor_class": 15,
  "armor_desc": "natural armor",
  "hit_points": 27,
  "hit_dice": "6d6 + 6",
  "speed": {
    "walk": 30,
    "climb": 30
  },
  "abilities": {
    "str": 10,
    "dex": 18,
    "con": 14,
    "int": 5,
    "wis": 14,
    "cha": 8
  },
  "saving_throws": {
    "dex": 6,
    "wis": 4
  },
  "skills": {
    "perception": 4,
    "stealth": 6,
    "survival": 4
  },
  "damage_resistances": "",
  "damage_immunities": "",
  "condition_immunities": "",
  "senses": {
    "darkvision": 60,
    "passive_perception": 14
  },
  "languages": "understands Draconic and Primordial (Terran) but can't speak",
  "challenge_rating": 2,
  "xp": 450,
  "traits": [
    {
      "name": "Geomantic Grounding",
      "desc": "While the drake is in contact with earth that conceals pre-era stonework, a buried ward, a conduit, or similar worked geomancy (GM discretion), it has resistance to lightning and thunder damage. In addition, it has advantage on saving throws against being knocked prone if the source of the effect is touching the ground."
    },
    {
      "name": "Capacitance",
      "desc": "Whenever a creature casts a spell of 1st level or higher within 15 feet of the drake, the drake gains 5 temporary hit points after the spell is cast (no action required). It can gain temporary hit points from this trait only once per round."
    },
    {
      "name": "Coneborn",
      "desc": "Difficult terrain composed of earth, loose rock, or mud doesn't cost the drake extra movement if the terrain is on a slope of 30 degrees or steeper (such as the flank of a conical hill)."
    }
  ],
  "actions": [
    {
      "name": "Multiattack",
      "desc": "The drake makes two attacks: one with its bite and one with its flux tail."
    },
    {
      "name": "Bite",
      "desc": "Melee Weapon Attack: +6 to hit, reach 5 ft., one target. Hit: 7 (1d6 + 4) piercing damage plus 3 (1d6) thunder damage if the drake currently has at least 1 temporary hit point from Capacitance; otherwise the bite deals piercing damage only."
    },
    {
      "name": "Flux Tail",
      "desc": "Melee Weapon Attack: +6 to hit, reach 5 ft., one target. Hit: 6 (1d4 + 4) bludgeoning damage, and the target must succeed on a DC 12 Strength saving throw or be pushed 5 feet straight away from the drake (directly downslope if both creatures are on a slope)."
    },
    {
      "name": "Spit Flux (Recharge 5-6)",
      "desc": "The drake expectorates a charged pellet at a point it can see within 30 feet. Each creature within 5 feet of that point must make a DC 12 Dexterity saving throw, taking 9 (2d8) force damage on a failed save, or half as much on a successful one. A creature that fails the save also cannot take reactions until the start of the drake's next turn as harmonic vibration rattles its joints."
    }
  ],
  "reactions": [
    {
      "name": "Molt Surge (1/Day)",
      "desc": "When the drake is reduced to half its hit points or fewer, it can use its reaction to shed a cloud of hot scales in a 10-foot radius centered on itself. The area becomes difficult terrain until cleared. Each creature in the area other than the drake must succeed on a DC 12 Dexterity saving throw or be blinded until the end of its next turn."
    }
  ]
}
```

---

## Scaling notes (optional)

- **Chick / CR 0–1:** Drop **Multiattack**; **Spit Flux** becomes **recharge 6** only; **Capacitance** grants **3** temp HP.
- **Adult / CR 5–7:** Medium size; increase HP and damage dice; **Molt Surge** **recharges** on **5-6**; add **legendary** **resistance** **1/day** if you want it as a **boss** on a **triad** of cones.

---

## Related

- Nest discovery table: `Elderwyld/Wilderness/pre_era_conical_hills_d20_find.md` (entry **15**)
- Nest **loot (d100)**: `Elderwyld/Wilderness/geomantic_drake_nest_loot_d100.md`
- Travel context: `Longmont Campaign/Campaign 2/Journey - Mireward Reach (Campaign 2).md`
- **Night camp** d100 (drakes appear in the **[E]** events): `Elderwyld/Wilderness/conical_hills_night_camp_d100.md`
