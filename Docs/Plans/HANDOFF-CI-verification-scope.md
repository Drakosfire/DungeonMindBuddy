# CI: Choose verification by affected boundary

Status: ACTIVE. The user explicitly requested correcting the verification
selection that led to an unnecessary two-hour backend run. Owner: this app lane;
branch `codex/verification-scope-policy`, base
`50a178354253bd87bf5d7291ec90a2700b1de4ce`. Delivery is one serial,
independently reviewable policy/documentation PR; merge remains separately
authorized. There is no implementation prerequisite.

Outcome: use only minimal checks needed for the affected invariant and its
owning boundary. Never run an entire named backend contract, a full frontend
suite, or a blanket full-project run as local agent verification. Documentation
changes normally need diff, mirror and affected-link checks only. Preserve
security and isolation through focused checks, and report separate full-suite
release evidence as missing rather than treating focused checks as a substitute.

The operator extended this serial PR to remove conflicting instructions found in
Buddy's verification audit. Expected write set:

- `.cursor/agents/extraction-lab-operator.md`
- `.cursor/agents/skeptical-reviewer.md`
- `.cursor/rules/subagent-delegation.mdc`
- `.cursor/rules/verify-before-debug.mdc`
- `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`
- `AGENTS.md`
- `Docs/Guides/GUIDE-development-verification.md`
- `Docs/Plans/HANDOFF-CI-local-verification-standard.md`
- `Docs/Plans/HANDOFF-CI-verification-scope.md`
- `Docs/Plans/HANDOFF-HOSTED-owned-native-graph-explorer.md`
- `Docs/Plans/HANDOFF-PLAN-contextual-paragraph-placement.md`
- `Docs/Plans/HANDOFF-STEWARDSHIP-close-cutover-and-audit-dungeonmind.md`
- `Docs/Plans/PLAN-surface-interaction-host-hoist-pr-sequence.md`
- `Docs/Sources/design-agent/PROCESS/AGENTS.md`
- `Docs/Sources/design-agent/PROCESS/HANDOFF.template.md`

 This slice
does not change CI test selection, triggers, fixture resets, database behavior,
security gates, deployment or protections. The one-App-clone fixture remains
unchanged; performance optimization is separate work.

Verification: inspect cumulative diff and instructions for contradictions;
check whitespace, exact export parity, and the design-agent bundle check against
its inherited baseline. Do not run a full frontend or backend suite for this documentation-only
change. No runtime or database contract is affected. Record failures and limits.
