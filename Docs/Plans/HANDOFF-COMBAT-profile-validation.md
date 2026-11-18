# COMBAT — validate system-neutral manual profiles

MERGED as #3990 at `1e208b20ac64bcac7682b4f8ea7ea5919fc69e79`; source lease
released to HANDOFF-COMBAT-versioned-records.md. Exact reviewed head
`c61c350d4a070ca88ea841737e2971a0d1a2f3b7` has independent code/evidence acceptance:
49 named-contract profile tests,16 CI guards and all1,557 classified files pass
in a clean isolated exact-SHA checkout with locked dependencies. Source/hash/
fixture/environment/Projects UUID/cleanup evidence is retained under
profile-exact-c61c350d4a070ca88ea841737e2971a0d1a2f3b7 in the task evidence root.
The managed verification checkout is confirmed archived. No persistence, UI,
DB/provider/runtime activation or full-goal completion is claimed.

Original authority: under the operator's Combat implementation and review/accepted-merge
authority. Serial successor to #3984, merged
`c67f8b8a50c5d7aab63dd983d5bf75d859710c54`. Fetched base
`b416410d5ecc3031a2c2db56a8aa31e0e5c480f6`; branch
`codex/combat-profile-validation`, existing isolated fc67 checkout. No unmerged
parent; one open Combat implementation PR. Root is the assigned designing owner.

Outcome: a private, pure APP validation foundation for immutable custom profiles,
typed named values, independent actor defaults and bounded resource adjustments.
The synthetic Crossing profile has Position, Resolve, Stress and Momentum, with no
required AC, HP or initiative. Only ordered pacing is admitted initially; incomplete
side/spotlight modes are refused. No persisted v2 encounters or UI are activated.

Exclusive writes: this handoff; predecessor HANDOFF-COMBAT-manual-order.md truthful
settlement; new src/application_state/combat_encounters/manual_profiles.py;
tests/test_combat_manual_profiles.py; retained fixture
tests/fixtures/combat/manual-profile-v1-compat.json; one named pure validation
contract in ci/contracts.json. Existing v1 DTOs/rulesets/serializers, repository,
HTTP, source producers, recovery, session initialization and migrations are
read-only. #3668's adoption/minimums paths do not overlap this module.

Classification gate resolved: cleanup #3983 merged, releasing its file lease.
The lane fast-forwarded from its initial3fcc base over disjoint main changes to
the base above. Add exactly tests/test_combat_manual_profiles.py to the fast lane
in ci/test-classification.json; no selector or existing entry changes. The new
pure tests have no provider/DB/service operations. No competing migration head,
service/port, provider or DB writes.

Invariant critique: frozen profiles must contain immutable child descriptors,
not mutable lists/dicts. IDs are unique across descriptors, values match exact
declared membership/types, unset is explicit, and booleans/fractions/unknown fields
are refused. Resource bounds are coherent but editing them does not clamp current
state. Explicit positive integer adjustments move toward the appropriate bound
without reversing direction or snapping an out-of-range value to the other bound.
Unset current and numeric overflow refuse without input mutation. Profiles pin a
deterministic canonical digest; importing this module cannot change old v1 payloads,
aliases or digest preimages. Defaults for different actors share no mutable maps.

Verification: pure model/transition tests at the owning boundary, synthetic
non-D&D values, deep immutability, invalid membership/types/bounds, adjustment
edges, independent defaults, canonical serialization and retained v1 API/template
payload/digest fixtures. Use the owning locked Python3.13 environment and run the
repo's named contract in an isolated exact-SHA checkout. Run CI contract/inventory
guards once classification ownership resolves. Inspect cumulative diff and obtain
independent exact-head Bugbot review. No browser claim for private validation code.

The full profile create→prepare→materialize→edit→recover→save integration remains
required after a sequenced additive DB acceptance change. #3877 reserves0161;
its #3875 prerequisite has merged. A user question about coordinating sequencing
with PRIME is pending; silence is not permission to message another chat. Side/
spotlight, runtime reader adoption and the real Graph journey remain required.
Detailed reviewed design/evidence: `/home/drakosfire/Projects/.codex/buddy-check.LPopRI`.

Preliminary code review found no correctness bugs. All49 working-tree pure tests
pass on Python3.13.12 with locked Pydantic2.13.4/pytest9.0.2. These are diagnostics;
exact-commit contract evidence and formal review remain pending. The compact
canonical profile budget does not establish PostgreSQL JSONB text-size acceptance.
Validate that storage boundary and freeze the complete persisted descriptor schema
before v2 activation. This slice proves neither persistence/version dispatch nor
source adoption, recovery, initialization or side/spotlight pacing.
