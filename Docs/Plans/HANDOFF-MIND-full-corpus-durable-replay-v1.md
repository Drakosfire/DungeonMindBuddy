# HANDOFF — MIND: full-corpus durable replay code preparation v1

**Created:** 2026-10-08

**Status:** CODE-PREPARATION COMPLETE / EXECUTION-HOLD

**Canonical handoff path:** `Docs/Plans/HANDOFF-MIND-full-corpus-durable-replay-v1.md`

**Conversation/workstream:** MIND / full-corpus recovery

**Flow / owner:** MIND; PRIME designing steward

**Direction:** PRIME DESIGN → MIND CODE → ARCHITECTURE independent review → PRIME acceptance

**Design authority base:** `12134e7cae37425131c1e74f170d85f48e21ac2c`

**PR topology:** serial

**Code-preparation activation gate:** satisfied by authority #1031 merge `3c8ad79a2008a20b75bd7d8791d139ad1404c75b`; endpoint implementation #1032 is now merged. A new exact execution lease is still required before any replay or storage write.

**Dispatch base rule:** fresh current `main` containing this handoff; record the exact dispatch base and reconfirm path ownership.

**PR authorization:** one design/architecture authority PR first; after its acceptance, merge, and re-anchor, one assigned endpoint-only implementation PR. No overlapping successor PRs.
**Implementation PR title:** `MIND: pin isolated full-corpus replay endpoint`

This is a new authority contract, not a revival of an old replay lease. The operator's full-graph reuse/replacement goal and PRIME's explicit bounded adoption authorize code preparation only. The authority PR is a steward-designated design exception under `AGENTS.md`; its sole changed path is this file. Repository operating law and `Docs/Process/STEWARD-CYCLE.md` continue to govern dispatch and review.

### Completed code-preparation checkpoint — 2026-10-08

Endpoint PR #1032 reviewed implementation head `9aab67aeef92a316c4b0dd2d4aa0196ab746fb80` merged as `f687ecef54dd508e3fdff0c85cba21792bfa3b7f`. Final runner SHA-256: `c0d9e3c26e016d6784bd03a9cbebad0d9ba446c004aa42a6c67c050b5e4ef54e`.

The source invariant is delivered: exact host/port/database path, rejection of query/service/host-address redirects, and guard enforcement before every entry point's database seams. Independent review found that leading-slash normalization admitted a different libpq database; the final repair requires exact raw `parsed.path` and tests raw/encoded slash cases across all four entry points. Author-local full replay cohort on the prior head: 149 passed under installed Core `a501784f21aaafb46d7561f46397a3afdc42f125`. Final repair head: 139 focused guard tests passed, 20 unchanged tests deselected; inherited Pydantic schema-shadow warning only. These are author-local synthetic results, not replay or product-readiness evidence. Canonical PR fetch confirmed exactly the two leased paths and passing allowlist/denylist checks.

The §4 code-preparation lease is released. No implementation successor or runtime write is dispatched by this completed handoff. PRIME owns a separately reviewed concrete isolated execution contract; storage/replay/migration/provider/live-binding/deletion all remain HOLD. The agreed full selected-World corpus, including Session 28 and relevant worldbuilding, must be accounted for before readiness claims or operator journey/provider QA under DungeonOverMind #35 merge `cfb9cd821fa48d2f1ecc0f6e5eb510e0002f7aad`. The frozen 44 sessions alone are not full current World integration.

## §1 Mission and merge-ready invariant

Prepare the existing zero-model governed replay runner to admit exactly one isolated endpoint, so a later separately leased replay cannot accidentally write the current live graph authority.

**Invariant:** all runner modes accept only `127.0.0.1:54362/dmb_current_corpus_replay_v1`; any other host, port, or database fails closed at the existing runtime guard before database probes, migrations, source admission, genesis, review, or publication. World, pristine-target, cohort digest, source-byte continuity, expected-parent, identity/review/publication and zero-model gates remain unchanged.

This capability does not execute replay, reserve storage, prove a completed graph, activate product loadability, or switch the live World. A newly replayed graph must have its own observed head; it must never be labeled a restoration of the missing historical terminal payload.

**Pre-dispatch critique:** changing only the port while preserving `localhost` normalization or allowing arbitrary loopback ports would widen the lease. Testing only `assert_runtime_dsn()` would miss a mode that bypasses it. §7 therefore requires negative mode-level proof before any seam probe/write, as well as the exact-tuple helper matrix. Endpoint preparation and durable replay are separate outcomes and remain serialized.

## §2 Context, authority, lane, and topology

- Buddy design base: `12134e7cae37425131c1e74f170d85f48e21ac2c`.
- Core reference anchor: `a501784f21aaafb46d7561f46397a3afdc42f125`. This is not permission to repin Buddy dependencies. Effective installed Core code must be independently pinned before execution.
- Runner at design base: `evals/graph_memory_layer/run_current_corpus_candidate_replay_acceptance.py`, SHA-256 `a17332314bab81380f3c753dc6c5b73884d2c85998c8bac9388f8074d7a10088`; currently fixed to port `54330`.
- Frozen cohort: 44 ordered unique campaign/session entries; manifest digest `d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c`.
- Private recovery inventory SHA-256: `d97a9aa8013134278e3a556d93312c9cb3c3d634c9f20f78ca3fccee03798786`. Inventory observations: 44 candidate files, 44 frozen source caches, 44 span indexes; no missing input files or candidate/source hash mismatches. Private material stays in operator storage, never in this PR.
- #730 is DONE/released. It forbids rerun, backfill or successor execution under that old lease. Its completion report is historical evidence, not new write authority.
- #731 merge: `9e739057540e52e763ba9fc6a62d2f1ef5ac2f96`. Its source-span continuity fix governs fresh publications; it neither changes a frozen World nor establishes product loadability. Verify compatible source-span code and its tests in the final execution pin; if another code repair is necessary, stop for a separate rebrief.
- Historical replay World: `dogfood-current-corpus-replay-v1`; reported genesis `rev:77fdd25fc46a0dc896a65b679f7dd68f`, terminal `rev:aa435599cb957b666987503b7bef585c`, 45 graph writes. Exact completed payload, receipt lineage, replay ledger and DB backup were not located. Its stopped container used tmpfs without retained mounts.
- Named successor: separately reviewed durable isolated replay, preservation/restore proof, actual Buddy read/source-open proof; later separately leased runtime cutover and conditional retirement.
- Remains false: recovered exact historical terminal state, new completed replay, product loadability, semantic acceptance, live cutover and retirement.
- Design lane: isolated branch `codex/mind-full-corpus-replay-authority`; no endpoint implementation lane until authority merge. Endpoint lane must start from fresh `origin/main` without checking out local `main`.
- Open PR snapshot at design: #1030, #1014, #1007, #927, #869, #844, #826, #798, #765, #764, #763; no new full-corpus recovery implementation PR. Recheck changed paths and ACTIVE handoffs before dispatch. Source isolation does not authorize use of their services, DBs, caches or generated `out/` state.
- State-authority sync set: this new handoff only. Record the authority merge and endpoint implementation/review facts when knowable through PRIME's guarded sync; keep execution HOLD. Old #730/#731 artifacts are historical, not rewritten or reactivated by this slice. Do not invent future merge facts or churn unrelated roadmaps.

## §3 Observable paths and adversarial sequences

- Exact leased tuple → existing runtime guard succeeds; no real connection is opened by tests.
- Current live `54330` with either the live or replay database name → `ReplayStop`, boundary `runtime_guard`, before any probe/write.
- Historical acceptance DB on leased port → deterministic runtime-guard rejection.
- `localhost`, other loopback addresses, remote hosts, wrong database, missing port and every other port → rejection; no host normalization or general loopback allowance.
- Environment/default DSN selects live endpoint → every mode still rejects it; no fallback to another authority or old file graph.
- Valid tuple but dirty checkout, nonpristine target, drifted cohort/source or invalid governed publication → preserve existing STOP behavior. This endpoint change cannot waive those checks.
- Preflight, execute and product-smoke invalid endpoint sequences → rejection before their first stateful seam. Use synthetic fixtures only; do not invoke CLI replay against a real database to prove this clause.

## §4 Files in scope — write lease

This authority PR originally created only this handoff. The following two-path CODE-PREPARATION lease delivered #1032 and is now released; it gives no further source or runtime/data-write authority. Retain the table as the completed implementation's diff contract, not an active reservation.

| Action | Path | Purpose |
|---|---|---|
| Modify | `evals/graph_memory_layer/run_current_corpus_candidate_replay_acceptance.py` | Pin exact isolated endpoint without relaxing existing admission gates |
| Modify | `tests/test_current_corpus_candidate_replay_acceptance.py` | Exact-tuple and mode-level zero-mutation rejection regressions |

**Bounded discovery exception:** none. Handoff maintenance is PRIME's guarded authority sync, not a third worker path. Another required test/module/dependency/schema path is a stop and rebrief, not an automatic lease expansion.

## §5 Explicitly out of scope / collision boundary

| Path | Exclusion |
|---|---|
| `apps/**`, `src/**`, `pyproject.toml`, `uv.lock` | No product, runtime, dependency, profile or admission semantics change |
| `out/**`, corpus files, source caches, registries | No candidate/source rewrite, identity correction, replay output or binding mutation |
| Old #730/#731 handoffs and reports | No reopening, backfill, historical graph mutation or false loadability claim |
| Docker/DB/runtime configuration and deployment files | No container/volume creation, startup, migration, live DSN switch or deletion |

No provider calls, extraction, manual whole-corpus semantic repair, new loader/framework, alias/identity changes or automatic fallback. Synthetic temporary test files are allowed only through existing test fixtures; private corpus must not enter published logs or CI.

## §6 Implementation and future execution contract

Keep fixed World `dogfood-current-corpus-replay-v1`, fixed database `dmb_current_corpus_replay_v1` and fixed host `127.0.0.1`; change leased port to `54362` and reject `localhost` instead of normalizing it. No caller-controlled endpoint override or broad allowlist. Use the existing typed STOP boundary. Do not silently catch an invalid DSN and substitute a default target. Tests must prove all entry paths enforce the guard before their first database seam.

### Proposed storage — NOT ACTIVATED

- Host/port/DB: `127.0.0.1:54362/dmb_current_corpus_replay_v1`.
- Container: `dmb-full-corpus-durable-20261008`.
- Named persistent volume: `dmb-full-corpus-durable-20261008-pgdata`; mount appropriate to the separately pinned PostgreSQL image. No tmpfs, ephemeral storage or automatic removal.
- Durable private operator exports outside the repository: complete DB dump, exact terminal graph, sources/revisions/evidence, all reviews/contributions/identity/publication receipts, frozen cohort, incremental/final replay ledger and hash manifest. Do not publish private paths, credentials or corpus prose.
- Read-only 2026-10-08 observation: Docker server `27.2.0`; escalated host listener check found no `54362` listener; Docker inventory found neither proposed container nor volume name. This does not reserve them. Recheck availability, disk space and private permissions before a future lease.

### Execution HOLD — separate exact lease required

PRIME must review and activate a new execution contract after endpoint merge. It must pin final Buddy/Core installed code, lockfiles, runner hash, schema inventory/migration command, PostgreSQL image digest, storage ownership, source/evidence policy, profile/vocabulary digests and exact immutable six-PC genesis roster payload. The source-span fix must be verified in the actual execution environment. No speculative command or unresolved placeholder is an executable lease.

Use unchanged verified frozen candidates and sources through existing governed source admission, prepare/review/identity and publication operations. No model calls, re-extraction, silent repairs, skipped sessions or bypasses. Expected cohort proof is 44 ordered confirms plus one approved genesis = 45 contiguous graph writes, with a new terminal head and exact expected-parent/receipt correspondence. On any STOP preserve the partial target and last-good-head artifacts; do not reset, resume or retry under an expanded lease without explicit review.

Historical C1 `514/307` and C2 `527/307` projection counts are comparison observations, not authoritative expected new payload hashes. Full cohort coverage does not prove semantic correctness, recall or precision.

Capture complete durable exports before shutdown; independently restore a backup into a separately leased witness and compare exact head/payload and full relevant row/hash inventory. Candidate files alone are not a backup of graph authority.

Product loadability remains a separate proof gate: actual isolated Buddy projection, complete object/neighborhood, GM/PLAYER filtering, authorized source open and digest, plus grounded query behavior. Existing runner smoke is necessary but insufficient. Provider work is not authorized here; any required provider witness needs its own lease.

Core DSN is global; `native_world_id` alone cannot choose this separate DB. Before future live rollout inventory all consumers and specify existing managed-binding deactivation/version-token CAS plus explicit runtime DSN ownership. Target unavailability/integrity failure must fail closed, never fall back to the old partial graph or raw file cache. Retirement remains conditional on validated replacement and cutover proof, including history citations, pending operations, PlanRun, source, backup and shared-table dependency inventory. Never drop an ambiguous shared DB.

## §7 Evidence required to merge

**Authority PR evidence:** exact base, one-file diff, hash/provenance privacy inspection, #731 ancestry check, endpoint lease/hold separation, independent ARCHITECTURE judgment and PRIME acceptance. No test or CI result implies replay authority.

**Endpoint implementation evidence:** helper positive/negative matrix, preflight/execute/product-smoke invalid-target rejection before any probe/write, environment/default target coverage, and the entire existing synthetic replay test file passing without providers or real databases. Record exact base/head, actual runner hash, dependency environment and author-local versus independently rerun results.

Exact commands for the endpoint implementation, from its clean isolated checkout:

```bash
uv run pytest tests/test_current_corpus_candidate_replay_acceptance.py -q
git diff --check
git diff --name-only origin/main...HEAD
sha256sum evals/graph_memory_layer/run_current_corpus_candidate_replay_acceptance.py
git merge-base --is-ancestor 9e739057540e52e763ba9fc6a62d2f1ef5ac2f96 HEAD
```

If a required test fails on base, capture the same failure on exact base/head; do not claim green or edit outside §4. No live/dogfood scenario is authorized in this code-preparation phase. Future actual product/restore proof belongs to the separately activated execution contract, not a synthetic-test claim.

## §8 Required review handback

Record exact PR/head/base and formal review-cycle number; declared topology; cumulative changed paths; §1 invariant disposition; each negative target and entry-path result; unchanged governing gates; actual runner hash and effective dependency pins; evidence provenance and any baseline failures; collision/STOP findings; and all execution/cutover/retirement actions still false. Return to PRIME after endpoint acceptance; do not turn this handback into replay activation.

## §9 Acceptance rubric

- [ ] Independent architecture review approves this new bounded authority without reopening #730.
- [ ] Authority PR merges before endpoint worker dispatch; fresh current-main anchor and path ownership are verified.
- [ ] Endpoint implementation changes only the two §4 paths and keeps serial topology.
- [ ] Only the exact leased tuple succeeds; live/historical/wrong-host/DB/port/default targets are rejected before probes/writes in every mode.
- [ ] Existing frozen-cohort, pristine-target, source, identity, review, publication and zero-model gates remain intact.
- [ ] No private corpus content, paths, credentials or replay exports are published.
- [ ] Runner/code/dependency proof is exact and does not claim restoration of historical terminal state or semantic acceptance.
- [ ] Containers, volumes, migrations, replay, providers, live runtime/bindings and deletion remain untouched and EXECUTION-HOLD.

## Stop conditions

Stop for unresolved handoff activation, lease collision, any third implementation path, generic endpoint configurability, admission/source-span repair beyond endpoint scope, inability to prove a mode's pre-write guard, unsafe shared runtime state, provider dependence, invented historical payload identity, or any attempt to treat code merge/storage availability as replay or live cutover authority. PRIME must resolve scope/ownership and record a new exact activation contract before execution.
