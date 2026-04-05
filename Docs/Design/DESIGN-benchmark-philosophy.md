# Benchmark Philosophy and Lessons Learned

**Date created:** 2026-03-28
**Last updated:** 2026-04-03
**Status:** Living document — update after each benchmark iteration

---

## Part 1: What the Benchmarks Are Looking For

DungeonMindBuddy's benchmark suite validates a multi-stage pipeline: raw corpus documents go in, and grounded GM-ready answers come out. Each benchmark tier tests a different contract along that pipeline.

### Mirathorn Vertical Slice: Three-Gate Model (Canonical Framing)

The Mirathorn vertical slice should be treated as **three separate gates**, not one blended pass/fail.

#### Gate 1: Ingestion Quality (API-backed)

**Suite:** `evals/mirathorn_vertical_slice/eval_entity_recall.py` + `eval_fact_quality.py`  
**Primary question:** Can the system convert real corpus text into high-quality, schema-valid, benchmark-usable entities/facts?

What it validates:

- Pass 1 entity recall against Mirathorn gold (`strict`, `loose`, density guardrail).
- Pass 2 fact quality gates (contract validity, gold coverage, projection parity, precision, cache-replay determinism).
- That extraction runs through real OpenAI-backed paths (no heuristic fallback for strict gates).

Critical examination:

- **Strength:** Closest to production ingestion behavior.
- **Weakness:** Slowest and most brittle due to external API/network dependencies.
- **Failure ambiguity risk:** API/network outages can fail the gate without a code regression.
- **Mitigation:** Keep fixture-only projection gates separate so ingestion failures do not obscure reducer health.

#### Gate 2: Projection Semantics (deterministic)

**Suite:** `evals/mirathorn_vertical_slice/run_step1.py`, `run_step2.py`, `run_step3.py`  
**Primary question:** Given fixed inputs, does layered projection logic behave correctly and deterministically?

What it validates:

- World baseline integrity.
- Campaign overlay behavior without mutating world canon.
- Truth-state precedence (`CANON`, `PREP`, `OBSERVED`).
- Expected conflict behavior and competing fact surfaces.

Critical examination:

- **Strength:** Fast, stable, deterministic, ideal for logic regressions.
- **Weakness:** Fixture-driven; may not reflect extraction drift in live corpora.
- **False confidence risk:** Projection can be green while ingestion is red.
- **Mitigation:** Never treat projection pass as end-to-end pass without Gate 1.

#### Gate 3: QA/Synthesis Usability (end-user contract)

**Suite:** `evals/mirathorn_vertical_slice/eval_synthesis.py`  
**Primary question:** After ingest/projection, does a GM-facing `ask` flow produce grounded, usable answers with stable CLI behavior?

What it validates:

- Ingest round-trip minimum counts.
- Grounded answer heuristics.
- Provenance/conflict visibility in context.
- CLI command-path and error-path stability.

Critical examination:

- **Strength:** Directly tests user-visible behavior.
- **Weakness:** Some scoring is heuristic and can pass mediocre prose.
- **Gap:** Does not yet enforce citation-grade factual QA against a strict answer gold set.
- **Mitigation:** Keep rubric diagnostics machine-readable and pair with targeted question-set regressions.

#### Operational Rule

The Mirathorn vertical slice is only "green" when **all three gates** pass independently. Report gate-level status before any aggregate status.

#### Current State (latest validated run)

Latest full-chain execution attempt:

```bash
env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step1.py \
&& env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step2.py \
&& env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/run_step3.py \
&& env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py \
&& env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py \
&& env PYTHONPATH=. uv run python evals/mirathorn_vertical_slice/eval_synthesis.py
```

Observed gate status snapshot:

- **Gate 1 (Ingestion Quality): PASS**
  - `eval_entity_recall.py`: **PASS**
    - strict recall `1.000`
    - loose recall `1.000`
    - density guardrail: PASS
  - `eval_fact_quality.py`: **PASS** (C1-C5 all PASS)
    - C2 Coverage recall `1.000`
    - C3 Projection parity: PASS
- **Gate 2 (Projection Semantics): PASS**
  - `run_step1.py` / `run_step2.py` / `run_step3.py` deterministic semantics: PASS
- **Gate 3 (QA/Synthesis): PASS**
  - `eval_synthesis.py`: overall PASS

Current implication:

- All three Mirathorn gates currently pass independently.
- Aggregate vertical slice verdict is **GREEN**.
- This run meets the benchmark rule: gate-level proof first, aggregate status second.

### Tier 1: Deterministic Projection (no LLM, no network)

**Suite:** `evals/canon_layering/run_benchmarks.py`
**Runs:** 6 golden scenarios with hand-authored inputs and expected outputs.

What it validates:

- **Layer isolation:** World-layer projection never contains campaign-layer facts. Campaign facts cannot mutate world canon.
- **Provenance completeness:** Every projected attribute traces back to at least one evidence ID.
- **Conflict detection:** When two facts compete for the same (entity, attribute) slot, the system detects and records the conflict.
- **Canon decision scope:** Manual canon decisions apply only to the entity+attribute they target and don't leak to unrelated attributes.
- **Determinism:** Same inputs produce byte-identical outputs across 5 runs.
- **Golden output matching:** Projection output matches hand-verified expected JSON (after stripping metadata fields added in later iterations).

Why it matters: The projection is the single source of truth that feeds synthesis. If the projection is wrong, no amount of prompt engineering fixes the answer. This tier runs without API keys, in under 2 seconds, and should never be flaky.

### Tier 2: LLM Ingestion Slice (requires API, deterministic gates)

**Suite:** `evals/llm_ingestion_slice/run_slice.py`
**Runs:** End-to-end ingestion of a locked source document through chunking, entity extraction, fact extraction, and projection.

What it validates:

- **Gate A — Source integrity:** SHA-256 fingerprint of the source document matches the locked reference. Prevents drift when corpus files move or get edited.
- **Gate V — Extraction viability:** Entity count > 0, fact count > 0, duplicate fact ratio below threshold, conflict count within expected band. Catches catastrophic extraction regressions.
- **Gate B — Event contract integrity:** Every event has required schema fields, proper ordering, and valid layer/campaign references.
- **Gate C — Hybrid correctness:** Core projection fields match expected values while conflict behavior stays within tolerance bands.
- **Gate D — Workflow state progression:** The projection demonstrates the instantiation → zero-tick → live state progression that proves the layered model works end-to-end.

Why it matters: This tier catches regressions in the LLM-dependent extraction pipeline. Because LLM outputs are non-deterministic, gates use threshold bands rather than exact equality. The viability gate was added specifically to fail fast on "zero entities extracted" scenarios that would otherwise produce misleading downstream results.

### Tier 2.5: Mirathorn Ingestion + Projection + QA Vertical Slice

**Suite:** `evals/mirathorn_vertical_slice/`  
**Runs:** A constrained but realistic end-to-end benchmark over Mirathorn using the three-gate model above.

Recommended execution order:

1. Projection semantics gate (`run_step1.py` -> `run_step2.py` -> `run_step3.py`)
2. Ingestion quality gate (`eval_entity_recall.py` -> `eval_fact_quality.py`)
3. QA/synthesis usability gate (`eval_synthesis.py`)

Why this order: deterministic failures should be triaged before API-backed failures, and QA should only be interpreted after ingestion + projection are known-good.

### Tier 3: Synthesis Quality (requires API, question-answer evaluation)

**Suite:** `evals/mirathorn_vertical_slice/eval_synthesis.py` + `run_council_room_question_set.py`
**Runs:** Ingests corpus, asks GM-style questions, scores answers against rubrics.

What it validates:

- **Gate D1 — Ingest round-trip:** Minimum evidence units, entities, and facts extracted from the source document.
- **Gate D2 — Grounded prose:** The synthesized answer mentions key domain terms, meets minimum length, and contains no error stubs.
- **Gate D3 — Provenance in context:** The formatted context contains entity headers, truth-state annotations, and conflict markers.
- **Gate D4 — CLI stability:** Command sequence (entities → projection → ask → quit) runs without crashes, and error cases (missing file, missing API key) are handled gracefully.
- **Council Room question set:** 5 targeted questions about a specific battle scene, each with must-hit tokens and stale-state detectors, scored via both strict (literal match) and semantic (equivalence group) signals.

Why it matters: This is the closest test to the actual user experience. A GM asks "What happened to the Wolf?" and the system should answer with the correct terminal state, citing specific evidence. The dual-signal scoring (strict + semantic) was introduced because the LLM correctly identifies outcomes but paraphrases the evidence — the semantic signal catches correctness that strict scoring misses.

### Tier 4: Corpus Coverage (no separate runner — diagnosed from Tier 3 failures)

Not a formal benchmark suite. Instead, when Tier 3 questions fail with `fail_incomplete` and zero `stale_hits`, the failure is diagnosed as a data gap — the rubric expects facts that were never ingested. The `corpus-gap-auditor` subagent (`.cursor/agents/corpus-gap-auditor.md`) automates the trace: search corpus for missing tokens, identify which documents need ingesting, ingest them, and re-run.

Why it matters: Distinguishing "the pipeline is broken" from "the data isn't there" prevents wasted debugging effort. Early benchmark iterations conflated these two failure modes.

---

## Part 2: Lessons Learned

### Lesson 1: Literal token matching is a trap

**What happened:** The first rubric scored `fail_stale` when the answer contained the word "alive" anywhere — even in the phrase "alive before the fight, but now dead." An answer that correctly described the Wolf's death was marked stale because "alive" appeared as historical context.

**Root cause:** The rubric treated token presence as a boolean signal without considering whether the token appeared in a stale-state context or an update-acknowledging context.

**Fix:** Introduced `GLOBAL_STALE_PATTERNS` (phrases that genuinely indicate no updates, like "nothing changed") and `UPDATE_SIGNAL_TOKENS` (phrases that prove awareness of changes, like "decapitated", "dead"). The stale classification now requires either a global stale pattern OR stale tokens with no must-hits and no update signals. A localized "unchanged" in a sentence that also describes updates is no longer fatal.

**Principle:** Score the answer's global semantic posture, not individual token presence.

### Lesson 2: Separate "wrong state" from "incomplete but correct"

**What happened:** Early scoring had only pass/fail. A question expecting ["killing blow", "dead", "oily sheen fades"] that got an answer mentioning "dead" and "decapitated" was marked the same as an answer saying "nothing changed." Both were "fail."

**Root cause:** No distinction between "the system picked the wrong temporal state" (stale) and "the system picked the right state but didn't cite every expected phrase" (incomplete).

**Fix:** Three-way verdict: `pass_updated`, `fail_stale`, `fail_incomplete`. This immediately clarified that most "failures" were actually incomplete answers pointing in the right direction, not wrong-state regressions.

**Principle:** Failure taxonomy matters more than pass/fail counts. Different failure modes require different fixes.

### Lesson 3: The LLM will paraphrase terminal outcomes

**What happened:** The projection contained "killing blow" as a fact value, but the synthesis model wrote "decapitated" instead. The strict rubric didn't see "killing blow" and scored the answer as incomplete.

**Root cause:** LLMs are trained to paraphrase. Given evidence that says "Bonogo deals the killing blow," the model synthesizes "the Wolf was decapitated" because that's what killing blow means in context.

**Fix (two-pronged):**

1. **Synthesis prompt tuning:** Added a "terminal outcome rule" instructing the model to include terminal phrases verbatim from projection evidence. This caused the model to write `"deals the killing blow"` as a direct quote.
2. **Semantic scoring:** Added `SEMANTIC_EQUIVALENCES` mapping tokens to regex groups (e.g., "killing blow" → ["decapitated", "head removed"]). The semantic scorer acts as a safety net when the model paraphrases despite the prompt instruction.

**Principle:** Prefer tightening the synthesis contract (tell the model what to do) over loosening the rubric (accept whatever it says). The rubric stays strict as a regression detector; the semantic signal provides the nuanced view.

### Lesson 4: Data gaps masquerade as pipeline failures

**What happened:** Questions about Council Room architecture consistently failed. We investigated the selection policy, the context formatter, and the synthesis prompt — all were working correctly. The architectural facts ("arched ceilings", "floating chandelier", "secret passage") simply didn't exist in the fact store.

**Root cause:** The benchmark rubric was written assuming certain documents had been ingested. Those documents hadn't been ingested yet. The pipeline was doing exactly what it should with the data it had.

**Fix:** Built the `corpus-gap-auditor` subagent workflow: search corpus for missing tokens, classify gaps as INGESTABLE / RUBRIC_MISMATCH / EXTRACTION_MISS, ingest missing documents, re-run. After ingesting `The Council Room.md` and `Battle with The Wolf and Aftermath.md`, semantic scoring went from 3/5 to 5/5.

**Principle:** Before debugging the pipeline, verify the data is actually there. The fastest diagnostic is `rg "missing_token" corpus/` — if it returns zero hits, the problem is corpus coverage, not code.

### Lesson 5: Projection "winner takes all" hides competing evidence

**What happened:** After ingesting new documents, the Council Room had multiple facts competing for the same attribute (e.g., geography had both "arched ceilings" and "hidden trapdoor"). The projection selected one winner and discarded the rest. The synthesis model never saw the losing facts.

**Root cause:** The projection schema was designed for a single selected value per (entity, attribute) pair. This is correct for conflict resolution but means useful non-contradictory details are invisible to the synthesis model.

**Fix:** Added `all_value_labels` to the projection output, listing all competing values (OBSERVED first, then CANON). The context formatter now renders up to 5 values per attribute instead of just the winner. This gives the synthesis model the full picture without breaking the selection policy.

**Principle:** The projection's job is to select the canonical truth, but the synthesis context should show the neighborhood. A GM asking "what's the room like?" benefits from seeing arched ceilings AND hidden trapdoor, not just whichever fact the selection policy happened to prefer.

### Lesson 6: MAX_ENTITIES caps silently exclude relevant data

**What happened:** After ingesting additional documents, the entity count grew beyond 50. Smaller but question-relevant entities (like "chandelier" with only 2 facts) were ranked below the cap and excluded from the synthesis context entirely.

**Root cause:** `MAX_ENTITIES = 50` was set when the store had ~40 entities. As the corpus grew, the cap became restrictive. The truncation note at the bottom of the context said "X entities omitted" but didn't indicate which ones were relevant.

**Fix:** Increased `MAX_ENTITIES` to 200. Updated the entity cap test to derive its threshold from the constant rather than hardcoding 50.

**Principle:** Context caps should be set relative to expected corpus scale, not to initial prototype size. When you change them, grep for tests that hardcode the old value.

### Lesson 7: Golden output tests need a normalization layer

**What happened:** Adding new metadata fields to the projection (`source_class`, `source_truth_state`, `all_value_labels`) broke golden output tests even though the core projection logic was unchanged. The tests compared full JSON equality, so any new field caused a mismatch.

**Root cause:** Golden output files were authored before the new fields existed. Adding fields is a valid forward-compatible change but strict equality doesn't allow it.

**Fix:** Introduced `_normalize_projection_for_compare()` that strips known metadata-only fields before comparison. Each time a new metadata field is added, it gets added to the strip list. The golden files remain untouched as the stable reference.

**Principle:** Golden output tests should validate structural correctness, not byte-for-byte reproduction. Keep a normalization layer between the projection output and the comparison, and update it when you add metadata-only fields.

### Lesson 8: Dual-signal scoring reveals different problems

**What happened:** After corpus ingestion, strict scoring regressed from 3/5 to 2/5 while semantic scoring jumped to 5/5. The strict regression happened because new competing facts slightly changed the model's phrasing in a given run.

**Root cause:** LLM synthesis is non-deterministic. Run-to-run variance in phrasing means strict token matching is inherently noisy. The same correct answer might hit "killing blow" in one run and paraphrase it in the next.

**Fix:** Always emit both strict and semantic verdicts. Use semantic as the primary quality signal. Use strict as a regression canary — if strict drops AND semantic drops, there's a real problem. If strict drops but semantic holds, it's phrasing variance.

**Principle:** Dual signals turn a noisy metric into an informative one. The delta between strict and semantic tells you whether you have a correctness problem (both drop) or a phrasing problem (only strict drops).

---

## Part 3: Design Principles (Carry Forward)

These are the principles we've validated empirically. They apply to any new benchmark added to the suite.

1. **Score semantics, not tokens.** Use equivalence groups for must-hit tokens. Keep strict scoring as a canary, not the primary signal.
2. **Classify failures, don't just count them.** At minimum: `pass_updated`, `fail_stale`, `fail_incomplete`, `fail_error`. Different failure classes point to different system layers.
3. **Tighten the contract, don't loosen the rubric.** When the model paraphrases, add synthesis prompt rules. When the data is missing, ingest more corpus. Don't lower the bar to make the number go up.
4. **Emit machine-readable diagnostics.** Every verdict should include `must_hits`, `stale_hits`, `global_stale_hits`, `semantic_must_hits`. Regressions should be diagnosable from the JSON output alone.
5. **Verify data before debugging code.** The fastest benchmark triage is: does the expected fact exist in the projection context? If no, `rg` the corpus. If it's not in the corpus, it's a coverage gap. If it's in the corpus but not in the projection, it's an extraction/projection bug.
6. **Normalize golden outputs.** New metadata fields should not break existing golden output tests. Keep a strip list and update it when schema evolves.
7. **Keep an adversarial fixture.** Maintain at least one test case where the answer contains both updated deltas and a localized unchanged trait. This prevents the stale detector from being too aggressive.
8. **Test scoring logic with unit tests.** The `classify_answer` and `classify_answer_semantic` functions have their own test file (`tests/evals/test_council_room_scoring.py`). Scoring drift is silent and dangerous — unit tests catch it before the benchmark runs.
9. **Separate external-dependency failures from logic failures.** Network/API outages are not reducer regressions. Keep gate status split so operational failures do not contaminate logic confidence.
10. **Require gate-level reporting.** Every benchmark run should emit: `gate_ingestion`, `gate_projection`, `gate_qa`, and only then an optional aggregate.

---

## Appendix: Current Benchmark Inventory


| Suite                           | Location                                                                       | Requires API | Runtime | What it tests                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------ | ------------ | ------- | ----------------------------------------------------------------------------- |
| Canon layering (golden)         | `evals/canon_layering/`                                                        | No           | ~1s     | Projection determinism, layer isolation, conflict detection                   |
| LLM ingestion slice             | `evals/llm_ingestion_slice/`                                                   | Yes          | ~30s    | Source integrity, extraction viability, event contracts, workflow progression |
| Mirathorn gate 1 (ingestion)    | `evals/mirathorn_vertical_slice/eval_entity_recall.py`, `eval_fact_quality.py` | Yes          | minutes | API-backed extraction quality and guardrails                                  |
| Mirathorn gate 2 (projection)   | `evals/mirathorn_vertical_slice/run_step1.py`, `run_step2.py`, `run_step3.py`  | No           | ~1-2s   | Layer semantics and conflict behavior over fixed fixtures                     |
| Mirathorn gate 3 (QA/synthesis) | `evals/mirathorn_vertical_slice/eval_synthesis.py`                             | Yes          | ~45s+   | End-user ingest -> ask usability contract                                     |
| Council Room questions          | `evals/mirathorn_vertical_slice/run_council_room_question_set.py`              | Yes          | ~40s    | Dual-signal answer quality for targeted GM questions                          |
| Corpus remote                   | `evals/corpus_remote/`                                                         | Varies       | ~10s    | Remote artifact validation, inventory building                                |


Commands:

```bash
uv run pytest tests/                                                    # All unit tests (~2s)
uv run python evals/canon_layering/run_benchmarks.py                    # Golden projections (~1s)
uv run python evals/llm_ingestion_slice/run_slice.py                    # Ingestion gates (~30s)
uv run python evals/mirathorn_vertical_slice/run_step1.py               # Mirathorn projection gate
uv run python evals/mirathorn_vertical_slice/run_step2.py
uv run python evals/mirathorn_vertical_slice/run_step3.py
uv run python evals/mirathorn_vertical_slice/eval_entity_recall.py      # Mirathorn ingestion gate
uv run python evals/mirathorn_vertical_slice/eval_fact_quality.py
uv run python evals/mirathorn_vertical_slice/eval_synthesis.py          # Synthesis gates (~45s)
uv run python evals/mirathorn_vertical_slice/run_council_room_question_set.py  # Question set (~40s)
```

