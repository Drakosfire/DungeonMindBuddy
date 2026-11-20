# Reuse immutable native preparation when opening a neighborhood citation

Status: COMPLETE. Owner: Elderwyld pre-cutover performance lane.
Authority: operator optimization-before-cutover goal with implementation/review/
merge authorization and lane ownership. Base: main565b0e97cf918a03dc387f1c426e94961d9099d3.

Outcome: a neighborhood source-anchor read reuses the exact immutable parsed
revision already available to the shared native read routes. It must still verify
the requested revision, open fresh source/provenance authority and enforce every
principal/role/World/binding/campaign/source/citation check on every read.
Do not cache read contexts, source views, authorization decisions or source bytes.

Evidence at predecessor start: open_neighborhood_anchor called inspect ->
_pinned without parsed_cache. A native-only full-app socket feasibility probe on retained Buddy
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

Implementation: inspect accepts a private optional _parsed_cache and forwards it
to _pinned; only open_neighborhood_anchor supplies the existing shared cache.
Standalone inspect defaults to uncached preparation. No other read/auth path or
dependency changes. All37 owner tests pass with exact declared Core a672791b
source and separately with candidate Core74f24c2. Six new checks prove one parse
across neighborhood/citation while every call verifies revision/opens source;
fixed-graph withdrawal withholding; scope denial; standalone default; and visible
new/historical response/citation restoration. At77354de6458b3d33b3fba029dc87785a8cac960f, all248 exact-SHA auth-app
checks pass on both declared/candidate Core. The repo-owned hosted verifier
passed1408 selected tests with collection parity and a successful build;
canonical evidence.json validation passed, Node22.23.0/npm10.9.8 and8workers.
Independent cumulative APPROVE77354de against actual base565b0e97 found no
code issues. Final174639d qualification/delta review passed before accepted
merge415e9f0d; runtime/test blobs were unchanged by finalization.

Retain Core source verification mirror at
/home/drakosfire/Projects/.codex/v7-elderwyld-scope/verification/core-a672-anchor-reuse
(archive of exacta672791bacd14a55da488b4639d95dfe39de3805, no dependency changes)
for declared-pin verification. Cleanup after delivery with active process/mount,
unique-data/commit checks and explicit scope; no removals authorized here.

Bounded verification rebrief: the required auth-app contract exposed one inherited
player-denial harness failure (247pass/1fail on both declared/candidate Core with
explicit local configuration). tests/test_native_source_inspection.py overrides
retired native_graph_gm_dependency while its production route now uses
native_graph_explorer_dependency. Route/test blobs exactly match base565b0e97;
this slice did not introduce the mismatch. Extend the lease by this one test path
only, updating the imported/overridden dependency, preserving401/409 assertions.
This restores the required authorization proof; no production authorization or
source-inspection behavior changes. Four-path PR, one cache capability plus its
required safety validation. Do not absorb other hosted/source work.

Actual committed Buddy77354de/Core77f20f8 full-app/lifespan/socket proof uses12
child-loaded module path/hash checks and a reachable new object/edge. Three cold
graph reads449–463ms after ordinary readiness (zero graph/revision/source work),
repeats196–208ms, citation187–191ms with0extra artifact fetches; later citations
203–217ms. Full new/historical responses and exact citation SHA preserved:
a64c21442cb988b1e92e410b34c30668317174ebdfe9e6792ccbea25593dafbc.
Eviction642–655ms and historical-return696–707ms remain beyond the retained~540ms
reference. This slice removes duplicate preparation, not every latency outlier;
V8/current deployment/cutover and matched writes remain unaccepted.

Base correction: a shared main ref advanced between inspection and branch
creation. The actual parent of the initial handoff is565b0e97, not the earlier
inspected7014b5de. Cumulative scope against565b0e97 is exactly these4paths; Build
commits already on main are excluded. Future branches should pin the inspected
SHA explicitly. No unrelated runtime changes were added by this correction.

Retained exact-head evidence is under task scratch/v8-core: auth-app declared/
candidate logs at77354de, actual socket helper/harness/JSON/log/pytest directory,
hosted-77354de-attempt2 evidence plus earlier lock-refused attempt. The global
lock was honored; a live unrelated Vite server retained it until natural release,
then the owned queue completed. No process of another lane was stopped. The
verifier removed only its disposable frontend-verification-pqw13yx3 source/cache
root and reports cleanup_complete, clean source, no surviving owned process group.
Its reclaimed byte count is not exposed by the verifier; backing UUID is the
verified Projects filesystem above. Task-local checksum-verified Node22.23/npm
10.9.8 cache/archive and Core source mirror remain retained with cleanup follow-up.
No global environment changes or serving database writes; no baseline rerun.

Accepted predecessor3994: reviewed final174639d merged as415e9f0d52ff0396f765849b6807559af30ce124.
Cumulative review and finaldelta approved;37owner/248auth-app checks,1408hosted/
build/canonicalevidence and shortGitHubchecks passed. It removed repeated immutable
citation preparation; fresh source/admission stayed unchanged. Actual first449–463ms
but eviction642–655/history696–707ms keptV8false. Successor native-source-proof-
reuse owns additional verification-work removal and acceptedCore227 pin; this
postmerge settlement does not mark that successor or cutover complete.
