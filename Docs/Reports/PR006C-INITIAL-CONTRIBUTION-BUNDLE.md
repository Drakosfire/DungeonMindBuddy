# PR006C — Initial Eldyrwild C2 Contribution Bundle

**Date:** 2026-07-11  
**Slice:** PR006C — Approved Initial World Supergraph Contribution Bundle  
**Predecessor:** PR006B / GitHub #334 (merge `b234988056abebb5b2a033cf236548a7c8c472f5`)

---

## Bundle identity

| Field | Value |
| --- | --- |
| Bundle ID | `eldyrwild-longmont-c2-initial-v1` |
| Bundle digest | `f4632636f5e4620b900e4df2d88eda41a46d14f36969b1f390b58d6044ca0620` |
| World ID | `eldyrwild` |
| Campaign scope | `longmont-c2` |
| Planning focus | `mireward-planning-window` |
| Focus sessions | `session-22`, `session-23` |
| Bundle path | `graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1/` |

### Ordered contribution IDs

1. `contribution:426a20487fd41cbd` — `001-world-hubs.json`
2. `contribution:2308cd6375dde06c` — `002-questionable-company-roster.json`
3. `contribution:a09aeeccf1080ade` — `003-session-22-mireward-road.json`
4. `contribution:12702a97be277a36` — `004-session-23-mireward-gate-battle.json`
5. `contribution:16ac92b4dd272323` — `005-tripod-null-calf-threat-prep.json`

### Source artifact IDs

- `graph-native:eldyrwild-c2-initial-v1:001-world-hubs`
- `graph-native:eldyrwild-c2-initial-v1:002-questionable-company-roster`
- `graph-native:eldyrwild-c2-initial-v1:003-session-22-mireward-road`
- `graph-native:eldyrwild-c2-initial-v1:004-session-23-mireward-gate-battle`
- `graph-native:eldyrwild-c2-initial-v1:005-tripod-null-calf-threat-prep`

Artifact URIs use stable `graph-data://approved-contribution-bundles/...` locators into the checked-in contribution records.

---

## Semantic contents

| Measure | Count |
| --- | --- |
| Unique bundle-owned nodes | 12 |
| Unique bundle-owned edges | 11 |
| Accepted assertions | 30 (`node` 16, `edge` 11, `attribute` 3) |
| Rejected assertions | 0 |
| Unresolved mentions | 0 |
| Identity decisions | 0 |
| Source domains | `worldbuilding`, `manual_seed`, `recap`, `statblock` |

### Shared-support assertions (PR006B contract)

| Node | Semantic assertion ID | Active contributions | Domains |
| --- | --- | --- | --- |
| `location:mireward` | `assertion:3e2a37249f847f60` | world hubs + session 22 + session 23 | `worldbuilding`, `recap` |
| `party:questionable-company` | `assertion:e43e22317e459bac` | roster + session 22 + session 23 | `manual_seed`, `recap` |

Mireward existence assertions use `campaign_scope = null` and `temporal_scope = null`.  
Questionable Company existence assertions use `campaign_scope = longmont-c2` and `temporal_scope = null`.  
Session chronology lives on event/edge assertions only.

---

## Governance

```text
identity decisions: 0
unresolved mentions: 0
rejected assertions: 0
approval basis: merge of PR006C
```

Do not treat this branch as approved. PR006D must pin:

- the actual PR006C merge SHA; and
- this bundle digest

before publication.

---

## Evidence coverage

| Measure | Result |
| --- | --- |
| Accepted assertions with ≥1 evidence ref | 100% (30/30) |
| Accepted assertions with resolvable source artifact | 100% (30/30) |
| Recap assertions with session locator | 100% (10/10) |
| Non-recap assertions with source locator | 100% (20/20) |

---

## Dry-run publication

```text
Dry-run publication:
  temporary test root only

Production Eldyrwild graph head:
  not created

Runtime availability:
  unchanged
```

All five contributions merge successfully in manifest order against a synthetic baseline fixture used only to satisfy Kernel baseline requirements. Rebuild with `publish=False` is equivalent to the temporary head.

---

## Plan trust statement

Plan may trust this bundle for:

- identities and basic roles of Mirathorn and Mireward;
- the Questionable Company roster;
- the existence and location of the Session 22 and Session 23 events;
- party participation in those events;
- the Tripod Null-Calf’s association with the Session 23 gate battle;
- provenance and independent multi-source support.

Plan may not trust this bundle for:

- complete Campaign 2 history;
- complete NPC, faction, location, item, or encounter coverage;
- exact ordering of events within a session;
- rich statblock rendering;
- complete combat mechanics;
- player-safe visibility filtering;
- projection ranking;
- graph-backed retrieval;
- facts outside the locked bundle scope.

---

## Unsupported projection requirements

1. Arbitrary attribute assertion values are retained in the contribution ledger but are not currently materialized as rich node fields.
2. A Plan card cannot yet surface the Tripod’s battlefield role, challenge expectation, or first-appearance detail from the graph head alone.
3. Visibility/admissibility has not been exercised through Projection Engine.
4. The initial bundle does not establish campaign completeness.

These are findings for later slices, not reasons to expand PR006C.

---

## Non-claims

PR006C does not prove:

- source extraction quality;
- identity resolution;
- production Eldyrwild world-head publication;
- projection usefulness;
- Plan or Play integration;
- complete Campaign 2 coverage.
