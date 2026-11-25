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

Expected write set: `AGENTS.md`, its required design-agent export mirror,
`Docs/Guides/GUIDE-development-verification.md`, and this handoff. This slice
does not change CI test selection, triggers, fixture resets, database behavior,
security gates, deployment or protections. The one-App-clone fixture remains
unchanged; performance optimization is separate work.

Verification: inspect cumulative diff and instructions for contradictions;
check whitespace, exact export parity, and the design-agent bundle check against
its inherited baseline. Do not run a full frontend or backend suite for this documentation-only
change. No runtime or database contract is affected. Record failures and limits.
