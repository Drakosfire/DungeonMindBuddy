# CI: keep local frontend verification off the root filesystem

Status: ACTIVE. PR topology: parallel-independent.

## Authority and lane

The coordinator adopts this bounded repair under the user's request to fix
continuing temporary-file disk exhaustion. Base is main
573d72f9a5e4f296fdb7de055b85882a568969bb, confirmed through the read-only GitHub
connector on 2026-11-10. Direct Git fetch was network-policy blocked; the matching
commit is present locally. Branch: codex/frontend-projects-temp-allocator.

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
