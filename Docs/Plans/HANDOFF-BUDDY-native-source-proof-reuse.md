# BUDDY: exact-source proof reuse for native neighborhood reads

Status: ACTIVE, implementation/review finalization; V8 and serving rollout unaccepted.
Owner: Elderwyld pre-cutover optimization lane. Authority: operator goal with
implementation/review/merge authorization; accepted Core226/227 design/API.
Author base99463c13bdc82f8eb6c5b93177eb99662d325416; runtime proof anchor
5dcd5ffc4b5422d31326d20699799a1556d9f73c. Core pin is accepted227 merge
a9e308fe5b208f7ee447bf483a252d08ed04ea0b, never an unmerged artifact dependency.
Parallel-independent from draftCore218. This slice does not activate cutover.

## Outcome and lease

Selected shared_neighborhood and open_neighborhood_anchor reads use an explicit
Buddy-service-owned, locked two-slot LRU. Each slot is a Core single-entry exact-
source proof cache capped at32MiB; total retained UTF-8 content cap is64MiB.
The exact-object wrapper uses the same neighborhood path. Pin identity selects a
slot only; Core still reads complete CURRENT source every time and compares every
raw field under its verifier namespace before reusing a successful immutable proof.
Fresh provenance, principal/binding/campaign/scope/evidence/citation checks remain.
Standalone inspection, catalog/search/evidence and factory defaults stay unchanged.
Every read context and source-body response still uses fresh admission checks.

Eight paths: apps/live_control_server/services/native_graph_inspection.py;
apps/live_control_server/integrations/dungeonmind/native_registry_source.py;
tests/test_native_graph_inspection.py; tests/test_native_recap_preparation.py
(one fake-factory keyword signature); pyproject.toml; uv.lock; this handoff; and
HANDOFF-BUDDY-native-anchor-parse-reuse.md predecessor settlement only.
No Core runtime, migration, public contract/route/DTO, profile/WorldKeeper, GC,
prewarm, provider/ingestion, selector, deployment or cutover change.

The two-slot retention was explicitly rebriefed before implementation after the
one-slot HTTP experiment reconstructed3times for2revisions. Retaining the old
proof removes that repeated work without caching source authority. Nonidentical,
missing, corrupt or unavailable source cannot hide behind a slot. Oversized
proofs verify ordinarily and are not retained. Detached in-flight slots maylive
until those requests finish; neither total RSS nor transient request memory is
claimed bounded by the64MiB retained-content cap. No implicit library-global cache.

## Verified implementation evidence

At runtime head5dcd5ff against exact acceptedCore source:
- 78 owner/source-inspection checks pass, including same-owner forwarding, unchanged
 standalone default, readonly factory/no eagerDB, LRU/cross-space/budget/concurrency,
 and existing withdrawal/scope/new-history/citation/fresh-source checks.
- 253 exact-SHA auth-app checks pass. Backend receipts/logs are in task scratch as
 source-proof-owner-5dcd5ff.log and source-proof-auth-5dcd5ff.log.
- Repo-owned hosted verifier passes1410selected cases (1405+4+1), collection parity
 and build, Node22.23.0/npm10.9.8,8workers. Canonical evidence.json validation passes;
 all checkout/install/inventory/test/build source boundaries are clean.
 Receipt: source-proof-hosted-5dcd5ff-attempt1/evidence.json; cleanup_complete true.
- Independent cumulative CODEAPPROVE at5dcd5ff against99463c1, no runtime findings.
 The soleP3 request was updating stale qualification language; this rewrite records
 completed evidence. Documentation-only deltas require their own review/receipts,
 recorded in the PR rather than self-referential claims about an unknown finalSHA.

Both pyproject Core declarations and the minimal2line uv.lock update point toa9e308f.
UV0.10.2fullresolution confirmed package graph/sources/shared artifact hashes;
unrelated optionalupload-times and2prunedgreenletplatformwheel entries were retained
from the existing lock. uvlock--check passes. Sharedvenv was not synced or changed.

## Actual HTTP result and limits

Pinned candidate Core8931b854cd9fea4f3b993b832e064adbfff3aa4f (draft218 plus accepted
227), Buddy5dcd5ff: fullmain.app/lifespan/owned loopbackHTTP, actualreadonlyfactory,
fixturebinding only.14loaded source-module paths/hashes match committed code.
Normalhealthreadiness does0knowledge preparation; no graph prewarm or GC tuning.
Three fresh workers returned exact ordinary-parser responses/citations and401.
Each initial5requests made5complete source reads,5freshsourceviews and1artifactfetch;
1fullsource reconstruction. Old/new/old lifecycle needs2fullproofs, not3, while
parsed-cache eviction/new/history each fetch the exact persisted artifact as needed.

Milliseconds across3workers: first484.9–492.6; warm77.8–84.0; parsed eviction
509.6–512.2; visible newrevision505.3–514.4; historical return536.2–554.2 (median
538.7); firstcitations66.6–69.9. Fullhistorical GC remains202–218ms. One historical
sample exceeds the approximate540ms retained classicreference; do not call this
an all-samples performance acceptance. Frozen classicbaseline was not rerun.
Retained proofcontent56721035bytes below64MiB; RSSready~462.5MiB,warm~523.2MiB,
end~594.7MiB. This is candidate composition, not adoption by servingbuild5202.
Prepare+commit10.75s(secondhop)/10.55s(visiblechange) is not matchedwrite acceptance.

Evidence family: native-postgres-artifact-source-proof-pool-8931b85-5dcd5ff.json/
.log/-pytest plus test_v8_postgres_artifact_source_proof_pool_candidate.py and
native_socket_source_proof_pool_actual.py. Testpassed79.25s. Earlier one-slot
 e762e35 result remains negative history evidence, not qualification for this code.
Still required for jointV8: remaining affected/currentElderwyld route and historical/
withdrawal evidence, matchedwrite/scale dispositions, final accepted dependency
adoption and canonical jointrecord. OnlyacceptedV8 permits V9/rollback preparation.

## Topology, resources and cleanup

Precommitted lease1c8599c84; explicitretentionrebriefad221b03b; no added paths.
Open4012maintenance/4008combat/3883projection/3888subjects/3889extensions inspected;
relevant changedpaths do not overlap runtime/test/dependency lease. Preserve newer
unrelatedPDF service changes from authorbase. Predecessor3994 merge415e9f0d is
settled here, never premark this successor complete. Reanchor before acceptance.

Existing Projects Core/Buddy checkouts, sharedvenv and verifiedNodecache reused;
UUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. NewUVcachecache/source-proof-adoption is
lane-owned and retained for qualification/integration; observed75522698bytes.
All evidence is under v7-elderwyld-scope/scratch/v8-core. Retain unique refs,
receipts/logs/probes/pytestdirs forreview/integration; cleanup follows explicit scope
and process/mount/dirty/unique-data/commit checks. No blanket deletion authority.

Firstfrontend receipt e762e35 refused a heldOSlock beforetesting. Ownedqueue3624475
waited naturalrelease, ran normalverifier and endedexit0. Verifier removed its own
clean temporaryroot verification/frontend-verification-z_iwhc_h, reportingcomplete
cleanup; exact reclaimed bytes unavailable. Backendqueue3784732 similarly waited,
then ran timing under the normalsharedlock and endedexit0. Noother process/inode
was altered. Sourcefixture794732f99a8f was dropped; priorf2798ab10366 also dropped.
No newmanualworktree/env, manualfilesystemremoval or servingwrites. Subsequent
receipts and postmerge settlement travel with the dependent acceptance slice.
