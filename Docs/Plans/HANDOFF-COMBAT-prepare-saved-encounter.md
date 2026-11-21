# COMBAT — prepare a saved encounter for a Plan scene

ACTIVE. Alan authorized the end-to-end Old Bath House build in chat
01a1ef4e-ff74-7d11-bd9a-2a499da090ff. This serial slice starts at
`b84831800c7d00e549bb73ea496633e1bd46d370` on
`codex/combat-prepare-saved-encounter` in the fc67 Buddy checkout. Root
owns implementation. No hosted runtime or database write lease.

## First PR

Extend scene preparation to copy a committed, same-World Combat encounter
into an unoccupied scene on an exact current, clean Plan. Admit an expected
source revision under a transaction lock. Preserve the exact draft,
ruleset and mechanics references and give the new encounter independent
identity and history. Reuse the existing idempotency, cancel and
authorization boundary. Refuse stale or foreign sources, run instances,
self-replacement, and occupied scenes. Retain existing creation behavior.

Expected writes are this handoff, scene template types and transaction,
and their application-state tests. Open #3824 touches the HTTP route and
route tests, outside this lease. #3808 owns portrait work and #3668
concerns mechanics adoption. No overlaps were found in the active write
paths. No migration planned. Verify with disposable PostgreSQL and the
owning scene template contract, including stale-source, conflict, replay,
and original preservation. Inspect exact head and obtain independent review.

## Serial successors

After the service PR, expose source/target preview and explicit confirmation
in Buddy using the Plan and Combat owners. Verify the ordinary signed-in
workflow, conflict and retention. Follow with only the asset or Play gaps
demonstrated by evidence, checking exact statblocks and art through both
paths. Finally rehearse both outcomes on a disposable or approved Old Bath
House run and deliver links. Pin each successor's own files and verify
portrait and authorization dependencies before activation.
