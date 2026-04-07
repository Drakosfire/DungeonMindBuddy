# Handoff: Benchmark Scoring Hardening and Gold Promotion

**Date:** 2026-04-07  
**Status:** READY  
**Priority:** HIGH  
**Depends on:** Phase 6 curation complete, scope-relevance system implemented

---

## 1) Problem Statement

The council-room benchmark scoring has three structural issues that compound each other:

### A. Two sources of truth for questions

The runner (`run_council_room_question_set.py`) has 7 **hardcoded** questions with `must`/`stale` lists. The curated JSON (`phase6_curated_questions.json`) has 10 questions with `must_hit_tokens`/`stale_tokens`/`semantic_equivalences`/`update_signal_tokens`. These are not the same questions, and the JSON is **not loaded by the runner**. Only `gold_questions.json` exists as a promotion target, but it currently has 1 entry and is also not loaded by the runner.

Promoting more questions into gold is meaningless until the runner reads from a single authoritative file.

### B. Token matching is substring-on-synthesis — inherently variable

`must_hit_tokens` are checked against **LLM synthesis output** (the `ask` CLI answer), not against fact store contents. The scoring functions (`classify_answer`, `classify_answer_semantic`) do case-insensitive substring matching. This means:

- **False positives:** "Ephanna" appears in the answer because the model mentions her as "absent" — the substring check passes even though the semantic intent ("who's present") is wrong.
- **False negatives:** `"wizards' college"` (ASCII apostrophe) doesn't match `"Wizards' College"` (Unicode right single quotation mark U+2019) in model output. This required adding a code-level semantic equivalence.
- **Brittleness at scale:** Compound phrases like `"not fully corrupted"`, `"uncertain reliability"`, `"guard operations"` are unlikely to appear verbatim in paraphrased answers.

### C. Semantic equivalences are split across two locations

The runner has a module-level `SEMANTIC_EQUIVALENCES` dict (13 entries). The curated questions have per-question `semantic_equivalences` in JSON. **The runner never reads the JSON equivalences.** The `update_signal_tokens` field in JSON is also unused — the runner uses a global `UPDATE_SIGNAL_TOKENS` tuple.

This means curator effort on per-question `semantic_equivalences` and `update_signal_tokens` is currently dead data.

---

## 2) Current File Layout


| File                                   | Role                                      | Question count                 | Loaded by runner?               |
| -------------------------------------- | ----------------------------------------- | ------------------------------ | ------------------------------- |
| `run_council_room_question_set.py`     | Runner with hardcoded questions + scoring | 7 (hardcoded `questions` list) | N/A — it IS the runner          |
| `output/phase6_curated_questions.json` | Curated candidate questions               | 10                             | **No**                          |
| `gold/gold_questions.json`             | Promoted gold questions                   | 1 (Q2 only)                    | **No**                          |
| `gold/gold_facts.json`                 | Gold fact anchors (C2 gate)               | 10                             | Yes (by `eval_fact_quality.py`) |


### Runner scoring functions

```
classify_answer()           — strict: case-insensitive substring on answer text
classify_answer_semantic()  — same + regex lookup in module-level SEMANTIC_EQUIVALENCES
```

Both use `max(1, len(must_tokens) - 1)` as the pass threshold — "allow one missed literal."

### Scope precision gate

The runner also runs 3 scope-precision cases (Elric exclusion, cold-start safety, ambiguous scope safety) using the relevance-gated retrieval system. This gate works correctly and is deterministic.

---

## 3) What Needs to Happen

### Phase 1: Unify question source (eliminate dual maintenance)

**Goal:** The runner loads questions from `gold/gold_questions.json` instead of maintaining a hardcoded list.

1. Add a `_load_gold_questions(path) -> list[dict]` function that reads the gold file and maps field names to runner format (`must_hit_tokens` → `must`, `stale_tokens` → `stale`).
2. Replace the hardcoded `questions` list with the loaded gold questions.
3. Keep the 5 legacy council-room questions (q_arch_current, q_arch_delta, q_wolf_status, q_pre_post, q_thalia) in the gold file — these are proven and well-calibrated.
4. Promote the remaining curated questions (Q1 roster, Q3-Q10) into `gold_questions.json` during this phase.
5. Update test expectations to match the new question count.

**Key files:**

- `evals/mirathorn_vertical_slice/run_council_room_question_set.py` — loader + remove hardcoded list
- `evals/mirathorn_vertical_slice/gold/gold_questions.json` — add all questions
- `tests/evals/test_council_room_question_set.py` — update count assertions

### Phase 2: Wire per-question semantic equivalences

**Goal:** `classify_answer_semantic` reads equivalences from the question payload, not just the module-level dict.

1. Extend `classify_answer_semantic` to accept an optional `question_equivalences: dict[str, list[str]]` parameter.
2. In `_semantic_token_present`, check the question-level equivalences first, then fall back to the module-level `SEMANTIC_EQUIVALENCES`.
3. When loading from gold JSON, pass each question's `semantic_equivalences` into the scoring call.
4. Keep the module-level `SEMANTIC_EQUIVALENCES` as a global fallback for tokens that appear across many questions (e.g., `"killing blow"` → `"decapitated"`).

**Key files:**

- `evals/mirathorn_vertical_slice/run_council_room_question_set.py` — scoring functions + run loop
- `tests/evals/test_council_room_scoring.py` — add tests for per-question equivalences

### Phase 3: Fix known scoring bugs

#### 3a. "Absent" false positive on roster question

The roster question asks "Who's actually in the council chamber?" and checks for `"ephanna"` as a `must_hit_token`. If the model says "Ephanna was absent," the substring check passes. This is a false positive.

**Options:**

- **Simple:** Remove `"ephanna"` from `must_hit_tokens` (she's narratively ambiguous — sometimes present, sometimes not).
- **Better:** Add a `must_not_cooccur` field: `{"ephanna": ["absent", "not present", "did not appear"]}`. If the token appears but is negated by a cooccurrence, it doesn't count as a hit.
- **Best long-term:** Move away from substring-on-synthesis toward entity-presence-in-context checks (use the scope-relevance system to verify entity inclusion in the formatter output, not the answer text).

#### 3b. Apostrophe normalization

`"wizards' college"` (ASCII) vs `"Wizards' College"` (Unicode U+2019) breaks strict substring matching. Currently patched by a semantic equivalence entry.

**Fix:** Add a `_normalize_text(text: str) -> str` function that normalizes Unicode apostrophes/quotes to ASCII before substring matching. Apply in both `classify_answer` and `classify_answer_semantic`.

```python
def _normalize_text(text: str) -> str:
    return text.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"')
```

#### 3c. Multi-word token brittleness

Tokens like `"not fully corrupted"`, `"uncertain reliability"`, `"guard operations"`, `"counter corruption"` are unlikely to appear verbatim. These are judgment calls:

- For each, decide: is this a hard requirement (must appear literally or via equivalence), or is it aspirational (nice to have but not gate-blocking)?
- Consider splitting compound phrases into individual keyword tokens where possible.
- The `max(1, len(must_tokens) - 1)` pass threshold already allows one miss — this is the existing tolerance.

### Phase 4: Consider structural alternatives to substring scoring

The current approach (substring-on-synthesis) is fundamentally limited because it checks **how the LLM phrases its answer**, not **whether the correct facts were retrieved and used**. Two alternative approaches are worth considering:

#### 4a. Entity-in-context gate (deterministic, no LLM variance)

Instead of checking answer text for `"bonogo"`, check whether `ent_bonogo` appears in the formatted context that was passed to the synthesis LLM. This is already possible — `format_projection_context` returns structured text with entity headers.

**Advantage:** Deterministic. Tests the retrieval/projection layer, not the synthesis layer.
**Limitation:** Doesn't test whether synthesis uses the context correctly.

#### 4b. Fact-anchor scoring (proven pattern from eval_fact_quality.py)

The C2 gate already does this well: gold facts have `match_keywords` checked against `fact["value"]["label"]` + `fact["value"]["normalized"]`. This is deterministic and tests extraction quality.

**For QA/synthesis questions:** Consider a hybrid: check entity presence in context (deterministic), then check answer text for a small number of high-signal keywords (not compound phrases).

These are design discussions, not immediate implementation. The handoff should note them as Phase E expansion targets.

---

## 4) Deferred Work (Unblock After Scoring Hardening)

### Bonogo preflight bug

`evals/mirathorn_vertical_slice/run_phase6_corpus_question_design.py` — entity name resolution fails for "Bonogo" → `ent_bonogo` (fuzzy=0.0). The entity exists in the fact store. Fix the resolver or add an explicit name alias.

### Barin Coppergleam alias

Entity anchor `ent_barin_coppergleam` exists but name resolution fails (fuzzy=0.5). Likely a Coppergleam/Stonefoot alias issue. Investigate whether the entity was ingested under a different name and add alias mapping.

### Taxonomy gaps

The curation process surfaced several phantom attributes that don't exist in `_VALID_ATTRIBUTES`:

- `beliefs` (remapped to `loyalty_or_alignment_context`)
- `status` (remapped to `event_outcome` or `physical_condition`)
- `combat_context`, `combat_outcome`, `strategy`, `event_sequence` (dropped)

Consider whether `beliefs` and `status` are distinct enough from existing attributes to warrant addition. Both are high-frequency GM question targets.

---

## 5) Key Files


| File                                                                  | Role                                                       |
| --------------------------------------------------------------------- | ---------------------------------------------------------- |
| `evals/mirathorn_vertical_slice/run_council_room_question_set.py`     | Runner: hardcoded questions, scoring functions, scope gate |
| `evals/mirathorn_vertical_slice/gold/gold_questions.json`             | Gold question file (1 entry, target for all promotions)    |
| `evals/mirathorn_vertical_slice/output/phase6_curated_questions.json` | 10 curated questions (source for promotion)                |
| `tests/evals/test_council_room_question_set.py`                       | Runner tests (7 ask assertions, stub CLI)                  |
| `tests/evals/test_council_room_scoring.py`                            | Scoring function tests (12 cases)                          |
| `evals/mirathorn_vertical_slice/eval_fact_quality.py`                 | C1-C6 gates (proven pattern for `match_keywords` scoring)  |
| `evals/mirathorn_vertical_slice/run_phase6_corpus_question_design.py` | Phase 6 generator (Bonogo bug lives here)                  |


---

## 6) Exit Criteria

1. Runner loads questions from `gold/gold_questions.json` — no more hardcoded question list.
2. Per-question `semantic_equivalences` from JSON are used during scoring.
3. Unicode apostrophe normalization is applied before substring matching.
4. Ephanna "absent" false positive is resolved (by removal, cooccurrence check, or entity-presence gate).
5. All 16 existing tests pass after changes.
6. At least the 5 legacy + Q1 roster + Q2 wizards questions are in `gold_questions.json` and pass scoring.
7. No regression in scope-precision gate results.

