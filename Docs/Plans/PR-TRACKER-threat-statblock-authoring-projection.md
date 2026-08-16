# PR Tracker — Threat + Statblock Domain

**Status:** ACTIVE DOMAIN TRACKER — publication/query/projection foundation complete  
**Updated:** 2026-08-16  
**Repository verification anchor:** `e504310f71863604267637eea6209dcbea04f929`  
**Roadmap:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md)  
**Lifecycle decision:** [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md)

This document owns status for **Threat/Statblock authoring, publication, query/hydration, projection, and domain-specific usability follow-ups**.

It does **not** own:

- whole-world DungeonMind adoption / product-authority CUTOVER — owned by [`PR-TRACKER-campaign-supergraph.md`](PR-TRACKER-campaign-supergraph.md);
- Playable/Play sequencing — owned by the active Playable/Play roadmaps and trackers;
- generic root product debt that is explicitly retained in `Backlog.md`.

The old publication-first critical-path narrative is historical after the merged #491/#502/#504/#508/#512 sequence. Merged PRs and handoffs retain the detailed recovery/state-machine evidence; this tracker keeps only current status and dispatchable successors.

## 1. Status contract

| Status | Meaning |
|---|---|
| `READY` | Dependencies are satisfied; one bounded handoff may be authored/dispatched now. |
| `DOING` | One active implementation branch/PR owns the slice. |
| `BLOCKED` | Bounded slice waits on a named dependency/gate. |
| `DEFERRED` | Intentionally outside the current pull order. |
| `DECOMPOSE` | Useful direction exists, but more than one independently useful capability is still bundled. |
| `DONE` | Merged and stated exit proof satisfied. |

No `NEW`, `BACKLOG`, `PARALLEL`, `RE-AUDIT`, or `PRE-DESIGNED` status may be treated as READY. Re-anchor first.

## 2. Current foundation

| Slice | Status | Current proof |
|---|---|---|
| `SBW01–05` | DONE | Client/readiness, drafts, generation, renderer, editing, validation through PR #404. |
| `SBW07` | DONE | Immutable accepted mechanics persistence through #409. |
| `SBW06` | DONE foundation | Revise contracts/lineage/durable attempts through #439; usability successors remain below. |
| `SBW08` | DONE `#457` | Exact external statblock resource + immutable `ThreatStatblockBinding`. |
| `SBW09a` | DONE `#462` | Durable exact-source / expected-parent publication operation. |
| `SBW09b` | DONE `#467` | Explicit create/connect/refuse Threat identity decision. |
| `SBW09c1` | DONE `#478` | Durable exact no-write reviewed publication proposal. |
| `SBW09c2a` | DONE `#476` | Exact contribution-operation → zero/one/many immutable revision lookup. |
| `SBW09c2b` | DONE `#491` | Proposal claim, durable commit intent/receipt, immutable recovery, exact verification. |
| `SBW10a` | DONE `#502` | Exact Threat query + mechanics hydration; Hermes read-only hydration tool. |
| `SBW10b` | DONE `#504` | Exact-revision Threat projection. |
| `MAGIC-D3 publication bridge` | DONE / product proof `#508` | Normal Workbench path publishes one exact accepted Threat chain; no duplicate confirmation. |
| Resident World Graph read optimization | DONE `#509` | Verified resident revision runtime and warm projection reads. |
| Threat parchment + shared Plan/Build lens | DONE `#512` | Campaign-useful glance/full projection and shared Plan/Build World Graph lens. |

### Current domain truth

The domain can now produce immutable mechanics, govern publication into one exact Threat/binding, query/hydrate that Threat, and render the same campaign-facing Threat projection through Plan/Build surfaces. Those capabilities are not root-backlog work anymore; regressions should be filed as new defects rather than reopening predecessor slices.

## 3. READY queue

### `AUTHORING-ARTIFACT` — stable editable/copyable Hermes artifact
**Status:** READY  
**Owner:** Hermes authoring UI  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`

**Slice:** Introduce one structured markdown artifact interaction with copy/edit affordances and provenance/uncertainty outside the paste-ready body. No ThreatDraft creation, graph write, or authoring-library browser in this slice.

**Exit proof:** Hermes can emit one artifact, the operator can copy/edit its markdown body, provenance remains inspectable separately, and ordinary prose answers remain unchanged.

### `REVISE-UX` — GM-facing Revise-with-AI primary flow
**Status:** READY  
**Owner:** Statblock Workbench  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`

**Slice:** Present one primary “Revise from working copy” instruction flow; move recovery IDs/choreography under Advanced; show a clear new-proposal result. Do not alter revision contracts or add accepted-revision repin behavior.

**Exit proof:** Normal revise requires no recovery-ID manipulation; advanced recovery remains available; existing lineage/retry semantics and tests remain authoritative.

### `HERMES-LIVENESS` — truthful immediate long-turn state
**Status:** READY  
**Owner:** Hermes Agent Interaction UI  
**Captured:** 2026-07-30  
**Last verified:** 2026-08-16 @ `e504310f71863604267637eea6209dcbea04f929`

**Slice:** Add elapsed time plus truthful in-flight/error/retry UI using state the product actually has today. Do not fabricate retrieval/synthesis stages and do not introduce the future lifecycle-event protocol in this slice.

**Exit proof:** A slow real turn visibly remains active, elapsed state updates, errors/retry are honest, and no invented internal stage is displayed.

## 4. DECOMPOSE before dispatch

| ID | Why it is not READY | Required split |
|---|---|---|
| `AOW01/AOW02` | Grounded authored-object context and “Develop as Threat” creation/opening mix evidence envelope, transformation, and durable draft action. | Freeze context envelope first; then one explicit Threat-draft action. |
| `GRAPH-CHIPS` | Response-side retrieved-evidence chips and composer-side explicit node anchors have different authority/input semantics. | `GRAPH-CHIPS-RESPONSE` and `GRAPH-CHIPS-QUERY`. |
| `AUTHORING-LIBRARY` | Browse/reopen/update drafts and accepted mechanics spans several lifecycle authorities. | Inventory/read first; mutation/update successors separately. |
| `EDITOR-EXPANSION` | Walk speed, attack to-hit/damage, and save DC are independently useful controls. | Dispatch one mechanic family at a time. |
| `HERMES-TELEMETRY` | Durable capture and aggregate reporting are different capabilities. | `HERMES-TELEMETRY-CAPTURE` then report/aggregation successor. |
| `SBW06d` | “Revise from exact accepted locator” changes revision authority, not just UX. | Re-anchor after `REVISE-UX`; design exact accepted-locator revision semantics separately. |

## 5. DEFERRED domain work

| ID | Status | Trigger |
|---|---|---|
| `SBW13` immutable child revision | DEFERRED | A real edit-after-accept workflow needs durable mechanics evolution. |
| `SBW14` governed binding adoption | DEFERRED | Multiple immutable mechanics revisions need an explicit selected-binding transition. |
| `SBW16–18` media | DEFERRED | Core authoring/query/projection usability is stable enough that images/3D materially improve play. |
| `AOW05` second-domain proof | DEFERRED | Object-placement architecture needs a second domain to justify a generality claim. |

## 6. Sequencing delegated elsewhere

The following old tracker rows remain useful context but are **not status-owned here anymore**:

| Capability | Current owner |
|---|---|
| Durable object placement / Playable placement semantics | current Playable/Play architecture + roadmap stack |
| Live combat exact lineage and runtime activation | `ROADMAP-play-world-object-combat-projection.md` and current Play workstream |
| Whole-world DungeonMind adoption / product-authority cutover | `PR-TRACKER-campaign-supergraph.md` |
| Build-local publication of shared Tool capabilities such as opening Workbench | root `Backlog.md` unless/until promoted into a Surface Interaction sequencing plan |

Do not dispatch historical `AOW03/AOW04`, `COMBAT01`, or `SBW15` literally from this file without reconciling them against those current owners.

## 7. Gate ledger

| Gate | Status | Meaning now |
|---|---|---|
| `R0-A` | DONE / operator-confirmed | Accepted mechanics create→generate→edit→validate→accept→reload foundation exists. |
| `R0-B` | DEFERRED closeout | Historical grounded-authoring evidence remains useful; new authoring slices above own product work. |
| `MAGIC-D1/D2` | DEFERRED | Desired authoring proofs, not publication blockers. |
| `MAGIC-D3` | PARTIAL PRODUCT PROOF | Publication/query/projection foundation landed; remaining authoring/liveness convenience work is separate. |
| `MAGIC-D4/D5` | DELEGATED | Placement/combat proofs belong to current Playable/Play owners. |

## 8. Dispatch discipline

Every READY implementation still requires a current handoff with one mission/invariant, exact base/dependencies, bounded allowlist, authority/persistence boundaries, owning tests, demolition declaration when replacing behavior, and explicit stop conditions.

If `Last verified` is older than 30 days, re-anchor before dispatch. Historical handoffs are evidence, not permission to execute against current `main`.
