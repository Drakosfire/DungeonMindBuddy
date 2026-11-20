# SURFACE: historical blank landing composition

Status: SUPERSEDED. Original implementation merged in [#2198](https://github.com/Drakosfire/DungeonMindBuddy/pull/2198).
The former ACTIVE header described that completed lane, not a current write lease.

The index route now renders the current [Buddy landing page](../../apps/live-control-ui/src/home/BuddyHome.tsx)
through [BuddyApp](../../apps/live-control-ui/src/BuddyApp.tsx) and its isolated
entry provider. The authoring hosts belong to [LocalWorkspace](../../apps/live-control-ui/src/LocalWorkspace.tsx).
The former blank runtime component, publication helper and CSS have no production
callers and are retired by the bounded cleanup handoff below.

[Original handoff, corrections and verification](https://github.com/Drakosfire/DungeonMindBuddy/blob/5574068634341c57235800b77f7278bf0c6c08ad/Docs/Plans/HANDOFF-SURFACE-blank-landing.md)
remain pinned in Git history. That historical document records the old composition;
it is not current route or execution authority.

Current retirement scope and navigation proof:
[blank runtime demolition](HANDOFF-CLEANUP-blank-runtime-demolition.md).
The navigation regression temporarily retains its registered test path until the
active CI classification owner releases the relocation; no obsolete runtime is
kept for that registry entry.
