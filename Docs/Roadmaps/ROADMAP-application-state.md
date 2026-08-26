# ROADMAP — Application State

**Status:** ACTIVE ARCHITECTURE / PLAY-FIRST SEQUENCE COMPLETE — AS0 through AS5 merged; AS6+ deliberately unselected  
**Line of work / flow:** `APP-STATE`  
**Created:** 2026-08-24  
**Updated:** 2026-08-26  
**Architecture authority:** [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)  
**Parent pickup:** [`../Plans/STEWARDS-ANCHOR-application-state.md`](../Plans/STEWARDS-ANCHOR-application-state.md)

---

## 0. Completed sequence

```text
AS0   DESIGN                 DONE — PR #636 merge 4c90df353bfb5d0f6857357e00eb8b2b6e142257
AS0.1 STORAGE-TOPOLOGY       DONE — PR #639 merge dd09f7f707e38f9f4348b759da8cfdbbe420fd60
AS1   PLAN DOCUMENTS         DONE — PR #641 merge 29ff1584b9f76bb5100a724a96bebbbcf8f08d12
AS2   PLAYABLE               DONE — PR #643 merge b4d63daab3eeb8150ca73fe9492d7a3d8744a4e0
AS3   PLAY RUNTIME           DONE — PR #646 merge 9c946cd8c24effccec8d06cfc1cb5e310c9edc5e
AS4   PLAY CONTINUITY        DONE — PR #649 merge 993f837b6f2fc601acf2ae3a4b7926af1858ac6c
AS5   PLAY DEMOLITION        DONE — PR #650 merge cc016661f80416e0816f56349217cf33c53a195f
AS6+  CANDIDATE FAMILIES     UNSELECTED — evidence-driven only
```

AS5 accepted head: `3477d1c581bbcf4898a66aec43a82cdc3bb84b8f`  
AS5 review: **1 distinct-head review cycle**, PASS-equivalent `5034313758`  
AS5 exact-head evidence: PR #650 comment `5429758776`

Earlier accepted evidence remains:

- AS0.1: accepted head `abb3fb15f9b56e8712c07c798674d0462827677f`; Cycle 2 PASS `5014814402`.
- AS1: accepted head `b42eb629e8924695af7af5a6c986f44a26dc3536`; 3 cycles; PASS `5023488870`; evidence `5415847095`.
- AS2: accepted head `6b1c2e77648eee6180d293c92d2c97a428e9002f`; 3 cycles; PASS `5024971680`; evidence `5417774447`.
- AS3: accepted head `913cfe0bbce4db27250afd8277e3af50712ee029`; 3 cycles; PASS `5026608908`; evidence `5420273265`.
- AS4: accepted head `be109c429460b6e22b0ded1c13e77dd0cc8e6b5e`; 2 cycles; PASS `5033365385`; evidence `5428663041`.

---

## 1. What the Play-first program established

### Content / authored material

Buddy PostgreSQL owns the durable content primitives used by Plan/Runbook:

```text
WorkObject
WorkRevision        # immutable historical committed revision
WorkingCopy         # mutable draft, exact base revision
```

Stable identity is independent of filesystem path, worktree, URL, bucket key, or other locator.

Historical invariant:

> **Committed revision N remains loadable after N+1 exists.**

A Play Run pins exact WorkObject/revision/digest identity and reads those historical bytes rather than current/latest content.

### Play Runtime

Buddy PostgreSQL owns:

```text
play.run
play.run_manifest
play.active_run
```

with:

- atomic Run + sealed manifest creation;
- SQL `run_revision` CAS;
- preserve-only transactional rebase;
- exact active-Run selection / resume;
- fail-closed aggregate integrity;
- no ordinary fallback to predecessor Play files.

### Demolition

Current product operation no longer depends on:

- Run JSON files;
- manifest sidecars;
- `active-run.json`;
- rebase-intent files/recovery engine;
- Play filesystem transaction locks/importers;
- `out/runtime/play/` existing or being writable.

AS5 evidence proved operation with that path absent and with a hostile sentinel, plus DB-down no-fallback behavior.

---

## 2. Consequence for Play Surface

The persistence pause is over.

PLAY-SURFACE BF2/BF3 may proceed on current product design without waiting for another APP-STATE slice:

```text
BF2  v2 READY Runtime / current-position / relevance
↓
BF3  Scene-centered current-moment cockpit
```

APP-STATE is **not** the current blocker for those slices.

Combat remains a separate domain and is still a candidate APP-STATE family; its persistence status must not be inferred from Play's completion.

---

## 3. AS6+ candidate families

These are migration families, **not pre-authorized PRs, schemas, or table names**.

Re-anchor from current product evidence before selecting any one:

| Family | Independently useful outcome when selected | Boundary |
|---|---|---|
| Combat | Combat survives browser/worktree/session locality | Combat-owned schema; Play holds references only |
| Ingest processing/review | IngestRun/review state survives path locality | accepted World-bearing output still publishes through DungeonMind |
| SourceArtifact identity | durable source identity/provenance/assets independent of path | distinct from IngestRun |
| Generated artifact lifecycles | statblock/location/NPC/shop/encounter/card drafts/projects gain stable product identity | domain-owned; do not force into WorkObject when not document-like |
| Asset metadata + DungeonMindServer bytes | consumers use stable `asset_id`; CDN/storage URL is delivery, not identity | large binary bytes stay outside PostgreSQL rows |
| Remaining content / `worldbuilding_source` | durable Build content without becoming World truth | explicit publish/corpus policy |
| Agent proposal/task durability | only if reload correctness requires it | do not migrate local state merely because it exists |
| Plan publish-to-corpus | explicit WorkRevision export | never silent publication |
| Run mutation history | optional audit history if independently useful | not event sourcing by default |

No family is “AS6” until steward/product evidence selects it.

---

## 4. Authority law — remains settled

```text
WORLD truth
→ DungeonMind authority

Buddy product/runtime state
→ Buddy Application State authority
```

One Buddy PostgreSQL substrate does **not** imply one generic domain model.

Do not:

- create a generic arbitrary-JSON application object table for every surface;
- put Buddy Runtime state into DungeonMind graph tables;
- create SQL foreign keys from Buddy application-state tables into DungeonMind authority tables;
- make CDN URLs/filesystem paths product identity;
- create unused future-domain tables before selecting a real consumer;
- retain predecessor file authority behind fallback toggles after a switch.

---

## 5. Current latency evidence to retain

AS3 measured Runtime CAS at roughly `74 ms` p95 against an original `50 ms` hypothesis. That hypothesis was not a merge gate and remains a performance observation for live table dogfood.

AS4 active-Run evidence measured PostgreSQL resume around `121 ms` p95. Treat future table-breaking latency as product evidence, not an excuse for speculative infrastructure work.

---

## 6. Collision / sequencing rules

- CUTOVER may proceed in parallel when write leases are disjoint.
- PLAY-SURFACE BF2/BF3 may proceed; APP-STATE has no active Play migration slice.
- An AS6+ family may begin only after re-anchor and independently useful product justification.
- If a selected family shares bootstrap/root dependency files with another active lane, serialize that overlap explicitly.
- No successor may reopen old Play filesystem authority as a convenience fallback.

---

## 7. End-state test for this roadmap

The application-state program is successful when Buddy durable product objects:

1. have stable domain identity independent of storage coordinates;
2. persist behind owning domain services on Buddy PostgreSQL;
3. use DungeonMindServer storage/CDN for large bytes behind stable Asset identity where applicable;
4. preserve DungeonMind as sole World Graph authority;
5. keep derived/regenerable representations non-authoritative unless product correctness says otherwise;
6. demolish replaced persistence topology rather than accumulating fallback modes;
7. meet measured product latency/reliability needs;
8. retain true historical authored revisions where product behavior depends on them.

The Play-first proof now satisfies this model for Plan/Playable/Play Runtime. Future families enter only from evidence.
