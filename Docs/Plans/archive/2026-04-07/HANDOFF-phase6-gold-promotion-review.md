# Handoff: Phase 6 Gold Promotion Review

**Date:** 2026-04-07  
**Status:** IN PROGRESS  
**Purpose:** Walk through the 10 curated Phase 6 questions with the user for gold promotion decisions, then address the Bonogo and Barin blockers to unblock deferred candidates.

---

## 1) What This Is

Phase 6 generated candidate benchmark questions from corpus documents beyond the original Mirathorn source. A `benchmark-question-curator` subagent processed the user's editorial verdicts (accept/revise/reject/defer) and produced 10 curated questions with remapped attributes. These questions need final user approval before promotion to `evals/mirathorn_vertical_slice/gold/gold_questions.json`.

**Source artifacts:**

- `evals/mirathorn_vertical_slice/output/phase6_curated_questions.json` — 10 question payloads
- `evals/mirathorn_vertical_slice/output/phase6_curated_review.md` — editorial notes per question

**Promotion target:**

- `evals/mirathorn_vertical_slice/gold/gold_questions.json` (new file)

---

## 2) Questions for Review

Each question below needs one of: **PROMOTE** (add to gold), **REVISE** (edit before promoting), or **CUT** (do not promote).

---

### Q1: `q_longmont_campaign_general_notes_3` — Elric Vane dual role

**Verdict from curation:** ACCEPT (no changes)

> What dual role does Commander Elric Vane play in the campaign notes?

- **Entities:** Commander Elric Vane, Shepherds' Flock
- **Attributes:** `rank_or_title`, `goals`
- **Coverage:** 100% (4/4 entity-attribute pairs matched)
- **Key facts tested:** Vane as "Commander" + "high priest in the cult"; goals about coordinating tainted meat spread
- **Tier:** `should_pass`
- **Surface:** `vertical_slice`

**Notes:** Straightforward question with full coverage. Also the entity used in scope-precision benchmarks — Elric Vane is the canonical "irrelevant to battle" entity.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q2: `q_the_emergency_council_meeting_1` — Wizards' College strategy

**Verdict from curation:** ACCEPT (dropped phantom `strategy` attr → `goals` only)

> What strategy does the Wizards' College propose during the emergency meeting, and what is the key tradeoff?

- **Entities:** Headmaster Tinkerbright, Wizards' College
- **Attributes:** `goals`
- **Coverage:** 50% (2/2 remaining pairs after attr fix). 13 Tinkerbright facts + 5 Wizards' College facts.
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** Strong fact coverage for the core question. Attr fix was mechanical — `strategy` was never in the taxonomy, `goals` captures the same intent.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q3: `q_longmont_campaign_general_notes_1` — Shepherds' ideology and patron

**Verdict from curation:** ACCEPT (remapped `beliefs` → `loyalty_or_alignment_context`)

> What does the Longmont campaign note establish about the Shepherds' ideology and patron?

- **Entities:** Shepherds' Flock, Maelthor
- **Attributes:** `loyalty_or_alignment_context`, `goals`
- **Coverage:** Partial. `goals` has 8 Shepherds + 2 Maelthor facts. `loyalty_or_alignment_context` coverage for these entities is unverified.
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** The `beliefs` → `loyalty_or_alignment_context` remap is reasonable but coverage on `loyalty_or_alignment_context` for Shepherds and Maelthor hasn't been confirmed by preflight. This question may initially fail until extraction catches the ideology signal under the `loyalty_or_alignment_context` attribute. Worth promoting even if it starts as a "stretch" anchor — it tests whether the pipeline captures cult ideology.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q4: `q_the_city_council_2` — Tinkerbright's arcane position

**Verdict from curation:** ACCEPT (no changes)

> Which council member represents arcane response, and what is his position on cult corruption?

- **Entities:** Headmaster Tinkerbright, Wizards' College
- **Attributes:** `rank_or_title`, `goals`
- **Coverage:** 75% (3/4 pairs). Tinkerbright has 10 `rank_or_title` facts and 13 `goals` facts. Only gap: Wizards' College `rank_or_title` (0 facts).
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** The Wizards' College `rank_or_title` gap is expected — it's an organization, not a titled individual. The question is really about Tinkerbright. Strong coverage where it matters.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q5: `q_the_city_council_4` — Merril, Torrin, Rurik governance roles

**Verdict from curation:** ACCEPT (no changes)

> Which roles do Merril, Torrin, and Rurik hold in city governance?

- **Entities:** Merril Tealeaf, Torrin Flamescale, Rurik Stonehammer
- **Attributes:** `rank_or_title`, `faction`
- **Coverage:** 83% (5/6 pairs). Strong `rank_or_title` across all three. Only gap: Rurik `faction` (0 facts).
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** Tests multi-entity breadth for secondary NPCs. These are the kind of entities a GM needs quick answers about during council scenes.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q6: `q_battle_with_the_wolf_and_aftermath_1` — Wolf's fate

**Verdict from curation:** REVISED (remapped `status`+`combat_outcome` → `event_outcome`+`event_progression`; added Bonogo)

> What happens to The Wolf by the end of the council chamber fight?

- **Entities:** The Wolf, Bonogo
- **Attributes:** `event_outcome`, `event_progression`
- **Coverage:** `event_outcome`/`event_progression` likely 0 direct facts for Wolf under those attributes. BUT `physical_condition` has "Decapitated; head removed from body" (OBSERVED) which provides the answer signal.
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** This is the hardest question in the set. The answer exists in the store under `physical_condition`, not under the target attributes. Two possible approaches:

1. Promote as-is and expect it to initially fail — it becomes a stretch anchor that drives extraction to capture `event_outcome` data.
2. Add `physical_condition` as an `alternative_attribute` so the existing fact matches.

The Bonogo entity is confirmed to exist (`ent_bonogo`) but was unresolved by the Phase 6 preflight due to a name resolution bug (fuzzy=0.0).

**Decision needed:** PROMOTE / REVISE / CUT  
**Follow-up decision:** Should `physical_condition` be added as an `alternative_attribute`?

---

### Q7: `q_battle_with_the_wolf_and_aftermath_3` — Thalia vs corrupted guards

**Verdict from curation:** REVISED (dropped phantom `status`; kept `loyalty_or_alignment_context`)

> How does Thalia's condition differ from fully corrupted guards during this encounter?

- **Entities:** Commander Thalia Ashenvale, The Wolf
- **Attributes:** `loyalty_or_alignment_context`
- **Coverage:** 100%. Thalia has 3 facts (innocent, duty-bound), Wolf has 2 facts (cult sympathizer, betrayed city).
- **Tier:** `must_pass`
- **Surface:** `vertical_slice`

**Notes:** Clean question with strong coverage. Tests whether synthesis can distinguish between "manipulated" and "corrupted" — a key narrative distinction in this campaign.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q8: `q_battle_with_the_wolf_and_aftermath_2` — Council chamber defenses

**Verdict from curation:** REVISED (dropped phantom `combat_context`; kept `defenses`)

> Which environmental defenses in the council chamber change the battle flow?

- **Entities:** Council Room, The Wolf
- **Attributes:** `defenses`
- **Coverage:** Council Room has 8 `defenses` facts, Wolf has 1. Good coverage for the core question.
- **Tier:** `must_pass`
- **Surface:** `core_extraction`

**Notes:** Tests place-entity attribute extraction — Council Room as a location with mechanical properties. The kind of question a GM asks when players enter a room.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q9: `q_the_emergency_council_meeting_2_v2` — Thalia's trustworthiness

**Verdict from curation:** REPLACEMENT (original was design-doc phrasing)

> Is Thalia trustworthy during the emergency meeting?

- **Replaces:** "How does Thalia's proposed guard sweep become a hidden failure mode?"
- **Entities:** Commander Thalia Ashenvale, The Wolf
- **Attributes:** `loyalty_or_alignment_context`
- **Coverage:** Thalia has 3 facts, Wolf has 2 facts. Both entities supported in Emergency Council doc.
- **Tier:** `must_pass`
- **Surface:** `vertical_slice`

**Notes:** Much better question than the original — this is exactly how a GM thinks about Thalia during council prep. Shares attribute space with Q7 but different document scope and narrative angle.

**Decision needed:** PROMOTE / REVISE / CUT

---

### Q10: `q_the_emergency_council_meeting_4_v2` — Consequences of delay

**Verdict from curation:** REPLACEMENT (original was meta-design question)

> What happens if the council deliberates too long?

- **Replaces:** "What time-pressure mechanic drives urgency during emergency council deliberation?"
- **Entities:** City Council
- **Attributes:** `event_outcome`, `goals`
- **Coverage:** `event_outcome` for City Council needs preflight verification. `goals` may be low.
- **Tier:** `must_pass`
- **Surface:** `vertical_slice`

**Notes:** Good GM question — tests whether the system captures consequence/urgency signals. May start as a stretch anchor if `event_outcome` coverage is thin. This is the weakest question in the set — coverage is uncertain and the entity is broad (City Council as an organization).

**Decision needed:** PROMOTE / REVISE / CUT

---

## 3) Deferred Questions (2) — Not for Promotion Now

These are tracked for future phases, not up for review today.

### D1: `q_battle_with_the_wolf_and_aftermath_4`

> After the chamber fight, what are the main branch paths that still converge on the sewers?

**Blocker:** `event_progression` for Wolf has 0 facts. Needs extraction expansion.

### D2: `q_the_emergency_council_meeting_3`

> Which council alignments emerge around purification, arming citizens, and covert operations?

**Blocker:** Barin Coppergleam entity resolution fails (fuzzy=0.5). Likely a Coppergleam/Stonefoot alias issue.

---

## 4) Post-Review Actions

After the user makes decisions on each question:

### Immediate

1. Build `gold_questions.json` from promoted questions
2. Strip curation metadata fields (editorial_verdict, editorial_notes, attribute_remapping, replaces_id, etc.) — gold file should be clean
3. Run `eval_fact_quality.py` to verify promoted questions don't break existing C1-C5 gates

### Bug fixes to unblock deferred candidates

1. **Bonogo preflight bug:** Fix entity name resolution in `evals/mirathorn_vertical_slice/run_phase6_corpus_question_design.py` — Bonogo exists as `ent_bonogo` but fuzzy=0.0 fails to match.
2. **Barin alias investigation:** Check whether `ent_barin_coppergleam` exists in the store with aliases. If the entity is actually "Barin Stonefoot" or similar, add alias mapping.

### Taxonomy consideration

1. `**beliefs` attribute:** Came up repeatedly. Consider whether `loyalty_or_alignment_context` adequately captures ideology/beliefs, or whether `beliefs` should be added to `_VALID_ATTRIBUTES`.
2. `**status` attribute:** Current-state questions (alive/dead/corrupted) are core GM needs. `physical_condition` covers some cases; `event_outcome` covers others. Is there a gap?

---

## 5) Gold Question Schema

For reference, promoted questions should match this shape:

```json
{
  "id": "q_...",
  "document_source": "corpus/...",
  "question": "...",
  "expected_answer_summary": "...",
  "must_hit_tokens": ["..."],
  "stale_tokens": ["..."],
  "update_signal_tokens": ["..."],
  "semantic_equivalences": {},
  "target_entities": ["ent_..."],
  "target_attributes": ["..."],
  "surface": "core_extraction | vertical_slice",
  "tier": "must_pass | should_pass"
}
```

Fields stripped during promotion: `editorial_verdict`, `editorial_notes`, `original_target_attributes`, `attribute_remapping`, `replaces_id`, `rejection_reason`, `bonogo_entity_status`, `coverage_status`, `coverage_match_ratio`, `target_entity_names_requested`, `unresolved_target_entity_names`.
