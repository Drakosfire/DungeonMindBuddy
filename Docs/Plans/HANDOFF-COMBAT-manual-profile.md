# COMBAT — run persisted system-neutral ordered encounters

ACTIVE under the operator's full Combat implementation/review/accepted-merge and
local delivery authority. Serial successor to #3995, merged
`087c293812e1699e0088062484df31367343b93a`. Fetched base
`82594fb5bb78a6c2e34ffefb0890fcba4d549250`; branch
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
   scene_template_types,scene_templates,adoption}.py; play/{session_encounter_types,
   session_encounters}.py; new migration
   migrations/versions/20261118_0162_manual_combat_profiles.py. Keep existing v1
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

PRIME settled sequencing in merged #3877: Combat owns20261118_0162, parent0161.
The fetched source's sole Alembic head was independently read as20261117_0161
before activation. Recheck before committing the migration. Rehearse
0160→0161→0162 on uniquely owned disposable PostgreSQL. Preserve v1 rows, aliases,
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
