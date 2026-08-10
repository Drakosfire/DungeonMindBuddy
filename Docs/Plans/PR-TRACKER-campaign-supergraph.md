# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole sequencing authority for Campaign Supergraph slices  
**Updated:** 2026-08-09 after PR #536 merged to `main` as `413e808112dc85499651cf232ff71614dc4b18b6` and post-#536 Lysandra docs authority sync  
**Repository anchor:** `413e808112dc85499651cf232ff71614dc4b18b6`  
**DungeonMind pin:** `2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4`  
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)  
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)  
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)  
**Integration roadmap:** [`Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)  
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This tracker records only current sequence, dependencies, and exit proofs. Completed implementation narrative belongs in merged PRs, archived handoffs, and acceptance reports.

At the immutable adjudication domain, effective Eldyrwild relationship conformance remains **346 semantic / 294 represented / 52 residual / 2 `uses_statblock`**. PR #536 made relationship conformance current-support aware so contradicted historical edges are durable history, not current residuals. The live Eldyrwild head may have additional current relationships beyond that historical baseline. The next real correction (`eldyrwild-lysandra-threat-direction-correction`) is gated on healing pinned contribution replay for `contribution:d3d244474789879c`, then accepts **parent-relative** effective movement (`0 / +1 / −1 / 0`), not absolute `294/52 → 295/51`.

## Rules

- One slice, one independently useful capability.
- Agents are not privileged writers.
- Graph claims are the canonical materialized fact plane; source anchors are the normal evidence route.
- No product fallback may select latest-ingest, preview-source, mutable run/store paths, arbitrary Markdown, or a parallel corpus index.
- Replacement paths are deleted in the replacement PR unless a named remaining consumer is documented.
- `DONE` requires merged code and the slice's stated exit proof. Code presence alone does not satisfy live acceptance.
- Program labels are not dispatchable work. Dispatch only a bounded `READY` slice with an explicit invariant and proof.
- Diagnostic conformance must never be mistaken for mutation authority. A residual moves only when a governed durable write changes the World Graph or when a pinned external semantic contract legitimately represents it.

## Status legend

| Status | Meaning |
|---|---|
| `READY` | Dependencies are met; a handoff may be authored/dispatched |
| `DOING` | One active implementation slice owns the capability |
| `BLOCKED` | Waiting on a named dependency or acceptance gate |
| `DONE` | Merged and exit proof satisfied |
| `DEFERRED` | Intentionally outside the current critical path |

## Current sequence

### Durable graph and product authority foundations

| Slice | Status | Depends on | Required outcome |
|---|---|---|---|
| PR001–PR007A foundations | DONE | — | Durable World Graph, Kernel, publication, revision-pinned projection |
| PR008A Plan graph migration | DONE | PR007A | Plan objects and references read World Graph identity |
| PR010A/PR010B Hermes graph retrieval | DONE | PR007A/PR008 | Graph-first Hermes reads, admitted evidence, multi-turn and reload continuity |
| PR011A foundation/A1/A2 | DONE | Kernel + ingest registry | Sealed prepare/confirm operations, server-owned run binding, game-facing review sheet |
| PR380A / #412 | DONE | projection engine | Canonical recap reads one exact World Graph snapshot |
| PR380B / #437 | DONE | PR380A | Recap and Build consume shared exact-ID World Graph objects |
| PR380C / #443 | DONE | PR380B + confirm receipt | Terminal confirm replaces candidate authority with exact committed revision |

### DungeonMind whole-world semantic adoption spine

| Slice | Status | Depends on | Required outcome |
|---|---|---|---|
| #521 world-object bridge | DONE | statblock bridge foundation | Threat/NPC mechanics and PC semantic identity can be bridged without product-authority cutover |
| #522 whole-world conformance | DONE | #521 | Inventory the exact Buddy world against pinned DungeonMind and fail closed on real incompatibility |
| #523 post-DungeonMind-v5 conformance | DONE | #522 | Re-pin graph-v5/world-object-v2 contracts and emit an evidence-driven residual ledger |
| #525 post-v28 semantic conformance | DONE | #523 + DungeonMind PR #28 | Reduce Eldyrwild semantic gaps to the exact relationship residual set without silent coercion |
| #526 residual relationship adjudication | DONE | #525 | Source-ground every residual relationship and assign explicit disposition/owner/next action |
| #528 DungeonMind-v4 re-pin | DONE | #526 + DungeonMind PR #29 | Consume new DungeonMind vocabulary exactly; move `287/59 → 291/55`; leave only Buddy-owned residuals |
| #530 explicit relationship adapters | DONE | #528 | Govern the three remaining lossless adapter cases; move `291/55 → 294/52` without World Graph mutation |
| #531 adjudication continuity + effective conformance | DONE | #530 | Carry adjudication across proven descendants and compose exact effective conformance without injected authority |
| `kernel-targeted-assertion-correction` / #534 | DONE | #531 | Correct exactly one durable assertion without superseding unrelated assertions from the same source contribution; preserve historical source authority, CAS publication, and replay equivalence |
| `dungeonmind-current-relationship-authority-conformance` / #536 | DONE | #534 | Count only current assertion-supported edges in v4/effective relationship inventory so contradicted history is not current residual |
| `eldyrwild-contribution-integrity-heal` (`contribution:d3d244474789879c`) | READY | #536 | Restore ledger source-payload digest to match revision-bound seal so pinned `rebuild_from_contributions` succeeds on current Eldyrwild head; do not rewrite immutable revision history |
| `eldyrwild-lysandra-threat-direction-correction` | BLOCKED | #534 + #536 + contribution-integrity heal | Publish one governed descendant replacing only the defective Lysandra→cultists threat assertion with cultists→Lysandra; accept parent-relative `0/+1/−1/0` conformance; pinned rebuild of Q is not waivable |
| `eldyrwild-effective-conformance-after-first-correction` | BLOCKED | Lysandra correction | Re-anchor descendant effective-conformance fixtures/tracker on the **actual current baseline** after Q (parent-relative proof already required by Lysandra); keep adjudication anchor/source seals unchanged |
| `buddy-remaining-relationship-correction-slices` | BLOCKED | first real correction proof | Select subsequent bounded correction/decomposition/identity/evidence slices from the remaining residual ledger; never zero the ledger in one omnibus PR |
| `dungeonmind-whole-world-authority-cutover` | BLOCKED | Buddy semantic closure + public DungeonMind existing-world adoption seam | No DungeonMind product authority cutover until whole-world conformance and durable adoption both prove READY |

### Parallel product backlog retained from the July sequence

These remain valid product capabilities, but they do **not** override the active kernel/adoption dispatch order above.

| Slice | Status | Depends on | Required outcome |
|---|---|---|---|
| exact-run-candidate-review-projection | READY | PR380C | Graph Review candidates come from one exact ExtractionRun-bound review model |
| retire-preview-union-review-materialization | BLOCKED | exact-run candidate projection | Remove preview-union product lifecycle and obsolete Graph Preview consumers |
| PR380D projection coordinator/cache/telemetry | READY | PR380B/PR380C | Shared request recipes, coalescing, warm cache, revision invalidation, telemetry |
| PR380E Ingest primary-path simplification | BLOCKED | exact-run candidate projection + retirement plan | Product workflow visibly separates source, candidate, review, and committed memory |
| PR380F extraction/identity hardening | READY | concrete dogfood defect | Narrow fixes preserve identity, evidence, and replay invariants |
| durable-memory end-to-end acceptance | READY | PR380C | Fresh fixture proves confirm, exact reload, Plan/Hermes retrieval, and reload persistence |
| PR011B Hermes governed writes | BLOCKED | accepted human reference path | Hermes prepares/proposes through the same protocol; GM remains confirmation authority |
| PR009 Play projection migration | READY | PR007A + surface lessons | Play consumes revision-pinned graph and admissibility contracts |
| PR012 leftover cleanup | BLOCKED | replacement slices | Delete only leftovers with a documented remaining consumer |

## Immediate dispatch order

1. Dispatch `eldyrwild-contribution-integrity-heal` for `contribution:d3d244474789879c` so pinned contribution replay matches revision-bound seals on the current Eldyrwild head.
2. After that heal merges, dispatch `eldyrwild-lysandra-threat-direction-correction` using the post-#536 handoff ([`HANDOFF-eldyrwild-lysandra-threat-direction-correction.md`](HANDOFF-eldyrwild-lysandra-threat-direction-correction.md)): parent-relative conformance, `--allow-live-world` fence, complete preflight, non-waivable pinned rebuild of Q.
3. Re-anchor formal descendant effective-conformance fixtures/tracker on the actual post-Q baseline (`eldyrwild-effective-conformance-after-first-correction`); do not force historical absolute counts onto an evolved head.
4. Select the next Buddy-owned residual slice from the adjudicated ledger by correction class; keep source corrections, compound decomposition, identity migration, and insufficient-evidence work distinct where their authority semantics differ.
5. In parallel, PR380D or other July product work may proceed only when isolated from the correction/adoption authority boundary.
6. Do not schedule DungeonMind product-authority cutover until both semantic closure and the public existing-world adoption seam are proven.

## Current acceptance debt

The following remain true after #536 (`413e8081…`):

- The public Kernel assertion-level correction operation exists (#534) and is proven on synthetic multi-assertion contributions; it has not yet been applied to Eldyrwild.
- Current-support-aware conformance (#536) is merged; historical contradicted edges are durable history, not current relationship residuals.
- Pinned `rebuild_from_contributions` on the live Eldyrwild head fails closed on ledger/revision digest mismatch for `contribution:d3d244474789879c` — this blocks Lysandra until healed.
- The Lysandra threat-direction contradiction is adjudicated and source-grounded but intentionally still uncorrected in the World Graph; its BUILD contract is parent-relative, not absolute `295/51`.
- Effective relationship conformance remains `294 represented / 52 residual` on the adjudication anchor; the live head may differ; diagnostics and adapters do not mutate the original graph.
- Whole-world DungeonMind adoption remains not ready; no product or Play mechanics authority cutover is authorized.
- The pre-confirm catalog/live lane still relies on preview-union-era materialization.
- The human confirm path needs a fresh bounded end-to-end acceptance run after the reconstituted PR380A/B/C sequence.
- Browser-reload receipt rehydration is deferred; post-confirm authority is currently an in-session transition.
- Projection coordination, invalidation, and telemetry are not yet app-level shared ownership.
- Hermes continuity is strong in Plan but not yet route-independent across Ingest, Build, and Plan.
- Play has not migrated to the World Graph projection spine.
- Worldbuilding draft elevation remains a separate authority design problem; do not relabel drafts as played canon for convenience.

## Completion evidence map

| Capability | Owning evidence |
|---|---|
| Storage, Kernel, projection contracts | Tests under `src/graph_memory`, server projection contracts, merged PRs |
| Semantic conformance/adjudication | Exact pinned fixtures + source seals + effective conformance tests under `tests/test_dungeonmind*` |
| Targeted assertion correction | Synthetic multi-assertion proof that one assertion changes while unrelated support/provenance is byte/semantic-equivalent; stale-parent/no-op/replay proofs |
| Real Eldyrwild correction | Exact before/after revision IDs, changed assertion identity, preserved source seal, descendant continuity, and effective residual delta |
| Graph Review candidate/confirm lifecycle | Graph Review integration tests and exact binding/interleaving tests |
| Durable memory acceptance | A bounded dogfood report showing exact IDs and revisions before and after reload |
| Hermes grounding | Tool trace, revision metadata, admitted anchors, abstention/coverage-gap tests |
| Surface migration | Exact-ID navigation tests and proof no preview/latest-ingest fallback is invoked |
| Demolition | Static/path inventory plus deletion of replaced product consumers |

## Adding a slice

Every new slice must state:

- purpose and independently useful outcome;
- owner and dependency;
- public/durable contract impact;
- user-visible authority transition;
- exact failure model;
- acceptance proof;
- explicit non-goals;
- retained paths, remaining consumers, and deletion owner.

For semantic-correction work, also state:

- exact adjudicated assertion/edge IDs in scope;
- whether historical source authority is preserved, superseded, contradicted, or clarified;
- why contribution-level supersession is or is not the correct primitive;
- expected effective-conformance delta;
- proof that unrelated active support is unchanged.

Do not reopen completed tenancy, authority, or graph-first decisions through a compatibility layer.

## Historical detail

The detailed tracker snapshot before consolidation is available in Git history at `09aed8db`. The August whole-world semantic chain is preserved by merged PRs #521–#531 and their fixtures. Archived handoffs and reports remain implementation evidence, not sequencing authority.
