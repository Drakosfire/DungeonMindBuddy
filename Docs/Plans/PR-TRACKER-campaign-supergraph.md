# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole sequencing authority for Campaign Supergraph slices
**Updated:** 2026-08-10 — #554 merged (`R_current=Q₃`); repair #555 multi-anchor + successor-state contract before BUILD dispatch
**Repository anchor:** `35776cd0…` / `origin/main` after #554 (`21e28e7871…`)
**#538 design predecessor / docs base:** PR #538 merge
**#536 design predecessor:** `413e808112dc85499651cf232ff71614dc4b18b6` (`KERNEL: make relationship conformance current-support aware`)
**DungeonMind pin:** `2e4fdc51f91c5c2a428500f7c2ece0d6742d04b4`
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)
**Integration roadmap:** [`Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This tracker records only current sequence, dependencies, and exit proofs. Completed implementation narrative belongs in merged PRs, archived handoffs, and acceptance reports.

At the immutable adjudication domain, historical Eldyrwild relationship conformance remains **346 semantic / 294 represented / 52 residual / 2 `uses_statblock`**. The formal **current** effective-conformance baseline is now anchored to exact live descendant:

```text
R_current = Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7
367 semantic / 311 represented / 56 residual / 3 uses_statblock
```

after integrity heal `DONE`, Lysandra `#537` live exit, Session-24 `#545` live exit, `#549` second re-anchor, `#550` C₃ live exit, `#552` DONE bookkeeping, and `#554` third effective re-anchor. Live head and formal baseline are both `Q₃` (`367 / 311 / 56 / 3`). Next gated work: repair and merge #555’s descendant-adjudication DESIGN (S25 multi-anchor + successor-state), then BUILD. Enclosing remaining program: `buddy-remaining-relationship-correction-slices`. Whole-world cutover remains `BLOCKED`.

## Rules

- One slice, one independently useful capability.
- Agents are not privileged writers.
- Graph claims are the canonical materialized fact plane; source anchors are the normal evidence route.
- No product fallback may select latest-ingest, preview-source, mutable run/store paths, arbitrary Markdown, or a parallel corpus index.
- Replacement paths are deleted in the replacement PR unless a named remaining consumer is documented.
- `DONE` requires merged code and the slice's stated exit proof. Code presence alone does not satisfy live acceptance. For `eldyrwild-contribution-integrity-heal`, that means the merge-ready Kernel guard + clone heal **and** the post-merge canonical live heal exit proof. For `eldyrwild-lysandra-threat-direction-correction`, that means the merge-ready correction package **and** the post-merge canonical apply exit proof (`P_live→Q_live`).
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
| `eldyrwild-contribution-integrity-heal` (`contribution:d3d244474789879c`) | DONE | #536 / #538 / #540 | Forensic heal + Kernel same-ID/different-source guard landed; canonical live heal exit proven (`already_healed`, head unchanged through heal) |
| `eldyrwild-lysandra-threat-direction-correction` / #537 | DONE | #534 + #536 + contribution-integrity heal `DONE` | Merged correction package + canonical `P_live→Q_live` exit proven (`P_live=rev:dfdf38edbefd734d108832e92467b208`, `Q_live=rev:b90646fb5b135988bd7842cde858c96e`, parent-relative `0/+1/−1/0`, retry `already_applied`) |
| `eldyrwild-effective-conformance-after-first-correction` | DONE | Lysandra correction `DONE` (merged package **and** canonical apply exit proof) | Current effective fixture/replay baseline re-anchored to exact post-Lysandra `R_current`; adjudication anchor/source seals unchanged |
| `eldyrwild-session24-cube-karsemine-false-location-correction` / #545 | DONE | Kernel contradiction `#544` + first effective re-anchor | Merged contradiction package + canonical `P→Q` exit proven (`P=rev:b90646fb5b135988bd7842cde858c96e`, `Q=rev:b8dfc063bc13a4fb297e83f5f9b313d9`, parent-relative `-1/0/−1/0`, retry `already_applied`) |
| `eldyrwild-effective-conformance-after-second-correction` / #549 | DONE | Session-24 correction `DONE` (merged package **and** canonical apply exit proof) | Re-anchored current effective fixture/replay baseline to exact `R_current = Q = rev:b8dfc063bc13a4fb297e83f5f9b313d9` (`368 / 311 / 57 / 3`); both C₁/C₂ authorities preserved; adjudication/source seals unchanged; merge `bd1e4922…` |
| `eldyrwild-session24-lysandra-caelynn-false-leads-correction` / #550 | DONE | #549 | Merged contradiction package + canonical `P→Q₃` exit proven (`P=rev:b8dfc063bc13a4fb297e83f5f9b313d9`, `Q₃=rev:ba3abde1bfc3659795bcd77bb55eb9f7`, parent-relative `-1/0/−1/0`, retry `already_applied`; C₁/C₂ preserved) |
| `eldyrwild-effective-conformance-after-third-correction` / #554 | DONE | Session-24 false-leads correction `DONE` (merged package **and** canonical apply exit proof) | Re-anchored current effective fixture/replay baseline to exact `R_current = Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7` (`367 / 311 / 56 / 3`); C₁/C₂/C₃ authorities preserved; adjudication/source seals unchanged; merge `21e28e7871…` |
| `eldyrwild-descendant-residual-adjudication-session25` / #555 | DOING | third re-anchor DONE | DESIGN repair: lock S25 as exact descendant-adjudication anchor, compose A∪S25 without rewriting A continuity, and stage open-candidate successor-state semantics; BUILD only after #555 merges. Handoff [`HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md`](HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md) |
| `buddy-remaining-relationship-correction-slices` | BLOCKED | descendant Session-25 adjudication BUILD `DONE` | Select one bounded correction/decomposition/identity/evidence slice from the **Q₃** residual ledger by adjudicated correction class (including former U₇); never zero the ledger in one omnibus PR |
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

1. Merge repaired #555 DESIGN (multi-anchor S25 authority + successor-state contract) — do **not** dispatch BUILD from the pre-repair handoff.
2. After #555 merges, dispatch BUILD for `eldyrwild-descendant-residual-adjudication-session25` per [`HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md`](HANDOFF-eldyrwild-descendant-residual-adjudication-session25.md) (S25-anchored descendant ledger for exact U₇; A continuity untouched; compose downstream).
3. After descendant adjudication BUILD `DONE`, select one bounded Buddy-owned residual slice from the **Q₃** ledger by adjudicated class — never omnibus. Open descendant candidates route to separate adapter/vocabulary slices.
4. In parallel, PR380D or other July product work may proceed only when isolated from the correction/adoption authority boundary.
5. Do not schedule DungeonMind product-authority cutover until both semantic closure and the public existing-world adoption seam are proven.

## Current acceptance debt

The following remain true after the third governed correction re-anchor:

- Integrity heal for `contribution:d3d244474789879c` is `DONE` (merged #540 + canonical live heal exit).
- Lysandra threat-direction correction is `DONE` (merged #537 + canonical `P_live→Q_live` exit).
- Session-24 cube→Karsemine false-location contradiction is `DONE` (merged #545 + canonical `P→Q` exit).
- Session-24 Lysandra→Caelynn false-leads contradiction is `DONE` (merged #550 + canonical `P→Q₃` exit).
- Formal current effective conformance is `R_current = Q₃ = rev:ba3abde1bfc3659795bcd77bb55eb9f7` (`367 / 311 / 56 / 3`) after #554; previous formal baselines `rev:b8dfc063…` (`368 / 311 / 57 / 3`) and `rev:b90646fb…` (`369 / 311 / 58 / 3`) remain historical; historical adjudication anchor `rev:3413bf6f5044cf2680233f5e37c90dcf` remains `346 / 294 / 52 / 2`.
- Remaining Buddy residuals on `Q₃` are **56**, including **7 UNADJUDICATED** Session-25 edges (`contribution:a4231edb9a228963`) that require an S25-anchored descendant adjudication authority composed with immutable A before correction. #555 DESIGN must land the multi-anchor + successor-state contract before BUILD. Diagnostics and adapters still do not mutate the World Graph.
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
