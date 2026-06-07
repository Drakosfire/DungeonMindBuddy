# C2S23 Mireward — Siege Mechanics + Threat Inventory

**Status:** Planning artifact. Not table canon until used or promoted.

**Branch anchor:** `cursor/c2s23-mireward-prep-ui`

**Purpose:** Capture the updated north-gate siege mechanics, cure-forward glassy-eye model, bardic escalation, harsh rest pressure, and the two new Mireward siege monsters now added to the Shepherd's Flock statblock hub.

---

## Locked decisions from operator

1. **Tripod Null-Calf appears on-screen** during the Mireward siege sequence.
2. **North gate is the focus** of the siege breaker pressure. If players are not challenged, the monster pressure may redirect toward the Bell / Shrine, tithe barn shelter, or ferry chain.
3. **Bardic music arrives when things get dire**: bagpipes out of the morning mist, not early casual counter-music.
4. **Glassy civilians are infected, dreaming, and receiving a signal.** They are not default enemies.
5. **The party / town can cure all glassy civilians** if they protect time, order, and cure logistics.
6. **Short rest pressure is harsh.** Rest is possible, but only with visible siege cost unless the town is stabilized.
7. **Monster docs should be flavorful and challenge-forward** so they can feed statblock generation and table use.
8. **Northbound exit readiness is intentionally deferred** for this slice.

---

## North-gate scene spine

The siege is now built around three simultaneous lanes:

| Lane | Pressure | Table question |
|---|---|---|
| **Gate Lane** | Meat flank, carts, rope lines, barricades, breach pressure | Can the party keep the north gate from becoming the enemy's tool? |
| **Cure Lane** | Glassy civilians, cure supplies, healers, spellcasters, blankets, names | Can the party save the infected without treating them as disposable? |
| **Signal Lane** | Wrong music, dream-receiver behavior, Tripod scouting, bagpipes | Can the party identify which sounds help and which sounds call the siege closer? |

The first fight should teach that killing monsters is only one piece of survival. A combat win without cure logistics leaves the town vulnerable. A cure plan without gate discipline gets interrupted. Music is risky until the bagpipes establish a human counter-rhythm.

---

## Glassy civilians — cure-forward model

**Truth:** The glassy civilians are infected, dreaming, and receiving a signal. They can be cured. The moral pressure is not *who must be killed?* but *can the town protect the cure process while under attack?*

Use a single **Cure Line** clock instead of tracking every civilian individually.

| Cure Line tick | State |
|---:|---|
| 0 | Glassy and clear-eyed refugees are mixed together; cure is possible but not organized. |
| 1 | Clear-eyed and glassy refugees are separated without violence. |
| 2 | First cure method is confirmed to work; someone wakes up and panic drops. |
| 3 | Cure station exists: supplies, helpers, water, restraints, blankets, names. |
| 4 | Most glassy civilians are stabilized; they no longer drift north unless the signal spikes. |
| 5 | All reachable glassy civilians are being cured in batches. |
| 6 | Everyone in the column is cured or safely recovering. Remaining horror is memory, exhaustion, and what the signal revealed. |

**Valid levers:** Medicine, Arcana, Religion, Survival, Persuasion, healing magic, anti-curse work, bardic stabilization, gentle restraint, water / blankets / name lists, trusted NPC organization.

**Failure does not mean cure is impossible.** It means the cure line is interrupted. Pick one:

- A glassy cluster starts walking north.
- A family member breaks quarantine to hold someone.
- The wrong rhythm spreads through the line.
- A cure station helper is dragged, charmed, or panicked.
- The Tripod Null-Calf observes the cure line and learns it matters.

---

## Bardic music — bagpipes out of the morning mist

Early music is dangerous. Mireward is full of festival performers, wrong verses, remembered Dustwalker rhythm, and scared helpers. Bardic counter-music should not be a casual first-round solution.

Trigger the bagpipes when at least two are true:

- Breach pressure is 5+.
- Panic is 5+.
- Cure Line is stalled at 3 or lower.
- The Tripod Null-Calf has appeared.
- A PC or beloved NPC is down.
- The party tries to short rest before the town is stable.
- The north gate is a physical scrum of cart, flesh, mud, and screaming.

**Arrival beat:** One impossible low drone rolls out of the morning mist and is almost mistaken for the wrong signal. A second pipe answers, sharp and human. Drums enter badly out of time, then find a marching pulse that does **not** match the wrong hymn.

**Table effect when bagpipes arrive:**

- Panic clock drops by 1 immediately.
- Cure Line may advance once if players protect the rhythm for one round.
- Glassy civilians stop walking north for one round and instead weep, vomit black water, or whisper their own names.
- The enemy reacts violently; the bagpipes become a target, not a free rescue.

---

## Harsh short-rest pressure

Short rests are allowed, but the siege keeps moving.

| Rest state | Cost |
|---|---|
| **Before Cure Line 4** | Two clocks advance: breach, panic, sleeper signal, or supply strain. Add a visible cost such as a barricade break, relapse, helper death, Tripod mark, or bagpipes arriving under worse conditions. |
| **After Cure Line 4 but before gate secure** | One clock advances. One NPC ally becomes unavailable afterward because they covered the party's downtime. |
| **After Cure Line 6 and gate held** | Safe enough, not comfortable. Rest in mud, blood, blankets, pipe-drone echoes, and exhausted cured civilians asking what happened while they were dreaming. |

---

## Threat ladder update

| Wave | Trigger | Threats | Goal |
|---|---|---|---|
| **0 — Refugees / uncertainty** | Brin and the 55 hit the north apron | Glassy civilians, bad counts, cure-line pressure | Teach the civic problem before monster pressure. |
| **1 — Meat flank** | 3-8 minute road clock | Sewer Meat Creature, Corrupted Meat Golem, Meat Worm, Aberrant Meatwing | Teach gate congestion, breach, poison/sludge, cart pressure. |
| **2 — Cure disruption / sleeper signal** | Wrong rhythm, violent quarantine, cure line exposed | Glassy clusters, optional hidden signaler | Make curing possible but costly under pressure. |
| **3 — Tripod reveal** | Gate/cure system starts to work, or first wave is beaten | **Tripod Null-Calf** | Show the siege is learning geometry, gates, and cure priorities. |
| **4 — Later siege breaker** | Later wave, short-rest cost, or escalation | **Latch-Harrow** | Make the north gate itself the monster's target. |

---

## Added statblock documents

| Monster | Path | CR | Role | Session use |
|---|---|---:|---|---|
| **Tripod Null-Calf** | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/tripod_null_calf_statblock_cr5.md` | 5 | Large three-limbed alien scout / geometry-breaker | Appears on-screen; can mark the north gate for later siege pressure. |
| **Latch-Harrow** | `corpus/eldyrwild-markdown/Elderwyld/Shephards Flock/Statblocks and Tokens/latch_harrow_statblock_cr8.md` | 8 | Huge siege breaker / breach-clock monster | Later-wave north-gate crisis; can redirect if players are not challenged. |

The Shepherd's Flock statblock hub has been updated to index both documents.

---

## Tripod Null-Calf table handling

Use the Tripod as a **scout with alien priorities**, not a boss. It should pin a cart, mark a gate brace, lift a glassy civilian, or study the cure line. If it is badly damaged, it should withdraw or leave behind a mark rather than fight to the death.

**Play expectation:** It should challenge party tactics by breaking assumptions about facing, flanking, and defensive lines. Its three limbs matter because it can anchor, pin, rotate, and touch multiple pressure points at once.

**Strong counterplay:** Disable a limb, remove reflections, separate it from the gate, break its anchor object, or force it to choose between preserving its mark and surviving.

---

## Latch-Harrow table handling

Use the Latch-Harrow as a **clock monster**. Put the north gate Breach Clock in front of the table.

- At **4 breach**, the north gate is compromised.
- At **8 breach**, the north gate fails / is destroyed.
- Tripod's **Mark the Gate** should make the Latch-Harrow's arrival feel earned: the siege learned where Mireward was weak.

**Play expectation:** The monster should be hard enough that simply dogpiling it is not obviously optimal. It should pressure helpers, cure work, braces, and gate repairs. Players can win by killing it, delaying it, redirecting it, or preserving the gate long enough for the town to adapt.

**Escalation lever:** If the party dominates, it redirects from the north gate toward the Bell / Shrine, tithe barn shelter, or ferry chain. This keeps the north gate as the focus while preserving a challenge dial.

---

## Remaining small decisions

- Decide exact cure method language at table: magic, medicine, song, purge, named recognition, or combined ritual.
- Decide who first hears the bagpipes: Stafl, Lysandra, Thrin, or a cured civilian.
- Decide whether the Tripod flees by reflection, mud, wall-crawl, or simply impossible geometry.
- Decide if the Latch-Harrow appears in Session 23 or is held as the visible next-wave cliffhanger.
