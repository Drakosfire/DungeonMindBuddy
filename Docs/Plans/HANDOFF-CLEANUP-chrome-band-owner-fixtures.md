# CLEANUP: align Chrome band tests with current CSS owners

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: c4a3403e8e552797e185899b7f35f4a6817047f9.
Branch: codex/chrome-band-owner-fixtures in the existing cleanup checkout.
Topology: serial after merged #4081; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: repair two stale CSS-owner assertions without changing runtime behavior.
Tools rules belong to ToolHostView.css; the shared Agent shell and launcher belong
to AgentInteractionChrome.css. Preserve all drawer/inset/Peek/sticky assertions,
the unavailable-Ask guard in both former and current owners, and compact launcher
bounds. Require a shared square token on both wrapper and button, between 2.75rem
(the circular-launcher handoff's 44px minimum at default root size) and 5rem.

Write lease: apps/live-control-ui/src/chrome/chromeBand.test.ts, this handoff,
and HANDOFF-CLEANUP-native-preview-catalog-fixtures.md for predecessor settlement.
All 60 open PR file lists checked at activation; no overlap on these existing paths.
No runtime CSS, routing, registry, lockfile, provider, database or host writes.

Verification: exact-head hosted verifier and validator plus full discovered
diagnostic under the shared frontend lock, with external task-owned scratch on
the verified Projects filesystem. Compare all test IDs and failures against the
retained parent run; expect six Chrome cases passing and only two failures
resolved. Preserve all unrelated red results and conditional inventory extras.
Independent exact-head cumulative source and raw-evidence review before merge.
Original cleanup owner/release gates remain outstanding.
