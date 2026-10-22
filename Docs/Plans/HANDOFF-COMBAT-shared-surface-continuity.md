# COMBAT — shared recoverable Plan/Play tool

ACTIVE. Architecture reviewed2026-10-22: one exact World encounter can be explicitly
resumed across Plan/Play without a scene/run ownership link. PRIME owns serial
implementation in buddy-context-loop, codex/combat-shared-surface-continuity,
base3f3f608650f23ba4746777fde2e4bc671db18478. Relevant open work has no overlapping lease.

One capability: lazy shared Combat tool using the existing CombatRosterModule on
Plan/Play, with browser recovery necessary to survive tool close/navigation/reload.
World-scoped exact encounter selection is advisory and explicit Open remains required;
never choose newest or treat encounter IDs as run/session IDs. No implicit ownership
of current scene, Plan/run association, encounter fork, new APP schema or API.

APP is sole committed Combat authority. Browser recovery stores versioned World+
encounter ID, complete base record/revision, working draft and exact pending Save
base/body. Same-origin WebLock coordinates one mounted editor per exact encounter;
it is not a distributed writer lease. Synchronous verified recovery writes precede
accepting edits. Lock/storage unavailable fails closed. Another local view refuses
editing, preserving recovery; other clients remain governed by APP CAS.

Close/unmount/scope change releases lock, retains recovery. Explicit Open reads APP
and offers explicit local draft recovery; a changed base is preserved with conflict,
never silently rebased/reposted. Exact pending Save survives unknown outcome. When
APP read shows base+1 and exact submitted draft, report matching committed state and
clear only matching recovery; this establishes state equality, not request authorship.
Matching Save acknowledgement or explicit Revert/Reload may clear owned recovery.
Edits made during Save survive acknowledgement with the new APP base. Lost-ack
reconciliation retains later edits after proving only the exact submitted commit;
it never treats the later edits as saved. All cleanup
checks stored bytes/ownership; old callbacks must not delete another draft.

Host document/run scene position, drafts, session copy and notes remain owned by
existing writers. No Combat reads/code load before explicit tool open. One shared
Surface catalog registration; no duplicate Plan/Play implementation. No arbitrary
new caps, latest fallback, backwards path or provider/Graph mutation.

Exclusive writes: this handoff; predecessor HANDOFF-COMBAT-exact-world-mechanics.md
and ROADMAP-demo.md; UI combat/new combatRecovery.ts and combatProjection.tsx, combatRoster.css/CombatSurfacePage.css style ownership plus
owning recovery/catalog/integration tests; generated combatRecoverySchema.json,
validateCombatRecovery.ts, scripts/generate_combat_recovery_schema.py and owning
schema synchronization test (render-safe client shape, not commit authority); shared CombatRosterModule.tsx and tests;
PlanSurfacePage.tsx and PlaySurfacePage.tsx opt-in imports/publication/hooks only.
No backend runtime, migration, Plan/Play writer, global registry or dependency changes.

Verify recovery before-close/reload, scoped ID/base mismatch, quota/lock failure,
late callbacks/ABA, two-view refusal and external-client CAS, lost ack without
reposting, edits during Save, exact encounter Plan→Play and reverse, lazy reads,
unchanged host draft/scene/notes. Bugbot exact cumulative review→PRIME merge→5202.
Actual rendered Plan/Play same fight, independent actor state/mechanics and local
recovery through tool close/reload; API restart retains prior state. No full J1–J6 award.

Review refinements: complete nested recovery shapes are generated from current APP
Combat and DMS exact-resource types, with annotation-only schema text removed. Unknown
validator vocabulary fails closed; synchronization test detects contract drift.
Pending Save permits exact retry/discard even when later working draft equals base,
and status remains unconfirmed rather than Saved. No new storage/model caps.
