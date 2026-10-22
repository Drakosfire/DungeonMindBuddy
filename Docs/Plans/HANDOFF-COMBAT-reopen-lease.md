# COMBAT — await owned browser lease release before reopening

SETTLED by #1593 (f168672c4d9f8e11e32f4605e6835531c1a8e7fa). Lease released.
Ordinary same-module Open→Open passed after delivery; source/tracker state unchanged.

Original scope: PRIME owns a serial slice frombe2860a15767c5289550d7bb8c4e8e5c64ca6e54,
branch codex/combat-reopen-lease, existing buddy-context-loop checkout. Remote
open PR census shows no overlapping active implementation lease.

Ordinary Open of the currently open clean Sheep encounter falsely reports another
view. close() resolves the held Web Lock callback but does not await the browser's
lock-request completion before open() issues another ifAvailable request. Existing
tests delay lock admission and did not exercise delayed actual release.

Invariant critique: wait for completion of this session's previous lock request,
not a delay, retry or another view's lock. Recheck lifetime after that await;
keep generation fencing before/after acquisition and storage parsing. Preserve
real cross-view exclusion and fail closed on unavailable locks/storage. Never
repost a Save, erase recovery or mutate APP/source identity while reopening.

Exclusive lease: this handoff; predecessor HANDOFF-COMBAT-remove-combatants.md and
Docs/Roadmaps/ROADMAP-demo.md settlement; combat/combatRecovery.ts, its unit tests
and surface/modules/CombatRosterModule.test.tsx only. No schema/API, source,
mechanics, new caps or compatibility paths. Plan/Play share this lease class.

Acceptance: controlled delayed-release lock manager proves no replacement request
is made until own previous request resolves; closing/changing view while waiting
must prevent late acquisition. Real other-view lock stays refused. Same module
Open→Open retains committed state; unknown Save recovery remains exact. Bugbot
exact cumulative review, PRIME merge, guarded UI delivery, ordinary same Sheep
encounter Open→Open after API restart shows saved source snapshot HP55 and tracker
HP53/55/Prone with unchanged Plan/current Scene. Full roster/J1–J6 remain open.

Predecessor #1592 mergedbe2860a15 after Bugbot approved70e42922d; author32 backend/
161 UI checks, independent14 APP/67 UI plus pending-Save-removal witness passed.
Guarded UI delivery retained1562 APP rows,63 product files and frozen sources.
Ordinary UI removed the manual Noke, loaded accepted mechanics and saved the same
encounter revision3. Exact snapshot sb_60f9d45845ec485099f1e5df8ad75d60 /
rev_c9d222fc732c4bca8db90664e13d803e / sha256:1db196f8370d016552ff6a95f1fc57c96e6a6be8e7ac0c1f9ea888d72de55c6e
retains source HP55; independent tracker HP53/55/temp0/Prone and active actor are
verified through APP. Original Plan revision11/hash unchanged. API restart retained
1562 rows/63 files/frozen sources and exact snapshot. Rendered reopening hit this
lease race, so predecessor's complete reopen gate is carried here. Its write
lease is released; removal/save evidence stands with that explicit limitation.
