# Preserve reported cache-write usage

Status: SETTLED. PR1810 merged723224944eda21888d77f2d36ea067b2e24c2ddb after independent exact0908e130 approval,196 author tests and30 independent scoped tests. Protected API delivery selected the reviewed installed Hermes artifact without modifying shared .venv; source tree273cf1275e98dee76410b8802e3eb297f4893d96. Explicit writes/zero/missingness verified at installed production namespace. Retained Q01 replay preserves9781 writes/25797input/233output, with zero provider calls and original bytes unchanged. All3588 APP rows,1097 native rows and39933 retained files are unchanged; schemas0077/0017 and UI11f83820 remain. Ordinary saved Conks Plan loads. Lease released; successor is operator-resumed PR1807. Historical ownership: PRIME's benchmark regression program.
Basec8565dc8b26bcd68811b33bad002af8cc5445049; branch codex/reported-cache-write-usage;
reuse buddy-context-loop and current dependencies. Serial successor to1809.
Plan1807 remains paused; HOSTED1802 and BENCHMARK harness are disjoint.

Observed: Q01 raw Responses receipts report input_tokens_details.cache_write_tokens;
the pinned Hermes normalizer reads cache_creation_tokens and exports canonical0.
Buddy therefore loses reported writes. Its current rate card cannot price writes.

Invariant: preserve the current provider's actual write bucket, distinguish an
unreported bucket from reported0, and preserve total input/output. Repair at the
pinned dependency normalization/hook, not by reconstructing raw usage downstream.
Do not add a backward field alias, a second provenance ledger or a guessed price.
An otherwise recognized model with reported writes gets unavailable cost until a
rate card can price that bucket; never label the incomplete estimate as complete.
Keep original raw benchmark evidence and rate snapshots unchanged.

Expected write lease:
- this handoff
- Docs/Plans/HANDOFF-AGENT-tool-success-count.md (predecessor settlement)
- patches/hermes-agent/0001-pre-dispatch-budget-veto.patch
- apps/live_control_server/services/agent_turn_trace.py
- tests/test_agent_turn_trace.py
- tests/test_hermes_usage_reporting.py (new provider-free pinned-source boundary test)

Dependency ownership: current API and worker distribution use the checkout's .venv
and generated out/hermes-agent. Do not mutate them during candidate preparation.
PRIME may prepare one candidate source under the established private recovery root
hermes-cache-write-candidate, using the existing pinned prepare script and local
upstream Git objects. This is necessary concurrency isolation from live consumers,
not another implementation worktree/environment. Reuse all Python dependencies.
PRIME may build and install one wheel within that candidate root for isolated
verification, reusing the existing interpreter and dependencies. This is a versioned
package artifact, not a new environment. Clean redundant candidate copies after
adoption; retain unique evidence/rollback.

Verification: exact patch applicability/source manifest; real pinned normalization
and post-request hook with synthetic SDK-shaped usage, explicit writes/0/missing;
product normalization and cost projection; retained raw Q01 usage replay without
providers; exact cumulative Bugbot review. Commit/push/open one PR. Dependency
installation into shared live dependencies and protected API delivery require a verified owning-process stop,
retained row/file fingerprints and repair/rollback protection. No migration or new
live provider run is required for this observer-only slice. Do not update prices.

Critique: changing only Buddy's mapper cannot recover a field already erased by
the dependency. A patch must be reproducible from the pinned upstream tree, and
unknown prices must remain unknown. No edits to live site-packages or generated
source are allowed as an implementation shortcut.
