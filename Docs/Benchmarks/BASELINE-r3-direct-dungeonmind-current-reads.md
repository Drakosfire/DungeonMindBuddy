# BASELINE — R.3 direct DungeonMind current-world read witness

**Date:** 2026-08-22 (historical V3 witness) / 2026-08-23 (frozen V4 vocabulary-v1) / 2026-08-24 (supported-contract vocabulary-v2) / 2026-08-24 (R.3a Buddy pin rerun)
**Branch:** `cutover/r3a-dungeonmind-pin` (R.3a pin); historical R.3 on `cutover/direct-dungeonmind-production-reads`
**Handoff:** [`../Plans/HANDOFF-CUTOVER-r3a-dungeonmind-pin.md`](../Plans/HANDOFF-CUTOVER-r3a-dungeonmind-pin.md)
**R.3 predecessor:** [`../Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md`](../Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md)
**Acceptance successor:** [`../Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md`](../Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md)
**Harness:** `scripts/compare_direct_dungeonmind_world_graph_reads.py` (local runner; private JSON output is never committed)
**Status:** R.3a pin rerun sealed — **0 blocking, 0 errored, 199 approved**; `SWITCH_READY`; production direct-read gate remains default-off

> **Historical 199 and frozen V4 200 are obsolete as acceptance numbers.**
> 199 was measured against corrupted V3 adopted-source state. The 2026-08-23
> V4 vocabulary-v1 witness in §2A recorded **200 blocking** plus two errored
> cases against the retired Buddy kernel. The current acceptance record is
> §2B (2026-08-24 vocabulary v2): **0 blocking, 0 errored**, with remaining
> Buddy-kernel differences counted as `approved semantic divergence`. The
> production direct-read gate remains default-off.

---

## 1. What this is

R.3 moves production World Graph reads from Buddy's hydrated graph kernel to
DungeonMind's native R.1/R.2 read services behind a thin DTO adapter. This
document is the durable, safe-aggregate record of the two witnesses the
handoff requires:

1. **Semantic parity witness (§6)** — the same logical reads executed through
   the legacy hydrated path (oracle) and the direct DungeonMind path against
   the real current adopted world, with every divergence classified per the
   handoff's §6.3 vocabulary.
2. **Real-current performance witness (§7)** — aggregate latencies for the
   operation set on both paths against the same exact revision.

The R.2a synthetic scaling baseline
(`Docs/Benchmarks/BASELINE-world-graph-reads-r2a.md` in the DungeonMind repo)
is unchanged by this document; R.2a measured synthetic graphs with in-memory
repositories, while this witness measures the real product graph against
PostgreSQL.

## 2. Subject and environment

```text
world:                    eldyrwild (real adopted world)
DungeonMind first rev:    D_A = rev:34b1f8e2625d5ba693fc726a2a1a4720
DungeonMind head:         D_B = rev:680c246047d67f9fe0293ee90526f670
legacy Buddy revision:    A  = rev:0c644e56b45bcaac709012206e3e41c2
receipt:                  V4; M0 538195e3… preserved; M1 16d3161d… served
manifest:                 83 / 83 / 93 / 13
authority store:          PostgreSQL dungeonmind_cutover_live @ localhost dev container
legacy store:             frozen Buddy store + hydrated cache
host:                     Linux dev machine, uv-managed Python 3.13
direct-read gate:         default off in production; witness process opts in
```

## 2A. Fresh V4 witness — 2026-08-23 stop point

Identity preflight (same live authority for both paths):

```text
receipt schema:     dm_existing_world_adoption_receipt_v4
M0:                 538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
M1 (served):        16d3161d270691460ccbf6d183055ad9f29f00bdbecf5c26dfe0189da2b9914e
D_A:                rev:34b1f8e2625d5ba693fc726a2a1a4720
head D_B:           rev:680c246047d67f9fe0293ee90526f670
Buddy A:            rev:0c644e56b45bcaac709012206e3e41c2
```

17 cases. 2 errored. No invented classification classes.

| §6.3 class | count | meaning |
|---|---|---|
| blocking semantic difference | **200** | see breakdown below |
| representation only | 2,345 | same class as the historical V3 witness |
| intentionally retired legacy-only field | 1,056 | same class as the historical V3 witness |
| new deterministic R.2 search ranking | 2 | search node-set selection |
| product-local presentation join | *(absent)* | the historical 1-row anchor case errored before classification |

### Blocking breakdown (frozen vocabulary only)

| kind | rows | unique ids | class |
|---|---|---|---|
| `evidence_only_in_legacy` | 166 | 99 | **blocking** — DungeonMind fail-closed per-evidence-chain admission vs Buddy kernel object-only scoping |
| `attribute_only_in_legacy` | 27 | 9 threat subjects | **blocking** — v6 adoption `properties=[]`; legacy reconstructs threat attributes from contributions |
| `node_only_in_legacy` | 6 | 2 objects | **blocking** — `location:mireward` (c1/pin lenses); `node:cutover-canary` (c2/world lenses; missing source artifact) |
| `error_envelope` | 1 | PLAYER case | **blocking** — legacy `unsupported_admissibility`, direct `served` |

The 200 is **not** a new semantic universe. It is the historical 199-class residual, re-measured against repaired V4:

- Evidence-chain tightening remains the bulk (was 169 rows; now 166). Unique evidence is 99 ids, mostly c1 recap chains plus mixed corpus / tpub / graph-review / two c2 recap rows.
- Unrepresented v6 properties remain exactly 27.
- `node:cutover-canary` remains a data-integrity exclusion on the direct path (3 lenses).
- `location:mireward` is newly counted as a node exclusion under c1/pin (3 lenses). That is the same fail-closed evidence-chain rule, now visible as an object drop rather than only as missing evidence rows.
- PLAYER envelope is newly blocking at 1: review-cycle-1 taught the direct adapter to serve PLAYER; the harness case is still named `player-rejected` and the legacy kernel still rejects PLAYER.

### Errored cases (not classified, not ignored)

1. `neighborhood:depth-2` — **legacy oracle** `KeyError: 'item_enormous_boulder'`. Direct path returned a result. This is a Buddy-kernel oracle failure, not a DungeonMind-read miss.
2. `anchor:emit-revalidate-open` — **direct path** `DirectWorldGraphReadError: Unexpected failure in the direct DungeonMind read path.` The historical presentation-join row was not produced because this case never compared.

### Performance (1 run; characterization only)

```text
projection            legacy  1665 ms    direct 20653 ms
object                legacy 16176 ms    direct 20012 ms
search                legacy 16352 ms    direct 20400 ms
neighborhood:depth-1  legacy 18239 ms    direct 20465 ms
neighborhood:depth-2  legacy ERROR       direct 20133 ms
evidence              legacy 16419 ms    direct 20275 ms
```

The §7 decision rule still holds: direct `scope_projection` remains ~20s and product-breaking relative to warm hydrated projection. `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` stays default-off. R.3a remains the named successor for that cost. Do not flip the gate from this witness.

### What this does *not* authorize

The repair did not take 199 → 0 or 199 → a small adapter residue. Remaining rows are still visibility / provenance / scope / missing-data differences against the retired Buddy kernel. This baseline does **not** invent a sixth classification class; that versioning belongs to [`../Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md`](../Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md), which redesigns R.3 "parity" into a supported-client API contract.

Until that design is accepted, do not:

- reclassify the 200 blocking rows;
- restore Buddy object-only admission or reconstructed `properties`;
- enable `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ`.

Private JSON (never commit): operator-local `r3-v4-parity-witness.json` beside the 2026-08-23 live-repair backup.

### 2B. Vocabulary-v2 sealed supported-contract witness — 2026-08-24

The first v2 run on head `23834205…` reported 0 blocking / 0 errored, but Review Cycle 2 rejected that proof: the classifier approved by broad shape. This section is the **sealed-ledger rerun** against the same repaired V4 authority. Unknown identities default blocking.

Ledger: `scripts/r3_v2_ratified_divergence_ledger.json`
(`dmb_r3_v2_approved_semantic_divergence_ledger_v1`; 6 node-drop contexts, 9 subject/kind properties, 99 evidence ids / 166 case rows).

Identity preflight (same live authority):

```text
receipt schema:     dm_existing_world_adoption_receipt_v4
M0:                 538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
M1 (served):        16d3161d270691460ccbf6d183055ad9f29f00bdbecf5c26dfe0189da2b9914e
D_A:                rev:34b1f8e2625d5ba693fc726a2a1a4720
head D_B:           rev:680c246047d67f9fe0293ee90526f670
Buddy A:            rev:0c644e56b45bcaac709012206e3e41c2
vocabulary:         v2 (sealed identities/contexts)
```

17 cases. **0 errored. 0 blocking semantic difference.**

| class | count | meaning |
|---|---|---|
| blocking semantic difference | **0** | no unresolved supported-contract violation |
| approved semantic divergence | **199** | exact ratified evidence-chain rows, Mireward c1/pin only, 9 retired subject/kind properties, cutover-canary c2/world lenses |
| representation only | 2,345 | unchanged |
| intentionally retired legacy-only field | 1,056 | unchanged |
| new deterministic R.2 search ranking | 2 | unchanged |
| product-local presentation join | 1 | `anchor:emit-revalidate-open` — direct `enough`, legacy `empty` |

PLAYER (`admissibility:player-served`): direct **served**; 0 PLAYER nodes; DungeonMind existence visibility classifies **390 GM-only** objects; PLAYER ∩ GM-only = ∅; unknown admissibility `unsupported_admissibility`. Legacy still rejects PLAYER; that envelope is not blocking.

Depth-2: native returned a coherent neighborhood. Legacy oracle `KeyError: 'item_enormous_boulder'` recorded in `legacy_counts`, not as an errored supported operation.

Anchor: **Case A — adapter / product-local join.** After DungeonMind revalidation, recap spans are sliced from digest-pinned **parent** bytes (`…:paragraph:NNN` or digest-prefixed line range). Sidecar files and `source_span_index.json` are unbound and are not served.

Performance (1 run; characterization only):

```text
projection            legacy  1690 ms    direct 20733 ms
neighborhood:depth-2  legacy ERROR       direct 20580 ms
```

`DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` stays default-off. R.3a remains the named successor for that cost.

Private JSON (never commit): operator-local `/tmp/r3-v4-cycle2-sealed-witness.json`.

### 2C. R.3a Buddy pin rerun — 2026-08-24

DungeonMind PR #45 merge `c5d3688587b0f5d506e0f7d64f33eb0628bac896` (R.3a
read-context optimization). Same live authority, same sealed v2 ledger, same
17 cases. Private JSON: `/tmp/r3a-buddy-pin-witness.json` (never commit).

Identity preflight unchanged from §2B.

17 cases. **0 errored. 0 blocking semantic difference.**

| class | count | meaning |
|---|---|---|
| blocking semantic difference | **0** | sealed R.3 contract unchanged by #43 → #45 |
| approved semantic divergence | **199** | exact §2B tally |
| representation only | 2,345 | unchanged |
| intentionally retired legacy-only field | 1,056 | unchanged |
| new deterministic R.2 search ranking | 2 | unchanged |
| product-local presentation join | 1 | unchanged |

Performance through **Buddy's adapter** (`direct_services_from_config` + DTO
mapping), not DungeonMind's own harness. Witness reuses one service object
(parsed-revision cache can hit). Medians of 3:

```text
projection            legacy  1840 ms    direct  548 ms
object                legacy 17150 ms    direct  142 ms
search                legacy 17210 ms    direct  155 ms
neighborhood:depth-1  legacy 17884 ms    direct  226 ms
neighborhood:depth-2  legacy ERROR       direct  120 ms
evidence              legacy 17304 ms    direct  161 ms
```

Product path currently constructs a new service bundle per request. Separate
lifecycle sample on the same campaign-GM projection (390 nodes):

```text
factory-only                         72 ms median
rebuild factory every projection    845 ms median
reused services                     754 ms median  (cache hits=2 misses=1)
```

Factory rebuild is not the remaining cost. Parsed-revision reuse saves ~90 ms.
Buddy DTO mapping of the admitted graph dominates. Sub-second product
projection vs the previous ~20.7 s direct path is enough to dogfood.

Disposition: `SWITCH_READY`. `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` stays
default-off in this PR. Local dogfood may set it to `1` after merge.

## 3. Semantic parity witness (HISTORICAL — corrupted V3 authority)

The tally in this section is the pre-repair witness. It is retained as
incident evidence, not as the current blocker count.

17 cases (handoff §6.1): head projection under campaign c1 / campaign c2 /
world-cross-campaign GM lenses, world-scope + campaign-qualified session
focus (the Plan seam), exact DungeonMind pin, legacy A→D_A bridge pin, exact
object hit/miss, lexical search with a known referent, search with explicit
seeds, depth-1/depth-2 neighborhood, evidence for object and relationship,
anchor emit → revalidate → open, PLAYER admissibility, and unknown-campaign
fail-closed.

### 3.1 Divergence tally (all cases)

| §6.3 class | count | meaning |
|---|---|---|
| blocking semantic difference | **199** | evidence-chain scope tightening (169); property assertions not represented in v6 payload (27); data integrity issue (3) |
| representation only | 2,345 | `dnd5e:` vocabulary prefix strip, v6 predicate/kind normalization, dual-sense direction canonicalization, legacy label-echo alias default retired, direct-path outcome strictly more complete than legacy |
| intentionally retired legacy-only field | 1,056 | `session_observation` history-only attribute rows; legacy kernel dangling edges; kernel projectability-filtered nodes; `external_resource` statblock-external nodes and their `uses_statblock` edges (handoff §D) |
| new deterministic R.2 search ranking | 2 | search node-set selection differs within the same admitted projection |
| product-local presentation join | 1 | anchor content-join availability (revalidation identity itself compares exactly) |

**199 blocking semantic differences remain.** The handoff prohibits normalizing
away visibility, provenance, scope, identity, or missing-data differences.
These divergences require either correction or an explicit design-review
change; implementation cannot expand its own acceptance vocabulary.

### 3.2 What compares exactly

Per §6.2: selected revision/head identity, `is_head`, scope/admissibility,
admitted object identity, labels, admitted aliases (after retiring the legacy
kernel's label-echo default — see below), relationship identity/endpoints
(modulo the classified vocabulary/direction normalization), evidence identity
and admitted provenance, visibility/admissibility outcomes, exact seed
preservation, missing/denied behavior, and historical pin behavior all compare
equal between the paths.

### 3.3 Blocking divergences (require correction or design-review change)

**Evidence-chain scope tightening (169 divergences).** DungeonMind's native
read path validates **every evidence chain** under the read's campaign scope;
Buddy's legacy kernel scoped objects but never evidence chains. Under the c1
campaign lens this excludes world-universal objects whose supporting artifacts
were adopted with a c2 campaign assignment. The handoff prohibits normalizing
away provenance/scope differences, so these are blocking semantic differences.

**Property assertions not represented in v6 payload (27 divergences).** The
v6 adoption set `properties=[]` for every object; legacy reconstructs threat
attributes from contributions. The handoff prohibits normalizing away
missing-data differences, so these are blocking semantic differences.

**Data integrity issue (3 divergences).** `node:cutover-canary` references a
source artifact that does not exist in the repository; direct path correctly
excludes, legacy kernel serves because it never validates evidence chains.
The handoff prohibits normalizing away missing-data differences, so these are
blocking semantic differences.

### 3.4 Historical V3 contract violation (closed by governed repair)

The Buddy data migrations directly mutated `source_artifacts` and rewrote the
V3 receipt's `membership_sha256`. That class of mutation is retired. The
governed repair is DungeonMind PR #43 plus the 2026-08-23 live Eldyrwild
apply. The Buddy mutation scripts are deleted.

### 3.5 Historical stop condition: 199 blocking semantic differences

The pre-repair witness reported **199 blocking semantic differences** (169
provenance/scope, 27 missing property-assertion, 3 broken-evidence-chain)
against corrupted V3 state. That number is not the current acceptance
baseline. R.3 continuation stops on the fresh V4 witness, then classifies
whatever remains with the frozen §6.3 vocabulary.

### 3.6 Representation-only differences (wire-visible, non-blocking)

- **Vocabulary prefix:** the v6 adoption namespaced every kind/predicate
  (`dnd5e:located_in`); the adapter strips the prefix so mounted consumers see
  the legacy vocabulary.
- **Predicate/kind normalization:** the adoption mapped free-form Buddy terms
  into the DND vocabulary (e.g. `within → located_in`); both paths name the
  same edges, with the successor's normalized terms on the wire.
- **Dual-sense direction:** dual-sense pairs (Buddy package #588) are served
  in the one canonical adopted direction (e.g. `leads`), where the legacy
  kernel served both senses (`leads` + `part_of`).
- **Label-echo aliases:** the legacy kernel defaulted a node's alias list to
  `[label]` when no alias was declared; the direct path serves the payload's
  explicit governed aliases only (verified: all 384 shared c1 nodes differ
  only by the echo; governed alias packages such as `Captain` serve exactly).
  No read-path product surface consumes the echo (alias consumers are all
  write-side authoring services).

### 3.7 Known legacy oracle defect surfaced

`neighborhood:depth-2` on the legacy path raises
`KeyError: 'item_enormous_boulder'` — the legacy kernel selects a node its own
projection does not contain. Recorded as witness data; the direct path serves
the case normally. This is one more instance of the legacy kernel's
consistency gaps the cutover retires.

### 3.8 Property assertions not represented in the v6 payload

The v6 adoption bundle producer
(`integrations/dungeonmind_kernel/eldyrwild_existing_world_adoption_bundle_v2.py`)
sets `properties=[]` for every `GraphObjectV6Record` — the adoption captured
the graph structure (objects, relationships, evidence) but not object
property assertions. The legacy kernel reconstructs these from contributions
(e.g. threat `description`, `threat_kind`, `battlefield_role`), so the legacy
projection serves 27 attribute rows the direct path cannot.

Handoff §6.2 requires "property assertion identity/value/metadata **where
represented**" — unrepresented assertions have nothing to compare against, so
these are classified as `property assertions not represented in v6 payload`
rather than blocking. If product surfaces need these attributes, the fix is a
successor adoption-bundle revision that populates `properties` from the
contribution payloads, not an adapter change.

### 3.9 Data integrity issue surfaced

`node:cutover-canary` is present in the DungeonMind authority payload but its
evidence chain references a source artifact
(`artifact:recap:longmont-c2:session-26-cutover-live-canary`) that does not
exist in the source repository. DungeonMind's fail-closed admission correctly
excludes it (`scope_unknown`); the legacy kernel serves it because it never
validates evidence chains. This is a pre-existing data integrity issue in the
authority store, not a read-path defect — the direct path is strictly more
correct here.

## 4. Performance witness (§7)

Median milliseconds per operation, same revision, both paths (cold = first
run of the process):

| operation | legacy (median) | legacy cold | direct (median) | direct cold |
|---|---|---|---|---|
| projection | 1,597 | 1,651 | 20,739 | 20,256 |
| exact object | 16,449 | 16,375 | 19,968 | 19,392 |
| search | 16,126 | 16,126 | 20,212 | 19,976 |
| neighborhood depth-1 | 17,436 | 17,436 | 20,937 | 20,937 |
| neighborhood depth-2 | ERROR (§3.5) | — | 20,598 | 20,598 |
| evidence | 16,273 | 16,273 | 20,547 | 20,307 |

### 4.1 Interpretation

- **The legacy projection row is the warm-cache outlier, not the norm.** The
  legacy projection *endpoint* benefits from the Buddy resident runtime +
  projection cache (1.6s warm). Every legacy *retrieval* operation re-projects
  per call and costs 16–17s — the same order as the direct path's ~20s.
- **The direct path is uniformly ~20s** because every read nests a full
  projection, and DungeonMind's `scope_projection` phase performs
  evidence-chain admission with per-row source-repository round-trips against
  PostgreSQL. R.2a's phase observability attributes this precisely on the real
  world: `scope_projection` = 20.1s of a 20.2s projection (99.6%);
  `head_lookup` 9ms, `revision_load` 50ms, `parse` 12ms.
- **§7 decision rule: triggered and answered.** The direct path is
  product-breaking on the warm-projection surface (20.7s vs 1.6s), and at
  rough parity (1.2–1.3×) on the retrieval surfaces where the legacy path
  also pays full projection cost. Per the handoff:

  ```text
  semantic parity NOT proven (199 blocking divergences)
  → preserve R.3 witness (this document + the harness)
  → dispatch R.3a optimization before the production switch
  → fix blocking divergences before treating the witness as trustworthy
  ```

  R.3a (reusable World Graph read context / parsed immutable revision reuse +
  batched source-provenance reads) is the named successor. The R.3 dispatch is
  env-gated (`DUNGEONMIND_WORLD_GRAPH_AUTHORITY=dungeonmind`); merging R.3 does
  not change production behavior until that switch flips, and the switch waits
  for R.3a.

### 4.2 Regression oracle going forward

The R.3 harness and this normalized witness are the post-cutover regression
oracle. R.3a compares `R.3 direct result == R.3a optimized direct result`;
Buddy hydration is not required to remain live to preserve the oracle.

## 5. Static inventory: surviving `graph_memory` kernel consumers

After R.3, 36 production modules under `apps/` still import
`graph_memory.kernel`. Every survivor is one of:

| retirement category | modules | fate |
|---|---|---|
| Read path — legacy branch only | `services/world_graph_projection.py`, `services/world_graph_retrieval.py` | Dispatched around in `dungeonmind` mode; the branch remains for non-DND modes and explicit test roots. Deleted with the legacy authority modes. |
| Read-path warmers — no-op in DND mode | `services/world_graph_prewarm.py`, `services/world_graph_projection_recipes.py` | Gated inert by R.3; deleted with the legacy read path. |
| Product-local content join (shared by both paths) | `services/worldbuilding_source_span_read.py` | Not kernel truth — registry/file presentation reads. Evacuated to a product utility when the kernel is deleted. |
| Governed write/review compatibility | `integrations/dungeonmind_kernel/world_graph_authority.py`; write pipeline `services/extract_promote.py`, `models/extract_promote.py`, `services/first_world_graph.py`, `services/world_graph_bootstrap.py`, `services/graph_review_contribution_merge.py`; governed packages `services/threat_publication_*` (4), `services/c1_world_graph_additive_apply.py`, `services/eldyrwild_*` corrections (7), `services/cutover_*` (6) | The legitimate temporary consumer R.3 deliberately preserves. Retired by the write-side successor that removes graph reconstruction from review/apply. |
| Adoption conformance tooling | `integrations/dungeonmind_kernel/` conformance modules (7) | Historical migration tooling; deleted with the adoption-era machinery. |
| Pure helpers | `src/graph_memory/interaction/digest_audit.py` (hash helper import) | Trivial to evacuate. |

The direct adapter itself (`integrations/dungeonmind/world_graph_reads.py`)
imports only Buddy wire DTOs (`graph_memory.projection.world_projection`,
`graph_memory.retrieval.models`) and the pure source-reader helpers
(`graph_memory.retrieval.source_reader`) — never `graph_memory.kernel`. Those
DTO/helper modules are product contracts to evacuate (not delete) at final
demolition.

The Hermes interaction stack (`graph_memory.interaction.expansion_executor`)
already reads through the retrieval *service*, so it inherits the direct
dispatch without its own kernel dependency (proven by
`tests/test_live_query_hermes_graph.py::test_hermes_expansion_tool_executes_via_direct_dungeonmind_read`).

## 6. Warnings and limitations

- Single host, single world, dev-local PostgreSQL container; absolute numbers
  are environment-specific. The phase attribution (§4.1) is the durable
  finding.
- 3 runs per operation; medians of 3. The direct path shows no warm/cold
  spread because it is stateless per read; the legacy path's warm projection
  row reflects its resident cache.
- The private JSON report (object/evidence identifiers, query text) is local
  operator output under `/tmp` and is intentionally not committed; this
  document carries safe aggregates only.
- The legacy oracle is the pre-R.3 service path (authority route + kernel),
  exercised through the current service modules' legacy helpers.

## 7. Reproduce

```bash
uv run python scripts/compare_direct_dungeonmind_world_graph_reads.py \
  --database-url "$DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL" \
  --world-id eldyrwild \
  --frozen-root /path/to/repo/out \
  --repo-root /path/to/repo \
  --runs 3 \
  --output /tmp/r3-witness.json   # local only; never commit
```

Expect ~15–20 minutes, dominated by per-read projection cost on both paths.
Exit code is non-zero iff any blocking semantic difference remains.
**Fresh V4 status (2026-08-23): 200 blocking divergences; 2 errored cases.
Historical V3 status: 199. Do not carry 199 forward as fact.**

## 8. Stop condition

R.3 continuation stops on the fresh V4 parity witness against:

- receipt V4
- M1 `16d3161d270691460ccbf6d183055ad9f29f00bdbecf5c26dfe0189da2b9914e`
- current D_B `rev:680c246047d67f9fe0293ee90526f670`
- the same live authority for both hydrated and direct paths
- `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` default-off in production; the
  witness process opts in for the direct side only

Classify every remaining divergence with the frozen handoff §6.3 vocabulary.
Do not pre-authorize implementation to "fix whatever remains" before that
evidence is inspected.
