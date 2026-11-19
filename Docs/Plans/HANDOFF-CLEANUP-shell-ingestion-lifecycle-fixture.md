# CLEANUP: verify ingestion survives sibling pane expansion directly

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: 59b419cdccac6bae5670be84e319d32d2aad22cc.
Branch: codex/shell-ingestion-lifecycle-fixture, existing cleanup checkout.
Topology: serial after merged #4089; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: retain the existing no-remount regression at the owning layout/real
Ingestion boundary. The current Ingestion module renders without automatically
calling postRecapIngest, so that old HTTP counter is no longer a mount witness.
Set the test route deterministically, enter a controlled draft title in the real
Ingestion module, expand Record, then require identical navigation/root/input DOM
objects and the retained title alongside Record content. Preserve the test's name
and all other SurfaceShell cases. Delete the unused status fixture and imports.
Do not substitute zero-call equality or mock away Ingestion. No runtime changes.

Write lease: apps/live-control-ui/src/surface/SurfaceShell.test.tsx, this handoff,
and HANDOFF-CLEANUP-private-media-binary-fixture.md for truthful predecessor
settlement. All 61 open PR file lists checked at activation; no overlap on existing
leased files. Shared runtime/module owners remain read-only. No app servers,
providers, operator databases or remote hosts are written.

Verification: focused before/after full SurfaceShell module. In a task-owned
external source copy only, force module keys to change when any pane collapses or
expands; require the no-remount case to fail at node identity, proving retained
title hydration alone cannot hide a remount. Restore the disposable mutation.
Focused results: baseline 6 passes/1 failure; direct lifecycle 7 passes. The
filtered negative run fails only this case at navigation object identity despite
identical serialized markup (six unselected cases pending). These are diagnostics,
not final exact-commit qualification.
Exact-head hosted verifier/build/validator and full discovered diagnostic under
the shared frontend lock with verified Projects external scratch. Require the
one intended failure to resolve without added/omitted/renamed cases, new failures
or changed remaining leading messages. Preserve unrelated red results, conditional
inventory extras and earlier unresolved quote-correction observation. Independent
exact-head cumulative source/raw-evidence review before merge. Original cleanup
owner/release gates remain open.
