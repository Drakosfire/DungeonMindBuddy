# Buddy maintenance follow-up queue

This queue holds the maintenance items explicitly transferred out of the root product backlog. A transfer keeps an item open; it does not imply completion, priority, or authorization to implement. The component owner remains responsible for the technical boundary.

## Open follow-ups

| Candidate | Component owner | Evidence and next check |
| --- | --- | --- |
| Retry Build World creation only when the outcome is ambiguous | Buddy Build frontend | ensureManagedWorld retries every rejected create POST, even though the retry exists to reconcile an uncertain commit. The controller suite already covers successful reconciliation. createWorldContainer delegates to apiFetch, whose LiveApiError carries status and code. Use those fields where the endpoint contract establishes a definitive rejection. Check the API error taxonomy and avoid repeating definitive validation or permission failures while preserving the server-owned idempotent retry for uncertain outcomes. |
| Give retained PDF shortcuts a browser storage lifecycle | Buddy Build frontend | Each distinct capture locator adds a localStorage entry and opening the preview scans all storage keys to rebuild the list. The shortcut list offers reopen but no removal. Measure growth with repeated captures, then evaluate explicit shortcut removal and scoped indexing. Verify existing entries remain readable and removing a shortcut preserves the durable PDF and its evidence. |
| Document the shared local APP-STATE Compose instance | Buddy local database operations | The local Compose file fixes the container name, volume name, and host port, so choosing a different Compose project name does not create an isolated database. Make the shared authority explicit and point parallel dogfood or restore rehearsals to the disposable database procedure. Preserve the existing volume identity and verify the runbook can distinguish shared and disposable targets before any write. |

## Transfer record

- 2026-11-13: Moved the three open entries above from **Follow-up cleanup and optimization sweep** in the [root backlog at the transfer base](https://github.com/Drakosfire/DungeonMindBuddy/blob/618f62faa1da66c978a7e58e219622031985ede4/Backlog.md#idea-follow-up-cleanup-and-optimization-sweep). The original owners, scope, and verification notes were preserved. No other entries were moved or marked done.
