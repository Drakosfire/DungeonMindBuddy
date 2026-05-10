---
# Optional workflow contract: literal markdown the worker pastes into the
# GitHub PR description. Dispatcher fills once; reviewers and parallel
# agents see one stable shape without inferring sections from free-form §2 prose.
# Delete this whole frontmatter block if you prefer prose-only handoffs.
pr_body_template: |
  ## Summary
  {{TODO: one sentence — same as §1 Mission}}

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — {{TODO: one-line title — phase + slice, e.g. "Phase C entry: route-equivalence shadow consumer in `breadcrumb_query_run`"}}

**Created:** {{TODO: YYYY-MM-DD}} (UTC).
**Status:** ACTIVE — dispatch this to one external/Codex subagent. One PR. Do not split into multiple PRs.
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-<rollout>.md` and `Docs/Plans/PLAN-<plan>.md` per `.cursor/rules/external-agent-pr-loop.mdc`.
**Plan anchor:** `Docs/Plans/PLAN-<plan>.md` (`active_phase: <X>`, milestone progress {{TODO: e.g. M2 in_progress → M3 not_started}}). This handoff opens the {{TODO: M*}} lane.

---

## §1 Mission

{{TODO: ONE sentence stating the single change. Resist the urge to add a second sentence.}}

## §2 Why this slice (context for the subagent)

- {{TODO: prior PR(s) that produced the inputs this slice consumes; merge hashes for traceability}}
- {{TODO: what this slice converts from "produced" to "consumed", or otherwise advances}}
- {{TODO: explicitly: what this slice does NOT do (no retriever rewiring, no grading change, no new gold, etc.) — keeps scope honest}}

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract that this PR will be reviewed against.
2. {{TODO: anchor file (schema, contract, decision doc) — read-only here}}
3. {{TODO: canonical example file the worker should mirror (test layout, prompt shape, etc.)}}
4. {{TODO: registry / gold / fixture the worker must compare against}}
5. {{TODO: the harness / dispatcher / writer file the worker will edit, with line ranges if it's a large file}}
6. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired so live tests don't need exported keys (see `.cursor/rules/dungeonbuddy-environment.mdc`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| {{TODO: Create / Modify}} | `{{TODO: relative/path/to/file}}` | {{TODO: one-sentence purpose}} |
| {{TODO: …}} | `{{TODO: …}}` | {{TODO: …}} |

> The agent's expected `git diff --stat` MUST be expressible from this allowlist. If a path is not in this table, the worker will be told to revert it during review.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `{{TODO: tempting/path/the/worker/will/reach/for}}` | {{TODO: collision risk — e.g. "test_*.py basename already exists on main with different content; renaming would orphan it"; or "gold file for an unrelated benchmark; 'while you're in there' edits silently change rubric"; or "schema doc that the planner reads — moving lines reorders neighbors and changes prompt-cache keys"}} |
| `{{TODO: …}}` | {{TODO: …}} |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### {{TODO: New module 1}}

```python
{{TODO: function signatures, types, docstring shapes; no implementation}}
```

Determinism / ordering rules:
- {{TODO: e.g. preserve the writer's canonical sort `sorted(records, key=lambda r: r.record_id)`}}
- {{TODO: e.g. "do not mutate input records"}}

### {{TODO: New module 2 / harness wiring}}

{{TODO: where in the existing file the new code slots in (line ranges from §3 are useful here)}}

```python
{{TODO: argparse flag spec, emission slot, error-handling pattern}}
```

## §7 Verification commands

The worker must run **every** command and paste the output into the PR body. The reviewer reruns each. **Every behavioral guarantee in §9 below must be exercised by at least one command here, at the boundary the guarantee describes.**

```bash
# Sanity: existing surfaces still green.
uv run pytest tests/<owning-suite>/ -q

# New unit-level tests for the modules added in §6.
uv run pytest tests/<owning-suite>/test_<new>.py -q

# Boundary-level test for the §9 guarantees that live at the harness/dispatcher/writer layer.
uv run pytest tests/test_<harness-or-boundary>.py -q

# Smoke: actually invoke the new flag end-to-end and inspect the field shape.
uv run python -m <module> --<new-flag> ... | head -20
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to the §4 allowlist paths only.** Not the whole-tree stat (mixes in dispatcher's uncommitted work).
2. **Verbatim §7 output** — pass/fail counts, last 20 lines on failure.
3. **One-paragraph "what stayed unchanged"** — call out at least the legacy-path no-op invariants (e.g. "default runs without the new flag are byte-identical to current main").

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet is paired with the §7 command that verifies it.

- [ ] {{TODO: behavioral guarantee 1}} — verified by `{{TODO: §7 command name}}`.
- [ ] {{TODO: behavioral guarantee 2}} — verified by `{{TODO: §7 command name}}`.
- [ ] {{TODO: scope guarantee — "no files outside §4 are touched"}} — verified by `git diff --stat <base>...HEAD` filtered to §4.
- [ ] {{TODO: legacy-path no-op invariant — "default runs without the new flag are byte-identical to main"}} — verified by `{{TODO: harness-boundary command, NOT loader-level}}`.

> **Reviewer reminder:** if a bullet describes a behavioral guarantee at a particular boundary (harness, dispatcher, writer), the §7 command that verifies it MUST exercise it at that boundary. Loader-side or unit-side coverage is necessary but not sufficient.

## §10 Out-of-band notes (optional)

- {{TODO: e.g. "this slice intentionally does not touch the canvas payload — Phase 4 work" — keeps reviewers from asking}}
- {{TODO: e.g. "if the worker hits a sandbox issue with `gh pr create`, post the PR-body markdown back to the dispatcher and the dispatcher will open the PR by hand"}}
