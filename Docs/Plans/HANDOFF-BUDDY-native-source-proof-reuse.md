# BUDDY: reuse exact-source verification proofs on native neighborhood reads

Status: ACTIVE. Owner: Elderwyld pre-cutover optimization lane.
Authority: operator optimization goal +implementation/review/merge permission;
accepted Core226 design and227 API mergea9e308fe5b208f7ee447bf483a252d08ed04ea0b.
Author base99463c13bdc82f8eb6c5b93177eb99662d325416, branchcodex/native-source-proof-reuse,
existing task-owned Buddy checkout/env. Core227 prerequisite satisfied: independent
review+allCI44415286696green. Parallel-independent from draftCore218: consumer
requires accepted227 API only; artifact storage is optional, not pinned unmerged.
After this slice, joint pinned candidate evidence still gates218/V8/cutover.

Outcome: explicit service-owned two-slot proof pool,32MiB per slot/64MiB total
content cap, injected only into
shared_neighborhood (and its exact-object wrapper) and open_neighborhood_anchor.
Keep standalone inspection, catalog/search/evidence defaults, routes/DTOs and
principal/binding/scope/evidence/source validation unchanged. Fresh complete Core
source row and fresh provenance on every context, even warm. Cache never grants
permission, supplies source truth or stores a returned caller model.

Eight-path lease: services/native_graph_inspection.py;
integrations/dungeonmind/native_registry_source.py;
tests/test_native_graph_inspection.py; tests/test_native_recap_preparation.py
(one test-only fake-factory keyword signature); pyproject.toml; uv.lock; this
handoff; HANDOFF-BUDDY-native-anchor-parse-reuse.md predecessor settlement only.
Existing optional factory defaults unchanged. Explicit cache argument travels
only through selected read ownership. No Core runtime edits, new public contract,
WorldKeeper/profile/route/DTO/GC/selector/provider/ingestion/deployment changes.

Critique: stale source data, missing/corrupt source, caller mutation, different
revision, source withdrawal, audience/binding/campaign denial must never reuse
an authority decision. Only successful identical raw-source proof is reusable;
Core owns all exact-key/bytecap/namespace/concurrency/deep/typedfailure invariants.
This slice proves injection/default ownership, reuses Core proof, and retains
fresh source/principal checks. Module-scoped instance is explicitly Buddy-service
owned per worker, never an implicit library-global or cross-worker cache.

Measured Core native10k component:6freshfullreads/1fullverify acrossfreshrepos;
first225.80ms, later52.78–57.06ms; exactordinaryparity. Content28357004bytes under
67108864cap; canonical source13787171bytes. This selects a bounded candidate
budget, NOT production RSS or route/V8 acceptance. No startup/graphprewarm.

Validation: owner tests for selected neighborhood/anchor reuse, same explicit
instance acrossfreshrepo factories, bytecap/read-only forwarding/defaultabsence,
standalone behavior, existing parse/freshsource/withdrawal/scope/new-history proof;
required auth-app and exactSHA repo-owned hostedfrontend/build/evidencevalidate.
No frontend change: no unrelated discovered diagnostic expansion. Independent
cumulative review, current pin/lock parity and exactsource qualification required.
Actual full-app HTTP candidate after ordinary readiness with0graphprep, first/
warm/eviction/new/history/citations, exactorderedauthorizedresponses, sourcework
counts and memory/write/affectedroute evidence before V8 acceptance. Frozen
classicbaseline mustnotrerun. Serving5202 remains unchanged until accepted rollout.

OpenPRs inspected:4012maintenance,4008combat,3883projection,3888subjects,3889source
extensions; relevant changedpaths4008/3883/3888/3889 do not overlap this lease.
Reanchor on changes, neverinferownership merely from cleanGitmerge. Newbase
includeslater unrelatedPDF service work; preserve it. Prior Buddy3994 accepted
merge415e9f0d52ff0396f765849b6807559af30ce124 settled here, no speculativefinalstate.

Reuse Projects Core/Buddy checkouts,sharedvenv and verifiedNode22.23/npm10.9.8cache.
FilesystemUUID48fa5d10-fe99-4557-9fc9-d8a2a4b41ac8. Scratch/evidence/UVcache under
v7-elderwyld-scope. Owner retains refs/evidence forreview/integration, cleanupafter
explicit scope/process/mount/dirty/unique-data/commitchecks. No globalsettings or
sharedvenv modification; no newmanualworktree/env, manualremoval orservingwrites.

Implementation checkpoint: acceptedCorepin a9e308f in both pyproject declarations
and uv.lock. Selectedservice owns/injects one64MiB cache; standalonefactorydefault
None.76owner/source-inspection checks passed against exactacceptedCore source.
Three new cases prove selectedowner/defaultabsence/read-onlyforwarding; existing
withdrawal/scope/new-history/citation checks remain. Source/recapfakefactories now
accept optionalkeyword only. UV0.10.2 fullresolution matched pin-only package/
dependency/source/sharedhash changes; unrelated upload-times/two prunedgreenlet
platformwheels were preserved fromexistinglock. Minimal2line lock update passes
uvlock--check. No sharedvenv sync. ExactSHAauth/hosted/build/review/jointmeasurements
are pending; no successorcompletion/performance/serving claim.

Newtask-owned UVcachecache/source-proof-adoption retained fordependency review/
qualification; cleanupfollowup afterintegration with explicit scope/process/mount/
unique-data checks. Owner/source logs and lockchecks retained in scratch/v8-core.
No manualfilesystemremovals orservingwrites.

Rebrief after actualHTTP checkpoint e762e35/Core8931b85: first494–496ms,warm77–82,
eviction505–519,new502–520,citation65–69 pass retained~540ms current-read reference.
Historical return731–762ms still triggers206–212ms fullGC. Two distinct revisions
caused3fullproofs: oldproof was discarded byone-slotowner. Before qualifying or
reviewing successor head, keep2revision-specific Core single-entry proof objects
in an explicit locked Buddy-service LRU pool. Each has32MiBcap; total retained
content≤64MiB. This changes only retention/ownership within existing8paths, noCore
API/publiccontract/route/admission/GC change. Each reusedslot still readscomplete
currentrow and usesCore exactallfieldkey; identity only selects a proofslot, never
establishes validity. Missing/corrupt/current source behavior staysfailclosed.
Detachedin-flightrequest slots maylive until thatrequest ends; totalRSS/transient
requestmemory are separate fromretainedpoolbudget andmustnot be claimedboundedby64.
Olde762 owner/auth/HTTP evidence remains checkpoint only, not newheadqualification.
Frontend was refused byexternallyheldOSlock before anytestsallocated. Retry only
throughnormal sharedlock; nootherprocess/lockinode changes. Independentreviewmust
cover poollock/eviction/isolation/budget and newhead allrequiredchecks.
