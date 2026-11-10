# RETRIEVAL: project object membership once per catalog

Status: ACTIVE. Root adopts the independently critiqued design under the active
retrieval goal. The exclusive expected write lease below is active. Standing
authority covers implementation, local verification, independent review and merge.
The design critique specifically confirms global record order, duplicate-witness
deduplication, distinct unknown-target closure refusal and the source-only fastpath.

Base: fetched main ec649ddc1da3b663853d3c5e9122bcf75cf7afb6, merged2323.
Branch/check-out: codex/retrieval-object-catalog in recorded-names-control.
Topology: serial, no unmerged parent. No other active retrieval implementation PR.
Open2225 is a retained failed composition experiment, not an active lease.
SURFACE2313 and STORAGE2308 remain independent; do not edit their paths.

## Outcome and evidence

Remove repeated whole-query hashing and repeated object/record membership scans
from navigation and selected-read closure. Preserve exact handles, catalog order,
record order, labels, attempted exclusions, empty/unknown behavior and complete
grant/observation checks. This changes no source/query policy or model input.

Accepted2323: reviewed/captured19b07a250c7fb92078f84173de4870aa5320869d,
merge ec649ddc1da3b663853d3c5e9122bcf75cf7afb6. All15 context cases/72 atoms pass;
median request-start to genuine context-ready6375.155123ms, writerHTTP0. Both
candidate cohorts passed conservation; first d49 cohort remains integration-
inconclusive and is not adopted. Six seconds remains unmet.

Evidence: out/retrieval-source-extents-v1/comparison-v2/. Actual retained query
catalogs have20 objects each. object-catalog-projection-opportunity-v1.json measures
the ordinary driver method at50–59ms/call versus about1ms for a single-pass inverse
membership prototype, with exact unexamined/examined tuples in all15 cases.
Selected-read closure also rebuilds handles/family membership repeatedly, including
when the complete admission predicate rechecks a concluded batch. These are real
repeated projection costs; do not multiply helper medians into claimed elapsed
savings. Retained traces, not writer outputs, define the measured critical path.

Other investigated options are not adopted: cross-member grants remove only17
transactions over15 cases; network pipelining has a tiny measured transport floor;
TOAST lz4 saves only3–7ms per tested grant; early existing-session opening-grant
savings are11–14ms before amortizing initialization. MVCC-only ACK is unsafe.
Core metadata-header/API work is deferred; this slice claims no Core paths.

## Design and invariants

Use one ephemeral immutable object-record catalog built from the exact current
query. Compute its query digest once, and inverse-index statement/assertion witness
membership in existing record order. No persistent cache, new evidence codec,
schema, receipt, provider, fallback or model-visible metadata.

The existing selected-ID API delegates to the same membership owner. Preserve
global query record order across multi-object selections, not concatenated object
order. Duplicate witnesses must not duplicate record IDs. Unknown handles grant
nothing. Source/Rules/page-only selections retain their no-query-hash fast path.
Navigation and closure consumers reuse one local catalog for their own operation;
they do not cache mutable attempted/opened status or weaken full admission checks.

## Validation and stopping decision

1. Independent design critique before activation; test adversarial membership,
   order, duplicate witnesses, attempted and unknown/empty cases at the owner.
2. Compare ordinary navigation and closure outputs against retained accepted
   behavior across all15 exact queries, including intermediate attempted states.
3. Run appropriate existing local owner/driver tests, cumulative diff/lint and
   independent exact-head review. Preserve inherited failures honestly. No GitHub CI.
4. If owner measurements justify the change, pin code/dependencies/sources and
   run the existing consolidated context workflow on fresh isolated clones,
   two workers8/7; reuse accepted2323, no fresh unchanged baseline.
5. Independently verify15/72 context support, attribution, chronology, uncertainty
   and exact citations; writer output is excluded. Audit original/retained data
   preservation and report actual request-to-context-ready timings, including
   slower cases and stochastic qualifications. Do not claim causal whole-cycle
   gains from helper timing or accept until one lucky run passes.
6. Remove superseded projection loops. Commit/push/open one bounded PR and merge
   under standing user authority when proven. Otherwise preserve findings without
   leaving an active competing implementation. No deployment.

## Expected write lease after activation

- Docs/Plans/HANDOFF-RETRIEVAL-object-catalog.md
- Docs/Plans/HANDOFF-RETRIEVAL-selected-source-admission.md (merged2323 settlement)
- src/application_state/agent_conversation/native_plan_assertions.py
- src/application_state/agent_conversation/native_batch_completion.py
- apps/live_control_server/services/plan_jev_driver.py
- tests/test_native_plan_assertions.py (existing pure object-membership owner tests;
  replaces the initially proposed corpus-source test location, same capability)
- tests/application_state/test_surface_native_acquisition.py

Artifacts: Projects-backed out/retrieval-object-catalog-v1. No serving ports.
Only disposable owner-test DBs and fresh candidate APP clones on127.0.0.1:55447
may change. Primary, original evaluator, native source DB, retained baselines and
frozen dependencies remain unchanged. No provider process is currently live.
