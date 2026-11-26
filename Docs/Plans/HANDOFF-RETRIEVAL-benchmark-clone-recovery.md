# RETRIEVAL: recover interrupted benchmark clone

Status: ACTIVE. The user explicitly authorized clone recovery and owns this
lane. Base: current `origin/main` ae5adad4086b2629a2a5845253428d71be215861;
branch `codex/benchmark-clone-recovery`. This serial prerequisite to the
existing negative-retrieval benchmark PR changes the disposable database owner,
its focused tests, this handoff and the laboratory guide. The benchmark remains
on its existing branch. The prior single-invocation clone runner was merged in
#4583. Open retrieval/benchmark PRs were checked for overlap; no other active
clone recovery implementation was found.

Outcome: allow an interrupted workstream to re-enter the *same* isolated App
clone under `disposable_benchmark_database`, not create a second clone. Require
an independently pinned original receipt and lock identity; acquire the original
cooperative lock, validate the owner/worker and exact local database identities,
require no App connections, and make the old receipt unusable before yielding.
A restarted evaluator may have a different explicitly pinned loopback port;
the original receipt stays bound to the original port, while both template
and clone OID/cluster identities must match at the new endpoint.
A new owner must maintain its own receipt and workers throughout the context.
On exception or absent explicit accept/abandon, retain the clone. Before teardown,
recheck the current owner, worker groups, lock, clone and connection closure.
The context does not kill processes, force disconnect, reset fixture data or
claim safety against a process that ignores the cooperative lock. Refuse rather
than guess when the receipt or worker state is ambiguous.

This first slice accepts only a retained receipt already recording all workers
closed and a quiescent owner state. It does not adopt a stale `running` receipt:
reconciliation of ambiguous worker records remains a separate unresolved case.
The exact old workstream receipt currently records a closed last worker and a
quiescent review state; source changes, template pins, Core login and live clone
identity still need revalidation before any actual adoption. No production data,
providers, or database creation are used in the focused tests. Test real-owner
and process failure conditions with mocks first; collect independent review and
owner-bound, exact-source evidence before use on the retained clone. A live run
must use one App clone and the existing read-only Core, no full content scans,
and close all workers and connections before accepted/abandoned teardown.
