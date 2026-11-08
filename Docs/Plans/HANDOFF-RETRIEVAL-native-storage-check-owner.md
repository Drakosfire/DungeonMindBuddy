# RETRIEVAL: one native storage predicate owner

Status: ACTIVE implementation; no live or primary migration authority.
Steward: Root; PRIME owns merge/delivery.
Branch: codex/retrieval-native-storage-check-owner, recorded-names-control checkout.
Topology: stacked on PR2264 exact0747c25d5a2d7b72ceefd3a2731d1aebe144c593.
Merge order2261,2264,this slice. No ports/services or retained DB writes leased.
Exclusive writes: this handoff; new migration20261108_0139_native_storage_owner.py
(after138); tests/application_state/test_native_storage_owner_migration.py.
Required validation lease expansion: .github/workflows/world-ownership-core.yml
one query-and-answer test-list entry, so new migration owner tests run in the
existing CI workflow. Checked current openSURFACE2262: no workflow overlap.
No historical migration, runtime, prompts, Gold, ingestion or source changes.
Migration139 scanned absent across fetched remote refs. PRIME notified of allocation.

Evidence: context-rollup-v1/retained-readonly-combined-check-feasibility.json:
allfour predicates124.284ms vs exactnative predicate22.052ms on retainedQ15.
15validnative+9mutation expression comparisons equal; no universal proof claimed.
Independent design: single-native-storage-owner-design-review.json conditionalPASS.

Hypothesis: lifecycle can remain the sole current native storage predicate owner;
remove only its three exact duplicate inner THEN expressions in receipt, execution
and completion checks. Keep outer Play wrappers, historical ELSE bodies, SQL NULL
acceptance and OR(receiptNative,executionNative) anti-downgrade guard unchanged.
Lifecycle exact expression must remain byte-identical. Failure constraint name may
move to lifecycle; inspect consumers and document this diagnostic difference.

Use PostgreSQL's own deparser on a transaction-local empty shape table to identify
the exact existing predicate. Require exactly one match in lifecycle/receipt/execution and exactly two in
completion (migration120 copies its previous predicate into both branches) before
any replacement. No SQL parser, regex rewriting, permanent function, new authority,
NOT VALID window or data rewrite. Drop the temporary shape table in migration.

Validation: fresh disposable55447 database only; old/new predicate equivalence,
direct SQL invalid current rows, null/missing/mixed schemas, actual native owners,
retained historical Play120/121 and legacy shapes, transactional failure/row
preservation, unchanged lifecycle. Independently review cumulative diff. Compare
actual UPDATE cost before claiming improvement; local SELECT results are not a
wholecycle claim. Use consolidated benchmark only after qualified source pin.
Stop on unmatched predicate, weakened rejection, or historical semantic difference;
retain failures rather than adding a fallback. No paid calls in this slice.

Discovery checkpoint: initial exact-deparse refusal preserved. PostgreSQL formats
CASE indentation by nesting; matching adapts indentation only and still requires
full exact fragment. Second refusal proved completion has two known exact copies,
not one. Remove four duplicates across three constraints, preserving lifecycle
as sole owner. Expected multiplicities are fixed, never permissive or guessed.

Parent helper settlement:2264source fixture lookup now recognizes exact existing
V1/V2writer family; targeted test1PASS6.70s and independent deltaPASS. No runtime
change. This successor follows8c0b4552f; earlier97a01base retained in evidence.
Working migration qualification5PASS10.26s includes exact lifecycle preservation,
legacy row unchanged, unmatched predicate refusal and injected after-first-ADD
transaction rollback. Selected current/historical owner37PASS15.38s; actual smallfixture UPDATE
comparison1PASS7.87s, fixedold/new/new/old samples22.273→20.470msmedian.
No large-row/fullretrieval speedup claim. Independent cumulative reviewPASS;
immutablecommit binding and CI/merge/delivery remain.

Predecessor2261 merged3b181c34b;2264 rebased onto that exact main, head0747c25d5.
Both2264commits range-diff equal, including fixture-onlyV1/V2 lookup correction.
This child re-anchored without source changes; historical testedsource retained.
