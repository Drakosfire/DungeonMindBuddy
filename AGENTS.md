# Agent operating policy

This file is the durable repository operating law for agents working in DungeonMindBuddy. It states invariants and ownership rules. Procedural commands belong in the linked Cursor rules/skills; slice-specific facts belong in the checked-in HANDOFF.

## Development cycle

A development cycle is:

```text
re-anchor
→ decompose candidate capabilities
→ allocate an isolated lane
→ design one slice
→ dispatch
→ review cycle 1..N
→ merge
→ atomic state-authority sync
→ re-anchor before the next dispatch
```

The cycle does not end at a green merge. It ends when the repository state and every mutable document that claims current workstream state agree again.

### Foundational invariants

1. **Re-anchor before dispatch.** Current repository authority and `main` beat chat history, stale handoffs, Project Sources, and old summaries.
2. **One independently useful capability.** One slice has one merge-ready invariant. Split when a second independently useful/revertible contract appears.
3. **The HANDOFF §4 allowlist is a write lease.** While a slice is active, its listed paths are that lane's exclusive expected write set. Other lanes may read them but must not edit them without an explicit split, transfer, or serialization decision.
4. **Parallel lanes use branches + worktrees.** Two or more agents may work concurrently when their write leases and runtime/state ownership do not conflict. Git merge conflicts are a last-resort safety net, not the coordination protocol.
5. **Source isolation is not runtime isolation.** Separate worktrees can still collide through ports, services, databases, `out/`, caches, generated state, shared fixtures, or external resources. A lane must name those collisions when relevant.
6. **Review every distinct head until merge-ready.** A review cycle is one complete formal reviewer judgment against one distinct PR head SHA. Fix commits, comments, CI reruns, and handbacks do not increment the count until another formal judgment is issued.
7. **Evidence lives at the owning boundary.** Helper tests cannot prove a service, workflow, persistence, concurrency, or surface invariant they do not exercise.
8. **No silent scope expansion.** A path outside the write lease, a second durable/public contract, or a new operator/product workflow is a stop/split signal unless the handoff explicitly bounded discovery for it.
9. **Atomic state-authority sync after state transitions.** After merge, phase close, gate trip, or another sequencing transition, update every mutable workstream document that claims current status/sequence/predecessor/next action in one coherent operation before dispatching the next dependent slice. Plan/checklist/handoff are common members, not a closed set; roadmaps, trackers, status docs, or indexes belong in the sync when they carry that state.
10. **Stable authorities do not churn for ceremony.** Architecture, contracts, and reference docs change only when their claims changed—not merely because an implementation PR merged.

## Parallel lane contract

A lane is the combination of:

```text
branch + worktree + HANDOFF + write lease + relevant runtime/state ownership
```

Before dispatching parallel work:

- pin the lane's base revision;
- inspect active PRs/worktrees/handoffs for overlapping expected writes;
- treat central routing, shared registries, lockfiles, root config, active sequencing docs, and generated schemas as collision hotspots;
- prefer splitting a seam so each lane has a clean owner;
- otherwise serialize the work or explicitly transfer the contested path.

When a worker discovers it needs a path leased by another active lane, stop and report the path, current owner, reason it is needed, and whether the seam can be split. Do not edit first and rely on Git to arbitrate later.

## Review-cycle counting

Use this exact definition across handoffs, reviews, and completion records:

```text
one formal reviewer judgment against one distinct head SHA = one review cycle
```

Examples:

```text
head A → REQUEST CHANGES = review cycle 1
head B → REQUEST CHANGES = review cycle 2
head C → APPROVE         = review cycle 3
```

Multiple findings in one judgment are still one cycle. A fix commit by itself is not a cycle. Re-reviewing the same unchanged head without a new formal judgment does not create useful process telemetry.

Review-cycle count is learning telemetry, not a quality target. Do not cap rounds to make the metric look good. Repeated finding classes should tighten future steward critique, handoff evidence, or repository rules.

## Atomic state-authority sync

After a state-changing event, first identify the workstream's mutable state authorities. Examples:

- `PLAN-*`
- `CHECKLIST-*`
- active HANDOFF status/archive state
- active `ROADMAP-*`
- PR/sequencing trackers
- current-state/status documents
- source/index manifests when they claim the current active set

Update the applicable set coherently so a fresh agent cannot observe contradictory states such as "PR pending" in a roadmap while `main` already contains the merge.

The sync records the new state; it does not rewrite architecture history or bundle unrelated cleanup.

## Token-efficient repo navigation

Use SymDex before broad file reads. Prefer symbol search, route search, file outlines, call graphs, literal text search, semantic search, and token-budgeted context packs before reading full files.

Use RTK for noisy shell commands such as git status, git diff, git log, grep, find, tests, docker logs, and build output.

Do not dump large files, logs, generated files, dependency trees, or vendored code into context unless explicitly needed. Correctness overrides token savings: preserve failed tests, stack traces, compiler errors, migration warnings, security findings, and destructive-command risks.

Never run destructive commands without explicit user approval.

### Git history and merge commits

After merges, prefer `git rev-parse HEAD` and `git show -s --format=… HEAD` over treating `git log --oneline` as the whole truth when the environment may omit merge commits. When remote state matters, fetch and compare exact refs rather than trusting wrapper output.

## External-agent PR loop

For a GitHub PR opened by an external/Codex-style worker, the procedure is `.cursor/skills/external-agent-pr-loop/SKILL.md`; non-negotiable loop invariants are in `.cursor/rules/external-agent-pr-loop.mdc`. Use `scripts/review_external_pr.py {fetch | verify | post | merge}` rather than rebuilding the `gh + git + sed` workflow manually.

The checked-in HANDOFF, cumulative diff, nano-commit story, and independently rerun evidence are the review contract. The PR description is transport metadata.

## Handoff and PR naming

Handoffs use:

```text
Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md
```

PR titles use:

```text
<FLOW>: <short capability>
```

`<FLOW>` is the repository/workstream's explicit operating label (for example `BUILD`, `STATBLOCK`, `TIMELINE`, `DOCUMENTS`, or another named active flow such as `HERMES`). Do not treat a historical four-flow list as a closed enum; the handoff must still name one unambiguous owner.

`DOCUMENTS` also covers repository development-process documentation/tooling when no product-domain flow owns the change.

PR numbers are optional GitHub transport metadata. They are not part of handoff filenames, branch names, PR titles, or design authority. Historical `HANDOFF-pr<N>-…` names remain historical and are not retroactively renamed.
