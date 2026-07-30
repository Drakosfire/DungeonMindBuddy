# Instructions — R0 Closeout and Publication-First Pickup

**Status:** ACTIVE operator and implementation pickup  
**Updated:** 2026-07-30  
**Sequencing authority:** [`../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md`](../Roadmaps/ROADMAP-threat-statblock-authoring-projection.md) + [`../Plans/PR-TRACKER-threat-statblock-authoring-projection.md`](../Plans/PR-TRACKER-threat-statblock-authoring-projection.md)  
**Result template / gate rules:** [`RUNBOOK-authored-world-object-magic-moment-dogfood.md`](RUNBOOK-authored-world-object-magic-moment-dogfood.md)  
**Current re-anchor:** [`../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md`](../Reports/REPORT-threat-statblock-roadmap-reanchor-2026-07-30.md)

This file previously instructed a fresh `R0-A` then `R0-B` reboot. Both reports now exist. Use this as the closeout and next-action brief.

## 0. Current evidence

| Gate / slice | Truth now |
|---|---|
| PR `#454` | MERGED — R0 evidence, provider-contract sync, timeout alignment, freestanding provenance honesty, Hermes UX unblockers |
| `R0-A` | `FAIL_PRODUCT` on 2026-07-29: provider reachable; draft created; generate returned `definition_invalid / HTTP 422`; no candidate |
| `R0-B` | `IN_PROGRESS`, provisional grounding/description pass; durable authoring artifact and evidence interaction remain incomplete |
| Immediate prerequisite | One exact accepted `(statblock_id, revision_id, digest)` must survive reopen |
| Critical next architecture | `SBW08` exact Threat/statblock binding, then governed publication, query/hydration, projection, placement, combat |
| Parallel authoring work | Graph chips, copyable artifact, `AOW01–02`, library, revise/editor UX, liveness |

Raw evidence:

- [`../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md)
- [`../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md)

## 1. Immediate operator action — rerun only the accepted-revision path

Start at the product door:

```text
http://127.0.0.1:5173/
→ Plan
→ Tools
→ Statblock
```

Verify:

| Process | URL | Check |
|---|---|---|
| DungeonMindServer | `http://127.0.0.1:7860` | statblocks health live |
| Buddy live-control API | `http://127.0.0.1:8000` | readiness configured/available |
| Live Control UI | `http://127.0.0.1:5173` | HTTP 200 |

Record:

```bash
git rev-parse HEAD
git show -s --format='%h %s' HEAD
python3 -c 'import json;from pathlib import Path;print(json.loads(Path("out/graph_memory/worlds/eldyrwild/head.json").read_text())["head_revision_id"])'
```

Run:

1. Create a real nontrivial ThreatDraft.
2. Create and generate through the real provider.
3. If a candidate appears, edit one shipped dedicated numeric field: primary AC, HP scalar, or ability score.
4. Validate the working copy.
5. Accept/save mechanics.
6. Capture `(statblock_id, revision_id, digest)`.
7. Hard reload.
8. Reopen the exact accepted identity.

AI revise remains `DEFERRED_REVISE_UX`; it is not required for this prerequisite.

## 2. Failure classification

| Observation | Correct action |
|---|---|
| Provider/auth unavailable | `BLOCKED_DEPENDENCY` |
| `definition_invalid` or another structured provider validation failure | `FAIL_PRODUCT`; capture raw field/reference diagnostics and dispatch only the owning-boundary fix |
| Buddy collapses structured diagnostics to a generic sentence | Include diagnostic-presentation repair in the narrow R0-A recovery slice |
| Candidate succeeds but accepted identity cannot reopen | `PASS_WITH_FRICTION` or `FAIL_PRODUCT` depending on whether exact recovery is possible; likely `AUTHORING-LIBRARY` or accepted-mechanics browse slice |
| Exact accepted identity survives reopen | Close prerequisite and begin `SBW08` re-anchor |

Do not count:

- corpus-promotion Statblock View;
- mocks;
- a draft without a candidate;
- a provider-side object that Buddy cannot retrieve;
- remembered IDs without an actual reopen check.

## 3. Publication-first implementation sequence

After one exact accepted revision exists:

```text
SBW08
exact external-resource + ThreatStatblockBinding contract
        ↓
SBW09a
durable recoverable publication operation
        ↓
SBW09b
create-new versus connect-existing Threat resolution
        ↓
SBW09c
governed Threat + exact binding commit
        ↓
SBW10a
Hermes query + exact mechanics hydration
        ↓
SBW10b
compact/full exact-revision Threat projection
        ↓
MAGIC-D3 dogfood
        ↓
AOW03 / AOW04
durable placement + shared surface capability routing
        ↓
MAGIC-D4
        ↓
COMBAT01 / SBW15
        ↓
MAGIC-D5
```

`MAGIC-D3` must include a non-exact-name Hermes query that finds the published Threat through role, capability, relationship, or campaign context and hydrates the exact bound revision.

## 4. R0-B closeout — parallel, not blocking publication

Do not rerun R0-B merely to unlock `SBW08`.

The existing report already demonstrates:

- multi-hop investigation;
- uncertainty honesty;
- premise rejection;
- a useful provisional Threat description;
- pinned revision, matched nodes, anchors, diagnostics, and recovery behavior.

Closeout work may capture the final authoring trace and verdict. The related implementation lane may include:

- response-side graph evidence chips;
- query node anchors;
- explicit established/inferred/creative proposal/unknown state;
- stable editable/copyable markdown artifact;
- honest long-turn liveness;
- `AOW01` context envelope;
- `AOW02` “Develop as Threat.”

These improve how Threats are authored. They do not replace or block governed publication/query/placement.

## 5. Stop conditions

Stop and report rather than widening scope when:

- the current provider returns a new contract shape not represented by the checked-in contract;
- field/reference diagnostics are unavailable at the provider boundary;
- publication would require bypassing the graph-governance path;
- create-or-connect cannot distinguish explicit existing-node selection from inferred matching;
- query hydration would copy mechanics into the graph;
- placement ownership is ambiguous across Plan, Build, and Ingest;
- combat integration would mutate graph or immutable mechanics state.

## 6. Links

| Doc | Role |
|---|---|
| [`SCRIPT-R0-A-statblock-live-dependency-proof.md`](SCRIPT-R0-A-statblock-live-dependency-proof.md) | Detailed R0-A click path |
| [`RUNBOOK-authored-world-object-magic-moment-dogfood.md`](RUNBOOK-authored-world-object-magic-moment-dogfood.md) | Gate rules and result template |
| [`../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md`](../Reports/MAGIC-MOMENT-R0-A-2026-07-29.md) | Real provider failure evidence |
| [`../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md`](../Reports/MAGIC-MOMENT-R0-B-2026-07-30.md) | Hermes dogfood evidence |
| [`../Design/DECISION-grounded-authored-world-object-lifecycle.md`](../Design/DECISION-grounded-authored-world-object-lifecycle.md) | Lifecycle authority |
