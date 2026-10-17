# COMBAT: generic command-board encounter experience

**Status:** BLOCKED — the prior head passed design-only review; this revision incorporates the pre-C0 authority, ruleset, save-inventory, and stale-gate dispositions. It grants no implementation write lease.
**Design base:** re-anchored on fetched `origin/main@b3f22927a3bd5d143d2c02512d2c106a5ada5fd1`.
**Serving baseline:** matched Buddy main snapshot `cb11bf86c69b7dbe96063753660fda7b829620b4` on 5202/8000; preserve it for Ingest dogfood.
**Topology:** serial implementation slices after the architecture and worktree-disposition gates resolve. One active Combat implementation PR at a time.

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
- PR #1323 tracks this design contract; there is no Combat implementation PR.

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

## 7. Gates before any implementation lease

- PRIME/ARCHITECTURE have dispositioned the absent `agent/play-command-board-disk-saves` reference as unverified historical bookkeeping: current worktree, local/remote branch, and expected-directory inventories found no match. It does not block C0. If an actual checkout or retained assets appear later, inventory and disposition them before any migration; never recreate speculative state.
- ARCHITECTURE must review the APP-STATE encounter ownership boundary, encounter-local revision/CAS semantics, immutable ruleset pin, and relation to Play Runs and session/world identity before C0 activation. This contract does not select a database schema or public endpoint shape.
- The steward must pin the exact current base, named worktree, expected paths, migration ownership, test boundary, deployment ports/state, and one-PR topology for the first approved slice.
- No Combat code, schemas, migrations, save data, server runtime, or 5202 state is leased by this design handoff.
