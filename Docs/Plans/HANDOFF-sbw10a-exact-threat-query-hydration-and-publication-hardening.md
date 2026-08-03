# STATBLOCK — HANDOFF: SBW10a exact Threat query/hydration with SBW09c2b publication-boundary hardening

**Created:** 2026-08-03
**Status:** ACTIVE — implementation in progress / PR delivery
**Flow / agent:** `STATBLOCK`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw10a-exact-threat-query-hydration-and-publication-hardening.md`
**Implementation base:** `dd1a7f2a2783e2a2fb189150bd837065122bee8f`
**Predecessor merge:** PR `#491`, merge commit `601326b03a5179682b630befd7ebbcaa761937ed`, implementation head `fe6d394e6d45a2d5e26d23e58ec2e72f68c61fb3`
**Suggested branch:** `feat/statblock-sbw10a-exact-threat-query-hydration-hardening`
**Required PR title prefix:** `statblock`

> Complete the publication write→read trust seam: harden the merged SBW09c2b failure classifications that can misstate durable publication authority, then expose one read-only SBW10a capability that queries published Threats and hydrates every returned mechanics binding from its exact immutable statblock revision. Do not build the visual Threat Sheet, edit mechanics, update bindings, place objects, or enter combat.

## §1 Mission invariant

```text
Every returned Threat and mechanic is attributable to one exact graph revision and one exact
(threat_node_id, binding_id, statblock_id, revision_id, definition_digest) chain; every publication,
dependency, and storage failure is classified from durable/readable authority, and no path silently
substitutes latest, first match, current head, copied mechanics, or non-durable in-memory state.
```

## §3 Owned predecessor defects (F1–F5)

| ID | Defect | Required classification |
| -- | ------ | ----------------------- |
| F1 | Admission collapses unavailable deps into 409 | unavailable→503; mismatch→409; integrity→500; zero artifacts |
| F2 | Retry treats not_found/operation_not_ready as transient | conclusive missing/stale→uncommitted; storage/graph→committing |
| F3 | Committing replay recon OSError skips c2a | c2a-first after lookup-key trust; OSError→recovery_pending |
| F4 | Connect-existing checks dead `node_upsert` | Reject Threat `assertion_kind="node"` rewrites |
| F5 | Double receipt-save returns synthetic count=2 | Return last durable disk record + typed storage failure |

## §5 Allowlist (summary)

Publication: `threat_publication_commits.py` + owning tests (+ route only if labels insufficient).

SBW10a new: `models/threat_query_hydration.py`, `services/threat_query_hydration.py`, `routes/threat_query_hydration.py`, `main.py` registration, hydration tests, Hermes interaction tool + plugin capability rule, Hermes owning tests.

Bounded discovery may include World Graph projection adapter, exact DungeonMind client, Hermes host paths.

## §6 Explicit non-goals

SBW10b Threat Sheet UI; binding preference writes; mechanics edit (SBW13); binding adoption (SBW14); Plan embed (SBW12); placement; combat; media; latest resolvers; copied mechanics into graph.

## §7 Contracts (frozen)

- Request requires exact `world_id`, `campaign_id`, `revision_pin` (no current-head default).
- Response returns zero/one/many Threat hits; every typed `uses_statblock` binding is enumerated; no first-win.
- Hydration calls `DungeonMindStatblockV1Client.get_exact_revision` only; digest equality gates trusted `revision`.
- Hermes tool `query_threat_mechanics_hydration` is read-only; scope injected from turn policy.

## §11 Demolition declaration

```text
Replaced path: none in SBW10a (no duplicate backend/Hermes query hydrator discovered that used latest/label/corpus)
Deleted in this PR: no
If no, retained reason: no legacy exact-Threat hydration consumer found under Hermes/backend allowlist
Named remaining consumer: legacy StatblockViewModule / visual consumers remain for SBW10b demolition
Required deletion owner: SBW10b
```

## §17 Still false after merge

SBW10b sheet; SBW13 edit; SBW14 binding preference; SBW12 embed; AOW03 placement; COMBAT01/SBW15 combat; MAGIC-D3 dogfood.
