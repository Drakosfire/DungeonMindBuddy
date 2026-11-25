# CI: Choose verification by affected boundary

Status: ACTIVE. The user explicitly requested correcting the verification
selection that led to an unnecessary two-hour backend run. Owner: this app lane;
branch `codex/verification-scope-policy`, base
`50a178354253bd87bf5d7291ec90a2700b1de4ce`. Delivery is one serial,
independently reviewable policy/documentation PR; merge remains separately
authorized. There is no implementation prerequisite.

Outcome: require a documented connection between a change's risks, affected
boundaries and selected checks. Make clear that a large named contract is not
automatically mandatory because one small test or symbol falls within its broad
inventory. Focused exact-source checks may establish the affected invariant when
they exercise its owning boundary. Preserve any explicitly applicable contract,
release, authorization, security, persistence, isolation and independent review
requirements; do not call narrow evidence full-suite or release qualification.

Expected write set: `AGENTS.md`, its required design-agent export mirror,
`Docs/Guides/GUIDE-development-verification.md`, and this handoff. This slice
does not change test selection, CI triggers, fixture resets, database behavior,
security gates, deployment or protections. The one-App-clone fixture remains
unchanged; performance optimization is separate work.

Verification: inspect cumulative diff and instructions for contradictions;
check whitespace, exact export parity, and the design-agent bundle check against
its inherited baseline. Use the repo-owned exact-SHA hosted frontend verifier
before review as the existing policy requires. No runtime or database contract
is affected by this documentation-only change. Record failures and limitations.
