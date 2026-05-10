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

### Handoff filenames carry the planned PR number

Handoff documents under `Docs/Plans/` use the form `HANDOFF-pr<N>-<short-slug>.md` (e.g. `HANDOFF-pr6-cohort-baseline-runner-c1s1-to-c1s3.md`). Resolve `<N>` at authoring time from the PLAN's PR-anchor table or `gh pr list --state all --limit 5 --json number --jq '.[].number' | sort -n | tail -1` plus one. The prefix makes it cheap to find a handoff from a PR number and vice versa, and keeps the post-merge archive self-describing without renaming. If `<N>` is genuinely unknowable at authoring time (rare — usually means two slices are being authored in parallel before either PR opens), omit the prefix and rename at archive time as part of the post-merge doc-sync.

The convention applies to **active** handoffs going forward; older handoffs in `Docs/Plans/archive/<date>/handoffs/` are not retroactively renamed. New handoffs that land in those archive folders post-merge SHOULD already carry the prefix from authoring time.
