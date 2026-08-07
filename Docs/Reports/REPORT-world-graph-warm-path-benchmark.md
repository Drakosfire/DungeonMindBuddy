# World Graph warm-path benchmark report (OPT-BENCH01)

**Measured code SHA:** `9ac6d3aa4ab3b532571db1fa7c9eb08409cc75fd`  
**Fixture:** `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1` (`world_id=eldyrwild`, `campaign_id=longmont-c2`)  
**Request:** Plan-like head-following projection — `scope_mode=campaign`, `focus.kind=session`, `focus.session_id=session-23`, `revision_pin=null`, `query_text=null`

## Results (10 iterations per scenario)

| Scenario | p50 e2e (ms) | p95 e2e (ms) | build p50 (ms) | cache | graph reads | resident |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| A — Fully cold | 6.27 | 6.58 | 3.17 | miss | 1 | miss |
| B — OPT01 resident | 3.15 | 3.49 | 2.99 | miss | 0 | hit |
| C — OPT02 prewarm | 3.25 | 3.77 | 3.07 | miss | 0 | hit |
| D — OPT03 surface warm | 0.09 | 0.21 | 0.00 | hit | 0 | hit |

## Relative improvements (p50 e2e)

| Comparison | Improvement |
| --- | ---: |
| B resident vs A cold | 49.8% |
| C OPT02 vs A cold | 48.1% |
| D OPT03 vs A cold | 98.6% |
| D OPT03 vs C OPT02 | 97.4% |

## Live Plan dogfood

Live Plan surface dogfood was **not run** in this automated bench environment (no live-control UI session wired). Template for manual follow-up:

| Observation | Result |
| --- | --- |
| Plan graph panel opens without manual refresh after publish | not observed (automated bench only) |
| Perceived "graph is simply there" on session focus | not observed |
| Network waterfall shows projection cache hit on repeat open | not observed |

## Measured answers

**What did OPT01 buy?** Scenario B (resident admitted, cache cold) vs A shows resident hits with zero graph payload reads on the warm path, but projection still builds each iteration because the completed cache is cleared. OPT01 removes repeated durable revision load cost.

**What did OPT02 buy?** Scenario C adds post-publish coordinator prewarm so the first read after publish already has the new head resident; e2e p50 improves vs fully cold even when the projection payload must still be built.

**What did OPT03 buy?** Scenario D replays the learned Plan recipe after publish and fills the completed projection cache, yielding cache hits with `graph_payload_reads==0` and near-zero build time — closest to "graph is simply there" within this harness.

**How close to "graph is simply there"?** OPT03 scenario D median e2e is 0.09 ms with typical cache status `hit` and graph payload reads `0`. Fully cold A median e2e is 6.27 ms.
