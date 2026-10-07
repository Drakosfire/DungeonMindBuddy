# SERVER — Core withdrawal V2 consumer adoption

Status: source accepted by PRIME at `849a1cfda5eb686267891cc34569678afed134d3`, merged as #1019 `804a9d38b877ad931f64ebbb015632d5f69010ce`; runtime adoption remains separately unactivated. Base: Buddy `main@049ecb5f718d7be5e14ced6f15dd033f40420128`. Serial topology: one new dependency-consumer PR on `codex/server-core-withdrawal-v2-adoption`; it is independent of held #1014's UI/runtime rollout. PRIME owns review and merge. Existing #826/#763 dependency edits are suspended and must re-anchor when revived.

**Question:** Can Buddy consume accepted Core `a501784f21aaafb46d7561f46397a3afdc42f125` (#100), including a governed locator-null withdrawn child and durable V4 adoption receipt, through its existing projection/source/history boundaries?

**Lease:** `pyproject.toml`, `uv.lock`, `tests/test_core_withdrawal_consumer.py`, and this handoff. No production adapter change is included: the existing binder accepts the SDK's verified V4 receipt attributes, and projection/retrieval/source contracts are unchanged. The lock diff changes only the selected Core Git references. No provider, retriever, authority, API, or product workflow is added.

**Runtime exclusion:** Current runtime/source/environment/DBs and #1014 remain untouched. Candidate environment is separately installed at `/tmp/dmb-core-a501-venv`; its Core distribution identifies exact a501. Hermes remains 0.18.2 from the existing prepared source. A future deployment must compose this bounded dependency delta with the then-accepted held UI/run source; it must not replace that source with bare main. Compare production source bytes rather than assuming a dependency PR carries unmerged UI.

## Owning proof

The new regression uses public Core SDK operations and existing synthetic Buddy read fixtures. It canonically adopts a synthetic V2 bundle, performs the existing explicit source-classification repair to create V4, then performs a capability-scoped V2 withdrawal with explicit null locator. Both in-memory and isolated PostgreSQL implementations are exercised. The fixture is synthetic only; the PostgreSQL branch refuses operator ports and requires an empty named test database at Core0014.

Buddy's actual direct adapter reads the child and historical parent: only the selected relationship disappears from the child, its control relationship survives, the old parent still contains the target, and the legacy adoption bridge remains intact. The same locator-null evidence is unchanged and readable for the retained assertion. The existing bounded source index returns its exact evidence membership, and a digest-verified source read still returns the synthetic source bytes under the child pin.

The synthetic database was initialized through Core0013 then advanced to `0014_adopted_withdrawal_v2`. This is not the previous 0007 rollout helper or live migration authority. Relevant existing source-admission, indexed saved-Plan, receipt/history and native/source-read continuity suites run under the inactive a501 environment with separate synthetic APP-STATE/Core databases. Verification: two new regression cases passed (memory and synthetic PostgreSQL). The existing read/source/index/receipt suites passed 126 cases; after supplying the missing Core test DSN, the fresh-recap source-read continuity case also passed. One native first-world **write** continuity case fails with `Admitted source pair is not snapshot-provable`; the identical case fails under a separate inactive Core5d baseline with the same error, so no new a501 regression is established and no unrelated fixture/runtime fix is included. Total distinct passing cases: 129. `uv lock --check`, changed-file Ruff and diff checks passed. Final base/head are recorded in the PR evidence packet. A temporary Git-index overlay onto live held source `b86fb0e09bb149d3de63718b2979fd4ddf746cf9` changed only `pyproject.toml`/`uv.lock`, retaining every UI/run/API/helper blob; no runtime files/index were touched.

## Real-data evidence limit

MIND's accepted private operation proof `83505ebad8c3fece589b1a8972034d1c8a0d77b588c74e5e489624909593f5c3` remains Core operation evidence. Its disposable database was removed and no standalone child/source export survives; its receipts cannot seed actual consumer reads by themselves.

Automatic approval review rejected a proposed new full live-Core snapshot and private-data reconstruction as insufficiently authorized sensitive-data replication. The command did not start. That payload was not recreated through another route. PRIME directed completion using synthetic consumer compatibility and the accepted MIND evidence; no real-data Buddy read of that withdrawn child is claimed. Any future real-data reconstruction requires explicit approval of that exact payload or another governed, authorized fixture export.

## Acceptance and future gates

Acceptance requires the exact locked Core pin, inactive imports, synthetic governed V4/V2 adapter proof, relevant existing read/source/index/history gates, changed-file Ruff and cumulative base→head review. PRIME independently accepted this source capability; that acceptance does not activate any runtime or data operation.

Future live readiness remains separate: prepare an exact composed consumer source/environment; re-anchor current source and data; own a new 0013→0014 migration/backup/preservation/rollback lease; respect downgrade refusal once V2 receipts exist; and obtain separate authority for durable V4 repair or withdrawal. Do not reuse #1014's 0007-specific backup helper as that authority. No live withdrawal, V4 promotion, deployment, model call, receipt rewrite, or Graph coverage improvement is authorized by this PR.
