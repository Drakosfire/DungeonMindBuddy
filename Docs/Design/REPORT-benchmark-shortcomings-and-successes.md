# Benchmark Shortcomings and Successes

**Date:** 2026-03-28
**Context:** Written after Phase E (synthesis contract tightening), corpus-gap ingestion, and a full skeptical review of the project.
**Last known benchmark state:** Strict 2/5, Semantic 5/5 on Council Room question set (live run with API). Artifact file was subsequently overwritten by a no-API test run — see Shortcoming S6.

---

## Successes: What the Benchmarks Get Right

### S1. The deterministic projection tier is genuinely solid

The 6 golden-scenario benchmark (`evals/canon_layering/run_benchmarks.py`) tests real invariants: layer isolation, provenance completeness, conflict detection, decision scope, and determinism. It runs in under 2 seconds with no API keys. It is never flaky. It catches real bugs when the projection logic changes.

This tier is the bedrock. Everything downstream depends on the projection being correct, and this tier proves it with hand-authored inputs and hand-verified expected outputs. No LLM variance, no threshold fudging, no generosity. It either matches or it doesn't.

### S2. Three-way failure classification prevents misdiagnosis

Splitting failures into `pass_updated`, `fail_stale`, `fail_incomplete`, and `fail_error` was the single most useful benchmark design decision. Before this, a correct answer missing one phrase and a completely wrong answer looked the same. After: the investigation immediately focuses on the right layer.

`fail_stale` means the selection policy is broken — the system picked an old state. `fail_incomplete` means the right state was selected but the answer didn't cite every expected phrase. `fail_error` means a crash. Each failure class points to a different part of the pipeline. This taxonomy is worth keeping and extending.

### S3. The stale-detector reform was a real fix

The original stale detector flagged any answer containing `"alive"` as stale, even when the answer said "alive before the fight, now dead." The fix — `GLOBAL_STALE_PATTERNS` for genuinely stale answers plus `UPDATE_SIGNAL_TOKENS` as override evidence — eliminated false positives without losing sensitivity. The adversarial test fixture (`test_localized_unchanged_trait_is_not_global_stale`) prevents regression. This is well-engineered.

### S4. Dual-signal scoring (strict + semantic) is the right architecture

The delta between strict and semantic scoring is genuinely informative. When both drop, there's a correctness problem. When only strict drops, it's LLM phrasing variance. This insight turned a noisy pass/fail metric into a diagnostic signal. The decision to keep both signals in every output — rather than replacing strict with semantic — was correct.

### S5. Corpus-gap diagnosis prevents wasted debugging

The workflow of tracing `fail_incomplete` with zero `stale_hits` to a data gap (rather than a code bug) saved hours of wrong-layer investigation. Searching the corpus for missing tokens before touching the pipeline is now a reflex. The `corpus-gap-auditor` subagent formalizes this, and it works.

### S6. Scoring logic has its own unit tests

`classify_answer` and `classify_answer_semantic` are tested independently in `tests/evals/test_council_room_scoring.py`. This means scoring drift (the most dangerous silent regression) is caught before the benchmark runs. The adversarial fixtures — localized unchanged trait, global stale phrase, semantic promotion, no false positive — cover the critical edge cases.

---

## Shortcomings: What the Benchmarks Get Wrong or Miss

### S1. Temporal provenance is tested but doesn't work in production

The reducer has code to use `asserted_in_session` and `sequence_index_within_session` for fact ordering (`canon_projection.py` lines 22-28, 46-51). The fact extractor populates these fields from `inferred_session` (`fact_extractor.py` lines 308-335). Unit tests verify the plumbing works (`test_temporal_provenance_copied_from_evidence_unit`).

**But in the actual store, 0 out of ~1,944 campaign facts have non-null temporal ordering.** The `inferred_session` field is derived from section headings via regex (`chunker.py`, `_SESSION_RE`), but the Longmont Campaign General Notes document doesn't have "Session N" headings — it uses running prose. The temporal provenance infrastructure exists end-to-end in code but produces all-null values on the actual corpus.

**Impact:** The selection policy for competing facts degenerates to lexicographic `fact_id` comparison when temporal fields are null. The only reason the Wolf's death is selected over "Invisible" is a hardcoded `_terminal_observed_rank` heuristic that string-matches death keywords. This works for terminal outcomes (death, decapitation) but fails for any non-terminal state change — a political status that flipped mid-session, a location that was damaged then repaired, a relationship that changed.

**What's missing from benchmarks:** No benchmark tests the selection policy on competing non-terminal facts with null temporal ordering. Every golden scenario has either non-conflicting facts or terminal outcomes. A test case with two competing OBSERVED values like "the gate is open" and "the gate is barred" — neither terminal — would expose the lexicographic fallback.

### S2. The semantic equivalence map is too generous in places

Some equivalences are principled:
- `"killing blow"` → `["decapitated", "head removed"]` — these are semantically identical in context.
- `"oily sheen fades"` → `["oily sheen", "sheen fades"]` — partial matches of the same phrase.

But others are too broad:
- `"before"` → `["before", "prior to", "pre-fight", "lead-in"]` — any contrast-structured answer hits this.
- `"after"` → `["after", "post-fight", "outcome", "end of"]` — `"end of"` appears in almost any temporal answer.
- `"dead"` → `["decapitated", "head removed", "death", "killed", "no longer active"]` — `"no longer active"` is vague enough to match many non-death states.

Combined with the pass threshold at line 70 (`len(must_hits) >= max(1, len(must_tokens) - 1)`), a question with 3 must-tokens only needs 2 hits, and each token has 3-5 semantic alternatives. The semantic scoring cannot realistically fail on a directionally-correct answer. This is a safety net so wide it no longer catches anything.

**What's missing:** A test that the semantic equivalence map can actually fail. There's a `test_semantic_no_false_positive_on_unrelated` test, but it uses "the wolf was alive and well" — obviously unrelated. There's no test with a subtly wrong answer that mentions death in the wrong context or attributes it to the wrong character.

### S3. The benchmarks don't test answer usefulness

All scoring checks whether specific tokens appear in the answer. No benchmark asks:
- Is this answer a useful length for session prep? (Some answers are 400+ words for a simple status question.)
- Is the provenance trace readable? (Citations like `[CANON, from: layer=world, source_class=seed_reference, fact=fact_the_wolf_physical_condition_bf103ae53327]` are machine-useful but GM-hostile.)
- Would a GM trust this answer enough to run a session from it?
- Does the answer correctly distinguish which facts are current vs. historical?

Token presence proves the system found the right data. It does not prove the system produced a useful artifact. These are different quality dimensions and the benchmarks only measure the first.

### S4. The canon decision path is untested in the production flow

`store.project()` always passes `conflicts=[]` and `canon_decisions=[]` to the projection reducer (`store.py` lines 283-290). Conflicts are auto-derived inside `project_entity_state`, which is correct. But canon decisions — the mechanism for a GM to manually override a conflict resolution — are always empty in the production flow.

The Tier 1 golden benchmarks thoroughly test canon decisions in isolation. But the production `ask` command never exercises this path. There is no CLI command to create a canon decision, and no benchmark that tests the round-trip: GM creates decision → store persists it → projection respects it → synthesis cites it.

**Impact:** The canon decision system is proven correct in a test harness but unproven in the product. If a GM eventually needs to say "no, the Wolf survived — ignore the session notes," there is no mechanism to do that through the CLI, and no benchmark that would catch a regression in this flow.

### S5. Entity merge pollution is documented but unbenchmarked

The skeptical review identified that the Wolf's alias set includes "Bonogo", "Grishna", "Torbin" — distinct characters merged into the Wolf entity by overly aggressive fuzzy matching. Pronoun filtering was added (`_PRONOUN_ALIASES` in `store.py`), and entity-type conflict blocking was added, but proper-name pollution persists.

There is no benchmark that measures entity merge quality. No test asks "after ingesting the full Mirathorn corpus, how many entities have incorrect aliases?" The unit test `test_entity_merge_is_blocked_when_types_conflict` tests a single code path, not the aggregate quality of merge decisions across a real corpus.

### S6. Benchmark artifacts are not protected against staleness

The `council_room_question_set.json` file is overwritten every time the benchmark runs — including during test suite runs that execute without an API key and produce empty answers. The artifact currently on disk shows 0/5 with empty strings, which does not reflect the last meaningful run (which was strict 2/5, semantic 5/5).

There is no mechanism to:
- Prevent a no-API run from overwriting a valid artifact.
- Timestamp or version the artifact.
- Distinguish "this result is from a real run" from "this result is from a dry-run stub."

**Impact:** Anyone reading the artifact file sees 0/5 and concludes the system is broken. The actual state is better than the artifact suggests, but the artifact doesn't know that.

### S7. Hardcoded entity filters will not generalize

`entity_extractor.py` lines 42-124 contain 83 lines of filter lists (`_JUNK_ENTITY_EXACT`, `_JUNK_ENTITY_PREFIXES`, `_LOW_SIGNAL_SINGLE_TOKENS`, `_LOW_SIGNAL_PHRASES`) tuned to the Mirathorn corpus. Terms like "fantastic livestock", "brewing competition", "cultural exhibitions" are Mirathorn-specific junk.

No benchmark tests whether entity extraction works on a document that isn't from Mirathorn. When a second campaign's documents are ingested, some of these filters will incorrectly suppress valid entities (e.g., "rescue" is in the low-signal list, but a campaign about a rescue mission would want that as an entity). No benchmark catches this because no benchmark uses a non-Mirathorn corpus.

### S8. The golden output normalization strip list is growing debt

`_normalize_projection_for_compare` now strips 3 fields: `source_class`, `source_truth_state`, `all_value_labels`. Every new metadata field added to the projection will need to be added here. At 3 fields this is manageable. At 8-10 fields the golden outputs are testing an increasingly narrow subset of the actual output, and the strip list becomes a maintenance hazard where forgetting to add a new field breaks all golden tests.

**What's missing:** A test that the strip list is complete — i.e., that no unexpected keys exist in the projection output beyond the golden keys plus the strip list. This would fail proactively when a new field is added, rather than silently allowing it through until someone notices.

---

## Severity Summary

| Issue | Severity | Category | Effort to Fix |
|-------|----------|----------|---------------|
| S1. Temporal provenance is all-null on real corpus | **Critical** | Correctness | Medium — requires session-heading extraction or manual annotation |
| S2. Semantic equivalences too generous | Medium | Scoring quality | Low — tighten specific entries, add subtly-wrong test cases |
| S3. No answer-usefulness scoring | Medium | Coverage gap | Medium — requires rubric design for length/readability |
| S4. Canon decisions untested in production flow | Medium | Coverage gap | Low — add CLI command + round-trip benchmark |
| S5. Entity merge quality unbenchmarked | Medium | Coverage gap | Medium — requires aggregate quality metric |
| S6. Artifacts not protected from stale overwrites | Low | Infrastructure | Low — add timestamp/API-key guard to artifact writes |
| S7. Entity filters won't generalize | Medium | Generalization | Medium — needs Set B corpus + regression test |
| S8. Golden normalization strip list growth | Low | Technical debt | Low — add unexpected-key assertion |

---

## Recommended Priority Order

**Immediate (before next feature work):**
1. Fix artifact staleness (S6) — 30 minutes. Guard artifact writes with an API-key check or timestamp header.
2. Tighten semantic equivalences (S2) — 1 hour. Remove "lead-in", "outcome", "no longer active". Add a subtly-wrong-answer test.

**Next iteration:**
3. Add a non-terminal competing-facts benchmark (S1) — 2 hours. Two OBSERVED values for the same attribute, neither terminal. Proves the selection policy fails without temporal ordering.
4. Add unexpected-key assertion to golden normalization (S8) — 30 minutes.

**Before second corpus:**
5. Test entity extraction on a non-Mirathorn document (S7) — half day. Pick a single non-Mirathorn campaign doc, ingest it, and check for filter suppression.
6. Implement canon decision CLI command and round-trip test (S4) — half day.
7. Design an answer-usefulness rubric (S3) — requires thought, not just code.
8. Add entity merge quality metric (S5) — requires a ground-truth alias list for at least one corpus.
