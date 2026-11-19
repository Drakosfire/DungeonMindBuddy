# CLEANUP: supported local Surface navigation journey

Status: ACTIVE under the standing cleanup goal's implementation, independent
review and merge authority. Serial one PR; base
`bf493b1a1d3f2603e31082cb0ae70c858709a3af`, branch
`codex/local-surface-navigation`, reused isolated checkout. No runtime resources.

## Bounded lease and settlement

Writes: this handoff; only the existing blank-Surface/AppChrome link journey in
`apps/live-control-ui/src/test/appNavigation.test.tsx`; completed predecessor
`HANDOFF-CLEANUP-navigation-history-entry.md` for removal. All59open PR paths and
complete cached #3824 paths at unchanged76c31187f3e9badecbc403f2d9c943994c5f5f9c
checked. #2405 remains0ba62b05450b215418a10b320069c11c2cf56c8f; preserve its
obsolete wrapper mock/setup seam. No shared fixture/runtime/classification writes.

#4141 merged at this base: exact reviewed9c3478d797e144ea0fc97ccd1169d6e82b1077a6,
localhosted1406/build/validator; full8130pass105fail2pending. The merge includes
four separate backend #4140/#4142 paths; entire-tree equality is false. Independent
postmerge review confirmed identical frontend/verifier/manifests/policy inputs.
No merged-SHA/backend qualification is claimed. Git history retains its assignment.

## Current supported contract and critique

The frontend README retains `/surface` as the full local Live Control board;
LiveControlApp loads its aggregate getSurfaceSessionViews contract. Root is the
released Home page and bare Plan requires World choice (#1566), so the old blank
root/default-session assumptions are obsolete.

Use actual App at `/surface`, a case-local complete aggregate fixture and a typed
empty World list; await actual Surface readiness. Retain Plan→Ingest→Build→Play→Home
link navigation, pathname checks, Plan→Ingest Agent-chrome DOM identity, Combat
href/no-accidental-navigation and unchanged browser document. Check Combat while
still in the workspace; Home intentionally owns a different entry composition.
Restore all spies in finally. Do not mock pages/router/history or issue a Chat turn.
This does not qualify provider Chat, auth or production deployment.

Rename only this case from `navigates blank Surface and AppChrome primary links
without replacing the document` to `navigates local Surface and AppChrome primary
links without replacing the document`. Record an explicit one-for-one ID mapping;
all other case IDs/bodies must remain byte-identical. No unaccounted omissions.

## Verification

Exact-head hosted/build/validator, full default-discovered comparison with approved
single ID migration, source equality, docs and independent cumulative review.
Baseline exact9c3478frontend8130pass105fail2pending. Keep full diagnostics red and
preserve all raw evidence; only this mapped contract correction earns credit.
