# HANDOFF — Foundational steward operating law

**Created:** 2026-08-12  
**Status:** COMPLETE — merged as PR #572.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOCUMENTS-foundational-steward-law.md`  
**Conversation:** DungeonBuddy development-process optimization  
**Flow / agent:** `DOCUMENTS`  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `9d5efb7eaa92a4890bd49db45130e5843777c8b9`  
**Merged revision:** `cf3172612d140061e73901394f3bb4a9f90da49b`  
**PR:** #572 — `DOCUMENTS: establish parallel steward operating law`  
**Review cycles:** 2

**Completion note:** Review Cycle 1 tightened equivalent-checkout language and made atomic state-authority sync a real transaction boundary under sequential-write tooling. Review Cycle 2 approved the polished head. Named successor remains: replace Jumpstart with the Steward Cycle and slim the handoff/runbook payload.

## §1 Mission and merge-ready invariant

**Mission:** A fresh agent can learn DungeonMindBuddy's durable development law from `AGENTS.md` and the always-on rules, including safe parallel worktree operation, review-cycle counting, and atomic state synchronization, without relying on Jumpstart or a per-slice handoff for universal policy.

**Merge-ready invariant:** Foundational process rules have one coherent meaning across `AGENTS.md`, git workflow, external-agent review rules, and re-anchor guidance: concurrent implementation is isolated by branches/worktrees and exclusive write leases, every formal judgment against a distinct PR head is counted as one review cycle, merge does not complete the development cycle until mutable state-authority documents are synchronized atomically, and no rule silently restores the stale single-active-branch model.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern all changed paths? | Yes. All changed files define or point to durable repository operating law. |
| Most likely failure | New `AGENTS.md` says parallel lanes are normal while `dungeonbuddy-git-workflow.mdc` still prefers one active branch, or atomic sync language remains narrowly plan/checklist-only. |
| Evidence that detects it | Exact text scans plus cumulative diff review for contradictory branch, review-cycle, and sync terminology. |
| Easiest boundary to under-test | Cross-file policy consistency. |
| Stop/split trigger | Any implementation/tooling change beyond process-policy text. |

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Current `AGENTS.md`, `.cursor/rules/external-agent-pr-loop.mdc`, `.cursor/rules/dungeonbuddy-git-workflow.mdc`, `.cursor/rules/anchor.mdc` |
| Current contradiction | Git workflow recommends one active branch while current operation uses parallel agents/worktrees. |
| Current duplication | Universal review/doc-sync rules are repeated in Jumpstart and handoff materials instead of being clearly foundational. |
| Named successor | Rename/reduce Jumpstart into Steward Cycle and slim the handoff template. |
| What remains false | No lane-preflight automation yet; no template diet yet. |

**State-authority sync set for this slice:** this handoff only. No product roadmap/tracker status changes are implied by a process-policy PR.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Fresh agent reads repo law | Learns navigation + old narrow PR conventions | Learns durable steward invariants and where procedure lives | `AGENTS.md` |
| Two agents start independent slices | Repo rule discourages parallel branches | Parallel worktrees/branches are normal when write leases do not overlap | git workflow rule |
| Agent needs a file leased by another lane | No foundational collision semantic | Stop, split seam, serialize, or explicitly transfer the write lease | `AGENTS.md` + git workflow |
| Reviewer revisits a changed head | Re-review required but counting is informal | One formal judgment per distinct head SHA = one review cycle | external-agent rule |
| Merge updates current-state docs | Atomic doc-sync is plan/checklist/handoff-shaped | All mutable state-authority docs named by the workstream move together | external-agent + anchor rules |

Adversarial sequence: Lane A leases shared registry → Lane B discovers it also needs that path → Lane B may read it but must not edit it until ownership is split/transferred/serialized; a normal merge conflict is not the coordination mechanism.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `AGENTS.md` | Make foundational operating law explicit and point procedure downward. |
| Modify | `.cursor/rules/dungeonbuddy-git-workflow.mdc` | Replace stale single-active-branch guidance with worktree/write-lease parallelism. |
| Modify | `.cursor/rules/external-agent-pr-loop.mdc` | Define review cycles and broaden atomic state sync invariant. |
| Modify | `.cursor/rules/anchor.mdc` | Align re-anchor wording with generalized state-authority sync and current invariant names. |
| Create | `Docs/Plans/HANDOFF-DOCUMENTS-foundational-steward-law.md` | Checked-in slice authority. |

## §5 Explicitly out of scope

| Path/capability | Why |
|---|---|
| `Docs/Plans/JUMPSTART-docs-relevance-first.md` | Successor owns rename and reduction. |
| `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` | Successor owns template diet. |
| `.cursor/skills/external-agent-pr-loop/SKILL.md` | Procedure remains valid; successor may polish pointers after Steward Cycle lands. |
| `scripts/**` | Automation is a later slice. |
| Product roadmaps/trackers | No product sequence changes. |

## §6 Implementation contract

Input: current repository process law on the pinned base.

Output: a single foundational operating model with these required concepts:

- re-anchor before dispatch;
- one independently useful capability / one merge-ready invariant;
- §4 allowlist doubles as an exclusive write lease for concurrent lanes;
- worktrees and short-lived branches are the normal parallel isolation mechanism;
- overlapping read scope is fine; overlapping write scope requires explicit coordination;
- runtime/service/durable-state isolation is separate from source-file isolation;
- review cycle = one formal reviewer judgment against one distinct head SHA;
- fixes/comments/CI reruns do not increment review count until another formal judgment;
- merge completes implementation, but the development cycle completes only after atomic state-authority sync;
- architecture documents do not churn merely because implementation merged;
- no silent scope expansion.

Failure behavior: contradictory policy across changed foundational files blocks merge.

Persistence/replay: not applicable — process text only.

## §7 Evidence required to merge

| Guarantee | Owning boundary | Evidence | Expected | Stop condition |
|---|---|---|---|---|
| No stale single-active-branch instruction remains in active Buddy git law | git workflow | exact diff/text inspection | parallel worktree model is unambiguous | active rule still says prefer one active branch |
| Review-cycle definition is deterministic | external-agent rule | text inspection | distinct-head formal judgment semantics stated once | comments/fix commits can ambiguously increment count |
| Atomic sync covers all mutable state authorities | external-agent + anchor | text inspection | plan/checklist/handoff are examples, not closed set | current-state roadmap/tracker can remain contradictory after merge |
| AGENTS is foundational, not a second runbook | `AGENTS.md` | structural review | principles + pointers, no command duplication | procedural command catalog copied into AGENTS |
| Concurrent lanes fail before file conflict | AGENTS + git workflow | adversarial policy review | write lease collision requires stop/split/transfer/serialize | merge conflict remains normal collision detector |
| Scope is exact | PR diff | changed-path review | only §4 paths changed | any other path changes |

Verification commands for an implementation environment:

```bash
git diff --check
git diff --name-only 9d5efb7eaa92a4890bd49db45130e5843777c8b9...HEAD
rg -n "single active branch|one active branch" AGENTS.md .cursor/rules/dungeonbuddy-git-workflow.mdc .cursor/rules/external-agent-pr-loop.mdc .cursor/rules/anchor.mdc
rg -n "review cycle|state-authority|write lease|worktree" AGENTS.md .cursor/rules/dungeonbuddy-git-workflow.mdc .cursor/rules/external-agent-pr-loop.mdc .cursor/rules/anchor.mdc
```

## §8 Required review handback

Record exact PR/head, changed paths, review-cycle number, findings, whether every contradiction scan is resolved, and any process lesson that should move into the Steward Cycle successor.

## §9 Acceptance rubric

- [x] `AGENTS.md` states the durable development cycle and delegates procedure rather than duplicating it.
- [x] Parallel worktrees/branches are explicitly supported and stale single-active-branch guidance is removed.
- [x] §4 path allowlists are defined as exclusive write leases while a slice is active.
- [x] Runtime/service/durable-state collision is distinguished from source-file collision.
- [x] Review-cycle counting is deterministic and head-SHA based.
- [x] Atomic state-authority synchronization is broader than plan/checklist/handoff and happens before next dispatch.
- [x] Re-anchor terminology matches the new invariant.
- [x] No successor implementation (Steward Cycle rename/template diet/automation) is pulled into this PR.
