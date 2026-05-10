# Agent operating policy

## Token-efficient repo navigation

Use SymDex before broad file reads. Prefer symbol search, route search, file outlines, call graphs, literal text search, semantic search, and token-budgeted context packs before reading full files.

Use RTK for noisy shell commands such as git status, git diff, git log, grep, find, tests, docker logs, and build output.

Do not dump large files, logs, generated files, dependency trees, or vendored code into context unless explicitly needed.

Correctness overrides token savings. Preserve failed tests, stack traces, compiler errors, migration warnings, security findings, and destructive-command risks.

Never run destructive commands without explicit user approval.

## External-agent PR loop

When work lands via a GitHub PR opened by a Codex-style external agent (HANDOFF write → external PR → judgment record → atomic doc-sync), the procedure / runbook is `.cursor/skills/external-agent-pr-loop/SKILL.md` (read on demand). The non-negotiable invariants are in `.cursor/rules/external-agent-pr-loop.mdc` (always-on). Use `scripts/review_external_pr.py {fetch | verify | post}` for the review loop — manual `gh + git + sed` is the anti-pattern.
