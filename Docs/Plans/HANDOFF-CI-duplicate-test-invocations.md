# CI: remove duplicate test invocations

Status: ACTIVE. PRIME owns this bounded CI-only slice under the operator's
2026-11-07 instruction to remove obvious waste before measuring a cleaned baseline.

## Authority and topology

Parallel-independent from origin/main@011dbfb02cb2ffdfedf94a7652792d18054340ab,
branch codex/ci-remove-duplicate-test-invocations in the existing buddy-context-loop
checkout/dependencies. No new checkout/environment. Existing product heads2196,
2197,2199,2200 remain unchanged; their runtime candidates/recipes are preserved.
SURFACE2198, INGEST2190/2193 and held Play2172/citation2191 do not own these changes.
No API/UI/World/provider/live-database write lease is granted. Local validation
may reuse only disposable test databases on54329 through the existing fixtures;
APP54331, Core54330 and benchmark55447 remain excluded. No new environment.

## Outcome and exclusive write set

Remove only demonstrably repeated Python test selections across the two workflows.
Every distinct collected test must remain in a required job with equivalent Python,
locked dependencies, PostgreSQL and test environment. Keep one invocation at the
owning group: native recap preparation and ingestion-review context stay in the
ingestion/publication group. Keep auth tests, authorization checks, job names,
required gates, timeouts and failure semantics. Do not optimize fixtures, shard
suites, introduce path filters or change caching in this slice. No new mirror test.

Expected writes:
- This handoff.
- .github/workflows/hosted-validation.yml
- .github/workflows/world-ownership-core.yml

## Verification and delivery

Preserve the original workflow selectors; compare actual pytest collection before
and after the edit. Distinct test definitions and pytest parameter-index combinations must be equal;
duplicated cross-job invocations should
fall. Pytest already deduplicates a repeated file argument within one invocation;
removing that manifest duplicate is clarity only, not an execution-time claim. Run the retained affected modules once, preserving failures. Inspect cumulative
diff and exact independent review, commit/push/open one PR, satisfy required CI and
merge under standing PRIME authority. No product deployment. This cleanup alone
does not establish the cleaned baseline, fixture performance or overall CI success.
After the first removals, measure wall time, queue/retry delay, runner time, setup,
test durations and timeouts before choosing the next bounded CI improvement.

## Verified local evidence

Actual collection at the pinned base and edited selectors preserves all2240 distinct
cases, removing167 repeated cross-job selections (2407→2240 invocations). Nine raw
display IDs embed generated UUIDs, so equality is checked using exact relative test
path, class chain, original name and pytest parameter indices; raw IDs/logs remain.
Test sources and both jobs' runner, PostgreSQL, environment, Python, uv, patched
Hermes preparation and locked dependency installation are unchanged/equivalent.

The affected cases run once:166passed,1skipped. The skip is the existing optional
vector-capable Core PostgreSQL case requiring DMB_NATIVE_RECAP_TEST_ADMIN_DSN;
it is not configured by either affected workflow. The ordinary agent reconstruction
case passed on the disposable APP test database. No provider/live-data writes.

Evidence: private runtime-evidence/q01-published-graph-authority/
ci-deduplication-{collection-proof,environment-proof,indexed-collected}.json and
ci-deduplication-retained-tests.log. Initial literal-name comparison is retained;
its nine UUID-only differences are not treated as missing coverage. This establishes
selection preservation, not timing gains or a cleaned performance baseline.
