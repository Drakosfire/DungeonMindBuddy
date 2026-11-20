# Backlog evidence reconciliation

ACTIVE — operator requested the backlog sweep after #3763 merged; root adopted a bounded status/pointer split on 2026-11-17. No runtime work, merge or deployment authority.

Original base: `28f4cab85a6a7eebabc4e89ce24166b86e198380`. Re-anchored on 2026-11-18 to Buddy main `e0ad49c18fa922bf415438d18729b988c23fb92d` and reconciled through main `b4ec5408180d74b8ef0a9cc9543271df6e5fb02c`. The user explicitly authorized updating both #3854 and #3683 while preserving their scopes. #3854 is the parent; #3683 is the stacked design-input successor, reviewed and merged after #3854. Branch: `codex/backlog-evidence-sweep-20261117`. Isolated checkout: `~/Projects/backlog-evidence-sweep-20261117`.

Expected writes: this handoff, `Backlog.md`, `Docs/Backlog/IDEA-conversation-search-replay.md`, `Docs/Backlog/IDEA-aw-workflow-capabilities.md`, and `Docs/Roadmaps/ROADMAP-demo.md`.

Serial documentation reconciliation. The original audit checked 69 open PR heads. Preserve #2087/#2090 campaign-membership content and #3683 design input; #2406 has since merged. The user now explicitly authorizes updating #3683 as the stacked successor; do not merge or close either draft without separate merge authority. The overlap is status/pointers only, not their proposed implementation/design contracts. Maintenance remains untouched by this PR; merged #4012 independently reconciled closed issue dispositions. The prior 21-item audit was a dated snapshot. #410 and #783 were independently checked open. No issue closure inferred from code merges.

Verification: review exact cumulative diff, citations, local links and anchors; exact-head hosted verifier under the global lock; independent root review before calling the result verified. Retain inherited failures as red. One draft PR only; no apps/tests, Gold, data, runtime or service writes. Preserve roadmap priorities/history and distinguish merged mechanisms, scripted controls, ordinary local witnesses and hosted acceptance.
