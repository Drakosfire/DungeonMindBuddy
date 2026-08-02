---
name: external-agent-pr-loop
description: >-
  Run the four-stage external-agent PR loop in DungeonMindBuddy: write a
  HANDOFF, review/verify/comment-on the resulting PR via
  `scripts/review_external_pr.py`, capture a YAML judgment record under
  `external_pull_requests[]` in the relevant PLAN doc, and atomically sync
  plan + checklist + handoff after merge via an in-IDE doc-sync subagent by
  default. Use when authoring a
  `Docs/Plans/HANDOFF-*.md` for a Codex-style branch agent, when a GitHub PR
  opens that was authored by such an agent, when posting a verdict
  (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`) on that PR, or when performing
  the post-merge doc-sync. The non-negotiable invariants live in
  `.cursor/rules/external-agent-pr-loop.mdc`; this skill is the runbook.
---

# External-agent PR loop — runbook

This is *how* to run each stage in the smallest possible token budget. The
non-negotiable invariants — critique before dispatch, one merge-ready invariant,
a truthful PR evidence ledger, §4 allowlist, owning-boundary/sequence proof,
atomic doc-sync, and rubric-as-learning-surface — live in
`.cursor/rules/external-agent-pr-loop.mdc`. Read that rule once for the contract;
come back here for the procedure.

For **in-IDE** subagents (the parent agent dispatches a `Task` and reads its
output), follow `.cursor/rules/subagent-delegation.mdc` instead. In this
runbook, Stage 4 explicitly *requires* in-IDE subagent delegation for doc-sync
unless a hard blocker makes delegation impossible.

## The loop

```text
conversation + flow identity
  → invariant + evidence critique
  → DESIGN → CODE HANDOFF write
  → external PR opens with code diff
  → judgment record
  → separate doc sync (atomic)
```

The cycle does **not** end at "merged green" — it ends when plan YAML,
checklist, handoff status, learned invariant, and evidence requirements all
match `main`.

---

## Stage 1 — Critique and author the HANDOFF

> **Re-anchor first.** A HANDOFF is downstream of the workstream-scope
> re-anchor (CHECKLIST Reanchor block + PLAN frontmatter +
> `external_pull_requests[]` most-recent entry). Read
> `.cursor/rules/anchor.mdc` (on-demand) before drafting if you have not
> already verified `Last green artifact (path)` and `next_gate_command` are
> current — the slice you are about to brief depends on both.

Filename convention: name the file
`Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md`, where `<FLOW>` is exactly one of
`BUILD`, `STATBLOCK`, `TIMELINE`, or `DOCUMENTS`. The PR title uses
`<FLOW>: <short capability>`. Do not wait for or encode a PR number; a GitHub
PR URL or number is optional transport metadata after the PR opens.

1. Copy `templates/HANDOFF.template.md` from this skill folder to
   `Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md`.
2. Fill every `{{TODO: …}}` slot. Do **not** delete a section; the worker and
   reviewer scripts both expect §1–§9.
3. Complete the §1 pre-dispatch critique before implementation launches:
   - can one invariant govern every claimed observable path;
   - what adversarial sequence is most likely to falsify it;
   - would the proposed §7 evidence actually detect that failure;
   - what fact forces a split or stop.
4. Keep the YAML `pr_body_template` frontmatter as a minimal transport pointer.
   The checked-in HANDOFF, cumulative code diff, nano commits, and verification
   output are authoritative. Do not spend design or code-agent effort
   maintaining a narrative PR description. `review_external_pr.py` does not
   treat the body as proof.
5. Run the **collision-risk pre-flight** before sending:

   ```bash
   rg -l "test_<basename>" tests/ || true
   rg -l "<feature>_v1" evals/ artifacts/ || true
   ```

   If anything matches, name the conflict in §5 explicitly. The agent cannot
   see your WIP branches or other open PRs.

### Invariant ↔ evidence pairing

For every §9 rubric bullet that asserts a behavioral guarantee, §7 MUST name:

- the owning boundary;
- the evidence class;
- the command or scenario;
- the expected observation;
- the result that blocks merge.

For stateful, concurrent, cross-surface, navigation, or partially durable work,
§3 must enumerate the ordered failure sequence and §7 must exercise it. A helper
unit test cannot prove a workflow invariant.

Two fix-loop lessons anchor this rule:

- PR #4 named harness-boundary safety properties but tested only the loader.
- PR #399 initially tested individual authoring pieces while missing
  post-commit interleavings, surface-to-agent leakage, editor hydration/first
  transaction behavior, and parent update re-entry.

---

## Stage 2 — Review the PR

`scripts/review_external_pr.py` consolidates the manual `gh + git + sed` dance.
Three idempotent subcommands, all read-only by default; only `verify` mutates
the working tree (auto-stash + checkout + restore) and only `post` writes to
GitHub.

Before reading implementation details, establish the exact PR/branch/head SHA
and the corresponding checked-in HANDOFF. Then inspect the cumulative diff and
nano-commit sequence. Do not use the PR description as evidence or authority.
The reviewer may require as many discrete, specific fixes and re-review rounds
as necessary to move the invariant to merge. Each finding must state the
failure or missing proof, affected path, owning boundary, and concrete fix
required to close it.

### 2a. Fetch + check allowlist / denylist / §7 commands

```bash
uv run python scripts/review_external_pr.py fetch <N> \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md \
  --extract-rubric
```

`--extract-rubric` is optional; it adds `handoff.rubric_bullets[]` (§9 list
lines) so you can draft verdicts and PLAN YAML without re-opening the handoff
for rubric copy/paste.

Here `<N>` is only the GitHub API lookup identifier; it is not part of the
handoff filename or naming convention.

Returns one JSON blob:

| Field | Use |
|---|---|
| `pr` | title, head sha, mergeable status |
| `files[]` | per-file additions/deletions |
| `allowlist_check {status, expected, extras, missing}` | `status: pass` ⇒ proceed; `extras` ⇒ scope creep, push back; empty `expected` ⇒ parser couldn't read the handoff (markdown-table heuristic keyed on a column literally named `Path`), do manual review |
| `denylist_check {status, hits}` | `hits` need a human pass — §5 prose sometimes carves out exceptions a glob can't see |
| `verification_commands[]` | extracted from §7 |
| `handoff.rubric_bullets[]` | when `--extract-rubric`: §9 `-` / `- [ ]` lines (blockquote lines skipped) |

### 2b. Verify §7 yourself

```bash
uv run python scripts/review_external_pr.py verify <N> \
  --handoff Docs/Plans/HANDOFF-<FLOW>-<short-slug>.md \
  --parse-counts
```

`--parse-counts` is optional; each `results[]` entry then includes
`passed_count` (integer) or `null` when the captured tail has no pytest-style
`N passed` summary (raise `--tail` if you see too many `null`s).

Auto-stashes the working tree, checks out the PR head, runs every §7 command,
restores `main`, pops the stash. Returns
`{passed, head_sha, results: [{command, exit_code, tail, passed_count?}]}`.

Never trust the PR description's "all green" — sandbox / runner differences
and silent skips happen. Treat the handoff's `verification_commands[]` as
authoritative for command count; prose counts often drift.

After commands pass, review the adversarial sequences manually. A green command
list does not prove that §7 selected the right sequence or owning boundary.

### 2c. Post the verdict

Write the review as a markdown file (preferred — no shell escaping, no Python
wrappers):

`/tmp/pr-<N>-round<R>-review.md`:

```markdown
---
pr_number: <N>
verdict: approve         # or request_changes / comment
---

<review body — begin with invariant disposition and evidence gaps.>

@comment <path>:<line>[:<side>]
<inline-comment markdown until the next @comment or EOF>

@comment <path>:<line>
<another inline comment — side defaults to RIGHT>
```

Then:

```bash
uv run python scripts/review_external_pr.py post \
  --review-md /tmp/pr-<N>-round<R>-review.md
```

**Self-review 422.** If you opened the PR and you are reviewing it, GitHub blocks
`REQUEST_CHANGES` and `APPROVE`. The script automatically falls back to
`event: COMMENT` and prepends a verdict banner. The verdict signal is preserved.

**Inline-comment anchoring.** `<line>` must be an added or modified line in the
PR's Files changed view, not a context line. `<side>` defaults to `RIGHT`.

### 2d. Re-review after fixes

Review only the new delta first, then re-evaluate the complete merge-ready
invariant and evidence ledger. A patch closes a finding only when it eliminates
the failure sequence rather than moving it elsewhere. New adversarial sequences
become new §7 requirements and judgment-record learning.

---

## Stage 3 — Capture the judgment record

After accepting / closing the PR, prepend or update an entry under
`external_pull_requests[]` in the relevant `Docs/Plans/PLAN-*.md`. Use
`templates/external_pr_yaml.template` as the skeleton.

Record:

- the invariant judged;
- evidence that proved it;
- missing evidence or waivers;
- fix-loop lessons added to `rubric_when_we_judge`.

**Two non-negotiable properties:**

1. **The rubric is a learning surface.** Every supersession MUST add a bullet
   under `rubric_when_we_judge`. Every accepted PR SHOULD leave the rubric
   tightened — same bullets two PRs in a row is a smell.
2. **Stale-note discipline.** Notes that describe what the PR did age well.
   Notes that describe what is still pending age badly. Re-verify temporal
   claims before quoting them elsewhere.

---

## Stage 4 — Merge + atomic doc-sync (one batch)

After the verdict is APPROVE, the **next single unit of work** runs the merge
ceremony AND updates plan + checklist + handoff. Do it as one edit batch.
Splitting across turns leaves a contradictory-state window.

### 4.0 Delegation policy (mandatory)

For token economy, Stage 4b doc-sync is **subagent-first**:

- Dispatch an in-IDE execution subagent for doc-sync edits.
- Prefer auto/background execution when the task can proceed unattended.
- The parent remains accountable for reviewing the diff and checks.
- Skip delegation only for a concrete tooling, permission, or judgment blocker;
  record the reason.

> The doc-sync edit list below is the workstream-scope re-anchor act. Read
> `.cursor/rules/anchor.mdc` when canonical-source or scope questions arise.

After local `main` updates post-merge, confirm the integration tip with
`git rev-parse HEAD` / `git show -s`.

### 4a. Merge ceremony — one subcommand

```bash
uv run python scripts/review_external_pr.py merge <N>
```

Returns JSON with the data the post-merge atomic doc-sync needs:

```json
{
  "pr": 4,
  "merge_commit": "21e84392da03095377b4de36defb82edfc37c741",
  "merged_at": "2026-05-10T16:22:43Z",
  "url": "https://github.com/Drakosfire/DungeonMindBuddy/pull/4",
  "title": "Phase C entry: …",
  "merge_strategy": "merge",
  "ff_pull_ok": true,
  "overlap_files": ["evals/.../README.md"],
  "stashed": true,
  "stash_pop_clean": true,
  "head_after_pull": "21e84392…"
}
```

The subcommand pre-checks dirty-tree overlap, stashes only when overlap exists,
runs `git pull --ff-only`, and pops afterward.

Defaults that match this repo:

- `--strategy merge`; override for squash/rebase.
- `--delete-branch` is on; use `--no-delete-branch` to keep the head ref.
- Refuses to merge unless `mergeStateStatus == CLEAN`; `--force` is explicit.

**Idempotent.** If the PR is already merged, the command short-circuits to
capture-state mode and emits the same JSON without touching GitHub.

**When pop conflicts.** If `stash_pop_clean: false`, the merge already happened
on `origin/main`; resolve the local restore manually.

### 4b. Doc-sync edits (same turn as 4a)

With `merge_commit` and `merged_at` from 4a, update all of the following in one
edit batch.

#### Plan (`Docs/Plans/PLAN-*.md`)

- Frontmatter: bump `version`, set `last_updated_at`.
- `changelog`: prepend a merge line.
- `execution_state`: next gate, integration notes, follow-ups, progress.
- `external_pull_requests[]`: prepend/update the Stage 3 entry.
- Current-state prose, primary files, and checklist state.
- Carry forward the accepted invariant and newly learned evidence requirements.

#### Checklist (`Docs/Plans/CHECKLIST-*.md`)

- Reanchor block: last green artifact, open decision artifact, next command.
- Phase Evidence: file list, command results, adversarial/manual proof.
- Session log: prepend a new entry using `templates/session_log.template`.

#### Handoff

- Completion banner with merge hash, review rounds, and follow-ups.
- Move to `Docs/Plans/archive/<YYYY-MM-DD>/handoffs/`.
- Update that archive's `README.md`.

---

## Quick reference

### Subcommand cheat sheet

| Command | Purpose | Mutates? |
|---|---|---|
| `fetch <N> --handoff <path> [--extract-rubric]` | PR metadata + allowlist + denylist + §7 commands (+ optional §9 bullets) | no |
| `verify <N> --handoff <path> [--parse-counts]` | Stash, checkout, run §7, restore | yes (auto-restored) |
| `post --review-md <path>` | Post review with inline comments | yes (GitHub) |
| `merge <N>` | Merge, ff local main, auto-stash overlap, emit doc-sync data | yes (GitHub + local tree) |

### Common pitfalls

- ❌ Dispatching before the invariant and required evidence survive critique.
- ❌ Briefing without §4 allowlist or §7 verification.
- ❌ Deleting the expected `pr_body_template` transport pointer or treating a generic PR body as review evidence.
- ❌ Silently expanding scope in review for a “tiny adjacent fix.”
- ❌ Accepting a green PR description without rerunning §7.
- ❌ Testing only a helper when the guarantee lives in a workflow or ordered sequence.
- ❌ Treating merged as the end of the cycle.
- ❌ Doing Stage 4b in the strong parent model when a subagent can do it.
- ❌ Reusing stale judgment notes without verification.
- ❌ Identical `rubric_when_we_judge` after a supersession.
- ❌ Reproducing the manual `gh + git + sed` dance.
- ❌ Writing one-shot JSON wrappers for review bodies; use `--review-md`.
- ❌ Anchoring inline comments to context lines.
- ❌ Writing a §9 behavioral claim without owning-boundary and adversarial proof.

### When the scripts can't help

- Handoff structure diverges from §1–§9 — `fetch` may produce empty allowlists;
  do manual review.
- PR-body invariant/evidence comparison is manual until tooling parses it.
- GitHub API outage — fall back to `gh pr review` or the web UI.
- A §7 command needs interactive input — add a fixture or record a manual proof;
  do not silently bypass it.

---

## References

- Contract / invariants: `.cursor/rules/external-agent-pr-loop.mdc`
- Merge contract design: `Docs/Design/DESIGN-merge-ready-invariant-evidence.md`
- Re-anchor act: `.cursor/rules/anchor.mdc`
- Sibling rules: `subagent-delegation.mdc`, `dungeonbuddy-git-workflow.mdc`
- Templates:
  - `templates/HANDOFF.template.md`
  - `templates/external_pr_yaml.template`
  - `templates/session_log.template`
- Canonical handoffs: `Docs/Plans/archive/2026-05-10/handoffs/`
- Plan example: `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`
- Checklist example: `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`
- Cross-project learning: `~/.cursor/learnings/Backlog.md` — `[READY] External-agent PR loop`.
