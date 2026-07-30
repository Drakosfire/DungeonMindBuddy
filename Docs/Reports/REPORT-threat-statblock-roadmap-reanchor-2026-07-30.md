# Report — Threat + Statblock Publication-First Roadmap Re-anchor

**Date:** 2026-07-30  
**Status:** CURRENT SEQUENCING AUTHORITY SYNCHRONIZED  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Evidence baseline:** merged PR `#454` plus `R0-A` and `R0-B` reports  
**Scope:** document-only re-anchor; no runtime or graph state changed

## 1. Decision

The statblock roadmap is re-anchored around the architectural proof that matters most:

```text
accepted immutable statblock revision
→ governed published Threat
→ Hermes query and exact mechanics hydration
→ exact projection
→ durable placement on product surfaces
→ exact activation in live combat
```

A direct Hermes answer → ThreatDraft → generation flow remains valuable, but it is an authoring convenience and connected-experience lane. It is not the blocker for publishing, querying, projecting, and placing a statblock that already has an exact accepted revision.

## 2. Evidence reconciled

### R0-A

The 2026-07-29 run reached the real provider:

```text
launcher → Plan → Tools → Statblock
→ create ThreatDraft
→ real provider generate
→ definition_invalid / HTTP 422
→ no candidate
```

Durable facts:

- draft ID/version existed;
- generation request ID existed;
- Buddy recorded terminal downstream validation failure;
- no candidate or accepted revision was invented;
- edit, validate, accept, and reload were unreachable;
- the product hid useful field/reference diagnostics behind a generic sentence.

Verdict remains `FAIL_PRODUCT`, not `BLOCKED_DEPENDENCY`.

PR `#454` subsequently synchronized the current consumer contract and removed timeout and freestanding-provenance blockers. The next operation is a merged-main rerun, not another repository-only readiness audit.

### R0-B

Hermes demonstrated:

- multi-hop campaign investigation;
- useful synthesis across Mireward, Shepherd, cult, swamp, meat-corruption, and Float Goat material;
- uncertainty preservation and premise rejection;
- a useful provisional Threat description;
- pinned graph revision, matched nodes, source anchors, diagnostics, and recovery behavior.

The report remains `IN_PROGRESS` because the authoring output is not yet a durable structured artifact and evidence/query interaction is incomplete.

This result supports graph chips, query anchors, copyable artifacts, epistemic labels, and liveness work. It does not need to block statblock publication.

## 3. What changed in sequencing

Previous sequencing:

```text
R0-A + R0-B
→ AOW01 / AOW02 Hermes-to-draft handoff
→ MAGIC-D1
→ connected authoring
→ graph publication
```

New sequencing:

```text
R0-A merged-main rerun
→ exact accepted revision
→ SBW08 binding contract
→ SBW09a–c publication
→ SBW10a query/hydration
→ SBW10b projection
→ MAGIC-D3
→ AOW03 / AOW04 placement
→ MAGIC-D4
→ COMBAT01 / SBW15
→ MAGIC-D5
```

Parallel lane:

```text
R0-B closeout
→ graph chips / query anchors
→ copyable authoring artifact
→ AOW01 / AOW02
→ MAGIC-D1 / MAGIC-D2
```

## 4. Immediate prerequisite

Rerun the accepted-revision path on merged `main`.

Exit conditions:

- real candidate under the current contract;
- one shipped dedicated numeric edit;
- authoritative validation;
- accepted exact `(statblock_id, revision_id, digest)`;
- hard reload and exact reopen.

If `definition_invalid` remains:

- preserve structured provider field/reference diagnostics;
- classify producer output versus consumer contract versus presentation ownership;
- dispatch only the narrow owning-boundary repair;
- rerun the same product path.

## 5. Publication contract requirements

`SBW08` must freeze:

- exact external statblock locator;
- immutable revision and digest;
- `ThreatStatblockBinding` identity/state;
- mechanics owner versus graph owner;
- multiple binding selection;
- stale and deletion behavior;
- saved-versus-published state.

`SBW09a–c` must keep separate:

- durable recoverable publication operation;
- create-new versus connect-existing resolution;
- governed commit.

No silent merge, duplicate Threat, or mechanics recreation is acceptable.

## 6. Query and projection are explicit gates

Publication is not useful merely because a graph contribution exists.

`SBW10a` must prove that Hermes can find the published Threat through:

- name or alias;
- role or capability;
- relationship;
- location, faction, event, or campaign context.

The result must resolve to the exact binding and hydrate mechanics from the owning store. The graph must not contain a copied statblock definition.

`SBW10b` must project useful game information from the exact binding. Provenance remains inspectable but does not dominate the default view.

## 7. Placement is the architectural proof

`ObjectPlacementV1` must preserve:

- exact Threat;
- exact binding;
- exact statblock revision;
- host locator;
- quantity;
- role;
- trigger;
- visibility;
- notes;
- local adjustments.

Plan, Build, Ingest, Hermes results, graph inspection, and object projections should invoke one shared capability. Surfaces initiate; owning services write.

A placement is not an embed and does not copy mechanics.

## 8. Combat remains downstream

The current `CombatRosterModule` is a real product surface but retains legacy artifact/path/title identity.

`COMBAT01` and `SBW15` must add exact Threat/binding/revision/placement lineage while preserving mutable runtime HP, initiative, conditions, notes, and defeated state.

Combat never mutates graph truth or immutable mechanics.

## 9. Documents synchronized by this re-anchor

- `Docs/Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`
- `Docs/Plans/PR-TRACKER-threat-statblock-authoring-projection.md`
- `Docs/Runbooks/INSTRUCTIONS-reboot-dogfood-R0A-R0B.md`
- `Docs/Runbooks/RUNBOOK-authored-world-object-magic-moment-dogfood.md`
- this report

The raw R0 reports remain unchanged as evidence.

## 10. First exact next action

```text
Run R0-A on merged main far enough to produce and reopen one exact accepted statblock revision.
```

On success, the next dispatch is a doc/contract-first re-anchor of `SBW08`.

On repeated opaque validation failure, the next dispatch is only the narrow structured-diagnostics and owning-boundary repair.
