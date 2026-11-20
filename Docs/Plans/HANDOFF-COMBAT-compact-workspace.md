# Combat compact workspace

ACTIVE under the user's compact Combat design and implementation assignment.
Root owns the slice. Branch codex/combat-compact-workspace starts from fetched
origin/main cf89e8662 in checkout fc67. Serial delivery.

1. Combat workspace UI: empty workspace, system selection, compact controls,
   wrapping, forward/back turns and both statblock presentation modes. Writes
   are limited to the Combat client directory, its roster module and owning
   client tests, and this handoff. Verify normal standalone and embedded hosts,
   persisted encounter compatibility, keyboard modality and narrow layout.
2. Historical encounter and projection extension: depends on the workspace.
   Verify the actual Session 26 export against other available records, resolve
   source aliases through corpus evidence, and preserve unknown values. Pin
   the import and API write scope before implementation.
3. Hosted delivery: depends on accepted UI and source-backed import. Verify
   signed-in access through a direct encounter link after authorized publication.

The first slice uses existing source and save ownership. Viewer mode is UI
state. It must never change selected turn, encounter data, source identity, or
revision. Modal dismissal returns focus to the roster control, including after
a mode switch. Use local browser fixtures outside operator state. Producer
#3668 and hosted authorization #3824 are read-only dependencies.
