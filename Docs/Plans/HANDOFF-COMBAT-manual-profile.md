# COMBAT — run persisted system-neutral ordered encounters

ACTIVE under the operator's full Combat implementation/review/accepted-merge and
local delivery authority. Serial successor to #3995, merged
`087c293812e1699e0088062484df31367343b93a`. Original base
`82594fb5bb78a6c2e34ffefb0890fcba4d549250`; qualification rebase
`b4ec5408180d74b8ef0a9cc9543271df6e5fb02c`; branch
`codex/combat-manual-profile`, existing isolated fc67 checkout. No unmerged parent;
one open implementation PR. Root is the assigned Combat designing owner.

Outcome: create, prepare, materialize, edit, explicitly recover, save and reopen a
manual profile using named stats/resources and ordered turns with optional rounds.
The synthetic Crossing encounter uses Position/Resolve and Stress/Momentum, with
no required AC/HP/initiative. It shares standalone and Plan/Play hosts, identity,
exact source access and draft ownership. Side/spotlight pacing remains a separate
required successor. This slice does not add profile conversion or automatic rules.

This vertical capability stays together because exposing persisted v2 records
without compatible access, initialization, recovery and rendering can corrupt or
lose work. Review by the owner map below; each boundary has independent evidence.

## Exclusive expected writes and review map

1. APP: combat_encounters/{manual_profiles,manual_encounters,repository,service,
   scene_template_types,scene_templates,adoption,access}.py; play/{session_encounter_types,
   session_encounters}.py; new migration
   migrations/versions/20261118_0163_manual_combat_profiles.py. Keep existing v1
   DTO definitions/serialization in types.py and rulesets.py unchanged.
2. HTTP: services/combat_encounters.py and routes/{combat_encounters,
   combat_scene_templates,combat_run_encounters}.py. Existing paths/access owners
   stay intact; no main.py, authentication registry or provider-contract changes.
3. Client: combat/{combatTypes,combatApi,combatRecovery,validateCombatRecovery,
   sceneTemplatesApi,runEncountersApi}.ts; generated combatRecoverySchema.json and
   its generator; PlanSceneEncounter.tsx, RunSceneEncounter.tsx; shared
   surface/modules/CombatRosterModule.tsx; combatRoster.css; new ManualCombat*
   components/helpers/types within src/combat. Existing legacy editors remain
   narrowed to legacy DTOs; a v2 actor must never blindly reach .hp/.ac code.
4. Tests: affected existing Combat API/module/recovery/schema/Plan/Play tests;
   actual-App selectedWorld/WorldOwnerApp.integration.test.tsx;
   new tests/application_state/test_manual_combat_postgres.py and relevant manual
   client tests; migration/HTTP/source/ownership guards in owning existing test
   files as needed. Add exact test paths to ci/contracts.json and classification.
5. This handoff and truthful predecessor settlement in versioned-records handoff.

Open #3668 owns BuildPdfStatblockReview.tsx, combatMinimums.ts and HTTP
services/combat_mechanics.py; those remain read-only. Reuse the existing source
verification entry points rather than editing their producer. Hosted integration
draft #3824 is a consumer; no authorization policy redesign or other owner lease
is absorbed. Re-anchor and split/return before exceeding this write set.

## Migration and state authority

The original PRIME allocation in #3877 was Combat0162 after0161, expressly
subject to confirming the current sole head. Main subsequently merged
`20261118_0162_saved_statblock_continuity.py`. Root audited the current migration
head, published assignments and open PR metadata: no0163 reservation was found.
Under the operator's existing Combat design/implementation authority, Root adopts
Combat20261118_0163 with parent20261118_0162 and has explicitly notified PRIME.
This is a bounded correction of the unmerged migration, not inferred approval from
elapsed time. The former self-imposed wait gate is withdrawn on this concrete
re-anchor/ownership audit; any actual overlapping lease must still be resolved.

The branch is rebased on `b4ec5408180d74b8ef0a9cc9543271df6e5fb02c` and its sole
head is independently confirmed0163. Renumber, parent and fresh-database rehearsal
travel together. The merged0162 is forward-only: rehearse0160→0161→0162→0163
forward on a uniquely owned fresh database with an unchanged legacy row; do not
downgrade through0162 or rewrite any applied migration identity. Old planned0162
browser/database results remain diagnostics, not current qualification.
Preserve v1 rows, aliases,
historical template/receipt/digest preimages and existing JSONB byte constraints.
Admit only matching version pairs. Downgrade refuses retained v2 data/history.
No live/operator database migration or record mutation is authorized here.

Existing API8001/UI5202 and owned immutable preview5218 stay untouched. Disposable
tests own unique DB/template/clone names and external scratch under the verified
Projects filesystem. Browser/API services need newly checked, exclusive ports
(candidate8018/5219, fixture providers only if explicit). Audit startup and state
paths before boot; no background provider jobs or operator stores. Preserve exact
source/process identity and cleanup. Local delivery uses accepted exact source,
never an in-flight hot-loaded branch presented as ready.

## Invariants and acceptance

- Existing access.guard/principal/World/run/CAS and rollback boundaries remain.
  APP owns immutable profile digest; Save takes only draft and expected revision.
  Source/identity admission is independently verified; existing actor source cannot
  change through ordinary Save. Old generated-add/AC-HP adoption refuses v2 before
  mutation. Source-only replacement is a future explicit owner if unsupported.
- Versioned manual initialization preserves prepared values/bounds/notes/status/
  participation, mints fresh actor/group/side identities and remaps references,
  resetting only profile-declared turn state. Legacy initialization is unchanged.
- One active recovery/Web Lock/CAS owner per encounter. Exact pending Save bytes
  survive uncertain outcomes; delayed acknowledgements retain later edits. Unknown
  raw recovery and foreign/stale scope are preserved/refused. Render authoritative
  pinned profile labels/types, not a tampered local copy with a matching hash string.
- Shared manual editing covers all named values and resource bounds, explicit
  adjustments, independent out-of-action/return, status/notes, grouping, ordering,
  current/next and optional rounds. Stable IDs preserve edits through grouping,
  projection and reorder. Generic authored sheets are distinct from exact source;
  no mapping is inferred from labels or source game mechanics.
- Exact-SHA backend contracts prove migrations/actual JSONB limits, v1 historical
  controls, v2 persistence/cold reads/CAS/principal/World/run rejection/rollback,
  prepared/run independence and source protection. Client tests prove generated
  schema/semantic recovery, unknown Save and host continuity. Required exact-head
  hosted/discovered frontend evidence and exact-base comparison retain inherited
  failures visibly red; independent code/evidence review precedes merge.
- Browser acceptance against actual API/disposable DB must demonstrate the full
  synthetic non-D&D flow, governed Graph selection/source access, defeat/return
  independent of zero, all field edits, Save/reload/recovery and wide/narrow crowded
  hosts. Synthetic transport-only evidence is insufficient for this activation.

The full goal remains incomplete until this integration, side/spotlight successors,
real runtime delivery and integrated acceptance are proven. Detailed inspected
owner map/designs/evidence: `/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

Integration discovery: the existing access.validate_binding decodes the retained
materialization request. Root expands this same vertical slice to that file only
for explicit v1/v2 request decoding; all existing receipt, World/run/scene and
lifecycle comparisons remain required. Reopen and mutation tests must exercise
this owning boundary. No new authorization capability or registry is introduced.

## Implementation checkpoint — not accepted or complete

The working vertical now has explicit persistence/HTTP version handling, manual
scene initialization and receipt decoding, profile creation in standalone/Plan,
shared manual rendering in all hosts, Graph identity with optional exact source,
stats/resources/bounds, participation, statuses/notes, groups and ordered turns.
Recovery retains exact pending Saves and later edits; local profile replacement
is refused against the server-pinned profile. Old AC/HP import/adoption refuses v2.

Working diagnostics (not exact-source qualification): 104 owning persistence/HTTP
checks pass using a task-local frozen uv environment; 40 editor/recovery/legacy
module checks and a separate 33 recovery/Plan/Play checks pass; typecheck passes.
The initial default test DB connection refusal and stale shared Python Core import
failure remain in external logs. The isolated server is container
`buddy-combat-manual-fc67`, loopback33073, data under external
`manual-working/pgdata`; tests use owned template/clones only. Task-local venv uses
the unchanged uv.lock and verified pinned Hermes tree273cf127; ignored source
`out` points to external generated dependency storage. No shared API/UI changed.

Preliminary review found two storage defects: cancellation-only v2 history was
missing from downgrade refusal, and compact profile size did not prove JSONB text
size. Both have code fixes and owning disposable DB regressions; final independent
review still pending. Downgrade locks history writers through its refusal proof.

Remaining before acceptance: finish editor usability/keyboard/projection focus and
crowded wide/narrow layout; strengthen manual host/source/auth/history/CAS tests;
run actual API/disposable DB browser journey after startup isolation audit;
cumulative exact-head review and required exact-SHA backend and hosted/discovered
frontend evidence with base comparison. The migration sequence rehearsal must be
green and retained. Side/spotlight remains a later required slice. This checkpoint
does not authorize merge, deployment of in-flight code or completion claims.

### PR4008 refinement checkpoint

Draft PR: https://github.com/Drakosfire/DungeonMindBuddy/pull/4008. Preliminary
client review found no-blur status loss, an incorrect Saved label for an unknown
pending Save, replacement-in-flight edits, missing complete draft byte checks and
input clearing after refused additions. These have code fixes and focused
regressions; 58 frontend checks and typecheck pass. Thirteen manual PostgreSQL/HTTP
checks pass, including authenticated version/CAS/World rejection and source
admission/replacement fences. These remain working diagnostics, not qualification.

Browser diagnostic uses actual Combat/scene/run routes and APP PostgreSQL with
synthetic governed Graph/DMS providers, isolated World metadata and a focused route
composition that does not run product main lifespan or background model workers.
It proved non-D&D create/edit/participation/Save, no-blur status recovery, exact
source preview/projection, and independently persisted source/values at revision4.
Four synthetic actors are retained. Wide/narrow inspection found and fixed unused
standalone width and deferred-renderer scroll growth; final crowded density and
all-host journey still required. Evidence is external `manual-browser/` with
read-only persisted snapshots, source hashes, logs and explicit fixture limits.
Screenshots are `combat-manual-profile-source-{wide,narrow}.jpg` in this chat's
visualizations directory; they are diagnostic witnesses before final acceptance.

Earlier owned rehearsal services were API8018 (exec session49936), UI5219
(session81881), container `buddy-combat-manual-fc67` port33073. API lifetime owned
its unique template/clone and cleaned them on graceful shutdown as recorded below.
The historical context/database name is external `manual-browser/context.json`;
it is not a live-service receipt. Do not restart shared8001/5202/5218.
Earlier terminated setup failures and successful cleanup remain in separate logs.
The final refinement diagnostic adds nine passing editor cases for staged input,
unset focus, removal/round/group cleanup, no-blur status retention, pending labels,
late acknowledgements, exact retries and refused-write input preservation. New
test inventory is1561 files and classified; final refinement typecheck passes.
The refined screenshot is `combat-manual-profile-refined.jpg`. These are still
incremental working diagnostics; no exact-head approval or full browser acceptance.

### Compact roster and Plan/Play checkpoint

Manual rows now use a descriptor-driven table with stable actor/field keys,
horizontal scrolling and a pinned participant column on wide screens. Current
actors remain visible inside collapsed groups; source selection stays attached
through reorder/collapse. Bounds, notes and extra actions remain available without
forcing tall cards. Narrow controls remain reachable without document overflow.

Real browser Plan creation exposed a transport `schema` versus retained `schema_`
digest mismatch. Client normalization now matches the existing Python non-alias
preimage, with shared `manual-scene-create-v2.json` fixture and Python/TS checks;
legacy receipt preimages remain unchanged. Generic committed manual readings now
refresh prepared history after Save, and the automatic refresh only advances to
a newer committed revision. Preliminary review found the older-editor/newer-history
case; the advance-only condition and regression address it. Final review pending.

Working checks:64 frontend cases passed at the table checkpoint; the subsequent
Plan/editor regression files pass23 cases;103 profile/record cases and typecheck
pass. These do not replace exact-head qualification. Browser captured preparation3
into Play, materialized fresh actor/group identities, edited/saved live2 and
returned to unchanged preparation3. Preparation then advanced independently to9
with16 actors, collapsed groups2+12, keyboard turn movement and a narrow Resolve6
edit. Read-only PG evidence proves captured/live/current independence and exact
source/profile equality. External evidence: `plan-play-browser-persisted.json`,
`crowded-table-browser-persisted.json`, `pre-resequence-owned-browser-snapshot.json`.
Screenshots: `combat-manual-{plan-source,play-source,compact-groups,compact-narrow}.jpg`.

The owned API49936 and UI81881 were gracefully stopped before migration
re-sequencing; both handles are terminal and the API context cleaned its owned
template/clone. The temporary browser tab was closed. PG container33073 remains
owned for the next verification run; shared processes were untouched. Do not reuse
the old planned0162 database/evidence as current migration qualification.

PRIME was explicitly notified of both the migration collision and the hosted
consumer PR3878/3879 route overlaps. Combat widens DTO versions without editing
their branches or authorization owners. The bounded0163 sequence correction is
recorded above; no PRIME reply or approval is fabricated. Full qualification, independent exact-head
review, accepted merge/local delivery and side/spotlight successors remain open.


Final diagnostic checkpoint: exact fc874f827 backend227 and hosted frontend/build
passed. Full discovered was red161 versus exact base b4ec540818 red160. The sole
new failure was the actual-App Combat test spying on the retired legacy-only list
entry point; update its reader spy to the version-aware API and assert both v1/v2
create/Save paths remain untouched on boot. No product runtime change is needed.
Keep all inherited failures and collection omissions visibly red; compare full
messages/case multiplicity before acceptance. Final exact-head evidence and review
remain required after this test correction.

## Accepted predecessor settlement

#4008 merged as83013db27115007435b586cf657c39119a47b60a after independent approval
of exact head a0b3c7aa4adc2233b39cd66d35b82b7b92b37f9e. Backend227 and hosted1410
passed; full discovered remains red160 inherited failures/two extra skipped cases,
with18 additive passes and no omissions against exact base b4ec540818. Paired
Staged diagnostics resolved failure-depth variability with matching base/head
causes. Browser ran clean fc874f8/migration0163; its product blob equality to final
a0 was independently accepted without relabeling execution SHA. Plan/Play source,
recovery and16actor responsive/group flow passed. Rehearsal API/UI and disposable
databases were cleaned. Evidence is outside source under buddy-check.LPopRI.
This ordered-manual slice is accepted; its ACTIVE write lease is retired. The
serial side-turn successor owns its newly pinned bounded writes in
HANDOFF-COMBAT-side-turns.md. Spotlight and real-runtime delivery are not complete.
