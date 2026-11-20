# CI: classify the merged response-assembly test

SETTLED: #2347 merged at2a375d79331e42f4fa97b8ee1b79ff123740d53e after
independent exact-head approval.65 guards/actual response cases pass;1490 files
classified. Source-only; no runtime changes. References rebased onto this merge.

Historical ACTIVE PRIME serial prerequisite from60d28dda015c46ffd9e345f72bf48216684a30a3,
branch codex/ci-response-assembly-inventory in existing context-loop checkout.
The authorized References slice found current main inventory red after merged
COMPOSITION2345 added tests/test_plan_jev_response_assembly.py without classifying
it. Preserve that original failure in reference-advertisement-ci-working.log.

Expected exclusive writes: this handoff and ci/test-classification.json exactly
one new domain-integration entry for that test. It reconstructs actual native
execution and writer/SDK request assembly with a MockTransport; it has no live
DB/provider calls. Domain integration matches existing native execution/writer
classification. No selectors, workflows, runner, test code or runtime changes.

Run exact-SHA CI guard/inventory plus the actual test; inspect diff and obtain
independent review before PRIME merge. Source-only delivery, no service restart.
Then re-anchor the parked committed References branch and resume its exact UI
verification. Keep unrelated work/coordination off; no ADVERSARY handoff needed.
