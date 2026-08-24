---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / R.3 — ratify DungeonMind ↔ Buddy graph-read contract
  - Direction: EVIDENCE → DESIGN → CODE
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-r3-read-contract-ratification.md
  - Implementation repository: Drakosfire/DungeonMindBuddy

  ## Exact predecessor truth
  - Live Eldyrwild authority is governed V4 (M1 `16d3161d…`, head `rev:680c246…`).
  - Buddy #630 is merged; #629 mechanical predecessor is `24250fb0` (pushed); Cycle 4 reviewed frozen head `bba098fc9aed68630caadc1e89b4c84639562862`.
  - Fresh repaired-authority witness: 200 blocking rows + 2 errored cases.
  - Direct-read gate remains default-off.

  Replace zero-difference Buddy-kernel parity as the R.3 merge criterion with an
  explicit supported-client API contract. Do not implement broad compatibility
  fixes in the same slice.
---

# HANDOFF — R.3: ratify the DungeonMind ↔ DungeonMindBuddy graph-read contract

**Created:** 2026-08-23  
**Status:** ACTIVE — design/acceptance; not implementation authorization  
**Workstream:** CUTOVER / World Graph runtime retirement  
**Direction:** EVIDENCE → DESIGN → CODE  
**Implementation repository:** `Drakosfire/DungeonMindBuddy`  
**Active implementation PR (frozen until this is accepted):** Buddy #629  
**Required DungeonMind pin:** `519b2c96fc42d22f3113cc9ca0d48bc70b6780e5` (#43)  
**Evidence:** [`Docs/Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md`](../Benchmarks/BASELINE-r3-direct-dungeonmind-current-reads.md) §2A  
**Predecessor implementation handoff:** [`HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md`](HANDOFF-CUTOVER-direct-dungeonmind-production-reads.md)  
**Named successor after acceptance:** narrow #629 resume (genuine defects + witness vocabulary), then R.3a

> Supporting DungeonMindBuddy as a current client does not require preserving
> obsolete Buddy kernel semantics, representations, bugs, or compatibility
> behavior that the architecture has intentionally replaced.

---

## 1. Why this document exists

The old R.3 framing — *direct reads must reach zero semantic differences
against the Buddy kernel* — is no longer a sufficient merge criterion.

The live V4 repair made Eldyrwild authority trustworthy. The fresh witness
against that authority is **200 blocking rows**, not 0. Most of those rows are
not lost product capabilities. They are the Buddy kernel disagreeing with
intended DungeonMind admission and with an adoption payload that never
materialized contribution-reconstructed attributes.

This document replaces zero-difference parity with an explicit **supported
client/API contract**. Legacy comparison remains archaeology, regression
discovery, and data-integrity detection. It is not a requirement to recreate
old behavior.

No compatibility implementation is authorized by this file until a steward
accepts it.

---

## 2. Locked predecessor facts

Do not reopen these:

```text
receipt          dm_existing_world_adoption_receipt_v4
M0               538195e399158bfb4fafce01f9c5af3c63e2137f70694fdead7a26e5800e0890
M1               16d3161d270691460ccbf6d183055ad9f29f00bdbecf5c26dfe0189da2b9914e
manifest         83 / 83 / 93 / 13
D_A              rev:34b1f8e2625d5ba693fc726a2a1a4720
head D_B         rev:680c246047d67f9fe0293ee90526f670
Buddy frozen A   rev:0c644e56b45bcaac709012206e3e41c2
DIRECT_READ      default-off
```

#629 mechanical predecessor is `24250fb0` on the **pushed** branch
`cutover/direct-dungeonmind-production-reads` (rebase onto #630, drop
`c3e57d9f`, #43 pin, delete illegal Buddy mutation scripts,
process-order-safe hydrated-route test, fresh V4 baseline). That commit is
not local-only. The ratification design commit
`bba098fc9aed68630caadc1e89b4c84639562862` is the Cycle 4-reviewed
pushed-but-frozen PR head. Direct reads stayed off. Implementation remains
frozen; do not resume #629 code in this docs cycle.

---

## 3. What DungeonMind promises current Buddy

These are the graph-read capabilities current DungeonMindBuddy product
surfaces still require. DungeonMind must expose them through the landed
R.1/R.2 APIs. Buddy may adapt wire shape. Buddy may not reconstruct a graph
to recover them.

| Capability | Current Buddy consumers | Contract |
|---|---|---|
| Head and exact-pin projection | Plan, Build, graph lens, Hermes/agent query context | One exact DungeonMind revision; `world` = `WORLD_CROSS_CAMPAIGN`; campaign scope is campaign |
| Exact object lookup | graph reference chips, object cards, Hermes object tool | Hit/miss/denied fail closed |
| Search / referent resolution | Plan/Build reference, agent query | Ranked search over the **admitted** projection |
| Neighborhood depth-1 and depth-2 | Hermes expansion, graph inspection | Native R.2 neighborhood; no Buddy kernel |
| Evidence retrieval | Plan evidence, Hermes evidence, source follow-through | Evidence that survives DungeonMind admission |
| Source-anchor emit → revalidate → open | Plan/Build source span, Hermes source citations | DND revalidation, then product-local content join |
| GM admissibility | every mounted surface today | Default product lens |
| PLAYER admissibility | typed retrieval/projection contracts; not yet a mounted UI lens | Supported API: serve PLAYER, hide GM-only, fail closed on unknown |
| Campaign / world / cross-campaign scope | Plan world-scope + campaign-qualified session focus | Scope is admission; session focus is presentation only |
| A→D_A pin bridge | historical pin consumers | Receipt-backed; frozen Buddy store never read on the direct path |

This list is the supported client contract. It is not “whatever the Buddy
kernel used to emit.”

---

## 4. Semantic rules that belong to DungeonMind

These rules are DungeonMind’s, not Buddy’s. Buddy adapts to them.

1. **Per-evidence-chain fail-closed admission.** An object, relationship, or
   evidence row is admitted only when every supporting evidence chain is in
   the requested campaign/visibility scope. Object-only scoping is retired.
2. **GM / PLAYER closed vocabulary.** Unknown admissibility fails closed.
   PLAYER does not leak GM-only rows.
3. **Exact published revision identity.** Returned revision ids are
   re-pinnable DungeonMind ids. Hydrated Buddy revision ids are private.
4. **Adopted membership is V4 M1 / manifest**, with historical M0 preserved.
   Direct reads must not recompute membership from the frozen store.
5. **Source-anchor admission is DungeonMind’s.** Product-local file opening
   is a non-authoritative join after revalidation, digest-pinned.
6. **v6 payload truth.** Direct reads serve the adopted/published graph, not
   contribution-replay reconstructions.

---

## 5. Rulings on the fresh V4 witness

Classification key:

```text
A  supported client/API contract break   → fix API, DND, or adapter
B  intentional semantic replacement      → Buddy adapts; DND does not emulate Buddy
C  retired implementation residue        → archive; do not migrate
D  independent data-integrity defect     → governed data repair, not parity
```

Witness vocabulary after this document is accepted is **v2**. Keep the
existing five §6.3 classes, and add:

```text
approved semantic divergence
```

Use that class only for differences this file ratifies. Do not silently
relabel blocking rows as `representation only` or
`intentionally retired legacy-only field`.

### 5.1 Evidence-chain admission — 166 rows + `location:mireward` under c1/pin

**Ruling: B — DungeonMind semantics win. Approved semantic divergence.**

Per-evidence-chain admission is the intended provenance model. Do not
recreate Buddy object-only admission in DungeonMind or in the adapter.

Product check (current mounted GM surfaces):

| Lens | `location:mireward` | Meaning |
|---|---|---|
| campaign c1 / c1 pins | dropped on direct | Correct. Mireward is C2 content; c1 recap/corpus chains do not make it a c1-admitted object |
| campaign c2 | present | C2 Plan/Play keep Mireward |
| world / world+session-focus | present; direct has **more** objects than legacy (469 vs 466) | World inspection is not starved |

Shorter evidence lists under a campaign lens are the product-correct
fail-closed outcome, not a lost Plan/Play/Hermes capability. Session focus
remains presentation: the direct adapter already recomputes focus flags from
admitted provenance (witness: 22 focus-anchored nodes on direct vs 0 on
legacy for the Plan seam).

**Do not** modify DungeonMind to emulate object-only scoping.

### 5.2 `properties=[]` — 27 rows / 9 unique attributes

**Ruling: C — retired adoption reconstruction. No DungeonMind prerequisite now.**

The 9 unique attributes sit on four threat nodes:

```text
threat:authored:42bd2bd2…   description, threat_kind=creature
threat:authored:d16d43d3…   description (Mireward Latchling), threat_kind=creature
threat:authored:d60f9863…   description (Meat Mind), threat_kind=creature
threat:tripod-null-calf     battlefield_role, challenge_expectation, first_appearance
```

They exist on the legacy path because the Buddy kernel reconstructs
contribution property assertions. The v6 adoption recorded
`properties=[]` for every object.

Current consumer check:

| Surface | Reads `projection.attributes` for these fields? |
|---|---|
| Plan / Build graph object cards | No. `selectedObjectCardModel` reads **corpus index** records |
| Graph lens / native object inspection | No attribute rendering in current graphLens/selectedObject readers |
| Play native threat / statblock | Separate threat-publication and statblock domain, not these adopted attributes |
| Hermes tools | No predicate-keyed consumption of these 9 fields |
| Agent query-context panel | Displays attributes **if present**; omits the section when empty |
| Threat publication identity/commit | Uses attributes for **newly authored** publications and advisory ranking; does not require adopted empty `properties` to be backfilled |

Object identity, label, kind, aliases, and evidence remain on the direct
path. `threat_kind=creature` duplicates node kind. Descriptions are
recoverable from admitted source evidence, not from a Buddy attribute row.

Do **not** restore Buddy `properties` layout. If a later named product
consumer needs Tripod battlefield role (or equivalent) as **authority
data**, dispatch a bounded DungeonMind materialization for that named
field — not a general parity backfill.

### 5.3 `node:cutover-canary`

**Ruling: C, with a D footnote. Retire as product data.**

The node is the first post-cutover mutation proof (`D_B` child of `D_A`).
It is not campaign content. Direct exclusion is because its evidence chain
points at a source artifact that does not exist. Do not manufacture
provenance so a migration canary stays queryable.

Keep `D_B` / parent `D_A` as operational history. Stop treating the canary
node as a live graph-read requirement.

### 5.4 PLAYER envelope — 1 row

**Ruling: A for the API, C for the witness case name.**

The supported contract is: PLAYER requests are served; GM-only material is
hidden; unknown admissibility fails closed. The direct adapter already does
this. Current mounted UI sends `admissibility: "gm"` only; PLAYER remains a
typed API capability.

The witness case `admissibility:player-rejected` is stale oracle semantics
from “both paths reject PLAYER.” Update the witness to expect **serve +
fail-closed hide**, with a GM-only-row leak still classified blocking.
Do not regress the adapter to `unsupported_admissibility`.

### 5.5 `neighborhood:depth-2` legacy `KeyError: 'item_enormous_boulder'`

**Ruling: C — retired oracle bug. Native contract already works.**

The Buddy kernel selects a node its own projection does not contain.
Direct returned a result (~20s). Do not patch the legacy kernel so it can
keep acting as an oracle. Keep independent R.3 tests that the native
depth-2 API returns a coherent neighborhood.

### 5.6 `anchor:emit-revalidate-open` — `DirectWorldGraphReadError`

**Ruling: A — genuine R.3 defect. Investigate on the #629 resume, not in this design slice.**

Source-anchor emit/revalidate/open is a named supported capability. The
witness never compared outcomes because the direct path raised
`Unexpected failure in the direct DungeonMind read path`
(`projection_internal_error`). That wrapper currently swallows the
underlying exception class, so ownership (adapter product-local join vs
DungeonMind `resolve_source_anchor`) is **not yet proven**.

Authorized next implementation, after this design is accepted:

1. Preserve the chained cause in the adapter error mapping (observability,
   not a semantic change).
2. Reproduce the case against repaired V4.
3. If the failure is adapter/product-local (URI/locator join, span opener,
   digest pin), fix it in #629.
4. If it is below the landed R.2 `resolve_source_anchor` seam, stop and
   dispatch a bounded DungeonMind prerequisite. Do not change DND public
   contracts inside the Buddy PR.

### 5.7 Already-classified non-blocking families

Leave these as they are. They are not this document’s dispute:

- `representation only` (2,345) — vocabulary prefix, predicate
  normalization, dual-sense direction, label-echo aliases
- `intentionally retired legacy-only field` (1,056) — including
  `external_resource` / statblock-external payloads the adapter already
  documents as field D
- `new deterministic R.2 search ranking` (2)

---

## 6. How the differential witness works after this decision

After steward acceptance, the witness is a **supported-contract checker**,
not a Buddy-kernel cloning score.

```text
blocking semantic difference
  → still a merge blocker (lost supported capability, leak, identity drift)

approved semantic divergence
  → ratified by this document; counted, not blocking

representation only
intentionally retired legacy-only field
new deterministic R.2 search ranking
product-local presentation join
  → unchanged
```

Reclassify the 166 evidence-chain rows, the c1 Mireward object drops, the
27 property rows, and the canary object drops into
`approved semantic divergence` **only after** this file is accepted. Until
then the 200-row tally remains the frozen evidence stop point.

The witness must still:

- identity-preflight V4 / M1 / D_B;
- fail on GM/PLAYER leaks, revision-id drift, missing supported ops;
- record errored cases instead of swallowing them;
- keep `--runs` performance characterization with the gate off outside the
  harness process.

R.3a’s regression oracle becomes: **supported-contract result of R.3
direct == R.3a optimized direct**, not “equals Buddy kernel.”

---

## 7. Exact conditions that permit #629 to resume

#629 stays frozen until a steward accepts this document. Then it may resume
**only** for:

1. Version the witness vocabulary to v2 and apply the ratified
   `approved semantic divergence` labels above.
2. Rewrite the PLAYER case from `player-rejected` to serve + fail-closed
   hide.
3. Investigate and fix the anchor `DirectWorldGraphReadError` per §5.6, or
   split a bounded DungeonMind prerequisite if ownership is below R.2.
4. Keep native depth-2 tests; do not repair the Buddy kernel KeyError.
5. Keep `DUNGEONMIND_WORLD_GRAPH_DIRECT_READ` default-off.
6. Prove current GM Plan / agent query / source-span open still function
   through the existing hydrated path against repaired V4 (already true
   for hydration smoke); after the anchor fix, add a direct-path
   emit-revalidate-open proof behind the test opt-in.

Out of scope for that resume:

- DungeonMind object-only admission compatibility
- restoring `properties=[]` via contribution replay
- keeping the canary queryable
- enabling the production direct-read gate
- R.3a performance work

---

## 8. Revised R.3 merge-ready invariant

> With DungeonMind as live graph authority and direct reads behind the
> default-off rollout gate, every current DungeonMindBuddy graph-read
> capability listed in §3 is supported through the DungeonMind R.1/R.2 API
> with explicit revision, scope, admissibility, evidence, and anchor
> semantics. Known differences from the retired Buddy kernel are either
> proven product defects and resolved, or explicitly ratified here as
> approved semantic divergence / retired residue. No compatibility
> behavior exists solely to preserve obsolete Buddy graph-engine
> semantics.

This still requires Buddy to work. It does not require DungeonMind to
become Buddy.

---

## 9. Stop conditions

Stop and return to design if:

- a proposed fix exists only to reduce the legacy-difference tally;
- an implementation would add a Buddy-compatibility mode to DungeonMind
  without a named current product consumer;
- evidence-chain admission is shown to break an intended current Buddy
  product experience under the correct campaign/world lens;
- a named consumer appears for the 27 attributes and their future
  DungeonMind representation is unclear;
- anchor repair requires changing DungeonMind public contracts beyond the
  current R.2 seam inside the Buddy PR;
- any change weakens GM/PLAYER, visibility, provenance, or
  source-admission guarantees merely to match Buddy;
- anyone proposes enabling the direct-read gate before R.3a;
- witness classes are silently reclassified without a versioned decision.

---

## 10. Successor sequence

```text
steward accepts this document
        ↓
#629 resume: vocabulary v2 + PLAYER witness + anchor investigation
        ↓
R.3 semantic closure under the invariant in §8
        ↓
R.3a native-read performance
        ↓
production direct-read rollout candidate
        ↓
Buddy graph-runtime demolition
```
