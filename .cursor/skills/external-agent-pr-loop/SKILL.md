---
name: external-agent-pr-loop
description: >-
  Operational runbook for DungeonMindBuddy external-agent PRs: create the checked-in
  HANDOFF, fetch/verify/post review evidence with scripts/review_external_pr.py,
  merge an approved PR, and execute the handoff's state-authority sync set. Durable
  law lives in AGENTS.md and .cursor/rules/external-agent-pr-loop.mdc; steward
  judgment/decomposition lives in Docs/Process/STEWARD-CYCLE.md.
---

# External-agent PR loop — mechanics

Use this file for **commands and transport procedure**. Do not use it to decide whether two outcomes belong in one slice or whether parallel lanes are safe; those judgments belong in [`Docs/Process/STEWARD-CYCLE.md`](../../../Docs/Process/STEWARD-CYCLE.md).

Read when you need to:

- create a checked-in handoff for an external/Codex-style branch worker;
- fetch and verify a PR against that handoff;
- post a formal review judgment;
- merge an approved PR;
- execute the workstream-specific state-authority sync named by the handoff.

For in-IDE subagents, use `.cursor/rules/subagent-delegation.mdc` instead.

## 0. Preconditions

Before mechanics begin, the steward has already completed the Steward Cycle readiness gate:

```text
re-anchored base
one capability / one invariant
parallel lane allocated
§4 write lease known
runtime/state collision decision made
§7 evidence planned
state-authority sync set named
```

If any of those are still unclear, return to the Steward Cycle instead of compensating with a larger handoff.

## 1. Create the HANDOFF

Copy:

```bash
cp .cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md \
  Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md
```

Fill every required placeholder and preserve section headings `§1` through `§9`.

Parser-critical details:

- §4 table has a column literally named `Path`;
- §5 table has a column literally named `Path`;
- §7 exact commands live in a `bash` fence;
- §9 acceptance items are normal markdown list/checklist bullets.

The optional `pr_body_template` frontmatter is only a transport pointer. Do not duplicate the handoff into the PR body.

Before dispatch, compare the §4 write lease with active PR/handoff lanes and run whatever collision preflight the Steward Cycle requires. The worker receives the checked-in handoff, exact base, branch/checkout identity, and relevant runtime/state ownership.

## 2. Fetch a PR for review

```bash
uv run python scripts/review_external_pr.py fetch <N> \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md \
  --extract-rubric
```

The command returns one structured payload containing PR/head metadata, changed files, allowlist/denylist checks, §7 commands, and optional §9 bullets.

Treat these fields as the pre-review gate:

| Field | Use |
|---|---|
| `pr` | exact title/head/merge state |
| `files[]` | changed-path inventory |
| `allowlist_check` | §4 lease drift (`extras` blocks normal review) |
| `denylist_check` | §5 collision/forbidden-path hints requiring judgment |
| `verification_commands[]` | exact §7 command set |
| `handoff.rubric_bullets[]` | optional §9 text for review drafting |

An empty parsed allowlist means the template/handoff shape was not understood; do not treat that as a pass.

## 3. Verify §7 independently

```bash
uv run python scripts/review_external_pr.py verify <N> \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md \
  --parse-counts
```

`verify` stashes local edits, checks out the PR head, runs the parsed §7 commands, restores the original branch, and pops the stash.

Review the result by provenance:

```text
author-local
independently rerun local
CI
manual/dogfood
operator waiver
```

A command list passing does not prove that §7 selected the correct owning boundary or adversarial sequence; that is reviewer judgment from the Steward Cycle.

If a required gate already fails on base, compare base/head and report the failure truthfully. Do not rename unchanged baseline failure as green.

## 4. Post Review Cycle N

A review cycle is counted by the foundational rule: one formal judgment against one distinct head SHA.

Preferred review-body file:

`/tmp/pr-<N>-cycle<C>-review.md`

```markdown
---
pr_number: <N>
verdict: approve         # or request_changes / comment
---

Review Cycle <C> — <disposition>

<invariant disposition, evidence, findings>

@comment <path>:<line>[:<side>]
<inline comment>
```

Post it:

```bash
uv run python scripts/review_external_pr.py post \
  --review-md /tmp/pr-<N>-cycle<C>-review.md
```

When the PR author and reviewer share the same GitHub identity, GitHub rejects self-`APPROVE` / self-`REQUEST_CHANGES`. The script falls back to `COMMENT` while preserving the verdict banner. That still counts as the formal review cycle when it is the steward's complete judgment against that head.

Inline comment lines must be changed lines in the PR diff.

### Re-review

After fixes:

1. fetch the new head;
2. review the finding-led delta;
3. rerun required evidence;
4. re-evaluate the complete invariant;
5. post the next formal review cycle against the changed head.

Do not count fix commits or evidence-only comments as cycles by themselves.

## 5. Capture review learning

The review itself is durable evidence. If the workstream has an explicit judgment/learning ledger (for example a PLAN `external_pull_requests[]` structure), update that ledger during the post-merge state-authority sync.

Do **not** invent a PLAN/checklist merely because this runbook historically expected one. The handoff §2 names the workstream's actual sync set.

At minimum, the completed handoff/state record should preserve:

```text
PR / merge revision
total review cycles
material finding classes
accepted evidence / waivers
named successor still false
```

Generalized lessons move to the appropriate upstream owner under the Steward Cycle learning rule.

## 6. Merge approved PR

```bash
uv run python scripts/review_external_pr.py merge <N>
```

The merge command handles the normal merge/fast-forward/local-overlap ceremony and returns structured data including merge commit, timestamp, PR URL/title, and local head after pull.

Useful properties:

- default merge strategy matches the repo's normal merge flow;
- branch deletion is on by default;
- dirty-tree overlap is stashed/restored when needed;
- an already-merged PR short-circuits to capture-state mode;
- a failed stash pop means the remote merge may already be complete—resolve local state without pretending the merge failed.

After merge, verify exact integration state (`git rev-parse HEAD`, `git show -s`, remote ref when relevant).

## 7. Execute atomic state-authority sync

Read the HANDOFF §2 field:

```text
State-authority sync set after merge
```

Update **that applicable set**, not a hardcoded PLAN/CHECKLIST trio.

Typical members may include:

```text
PLAN execution state / judgment ledger
CHECKLIST re-anchor/evidence
HANDOFF completion status/archive
ROADMAP phase/next slice
PR tracker
STATUS/current-state guide
active source/index manifest
```

Prefer one commit or one small sync PR. If tooling can only write files sequentially, treat the writes as one guarded transaction:

1. do not dispatch a dependent successor between partial writes;
2. update every intended authority;
3. re-read the complete set;
4. verify exact repository head;
5. only then declare the development cycle closed.

Stable architecture/contracts are not routine sync members unless their claims actually changed.

## 8. Re-anchor before the next dependent slice

Return to [`Docs/Process/STEWARD-CYCLE.md`](../../../Docs/Process/STEWARD-CYCLE.md):

- confirm merged behavior, not handoff promises;
- confirm state authorities agree;
- inspect active parallel lanes/write leases;
- carry forward repeated review lessons;
- decompose the next candidate again rather than chain-dispatching from the old plan.

## Quick command reference

| Command | Purpose | Mutates? |
|---|---|---|
| `fetch <N> --handoff <path> [--extract-rubric]` | PR metadata + lease/denylist + §7 commands | no |
| `verify <N> --handoff <path> [--parse-counts]` | checkout head, run §7, restore | local working tree temporarily |
| `post --review-md <path>` | formal review judgment/comments | GitHub |
| `merge <N>` | merge + refresh local integration state | GitHub + local repo |

## Mechanical failure cases

- **Handoff parser returns empty §4/§7:** inspect template structure; do not waive silently.
- **Interactive verification:** add a fixture or explicit manual proof rather than bypassing it.
- **GitHub API outage:** use the equivalent `gh`/web path, preserving exact head and review-cycle semantics.
- **Self-review 422:** preserve verdict through the script's COMMENT fallback.
- **Inline anchor rejected:** anchor only to changed lines.
- **Stash restore conflict:** remote merge/review state may still be valid; resolve local restore separately.
- **State-sync set unclear:** return to Steward Cycle/re-anchor; do not default blindly to old PLAN/CHECKLIST assumptions.

## References

- Durable law: `AGENTS.md`
- External PR invariants: `.cursor/rules/external-agent-pr-loop.mdc`
- Steward judgment/process: `Docs/Process/STEWARD-CYCLE.md`
- Re-anchor discipline: `.cursor/rules/anchor.mdc`
- Handoff template: `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`
- Review tooling: `scripts/review_external_pr.py`
