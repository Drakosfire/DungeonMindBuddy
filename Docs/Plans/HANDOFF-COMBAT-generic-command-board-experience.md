# COMBAT: generic command-board encounter experience

**Status:** ACTIVE — PRIME authorized the steward to activate C0 on 2026-10-17 after architecture disposition through PRIME. This lease covers C0 only; C1–C4 remain queued.
**Base:** Re-anchored to current Buddy main `42ec6ccb1fcc9f38ca7a58f2d05cad09aba16cbc` (the merge of Ingest PR #1362). The original C0 implementation head and prior main composition remain in branch history.
**Branch / checkout:** remote PR branch `codex/combat-c0-durable-encounters`, original implementation head `a7132abb0d53a07718813c66355c023853a1789b`. The assigned `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy` checkout is currently on the Ingest branch with unrelated dirty Ingest work; do not switch, reset, stash, or edit that checkout.
**Serving baseline:** #1362 is merged, but its current-head rendered visual acceptance remains deferred to the next already-authorized 5202 rollout. Preserve the current serving state; no live APP-STATE migration, API restart, database mutation, or dist replacement is authorized by this lease.
**Topology:** serial within Combat: one C0 PR; C1–C4 wait for C0 review/merge. PRIME owns the held MEDIA #1306 migration rebase. PRIME confirmed C0 exclusively owns APP migration `20261017_0031` descending from accepted `20261017_0030`; MEDIA #1306's old `0028` branch must be rebased and renumbered only after C0. No other active C0 implementation lease exists.

## 1. Product outcome

A GM can select graph-backed creatures or exact statblock revisions, assemble and edit an encounter, save and reopen it, start that exact encounter in Play, and run the fight from a focused command board. The live board keeps the current actor and next turn obvious; supports initiative order, round boundaries, individual and grouped enemies, HP/temp HP, damage/healing, notes, conditions, defenses, and one-step statblock drilldown.

Combat remains generic at its core. A loaded system configuration supplies the ruleset identity and rules-specific projections. The first acceptance target is D&D 5e using the configured edition; this work does not claim an automated D&D rules engine.

## 2. Primary references

- `evals/c2_live_prep/mireward-prep/combat.html` — table layout and combat interaction language.
- `evals/c2_live_prep/mireward-prep/statblocks.html` — statblock drilldown.
- `evals/c2_live_prep/mireward-prep/assets/prep.js` — hybrid initiative barrel, stable active pointer, virtual Top/Bottom of Round, group/dead buckets, and turn traversal.
- `evals/c2_live_prep/mireward-prep/saves/combat/longmont-c2__session_26__mireward_wall_breach__combat_state_v1.json` and the Session 22 save — existing at-table examples to inspect for useful state and migration needs.
- `apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx`, its tests, `combatMinimums.ts`, `apps/live_control_server/services/combat_state.py`, `combat_saves.py`, and the live routes — current implementation to extend or replace by invariant.
- `Docs/Plans/PLAN-command-board-combat-statblock-generator-roadmap.md`, `Docs/Plans/HANDOFF-PLAY-SURFACE-add-to-combat.md`, `Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md`, and `Docs/Design/ARCHITECTURE-application-state-layer.md` — current sequence and state-ownership constraints.

## 3. Current-state findings

- A server-backed roster exists with active/next actor, initiative sorting, team, editable initiative/HP/temp HP, damage/heal, conditions, notes, defeated state, statblock labels, and current/save-slot APIs.
- Current encounter state is `dmb_combat_encounter_state_v1` in `session_dir()/combat/current_combat.json`; it is a single mutable file whose identity follows the checkout/session directory. Architecture identifies that locality as a product defect.
- `combat_saves.py` supports named save slots, backups, load, unload, and new encounter. `CombatRosterModule` exposes Load, Unload, and New, but not the save-current action even though the API exists.
- The current add path accepts generated Statblock View output. There is no general graph-backed encounter builder that selects exact creature/statblock revisions and creates an editable roster.
- The live roster does not yet carry an explicit loaded `ruleset` configuration or use it to project defenses/actions. Statblock Workbench currently hard-codes D&D 5e 2024 for create context. `combatMinimums` is a limited projection, not a complete ruleset adapter.
- The static prototype's initiative barrel semantics are not preserved by the live service: live advance traverses all entities, including defeated ones; current UI does not expose manual reorder, grouped enemy stacks, dead bucket, or virtual round markers.
- Existing `HANDOFF-PLAY-SURFACE-add-to-combat.md` remains deferred until durable Combat authority is established. The historical `agent/play-command-board-disk-saves` worktree reference was checked against the current worktree list, local/remote branches, and expected worktree directory; none matched. PRIME/ARCHITECTURE disposition this as unverified historical bookkeeping, not a C0 blocker. If a matching checkout or retained assets appear later, inventory and disposition them before migration; do not recreate them speculatively.
- The design contract in PR #1323 was merged at `c2b18ebd980fcc154e94f19b7e7338de1505007e`. This active C0 lease is the first implementation slice; implementation PR #1327 is open and awaits PRIME review.

### Retained save inventory and explicit disposition

A read-only inventory found **13 tracked JSON save records** under `evals/c2_live_prep`; these are repository evaluation/prototype fixtures, not proof of the live server's configured save directory. None were changed.

| Record | Observed identity | C0 disposition |
|---|---|---|
| `evals/c2_live_prep/live/session_23/combat/current_combat.json` | `longmont-c2`, session 23, `mireward-north-reach-gate` / North Reach Gate Combat | Preserve exact bytes. Do not auto-import; any adoption requires an explicit owner/session/ruleset/source mapping, recorded digest, and retained original. |
| `evals/c2_live_prep/live/session_23/combat/saves/mireward-north-reach-gate.json` | Same campaign/session/encounter identity as the current file | Preserve separately; do not collapse by slug or auto-import. Any adoption must resolve the current-vs-slot choice explicitly and retain the original. |
| Nine archival files in `evals/c2_live_prep/live/session_23/combat/backups/`: `current_combat.20260610T221544Z.unload.json`; `current_combat.20260610T221546Z.preload.json`; `current_combat.20260612T040703Z-1.preload.json`; `current_combat.20260612T040703Z-1.unload.json`; `current_combat.20260612T040703Z.preload.json`; `current_combat.20260612T040703Z.unload.json`; `current_combat.20260612T040850Z-1.unload.json`; `current_combat.20260612T040850Z.preload.json`; `current_combat.20260612T040850Z.unload.json` | Session 23 North Reach Gate, scratch, and API scratch snapshots | Preserve in place as recovery evidence; leave out of automatic import and never rewrite during migration. |
| `evals/c2_live_prep/mireward-prep/saves/combat/longmont-c2__session_22__north_reach_gate__combat_state_v1.json` | Legacy prototype state, Longmont C2 session 22 | Leave as immutable prototype fixture; not live authority and not auto-imported. |
| `evals/c2_live_prep/mireward-prep/saves/combat/longmont-c2__session_26__mireward_wall_breach__combat_state_v1.json` | Legacy prototype state, Longmont C2 session 26 | Leave as immutable prototype fixture; not live authority and not auto-imported. |

Before any C0 migration, read the effective `DUNGEONMIND_LIVE_SESSION_DIR` (or the code default if unset) without logging unrelated environment values; enumerate the actual current save, named slots, and backups and record checksums plus an explicit preserve/import/leave decision for each. This design pass did not read or modify that runtime directory. No speculative repair or backwards-compatibility runtime path is authorized.

## 4. Invariants for architecture review

1. **Combat owns mutable fight state.** HP, temp HP, initiative, conditions, defeat, ordering, round/turn position, and encounter notes never write back into the World Graph or immutable statblock revision.
2. **Mechanics are pinned.** Each graph-backed combatant retains exact Threat/placement and immutable statblock revision identity plus digest. A current display name or latest revision is never an authority substitute. Store a bounded mechanics snapshot so the row remains usable if the mechanics service is temporarily unavailable.
3. **Encounter identity is durable and scoped.** APP-STATE is the durable Buddy authority for encounter records; checkout-local `session_dir()` files are not the post-C0 source of truth. Encounter IDs are stable across browser reload, server restart, and checkout/worktree changes. World/campaign/session association and Play's reference to the encounter are explicit. Each mutation supplies the expected record revision and commits with an encounter-local compare-and-swap guard; stale writes fail instead of overwriting newer state. Creating another encounter never silently replaces the prior one.
4. **Rules are configured and pinned.** An encounter references an immutable loaded ruleset configuration `{system_id, edition_id, ruleset_revision, ruleset_digest}` plus an optional immutable house-ruleset revision/digest. Runtime reads resolve that exact revision and verify the digest; they never silently follow `latest`. Generic Combat code does not assume D&D-specific stat fields; the configured system adapter supplies display and seed defaults. Do not hard-code the Workbench's current `dnd5e/2024` constant as Combat's universal default.
5. **The initiative barrel is stable.** Explicit sorting establishes an initial order; manual reorder changes the persistent barrel; active turn is a stable pointer. Top/Bottom of Round are virtual queue nodes. Defeated actors do not take turns, while their records and individual HP remain available.
6. **Groups preserve individuals.** A group can collapse for scanability, but each member keeps its own HP, defeated state, source identity, and turn behavior. Dead entries do not advance initiative.
7. **Play references Combat.** Starting Play from a prepared encounter records that exact encounter ID; Play does not copy a second mutable Combat state or infer a different/latest encounter.
8. **Saves are explicit and recoverable.** Save, reopen, and switching encounters are clear user actions with recoverable state. Replacing/unloading the active encounter preserves the existing backup behavior unless architecture selects a stronger authority.

## 5. Proposed serial implementation sequence

Each row is one bounded implementation PR after its prerequisite is reviewed. Do not combine the full roadmap into one large code slice.

| Slice | Independently useful result | Required owner review |
|---|---|---|
| **C0 — Durable encounter authority** | Versioned encounter resources in Buddy APP-STATE with stable identity, encounter-local expected-revision CAS, an immutable ruleset revision/digest binding, and explicit create/list/open/save that survives checkout/browser/server changes. Before import, inventory the effective runtime store and disposition every retained current file, named slot, and backup; preserve originals, import only explicitly mapped valid records, and leave ambiguous/fixture/backup records untouched. No static-only compatibility UI or speculative legacy repair. | ARCHITECTURE + APP-STATE |
| **C1 — Generic roster assembly** | Select graph-backed creatures and exact statblock revisions; create individual/group instances with immutable source locator and mechanics snapshot; edit encounter before play. | ARCHITECTURE + STATBLOCK |
| **C2 — Live command board** | Port the tested initiative barrel, reorder, round markers, active/next cues, groups/dead bucket, HP/temp/damage/heal, conditions, notes, defenses, and statblock drilldown into shared live-control components. | PLAY-SURFACE |
| **C3 — Play continuity** | Start the exact saved encounter in Play and resume it by stable encounter reference. One Combat authority continues to own mutable state. | ARCHITECTURE + PLAY-SURFACE |
| **C4 — Configured D&D acceptance** | Load a D&D 5e edition/configuration; verify statblock-to-combat projections and a complete prep → save/reopen → Play → multi-round combat flow using a retained safe fixture. | ARCHITECTURE + STATBLOCK + operator dogfood |

Reorder or merge slices only when ARCHITECTURE confirms a smaller coherent authority boundary. Changes to shared registries, schemas, migrations, routes, or Play runtime require path-level collision review before each implementation lease.

## 6. Acceptance evidence

- Open an encounter in one browser/worktree, save it, restart or switch checkout, and reopen the exact same identity and state with no duplicate or latest-item guess. Prove two concurrent writes with the same expected revision cannot silently overwrite one another; stale revision returns a conflict and the committed revision remains intact.
- Bind a ruleset to an immutable revision/digest, reload it after configuration changes, and prove the saved encounter still resolves the pinned version or reports that exact version unavailable rather than substituting `latest`.
- Before any migration, inventory the effective runtime directory, enumerate every current/save/backup file, checksum it, and record preserve/import/leave decisions. Verify originals remain byte-identical after rehearsal.
- Build an encounter from exact graph-backed statblock revisions and verify source locators, revision digests, and combat-owned mutations survive save/reload.
- Exercise manual reorder, round markers, turn wrap, defeated/dead behavior, grouped enemies with distinct HP, temp HP, damage/healing limits, and active/next display against the static prototype behavior.
- Start Play from a selected saved encounter and prove Play resumes that exact Combat state after reload; no duplicated mutable state.
- Verify D&D 5e configured defaults/projections from loaded rules configuration and verify the generic encounter core does not assume D&D-only mechanics.
- Render at desktop and narrow widths. Show AC/defenses, current/next actor, HP, and notes in the operational row; open deeper statblock mechanics without losing fight context.
- Run owning API, persistence/migration, domain, and UI tests. Verify existing saves are preserved or explicitly migrated. Do not claim completion from mocks alone.

## 7. Architecture disposition and implementation boundary

PRIME forwarded ARCHITECTURE's C0 judgment: use a minimal Buddy-owned immutable packaged ruleset configuration, not a new generic configuration table or a speculative system registry. Begin with explicit generic manual tracking: stable system/edition/schema/revision identity, enabled fields and labels, manual defaults, and canonical digest. Do not claim automated adjudication. Persist the exact validated config snapshot and digest in each encounter; a later packaged config change must not rewrite or silently replace an encounter's pin. An edition-specific D&D projection belongs only in a later explicitly configured slice; never inherit the current 2024 Workbench constant silently.

Each encounter is owned by exactly one verified managed World. Campaign and session metadata are optional, but a session requires a campaign. Store bounded validated state, not arbitrary JSON. Every mutation is guarded by the encounter's expected APP revision; a stale write conflicts. Selection is explicit. No automatic import of checkout-local saves, no current-encounter singleton, no Play mutation, and no graph-backed roster assembly in C0. Preserve the existing generated-Build-statblock insertion path by targeting an explicitly selected durable encounter; graph-backed selection remains C1. Legacy files and prototype fixtures remain byte-identical and are not a post-C0 authority or compatibility path.

The accepted APP chain is `20261017_0030` on main; C0 owns `20261017_0031` → `20261017_0030`. The open MEDIA #1306 PR contains an inactive old `0028` migration based on `0027`; PRIME owns its later rebase/renumbering and confirmed it has no `0031` claim. Do not merge it as a competing migration head.

## 8. Exact C0 write lease

- `Docs/Plans/HANDOFF-COMBAT-generic-command-board-experience.md` — keep this contract current and record truthful implementation/verification evidence; do not mark the in-flight slice settled before merge.
- `src/application_state/migrations/versions/20261017_0031_combat_encounters.py`.
- New files only under `src/application_state/combat_encounters/`: `__init__.py`, `types.py`, `repository.py`, `service.py`, and `rulesets.py`.
- New files only under `apps/live_control_server/services/` and `apps/live_control_server/routes/`: `combat_encounters.py` in each directory. In `apps/live_control_server/main.py`, add only the Combat router import and registration. During the current-main re-anchor, preserve existing Build runtime initialization and all accepted main code. Future Rules branch re-anchors must compose against the accepted main.
- New files only under `apps/live-control-ui/src/combat/`: `combatTypes.ts` and `combatApi.ts`.
- `apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx` and its existing `CombatRosterModule.test.tsx`.
- `apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx` and its existing `StatblockViewModule.test.tsx` — redirect generated-statblock insertion to an explicitly selected durable encounter; do not add Graph selection here.
- `apps/live_control_server/routes/live.py` and `tests/test_statblock_add_to_combat.py` — retire the legacy checkout-local `/combat/current`, `/combat/saves`, and generated-statblock `/combat/add` HTTP routes with an explicit `410 Gone`; prove they do not create or mutate legacy files. Preserve all existing save and backup bytes. Do not import, delete, or migrate them.
- New owning tests: `tests/application_state/test_combat_encounters_postgres.py` and `tests/test_live_combat_encounters.py`.

This set was expanded on 2026-10-17 after ARCHITECTURE identified that checkout-local combat routes still offered a second writable encounter authority. The old `current_combat.json` read path returns an in-memory empty state when the file is absent; do not describe that GET as writing an empty file. The defect is its implicit current-encounter identity and the remaining legacy mutation/save/load authority. This C0 correction retires those HTTP routes; it does not alter legacy files, the internal historical file services, or the UI client wrapper files.

PRIME explicitly transferred `apps/live_control_server/routes/live.py` into this C0 lease on 2026-10-17. Open MEDIA #1306 is frozen/inactive and has no competing execution lease; PRIME owns its future rebase/renumber after C0 settles. Keep the MEDIA routes and all unrelated contents of `live.py` unchanged. The MEDIA-owned `liveApi.ts` and `liveApi.test.ts` remain outside this C0 lease; current production UI has no consumers of their legacy Combat helpers. The held Ingest #1235 Graph Review paths also remain out of scope. No other paths are implied. If the verified managed-World resolver, test harness, or implementation boundary requires another path, stop and return to the steward before editing it.

## 9. Verification and completion

- Exercise migration upgrade on the existing disposable APP-state test database only; never migrate retained/runtime APP-STATE under this lease.
- Test create/list/open/save/reopen against disposable PostgreSQL, same-revision concurrent CAS, stale conflict, cross-World denial, session-without-campaign refusal, state bounds/shape, and exact ruleset snapshot/digest stability after the packaged catalog changes.
- Verify old tracked combat JSON fixtures remain byte-identical and do not become implicitly loaded.
- Run owning UI, route, application-state, typecheck/build, and `git diff --check` checks. Inspect the exact cumulative `main@42ec6ccb1fcc9f38ca7a58f2d05cad09aba16cbc` → head diff.
- Prepare one PR for PRIME review. Do not merge, deploy, restart APIs, migrate live APP-STATE, or modify 5202's served output under this lease.

### C0 working verification (2026-10-17)

- Expanded disposable PostgreSQL persistence and direct Combat-router suites passed on the current PR head: 12 tests total (8 state, 4 route), covering migration, save/reopen, concurrent CAS, stale conflicts, World isolation and canonical IDs, immutable ruleset digest, draft storage bounds, verified-World resolution, statblock insertion/provenance/order, invalid anchors, and HTTP error mapping. Tests used
  `TMPDIR=$PWD/.pytest_cache` under the existing checkout, as clarified by PRIME; no `/tmp`, new worktree, or per-slice environment was used.
- The test harness mounted the Combat router directly because importing the full app in the shared dependency set fails before app construction: the installed `generationengine` package lacks `ImageOptions`, imported by the unrelated MEDIA router. App-level startup still needs a compatible shared dependency set.
- At the original C0 head, Combat roster and Statblock View focused UI suites passed (8 tests) and UI TypeScript typecheck passed. A direct no-file probe also confirmed boolean combat stats are rejected. Follow-up repair evidence is below.
- Ruff passes for the new Combat Python modules and tests. The changed `main.py` still reports its pre-existing import-order violation; the same I001 was reproduced on the base version, so the unrelated import block was left untouched.
- Production Vite build passed (708 modules) to the existing `.pytest_cache` directory with `emptyOutDir` disabled; Vite emitted its large-chunk warning. Rendered acceptance is still outstanding. The C0 lease forbids replacing local `dist` or the 5202 served output; no server/database runtime was changed.
- This is C0 evidence only. Graph-backed creature selection, Play continuity, loaded D&D configuration/projection, and desktop/narrow rendered acceptance remain future C1–C4 requirements.

### C0 race and legacy-route repair (2026-10-17)

- Combat UI async create/list/open/save/reload results are fenced by the selected World generation, including A→B→A changes. A late response cannot replace the newly selected World or clear a newer request's busy state. A save commits the submitted snapshot while preserving edits made during that save as dirty. Statblock-to-encounter adds similarly ignore completions after the World or target encounter changes.
- Retired the checkout-local `/combat/current`, `/combat/saves`, and generated-statblock `/combat/add` routes. They declare `410 Gone` in route metadata and raise the same explicit retired-authority error. The old current/save/backup bytes are seeded and compared unchanged by the retirement tests. The route wrappers in MEDIA-owned `liveApi.ts` remain untouched; repository-wide search found no production UI callers, only their declarations and API tests.
- Follow-up owning UI suites pass **13 tests**, including A→B→A stale create/open/reload/add cases and an edit-during-save case. UI TypeScript typecheck passes. Route-handler retirement and file-preservation suite passes **13 cases**; Ruff and `git diff --check` pass.
- The supplied FastAPI TestClient is unusable in the shared runtime: a minimal FastAPI route also hangs on request under FastAPI 0.136.3 / Starlette 1.1.0 / httpx2 2.3.0. Therefore the follow-up route suite directly invokes each registered handler and verifies its declared 410 status, raised HTTPException, and unchanged files; a real HTTP response was not verified here. The full-app import also remains unavailable because the installed `generationengine` lacks unrelated MEDIA's `ImageOptions` import.
- Production Vite build passed (708 modules) into the existing `.pytest_cache` directory with `emptyOutDir` disabled; Vite emitted its large-chunk warning. Rendered desktop/narrow acceptance remains outstanding. No served output, live API, database, or 5202 state was changed.

### C0 replace-in-flight edit guard (2026-10-17)

- PRIME/ARCHITECTURE held the prior head because opening or reloading an encounter left its currently visible draft editable while the replacement request was pending. A late success could then overwrite edits typed after the request began.
- The roster now disables draft and per-combatant editing controls during explicit create/open/reload replacement requests, including the new-encounter title while Create is pending. Save remains editable while pending because its submitted-snapshot path preserves newer local edits.
- Deferred-response regression coverage proves Create, Open, and Reload keep the title and combatant notes locked until the replacement arrives, then show the exact returned draft. Focused CombatRosterModule suite passes 11 tests; Statblock View and broader checks are pending for the repaired head.
- At the prior checkpoint, C0 was re-anchored on `main@6e7ee2e3d228a5b30277542ecd013779046a03c9`; the following published re-anchor below supersedes that base.

## 10. Superseded design-only gate record

- PRIME/ARCHITECTURE have dispositioned the absent `agent/play-command-board-disk-saves` reference as unverified historical bookkeeping: current worktree, local/remote branch, and expected-directory inventories found no match. It does not block C0. If an actual checkout or retained assets appear later, inventory and disposition them before any migration; never recreate speculative state.
- The pre-C0 ARCHITECTURE gate has been dispositioned through PRIME as recorded in §7. It does not authorize database schema/runtime changes outside the bounded C0 lease.
- The steward has pinned the current base, isolated checkout, exact paths, migration owner, disposable test boundary, serving state, and one-PR topology above.
- The old design-only document's code-free rule has been replaced by the exact C0 lease in §8. No runtime/deployment or 5202 mutation is leased.


## Current re-anchor and owner audit — 2026-10-17

A fresh comparison found that current main advanced 110 commits beyond the original C0 base. The C0 PR's changed paths are exactly the lease in §8. The open-PR census checked 21 PRs. PRIME settled the current shared-path ownership before the source re-anchor:

- `apps/live_control_server/main.py`: C0 owns only the Combat router import and registration regions for this integration. Preserve current main's Build runtime initialization and all accepted main code. RULES PR #763 is paused and #765 has no current active implementation dispatch; any later Rules re-anchor must compose against the accepted main.
- `apps/live_control_server/routes/live.py`: PRIME's pinned C0 transfer authorizes only the legacy Combat route retirement/integration paths in §8. MEDIA #1306 remains under the operator's DO NOT MERGE/DEPLOY hold; preserve its existing code, do not resume or change its branch, and re-anchor it only after C0.

### Exclusive C0 paths

The exact §8 lease remains the scope. Besides the two bounded integration paths above, these paths are exclusive to C0 in the current open-PR census:

- `apps/live-control-ui/src/combat/combatApi.ts`
- `apps/live-control-ui/src/combat/combatTypes.ts`
- `apps/live-control-ui/src/surface/modules/CombatRosterModule.tsx`
- `apps/live-control-ui/src/surface/modules/CombatRosterModule.test.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockViewModule.tsx`
- `apps/live-control-ui/src/surface/modules/StatblockViewModule.test.tsx`
- `apps/live_control_server/routes/combat_encounters.py`
- `apps/live_control_server/services/combat_encounters.py`
- `src/application_state/combat_encounters/__init__.py`
- `src/application_state/combat_encounters/types.py`
- `src/application_state/combat_encounters/repository.py`
- `src/application_state/combat_encounters/service.py`
- `src/application_state/combat_encounters/rulesets.py`
- `src/application_state/migrations/versions/20261017_0031_combat_encounters.py`
- `tests/application_state/test_combat_encounters_postgres.py`
- `tests/test_live_combat_encounters.py`
- `tests/test_statblock_add_to_combat.py`

Original implementation head `a7132abb0d53a07718813c66355c023853a1789b` is preserved in branch history. The local assigned checkout remains on the Ingest lane with unrelated dirty files; no branch switch, new checkout, server, environment, live migration, API restart, database mutation, or 5202 change is authorized.


## Latest re-anchor after #1362 — 2026-10-17

- Re-fetched GitHub state before refreshing this lane. Current Buddy main is `42ec6ccb1fcc9f38ca7a58f2d05cad09aba16cbc`, which merges #1362 and #1363. Comparisons from the prior pinned f35 main show only the three #1362 Ingest-provenance paths and eight #1363 requested-detail writer paths; neither set overlaps this 20-path C0 lease.
- Rechecked open PRs and owner dispositions: #1363 is the connected requested-detail producer successor; #1306 remains held; #763/#765 remain paused/no active implementation dispatch. PRIME’s C0 integration ownership for `main.py` router import/registration and the bounded Combat routes in `live.py` remains in force.
- The remote C0 branch is composed on current main while retaining all 20 exact §8 C0 paths. The prior C0 implementation and earlier f35-based composition remain in its history. No files outside §8 are added to the C0 cumulative diff.
- Fresh owning checks for the refreshed branch head have not yet been run. The verification recorded above is historical evidence for its cited earlier heads and must not be represented as fresh evidence for the refreshed head.
- Ingest extraction-quality issues remain known; do not ask the operator to repeat Session 29 dogfooding until PRIME closes that gate. Preserve the operator’s Build session.


### Re-anchor result — 2026-10-17

- Re-anchor merge commit: `bd84b2e870f38303f04019609c42a77da465d020`, with C0 branch head `ce8a507ecd32de9628f83e453f0f9ab1e72769b7` and current main `42ec6ccb1fcc9f38ca7a58f2d05cad09aba16cbc` as parents.
- GitHub comparison against current `main@42ec6ccb1fcc9f38ca7a58f2d05cad09aba16cbc` reports the C0 branch ahead by its six implementation/history commits and zero commits behind. The cumulative PR diff remains the exact 20 paths in §8; the four-commit main advance from the prior checkpoint touched only requested-detail writer paths outside this lease.
- No GitHub Actions PR workflow runs are attached to the re-anchor commit. Fresh owning C0 tests and independent exact-head review remain pending; do not reuse the older-head checks above as current-head proof.
