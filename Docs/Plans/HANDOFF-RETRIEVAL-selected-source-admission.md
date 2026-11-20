# RETRIEVAL: settle one actual selected-source batch efficiently

Status: MERGED as2323, ec649ddc1da3b663853d3c5e9122bcf75cf7afb6. The exact
reviewed/captured head was19b07a250c7fb92078f84173de4870aa5320869d. Its write
lease is released; the consuming object-catalog handoff owns the next slice.
Fixed comparison-v2 independently passed15/15 cases72/72 atoms and conservation;
median request-start to genuine context-ready6375.155123ms, writerHTTP0. First
d49 comparison remains INCONCLUSIVE_NOT_EXERCISED, with all evidence preserved.
Primary/original APP/native data remain unchanged. No deployment; goal still active.

Base: fetched main 9e4e68f79809d698f36d7ce3f47f597ee8d4f078, merged2322.
Topology: serial, no unmerged parent. The2322 implementation lease is released;
its exact reviewed/captured head is0ff4a6941ef188ec6ccb75d44c44cd83e3c45de4.
Checkout: existing recorded-names-control, branch codex/retrieval-source-extents
from that fetched main. Never local main. No serving runtime is active.

## Outcome and evidence

Reduce repeated source admission, durable acknowledgements and reconstruction
within one actual controller-selected read closure. Preserve the individual
existing source grants, observations, exact extents and citation authority. This
is an APP/native-read owner change, using the existing Core source API. If that
API contract must change, stop and name its repository owner before implementation.

Accepted2322 evidence is in out/retrieval-opening-batch-v1/comparison/: median actual
request-start to genuine context-ready6540.902331ms,15/15 cases72/72 supported
atoms,30 controller calls, writerHTTP0. Q03's three terms are acquired Graph
assertion/citation supported rather than separately body-present; exact five
source spans were independently checked and rehashed. Preserve both the initial
body-only HOLD and the corrected support assessment. The goal is still active.

Use comparison/residual-critical-path-audit-v2.json, not its corrected v1 subtotal.
Median cumulative native_source_append is1678ms; median per-case enclosing work
outside nested materialization is1253ms. Materialization includes Core IO and host
work, not pure database time. These are nested cumulative work, not additive
elapsed phases. execution_append and trace_append overlap other measurements.
Actual serialized controller-round cumulative time can be subtracted per case
from elapsed; do not subtract independently aggregated medians or sum overlapping
spans. Bootstrap source authority and Graph query are consecutive separate phases.

Existing NativeBodyNavigation.select serializes grants and observations around
each source. Consecutive direct-source grants already share one append; do not
rebuild that capability. NativePlanSession guards the whole storage image and
detaches public exports on each transaction. The service currently permits only
direct-source grant tuples. Closed producer and transaction boundaries matter.

Hypothesis: settle an actual selected-source closure with fewer redundant durable
handshakes/materializations/exports, removing a material part of this seconds-scale
host cost without changing controller input, selected knowledge or source policy.
The retained timings are an opportunity bound, not a promised saving.

## Design gates before a write lease

1. Map actual dependencies: direct sources, sections, explicit full documents,
   already covered extents, search/discovery, human-selected reads, partial and
   unavailable results. A planned full-document read cannot satisfy a selected
   section until a real successful acquisition exists. Do not orphan a granted
   section by later skipping its observation.
2. Choose one coherent batching/handshake mechanism. Reuse the closed existing
   producers, event codecs, ledger and source API. No alternate producer, batch
   provenance authority, generic callback engine, long-lived body cache, fallback
   or question-specific policy. Preserve actual event order dependencies.
3. Grants must commit before physical Core IO. APP must still prove the actual
   claim/image/selection and Core must enforce principal, membership, source
   revision/hash, epoch/revocation and exact selector. Do not silently move IO
   across those boundaries to make a timing look smaller.
4. Specify exception/rollback/unknown semantics. Preserve already committed and
   known partial success; never silently replay unknown grants/physical reads.
   An all-or-nothing batch must not erase required known evidence when a later
   sibling read fails. Unknown failure is not an unavailable successful read.
5. Inspect whether independent physical reads can overlap safely. Shared private
   mutable Turn/connection/source contexts cannot be handed to parallel callbacks.
   Do not add concurrency without a proven isolation contract. If serial Core IO
   is required, eliminate unnecessary host serialization at its owning boundary.
6. Inspect storage and complete recovery acceptance. Unchanged event representations
   may need no migration; prove that rather than adding a decorative reader fence.
   Preserve closed command/producer dispatch, exact CAS/ACK and public/private
   mutation refusal. Do not replace full owning checks with helper-only tests.
7. Independently critique this design, quantify the transactions/exports avoided
   on retained captures, then root pins an ACTIVE handoff/ref and exact write set.

## Intended scope and validation

Expected owner paths, subject to design adoption: native_reads.py, service.py,
native_plan_session.py, corpus_source_navigation.py and only their necessary
existing source/phase invariants and owner tests. Any widened path/contract needs
a checkpoint and explicit amendment. Include truthful2322 predecessor settlement
in the next consuming implementation handoff's lease. No unrelated ingestion,
composition, source-label repair, schema project or writer grading.

Use actual isolated APP/Core mock-transport tests for real grants before IO,
dependency/overlap fulfillment, partial/unknown failures, duplicate/mixed replay,
stale claim/image, epoch/membership, callback mutation and exact receipt/citation
reconstruction. Use existing retained contexts/decisions and workflow for offline
equivalence where useful; no per-question scripts or alternate harness.

After credible owning proof and exact-head review, one changed15-case cohort may
compare against accepted2322 using the same existing workflow, sources, providers,
roles and ordinary attempt policy. Preserve all72 atoms, attribution, chronology,
uncertainty and exact inspectable citation support. Writer output is excluded.
No unchanged paid baseline or retry-until-pass. Keep primary, original evaluator,
native sources and all existing evidence/resources unchanged.

Adopt only a measured meaningful improvement with full supported context; retain
rejected/inconclusive evidence. Actual request-start to context-ready6000ms remains
the goal; an accepted-to-ready number, helper speedup or partial reduction does
not complete it. No deployment. One bounded reviewable PR after activation.

## Adopted mechanism and gate evidence

Independent design review: retrieval-record-transitions-v1/selected-source-admission-design-review-v2.json,
base9e4e68f79, reviewed original draft d91e635be944be876264d9fb81c0c59512dca34fe54930aabf5094da400b29d1.
Exact full-ledger/packet/projection/citation offline feasibility is retained in
out/retrieval-opening-batch-v1/comparison/same-member-offline-owner-feasibility-v1.json:
all15 contexts remain equal;11 actual consecutive eligible same-catalog groups,
19 repeated captures and38 grant/observation transactions potentially removable.
This is feasibility, not actual grouped IO/commit or latency proof.

Choose one mechanism: commit all existing individual grants of one consecutive
same-exact-catalog/source/access-span/authority/controller group, capture its
verified body once through the existing Core owner, project each exact selected
extent with existing selectors, atomically commit all individual observations.
No cross-member observation batch. Full-document/section dependencies are group
boundaries; one successful future full-document read cannot orphan pregranted
sections. A single-item group uses this same owner. Previous physical-member
groups remain committed if this group fails; a capture/transaction crash leaves
this one physical group unresolved, with no automatic retry. Explicit Core None
produces existing unavailable observations; access/integrity exceptions propagate.
Projection integrity refusals retain existing typed failure semantics, never omit
a group member or silently return a smaller tuple. Complete replay is whole and
ordered; partial, mixed, reordered or cross-controller replay refuses.

Existing per-item public body-write ports/commands are superseded after existing
callers/tests move to the one group owner. Reuse canonical extent selectors and
existing event codecs; keep historical readers, not competing runtime producers.
The existing service direct-grant tuple check must become an exact closed producer/
family gate, not an arbitrary tuple append. No new generic batch framework.

Activation adopts the design/failure contract and offline owner evidence above.
Actual APP/Core tests and complete owner performance measurements are implementation
gates before paid execution, not claimed completed by this activation.

## Exclusive expected write lease

- Docs/Plans/HANDOFF-RETRIEVAL-selected-source-admission.md
- Docs/Plans/HANDOFF-RETRIEVAL-opening-batch.md (truthful merged2322 predecessor sync)
- src/application_state/agent_conversation/native_reads.py
- src/application_state/agent_conversation/service.py
- src/application_state/agent_conversation/native_plan_session.py
- apps/live_control_server/services/corpus_source_navigation.py
- apps/live_control_server/services/plan_jev_driver.py (ordinary caller must pass consecutive source reads to the one navigation grouping owner)
- tests/application_state/test_native_corpus_sources.py (migrate owning single-item port tests and cover group failures)
- tests/application_state/test_surface_native_acquisition.py
- tests/application_state/test_surface_native_decisions.py
- tests/test_native_reference_navigation.py

No serving ports; only disposable owner-test DBs and later fresh candidate APP
clones on127.0.0.1:55447 may change. Accepted/original APP, native source DB, primary
data, frozen dependencies and all retained evidence remain unchanged. Artifacts
use Projects-backed out/retrieval-source-extents-v1. No provider worker is active.
Exact code review, source/inventory pins and explicit experiment acceptance precede
any changed paid cohort; no unchanged baseline. No deployment.

Owning integration checkpoint: the first changed cohort atd49e25d8633c19b5cb983341aaf3465ad7aa3d03
produced zero multi-section groups. The actual Plan driver only grouped direct
sources and passed body handles individually. Root extends this same slice's lease
to that caller; no new capability. Preserve comparison/ as failed-integration
evidence. Extend the actual SDK test through PlanJevDriver.apply, not only direct
navigation.select. Re-review the changed head and use a distinct changed capture
only after this real dispatch boundary is proven; never relabel the first run as
successful grouping or repeat unchanged code.
