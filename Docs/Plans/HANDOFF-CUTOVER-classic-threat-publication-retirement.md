# Retire mounted classic Threat publication

Status: COMPLETE — accepted and merged as PR #4234. Owner MIND; explicit operator authorization covers the full vNext
lane's design, implementation, review and merge. Serial successor to accepted
PR #4233 at `43c39419cb9024054d6ef78db99746111f04178b`. Branch
`codex/v10-retire-classic-threat-publication`; reuse existing task Buddy checkout
and accepted Core/WK runtime. Pin this assignment before runtime edits.

## One coupled outcome

Retire the eight mounted classic Threat publication POST actions with HTTP410
after existing request/ID and actor admission, before storage/source/head/authority
access. Retain GETs as recorded history. Commit GET always advertises
`retry_allowed: false` without rewriting the durable record. Keep all known states
and unknown outcomes honest; absence is not proof that a prior dispatch did not
commit. Never reconcile by publishing, automatically reprepare, release a retained
uncertain pointer, follow a successor into a fresh write, or migrate old IDs.

Replace the classic ThreatPublicationPanel with historical inspection only.
Preserve the exact browser session pointer and server ledgers. No begin, refresh,
cancel, retry, candidate preparation, identity decision, proposal or commit call.
Historical inspection is independent of current graph head, mutable draft version,
accepted mechanics freshness and source availability. Validate response identities
against retained pointers before displaying facts; stale async responses may not
cross draft scope. Missing/corrupt/unavailable history remains unresolved, with
original storage bytes intact. Read-only reread is allowed.

Workbench keeps V1 mechanics save/reopen and retained history reachable; remove
its classic publication head preflight and fresh controls. Native V2 creation and
mechanics association are unchanged. No new compatibility/reconstruction API.
The library classic writer remains explicit retirement debt; do not claim its
excision from HTTP retirement. GET locking may create lockfiles/directories:
zero durable-ledger mutation does not mean zero filesystem effects.

API retirement and UI removal are indivisible: splitting them leaves a knowingly
active UI dispatching retired mutations. Review map: four small route closures,
one history-response flag, read-only panel/state replacement, Workbench mount,
then owning mounted/backend/UI proofs. Preserve useful library/codec tests; replace
obsolete fresh-publication UI/route expectations only for this explicit retirement,
not to obtain a faster green suite. No test selector or exclusion changes.

## Exclusive fourteen-path lease

1. This handoff and exact evidence/disposition.
2. Docs/Plans/HANDOFF-CUTOVER-native-threat-draft-admission.md: backward PR4233 merge settlement.
3. apps/live_control_server/routes/threat_publication.py.
4. apps/live_control_server/routes/threat_publication_identity.py.
5. apps/live_control_server/routes/threat_publication_proposals.py.
6. apps/live_control_server/routes/threat_publication_commits.py.
7. apps/live_control_server/services/threat_publication_commits.py: GET retry flag only.
8. apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.tsx.
9. apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx: classic mount/head/dock only.
10. apps/live-control-ui/src/statblocks/publication/ThreatPublicationPanel.test.tsx.
11. apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx: affected classic controls/history only.
12. NEW tests/test_classic_threat_retirement.py: complete mounted POST/GET authority proof.
13. tests/test_threat_publication_identity_routes.py: retired POST and retained GET contract alignment.
14. ci/test-classification.json: inventory entry for the new backend test only; no selection/exclusion change.

MIND owns backend and docs; Hubble may own the four UI paths exclusively after
explicit dispatch. Aristotle reviews independently without edits. No shared
source/state collision; one PR, one branch, serial delivery. Read-only fixture
imports allowed. Return to MIND/rebrief before any additional path is edited.
No native V2, schema, codec, API client, dependency, Core/WK, auth policy, routing
registry, migration, deployment, provider, ingestion or retrieval benchmark changes.

## Re-anchor and ownership

Fetched main43c39419; clean existing checkout. Inspected58 open PRs, including
3824 hosted,3808 portraits,3716 historical mechanics and3729 preview guidance;
actual patches do not own these fourteen paths. Existing auth wrappers, API client,
Build/Plan shells, native routes, mechanics persistence and hosted test owners stay
outside this lease. No adoption or merge of those unrelated PRs.
Projects parent UUID `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8` and executor write
access verified before new task scratch allocation. No new environment/worktree.

## Owning verification and completion

- Mounted valid requests to all eight POST paths return410; storage, graph, source
  and publication tripwires stay untouched. Existing denial/invalid-input admission
  continues to fail closed. No fresh durable mutation, including cancel/retry.
- Real retained operation/identity/proposal/commit GETs preserve recorded state and
  ledger bytes; commit retry is false even for formerly retryable states. Missing,
  corruption and outage cannot imply safe fresh publication. Existing historical
  producer/adapter tests remain library controls.
- Mounted panel: no pointer, all retained stages and terminal/ambiguous states,
  missing/corrupt/outage, mismatched identities, changed draft version, remount,
  delayed response after scope change, read-only reread. Prove session bytes remain
  unchanged and no mutation API is called. Workbench history needs no current head;
  V1 mechanics and native V2 route consumers remain intact.
- Affected backend/auth/native preservation cohorts, focused mounted UI tests,
  exact-source repo-owned hosted verifier, and one meaningful full-discovered
  frontend diagnostic. Record every inherited/new failure accurately; do not call
  the bounded hosted sample full release qualification. Independent exact-head
  cumulative source/evidence review before merge.

Keep the full goal active. After this slice: callable classic writer/public API
retirement, remaining historical/current boundary and import isolation, compatible
serving rollout, later-write-safe rollback, and V11 deployed acceptance. Do not
rerun the frozen retrieval baseline or launch provider/ingestion experiments.

## Preflight rebrief before classification write

MIND adopts Aristotle's preflight correction: add the new test's inventory entry
as path14 before editing that owner. This is required additive inventory, not a
selector or gate change. All13 original lease paths remain unchanged. Existing
identity test cases are retained, with their historical setup moved to library
producers and their useful mounted GET assertions preserved. The browser codec
stores identifiers only, not the full original confirmation body. Historical
inspection must remain mounted when a retained V1 draft is edited out of the
mechanics-saved state. Missing/unloadable drafts remain a limitation unless an
existing entry already supplies that ID; no arbitrary orphan recovery is claimed.

## Accepted checkpoint and exact evidence

PR #4234. Accepted source `af3bb062ca03238cf857d7cc5f3081a24ec21c54` against
base `43c39419cb9024054d6ef78db99746111f04178b`. Independent Aristotle final
bounded ACCEPT is review `5992289571`; Hubble independently audited the evidence
and exact-base comparison, without claiming independent source review of his UI.
The current lane is V9/V10 preparation, not a serving cutover or V11 acceptance.

The eight classic HTTP actions are retired. Recorded history is inspection-only;
no absence, unknown outcome or newer draft version clears the browser pointer or
authorizes publication. Missing/unloadable draft entry is still a limitation:
this is not arbitrary orphan recovery. History may create lockfiles/directories;
recorded ledger bytes remain unchanged. V1 mechanics and native V2 creation remain.

Backend execution at `d036560813054b0aab12672f71f0e3c5f6a0c3ac`:
139 owning + 96 native + 376 preservation + 316 authorization = **927 passed**,
zero failures/errors/skips. Source was frozen and clean. Backend source, tests and
configuration are byte-identical at accepted af3; do not claim backend execution
at af3. Installed files match before/after: Core179 + DND39 at
`d206e56a9aa34ae6eb6cc7ac61980a7ac8919c4d`; WK14 at
`348c0dbf5156e7e7d5d951de90b9086501fc834f`. No dependency sync occurred.

At exact af3, focused UI **194 passed**, with existing dependencies, Node22 and
the shared resource lock. Official fresh-locked hosted verifier: **1,414 selected
passed / 147 filtered**, build, parity and canonical validation exit0. Node22.23.0,
npm10.9.8, eight workers. Official full-discovered proof remains **RED**:

| Exact source | Passed | Failed | Report-only skipped | Build | Validator |
| --- | ---: | ---: | ---: | ---: | ---: |
| Candidate af3 | 8,335 | 103 | 2 | 0 | 1 |
| Base43c | 8,339 | 103 | 2 | 0 | 1 |

Every failed ID and first diagnostic line matches the exact base; zero new,
resolved or changed failures. The App E7 remount failure is reproduced at base,
not inferred from the older 102-failure reference. The same two report-only
skips (BuildSurfaceShell narrow-sheet and vendored statblock-client contract)
explain collection-parity red; no inventory omissions. Builds passed on both.
Only the two leased UI test files changed case inventories: 53 obsolete publishing
cases replaced by49 history/refusal cases, net minus4. No case changes elsewhere,
selector/exclusion changes or backend identity case deletion. All six existing
backend identity cases retain useful read/admission/privacy proofs with historical
fixture setup through library producers.

Original candidate defects are retained in evidence: the first backend smoke had
two fixture errors (proposal digest and restart principal), corrected before its
expanded45-pass proof; d036 focused UI had192 passes/two owned failures. Af3 fixes
history-dock replacement of disabled mechanics controls and exact B candidate
membership; assertions were strengthened. Those two UI failures are repaired
candidate defects, not inheritance. A proposed broad test-file rewrite was rejected
by automatic review and never executed; the safe targeted adaptation retained all
six original backend cases.

## Evidence, resources and continuation

MIND retains evidence under
`/home/drakosfire/Projects/.codex/v7-elderwyld-scope/scratch/v10-classic-threat-retirement/`:
`qualification-af3bb062.json`, backend JSON/XML/logs and installed audits,
`focused-af3bb062-results.json`, official hosted/discovered receipts,
`base-discovered-43c39419/`, `exact-base-comparison-af3bb062.json` and
`continuation.json`. Both base/candidate receipts have clean source, matching
artifact hashes, completed cleanup and independently absent temporary roots.
Backend95261, focused96586, frontend34022 and base51669 are terminal. Eight
attributable native databases and clients were independently absent, with zero-
client lifecycle records before drop. Other owning fixtures did not retain exact
names: successful teardown only, no independent absence/pre-drop-zero claim.

No new manual worktree, verification mirror or environment. Reuse the existing
task Buddy checkout and accepted historical-manual runtime cache. MIND retains
this scratch (15,543,130 bytes at pre-seal inventory) and new task cache
`/home/drakosfire/Projects/.codex/v7-elderwyld-scope/cache/v10-classic-threat-retirement/`
(2,164,834 bytes), for active full-goal evidence and continuation. The verified
backing filesystem UUID is `48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8`. Only owning
verifier/fixture temporary outputs were removed; no manual artifacts were deleted,
and reclaimed bytes were not measured. No serving process, mount or global
configuration was changed. After active use ends, inspect processes/mounts,
dirty worktrees and unique commits before any specifically authorized cleanup.
This follow-up applies to each retained scratch/cache and the reused checkout;
never blanket-clean shared caches or another lane's artifacts.

Accepted merge: `e4829505224a29ea9b4d3688ac22762588d60b05`, seal
`9d63c1c0232c8f8f93fbc6777b4417a431470920`, tree equality
`b880babefea207aaa1728e054b558ffa3e29ac50`. Reviews5992289571 and5992315513
accept the bounded implementation/seal; CI44732012856/44732012858/44732012841
pass. Backend evidence at d036 is byte-identical in the backend at af3; frontend
qualification tested af3 directly. This merge equality does not claim execution
of the actual merged commit or a serving deployment. This successor settles the
former merge-pending field without changing the retained red full-default result. What remains false: callable classic library writers are not
excised; Kernel current/public WorldGraph APIs are not yet quarantined; deployed
current authority, later-write-safe rollback and V11 are not accepted. Core main
was re-fetched at d206 and matches Buddy's accepted pin. Next primary question:
which remaining current/public APIs and imports require an explicit historical
compatibility boundary before serving rollout? Audit real consumers; do not add
new reconstruction features for unused helpers by default. No serving change,
provider/ingestion experiment or frozen retrieval baseline rerun occurred here.
