# Reuse immutable native preparation when opening a neighborhood citation

Status: ACTIVE. Owner: Elderwyld pre-cutover performance lane.
Authority: operator optimization-before-cutover goal with implementation/review/
merge authorization and lane ownership. Base: main7014b5de30e32b306893f4bc6315a086d34d4c18.

Outcome: a neighborhood source-anchor read reuses the exact immutable parsed
revision already available to the shared native read routes. It must still verify
the requested revision, open fresh source/provenance authority and enforce every
principal/role/World/binding/campaign/source/citation check on every read.
Do not cache read contexts, source views, authorization decisions or source bytes.

Evidence: existing open_neighborhood_anchor calls inspect -> _pinned without
parsed_cache. A native-only full-app socket feasibility probe on retained Buddy
ca5a045/Core74f24c2 removed one duplicate2291524-byte artifact fetch and reduced
one exact citation opening688ms→193ms; later citations743/736→212/213ms. Full DTO/
exact source, revision verification and fresh-source checks passed. These are
feasibility observations, not current deployment/latency acceptance. Existing
frozen classic baseline was not rerun. Eviction/history latency outliers remain.

Scope/write lease: only inspect and open_neighborhood_anchor in
apps/live_control_server/services/native_graph_inspection.py, owning regression
coverage in tests/test_native_graph_inspection.py and this handoff. A private
optional cache argument is allowed internally; no request/response/route changes.
Keep ordinary standalone inspect behavior by default. No auth, profile, descriptor,
Kernel, WorldKeeper, dependency/lockfile, frontend, source authority or GC changes.
Current main catalog/presentation/assertion read changes remain intact. Relevant
open hosted authorization/recap work is outside these two preparation calls.

One independently reviewable Buddy optimization PR, from current main. The
NativeParsedRevisionCache API exists at Buddy's accepted Core pin a672791b;
this code slice does not depend on unmerged artifact APIs. Review/test it against
the locked Core behavior and the current candidate Core runtime separately.
Core218 remains separate and must be accepted/re-pinned before claiming artifact
performance adoption. No deployment/selector/cutover change in this PR.

Required proof: neighborhood→anchor prepares once for an unchanged exact pin;
each call still verifies revision and opens fresh source authority. Current and
historical pins may not cross-reuse; changed source authority/withdrawal at a
fixed graph pin must reauthorize and withhold text. Preserve binding, wrong-
campaign/principal/authentication denials and exact receipt/span/citation behavior.
Test no cache/context/authorization escape and standalone inspect default.
Use focused local owner contracts, then required exact-SHA repo verification and
independent cumulative review. Preserve failures and no fabricated qualification.
Keep a regression for the removed graph preparation, not a timing-only assertion.

Reuse the existing task-owned Projects Buddy checkout/env. Evidence and any
verification mirrors/caches stay under the verified v7-elderwyld-scope task root
(UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8). No serving data, provider calls, new
ingestion or frozen baseline rerun. Retain active review artifacts with explicit
cleanup follow-up and process/mount/dirty-data/unique-commit checks; no deletion
permission is inferred. Core cutover goal remains performance-gated.
