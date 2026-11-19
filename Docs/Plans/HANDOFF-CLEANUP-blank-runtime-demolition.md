# CLEANUP: retire the orphaned blank runtime and preserve landing navigation

Status: ACTIVE under the user-authorized cleanup goal, including review and merge.
Base: 5574068634341c57235800b77f7278bf0c6c08ad.
Branch: codex/demolish-blank-runtime, existing cleanup checkout.
Topology: serial after merged #4090; no unmerged behavioral dependency for this
slice. Test relocation is a separate BLOCKED successor, not dispatched below.
Owner: cleanup steward; independent Bugbot review before merge. Follow-up #4074.

## Invariant and discovery

Current index rendering belongs to BuddyApp/BuddyHome/IsolatedEntry; authoring
hosts belong to LocalWorkspace. BlankSurface.tsx, blankSurface.ts and its CSS
reference only each other and their own test. Complete current-repository symbol,
path and dynamic-glob checks found no additional runtime loader/caller. Original
blank lane #2198 merged; its stale ACTIVE handoff is historical, not a live lease.
All 60 pinned open PR head/base objects were inspected using full Git diffs and
production source searches: no introduced references, external production callers
or overlapping target paths. Whole identifiers distinguish unrelated old
isBlankSurface variables. No fetch/new worktree was needed; all objects existed.

Delete the three unused runtime files (3262 tracked bytes before, zero afterward).
Do not claim host disk recovery or startup download savings: unreachable source
was not a serving capability. Replace the obsolete App integration scenario with
current real landing -> Build fixture -> Back/Forward coverage. Preserve initial
no-HTTP/no-work/no-tools behavior, modified-click semantics, projection activation,
retirement on landing reentry and one instrumented real authoring host on forward
navigation. The tool-only Build fixture registers no Ask plugin; the real Agent
chrome correctly stays gated, independently of its component being composed.
Retire the two unit cases whose sole subjects are the deleted unused primitive;
this is semantic retirement with that code, not deletion for speed. Explicitly
pair the old/new navigation case and inventory the two retired cases at review.

## Exclusive write set and registry collision

- apps/live-control-ui/src/blankSurface/BlankSurface.tsx (delete)
- apps/live-control-ui/src/blankSurface/blankSurface.ts (delete)
- apps/live-control-ui/src/blankSurface/blankSurface.css (delete)
- apps/live-control-ui/src/blankSurface/BlankSurface.test.tsx (current navigation proof)
- Docs/Plans/HANDOFF-SURFACE-blank-landing.md (replace stale authority with pinned history)
- This handoff and HANDOFF-CLEANUP-shell-ingestion-lifecycle-fixture.md (settlement)

No runtime entry/caller files, manifests, lockfiles, providers, databases or hosts
are edited. ci/test-classification.json has active CI ownership: the standalone
shadow handoff at #2302 pins the classification lease as frozen; #2298/#2299 and
other integration drafts also touch it. Preserve that registry and the existing
registered test path in this slice.

BLOCKED successor: the owning CI classification worker/coordinator must release
or explicitly split that manifest lease before moving the remaining regression
to src/home/BuddyLandingNavigation.test.tsx, updating its classification and
removing the now test-only blankSurface directory. That outcome remains open
under #4074; this slice does not claim complete directory demolition. No successor
lane or write lease is allocated here. Keep the current test-file comment explicit.

## Verification

Run focused baseline/new navigation diagnostics using task-owned external source
and the global frontend lock. Check surviving entry imports, current route wiring,
all reference/link targets and exact source-byte deletion. Obtain independent
critique of the retirement and collision split. Then run exact-head hosted
verifier/build/validator and full discovered diagnostic. Compare against retained
byte-identical parent frontend: exactly two passed orphan unit cases retired,
one old/new navigation name pair, no other case additions/omissions or new
failures/changed remaining leading messages. Require the new navigation case to
pass. Preserve unrelated red results, conditional inventory extras and earlier
unresolved quote-correction observation. Full release qualification remains red.
Independent exact-head cumulative source/raw-evidence approval before merge.
Original cleanup owner/release gates remain outstanding.
