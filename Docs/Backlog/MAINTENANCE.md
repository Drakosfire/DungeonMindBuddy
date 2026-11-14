# Buddy maintenance follow-up queue

This queue holds the maintenance items explicitly transferred out of the root product backlog. A transfer keeps an item open; it does not imply completion, priority, or authorization to implement. The component owner remains responsible for the technical boundary.

## Open follow-ups

| Candidate | Component owner | Evidence and next check |
| --- | --- | --- |
| Give retained PDF shortcuts a browser storage lifecycle | Buddy Build frontend | [#3380](https://github.com/Drakosfire/DungeonMindBuddy/pull/3380) shipped removal and passed 19 focused tests. In a synthetic Chrome run with 50 selected-World shortcuts and 200 reads per scenario, scans averaged 0.034, 0.104 and 0.518 ms across 100, 1,000 and 5,000 storage keys. A simulated World-scoped lookup averaged about 0.01 ms and serialized 50 entries in 9,991 ASCII bytes. Revisit indexing when representative profiles show a user-visible preview delay or report quota pressure. Any storage change must preserve legacy shortcuts and cross-tab updates and verify World isolation. |

## Transfer record

- 2026-11-13: Moved the three open entries above from **Follow-up cleanup and optimization sweep** in the [root backlog at the transfer base](https://github.com/Drakosfire/DungeonMindBuddy/blob/618f62faa1da66c978a7e58e219622031985ede4/Backlog.md#idea-follow-up-cleanup-and-optimization-sweep). The original owners, scope, and verification notes were preserved. No other entries were moved or marked done.
