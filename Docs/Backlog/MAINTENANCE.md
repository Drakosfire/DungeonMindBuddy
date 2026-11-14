# Buddy maintenance follow-up queue

This queue holds the maintenance items explicitly transferred out of the root product backlog. A transfer keeps an item open; it does not imply completion, priority, or authorization to implement. The component owner remains responsible for the technical boundary.

## Open follow-ups

| Candidate | Component owner | Evidence and next check |
| --- | --- | --- |
| Give retained PDF shortcuts a browser storage lifecycle | Buddy Build frontend | Build can remove one browser shortcut without a PDF service request. The capture review test proves existing entries remain readable and removal persists across remount. Opening a preview still scans all localStorage keys. Measure growth and scan cost with repeated captures, then evaluate scoped indexing that preserves existing shortcuts and isolates Worlds. |

## Transfer record

- 2026-11-13: Moved the three open entries above from **Follow-up cleanup and optimization sweep** in the [root backlog at the transfer base](https://github.com/Drakosfire/DungeonMindBuddy/blob/618f62faa1da66c978a7e58e219622031985ede4/Backlog.md#idea-follow-up-cleanup-and-optimization-sweep). The original owners, scope, and verification notes were preserved. No other entries were moved or marked done.
