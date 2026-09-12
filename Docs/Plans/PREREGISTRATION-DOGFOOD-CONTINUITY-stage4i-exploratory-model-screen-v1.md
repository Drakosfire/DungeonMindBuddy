# PREREGISTRATION — DOGFOOD-CONTINUITY Stage 4I exploratory model screen

**Registered:** 2026-09-12  
**Status:** FROZEN HUMAN HYPOTHESIS — authored before any Stage 4I paid Luna/Terra/Sol run  
**Companion handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4i-exploratory-model-screen-v1.md`  
**Design branch:** `dogfood-continuity/stage4i-payload-output-model-ablation-v1`  
**Design base:** `0aa77bf791efa00cb51f45f3c7acd273ac3f351f`  
**Purpose:** State, before observing Stage 4I results, what a human reviewer believes a near-perfect campaign-memory ingestion of the frozen seven-source Mireward cohort should preserve, and what model/cost behavior is expected.

> This document is **human review authority only**. It MUST NOT be passed to any extraction prompt, runtime generation step, model context, deterministic enrichment step, or scorer. It does not change the frozen #708 entity/fact gold or #709 temporal overlay. It exists to prevent post-hoc goal movement.

---

## 1. Source basis

This preregistration was written after reading the exact seven sources frozen by benchmark `c2-mireward-campaign-memory-dev-v1`:

1. `Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Mireward Gate.md`
2. `Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md`
3. `Longmont Campaign/Campaign 2/Session Recaps/Session 25 - Mireward Gate Battle II.md`
4. `Elderwyld/Cities and Towns/Mireward/Mireward_PLACE_BUILD_SCAFFOLD.md`
5. `Elderwyld/Cities and Towns/Mireward/NPCs/brin_holloway/character_seed.md`
6. `Elderwyld/Cities and Towns/Mireward/NPCs/orric_tane/character_seed.md`
7. `Longmont Campaign/Campaign 2/PCs/karsemine/timeline.md`

The frozen benchmark already scores six entity anchors and five fact anchors. The expectations below deliberately go beyond those five facts, but remain qualitative human witnesses unless and until a later slice explicitly creates additional benchmark authority.

---

## 2. Primary hypothesis

**H1 — The dominant quality problem exposed by #710 is lossy semantic compression, not failure to notice the relevant source material.**

A fact-extraction contract that explicitly preserves the concrete payload of discoveries, tactical observations, conclusions, and active threats should recover substantially more table-useful campaign memory without requiring a larger fact schema.

The ideal result is not “more prose” or “more facts.” It is **higher information density**:

```text
fewer model-owned fields where code can derive them
+
short facts that retain the decisive answer
+
source/evidence lineage sufficient to distinguish authority and time
```

A model should not spend tokens saying merely that someone learned something when the source states what they learned.

---

## 3. Human perfect-memory target

If I were the GM asking DungeonBuddy, after ingesting only these seven sources, “What matters about Brin, Orric, Karsemine, and Mireward?”, the following is the minimum accumulated memory I would consider excellent.

### 3.1 Brin Holloway

**Identity**

- Session 23 Brin Holloway and the stable Brin Holloway reference are one actor.
- Later references to `Brin` in Session 25 resolve to that same actor.

**Durable/background truth**

- Brin is a cook from Edge.
- Stable reference material adds that he was involved in the Edge support/relief column and became its practical march leader; these reference details should retain their source authority rather than be rewritten as played events unless the recaps support them.

**Played campaign state/history**

- In Session 23 he arrives at Mireward with the refugee/survivor group and acts as its clear leader.
- In Session 25 he is still functioning as the refugee leader and is coordinating with Mireward leadership.
- By Session 25 he has separated refugees by eye condition and is helping manage quarantine/housing.

**Temporal shape**

- “Cook from Edge” is background, not something that began in Session 23.
- Arrival at Mireward is a Session 23 historical event.
- Refugee leadership is a continuing state observed in Sessions 23 and 25; its true beginning is not established by these sources.

**Do not flatten**

- Do not replace all of the above with one generic fact such as `Brin led refugees`.
- Do not turn source-specific head counts into one falsely precise canonical count when the corpus contains approximate/different counts.

### 3.2 Orric / Orik Tane

**Identity**

- `Orik Tane` in played recaps and `Orric Tane` in stable reference material are one actor with spelling/alias drift, not two mayors.

**Durable/current truth**

- Orric/Orik is Mireward's civilian mayor.
- He is mayor in Session 23 and is still identified as mayor in Session 25.
- The sources do not establish when he became mayor.

**Reference-vs-play distinction**

- Reference material describes his counter-festival/civil-calm stance and reluctance to publicly name a siege before the alarm. Those are useful portrayal/governance facts, but their reference authority should remain visible.
- Played Session 23 establishes the mayor role and his reaction to the actual crisis.

**Do not flatten**

- Do not create separate `Orik` and `Orric` campaign-memory people.
- Do not infer “became mayor in S23.”

### 3.3 Karsemine

**Identity/current continuity**

- Karsemine is one continuing PC across her timeline and Sessions 23–25.

**Knowledge acquired in play**

- Session 23: Hunter's Mark reveals that the tripod creatures are **resistant to poison and weak to fire**.
- This is knowledge Karsemine acquired in Session 23; it should remain available afterward rather than being reduced to “learned weaknesses and resistances.”
- Session 24: after moving Hunter's Mark to the golem, she learns that the golem is **immune to poison and charm and weak to fire**.
- The tripod and golem payloads are distinct monster knowledge and must not be conflated.

**Use of knowledge**

- Session 24 shows Karsemine using fire against the tripod, igniting/killing it. This is useful supporting evidence that the discovered fire weakness matters at the table; it should not replace the actual weakness fact.

**Temporal shape**

- The tripod weakness knowledge begins in Session 23 and remains useful afterward.
- The golem immunity/weakness knowledge begins in Session 24.

**Do not flatten**

- `Karsemine learned its weaknesses and resistances` is insufficient when the answers are in source text.
- Do not turn the knowledge into timeless generic bestiary lore detached from who learned it and when.

### 3.4 Mireward Reach

**Place identity**

- Mireward / Mireward Reach is one place.

**Played operational state**

- Session 23 establishes immediate threat at the north gate plus arrival of refugees/survivors from Edge.
- The North Gate battle begins in Session 23.
- Session 24 explicitly ends that local battle.
- Ending the Session 23–24 battle does **not** mean the broader threat to Mireward is over.
- Session 25 confirms continuing operational pressure: refugees still require housing/quarantine, new hybrid creatures attack/burrow outside the wall, and Thrin is dragged underground/disappears.

**Refugee/quarantine state**

- By Session 25 refugees are being housed in the Ironveil Warehouse and separated/managed based on eye condition.
- The situation is a continuing operational problem, not merely an event that “refugees arrived.”

**Authority distinction**

- The Mireward place-build scaffold explicitly says it is planning/scaffold material and non-canon until promoted except where otherwise locked/promoted.
- A perfect ingestion must not silently promote every scaffold claim to played/canonical truth merely because its metadata contains `canon_layer: world`.
- Scaffold material can supply planning/reference context while played recaps remain the authority for what happened at the table.

**Do not flatten**

- `North Gate battle ended` must not erase `Mireward remains under broader threat`.
- `Mireward has refugees` is too weak if the source supports active quarantine/housing pressure and renewed attack.

### 3.5 High-salience campaign memory beyond the frozen five fact anchors

The benchmark intentionally stays small. A human-perfect ingestion should nevertheless surface at least these additional high-value truths when inspecting the resulting store:

- Session 24 golem tactical payload: immune to poison and charm; weak to fire.
- Session 25 refugees are housed/quarantined at the Ironveil Warehouse with Brin involved in management.
- Session 25 renewed hybrid attack proves broader pressure continues after the North Gate battle ends.
- Session 25 Thrin is pulled underground and disappears — an immediate unresolved campaign thread.
- Hesta Bramblewood is the local apothecary encountered in Session 25 who agrees to help with sleep potions; this is a named actor/table-useful service relationship even though she is outside the frozen anchor set.

These are **qualitative preregistered witnesses**, not new scored anchors.

---

## 4. Perfect compact synthesis

A strong accumulated-memory surface should be able to derive something approximately this dense without rereading the seven documents:

> Mireward Reach remains under active pressure from the northern meat-creature threat. Edge refugees led by Brin Holloway arrived in Session 23; Brin is a cook from Edge and remains the refugees' practical leader through Session 25, when refugees are housed/quarantined at the Ironveil Warehouse. Mayor Orric Tane — spelled Orik in the played recaps — remains Mireward's mayor. The North Gate battle runs from Sessions 23–24 and ends in Session 24, but the wider threat does not: new hybrids attack in Session 25 and Thrin is dragged underground. Karsemine learns in Session 23 that the tripod creatures resist poison and are weak to fire, then in Session 24 that the golem is immune to poison and charm and weak to fire. Planning-only scaffold material must remain distinguishable from played/canonical evidence.

This paragraph is a **human target summary**, not text to feed to a model and not a required exact wording.

---

## 5. Model-screen prediction

The paid Stage 4I screen uses one frozen `payload_lean_v1` contract and one run each on Luna, Terra, and Sol.

### H2 — Semantic-contract effect will be larger than model-size effect on the five frozen facts

My prediction before seeing results:

```text
Sol:   6/6 entity anchors, 5/5 fact anchors
Terra: 6/6 entity anchors, 5/5 fact anchors
Luna:  6/6 entity anchors, at least 4/5 fact anchors; 5/5 is plausible
```

The key falsifiable claim is that the payload-preservation instruction should repair at least one of #710's two stable fact misses **across model sizes**, rather than only on Sol.

If all three still miss the same two facts, H1 is weakened: the problem is deeper than the simple payload-preservation instruction.

### H3 — Luna will be much closer to Terra/Sol in quality than price ratios suggest

I expect Luna to be disproportionately competitive on this bounded structured-extraction task. I do **not** predict equal stability from one run, but I predict its single-run campaign-memory result will be close enough to justify replication if it avoids obvious hallucination/noise.

A particularly informative result would be:

```text
Luna ≈ Terra ≈ Sol on core entity/fact recall
while
Luna << Terra < Sol on measured cost
```

That would make `cheap-first + evidence-driven escalation` the leading architecture hypothesis for corpus-scale ingestion.

### H4 — Orik/Orric identity will probably remain unresolved without a dedicated identity intervention

Even if all three models recover both name forms, I expect at least some runs to keep `Orik Tane` and `Orric Tane` as separate identities because Stage 4I is not adding spelling-tolerant reconciliation.

If a model coalesces them anyway, record it as interesting model behavior, not proof that identity handling is solved.

### H5 — Brin identity should remain the easy positive control

Because the name is stable across recap/reference sources, I expect all three models to keep Brin coherent within-run. Failure here would be a serious quality regression even if the five fact anchors look good.

### H6 — Temporal meaning will be inspectable but not fully represented

I expect the improved facts to retain enough source/session evidence for a human reviewer to reconstruct the correct temporal story, but Stage 4I should not magically produce a complete temporal model:

- North Gate battle S23–S24;
- broader Mireward pressure remains active in S25;
- Karsemine acquires specific knowledge in S23/S24;
- background roles are not synonymous with first-observed session.

A model emitting good facts does not by itself prove DungeonMind temporal semantics.

---

## 6. Output-density hypothesis

### H7 — We are paying for output responsibilities the model does not need to own

At least `fact_id` is already known to be deterministically recomputed by persistence. I expect the field-responsibility audit to find additional token expenditure that can move from model output to deterministic code, but I do not preregister any specific additional field as removable before that audit proves it.

The perfect `payload_lean_v1` result is therefore paradoxically **more semantically specific while no larger, and ideally smaller, in visible structured output**.

For example:

```text
BAD / low density
{
  "fact_id": "fact_karsemine_event_outcome_...",
  "subject_entity_id": "...",
  "attribute": "event_outcome",
  "value": {
    "kind": "scalar",
    "label": "Karsemine learned the creature's weaknesses and resistances",
    "normalized": "..."
  }
}

BETTER / higher density
model owns the minimum semantic payload required to persist:
Karsemine + event_outcome + "tripod resists poison; weak to fire"

runtime owns deterministic IDs and other proven derivable structure.
```

Exact model-facing shape is intentionally not preregistered until the field audit proves which fields are safe to remove.

### H8 — Reasoning volume may be a larger cost lever than JSON field trimming

#710 reported ~750k output tokens across three Sol runs but did not separate reasoning tokens from visible structured output. I predict removing redundant JSON fields alone will produce useful but modest savings unless visible serialization dominates. If reasoning tokens are a large share, model choice/reasoning behavior will dominate cost economics.

This is why Stage 4I must measure:

```text
reasoning_tokens
visible_output_tokens
parsed output bytes
persisted rows
```

before claiming where the cost savings come from.

---

## 7. What would count as the strongest possible experimental outcome

The strongest possible Stage 4I result would be:

1. all three models recover 6/6 entity anchors and 5/5 fact anchors;
2. all three preserve both #710-missed decisive payloads rather than generic learning/danger summaries;
3. Brin remains coherent across sources;
4. the human witness packet preserves the S23–24 local battle end versus S25 broader threat distinction;
5. the result contains the additional high-salience S24/S25 truths above without obvious unsupported inventions;
6. `payload_lean_v1` reduces redundant visible output while preserving or improving semantic specificity;
7. Luna is close enough to Terra/Sol on qualitative memory to justify three-run replication;
8. measured Luna cost per evidence unit is dramatically lower than Terra/Sol;
9. corpus workload census shows a whole-corpus Luna-first rehearsal is economically trivial enough to run freely, with Terra/Sol reserved for measurable escalation cases.

If that happens, the next architectural hypothesis becomes:

> **Default campaign-memory ingestion should be cheap-first, with deterministic quality/authority checks deciding when material needs Terra or Sol escalation.**

That is not accepted architecture yet. It is the best-case hypothesis this experiment is designed to test.

---

## 8. Results that would falsify or materially weaken this hypothesis

Any of the following matter more than a cheap bill:

- Luna/Terra omit or distort table-critical payloads that Sol consistently preserves;
- payload preservation increases verbosity/noise without recovering the actual answers;
- output-leaning removes information needed for evidence, authority, identity, or fact semantics;
- the same Karsemine/Mireward failures persist on all three models under the improved contract;
- Brin identity fragments under the candidate contract;
- model outputs incorrectly promote scaffold-only claims to played/canonical truth;
- apparent 5/5 recall is achieved by keyword-shaped hallucination rather than source-grounded facts;
- whole-corpus census reveals source classes or compatibility failures that make the seven-source cost/quality screen nonrepresentative.

A falsified hypothesis is a successful experiment if provenance is clean and the result changes the next engineering decision.

---

## 9. Freeze rule

Once any Stage 4I paid model call begins:

- this preregistration must not be edited to match observed results;
- corrections of factual source-reading mistakes require a separately dated amendment that preserves the original text;
- the frozen benchmark/gold remains unchanged;
- evaluation must report where results match, exceed, or contradict these hypotheses.

The final Stage 4I review should include a compact disposition table:

```text
HYPOTHESIS | RESULT | SUPPORTED / MIXED / WEAKENED / FALSIFIED | NOTE
H1
H2
H3
H4
H5
H6
H7
H8
```
