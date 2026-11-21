# COMBAT — running encounter toolbar

MERGED in #4302 as `d257a0ff7708f37b54e8729d1eda8b07c8f6ce9b`.
Reviewed head `8dc7af8639c588124006146bc510b12f7ac79c7f`. Its hosted
frontend verifier passed 1,430 checks and the build. The earlier full
diagnostic matched the 102 inherited failures and two skips. The roster
successor now owns the Combat presentation files. Deployment remains pending.

Historical activation. The user authorized frontend changes in the active Combat visual
refresh goal for this chat (01a1ef4e-ff74-7d11-bd9a-2a499da090ff).
Root owns the design and implementation. Base
`01e22a26a020ca7399458bba61cee6d817c8702c` from fetched origin/main.
Branch `codex/combat-running-toolbar`, isolated checkout
`/home/drakosfire/Projects/.codex/fc67/DungeonMindBuddy`. No implementation
parent. Serial topology.

## First PR

Put encounter and turn controls on one desktop strip, with the roster
immediately beneath it. Keep Back and Next turn visible. Open setup and
creation on demand. Preserve empty/sample and system selection workflows.
Retain status, save and recovery messaging when action is required. Avoid
wide empty spacers between current and next actors.

Expected writes are this brief, CombatSurfacePage and its CSS/tests, shared
CombatRosterModule and its tests, CombatEncounterAssembly markup for its
anchored panel, and combatRoster.css. Open PRs #3668, #3824,
and #4259 were checked at their remote heads and do not write these Combat
paths. Follow existing appearance tokens and navigation ownership. No live
runtime lane, shared database, or schema lease.

Verify standalone and embedded loading and setup, scoped links, gesture and
keyboard paths, recovery, revisioned saves, and round boundaries. Setup panels
must not silently reset a draft or hide a recoverable save. A previously
synchronized encounter remains distinct from an unsaved sample. Verify
desktop and narrow layout and run the repository exact-head frontend verifier.

## Serial successors

After this PR merges, pin the roster presentation slice. It delivers compact
rows with numeric HP and a meter, clear current/next/defeated states, wrap and
editing, and discoverable docked and modal corpus inspection. Verify using
the crowded Mireward data at desktop and narrow sizes, keyboard focus, exact
corpus provenance, and non-D&D profiles. Do not pre-allocate its write lease.

After acceptance, stage the hosted release using the verified production
baseline, hand any sudo action to Alan, and verify the existing signed-in
Mireward link. Capture before and after at matching dimensions. The approved
docked and overlay mockups are in the chat's combat-dnd5e-2026-11-20 artifacts.
