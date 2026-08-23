# BASELINE — R.3 direct DungeonMind current-world read witness

**Date:** 2026-08-22
**Branch:** `cutover/direct-dungeonmind-production-reads`
**Handoff:** [`../Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md`](../Plans/HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md)
**Harness:** `scripts/compare_direct_dungeonmind_world_graph_reads.py` (local runner; private JSON output is never committed)
**Status:** characterization witness, not an SLO and not a merge gate

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
DungeonMind revision:     D_A = rev:34b1f8e2625d5ba693fc726a2a1a4720 (head)
legacy Buddy revision:    A  = rev:0c644e56b45bcaac709012206e3e41c2
graph shape (parsed):     470 objects / 323 relationships / 185 evidence rows
authority store:          PostgreSQL dungeonmind_cutover_live @ localhost dev container
legacy store:             frozen Buddy store + hydrated cache (out/)
host:                     Linux dev machine, uv-managed Python 3.13
runs per operation:       3 (median reported; cold = first run)
```

Data migrations applied to the live database as part of R.3 (both idempotent,
both recompute the tamper-evident artifact fingerprints and the adoption
receipt's `membership_sha256`):

- `scripts/migrate_adopted_source_artifact_visibility.py` — adopted source
  artifacts `visibility NULL → gm`. DungeonMind's fail-closed scope gate
  excludes v2 artifacts with unset visibility; Buddy's legacy kernel only ever
  served GM reads, so GM is the faithful classification.
- `scripts/world_own_worldbuilding_source_artifacts.py` — two session-less
  worldbuilding corpus documents re-assigned from `longmont-c2` to world
  ownership (`campaign_id = NULL`), their correct semantic classification.

## 3. Semantic parity witness

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
| blocking semantic difference | **0** | — |
| representation only | 2,345 | `dnd5e:` vocabulary prefix strip, v6 predicate/kind normalization, dual-sense direction canonicalization, legacy label-echo alias default retired, direct-path outcome strictly more complete than legacy |
| intentionally retired legacy-only field | 1,056 | `session_observation` history-only attribute rows; legacy kernel dangling edges; kernel projectability-filtered nodes; `external_resource` statblock-external nodes and their `uses_statblock` edges (handoff §D) |
| successor_admission_semantics_accepted | 169 | evidence-chain scope tightening residual (see §3.3); cross-campaign evidence chains excluded by DungeonMind's fail-closed per-evidence-chain admission |
| property assertions not represented in v6 payload | 27 | v6 adoption set `properties=[]` for every object; legacy reconstructs threat attributes from contributions (§3.6) |
| new deterministic R.2 search ranking | 2 | search node-set selection differs within the same admitted projection |
| data integrity issue (broken evidence chain) | 3 | `node:cutover-canary` references a source artifact that does not exist in the repository; direct path correctly excludes, legacy kernel serves because it never validates evidence chains |
| product-local presentation join | 1 | anchor content-join availability (revalidation identity itself compares exactly) |

No blocking semantic differences remain after classification.

### 3.2 What compares exactly

Per §6.2: selected revision/head identity, `is_head`, scope/admissibility,
admitted object identity, labels, admitted aliases (after retiring the legacy
kernel's label-echo default — see below), relationship identity/endpoints
(modulo the classified vocabulary/direction normalization), evidence identity
and admitted provenance, visibility/admissibility outcomes, exact seed
preservation, missing/denied behavior, and historical pin behavior all compare
equal between the paths.

### 3.3 The accepted residual (reviewed during R.3)

DungeonMind's native read path validates **every evidence chain** under the
read's campaign scope; Buddy's legacy kernel scoped objects but never evidence
chains. Under the c1 campaign lens this excludes a small set of
world-universal objects whose supporting artifacts were adopted with a c2
campaign assignment. The reviewed resolution:

- The two session-less worldbuilding corpus documents were world-owned by
  migration (§2), which restored the genuinely world-universal objects they
  support (e.g. the primary city location) under c1 reads.
- One object whose remaining evidence is genuine c2 session chronology stays
  excluded under c1 (`location:mireward`, with its dependent edges/evidence —
  the 15 accepted-residual divergences). This is the intended fail-closed
  successor semantics, explicitly accepted in review.

The same tightening also retired a legacy kernel inconsistency the witness
surfaced: the legacy c1 projection served edges whose endpoints it did not
itself admit (dangling edges, e.g. to player characters it had excluded).

### 3.4 Representation-only differences (wire-visible, non-blocking)

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

### 3.5 Known legacy oracle defect surfaced

`neighborhood:depth-2` on the legacy path raises
`KeyError: 'item_enormous_boulder'` — the legacy kernel selects a node its own
projection does not contain. Recorded as witness data; the direct path serves
the case normally. This is one more instance of the legacy kernel's
consistency gaps the cutover retires.

### 3.6 Property assertions not represented in the v6 payload

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

### 3.7 Data integrity issue surfaced

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
  semantic parity proven
  → preserve R.3 witness (this document + the harness)
  → dispatch R.3a optimization before the production switch
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
Exit code is non-zero iff any unclassified (blocking) divergence remains.
