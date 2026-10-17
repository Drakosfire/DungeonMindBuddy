# AGENT: let code locate exact requested-detail phrases

**Status:** ACTIVE; PRIME implements solo, ARCHITECTURE independently reviews.
**Base:** main@f51f5b7745d28ba9b3afcc427193d253b0ab2b2d; branch codex/jev-question-phrase-gaps.
**Lane:** existing buddy-tool-denial-delivery checkout/dependencies/private evidence directory. No new checkout, environment, source export, server or /tmp task files.
**Topology:** serial successor to merged #1364 and #1363. DOGFOOD C0 #1327 is disjoint. No provider/serving/retained writes during implementation/review.

## Outcome and failure evidence

V3 asks the prose model to count character offsets. Fresh ordinary-glossary-http-toll-20261017-01 retained the correct toll section but its one writer produced out-of-range offsets and was correctly refused; no retry. ARCHITECTURE advised exact question-phrase copying with code-owned unique substring location. Preserve this failed attempt. Read-only production APP preflight finds zero V3 capability/schema trace matches; serving39aa160 has never adopted V3. Existing running turns do not have V3 traces. V3 exists only in dropped-clone research; Git refs preserve it, so retire that never-served format instead of adding a compatibility adapter. Live historical V1/V2 validation remains unchanged.

## Contract

New named V4 format with exact-question-phrase packet capability. Each gap contains only strict question_phrase, 1–256 Unicode code points, printable/nonblank/no outer whitespace. Host requires exactly one case-sensitive exact occurrence in original user question, including overlapping occurrence detection; no normalization, trimming, fuzzy match or fallback offsets. Code derives and sorts positions; rejects duplicate or overlapping phrases. Preserve fixed escaped excerpt-scoped rendering, 16-gap count/128-segment capacity, partial/insufficient status and missing-details requirements. Facts/citations and exact original-question/envelope/captured-output APP reconstruction stay unchanged.

Instructions ask the model to copy, never count, and to give a supported qualitative constraint or relevant partial information when an exact requested value is unavailable. No corpus names, expected facts, gold or source selectors enter that generic instruction.

## Exact write lease

- This handoff; factual settlement of Docs/Plans/HANDOFF-AGENT-requested-detail-gaps.md and HANDOFF-AGENT-selection-glossary.md.
- src/application_state/agent_conversation/source_writer_output.py: V4 phrase contract, strict location/normalization and V3 retirement.
- apps/live_control_server/services/build_jev_writer.py: exact capability/schema/instructions.
- tests/test_build_requested_detail_gaps.py: phrase membership, repeated/overlap, Unicode/escaping, prose/scope/numeric injection, old-format isolation, actual SDK→APP refusal/reopen.
- tests/test_agent_build_jev_ordinary_harness.py: required empty V4 gap list fixture; no weaker assertions.

No Graph, acquisition, selection, UI, ingestion, schema migration, provider, dependency or retained-data change. Stop/split if more paths/contracts needed.

## Verification

Exercise the actual mocked SDK/APP seam, raw producer/envelope reconstruction, invalid phrase/capability/foreign question refusal, unchanged facts/citation indexes/history, capacity and historical V1/V2. Run focused tests/lint/cumulative diff, push one PR, independent exact-head review. Then changed-format ordinary Toll under standing approval, one writer with no unchanged retry, to evaluate supported partial facts plus specific unknowns. No serving or full Mirathorn completion claim from synthetic success or frozen pilots.

## Implementation evidence

New build_cited_source_answer_v4 uses exact_question_phrase_selected_excerpts_v1. Only question_phrase is accepted; code requires unique case-sensitive membership (including overlapping duplicate detection), locates/sorts spans and refuses overlap. Old offset fields and never-served V3 capability/format are rejected without an adapter. Live historical V1/V2 producer shapes remain unchanged. Fixed host rendering/capacity/positive citations/APP proof remain intact. Generic writer instructions permit source-supported qualitative constraints alongside missing exact values.

Sixty focused cases pass in37.20s across phrase gaps, cited-writer proof and selection. Cases include actual mocked SDK→APP failure/reopen, exact/foreign/case/repeated/overlap/Unicode/Markdown/numeric/prose-scope refusal and completion capacity. Scoped Ruff and cumulative diff pass. No provider or serving/retained writes during implementation. Read-only retirement preflight is retained privately; V3 failures remain in Git and research artifacts. Fresh model semantics and serving adoption remain separate.
