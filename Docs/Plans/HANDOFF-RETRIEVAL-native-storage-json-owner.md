# RETRIEVAL: materialize native storage-check JSON once

Status: ACTIVE bounded qualification; Root activates the expected write lease. Root owns this
human-authorized retrieval optimization design. Branch
codex/retrieval-native-storage-json-owner, base18b992193b103b1e0a05490855bd8af620bed835.
Serial topology, predecessor2287merged18b992193 with user approval. No unmerged
behavior dependency. Expected scope after activation: forward APP migration142,
existing native storage migration tests plus bounded new owner tests, this handoff
and truthful predecessor settlement. Other open UI/held composition/ingestion
lanes do not own this predicate; migration numbering must be rechecked before edit.

Measured owner: retained ledger~2.17MB, receipt~217KB. Actual UPDATE driver~64ms,
server45–49ms. Identical temporary row/index/storage copies measure~41ms with
CHECKs versus~19ms without. No real check was dropped. SQL-only append/narrow
ack feasibility70.28→57.32ms is insufficient alone and does not replace typed
readback/recovery. Delayed observation batches remain rejected.

Hypothesis: repeated JSON operators in the one native storage predicate repeatedly
decompress its large toasted inputs. A temporary pure PL/pgSQL function evaluating
the same predicate after object||empty-object local copies measured25.607→2.610ms.
This is one valid-row feasibility result, not a whole-cycle gain. Keep every exact
predicate, lifecycle selector, NULL/coalesce rule, reader fence and retained row.
Replace the active native inline fragment with one function owner; no cache,
trusted flag, alternate default, new model representation or weakened constraint.

Design gates: differential valid/malformed/SQLNULL/JSONscalar/nested-type parity
across Build/Plan/Play and lifecycle/completion families; verify immutable function
and protected search_path; exact deparser/whole-fragment match before migration;
forward-only transactional failure and retained-row conservation. Preserve old
migration tests at their actual139boundary rather than rewriting their expected
behavior to a newer owner. Independent design critique before activation.

Qualification after activation: actual PostgreSQL constraints/refusal and migration
rollback tests; fixed retained30context canonical parity (15cases twice); whole
append measurements and controlled fresh capture-context comparison only after
local gates. Writer output excluded. Report component/whole-cycle medians/tails
separately; no extrapolating23ms across unmeasured calls into a success claim.
Reject on any refusal/data/authority regression; retain failures. Six seconds is
still the broader target, not achieved by local predicate timing.

Resources: owned isolated55447 profiling/test/benchmark clones only; frozen native
read-only and primary unchanged. All evidence under retrieval-controller-host-
accounting-v1 and the future dedicated storage-owner experiment root. No live
runtime upgrade or primary migration authorized by this design.

## Activation checkpoint

Independent design critique completed. Temporary differential tests192primitive
and249whole-lifecycle cases match TRUE/FALSE/SQLNULL/SQLSTATE across existing
Build/Plan/Play shapes, malformed JSON/nulls and completed shapes. Catalog
properties include explicit CALLED ON NULL INPUT, immutable, invoker security,
parallel-safe, protected pg_catalog search_path. Never use STRICT: CHECK accepts
SQLNULL, so strict argument null propagation could bypass the old COALESCE.
Current column types and common text collation verified read-only. Preserve
these gates in actual migration tests. No real constraints changed by prototypes.
Source temporary probes initially omitted arguments/Play JSON serialization;
those failures rolled back and are not passing evidence.

Activated writes: new20261109_0142_native_storage_json_owner.py; existing
tests/application_state/test_native_storage_owner_migration.py; bounded new
tests/application_state/test_native_storage_json_owner.py; this handoff and
HANDOFF-RETRIEVAL-controller-host-accounting.md predecessor settlement. Migration
slot142 rechecked; fetched remote946813e3 changes only Reference docs, disjoint from the pinned base18b992193. No primary/live migration authority.

## Implementation qualification

Actual PostgreSQL owner suite17passed, including positive Build authoring/image,
Plan/Play, completed Rules, SQLNULL/JSONscalar parity, sole lifecycle ownership,
function properties, populated-row conservation, unexpected function identity
and transactional failure rollback. Historical139 tests retain their139boundary.
Initial fixture failures are retained with corrected DB-only required fingerprints.

Prospective rollback-only append ABBA samples: parent258.474/258.859ms;
candidate239.106/239.989ms, approximately19.1ms lower median under cProfile.
Every append verified retained event equality and full transaction rollback.
Both clones are isolated; no provider/CoreIO or primary effects. This synthetic
large retained fixture is not a whole-cycle latency comparison. Evidence:
retrieval-native-storage-json-owner-v1. Full30 retained contexts and controlled
fresh comparison remain pending; do not claim six-second success or adoption.

## Fresh qualification and CI settlement

Pinned candidate c6096f063, parent18b992193. Both ordinary capture-context arms
completed15/15 with two separate isolated workers per arm. Independent reviews
verify72/72 required context atoms in each, exact quotes/selectors/source-local
authority, chronology and uncertainty; zero writer I/O. Exact30 retained native
benchmark rows also accepted by both actual lifecycle predicates, read-only.

Fresh accepted-to-ready median9463.030→10086.765ms; nearest-rank p95
19818.506→18613.693ms. Controller calls75→74. This pair DOES NOT demonstrate
whole-cycle improvement. Preserve it; no unchanged replay. Local append
improvement is not extrapolated into six-second success.

CI initially refused the unclassified new test filename before tests ran.
Consolidated the same17 tests into the existing CI-classified native storage
owner suite, avoiding the active CI lane's registry. All function/fixture ASTs
match the reviewed files exactly; consolidated suite17passes. The new standalone
test file is removed, not registered as another parallel suite. No runtime or
migration change after the benchmark pin. Evidence remains under
retrieval-native-storage-json-owner-v1 and retrieval-native-storage-comparison-v1.
PR2290 is implementation delivery, not adoption, deployment or goal completion.
