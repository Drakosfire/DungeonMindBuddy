# RETRIEVAL: adopt shared relevance instructions

Status: MERGED #2260 at `3f34e9932a7efb23eea9d26d4988dd5eecedd7c9`, exact head `c0e0c1b59d4c2c549594c341d2fafdb8548c137c`, after owning review/check gates. No new performance experiment or successor redesign is activated.

Protected paired delivery verified on 2026-11-09: API `d8174ba9ad2e431fa534f39095a5d535311ba7f6`, UI `0e984f79b149c98b9851a1eaf1fa2147a2bdab40`, APP schema `20261108_0141`. Implementation and runtime write leases are RELEASED. Delivery preserved retained APP/Core rows and session inventory except the schema version; the original failed attempt was preserved. This is technical delivery evidence, not operator acceptance.

Exclusive writes: this handoff; apps/live_control_server/services/plan_jev_dispatch.py;
src/application_state/agent_conversation/{jev_retrieval_contract.py,native_retrieval.py};
tests/test_jev_retrieval_contract.py, tests/test_native_object_retrieval.py,
tests/application_state/test_surface_native_decisions.py, tests/test_surface_native_writer.py;
src/application_state/migrations/versions/20261108_0137_shared_relevance_guidance.py.
No service/Rules/Build work projection/ingestion/source-authority changes.

The user corrected the adoption rule: simplification is independently valuable;
failed proof of speedup is not a demonstrated regression. Restore only the reviewed
2253 runtime delta6c2f0a0fe; preserve both15/15 contextPASS cohorts and mixed timings.
Hypothesis: identical relevance instruction once per state preserves all semantic
choices and source context. Controls: exact original2253 runtime blobs, fixed
models/candidates/keyword behavior, frozen corpus and prior context assessments.
Acceptance: current/historical wire reconstruction and owning tests, actualSDK
parity reused only with identical blobs, independent cumulative review. No paid
rerun or speedup claim. Stop on semantic/source/choice regression; no fallback.

Reader fence137 is allocated here after fetched main and all-local-ref137 path
history inspection returned no match. Main head136 is the adopted Rules constraint
upgrade. Original2253 fence135 is obsolete and must NOT be restored over association135.
New PlanV2/BuildV4 persisted parent request codecs change exact controller bytes;
native_retrieval.verify_input parses parent_request_json and reconstructs actual
request commitments. Old code only recognizes PlanV1/BuildV2/V3 and cannot safely
continue/reconstruct new requests.137 is therefore a no-data reader fence at the
existing migration owner, not a data or capability migration. Retain all current
old-reader checks and add136. No databases are migrated except disposable55447
owning test fixtures. Primary/live/original evaluator remain unchanged.

Automatic approval rejected an attempted unallocated137/conflict resolution.
This handoff explicitly records its necessity/allocation and exact conflict rule:
retain current dynamic-head assertion and all existing old-reader cases, adding136;
do not restore the old fixed135 assertion or discard unrelated Rules-era tests.
Independent review must verify this justification before delivery.


Delivery evidence: `plan-page-settled-proof.json`, `plan-page-readonly-proof.json` and `plan-page-api-candidate-owners.log` under the established PRIME runtime-evidence root. The exact assembled API candidate passed243 owning cases with3 explicitly excluded inherited fixtures; UI TypeScript/Vite passed. No provider calls, fresh ingestion, publication or authored-page mutation occurred during delivery.
