# PR Tracker — Campaign Supergraph

**Status:** Active implementation tracker — sole sequencing authority for Campaign Supergraph slices
**Updated:** 2026-08-17 — DungeonMind PR #34 exact Eldyrwild PostgreSQL existing-world adoption proof DONE; next is correspondence / authority-transition DESIGN
**Repository anchor:** `c0a008312b5305ada48157b6a7fb1efa879ec574` (Buddy `main` at guarded CUTOVER authority-sync start)
**Dispatch gate:** correspondence / authority-transition DESIGN. After this direct steward sync lands, re-anchor current `main` and author the DESIGN handoff directly on `main`. Do not dispatch CODE cutover before that design is accepted. Do not redispatch [`HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md`](HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md).
**#538 design predecessor / docs base:** PR #538 merge
**#536 design predecessor:** `413e808112dc85499651cf232ff71614dc4b18b6` (`KERNEL: make relationship conformance current-support aware`)
**DungeonMind pin:** `d2204dd0901237d8b446b4f2363f896306e32e6f` (PR #34 merge / current DungeonMind `main`; unchanged #33 runtime-under-proof remains `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92`)
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

PR #566 is merged and non-publishing: canonical bytes remain unchanged, while its locked authority proves exactly four source-sealed kind repairs. PR #568 sealed the historical v4/v2 CUTOVER ledger (Case A → admit `thread`). DungeonMind PR #30 published `dnd5e:thread`. PR #571 remeasured against v5/v3 and cleared `WORLD_OBJECT_KIND`. PR #575 classified the 28 identity-lifecycle shadow paths as `SOURCE_MIGRATION_HISTORY` **on the pre-`alias_remove` world**. PR #577 measured the eight `EVIDENCE_PROVENANCE` alias blockers and correctly STOPped. PR #580 filled generic Kernel `alias_remove`. PR #583 applied the exact-six Eldyrwild identity-shadow retirements; live result `rev:0c644e56b45bcaac709012206e3e41c2`, payload `0640d7ef…`, `EVIDENCE_PROVENANCE` 8→2. PR #585 proved the current identity lifecycle through `alias_remove` (head `7c339a23…`; merge `0fe9f88c…`; current proof 28/28). PR #587 sealed the Captain/Thrin alias assertion package (head `e3f33ddd…`; merge `cc5dc6dd…`). PR #588 sealed the dual-sense relationship endpoint-aspect package (head `b4c78161…`; merge `3415fcf9…`). DungeonMind #31 published assertion-scoped relationship endpoint aspects v6 (merge `351af975…`); #32 added the atomic existing-world adoption boundary (merge `3d34d53b…`); #33 preserved existing-world history replay v2 (merge `f2e27380…`, unchanged runtime-under-proof). PR #602 sealed the exact Eldyrwild `dm_existing_world_adoption_bundle_v2` / `dm_union_graph_v6` (head `775f4aa2…`; merge `9b170c71…`; pre-fix blob `14cbe339…`; current graph 469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected relationships). The first real PostgreSQL acceptance attempt correctly STOPped: same raw Buddy evidence ID under two source revisions (`contribution:2807888820d76c78`; 15 contributions / 57 unique raw IDs). PR #609 repaired Buddy export identity to `<raw>:dmv1:<canonical v1 binding sha256>` (head `ef71a7eb…`; merge `7922b610…`; implementation stamp `4446b6d2…`; new blob `274cdd9e…`). DungeonMind PR #34 independently accepted that exact snapshot into empty PostgreSQL (head `935d3d91…`; merge `d2204dd0…`, current DungeonMind `main`; 2 review cycles; Cycle 2 `4948479110`). Exact adoption is no longer acceptance debt. Observational correspondence, snapshot drift/catch-up, living-write ownership, authority switch/rollback, first post-cutover mutation, and old-authority demolition remain unproved. The next bounded capability is correspondence / authority-transition DESIGN. Product-authority cutover remains `BLOCKED`. Disposition remains `CUTOVER_NOT_READY`.

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
| `cutover-alias-assertion-package-after-575` / #577 | SUPERSEDED | #575 + merged PR #576 | Forensic STOP only: two source-grounded aliases (`Captain`, `Thrin Branchborn`) and six merge-shadow aliases. Already closed unmerged at `b31bbc32…` on 2026-08-13. Do not reopen, merge, or extend. Historical: Captain/Thrin packaging waited on `cutover-identity-lifecycle-through-alias-remove`; that proof is now `DONE` in PR #585. |
| `kernel-alias-remove-identity-decision` / #580 | DONE | #576 + PR #577 STOP measurement | Replay-safe public `remove_identity_alias`; head `5d4d43f01bc99729f6d6e577ec33553d9b5249b4`; merge `3a52d309a606608c9338147b78e0a2f708084042`; 2 review cycles; no Eldyrwild mutation; author-local 47 focused tests + Ruff + `git diff --check`; no GitHub Actions / commit-status evidence on the reviewed head; `tests/test_graph_kernel_boundaries.py` 4 failed / 4 passed on both base and head |
| `cutover-eldyrwild-identity-shadow-alias-remove` / #583 | DONE | merged #580 | PR: #583; implementation head `2cacc7cbdf77977e86daf29ed2b9058f94d54e70`; merge `299579bd3c3f78a9393ae3c97c57a1dfd6b155ed`; 3 review cycles; live parent `rev:5a7c13ae45c49a65b402920499be72ed`; live result `rev:0c644e56b45bcaac709012206e3e41c2`; live payload `0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2`; live/replay proven; retry `already_applied` / no-op; `EVIDENCE_PROVENANCE` 8→2; merge-only lifecycle proof 16/28 on the cleaned head |
| `cutover-identity-lifecycle-through-alias-remove` / #585 | DONE | exact-six slice `DONE`, including canonical live publication + replay proof | PR: #585; head `7c339a23d77b4465ca0adeda015859215b65285d`; merge `0fe9f88cfafda38319145e88d0f8b354d53830ca`; 2 review cycles; current proof 28/28 passed, unresolved `[]`; historical merge-only 16/28 remains non-authoritative; remasurement `ATTRIBUTE_ASSERTION=0`, `EVIDENCE_PROVENANCE=2`, `IDENTITY_HISTORY=20`, `CONTRIBUTION_HISTORY=5291`; fixture SHA `c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531`. No World Graph mutation. |
| `cutover-alias-assertion-package-after-shadow-alias-remove` / #587 | DONE | identity-lifecycle-through-alias-remove `DONE` (#585) | PR: #587; head `e3f33ddde879637d6d8bfb9b03b2c5690e235a3d`; merge `cc5dc6ddba0750924a46cf13843498c124937e5f`. Sealed Captain and Thrin Branchborn as revision-bound DungeonMind-compatible alias assertion package rows. No World Graph mutation. |
| `cutover-dual-sense-relationship-decomposition-package` / #588 | DONE | #587 | PR: #588; head `b4c78161ac6a2653f9df7f285c42b8006e8c3bfa`; merge `3415fcf96a28a29907e248e047ea0d2e75c50071`. Sealed dual-sense relationship endpoint-aspect package. No World Graph mutation. |
| DungeonMind #31 relationship endpoint aspects v6 | DONE | Buddy dual-sense package | Merge `351af975598ee6f28d65634da150ac83d9b79808`. `DND: add assertion-scoped relationship endpoint aspects v6`. |
| DungeonMind #32 existing-world adoption boundary | DONE | #31 | Merge `3d34d53b1c24862da32cf5f9f25e9b05b6ba5441`. `DND: add atomic existing-world adoption boundary`. |
| DungeonMind #33 existing-world history replay v2 | DONE | #32 | Merge `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92` (unchanged runtime-under-proof for #34). `DND: preserve existing-world history replay authority v2`. |
| `cutover-eldyrwild-dungeonmind-v6-adoption-bundle-v2` / #602 | DONE | #587 + #588 + DungeonMind #33 | PR: #602; head `775f4aa23d9eb73ef33b4f1446ad9d7dd6f553ec`; merge `9b170c71a9d800157918186f8f17dc43fd993bcf`; pre-fix blob `14cbe3394cd622fd58f321da1a6dfbcd6a3b97d3`. Exact non-mutating `dm_existing_world_adoption_bundle_v2` / `dm_union_graph_v6`; 469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected. |
| first PostgreSQL existing-world acceptance attempt | STOPPED | #602 sealed bundle | Real PostgreSQL rejected same `dm_evidence_ref_v1` ID with different source revisions (`contribution:2807888820d76c78`; 15 contributions / 57 unique raw IDs). No DungeonMind runtime/schema change. Correct STOP. |
| `cutover-eldyrwild-durable-contribution-evidence-identity` / #609 | DONE | PostgreSQL evidence-identity STOP | PR: #609; head `ef71a7eb6cb376d01144e1c01242d16a77803886`; merge `7922b6108cf9e05787f9c79cddcee9347edb0b44`; implementation stamp `4446b6d207921a4be121ebb756d68b6078b8eee0`; new blob `274cdd9e6d38d5a00aa43d780779e95a7919d975`. Contribution evidence IDs are `<raw>:dmv1:<canonical v1 binding sha256>`. GitHub recorded no formal review submissions; do not invent a cycle count. Author-reported PostgreSQL green against unchanged `f2e27380…` was not itself the independent acceptance PR; that proof is DungeonMind #34. |
| `dungeonmind-eldyrwild-postgres-existing-world-adoption-proof` / DungeonMind #34 | DONE | #609 `DONE` + DungeonMind #33 | DungeonMind PR #34; title `BUILD: prove Eldyrwild PostgreSQL adoption`; implementation head `935d3d9117442a92ef2dd8f11967fed20f863ea1`; merge `d2204dd0901237d8b446b4f2363f896306e32e6f` (current DungeonMind `main`); 2 review cycles; Cycle 1 `4948116743` CHANGES REQUIRED; Cycle 2 `4948479110` MERGE-READY (formal COMMENT because reviewer == author). Exact blob `274cdd9e6d38d5a00aa43d780779e95a7919d975`; bundle SHA-256 `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`; published revision `rev:34b1f8e2625d5ba693fc726a2a1a4720`; graph payload `047214f19e3a2d22b1cf3e0596283844ef34853dd2e4f38d341c6b212ae320ef`; shape 469/323/3/5; 83/83 source, 93 `GraphContributionV2`, 13 `IdentityDecisionRecordV2`. Three test/fixture paths only; no production runtime/schema edits. PostgreSQL integration green; inherited repo-wide Ruff `SIM300` left `ci / core` red. Does not prove correspondence, snapshot drift, writer ownership, or product-authority switch. Historical handoff: [`HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md`](HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md). |
| correspondence / authority-transition DESIGN | READY | DungeonMind #34 `DONE` | Bounded DESIGN gate. Must resolve/decompose observational correspondence, snapshot drift/quiescence or catch-up, living-write ownership, switch/rollback authority, and first post-cutover mutation proof before CODE cutover is dispatchable. No successor handoff yet; steward-author it directly on `main` before any CODE cutover. |
| `dungeonmind-whole-world-authority-cutover` | BLOCKED | correspondence / authority-transition DESIGN accepted | No DungeonMind product authority cutover. Exact PostgreSQL adoption does not switch Buddy reads/writes. |

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

1. Re-anchor current `main`, then author the correspondence / authority-transition DESIGN handoff directly on `main`. Do not redispatch [`HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md`](HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md). Do not dispatch CODE cutover until that design gate is accepted.
2. Confirm PR #577 remains closed unmerged. Do not rescue or extend that branch. Do not redispatch Captain/Thrin packaging or dual-sense packaging.
3. Keep DungeonMind product-authority cutover `BLOCKED`. Exact PostgreSQL adoption does not switch Buddy reads/writes, Plan/Play/Hermes, living-write ownership, or old graph authority. Observational correspondence, snapshot drift/catch-up, writer handoff, first post-cutover mutation, and demolition remain unproved.

## Current acceptance debt

The following remain true after DungeonMind PR #34 and the direct Buddy authority sync:

- Integrity heal, Lysandra, Session-24 corrections, closure, PR #566, CUTOVER re-anchor #568, v5 re-pin #571, identity-lifecycle #575/#583/#585, Captain/Thrin #587, dual-sense #588, DungeonMind #31/#32/#33, exact adoption-v2 bundle #602, evidence-identity #609, and DungeonMind #34 exact PostgreSQL existing-world adoption proof are `DONE`.
- Canonical Eldyrwild is `rev:0c644e56b45bcaac709012206e3e41c2` (`323 / 314 / 9 / 3`) with exact payload SHA `0640d7ef…`; the approved migration projection is non-publishing (`323 / 318 / 5 / 3`).
- Accepted exact snapshot: Git blob `274cdd9e6d38d5a00aa43d780779e95a7919d975`; bundle SHA-256 `90574dfc4101e4198c7fd96478d6f49e65aa534d0aa91fa41a9a17da9d49695f`; published revision `rev:34b1f8e2625d5ba693fc726a2a1a4720`; graph payload `047214f19e3a2d22b1cf3e0596283844ef34853dd2e4f38d341c6b212ae320ef`; shape 469 objects / 323 relationships / 3 secondary aspects / 5 aspect-selected relationships.
- DungeonMind PR #34 accepted that snapshot against unchanged #33 runtime `f2e27380…` (head `935d3d91…`; merge `d2204dd0…`; 2 review cycles; Cycle 2 `4948479110`). Current DungeonMind `main` is `d2204dd0…`.
- The first real PostgreSQL attempt against pre-fix blob `14cbe339…` correctly STOPped on evidence identity (15 contributions / 57 raw IDs). That class is repaired in Buddy and independently accepted by #34.
- #34 did not prove observational correspondence after later Buddy changes, snapshot drift/descendant catch-up, living-world writer ownership, production read switch, rollback operator workflow, first post-cutover mutation, or old-authority demolition.
- Disposition remains `CUTOVER_NOT_READY`. Next bounded capability is correspondence / authority-transition DESIGN. Product-authority cutover remains `BLOCKED`.
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
