# QA: restore current native writer integration checks

ACTIVE serial successor to merged2382/1c238dcaa9d549afc3d292c02709fab9b3dc5b57.
Branch codex/qa-native-writer-fixtures; isolated non-serving checkout. No other
implementation PR in this lane. All later deferred fundamentals remain in scope
of the goal, not this individual PR.

Outcome: existing tests exercise the current native structured-output boundary
instead of obsolete prompt/trailer/decision assumptions. No runtime, model,
prompt, schema, Gold, assessment threshold or benchmark result changes.

Confirmed baseline evidence: source-attribution-delivery/ under the external
fundamentals-reconciliation-v1 root. All25 query and5 saved-reader failedIDs
were independently reproduced on frozen83877. Most query failures require the
host policy discriminator in prose instructions even though the strict native
schema already owns it. Two authoring fixture paths drop the real final evidence
message. One source decision fixture emits exclude for the post-read question.

Exclusive writes: this handoff; predecessor HANDOFF-QA-captured-source-attribution.md
for backward-looking settlement; tests/test_native_plan_assertions.py,
tests/test_plan_jev_authoring.py, tests/test_agent_native_corpus_sources.py.
Check policy against Responses text.format strict schema (mixed Base when used),
and assert it does not leak in the compiled discussion instructions. Historical
authoring/connected-review prompt paths are not newly certified as cleaned by
this test-only change; their policy is still checked at the native schema owner.
Decode every actual JSON message,
skipping only the exact historical Return JSON trailer. Explicit valid post-read
fixture choice preserves the existing read/review flow. Keep all semantic,
source, citation, reload, routing, failure and no-fallback assertions unchanged.
The newly reached source-case call-count/search-grant assertions also described
the obsolete three/four-call path. Verify exactly two current decisions, one
request-owned discovery and an exact authorized full-read pair instead; retain
replay's no-extra-call checks and all reopen/changed-binding/foreign-query checks.

Do not absorb the separate native_direct_source_selection negative-batch case,
runtime fixes or further newly exposed behavior without a scope checkpoint.
No new test runner, per-question branch, provider call, primary write or deployment.

Validation: targeted previously failed integration cases, existing affected
modules, exact-SHA local query/saved-reader contracts and hosted verifier;
independent cumulative review. Preserve all red/unknown results and compare
remaining IDs to retained baseline, not a manufactured broad-green claim.
