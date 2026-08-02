# Agent operating policy

## Token-efficient repo navigation

Use SymDex before broad file reads. Prefer symbol search, route search, file outlines, call graphs, literal text search, semantic search, and token-budgeted context packs before reading full files.

Use RTK for noisy shell commands such as git status, git diff, git log, grep, find, tests, docker logs, and build output.

### Git history and merge commits

After merges, prefer `git rev-parse HEAD` and `git show -s --format=… HEAD` over treating `git log --oneline` as the whole truth when the environment may omit merge commits (a short log can show the PR branch tip while `HEAD` is the merge commit).

Do not dump large files, logs, generated files, dependency trees, or vendored code into context unless explicitly needed.

Correctness overrides token savings. Preserve failed tests, stack traces, compiler errors, migration warnings, security findings, and destructive-command risks.

Never run destructive commands without explicit user approval.

## External-agent PR loop

When work lands via a GitHub PR opened by a Codex-style external agent (HANDOFF write → external PR → judgment record → atomic doc-sync), the procedure / runbook is `.cursor/skills/external-agent-pr-loop/SKILL.md` (read on demand). The non-negotiable invariants are in `.cursor/rules/external-agent-pr-loop.mdc` (always-on). Use `scripts/review_external_pr.py {fetch | verify | post}` for the review loop — manual `gh + git + sed` is the anti-pattern.

### Handoff and PR naming follows the operating flow

Handoff documents under `Docs/Plans/` use the form
`HANDOFF-<FLOW>-<short-slug>.md`, where `<FLOW>` is exactly one of
`BUILD`, `STATBLOCK`, `TIMELINE`, or `DOCUMENTS`. For example:
`HANDOFF-DOCUMENTS-design-agent-source-set-sync.md`.

PR titles use the same flow identifier:

```text
<FLOW>: <short capability>
```

Examples: `BUILD: persist surface lease`,
`STATBLOCK: validate draft mechanics`, `TIMELINE: append recap event`, and
`DOCUMENTS: sync design-agent sources`.

PR numbers are optional GitHub transport metadata. They are not part of the
handoff filename, branch name, PR title, or design authority. Existing
`HANDOFF-pr<N>-…` files remain historical names and are not retroactively
renamed.
