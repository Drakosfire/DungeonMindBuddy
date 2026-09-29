# Agent operating policy

DungeonMindBuddy owns Buddy product/runtime behavior. This file is the repository's
agent policy; slice-specific authority lives in a durable pinned handoff. Legacy
`.cursor` rules and skills are not required reading or additional policy gates.
When consulting historical process material, apply this policy and explicit user
instructions rather than conflicting legacy requirements.

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

## Handoff and lane authority

The designing steward authors or adopts the bounded handoff before dispatch.
An implementation worker consumes that authority; it may redesign or activate
it only when explicitly assigned design/stewardship work.

- `BLOCKED` records a concrete design with unresolved gates. It grants no write
  lease and does not allocate an implementation lane.
- `ACTIVE` requires explicit authorization, a pinned path/ref, satisfied gates,
  an expected-path allowlist (§4), verification evidence, and declared PR topology.
- The ACTIVE allowlist is an exclusive expected write lease. Other lanes may
  read those paths but must not edit them without an explicit transfer or split.
- Before activation, critique the invariant and its failure cases. Re-anchor when
  gates change; record newly knowable facts without silently changing the mission.
- A lane names its branch/base, isolated checkout, handoff, write set and relevant
  ports, services, databases, output directories and external state.
- Inspect open PRs and active leases before dispatch. Shared routing, registries,
  lockfiles, root configuration, schemas and sequencing documents are collision
  hotspots. Split, serialize or explicitly transfer overlapping ownership.
- If required paths or contracts exceed the lease, return to the steward before
  editing. Git conflicts are not an ownership protocol.

Every ACTIVE handoff declares one topology:

- **serial** (default): one open implementation PR in the workstream. A successor
  may be pinned as BLOCKED; it is not dispatched until its recorded gates resolve.
- **stacked**: name the exact unmerged parent/head and merge/rebase order.
- **parallel-independent**: no unmerged behavioral dependency and safe, explicit
  write/runtime ownership; name the concurrent lanes checked.

Opening the assigned PR is already part of authorized work. A newly discovered
capability does not authorize another PR. Fix an in-scope defect in the current
PR; otherwise the steward decides whether to amend the slice, split it or change
its topology. Preserve useful work and evidence when superseding a lane.

## Git and checkout safety

Never work on or leave local `main` checked out. Start from the fetched remote:

```bash
git fetch origin main
git switch -c codex/<slice> origin/main
# Or allocate a separate checkout:
git worktree add -b codex/<slice> <path> origin/main
```

If this checkout is on `main`, fetch and detach at `origin/main`. Before finishing,
`git branch --show-current` must not report `main`. Do not remove a checkout used
by an active task or runtime. Coordinate ownership and verify its replacement
before pruning it. Separate checkouts do not isolate ports or databases.

## Review and verification

Review the exact cumulative base→head change, affected contracts and required
evidence. Independently verify behavior at its owning boundary. State inherited
failures, missing evidence and the limits of author-reported checks honestly.
Preserve required human acceptance; technical checks do not imply it.

One complete formal judgment against one distinct head SHA is one review cycle.
Fix commits, comments and CI reruns alone are not new cycles. Request another
review for a material code, evidence or authority change; avoid status-only
commits and repeated unchanged HOLD loops. Review count is learning telemetry,
not a target or a reason to stop before correctness.

`scripts/review_external_pr.py` is optional transport tooling. Inspect the chosen
subcommand before use: helpers may stash edits, switch checkouts or update local
`main`. Do not use helper behavior that conflicts with isolation, ownership or
merge authority. Direct Git/GitHub tools are valid when they preserve these rules.
The pinned ACTIVE handoff and cumulative change are the review contract; the PR
body is its transport summary.

## State settlement and documentation

Name mutable authority documents that need to record the completed predecessor
in the consuming implementation handoff's write lease. Include that truthful,
backward-looking sync in the implementation PR when already knowable. Never
pre-mark the in-flight slice complete, invent its merge SHA/review count or claim
an unfinished successor is done.

Facts learned after merge normally travel with the next dependent implementation.
If no suitable successor exists or delay would leave authority materially
misleading, perform a guarded steward sync after re-anchoring. Keep the whole sync
coherent before dependent dispatch. Stable architecture/reference documents
change only when their claims change.

Routine status bookkeeping does not need a separate PR. Explicitly requested
policy changes and steward-designated design/architecture artifacts may have
focused review PRs. `DOCUMENTS` is retired as a generic standalone flow.
Handoffs use `HANDOFF-<FLOW>-<short-slug>.md`; PR titles use `<FLOW>: <capability>`.
FLOW names the owning workstream, not a fixed enum. PR numbers are transport
metadata, not naming authority. Git history is the default archive.

## Efficient investigation

Use focused symbol/route search and small context packs when available; otherwise
use `rg` and targeted reads. Use RTK when available for noisy output. Missing
optional navigation tools do not block ordinary investigation. Preserve useful
failure output and avoid dumping whole logs, dependency trees or historical docs.
Fetch and compare exact remote refs when state matters. Obtain explicit approval
for destructive actions unless already authorized by the user.
