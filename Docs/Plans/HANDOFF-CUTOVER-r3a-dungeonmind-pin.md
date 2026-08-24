---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / R.3a — Buddy pin of optimized DungeonMind reads
  - Direction: CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-r3a-dungeonmind-pin.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  Pin DungeonBuddy to the merged optimized DungeonMind R.3a library, rerun
  the sealed R.3 supported-contract witness against the real current product
  adapter, measure Buddy's current `direct_services_from_config()` lifecycle,
  and determine `SWITCH_READY` without changing the production default.
---

# HANDOFF — R.3a: pin optimized DungeonMind native reads

**Created:** 2026-08-24
**Status:** LANDED — dogfood accepted; successor is the native-read switch
**Workstream:** CUTOVER / World Graph runtime retirement
**Direction:** CODE → REVIEW
**Implementation repository:** `Drakosfire/DungeonMindBuddy`
**Buddy base (at #632):** `#631 merge` `ffc39ab394ea55b00dc8b2a0fd41be0448635600` (historical; not current `main`)  
**Reviewed R.3 implementation head:** `65405b48ed2d3de917060f41fbb7d69e2eaafe32` (#631 accepted code; second parent of `ffc39ab3`)  
**#632 merge:** `54779636750ebf7a639aef8a6184cc61ead9c860`  
**Current Buddy `main` (after APP-STATE):** `87597f406aae2b169bf4addde2a2b34b1b3d7cad`
**Required DungeonMind pin:** `c5d3688587b0f5d506e0f7d64f33eb0628bac896`
(merge of DungeonMind PR #45 — R.3a read-context optimization)
**Predecessor pin (historical):** `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5`
(DungeonMind PR #43)
**Suggested branch:** `cutover/r3a-dungeonmind-pin`
**Suggested PR title:** `CUTOVER: pin optimized DungeonMind R.3a native reads`
**Predecessor:** Buddy R.3 direct production reads (merged) + DungeonMind #45
**Successor:** native-read switch — remove `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ`
and make native DungeonMind reads the only `dungeonmind` production path
(`Docs/Plans/HANDOFF-CUTOVER-native-read-switch.md`). Then demolish the
hydrated Buddy graph runtime.

> **Dispatch ruling:** DungeonMind is no longer the cutover blocker. This PR
> does not flip the production gate, does not delete hydration, and does not
> redesign Buddy's service factory. It pins the optimized library, proves the
> sealed R.3 contract is unchanged, and measures the adapter as it exists.

---

## 1. Mission

Pin DungeonBuddy to the merged optimized DungeonMind R.3a library, exercise
the already-landed R.3 native read path against the real current product, and
determine `SWITCH_READY` without changing the production default.

We are not comparing against Buddy kernel semantics. We are making sure that
upgrading DungeonMind from #43 → #45 did not alter the accepted R.3
supported-contract result:

```text
0 blocking
0 errored
199 approved semantic divergence
```

## 2. In scope

- Exact DungeonMind pin `c5d3688587b0f5d506e0f7d64f33eb0628bac896` in
  `pyproject.toml` / `uv.lock`.
- Keep the V4 receipt/manifest contract assertion on the new pin.
- Rerun `scripts/compare_direct_dungeonmind_world_graph_reads.py` against live
  Eldyrwild (`dungeonmind_cutover_live`).
- Measure Buddy's actual adapter (`direct_services_from_config()` per product
  request vs the witness's long-lived service object). Do not redesign the
  factory unless the product-path latency is product-breaking.
- Record disposition `SWITCH_READY` or `SWITCH_NOT_READY`.
- Leave `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` default-off.

## 3. Out of scope (falsification)

- Enabling the production direct-read gate, or changing its default to `1`.
- Deleting hydration, contribution replay, UnionSupergraphStore, projection
  cache, or `graph_memory.kernel`.
- Passing a process-global parsed-revision cache into Buddy unless measurement
  proves the per-request factory is product-breaking.
- DungeonMind L.1 architecture-fitness work.
- Write-path changes.

## 4. Why the gate stays off in this PR

The flag existed because direct reads were ~20s. R.3a removed that cost in
DungeonMind. Enabling it is a product-routing decision for the next slice,
after this pin is green. Keeping a permanent toggle between the new
architecture and the architecture we are retiring is a later demolition
concern, not this PR.

## 5. Acceptance

```bash
uv run pytest tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_cutover_dungeonmind_world_graph_authority.py \
  tests/test_world_graph_projection_routes.py \
  tests/test_world_graph_retrieval_routes.py
uv run python scripts/compare_direct_dungeonmind_world_graph_reads.py \
  --database-url "$DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL" \
  --world-id eldyrwild \
  --frozen-root /path/to/repo/out \
  --repo-root /path/to/repo \
  --runs 3 \
  --output /tmp/r3a-buddy-pin-witness.json
```

Expected: pin SHA present; V4 types importable; sealed witness 0 blocking /
0 errored / 199 approved; product-path campaign projection sub-second (or an
explicit `SWITCH_NOT_READY` with the remaining cost). Private JSON is never
committed.

Author-local owning tests on pin head
`8ad097485ef0f81d52b57ff8b1d441da7086ab97` (pytest 9.0.2; this correction
successor does not change those files):

```text
collected 126
105 passed, 21 skipped, 0 failed, 10 warnings in 12.31s
```

Per file:

- `tests/test_cutover_direct_dungeonmind_world_graph_reads.py` — 40 passed
- `tests/test_cutover_dungeonmind_world_graph_authority.py` — 29 passed, 21 skipped (env-gated live integration)
- `tests/test_world_graph_projection_routes.py` — 4 passed
- `tests/test_world_graph_retrieval_routes.py` — 32 passed

## 6. Stop conditions

- Blocking or errored rows vs the sealed R.3 contract.
- Identity preflight drift (receipt V4, M0/M1, D_A, D_B).
- Product-path latency still in the multi-second range after the pin.
- Any change that flips the production gate to "prove" the optimization.

## 7. Handback

- Pin: `c5d3688587b0f5d506e0f7d64f33eb0628bac896` (DungeonMind #45)
- Owning tests: 105 passed / 21 skipped / 0 failed on pin head `8ad09748`
  (see §5 for the four-file breakdown)
- Witness: 17 cases, 0 errored, 0 blocking, 199 approved, 2345 representation,
  1056 retired, 2 ranking, 1 presentation join
- Adapter performance (reused services): projection 548 ms; retrievals
  120–226 ms
- Product factory rebuild: projection 845 ms; factory-only 72 ms; cache reuse
  saves ~90 ms. Do not redesign the factory in this slice.
- Disposition: **SWITCH_READY**
- Production gate: still default-off
- Named next slice: native-read switch — remove
  `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` rather than defaulting it to `1`, then
  demolish the hydrated Buddy graph runtime
