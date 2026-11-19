# CLEANUP: preserve neutral core boundaries alongside shared React hosts

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: 1b1decc8703db9d1912ec237f4f4a075038c237b.
Branch: codex/neutral-core-host-boundaries, existing cleanup checkout.
Topology: serial after merged #4086; no unmerged behavioral dependency.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

Outcome: apply the existing surface interaction architecture's distinction
between neutral core contracts and shared React presentation. Keep index.ts,
publication.ts, surfaceIdentity.ts and types.ts as the exact neutral core. Name
all eleven later SurfaceSelectionActions/contextHost/peekHost production files
explicitly; reject any unclassified file instead of skipping new host directories.
Retain all original forbidden core imports/React/JSX guards and additionally forbid
core import/re-export specifiers into shared hosts (including the previously
separate projection/toolHost/editHost packages). Leave those packages' existing
separate boundary coverage and runtime files unchanged. These remain source-pattern
guards, not exhaustive semantic module resolution. This corrects the old
SIH-01 scanner's scope, not shared host behavior or domain policy.

Write lease: apps/live-control-ui/src/surfaceInteraction/boundaries.test.ts,
this handoff, and HANDOFF-CLEANUP-projection-adapter-owner-guard.md for truthful
predecessor settlement. All 61 open PR file lists checked at activation; no overlap
on existing leased files. Architecture/runtime/caller files remain read-only.
No providers, databases or external host writes.

Verification: focused before/after module plus task-local negative probes for
an unclassified host file, a React import in core, and a host re-export in core.
Baseline: 1 pass/2 failures; classified core: 3 passes. Each negative probe gives
2 passes/1 intended failure. These are working-tree diagnostics, not final proof.
Exact-head hosted verifier/build/validator then full discovered diagnostic, using
the global frontend lock and verified Projects external scratch. Explicitly pair
the two stale package-wide test names with their neutral/core classification
replacements; accept no other additions/omissions or new failures/changed remaining
leading messages. Require both intended inherited failures to resolve. Preserve
unrelated red results, two conditional inventory extras and the earlier unresolved
quote-correction observation. Independent exact-head cumulative source/raw-evidence
review is required before merge. Original cleanup owner/release gates remain open.
