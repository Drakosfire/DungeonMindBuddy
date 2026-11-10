# CI: keep local frontend verification off the root filesystem

Status: ACTIVE. PR topology: parallel-independent.

## Authority and lane

The coordinator adopts this bounded repair under the user's request to fix
continuing temporary-file disk exhaustion. Design base was main
573d72f9a5e4f296fdb7de055b85882a568969bb. Publication re-anchor is main
49ac23cebc1194d84ae7bc67d2e7a63cf5060010, confirmed through the read-only GitHub
connector on 2026-11-10. Only unrelated BUILD paths advanced. Direct Git fetch
was network-policy blocked; both matching commits were already present locally.
The lane was rebased onto the new main with unchanged implementation blobs.
Branch: codex/frontend-projects-temp-allocator.

## Invariant

The local frontend verifier must not silently allocate its source worktree,
dependency installation, subprocess temporary files or caches on root-backed
system temp/home storage. Default to the verified Projects workspace, validate
storage before allocation, and fail closed. Explicit root and filesystem UUID
configuration supports another authorized executor without an automatic fallback.
Keep exact-SHA evidence, the global resource lock, failures and owned cleanup.

## Ownership and scope

Exclusive expected write lease: scripts/ci_local_frontend.py;
tests/test_ci_local_frontend.py; this handoff; the narrow local-verification
instructions in AGENTS.md. Open CI PRs 2288, 2298, 2299 and 2302 were inspected;
none owns the allocator/test paths. Product lanes are independent. No frontend
product change, global setting, live data cleanup, merge or deployment.

## Verification

Run the verifier guard tests with real Git fixture worktrees and all test scratch
on Projects. Cover unset/hostile ambient TMPDIR, root/default selection, wrong UUID,
missing/unwritable roots, symlink escape, child cache/temp routing, and existing
success/failure/interruption cleanup. Run adjacent contract guards and inventory.
Do not equate stubbed npm contract tests with a full frontend suite.

## Retention

Task root: /home/drakosfire/Projects/.codex/frontend-temp-allocator-20261110.
Its worktree, scratch and cache are owned by this repair. Retain source and evidence
for review; no existing files, shared caches or other worktrees are deleted.
Clean up retained reproducible task artifacts only after review and authorization.

## Implementation evidence

The allocator ignores ambient temp/cache defaults, checks the resolved workspace
and evidence filesystem before allocation, and passes task-owned temp/cache
settings to Node/npm/Git children. The tiny persistent `/tmp` lock remains the
same inode/coordination boundary. `--workspace-root` plus `--workspace-uuid`
provides explicit portability; there is no automatic storage fallback.

Local guard result: 44 passed, including real fixture Git worktrees, a real child
Python temp-path probe, cancellation cleanup and storage failure cases. Actual
host preflight confirms the expected Projects UUID. AST parsing and diff whitespace
checks pass. Existing Python plugin deprecation warnings remain.

The adjacent contract suite is 13 passed / 1 failed on both the candidate and an
isolated exact-base 573d72f9a checkout: inventory lacks classification for
`apps/live-control-ui/src/media/MediaImageWizard.edit.test.tsx`. The inventory
command reports that same inherited failure. No classification is silently added
outside this lease. No npm download, full frontend run or product build is claimed.

Retained paths under the task root: `worktrees/buddy` (implementation, about 313 MB),
`verification/baseline` (exact-base failure witness, about 313 MB), `scratch`
(test fixtures/logs, about 3 MB), `cache` (empty). All are on the Projects UUID.
No prior data, shared caches or other-task files were removed; reclaimed bytes: 0.
Only newly generated fixture worktrees/temp directories were cleaned by their tests.
The worktree is not on main. After review/publication, request scoped cleanup of
retained reproducible artifacts; preserve implementation commits and evidence first.
