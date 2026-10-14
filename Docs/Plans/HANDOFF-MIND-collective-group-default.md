# MIND: source-local collective default

Status: ACTIVE. Owner: PRIME, solo implementation.
Pinned base: `9083530dae7cfadb4578a4727dab09478e4b5db2`.
Topology: serial; current open Buddy PRs inspected, no overlapping extraction lane. Stewards remain stopped.

## Outcome

Default an extracted collective to `group`, reducing unsupported faction typing. Explicit factions and organizations remain permitted. Change only the collective pass default; no instructions, schema, source, roster, identity resolution, route, or budget changes. Existing authored knowledge is untouched.

## Lease

- `src/graph_memory/extraction/recap_extraction_profile.py`
- this handoff

No serving or database lease. Candidate-only experiments already exercised the owning prompt/GE boundary: an exact-baseline prompt hash and only `faction`→`group` default produced six groups in one 7.2-second DeepSeek response. Newly authored synthetic controls retained an explicit faction, organization, and temporary group with both defaults. This is preliminary evidence, not broad accuracy or publication acceptance.
Verification: existing profile/extractor suite and bounded client suite; cumulative diff and lint. Preserve exact experiment procedure and measurement privately. No new tests that merely mirror the one-line default.

PRIME authors this proposal. Independent review required before merge; the operator's previous ARCHITECTURE review exception applied only to PR #1138. No implicit new agent dispatch. Carry this work through PR, then hold merge pending review.
Rollout: accepted merge precedes a new full candidate graph evaluation. Prior C1S16 graphs remain held for guard identity/tunnel/relationship fidelity; this default alone does not resolve them.
