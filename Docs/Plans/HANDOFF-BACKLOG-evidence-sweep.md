# Backlog evidence reconciliation

ACTIVE — operator requested the backlog sweep after #3763 merged; root adopted a bounded status/pointer split on 2026-11-17. No runtime work, merge or deployment authority.

Base: `28f4cab85a6a7eebabc4e89ce24166b86e198380`. Branch: `codex/backlog-evidence-sweep-20261117`. Isolated checkout: `~/Projects/backlog-evidence-sweep-20261117`.

Expected writes: this handoff, `Backlog.md`, `Docs/Backlog/IDEA-conversation-search-replay.md`, `Docs/Backlog/IDEA-aw-workflow-capabilities.md`, and `Docs/Roadmaps/ROADMAP-demo.md`.

Serial documentation reconciliation. All 69 open PR heads were checked. Narrow split preserves #2087/#2090 campaign-membership content, #2406 owner-role language and #3683 unmerged design input. Do not merge, close, adopt or rewrite those PRs. The overlap is status/pointers only, not their proposed implementation/design contracts. Maintenance remains untouched; the parallel audit reports all 21 issue-backed items open. #410 and #783 were independently checked open. No issue closure inferred from code merges.

Verification: review exact cumulative diff, citations, local links and anchors; exact-head hosted verifier under the global lock; independent root review before calling the result verified. Retain inherited failures as red. One draft PR only; no apps/tests, Gold, data, runtime or service writes. Preserve roadmap priorities/history and distinguish merged mechanisms, scripted controls, ordinary local witnesses and hosted acceptance.
