# RETRIEVAL: one native storage predicate owner

Status: MERGED #2265 at `5c49a30f37b11ac3b5706f553f0505b3b9a571cb`, exact head `5a3dbfae3d4a45c41eff2ab0d85589beefb6e365`, after independent approval and seven green checks. PRIME applied migration139 within the protected136→141 upgrade; this grants no separate live migration authority to other stewards.

Protected paired delivery verified on 2026-11-09: API `d8174ba9ad2e431fa534f39095a5d535311ba7f6`, UI `0e984f79b149c98b9851a1eaf1fa2147a2bdab40`, APP schema `20261108_0141`. Implementation and runtime write leases are RELEASED. Delivery preserved retained APP/Core rows and session inventory except the schema version; the original failed attempt was preserved. This is technical delivery evidence, not operator acceptance.

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

Post-CI fixture settlement: parentf5c50bbbd changes only two test files and
lease documentation;9focused testsPASS23.04s, independentdeltaPASS. This
rebase leaves all src/apps/evals blobs identical to benchmark candidatee40.
Migration139/test/CI-entry implementation remains frozen; PRIME's serialPlan
successor may reserve140 after this reader fence. Root does not edit the released
shared runtime paths during the frozen comparison. Merge/delivery still pending.


Delivery evidence: `plan-page-settled-proof.json`, `plan-page-readonly-proof.json` and `plan-page-api-candidate-owners.log` under the established PRIME runtime-evidence root. The exact assembled API candidate passed243 owning cases with3 explicitly excluded inherited fixtures; UI TypeScript/Vite passed. No provider calls, fresh ingestion, publication or authored-page mutation occurred during delivery.
