# Agent operating policy

DungeonMindBuddy owns Buddy product/runtime behavior. This file is the repository's
agent policy; slice-specific authority lives in a durable pinned handoff. Legacy
`.cursor` rules and skills are not required reading or additional policy gates.
When consulting historical process material, apply this policy and explicit user
instructions rather than conflicting legacy requirements.

## Start here

Use the [documentation index](Docs/README.md) to find the owning contract.
Read the active handoff before implementing, and use the verification standard
below for the affected boundary. The [lab guide](evals/README.md) points to
experimental runners and their inputs.

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

The designer or owner named in the bounded assignment authors or adopts its handoff before dispatch. Responsibilities derive from that assignment, not a standing Steward role. This wording grants no additional merge, runtime, provider, or model authority. An implementation worker consumes the pinned authority; it may redesign or activate it only when explicitly assigned that design work.

- `BLOCKED` records a concrete design with unresolved gates. It grants no write
  lease and does not allocate an implementation lane.
- `ACTIVE` means the slice is authorized to start, not ready to merge. Record
  explicit authorization, a durable pinned assignment, the bounded write set,
  and any actual start prerequisite. If there is no prerequisite, work may start;
  do not wait for evidence the work itself is meant to produce.
- Record how the slice will be verified at the owning boundary. Collect results
  during implementation and require the applicable evidence and approvals at
  review, merge, or delivery. Only a named prerequisite (such as an unmerged
  dependency or an unresolved write/runtime collision) can block start.
- Reuse an existing pinned handoff or assignment if it already records the
  scope and ownership. Routine, explicitly authorized, single-PR work may use
  a short pinned brief; no separate handoff PR or full template is required.
- The ACTIVE allowlist is an exclusive expected write lease. Other lanes may
  read those paths but must not edit them without an explicit transfer or split.
- For a product slice, name the ordinary user action and visible result. Connect
  the smallest safe path through the real app entry point early. Add supporting
  infrastructure when a concrete boundary or failure case requires it. If that
  prerequisite grows before the app path works, checkpoint the scope and
  deliver the smallest independently useful outcome the user authorized.
  Helper evidence does not complete a product slice.
- Before activation, critique the invariant and its failure cases. Re-anchor when
  gates change; record newly knowable facts without silently changing the mission.
- A lane names its branch/base, isolated checkout, handoff, write set and relevant
  ports, services, databases, output directories and external state.
- Inspect open PRs and active leases before dispatch. Shared routing, registries,
  lockfiles, root configuration, schemas and sequencing documents are collision
  hotspots. Split, serialize or explicitly transfer overlapping ownership.
- If required paths or contracts exceed the lease, return to the named owner before
  editing. Git conflicts are not an ownership protocol.

Use **serial** unless explicitly choosing another topology. Record the exact
parent/order for stacked work or the concurrent lanes checked for parallel work:

- **serial** (default): one open implementation PR in the workstream. A successor
  may be pinned as BLOCKED; it is not dispatched until its recorded gates resolve.
- **stacked**: name the exact unmerged parent/head and merge/rebase order.
- **parallel-independent**: no unmerged behavioral dependency and safe, explicit
  write/runtime ownership; name the concurrent lanes checked.

Opening the assigned PR is already part of authorized work. A newly discovered
capability does not authorize another PR. Fix an in-scope defect in the current
PR; otherwise the named owner decides whether to amend the slice, split it or change
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

## Local verification standard and hosted pause

Alan requested local-first verification and pausing long automatic GitHub PR runs.
The operational standard after this policy lands is local exact-source evidence,
not waiting for the long Hosted validation/World ownership workflows. Those two
workflows remain manually dispatchable with all commands/tests intact. Short
focused regression/security checks remain automatic. No branch protection is changed.

For every change, choose only the minimal checks needed to verify the changed
invariant at its owning boundary, including the relevant failure cases. Inspect
the exact cumulative diff and record the commands, revision, environment,
coverage and limitations. A documentation-only change normally needs only diff,
consistency and affected-link checks; do not run product tests without an
identified reason. For code, use focused test cases and other checks only where
they establish an affected behavior. Use the owning locked environment and an
isolated exact-SHA checkout when exact-source evidence is needed.

Verification scope is governed by this section. Handoffs, templates, skills,
agent prompts, reviewer requests, prior receipts and CI inventories may identify
what needs proof. They cannot widen the local verification permitted here.
Before starting a test or delegating one, identify the changed behavior, the
relevant failure cases, and the exact cases or manual checks that prove them.
Inspect what a wrapper or unfiltered command selects before using it. If it
selects a prohibited suite or cannot target the cases, use a narrower entry
point or record the coverage gap. Review existing evidence before repeating
work. Repeat a check only to resolve a material gap in source, coverage,
isolation or credibility. If a prohibited run starts, stop it promptly and
record it as incomplete.

Do not run an entire named backend contract, a full frontend hosted or discovered
suite, or a blanket full-project test run for local agent verification. Membership
of a focused test in a broad contract is not a reason to run the contract. Preserve
required auth, principal, CAS, rollback, history and graph draft-loss protections
with focused checks when affected. Do not delete or disable tests to make checks
pass. If separate full-suite evidence is required for release, record it as
missing; focused checks do not satisfy it and no gate is bypassed or claimed green.

Honor `/tmp/dungeonmind-frontend-verification-<uid>.lock` for focused local
frontend tools. For browser, build, or database checks needing substantial scratch,
verify the Projects filesystem before allocating a task directory. Use
`mktemp -d "$HOME/Projects/.codex/buddy-check.XXXXXX"` and keep that task's scratch
and caches there. Remove disposable outputs when finished and retain evidence
referenced by the handoff. Never reuse evidence from a different SHA or represent
an incomplete, stale or failed check as passing.

Database checks use one explicitly owned disposable App clone per workstream,
reused across serial cases and retries. Prepare/reset fixture state between cases;
close workers and connections before final exact-clone teardown after acceptance
or abandonment. Use the existing read-only Core snapshot where required. Never
use operator/live data or providers, allocate per-case App clones, or run full
contents scans merely to inventory an exclusively owned benchmark database.
Retain SHA, commands, versions, isolation/cleanup and all exit/failure evidence.
Auth/principal/CAS/rollback/history and graph draft-loss protections remain required
when affected. Independent exact-head review and user/process merge authority
remain separate from test evidence. The local tool is not a self-hosted runner or
a replacement GitHub status check; no fabricated hosted-green claim is permitted.
Report full qualification as missing or failed until the required proof exists.
Apply that status only to the delivery gate that requires it. Existing unmerged CI drafts do not
silently reactivate long PR runs: reconcile triggers/authority with this policy.

Rollback: restore only the two removed pull_request trigger blocks from the parent
revision after an explicit reviewed rollback decision; the manual commands/tests
are unchanged. Review workflow changes and local guard evidence together. Never
change protections/security rules or deployment as part of this policy.

## Delivery and deployment

**Name the gate.** State whether a blocker affects implementation, merge,
staging, activation, or product acceptance. Record the affected behavior or
risk, the missing evidence or operator action, and its owner. Continue
authorized work outside that gate. An inherited failure, historical HOLD, or
unfinished platform qualification blocks a delivery only when it affects the
candidate or an applicable gate explicitly requires that evidence.

**Use the routine path for reversible image updates.** Follow the approved
deployment path. Verify the current serving parent, the exact candidate source
and image, and a compatible rollback. Check readiness and smoke the changed
user workflow where applicable. Use the relevant first-deployment or change
procedure when the release affects schemas or persisted data, permissions,
networking, proxy configuration, or recovery compatibility. Preserve applicable
release, security, and operator gates. Keep local verification focused as
specified above.

**Reuse evidence on serving ports.** Compare the reviewed change and serving
candidate for the behavior being carried over. Reuse evidence when the
relevant code, configuration, schema, and runtime assumptions still match.
Check the differences that can affect behavior and record both source and
serving revisions. Verify the actual live release separately.

**Carry authorization through delivery.** Once an authorized deployment names
its target and scope, proceed through the approved path when the applicable
gates are met. Request a new decision for a material change in target, scope,
data impact, or recovery plan. If the workflow requires an operator-controlled
step, prepare the exact candidate and evidence before handing it off. Report
which stages actually happened: merged, staged, live, and accepted.

## State settlement and documentation

Name mutable authority documents that need to record the completed predecessor
in the consuming implementation handoff's write lease. Include that truthful,
backward-looking sync in the implementation PR when already knowable. Never
pre-mark the in-flight slice complete, invent its merge SHA/review count or claim
an unfinished successor is done.

Facts learned after merge normally travel with the next dependent implementation.
If no suitable successor exists or delay would leave authority materially
misleading, the owner named in the assignment performs a guarded state sync after re-anchoring. Keep the whole sync
coherent before dependent dispatch. Stable architecture/reference documents
change only when their claims change.

Routine status bookkeeping does not need a separate PR. Explicitly requested
policy changes and design/architecture artifacts explicitly requested in the assignment may have
focused review PRs. `DOCUMENTS` is retired as a generic standalone flow.
Handoffs use `HANDOFF-<FLOW>-<short-slug>.md`; PR titles use `<FLOW>: <capability>`.
FLOW names the owning workstream, not a fixed enum. PR numbers are transport
metadata, not naming authority. Git history is the default archive.

## Agent action catalog

The [Buddy action catalog](evals/plan-authoring-benchmark.md#action-catalog)
is the canonical inventory of actions Buddy can choose, actions the operator
can complete through Buddy, and requested capabilities. Other READMEs,
handoffs and benchmark documents link to this inventory.

Before changing an action, its routing, or its review, confirmation or
recovery boundary, check the catalog. The owning lane must update the
affected entry in the same PR when an action is added, changed, removed,
or its evidence status changes. Record the surface and action owner, the
strongest verified boundary and its evidence link, and any remaining gap.
Distinguish ordinary agent turns, operator actions, component tests, and
requested behavior. A shipped route or passing component test alone does
not establish ordinary workflow proof.

When a change affects which action Buddy should choose or when it may act,
use the [benchmark catalog](evals/README.md) to identify the owning benchmark
and update its coverage in the same PR. Use its fixture and scoring rules for
the selected cases and apply the local verification scope above. Apply the state-settlement rule
above when new evidence arrives after merge.

## Efficient investigation

Use focused symbol/route search and small context packs when available; otherwise
use `rg` and targeted reads. Keep Git, search, test, and log output focused.
Preserve failures, stack traces, compiler and migration errors, and
destructive-command risks.
Fetch and compare exact remote refs when state matters. Obtain explicit approval
for destructive actions unless already authorized by the user.

## Model prompt context boundary

Host-side metadata is not context and must never be sent in product model prompts.
Follow the [ecosystem prompt policy](https://github.com/Drakosfire/DungeonOverMind/blob/main/Docs/Guides/GUIDE-model-prompt-context-boundary.md).
Keep identifiers, hashes, receipts, execution bindings, accounting/capacity policy
and telemetry in their existing host owners, outside model-visible input. Preserve
meaningful task/evidence context, user constraints and all host checks. Use local
aliases when models must select or cite items; the host resolves exact identities.
Audit final serialized requests, including nested state and tool results. Do not
replace this boundary with regex scrubbing, another prompt channel or a new
provenance authority.
