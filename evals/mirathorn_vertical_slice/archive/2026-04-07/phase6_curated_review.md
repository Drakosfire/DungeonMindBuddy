# Phase 6 — Curated Question Review

**Date:** 2026-04-05
**Status:** Curated — awaiting user gold-promotion approval
**Input:** 20 candidate questions from phase6_candidate_questions.json
**Output:** 10 curated questions (5 accept + 3 revised + 2 replacements)
**Deferred:** 2 questions tracked for Phase 7

---

## Valid Attribute Reference

From `src/ingestion/fact_extractor.py` `_VALID_ATTRIBUTES`:

```
species, role, rank_or_title, faction, current_location,
physical_condition, mental_state, loyalty_or_alignment_context,
relationship_tags, operational_status, event_outcome, event_progression,
portrayal_notes, unresolved_questions, source_comments,
history, geography, demographics, defenses, economy, governance, atmosphere, goals
```

---

## Accepted Questions (5)

### 1. q_longmont_campaign_general_notes_3 — ACCEPT (no changes needed)

- **Question:** What dual role does Commander Elric Vane play in the campaign notes?
- **Target attrs:** `rank_or_title`, `goals` — both VALID
- **Coverage:** 100% (4/4 pairs matched)
- **Key facts:** Vane rank_or_title: "Commander" + "high priest in the cult"; goals: "Coordinates the spread of tainted meat"
- **Attribute changes:** None

### 2. q_the_emergency_council_meeting_1 — ACCEPT (attribute fix applied)

- **Question:** What strategy does the Wizards' College propose during the emergency meeting, and what is the key tradeoff?
- **Target attrs:** `goals` — VALID
- **Attribute fix:** Dropped `strategy` (not in taxonomy). `goals` already covers strategic intent with 13 Tinkerbright + 5 Wizards' College facts.
- **Coverage:** 50% (2/4 original pairs → now 2/2 with fixed attrs)

### 3. q_longmont_campaign_general_notes_1 — ACCEPT (attribute fix applied)

- **Question:** What does the Longmont campaign note establish about the Shepherds' ideology and patron?
- **Target attrs:** `loyalty_or_alignment_context`, `goals` — both VALID
- **Attribute fix:** Remapped `beliefs` → `loyalty_or_alignment_context` (beliefs not in taxonomy). goals has 8 Shepherds + 2 Maelthor facts.
- **Coverage:** Partially answerable. loyalty_or_alignment_context coverage for Shepherds/Maelthor needs preflight verification.

### 4. q_the_city_council_2 — ACCEPT (no changes needed)

- **Question:** Which council member represents arcane response, and what is his position on cult corruption?
- **Target attrs:** `rank_or_title`, `goals` — both VALID
- **Coverage:** 75% (3/4 pairs). Tinkerbright rank_or_title: 10 facts, goals: 13 facts. Wizards' College goals: 5 facts. Only gap: wizards_college rank_or_title (0).

### 5. q_the_city_council_4 — ACCEPT (no changes needed)

- **Question:** Which roles do Merril, Torrin, and Rurik hold in city governance?
- **Target attrs:** `rank_or_title`, `faction` — both VALID
- **Coverage:** 83% (5/6 pairs). Strong rank_or_title across all three. Only gap: Rurik faction (0 facts).

---

## Revised Questions (3)

### 6. q_battle_with_the_wolf_and_aftermath_1 — REVISED

- **Question:** What happens to The Wolf by the end of the council chamber fight?
- **Original attrs:** `status`, `combat_outcome` — NEITHER in taxonomy
- **Remapped attrs:** `event_outcome`, `event_progression` — both VALID
- **Entity fix:** Added `ent_bonogo` to target_entities. Bonogo EXISTS in fact store (confirmed: `ent_bonogo` with `operational_status`, `current_location`, `role` facts). Phase 6 preflight name resolution failed (fuzzy=0.0) — this is an **entity resolution gap** in the runner, not a missing entity.
- **Coverage note:** event_outcome/event_progression for Wolf likely 0 direct facts, BUT physical_condition has "Decapitated; head removed from body" (OBSERVED) which provides the answer signal. Partially answerable via related attributes.

### 7. q_battle_with_the_wolf_and_aftermath_3 — REVISED

- **Question:** How does Thalia's condition differ from fully corrupted guards during this encounter?
- **Original attrs:** `status`, `loyalty_or_alignment_context`
- **Remapped attrs:** `loyalty_or_alignment_context` only — VALID
- **Change:** Dropped `status` (not in taxonomy, 0 facts for both entities)
- **Coverage:** 100% of remaining pairs. Thalia loyalty: 3 facts (innocent, duty-bound). Wolf loyalty: 2 facts (cult sympathizer, betrayed city). Strong support.

### 8. q_battle_with_the_wolf_and_aftermath_2 — REVISED

- **Question:** Which environmental defenses in the council chamber change the battle flow?
- **Original attrs:** `defenses`, `combat_context`
- **Remapped attrs:** `defenses` only — VALID
- **Change:** Dropped `combat_context` (not in taxonomy, 0 facts)
- **Coverage:** 50% of original pairs → council_room defenses: 8 facts, Wolf defenses: 1 fact. Adequate for the question.

---

## Replacement Questions (2)

### 9. q_the_emergency_council_meeting_2_v2 — REPLACEMENT

- **Replaces:** q_the_emergency_council_meeting_2 ("How does Thalia's proposed guard sweep become a hidden failure mode?")
- **Rejection reason:** Design-document phrasing ("hidden failure mode") — not how a GM would ask
- **New question:** "Is Thalia trustworthy during the emergency meeting?"
- **Target attrs:** `loyalty_or_alignment_context` — VALID
- **Coverage:** Thalia loyalty: 3 facts, Wolf loyalty: 2 facts. Both entities supported in Emergency Council doc preflight.
- **Why this works:** GM-realistic trust question that surfaces the same narrative tension without meta-analytical framing.

### 10. q_the_emergency_council_meeting_4_v2 — REPLACEMENT

- **Replaces:** q_the_emergency_council_meeting_4 ("What time-pressure mechanic drives urgency during emergency council deliberation?")
- **Rejection reason:** Meta-design question about game mechanics. Maelthor entity also unsupported in Emergency Council doc (fuzzy=0.0).
- **New question:** "What happens if the council deliberates too long?"
- **Target attrs:** `event_outcome`, `goals` — both VALID
- **Entity fix:** Removed Maelthor (unsupported in this doc). Kept City Council only.
- **Coverage:** event_outcome for city_council needs preflight verification. goals for city_council may be low — this question may score partially_answerable.

---

## Deferred Questions (2) — Phase 7 Candidates

### D1. q_battle_with_the_wolf_and_aftermath_4

- **Question:** After the chamber fight, what are the main branch paths that still converge on the sewers?
- **Blocker:** `event_sequence` yields 0 facts (not in valid taxonomy). Would need `event_progression` but still 0 coverage for Wolf.
- **Status:** Keep as Phase 7 candidate. Requires extraction coverage expansion for event progression data.

### D2. q_the_emergency_council_meeting_3

- **Question:** Which council alignments emerge around purification, arming citizens, and covert operations?
- **Blocker:** Barin Coppergleam unsupported (fuzzy=0.5). Likely Coppergleam/Stonefoot alias — entity anchor `ent_barin_coppergleam` exists but name resolution fails.
- **Status:** Blocked on alias resolution. Good question otherwise (60% coverage, 6/10 pairs matched).

---

## Attribute Gaps Found

| Invalid Attribute | Found In | Remapping Applied |
|---|---|---|
| `strategy` | q_the_emergency_council_meeting_1 | Dropped (goals covers intent) |
| `beliefs` | q_longmont_campaign_general_notes_1 | → `loyalty_or_alignment_context` |
| `status` | q_battle_1, q_battle_3 | → `event_outcome` (q1), dropped (q3) |
| `combat_outcome` | q_battle_with_the_wolf_and_aftermath_1 | → `event_progression` |
| `combat_context` | q_battle_with_the_wolf_and_aftermath_2 | Dropped (0 facts) |
| `event_sequence` | q_battle_4 (deferred), q_meeting_2 (rejected) | Not remapped — deferred/rejected |
| `ritual` | q_meeting_4 (rejected) | → `event_outcome` in replacement |

**Taxonomy expansion candidates** (for future consideration):
- `beliefs` — strong narrative signal for cult/faction ideology questions
- `status` — current state of an entity (alive/dead/corrupted) is a core GM question
- `combat_context` — battle environment details are GM-relevant

---

## Bonogo Entity Status

**Entity:** `ent_bonogo`
**Status:** EXISTS in fact store
**Facts confirmed:** `operational_status`, `current_location`, `role` (at minimum)
**Phase 6 preflight issue:** Name resolution returned `null` with fuzzy=0.0. The entity anchor exists but the preflight resolver in `run_phase6_corpus_question_design.py` failed to match "Bonogo" → `ent_bonogo`.
**Action needed:** Fix entity name resolution in Phase 6 runner or add explicit name alias.

---

## Files Written

| File | Description |
|---|---|
| `evals/mirathorn_vertical_slice/output/phase6_curated_questions.json` | 10 curated questions with editorial verdicts and attribute remapping |
| `evals/mirathorn_vertical_slice/output/phase6_curated_review.md` | This review document |

---

## Next Actions

1. **User review:** Approve the 10 curated questions for gold promotion
2. **Gold promotion:** Once approved, promote to `evals/mirathorn_vertical_slice/gold/gold_questions.json`
3. **Run verification:** `env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py` after promotion
4. **Fix Bonogo resolution:** Update Phase 6 runner or entity anchors so "Bonogo" resolves to `ent_bonogo`
5. **Fix Barin Coppergleam resolution:** Investigate alias issue (Coppergleam vs Stonefoot?) to unblock deferred q_meeting_3
6. **Phase 7 planning:** Expand extraction coverage for `event_progression` to unblock deferred q_battle_4
7. **Taxonomy expansion discussion:** Consider adding `beliefs`, `status` to `_VALID_ATTRIBUTES` — both are high-signal GM question targets
