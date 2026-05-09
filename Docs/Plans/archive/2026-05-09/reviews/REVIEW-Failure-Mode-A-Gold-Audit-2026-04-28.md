# Failure mode A — Gold-quality audit (whole-party spread vs narrow cast)

**Date:** 2026-04-28  
**Scope:** Verify whether the gold for the "roster-copy / multi-PC" failures in `scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json` is giving the model **clean** signals, **mixed** signals, or **incorrect** signals.  
**Method:** Read each must-route row in the gold against the actual recap line, then against the routing prompt's rules. Distinguish gold-design intent from model performance.

---

## 0. What the gold is being asked to enforce (one sentence each)

- **Hub manifest (PCs):** `baergrom`, `bonogo`, `caelynn`, `ephanna`, `karsemine`, `stafl` — six PC hubs (`evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json` lines 10–53).
- **Party labels in scope:** "Questionable Company" (only entry in `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json`).
- **Prompt's roster-copy rule (rule 4):** when a unit names the party label as the acting band, `assigned_hubs` MUST equal the full manifest **even when some PCs are not named in the recap text** (`evals/sentence_routing_retrieval_falsification/routing_prompt.py` lines 89–97; final self-check lines 122–123).
- **Prompt's group-without-party rule (rule 5):** "the group / the team / our team / teammates" used as joint subject of movement, fight, or shared decision triggers full-roster expansion; ambient framing does not.
- **Prompt's narrow-multi-PC rule (rule 3):** when two or three PCs each have a clear in-unit role, assign exactly those PCs and no others.

So the gold must satisfy two opposing rules simultaneously, and each unit gets adjudicated to **one** of them. The audit below asks: is each adjudication clean, defensible-but-borderline, or incorrect?

---

## 1. Structural concerns about the recap vs. manifest

Two structural facts shape every roster-copy adjudication:

### 1a. Baergrom is in the manifest but not in the recap text

`grep -c '[Bb]aergrom' Session 20 - Recap.md` → **0**.

Baergrom's own timeline acknowledges this gap: "Sessions … 18–20: present in recaps / Caelynn mirror; not yet rowed here." (`corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/timeline.md` line 32 — "Backfill TODO".)

This is **intentional gold design** in concert with the prompt: rule 4's last sentence says "do not abstain from a roster-copy unit just because one roster member is not named in the recap prose." But it means **every roster-copy row in this scenario is testing the same skill**: will the model trust the manifest over the text?

### 1b. Thrin is named in the recap but is not in the manifest

`grep '[Tt]hrin' Session 20 - Recap.md` finds **4 occurrences** (lines 14, 16, 30 — battle scene, watch detail, "Ephanna keeping a close eye on Thrin").

Thrin is correctly classified as an NPC: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md` declares `subject_class: npc`. So leaving him out of the PC manifest is correct.

But narratively the model sees a recap where the active band reads as "Ephanna, Karesmine, Caelynn, Thrin, Bonogo, Stafl" — five PCs and one NPC who acts. There is **no textual cue** that Baergrom belongs to "the group". Combined with 1a, this means the model has to override **both** "the recap names this party as 5 PCs" **and** "the named 6th party member is an NPC, not a PC" to satisfy roster-copy gold.

This is not a gold bug. It is a **hard ask** that consistently lands as the dominant failure (`u-L0026-06`/`u-L0030-03` recurrences in the cohorts cited in `Docs/Plans/archive/2026-05-09/reviews/REVIEW-Sentence-Hub-Routing-Failure-Modes-2026-04-28.md` §2).

---

## 2. Row-by-row audit (must-route rows in this scenario)

Cross-check format: `unit_id` → recap text → gold expected → which prompt rule applies → verdict (clean / borderline / incorrect).

### Row 1 — `u-L0024-07` (narrow multi-PC)

> "Marla then grapples Bonogo and is about to do much worse when Caelynn comes to the rescue."

- **Gold:** `[bonogo, caelynn]`, `max_extra_hubs=0`.
- **Rule:** prompt rule 3 (narrow multi-PC, distinct in-unit roles).
- **Textual evidence:** Bonogo = grappled (object/locus); Caelynn = rescuer (actor). Both explicit.
- **Verdict: CLEAN.** Defensible without interpretation; matches the strict-prompt counter-example baked into `_NARROW_MULTI_PC_GUARD` verbatim (`routing_prompt.py` lines 28–30).

### Row 2 — `u-L0026-06` (narrow multi-PC, 3 PCs)

> "Marla approaches Caelynn and asks her how she should deal with Bonogo, but Ephanna quickly intervenes, letting her, and the town, know that the Questionable Company is leaving town to continue their journey."

- **Gold:** `[caelynn, bonogo, ephanna]`, `max_extra_hubs=0`.
- **Rule:** prompt rule 3 (narrow multi-PC). Note the unit also contains the party label "Questionable Company" — but rule 4's roster-copy is gated on "acting/deciding/resting/watching/preparing/moving band"; here the party is the **subject of reported speech**, not actively doing the verb. Rule 6 explicitly says "reported speech about the party without joint action uses only rule 3 roles".
- **Textual evidence:**
  - Caelynn = direct addressee of Marla's question. ✓
  - Ephanna = actor (intervenes). ✓
  - Bonogo = **decision topic** ("how she should deal with Bonogo"). Rule 3's "object/locus" examples are physical (struck/grappled/enveloped/rescued) plus "directly addressed as the decision point". Bonogo is the decision **about whom**, not the decision **point** in a strict reading.
- **Verdict: BORDERLINE.** The Caelynn + Ephanna pair is clean. The Bonogo slot is a defensible but **interpretive** stretch of "decision point" — a narrow reader of rule 3 would assign `[caelynn, ephanna]` and treat Bonogo as background continuity that belongs on the *next* unit (where Bonogo actually appears as actor or object).
- **Why this matters for the failure pattern:** the cohort summaries record `u-L0026-06` as the most recurrent miss (5/5 misses across both prompt variants per `Docs/Plans/archive/2026-05-09/reviews/REVIEW-Sentence-Hub-Routing-Failure-Modes-2026-04-28.md` §2). The model dropping **Bonogo** specifically is consistent with a strict reading of rule 3, not arbitrary noise.

### Row 3 — `u-L0022-01` (roster-copy + named PC inside same unit)

> "As the group approaches the preparations happening in the field, they find Stafl singing and directing the workers from a makeshift throne of barrels on the back of a wagon."

- **Gold:** all 6 PCs, `max_extra_hubs=0`.
- **Rule:** prompt rule 5 ("the group" + joint movement) **plus** Stafl named as object/locus of "find".
- **Textual evidence:** "the group approaches" → joint movement → roster-copy. "they find Stafl" → Stafl is in object position.
- **Verdict: CLEAN, but mixed-signal at the rule level.** Two rules both fire; gold picks the broader (roster). A strict-rule-3 reader could land on `[stafl]` only. The gold's choice is correct per rule precedence, but the unit is a **stress test** of "rule 5 outranks rule 3 when both apply".
- **Note on the Baergrom problem:** this row triggers it: rule 4/5 says copy the manifest, manifest contains baergrom, recap contains 0 baergrom mentions, model is asked to add him on faith.

### Row 4 — `u-L0026-03` (roster-copy by carryover; focal subject is scenery)

> "Immediately they can all see the trees pull back and then start to turn to the east, away from the town."

- **Gold:** all 6 PCs, `max_extra_hubs=0`.
- **Context (from the prior unit `u-L0026-01`):** "Questionable Company, along with the townsfolk, watch as the forest comes within range of their plan."
- **Rule:** prompt rule 5 ("they" carries from prior-unit "Questionable Company") + rule 7 (one-hop pronoun binding) — though rule 7 caps at one carried slug, so the binding here has to come from rule 5's "the group" / party-label scope, not rule 7.
- **Textual evidence problem:** the focal subject of *this* unit is **the trees** (event/location), not the PCs. The PCs are passive observers. Per rule 5: "Abstain when group/team wording is only vague framing and no PC has a role from rule 3." A strict reader would call this "the group passively perceives a scenery state change" → either narrow assign or `event_or_object_placeholder`.
- **Verdict: BORDERLINE.** Defensible as roster-copy *if* you read "they can all see X happen" as a shared experiential beat the GM wants on every PC's hub timeline (so the next session, any PC's hub recall returns "we watched the forest turn"). But the unit is **not** about a band action; it's about the world reacting. Choosing roster-copy here makes the "passive observation by the group counts as roster-copy" rule active for the rest of this scenario.

### Row 5 — `u-L0030-03` (roster-copy by carryover; focal subject is an object set)

> "Thirty minutes later they come across an unusual sight: a wagon partly unloaded and horses wandering around a stack of crates."

- **Gold:** all 6 PCs, `max_extra_hubs=0`.
- **Context (from prior `u-L0030-01`):** "The group sets off from the town, Ephanna keeping a close eye on Thrin."
- **Rule:** rule 5 ("the group" → "they come across") for joint movement.
- **Textual evidence problem:** "come across an unusual sight" is the main verb, but the **content** of the sight (wagon/horses/crates) is the focal subject. This is *more* clearly a "find scenery during travel" beat than `u-L0026-03`. Rule 5 covers this — joint movement ("come across") with the band as subject.
- **Verdict: CLEAN-LEANING.** Better evidence for roster-copy than `u-L0026-03` because "come across" is genuinely a joint-movement verb, not a passive perception. A model-side narrow reader could still call it scenery framing and abstain — but the gold is on solid ground.
- **Note:** still triggers the Baergrom-on-faith ask.

---

## 3. Summary verdict

| Row | Gold expectation | Rule applied | Audit verdict | Why model fails |
|---|---|---|---|---|
| `u-L0024-07` | `[bonogo, caelynn]` | rule 3 narrow multi-PC | **CLEAN** | Should pass; if it fails, it's a model bug, not gold. |
| `u-L0026-06` | `[caelynn, bonogo, ephanna]` | rule 3 narrow multi-PC | **BORDERLINE** | Bonogo as "decision topic" stretches rule 3's "object/locus". A strict reader gets `[caelynn, ephanna]` and is internally consistent. |
| `u-L0022-01` | full roster (6) | rules 4/5 outrank rule 3 | **CLEAN, mixed-rule** | Tests rule 5 > rule 3; also requires Baergrom-on-faith. |
| `u-L0026-03` | full roster (6) | rule 5 by carryover | **BORDERLINE** | Focal subject is scenery (the trees), PCs are passive observers; rule 5's own "abstain on vague framing" carve-out can defensibly apply. Plus Baergrom-on-faith. |
| `u-L0030-03` | full roster (6) | rule 5 ("come across") | **CLEAN-LEANING** | Joint-movement verb is genuine; still requires Baergrom-on-faith. |

**Mixed/incorrect signal?** The gold is **not** giving incorrect signals. It is internally consistent with the routing prompt, with one **interpretively borderline** narrow-multi-PC row (`u-L0026-06`) and one **interpretively borderline** carryover roster-copy row (`u-L0026-03`).

But the gold is testing **two genuinely hard things at once** in this scenario:

1. **"Trust the manifest over the text"** — every roster-copy row depends on the model adding Baergrom from the manifest with zero textual support. This is one rule, repeated three times, dressed as three different rows.
2. **Where rule 3 ends and rule 5 begins** — `u-L0026-06` (narrow), `u-L0026-03` (carryover-broad), `u-L0030-03` (carryover-broad), `u-L0022-01` (mixed-but-broad). The model is asked to navigate this boundary on rows where the textual evidence does not unambiguously point to one rule.

So the answer to "is the gold giving us mixed signals?" is:

- **Within a single row:** mostly clean. Two rows (`u-L0026-06`, `u-L0026-03`) are borderline-but-defensible.
- **Across the scenario:** the scenario bundles two distinct skills (Baergrom-on-faith + rule-3-vs-rule-5 boundary judgment) into one pass/fail gate. A run that **succeeds at narrow-PC discrimination** but **fails at roster-faith** counts the same as one that **succeeds at roster-faith** but **drops a multi-PC slot**. The headline pass-rate (0/5) does not distinguish those failure shapes.

---

## 4. Recommendations before more prompt or model work

These are **gold-side** recommendations only — the question was about gold quality. Anything prompt-side is out of scope for this audit.

1. **Disambiguate `u-L0026-06` Bonogo intent.** Decide explicitly: should Bonogo's hub timeline retrieve "Marla asked how to deal with Bonogo"? If yes, document in `scenario_notes` that "decision topic" satisfies rule 3's object/locus; consider a parallel rule-3 example in the prompt. If no, change gold to `[caelynn, ephanna]` and add a `scenario_notes` line. Current 5/5 misses are a strong "the model isn't reading rule 3 the way the gold writer is" signal.
2. **Disambiguate `u-L0026-03` "they can all see" intent.** Either (a) keep as roster-copy and document explicitly that "passive shared perception of a world-state change" is a rule-5 trigger (and add an example to the prompt), or (b) change to abstain / `event_or_object_placeholder` and treat the trees-turning beat as scenery the model legitimately abstains from.
3. **Split the Baergrom-on-faith test into its own narrow scenario.** Rather than embedding it in three different roster-copy rows in a mixed scenario, build a small slice (3–4 units, all unambiguous "the group / Questionable Company moves/decides/rests" rows) and measure how often the model copies the manifest with no textual support. That moves the variable into a controlled gate; right now it's tangled with rule-3-vs-rule-5 evidence.
4. **Add `scenario_notes` rationale to the gold file** for any row where a rule choice is non-obvious. Per `.cursor/rules/gold-realignment-vs-deflation.mdc`, gold edits need to record the corpus rationale to remain principled. This file currently only has a one-line scenario note ("Mixes dual/multi-PC recall, roster positives, and abstain-precision sentinels; excludes u-L0016-03.") with no per-row rationale.

---

## 5. What this audit does **not** claim

- It does **not** claim the gold is wrong. Two rows are borderline-but-defensible; the others are clean.
- It does **not** claim the model is correct when it under-spreads. The "model dropping Baergrom" failure is a gold-vs-model contract gap, not a gold defect.
- It does **not** propose prompt changes. Recommendations are gold-side adjustments to make the contract sharper before any further prompt or model intervention.

---

## 6. Sources used in this audit

- Gold file: `evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json`
- Prompt: `evals/sentence_routing_retrieval_falsification/routing_prompt.py`
- Recap: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md`
- Party registry: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_party_registry.json`
- Baergrom timeline (Session 18–20 backfill TODO): `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/PCs/baergrom/timeline.md`
- Thrin classification (NPC): `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/README.md`
- Cohort summaries cited in §2 / parent doc: `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-{party_continuation_v1,party_roster_strict_v1}--N5--20260428T18520{2,4}Z.json`
