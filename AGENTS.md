# Agent operating policy

This file is the durable repository operating law for agents working in DungeonMindBuddy. It states invariants and ownership rules. Procedural commands belong in the linked Cursor rules/skills; slice-specific facts belong in the checked-in HANDOFF.

## Ecosystem execution core — overmind-agent-core-v1

These rules are intentionally shared across active DungeonMind ecosystem repositories. Repository-specific law may add constraints, but it must not weaken this core.

1. **Re-anchor before action.** Fetch the current remote default branch and inspect relevant open PRs/active work before editing, reviewing, or merging. Chat history, stale handoffs, and local `main` are not current authority.
2. **Respect ownership boundaries.** Cross-repository architecture and sequencing belong in DungeonOverMind; runtime/product implementation belongs in the repository that owns the capability. When a change crosses owners, name the contract.
3. **Handoffs are portable bounded contracts.** A handoff may live on `main`, a branch, a PR, or another durable pinned ref/location. Its location alone neither activates nor invalidates it. Execution authority comes from explicit authorization/status, a pinned authority/ref, and bounded scope/write ownership. Do not require a handoff to be merged to `main` unless the specific workstream explicitly makes that a gate.
4. **Finish authorized implementation work all the way to a PR.** Once implementation is authorized, ordinary completion includes: implement → test/verify → inspect the cumulative diff → commit intended changes → push the branch → open or update the assigned PR. If no PR exists, open it. Do not stop with intended work only local, uncommitted, or unpushed and wait for another prompt to commit/push/open the PR.
5. **Merge is separate authority.** Opening/updating a PR is part of implementation completion; merging it is not. Merge only when the user or the repository's explicit process authorizes merge.
6. **Use isolated Git lanes.** Do not develop on local `main`. Use a branch/worktree or equivalent isolated checkout, and treat file/runtime/state collisions as coordination problems rather than relying on Git conflicts.
7. **Keep slices bounded.** One implementation slice should deliver one independently useful capability. A second capability, new durable/public contract, or unplanned extra PR is a stop/split signal unless explicitly authorized.
8. **Verify at the owning boundary.** Review the exact cumulative base→head diff and prove behavior at the layer that owns the invariant. A green helper test is not evidence for a boundary it does not exercise.
9. **Settle after merge.** Re-anchor, synchronize mutable authority that now became stale, and prune superseded process/transition scaffolding. Git history is the default archive; preserve a separate archive copy only when it carries unique durable evidence.

## Development cycle

A development cycle is:

```text
re-anchor
→ decompose candidate capabilities
→ design one slice
→ pin durable HANDOFF authority
→ satisfy activation gate / re-anchor
→ declare PR topology
→ allocate an isolated implementation lane
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
3. **The designing steward owns handoff durability.** The steward/designing agent authors or adopts the implementation HANDOFF and ensures the exact authority is durably addressable at a pinned path/ref before dispatch. It does not have to be on `main`. An implementation worker consumes that pinned handoff; it does not materially redesign or activate its own authority document unless the assigned slice is itself design/architecture work.
4. **BLOCKED is durable, not dispatched.** A handoff may be stored on any durable pinned ref with `Status: BLOCKED` while a predecessor, review, merge, operator decision, or other activation gate remains unresolved. Its presence does not create an implementation lane, reserve its §4 paths, or authorize code changes. Only an explicitly authorized `ACTIVE` handoff may be dispatched. Activation requires re-anchoring after the gate becomes true and recording the newly knowable activation facts without changing the slice mission/invariant unless the design is deliberately re-reviewed.
5. **The HANDOFF §4 allowlist is a write lease only while the slice is ACTIVE.** While a slice is active, its listed paths are that lane's exclusive expected write set. BLOCKED handoffs are durable design authority but hold no write lease. Other lanes may read leased paths but must not edit them without an explicit split, transfer, or serialization decision.
6. **Parallel lanes use branches + isolated checkouts.** Worktrees are the normal local mechanism; an external/remote worker may provide equivalent checkout isolation. Two or more agents may work concurrently when their write leases and runtime/state ownership do not conflict. Git merge conflicts are a last-resort safety net, not the coordination protocol.
7. **Source isolation is not runtime isolation.** Separate worktrees/checkouts can still collide through ports, services, databases, `out/`, caches, generated state, shared fixtures, or external resources. A lane must name those collisions when relevant.
8. **Review every distinct head until merge-ready.** A review cycle is one complete formal reviewer judgment against one distinct PR head SHA. Fix commits, comments, CI reruns, and handbacks do not increment the count until another formal judgment is issued.
9. **Evidence lives at the owning boundary.** Helper tests cannot prove a service, workflow, persistence, concurrency, or surface invariant they do not exercise.
10. **No silent scope expansion.** A path outside the write lease, a second durable/public contract, or a new operator/product workflow is a stop/split signal unless the handoff explicitly bounded discovery for it.
11. **Atomic state-authority sync is backward-looking maintenance.** Each implementation handoff must identify the mutable authority documents that need to be synchronized for its already-completed predecessor. Those updates travel in the implementation PR when they are truthfully knowable before that PR merges. They record completed prior work; they do not pre-mark the in-flight implementation slice complete, invent its future merge SHA/review count, or advance a successor as already done. Facts that become knowable only when the current implementation merges are normally recorded by the next dependent implementation PR's predecessor sync. If no suitable successor exists, or delaying the truth would leave repository authority materially misleading, the steward applies a direct guarded sync after re-anchoring. Cross-repository sync follows the same rule. Plan/checklist/handoff are common members, not a closed set; roadmaps, trackers, status docs, or indexes belong in the sync when they carry that state.
12. **Documentation-only PRs are exceptional, not forbidden.** Routine handoff maintenance, roadmap/tracker/status synchronization, completion recording, and other state-authority bookkeeping should usually travel with the work that consumes them. A handoff may be committed/pushed on a branch, carried in a design PR, merged to `main`, or otherwise pinned durably; no one storage location is required by repository law. Rare steward-designated **design or architecture PRs** are allowed when the design artifact itself needs explicit review before implementation. Executable process/tooling changes use normal implementation PRs unless the user explicitly directs another guarded transaction.
13. **Stable authorities do not churn for ceremony.** Architecture, contracts, and reference docs change only when their claims changed—not merely because an implementation PR merged.
14. **PR topology is handoff authority; the default is serial.** Every ACTIVE implementation handoff must declare whether its assigned PR is `serial`, `stacked`, or `parallel-independent`. If the field is absent or ambiguous, treat it as `serial`: one open implementation PR in that workstream, and any newly discovered successor/repair returns to the steward rather than opening another PR. “Open the assigned PR without asking” means the worker does not need separate user confirmation for the one PR already authorized by its ACTIVE handoff; it is not permission to choose or expand PR topology. A `stacked` handoff must name its exact unmerged predecessor and required merge/rebase order. `parallel-independent` requires no dependency on another unmerged result plus safe write/runtime ownership. A dogfood STOP or new defect observed on a synthetic/combined unmerged head is evidence for steward re-decomposition, not automatic authority to spawn another PR.

## Parallel lane contract

An **active implementation lane** is the combination of:

```text
branch + isolated checkout/worktree + ACTIVE HANDOFF + write lease + relevant runtime/state ownership
```

A checked-in `BLOCKED` handoff is not a lane and does not participate in write-lease collision ownership until activation.

Before dispatching parallel work:

- pin the lane's base revision;
- inspect active PRs/worktrees/ACTIVE handoffs for overlapping expected writes;
- treat central routing, shared registries, lockfiles, root config, active sequencing docs, and generated schemas as collision hotspots;
- prefer splitting a seam so each lane has a clean owner;
- otherwise serialize the work or explicitly transfer the contested path.

When a worker discovers it needs a path leased by another active lane, stop and report the path, current owner, reason it is needed, and whether the seam can be split. Do not edit first and rely on Git to arbitrate later.

## PR topology and open-PR budget

PR creation is an execution step inside an already designed lane. It is not a worker-level scheduling decision.

The HANDOFF must name one topology:

```text
serial
  default
  one open implementation PR in the workstream
  dependent/successor handoffs may exist durably as BLOCKED
  no successor branch/PR until predecessor merge + state sync + re-anchor

stacked
  explicit exception for dependent unmerged work
  each handoff names the exact parent PR/head/base relation
  merge/rebase order is written before dispatch
  a worker may open only the stacked PR explicitly assigned to its handoff

parallel-independent
  explicit exception for truly independent work
  no unmerged behavioral dependency
  disjoint or deliberately isolated write/runtime ownership
  each handoff names the concurrent lanes it was checked against
```

The user may direct agents not to ask for confirmation before opening the PR named by an ACTIVE handoff. Honor that by opening **that assigned PR** without ceremony. Do not reinterpret it as authority to open a successor, repair, cleanup, or dogfood-followup PR.

When a new defect appears while another PR in the same workstream is open:

1. if it violates the current slice invariant and fits the current lease, fix the current PR;
2. if it is a separate capability/repair, return it to the steward, who may author and pin a `BLOCKED` successor handoff without dispatching it;
3. open another PR only when the steward has deliberately changed the topology to `stacked` or `parallel-independent` and the relevant handoff records that decision.

If the repository already contains an unplanned fan-out of dependent PRs, freeze new PR creation, land a stewardship recovery handoff, declare a drain order, and rebase/review/merge against real `main` one PR at a time. A synthetic combined branch may be useful diagnostic evidence, but it is not integration authority.

## Always release `main`

Git will not check out the same branch in two worktrees. **Never leave `main` checked out.**

- Do not work on `main`. Do not `git switch main` / `git checkout main` / `git pull` on `main` to clean up or start the next task.
- Start from the remote, without checking out local `main`:

      git fetch origin main
      git switch -c <branch> origin/main

- Add worktrees the same way. Never `git worktree add <path> main`. Never `git worktree add <path>` while this repo is on `main`.

      git fetch origin main
      git worktree add -b <branch> <path> origin/main

- If you are on `main`, release it immediately:

      git fetch origin main
      git switch --detach origin/main

- Before you finish a turn, `git branch --show-current` must not print `main`. If it does, detach as above.

## Worktree / Cursor workspace switch order

Never delete, move, or prune the checkout the **current Cursor window** is using until a replacement checkout is live in that window.

Required order:

1. `git fetch origin main`
2. Create the new worktree from `origin/main`. Never `git worktree add <path> main`. Never add a worktree while this repo has `main` checked out.

       git worktree add -b <branch> <new-path> origin/main

3. Switch the Cursor workspace / agent root onto `<new-path>`.
4. Confirm a **new terminal** launches: `pwd` is `<new-path>`, `git branch --show-current` is not `main`, and Git commands succeed.
5. Only then remove or move the previous worktree.

Do not invert this. Deleting the open worktree first leaves terminals spawning in a missing directory (`worktree doesn't exist`) and the window stays bound to a path that is gone.

`move_agent_to_root` fetches `origin/<branch>` at the destination. A local-only branch aborts that switch. Push the new branch, or open the new folder in Cursor, **before** removing the old checkout.

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

Before dispatching an implementation slice, identify the workstream's mutable state authorities that still need to record the **completed predecessor**. Examples:

- `PLAN-*`
- `CHECKLIST-*`
- predecessor HANDOFF status/archive state
- active `ROADMAP-*`
- PR/sequencing trackers
- current-state/status documents
- source/index manifests when they claim the current active set

Put that predecessor sync set in the implementation handoff's write lease. When those facts are already true before implementation begins, land the whole sync in the implementation PR alongside the executable capability. This keeps routine maintenance attached to the work that consumes the predecessor rather than creating a documentation PR.

The sync is intentionally backward-looking. It may record the predecessor's exact PR/merge SHA, review-cycle count, accepted design decision, completion/archive state, and the fact that the current implementation slice is now the active work. It must **not** mark the current implementation slice `DONE`, invent its future merge SHA or final review-cycle count, or claim a successor has completed.

Facts that become knowable only after the current implementation merges are carried by the next dependent implementation PR's predecessor sync. When there is no suitable successor, when a cross-repository dependency must be truthful before further dispatch, or when waiting would leave active authority materially misleading, use a direct guarded steward sync after re-anchoring. **Do not open a routine documentation-only PR for that sync.**

Prefer to land each applicable sync set together. When an API/tool can update only one file per commit, sequential file writes are acceptable only inside the same guarded sync operation: no dependent dispatch or "cycle complete" claim occurs until every intended authority is updated and the final repository state has been re-read.

The sync records completed state; it does not rewrite architecture history or bundle unrelated cleanup.

## Token-efficient repo navigation

Use SymDex before broad file reads. Prefer symbol search, route search, file outlines, call graphs, literal text search, semantic search, and token-budgeted context packs before reading full files.

Use RTK for noisy shell commands such as git status, git diff, git log, grep, find, tests, docker logs, and build output.

Do not dump large files, logs, generated files, dependency trees, or vendored code into context unless explicitly needed. Correctness overrides token savings: preserve failed tests, stack traces, compiler errors, migration warnings, security findings, and destructive-command risks.

Never run destructive commands without explicit user approval.

### Git history and merge commits

After merges, prefer `git rev-parse HEAD` and `git show -s --format=… HEAD` over treating `git log --oneline` as the whole truth when the environment may omit merge commits. When remote state matters, fetch and compare exact refs rather than trusting wrapper output.

## External-agent PR loop

For a GitHub implementation PR opened by an external/Codex-style worker, the procedure is `.cursor/skills/external-agent-pr-loop/SKILL.md`; non-negotiable loop invariants are in `.cursor/rules/external-agent-pr-loop.mdc`. Use `scripts/review_external_pr.py {fetch | verify | post | merge}` rather than rebuilding the `gh + git + sed` workflow manually.

The checked-in ACTIVE HANDOFF, cumulative diff, nano-commit story, and independently rerun evidence are the review contract. The PR description is transport metadata.

Implementation PRs include the backward-looking state-authority sync named by their handoff. Routine state maintenance does not enter a separate PR loop. Rare steward-designated design/architecture PRs may be opened under the owning flow when the design artifact itself needs review; they remain narrowly scoped and are not a revival of the generic `DOCUMENTS` flow.

## Handoff lifecycle and PR naming

Handoffs use:

```text
Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md
```

Implementation handoffs are steward-authored or steward-adopted and durably pinned before dispatch; they do not need to be on `main`. If a prerequisite is unresolved, keep the handoff `BLOCKED` with an explicit activation gate and design-time authority snapshot. When the gate becomes true, the steward re-anchors, records the newly knowable predecessor/merge/base facts, changes `BLOCKED → ACTIVE`, and only then allocates/dispatches the implementation lane.

Implementation PR titles use:

```text
<FLOW>: <short capability>
```

`<FLOW>` is the repository/workstream's explicit operating label (for example `BUILD`, `STATBLOCK`, `TIMELINE`, `CUTOVER`, or another named active flow such as `HERMES`). Do not treat a historical flow list as a closed enum; the handoff must still name one unambiguous owner.

`DOCUMENTS` is retired as a standalone PR flow. Historical `DOCUMENTS` PRs and handoffs remain historical evidence and are not retroactively renamed. Routine documentation/state-authority maintenance rides with the consuming implementation PR or, when necessary, a direct guarded steward sync. Rare design/architecture PRs use the owning workstream label rather than `DOCUMENTS`.

PR numbers are optional GitHub transport metadata. They are not part of handoff filenames, branch names, PR titles, or design authority. Historical `HANDOFF-pr<N>-…` names remain historical and are not retroactively renamed.
