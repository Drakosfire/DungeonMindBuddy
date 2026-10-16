# MIND: source-local collective default

Status: ACTIVE. Owner: PRIME, solo implementation.
Pinned current base: `60c35904d1ef9658f3f00922d9394508b981e973`. Original proposal base: `9083530dae7cfadb4578a4727dab09478e4b5db2`.
Topology: serial existing PR #1139, rebased from exact original head `95511dcb01ce460c205450e594d2278c48d63ec5`. PRIME implements solo; DOGFOOD owns disjoint UI work, ARCHITECTURE reviews. No overlapping active profile lease.

## Outcome

Default an extracted collective to `group`, reducing unsupported faction typing. Explicit factions and organizations remain permitted. Change only the collective pass default; no instructions, schema, source, roster, identity resolution, route, or budget changes. Existing authored knowledge is untouched.

## Lease

- `src/graph_memory/extraction/recap_extraction_profile.py`
- this handoff

No serving or database lease. Candidate-only experiments already exercised the owning prompt/GE boundary: an exact-baseline prompt hash and only `faction`→`group` default produced six groups in one 7.2-second DeepSeek response. Newly authored synthetic controls retained an explicit faction, organization, and temporary group with both defaults. This is preliminary evidence, not broad accuracy or publication acceptance.
Verification: existing profile/extractor suite and bounded client suite; cumulative diff and lint. Preserve exact experiment procedure and measurement privately. No new tests that merely mirror the one-line default.

PRIME authors this proposal. Independent ARCHITECTURE review required before merge under the operator's standing review authorization. Update existing PR #1139, then hold merge pending that exact-head review.
Rollout: accepted merge precedes a new full candidate graph evaluation. Prior C1S16 graphs remain held for guard identity/tunnel/relationship fidelity; this default alone does not resolve them.

Current S29 gold-driven prompt treatment independently exposed the same conflicting default: new ad-hoc-group guidance still emitted the adventuring party as faction while the rendered default remained faction. That broader treatment remains held for missing children and lost location granularity; it is not included here. Preserve its exact private receipt at `c2-session29-source-defined-entities-20261016T0020`. No newly inferred fact or changed prompt is part of this two-path slice.
