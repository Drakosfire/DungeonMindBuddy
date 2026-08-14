# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole sequencing authority for Campaign Supergraph slices
**Updated:** 2026-08-13 — Review Cycle 1: live-exit facts stand; ATTRIBUTE_ASSERTION is not currently authorized; identity-lifecycle-through-alias_remove is next
**Repository anchor:** `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed` (PR #583 merge / `origin/main` at this state-sync dispatch)
**Dispatch gate:** this state-sync PR. After merge, re-anchor to its merge SHA / current `main`, then dispatch `cutover-identity-lifecycle-through-alias-remove` from that descendant.
**#538 design predecessor / docs base:** PR #538 merge
**#536 design predecessor:** `413e808112dc85499651cf232ff71614dc4b18b6` (`KERNEL: make relationship conformance current-support aware`)
**DungeonMind pin:** `be76acc997c5fbcb8ceaa090969ec051afa6051d` (PR #30; world-object-v5 / world-property-v3)
**Architecture:** [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](../Design/ARCHITECTURE-campaign-supergraph.md)
**Roadmap:** [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md)
**Current-state guide:** [`Docs/Design/STATUS-world-graph-continuity-spine.md`](../Design/STATUS-world-graph-continuity-spine.md)
**Integration roadmap:** [`Docs/Roadmaps/ROADMAP-cross-surface-statblock-demo.md`](../Roadmaps/ROADMAP-cross-surface-statblock-demo.md)
**UI shell (cross-boundary):** [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md)

This tracker records only current sequence, dependencies, and exit proofs. Completed implementation narrative belongs in merged PRs, archived handoffs, and acceptance reports.

At the immutable adjudication domain, historical Eldyrwild relationship conformance remains **346 semantic / 294 represented / 52 residual / 2 `uses_statblock`**. The exact post-#566 canonical World Graph is now the CUTOVER activation source:

```text
canonical = rev:0c644e56b45bcaac709012206e3e41c2
payload = 0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
323 semantic / 314 represented / 9 residual / 3 uses_statblock

approved migration projection = in-memory only
323 semantic / 318 represented / 5 residual / 3 uses_statblock
```

PR #566 is merged and non-publishing: canonical bytes remain unchanged, while its locked authority proves exactly four source-sealed kind repairs and leaves five dual-sense STOP edges. PR #568 sealed the historical v4/v2 CUTOVER ledger (Case A → admit `thread`). DungeonMind PR #30 published `dnd5e:thread`. PR #571 remeasured against v5/v3 and cleared `WORLD_OBJECT_KIND`. PR #575 classified the 28 identity-lifecycle shadow paths as `SOURCE_MIGRATION_HISTORY` (`ATTRIBUTE_ASSERTION` 28→0; `IDENTITY_HISTORY` remains 14; `CONTRIBUTION_HISTORY` remains 5285) **on the pre-`alias_remove` world**. PR #577 measured the eight `EVIDENCE_PROVENANCE` alias blockers and correctly STOPped: two are source-grounded current-node aliases and six are active only because `merge_identity()` unioned merged-away labels onto survivors. Direct cleanup or classifying those six as history is unauthorized. PR #580 filled the generic Kernel `alias_remove` primitive (`remove_identity_alias`; head `5d4d43f0…`; merge `3a52d309…`; 2 review cycles; no Eldyrwild mutation). PR #583 applied the exact-six Eldyrwild identity-shadow retirements (head `2cacc7cb…`; merge `299579bd…`; 3 review cycles) and its canonical live/replay exit is proven: parent `rev:5a7c13ae45c49a65b402920499be72ed` → result `rev:0c644e56b45bcaac709012206e3e41c2`, retry `already_applied`, `EVIDENCE_PROVENANCE` 8→2. The two remaining alias blockers are `Captain` and `Thrin Branchborn`. `IDENTITY_HISTORY` is now 20 and `CONTRIBUTION_HISTORY` is now 5291 because the six new `alias_remove` decisions are durable history. The merge-only #575 proof now reconstructs only 16/28 on that cleaned head, so `ATTRIBUTE_ASSERTION` is **not currently authorized as 0**. The next bounded slice is proving identity lifecycle through `alias_remove` and regenerating source-history policy from a current passed proof. Captain/Thrin packaging stays `BLOCKED` until that proof. Whole-world adoption and product-authority cutover remain `BLOCKED`.

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
| `SUPERSEDED` | Replaced by a named successor slice that owns the remaining scope |

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
| `eldyrwild-descendant-residual-adjudication-session25` / #557 | DONE | #554 + #555 DESIGN DONE | Sealed exact U₇ at S25, composed with immutable A, cleared `UNADJUDICATED` at Q₃ while keeping `367/311/56/3`; merge `e88ac88bd511452e354ac0d804731475b8527e71` |
| `eldyrwild-session25-ephanna-thrin-false-hires-correction` / #559 | DONE | #557 DONE | Merged contradiction package (`8abfca285a780adb33797c71fd5ff6878caa6a76`) + canonical `Q₃→Q₄` live exit proven (`Q₄=rev:3759d8d6a02f09306397918234a2ded2`, parent-relative `-1/0/−1/0`, retry `already_applied`; C₁/C₂/C₃ + U₁–U₆ preserved) |
| `eldyrwild-effective-conformance-after-fourth-correction` | DONE | #559 merged + canonical C₄ live exit | Re-anchored current effective fixture/replay baseline to exact `R_current = Q₄ = rev:3759d8d6a02f09306397918234a2ded2` (`366 / 311 / 55 / 3`); composed A+S25 authority unchanged; absorbed as first implementation commit of the closure PR |
| `eldyrwild-relationship-semantic-closure` | DONE | Q₄ re-anchor + canonical closure exit | Canonical effective state is `323 / 314 / 9 / 3`; nine deferred kind-miscoding residuals remain source-sealed for migration authority |
| `eldyrwild-relationship-node-kind-source-repair` / #566 | DONE | #563 closure + exact canonical pin | Non-publishing locked authority proves four in-memory kind repairs and five dual-sense STOP edges; manifest SHA `96cc26fc…` |
| `cutover-whole-world-reanchor-after-566` / #568 | DONE | #566 + exact canonical revision/payload | Sealed historical v4/v2 CUTOVER ledger; Case A admitted Buddy `thread` into DungeonMind via PR #30; fixture SHA `6c978f89…` |
| `cutover-repin-dungeonmind-v5-after-pr30` / #571 | DONE | #568 + DungeonMind #30 (`be76acc…`) | Remeasured canonical + four-kind projection against world-object-v5 / world-property-v3; `WORLD_OBJECT_KIND` cleared; relationship inventories unchanged; fixture SHA `a666a2bc…` |
| `cutover-identity-lifecycle-history-after-571` / #575 | DONE | #571 + exact identity-lifecycle proof | Proved the 28 `ATTRIBUTE_ASSERTION` paths are reconstructable identity-lifecycle shadow **on the pre-`alias_remove` world**; classified only those proven paths as `SOURCE_MIGRATION_HISTORY`; `IDENTITY_HISTORY=14`; `CONTRIBUTION_HISTORY=5285`; merge `d32c244e…`; 3 review cycles; fixture SHA `1a2cd8f9…`. That merge-only proof is historical, not current authority after #583. |
| `cutover-alias-assertion-package-after-575` / #577 | SUPERSEDED | #575 + merged PR #576 | Forensic STOP only: two source-grounded aliases (`Captain`, `Thrin Branchborn`) and six merge-shadow aliases. Already closed unmerged at `b31bbc32…` on 2026-08-13. Do not reopen, merge, or extend. The six Eldyrwild `alias_remove` applications proved live/replay `EVIDENCE_PROVENANCE` 8→2; Captain/Thrin packaging stays `BLOCKED` until `cutover-identity-lifecycle-through-alias-remove` re-authorizes classification. |
| `kernel-alias-remove-identity-decision` / #580 | DONE | #576 + PR #577 STOP measurement | Replay-safe public `remove_identity_alias`; head `5d4d43f01bc99729f6d6e577ec33553d9b5249b4`; merge `3a52d309a606608c9338147b78e0a2f708084042`; 2 review cycles; no Eldyrwild mutation; author-local 47 focused tests + Ruff + `git diff --check`; no GitHub Actions / commit-status evidence on the reviewed head; `tests/test_graph_kernel_boundaries.py` 4 failed / 4 passed on both base and head |
| `cutover-eldyrwild-identity-shadow-alias-remove` / #583 | DONE | merged #580 | PR: #583; implementation head `2cacc7cbdf77977e86daf29ed2b9058f94d54e70`; merge `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`; 3 review cycles; live parent `rev:5a7c13ae45c49a65b402920499be72ed`; live result `rev:0c644e56b45bcaac709012206e3e41c2`; live payload `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2`; live/replay proven; retry `already_applied` / no-op; `EVIDENCE_PROVENANCE` 8→2; merge-only lifecycle proof 16/28 on the cleaned head |
| `cutover-identity-lifecycle-through-alias-remove` | READY | exact-six slice `DONE`, including canonical live publication + replay proof | Extend the diagnostic identity-lifecycle proof so post-#583 survivor state is reconstructable from durable merge + later `alias_remove` history; regenerate source-history policy from that current passed proof; remeasure `ATTRIBUTE_ASSERTION`. No World Graph mutation. Do not dispatch Captain/Thrin from this slice. |
| `cutover-alias-assertion-package-after-shadow-alias-remove` | BLOCKED | identity-lifecycle-through-alias-remove `DONE`, including regenerated source-history policy and remasurement that still selects the two alias blockers | Reconstruct exactly the two remaining source-grounded current-node aliases (Captain, Thrin Branchborn) as DungeonMind-compatible alias assertion package rows from revision-bound Buddy source authority. Expected package-construction observation: `EVIDENCE_PROVENANCE` 2→0. No World Graph mutation. |
| `dungeonmind-whole-world-authority-cutover` | BLOCKED | CUTOVER package-construction clear + public DungeonMind existing-world adoption seam | No DungeonMind product authority cutover until the blocker ledger and durable adoption proof both authorize it |

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

1. After this state-sync PR merges, re-anchor to its merge SHA / current `main`, confirm PR #577 remains closed unmerged, then start `cutover-identity-lifecycle-through-alias-remove` from that descendant using [`HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md`](HANDOFF-CUTOVER-identity-lifecycle-through-alias-remove.md). Record the exact dispatch-base SHA in the implementation handback. Prove post-#583 survivor lifecycle from merge + later `alias_remove`. Regenerate source-history policy from a current passed proof. Remeasure. Do not mutate the World Graph. Do not package Captain/Thrin in that slice.
2. Captain/Thrin packaging stays `BLOCKED` until that current proof authorizes classification. Do not seal a one-row package later. Do not treat locked #575 `ATTRIBUTE_ASSERTION=0` as current.
3. Keep the five dual-sense STOP edges as migration decisions; do not reopen broad Buddy relationship cleanup. Do **not** dispatch Case B adoption-seam work while package-construction blockers remain.
4. Confirm PR #577 remains closed unmerged. Do not rescue or extend that branch.
5. Do not schedule DungeonMind product-authority cutover until whole-world adoption and the public existing-world adoption seam are proven.

## Current acceptance debt

The following remain true after PR #566, PR #568, DungeonMind PR #30, and the CUTOVER re-pin:

- Integrity heal for `contribution:d3d244474789879c` is `DONE` (merged #540 + canonical live heal exit).
- Lysandra threat-direction correction is `DONE` (merged #537 + canonical `P_live→Q_live` exit).
- Session-24 cube→Karsemine false-location contradiction is `DONE` (merged #545 + canonical `P→Q` exit).
- Session-24 Lysandra→Caelynn false-leads contradiction is `DONE` (merged #550 + canonical `P→Q₃` exit).
- Canonical Eldyrwild is `rev:0c644e56b45bcaac709012206e3e41c2` (`323 / 314 / 9 / 3`) with exact payload SHA `0640d7ef…`; the approved migration projection is non-publishing (`323 / 318 / 5 / 3`). The pre-live parent `rev:5a7c13ae45c49a65b402920499be72ed` / `2632870e…` remains historical.
- PR #566 is verified against locked manifest SHA `96cc26fc…`; four kind-only paths are approved for in-memory projection and five dual-sense edges remain explicit STOP decisions.
- Historical #568 fixture SHA `6c978f89…` still reproduces under explicit world-object-v4 / world-property-v2 loaders.
- Post-PR30 re-pin (#571) clears `WORLD_OBJECT_KIND`; identity-lifecycle #575 cleared `ATTRIBUTE_ASSERTION` 28→0 **on the pre-`alias_remove` world** by classifying proven merge-shadow fields as `SOURCE_MIGRATION_HISTORY`. PR #583 live/replay exit retired the six merge-shadow aliases: current `EVIDENCE_PROVENANCE` is 2 (`Captain`, `Thrin Branchborn`); `IDENTITY_HISTORY` is 20 and `CONTRIBUTION_HISTORY` is 5291 (mechanical +6 from the six new `alias_remove` identity decisions). The merge-only #575 proof reconstructs 16/28 on `rev:0c644e56…`, so `ATTRIBUTE_ASSERTION` is **not currently authorized as 0**. Disposition remains `CUTOVER_NOT_READY`. Next bounded slice is `cutover-identity-lifecycle-through-alias-remove`, not the Captain/Thrin package and not Case B.
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
