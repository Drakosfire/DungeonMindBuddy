# Design Brief: Live Query Retrieval Alignment vs Enhanced Query

## Objective

Align manifest-backed retrieval behavior with query-enhancement specificity so the retrieval/admission path reliably favors the intended canonical evidence when the enhancement output includes precise route/title hints.

Primary failing example:
- User query: `what was the last thing that happened in Session 22`
- Enhancement output already includes explicit session-title cues (for example, `Session 22 - Mireward Road and Lysandro`)
- Retrieval/admission still admits and cites Session 21 recap evidence in some runs, producing confident but incorrect answers.

This brief is for diagnosis and design only. Do not introduce hard session-lock guardrails as a workaround.

## Non-goals / Constraints

- Do not hard-filter evidence to only one session.
- Do not add benchmark-ID or question-ID special casing.
- Keep corpus-discovery behavior general (no oracle-only path).

## Canonical truth target (for this failing query)

For "last thing in Session 22", the expected ending beat is the Mireward arrival / Lysandro reveal sequence from Session 22 recap family (including "Is that little Lysandra?" / "Lieutenant Lysandra now").

## Verified evidence locations

Canonical target content exists in:
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md`
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl`

## Key artifact showing current behavior

- `evals/c2_live_prep/artifacts/runs/2026-06-01/live_query_trace_session22_fresh_ingested_lexical.json`

Observed in that trace:
- Enhancement source: `llm`
- `effective_question` includes explicit Session 22 route/title cues + aliases
- Final status can be `ok` with accepted citations, yet cite Session 21 evidence in drifted runs
- Therefore the primary mismatch is retrieval/admission ranking, not answer-template policy

## Current pipeline path (what to inspect)

### Query enhancement and wiring
- `src/live_play/live_query_context.py`
  - `_run_query_enhancement_llm(...)`
  - `QueryEnhancementResult.effective_question`
  - `run_context_lookup_turn(...)` wiring into `QueryRequest(question=effective_question)`

### Retrieval/admission
- `src/live_play/manifest_context_query.py`
  - `_score_entry(...)` candidate scoring
  - `retrieve_candidates(...)` lane-budgeted selection
  - `_extract_markdown_spans(...)` span-level overlap scoring
  - `_extract_session_memory_units(...)` unit-level overlap scoring
  - `_apply_evidence_budget(...)` admitted/rejected capping and order
  - `_admission_reason(...)` use/authority gating after scoring

### Manifest lexical supply
- `src/live_play/planning_corpus_manifest.py`
- `evals/c2_live_prep/benchmarks/c2s23_planning_corpus_manifest.json`

## Working hypothesis

Enhancement is producing good lexical specificity, but retrieval does not exploit that specificity strongly enough:

1. Overlap scoring remains broad and can overvalue generic tokens.
2. Exact recap-title/route hints from enhancement are not strongly boosted end-to-end.
3. Span/unit scoring can still surface cross-session lines that meet minimum overlap.
4. Citation gate validates admitted IDs, not semantic target correctness; wrong-but-admitted can pass.

## Required diagnosis outputs

Produce a short findings table that answers:

1. Where does `effective_question` influence scoring (entry, span, unit) and with what weight?
2. Where do exact title/route cues contribute vs disappear?
3. Which scoring components caused Session 21 to outrank intended Session 22 ending-beat evidence?
4. Is drift introduced at candidate selection, span extraction, session-memory extraction, or admitted-budget selection?

## Design direction (allowed)

Improve retrieval specificity **without** hard session filtering. Candidate approaches to evaluate:

- Token weighting:
  - Downweight stopwords/common tokens.
  - Upweight distinctive tokens (session title words, named entities, route fragments).
- Exact/near-exact title-route boosts:
  - When enhanced query references a manifest route/title token sequence, increase score for matching recap/session-memory entries.
- Alias-aware scoring:
  - Use enhancement aliases/tags directly as weighted features, not only as appended free text.
- Field-aware scoring:
  - Score route/source_id/lexical_terms/excerpt separately; tune so route-title specificity can dominate generic prose overlap.

## Verification requirements

For the same query:
- Admitted top evidence should include Session 22 ending-beat recap/session-memory units.
- Final accepted answer should cite Session 22 ending-beat evidence (not Session 21 closing lines).

Regression safety:
- Run a small multi-query smoke to confirm cross-session questions still retrieve cross-session context when genuinely needed.

## Suggested implementation checklist

1. Instrument scoring components in trace output (temporary or debug-gated) so component-level contributions are visible.
2. Implement scoring adjustments in `manifest_context_query.py` only (keep policy gates unchanged).
3. Re-run trace for Session 22 query and compare:
   - top candidates
   - admitted evidence IDs
   - citation IDs in final answer
4. Run focused tests and update/add retrieval tests that lock in specificity behavior.

