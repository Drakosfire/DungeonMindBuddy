# Fresh source-navigation import isolation

Status: COMPLETE — accepted implementation; documentation seal/merge pending.
Owner MIND, with operator authorization for the full optimized vNext lane's design,
implementation, review and merge. Delivery is serial, not an unmerged stack.

## Current checkpoint

- Roadmap phase: V10 current/public legacy retirement, before deployed V11.
- Base/main anchor:817354e15398239947cc86736e58d87a3e0f0b1c, merged prerequisite4237.
- Accepted implementation: PR #4236 source160d531979d0c69cd1f2d56dacf2283fcbe7b2bc.
- Independent COMMENT [review5994432216](https://github.com/Drakosfire/DungeonMindBuddy/pull/4236#pullrequestreview-5994432216)
  accepts cumulative source/evidence against that base.
- Last accepted predecessor:4237 source6c4d77da, seal353a7fa58, merge817354e;
  source/seal reviews5993948969/5993964656, tree equalitya922e61225b4695307dae0a07f41c56ba1e7bf11.
- Core pin e56a3faee749ced9ac0913da5d7282da84b7cc2d and WK348c0dbf remain unchanged.
- Remaining delivery gate: documentation delta review and short checks, then
  guarded merge. No actual merged execution or serving deployment is claimed.

## Outcome and invariant

Fresh navigation module imports and NativeBodyNavigation dispatch do not load
retained classic readers merely because historical navigators share modules.
NativeSourceNavigator._access defers its classic imports until after corpus-origin
dispatch and binding verification. CorpusSourceNavigation.access/search defers
classic imports until existing eligibility/reuse/binding boundaries. Both runtime
files have identical non-import ASTs against accepted817354e.

Original authority, current-source checks, admission before body IO, exact citation
bytes, source/catalog correspondence, durable prefix/replay, scan counts and ranking
are preserved. No new class, compatibility API, schema, dependency, source-admission
rule, migration, UI or deployment behavior. The accepted4237 action-less-policy guard
is inherited from base; it is not another capability in this PR.

## Exact twelve-path lease and review map

1. Docs/Plans/HANDOFF-CUTOVER-native-source-navigation-import-isolation.md: current state/evidence.
2. Docs/Plans/HANDOFF-CUTOVER-native-projection-import-isolation.md: settle4235 merge.
3. apps/live_control_server/services/native_source_navigation.py: deferred imports only.
4. apps/live_control_server/services/corpus_source_navigation.py: deferred imports only.
5. tests/test_native_source_navigation_runtime.py: actual mock owners, cold imports/dispatch.
6. tests/test_corpus_source_navigation.py: actual mock owners, scan/admission tripwires.
7. tests/application_state/test_corpus_source_search_postgres.py: replay mock owner only.
8. tests/test_native_source_origin.py: supported typed-span origin fixture through actual Core.
9. tests/application_state/test_native_source_navigation_postgres.py: owning0053 roundtrip proof.
10. tests/test_agent_native_corpus_sources.py: current HTTP passage/prose fixture and exact citations.
11. Docs/Plans/HANDOFF-CUTOVER-retained-plan-batch-coverage.md: settle4237 merge.
12. tests/test_plan_jev_acquisition.py: supported-span fixture for actual two-object broker proof.

MIND owns continuity/HTTP/broker/mocks; Hubble authored the origin and0053 fixture
repairs; Aristotle independently reviewed all source/evidence. All workers are
finished. Rebrief MIND before another path or production behavior. No CI inventory,
selector or exclusion change. Required proof repairs stay with this boundary; the
independently useful runtime defect was split into prerequisite4237 first.

Authority was pinned before changes: initial17210d94, post-prerequisite eleven-path
rebriefa579861c/ownership7d65bb8d, then before-edit broker rebriefc223e662.
Main817354e was re-fetched; open PR path audits found only old3307/2225 overlaps
on corpus navigation/current HTTP fixtures. Their heads8cb62d310bba188ed328459def044dca7792b520
andf720e5f55f5b357dba09977663306482d5188a65 remain unmerged/unmodified. MIND
allocated current-main import/fixture regions explicitly; no old ranking/status
proposal is adopted. The added broker path had no open overlap.

## Accepted exact-source proof

| Cohort on160d5319 | Passed | Inapplicable skipped | Failed/errors |
| --- | ---: | ---: | ---: |
| Owning/navigation/origin/APP persistence | 180 | 2 | 0 |
| Fresh native source/corpus/writer/HTTP | 73 | 0 | 0 |
| Retained activation/inventory/acquisition | 53 | 0 | 0 |
| Auth contract | 316 | 0 | 0 |

The only skips are Play parameters of Plan-only selection/finish assertions.
Both corresponding Plan cases pass; exact skip IDs/reasons are checked in the
qualifier. Required proof omissions0. APP persistence uses real PostgreSQL with
in-memory Core where applicable; this is not a Core PostgreSQL witness.

Cold subprocesses fence both module imports and actual fresh navigator selection
using validated native authority/matching context, with database construction/
connection forbidden. Retained tests preserve binding drift, body-IO tripwires,
selected/unselected/repeated scan and donor verification. The actual broker keeps
one native context, two ordered durable operations with returned pins, and closed
lifetimes. No original authority is translated into fresh current truth.

Current HTTP variants exercise matched-section acquisition or explicit expansion/
full-source inspection followed by a proper subsection vote. They assert two/four
controller calls and one acquisition; actual body aliases, source identity, UTF8
passage digest/lines, writer inclusion, exact selected reopening after head advance,
unchanged replay/history and binding/auth refusals. Covering reads retain original
read ID/selector policy; derived citation extents stay narrower than the full source.
No second read is fabricated or whole-document text made writer-eligible.

Installed before/after audits are identical: Core180+DND39 at e56a3fa and WK14
at348c0dbf, exact committed bytes and site-packages origins. Changed-path Ruff
remains RED with96 inherited diagnostics/zero new; no suppressions or unrelated
formatting. Official exact-SHA hosted frontend1414 selected passes/147 filtered,
build/collection parity/validator0, clean isolated source, Node22.23.0/npm10.9.8,
eight workers. Artifact hashes match, cleanup complete and temporary root absent.
All three short checks pass on160. The prior full-default frontend diagnostic
remains red/not release-qualified; this PR does not turn that into whole-suite green.

## Architectural lessons and retained history

- Core admits the original fixture anchor; Buddy intentionally filters unsupported
  heading locators. Positive origin/broker proof needs explicit digest/line-bound
  span evidence published through Core. Nullable V2 metadata was not the cause.
  Shared heading fixtures, locator policy, source authority and admission are unchanged.
- Test0053's own constraint upgrade/downgrade in a rollback-only isolated transaction.
  Historical Play JSON text, current constraint and schema version are restored.
  Do not downgrade current head through0169's forward-only recovery guard or claim
  this unit proves a full-schema rollback. Populated-navigation refusal is retained.
- Current Plan V2 receives evidence prose and requires acknowledged writer passages.
  Fix synthetic transport/candidate fixtures to that contract, not production
  passage eligibility or prompt privacy. Legacy helper defaults remain unchanged.

Earlier4f907/a2ce failed runs and working fixture mistakes remain FAILED evidence,
not relabelled green. Exact-base052bea/817354e archive diagnostics establish the
fixture/compatibility debt;4237 separately repaired the optional-action defect.
Detailed chronology belongs in PRs, artifacts and Git history rather than this
current-state handoff. No frozen retrieval baseline/provider/ingestion run occurred.

## Evidence and resource continuity

Owner MIND retains /home/drakosfire/Projects/.codex/v7-elderwyld-scope:

- scratch/v10-native-source-navigation-import-isolation/: backend-160d5319.json,
  cohort XML/logs, before/after installed audits, resource-audit-160d5319.json,
  frontend-160d5319.json, hosted-160d5319/evidence.json, Ruff and failed-run reports.
- verification/native-source-navigation-base-052bea and
  verification/native-source-navigation-base-817354e: exact-base backend snapshots,
  with their archives retained in task scratch for failure attribution.
- cache/v10-native-source-navigation-import-isolation and reused qualified
  cache/v10-native-projection-import-isolation/env; no dependency mutation/new env.
- Reused Buddy checkout; old40c176da is protected by local branch
  codex/v10-source-navigation-pre-prereq and original PR/Git evidence.

Pre-seal sizes: scratch73,273,677 bytes, cache0 bytes, baseline mirrors32,601,788
and32,601,443 bytes. Backing UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8 and write
access verified. Six recorded test/runner PIDs are absent. Exact APP fixture database
names were not retained: successful teardown only, no independent named absence
claim. No manual filesystem deletion; manually reclaimed bytes0. Official verifier
roots were removed by their own lifecycle (paths in receipts); reclaimed bytes
were not instrumented. Retain these paths for the active full goal; after use,
inspect processes/mounts, dirty worktrees and unique commits, protect required
commits, then perform only specifically authorized cleanup.

## What remains false and next dispatch

Serving rollout, later-write-safe rollback and deployed V11 latency/auth/order/
exact-citation acceptance remain incomplete. Saved-section/body-opener modules
still eagerly load historical adapters; whole-server isolation and remaining
unmanaged projection/recap/context plus current/public Core legacy retirement
are not done. This source merge alone does not deploy the optimized experience.

Next primary question: can current native-body reopening import without loading
historical section/passage readers while retaining original saved-section authority?
Read-only preflight identifies agent_native_source_sections.py and
agent_source_passages.py, retaining the existing SourcePassageOpenError owner.
Pin a new serial lease after this merge; preserve current/retained exact reopening,
replay and authorization. Safe parallel work is read-only consumer/route auditing,
not another overlapping implementation. Full optimized Elderwyld goal stays active.
