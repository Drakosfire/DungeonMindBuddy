---
name: external-agent-pr-loop
description: >-
  Run the four-stage external-agent PR loop in DungeonMindBuddy: write a
  HANDOFF, review/verify/comment-on the resulting PR via
  `scripts/review_external_pr.py`, capture a YAML judgment record under
  `external_pull_requests[]` in the relevant PLAN doc, and atomically sync
  plan + checklist + handoff after merge. Use when authoring a
  `Docs/Plans/HANDOFF-*.md` for a Codex-style branch agent, when a GitHub PR
  opens that was authored by such an agent, when posting a verdict
  (`APPROVE` / `REQUEST_CHANGES` / `COMMENT`) on that PR, or when performing
  the post-merge doc-sync. The non-negotiable invariants live in
  `.cursor/rules/external-agent-pr-loop.mdc`; this skill is the runbook.
---

# External-agent PR loop — runbook

This is *how* to run each stage in the smallest possible token budget. The
non-negotiable invariants (must-include §4 allowlist, "test the boundary that
owns the rubric", atomic doc-sync, rubric-as-learning-surface) live in
`.cursor/rules/external-agent-pr-loop.mdc`. Read that rule once for the
contract; come back here for the procedure.

For **in-IDE** subagents (the parent agent dispatches a `Task` and reads its
output), follow `.cursor/rules/subagent-delegation.mdc` instead.

## The loop

```
HANDOFF write  →  external PR opens  →  judgment record  →  doc sync (atomic)
   (parent)         (external agent)        (parent)            (parent)
```

The cycle does **not** end at "merged green" — it ends when plan YAML,
checklist, and handoff status all match `main`.

---

## Stage 1 — Author the HANDOFF

1. Copy `templates/HANDOFF.template.md` from this skill folder to
   `Docs/Plans/HANDOFF-<slug>.md`.
2. Fill every `{{TODO: …}}` slot. Do **not** delete a section; the worker and
   the reviewer scripts both expect §1–§9.
3. Run the **collision-risk pre-flight** before sending:

   ```bash
   rg -l "test_<basename>" tests/ || true
   rg -l "<feature>_v1" evals/ artifacts/ || true
   ```

   If anything matches, name the conflict in §5 explicitly. The agent cannot
   see your WIP branches or other open PRs.

### Rubric ↔ verification pairing (the round-1 trap)

For every §9 rubric bullet that asserts a behavioral guarantee (e.g. "byte-
identical when flag X is unset", "error payload on load fail, never raises"),
§7 MUST include a command that exercises that guarantee at the boundary the
rubric describes (harness, dispatcher, writer — whichever owns the contract).
Loader-side or unit-side coverage is necessary but not sufficient.

This trap is exactly what cost PR #4 a round of rework: §9 named two harness-
boundary safety properties, §7 only covered them at the loader boundary, the
worker built faithfully to the lower bar, and the harness `try/except` arm went
untested. Round 2 added the missing harness tests.

---

## Stage 2 — Review the PR

`scripts/review_external_pr.py` consolidates the manual `gh + git + sed` dance.
Three idempotent subcommands, all read-only by default; only `verify` mutates
the working tree (auto-stash + checkout + restore) and only `post` writes to
GitHub.

### 2a. Fetch + check allowlist / denylist / §7 commands

```bash
uv run python scripts/review_external_pr.py fetch <N> \
  --handoff Docs/Plans/HANDOFF-<slug>.md
```

Returns one JSON blob:

| Field | Use |
|---|---|
| `pr` | title, head sha, mergeable status |
| `files[]` | per-file additions/deletions |
| `allowlist_check {status, expected, extras, missing}` | `status: pass` ⇒ proceed; `extras` ⇒ scope creep, push back; empty `expected` ⇒ parser couldn't read the handoff (markdown-table heuristic keyed on a column literally named `Path`), do manual review |
| `denylist_check {status, hits}` | `hits` need a human pass — §5 prose sometimes carves out exceptions a glob can't see |
| `verification_commands[]` | extracted from §7 |

### 2b. Verify §7 yourself

```bash
uv run python scripts/review_external_pr.py verify <N> \
  --handoff Docs/Plans/HANDOFF-<slug>.md
```

Auto-stashes the working tree, checks out the PR head, runs every §7 command,
restores `main`, pops the stash. Returns
`{passed, head_sha, results: [{command, exit_code, tail}]}`.

Never trust the PR description's "all green" — sandbox / runner differences
and silent skips happen.

### 2c. Post the verdict

Write the review as a markdown file (preferred — no shell escaping, no Python
wrappers):

`/tmp/pr-<N>-round<R>-review.md`:

```markdown
---
pr_number: <N>
verdict: approve         # or request_changes / comment
---

<review body — anything before the first @comment marker.
Multi-line, backticks, code fences, headings — all native markdown.>

@comment <path>:<line>[:<side>]
<inline-comment markdown until the next @comment or EOF>

@comment <path>:<line>
<another inline comment — side defaults to RIGHT (the new file)>
```

Then:

```bash
uv run python scripts/review_external_pr.py post \
  --review-md /tmp/pr-<N>-round<R>-review.md
```

**Self-review 422.** If you opened the PR and you are reviewing it (common on
this repo — parent and Codex worker often share an account), GitHub blocks
`REQUEST_CHANGES` and `APPROVE`. The script automatically falls back to
`event: COMMENT` and prepends a verdict banner to the body. The verdict
*signal* is preserved; the merge button just doesn't get auto-greened.

**Inline-comment anchoring.** `<line>` must be a line that appears as
**added or modified** in the PR's "Files changed" view, not a context line.
GitHub returns 422 with no useful message otherwise. `<side>` defaults to
`RIGHT` (the new file).

---

## Stage 3 — Capture the judgment record

After accepting / closing the PR, prepend (or update) an entry under
`external_pull_requests[]` in the relevant `Docs/Plans/PLAN-*.md`. Use
`templates/external_pr_yaml.template` as the skeleton.

**Two non-negotiable properties:**

1. **The rubric is a learning surface.** Every supersession MUST add a bullet
   under `rubric_when_we_judge`. Every accepted PR SHOULD leave the rubric
   tightened — same bullets two PRs in a row is a smell.
2. **Stale-note discipline.** Notes that describe what the PR *did* age well.
   Notes that describe what is *still pending* age badly. Re-verify any
   temporal claim in `judgment_record.notes` before quoting it elsewhere.

---

## Stage 4 — Merge + atomic doc-sync (one batch)

After the verdict is APPROVE, the **next single unit of work** runs the
merge ceremony AND updates plan + checklist + handoff. **Do it as one edit
batch.** Splitting across turns leaves a contradictory-state window where a
fresh agent reads "pending" while `main` already has the change.

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

The subcommand pre-checks dirty-tree overlap (which PR-touched files
intersect `git status --porcelain`), stashes only when overlap exists, runs
`git pull --ff-only`, and pops afterward — replacing the 9-call
`gh + git + sed` ceremony.

Defaults that match this repo:
- `--strategy merge` (matches PR #2/#3/#4 merge-commit shape; override for
  squash/rebase).
- `--delete-branch` is on; pass `--no-delete-branch` to keep the head ref.
- Refuses to merge unless `mergeStateStatus == CLEAN`; pass `--force` to
  override (rebase-required, branch-protection-blocked, etc.).

**Idempotent.** If the PR is already merged (you re-run after a partial
sync), the subcommand short-circuits to capture-state mode and emits the
same JSON without touching GitHub or the local tree. Useful when the
post-merge `git pull` failed and you need to recover the merge data without
re-merging.

**When pop conflicts.** If `stash_pop_clean: false` in the output, the
command exits 1 and leaves the conflict for you to resolve manually
(`git status` to see, `git stash drop` after fixing). The merge itself is
already done on `origin/main` — only the local working-tree restore failed.

### 4b. Doc-sync edits (same turn as 4a)

With `merge_commit` and `merged_at` from 4a's JSON output, update ALL of
the following in one edit batch:

#### Plan (`Docs/Plans/PLAN-*.md`)

- Frontmatter: bump `version`, set `last_updated_at` to UTC now.
- `changelog`: prepend a one-liner referencing the merge commit short hash.
- `execution_state`: `next_gate_command`, `integration_notes` (full merge
  hash), `flagged_followups`, `milestone_progress`.
- `external_pull_requests[]`: prepend the new entry from Stage 3 (use
  `templates/external_pr_yaml.template`).
- *Current state snapshot* prose, *Primary files* for the affected phase,
  *workstream checklist* checkboxes.

#### Checklist (`Docs/Plans/CHECKLIST-*.md`)

- *Reanchor block*: `Last green artifact (path)`, `Current blocking red gate`,
  `Next command to run`.
- *Phase Evidence*: file list, test counts, command outputs from §7.
- *Session log*: prepend a new entry. Use
  `templates/session_log.template`.

#### Handoff

- One-line completion banner at top with merge hash + round commits +
  key follow-ups.
- Move file to `Docs/Plans/archive/<YYYY-MM-DD>/handoffs/`.
- Update that date's archive `README.md` `handoffs/` row.

---

## Quick reference

### Subcommand cheat sheet

| Command | Purpose | Mutates? |
|---|---|---|
| `fetch <N> --handoff <path>` | PR metadata + allowlist + denylist + §7 commands | no |
| `verify <N> --handoff <path>` | Stash, checkout, run §7, restore | yes (auto-restored) |
| `post --review-md <path>` | Post review with inline comments | yes (GitHub) |
| `merge <N>` | Merge, ff local main, auto-stash overlap, emit doc-sync data | yes (GitHub + local tree) |

### Common pitfalls

- ❌ Briefing without §4 allowlist or §7 verification.
- ❌ Silently expanding scope in review for a "tiny adjacent fix" — revert,
  re-brief.
- ❌ Accepting a green PR description without rerunning §7 yourself.
- ❌ Treating "merged" as the end of the cycle — the next agent reads stale
  docs.
- ❌ Reusing a `judgment_record.notes` block weeks later without re-verifying
  its temporal claims.
- ❌ Identical `rubric_when_we_judge` two PRs in a row after a supersession —
  supersessions teach the rubric.
- ❌ Reproducing the manual `gh + git + sed` dance instead of using
  `scripts/review_external_pr.py`.
- ❌ Writing a one-shot Python wrapper to JSON-encode review bodies (use
  `--review-md`).
- ❌ Building inline-comment payloads in shell with backticked code blocks
  (heredoc / `cat <<EOF`) — the shell tries to interpret backticks as
  command substitution.
- ❌ Hand-anchoring inline comments to context lines (anchor to additions /
  modifications only).
- ❌ Writing a §9 rubric bullet for a behavioral guarantee without naming the
  §7 command that tests it at the right boundary.

### When the scripts can't help

- Handoff structure diverges from §1–§9 — `fetch` will produce empty
  allowlists; do manual review.
- GitHub API outage — fall back to `gh pr review` interactive or the web UI.
- A §7 command needs interactive input (GUI test, browser launch) — add a
  fixture or mark `xfail`; do not bypass.

---

## References

- Contract / invariants: `.cursor/rules/external-agent-pr-loop.mdc`
- Sibling rules: `subagent-delegation.mdc`, `two-model-workflow.mdc`,
  `dungeonbuddy-git-workflow.mdc`
- Templates (this skill folder):
  - `templates/HANDOFF.template.md`
  - `templates/external_pr_yaml.template`
  - `templates/session_log.template`
- Canonical handoff (PR #3): `Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-phase-b-route-equivalence-artifact-output.md`
- Canonical handoff with the boundary-test rubric (PR #4): `Docs/Plans/archive/2026-05-10/handoffs/HANDOFF-phase-c-route-equivalence-shadow-consumer.md`
- Plan with `external_pull_requests[]`: `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`
- Checklist with Reanchor + Session log: `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`
- Cross-project learning: `~/.cursor/learnings/Backlog.md` — `[READY] External-agent PR loop`.
