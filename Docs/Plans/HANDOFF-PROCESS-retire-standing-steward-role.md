# HANDOFF-PROCESS-retire-standing-steward-role

**Status:** ACTIVE, documentation design/policy slice
**Base:** `ec646dab173deb1ddc6075226a496b400afc8eb5` (DungeonMindBuddy `main`, verified 2026-11-11)
**Branch:** `codex/retire-standing-steward-role`
**Owner:** explicitly assigned documentation/policy slice owner
**Topology:** serial; no PR creation or external publication in this task

## Mission

Remove the standing Steward authority layer from current Buddy instructions and pickup guidance. Make responsibilities derive from the bounded assignment: identify the explicitly assigned owner/designer/reviewer for the task, preserve independent review, and do not imply a default person/agent. This wording grants no additional merge, runtime, provider, or model authority. Preserve all permission gates and scope limits.

## Expected paths

Canonical files, edited before their exports:

- `Docs/Plans/HANDOFF-PROCESS-retire-standing-steward-role.md` (this pinned design authority)
- `AGENTS.md`
- `Docs/Process/STEWARD-CYCLE.md`
- `.cursor/rules/anchor.mdc`
- `.cursor/rules/dungeonbuddy-git-workflow.mdc`
- `.cursor/rules/external-agent-pr-loop.mdc`
- `.cursor/skills/external-agent-pr-loop/SKILL.md`
- `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`
- `Docs/Plans/README.md`
- `Backlog.md` (current DEMO destination label only)
- `Docs/Plans/ANCHOR-dungeonmind-net-platform-refresh.md` (continuing owner/process instructions only)
- `Docs/Plans/STEWARDS-ANCHOR-application-state.md` (current pickup/owner instructions only; preserve statuses and history)
- `Docs/Plans/JUMPSTART-docs-relevance-first.md` (superseded pointer only)
- `Docs/Plans/PLAN-CON-READY-PLAY-dogfood-thread-v1.md`
- `Docs/Plans/PLAN-CON-READY-authoring-v2-derived-gold-ablation-loop-v1.md`
- `Docs/Plans/PR-TRACKER-play-world-object-combat-projection.md`
- `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
- `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`
- `Docs/Roadmaps/ROADMAP-con-ready.md`
- `Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`
- `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`
- `Docs/Roadmaps/ROADMAP-play-world-object-combat-projection.md`
- `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
- `Docs/Roadmaps/README.md`
- `Docs/Design/INDEX-design-agent-source-set.md`
- `Docs/Plans/STEWARDS-HANDOFF-demo.md` (continuing mandate only; retain historical evidence)
- `Docs/Roadmaps/ROADMAP-demo.md` (current pickup guidance only)
- `Docs/Design/ARCHITECTURE-application-state-layer.md` (continuing owner guidance only)

Repository-export refresh metadata:

- `Docs/Sources/design-agent/README.md` (record the exact refreshed repository exports; say user-managed Project Sources were not changed)

Byte-for-byte export mirrors, updated after canonical sources:

- `Docs/Sources/design-agent/PROCESS/AGENTS.md`
- `Docs/Sources/design-agent/PROCESS/STEWARD-CYCLE.md`
- `Docs/Sources/design-agent/PROCESS/HANDOFF.template.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md`
- `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-HANDOFF-demo.md`
- `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md`
- Other directly corresponding active export copies, only if the canonical file is changed

## Exclusions

Do not change historical embedded evidence, status/sequence judgments, archived copies, historical reports or underlying archived content. On superseded wrappers, change only the current DEMO destination label. Do not change or rename filenames, URLs or technical identifiers. Preserve all unrelated text. Preserve all `agent_steward` literals, preflight script/test names and hash-sensitive values. Do not change runtime, service, provider, database or model settings. This worker must not open a PR, publish externally, or communicate externally. After independently reviewing the committed head, the coordinating owner may publish this bounded slice as a reviewable draft. Do not alter or close existing PRs, and do not merge any PR. Do not introduce legacy `.cursor` rules as policy gates where current `AGENTS.md` says they are not. Do not substitute PRIME (or another agent) as the default owner. Do not weaken independent review, approval gates, explicit assignment scope, or existing limits on merge/runtime/model authority.

## Acceptance

- Current instructions name bounded assignment as the source of role/responsibility and explicitly deny extra merge/runtime/model authority.
- Canonical process/pickup/index docs no longer assign a standing Steward authority; named task ownership and reviewer independence remain clear.
- Current design-agent exports byte-match their canonical source files, and repository-export refresh metadata is truthful without implying user-managed Project Sources changed.
- Historical evidence and protected technical identifiers remain unchanged.
- Links resolve, diff passes whitespace checks, no unrelated paths changed; exact base/head and changed-path manifest are reported.
