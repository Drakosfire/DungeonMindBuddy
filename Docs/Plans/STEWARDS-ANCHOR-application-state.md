# STEWARD'S ANCHOR — APPLICATION STATE

**Status:** ACTIVE ARCHITECTURE PICKUP — PLAY-FIRST SEQUENCE COMPLETE; NO PRE-AUTHORIZED AS6  
**Line of work / flow:** `APP-STATE`  
**Created:** 2026-08-24  
**Updated:** 2026-08-26  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Current completion anchor:** PR #650 merge `cc016661f80416e0816f56349217cf33c53a195f`  
**Architecture:** [`../Design/ARCHITECTURE-application-state-layer.md`](../Design/ARCHITECTURE-application-state-layer.md)  
**Roadmap:** [`../Roadmaps/ROADMAP-application-state.md`](../Roadmaps/ROADMAP-application-state.md)  
**Repository law:** [`../../AGENTS.md`](../../AGENTS.md)  
**Primary adjacent Play authority:** [`../Design/ARCHITECTURE-playable-material-and-runtime.md`](../Design/ARCHITECTURE-playable-material-and-runtime.md)

---

## 0. Pickup truth

The activation question that created APP-STATE has been answered for the Play-first program.

```text
AS0   DESIGN                 DONE
AS0.1 STORAGE TOPOLOGY       DONE
AS1   PLAN                   DONE
AS2   PLAYABLE               DONE
AS3   PLAY RUNTIME           DONE
AS4   PLAY CONTINUITY        DONE
AS5   PLAY DEMOLITION        DONE
AS6+  UNSELECTED
```

AS5 / PR #650:

- merge: `cc016661f80416e0816f56349217cf33c53a195f`
- accepted head: `3477d1c581bbcf4898a66aec43a82cdc3bb84b8f`
- review cycles: **1**
- final PASS-equivalent review: `5034313758`
- exact-head evidence comment: `5429758776`

Do not describe AS5 as active/unmerged. Do not invent an AS6 merely to continue numbering.

---

## 1. Mission that remains authoritative

> **DungeonBuddy surfaces persist durable Buddy-owned product state through domain-owned services on a shared PostgreSQL application-state substrate, while DungeonMind remains World Graph authority and storage coordinates never become product identity.**

```text
Surface
→ domain capability/service
→ domain invariant + transaction boundary
→ Buddy Application State Layer
→ PostgreSQL
```

Large binary bytes belong behind stable Asset identity and external storage/CDN when that family is selected.

The shared substrate does **not** mean one generic domain model.

---

## 2. Settled authority law

```text
WORLD truth → DungeonMind authority
Buddy product/runtime state → Buddy authority
```

Do not:

- put Play/Plan/Combat runtime into DungeonMind graph tables;
- make SQL foreign keys across Buddy/DungeonMind authority databases;
- create a generic arbitrary-JSON “everything” table;
- use paths/URLs/bucket keys as durable identity;
- create future-domain tables before a real consumer is selected;
- retain switched file authority behind fallback toggles.

---

## 3. Proven content primitives

Current Buddy content foundation:

```text
WorkObject
  stable identity
  kind / scope / metadata
  current committed revision

WorkRevision
  immutable revision identity
  revision_n
  canonical bytes
  content_sha256
  provenance / timestamps

WorkingCopy
  mutable recoverable draft
  exact base revision
```

Historical invariant:

> **Revision N remains loadable after revision N+1 is committed.**

A Play Run pins exact committed revision identity and digest. Current/latest workspace state is not substitute authority.

---

## 4. Proven Play Runtime substrate

Current PostgreSQL authority includes:

```text
play.run
play.run_manifest
play.active_run
```

Proven behavior:

- atomic Run + manifest sealing;
- exact replay/idempotency and integrity proof;
- SQL `run_revision` CAS;
- preserve-only transactional rebase;
- active Run set/get/clear;
- exact resume/reload from another process/worktree/root;
- DB unavailable fails closed;
- contradictory predecessor files are not fallback authority.

AS5 demolished current-product dependence on Run JSON, manifest sidecars, `active-run.json`, Play rebase intents, Play file locks, and current-production legacy Play importers.

Git history is the predecessor migration archive. Do not resurrect those modules into ordinary runtime.

---

## 5. Product consequence: Play Surface is unblocked

APP-STATE no longer owns an active Play migration slice.

PLAY-SURFACE may proceed:

```text
BF2  v2 READY / current-position / relevance
↓
BF3  Scene-centered current-moment cockpit
```

A persistence concern discovered during BF2/BF3 should be treated as a new concrete defect/evidence item, not as permission to reopen AS1–AS5 architecture wholesale.

Combat remains separate and may later be selected as an APP-STATE family. Play's completion does not imply Combat durability.

---

## 6. Selecting a future APP-STATE family

A future steward may select a candidate only when all are true:

1. a concrete user-relied-on durable state currently depends on unsafe/local topology;
2. migration creates one independently useful product outcome;
3. the owning domain is explicit;
4. authority does not collapse into a generic application object model;
5. predecessor import/cutover/demolition can be stated honestly;
6. the slice has owning-boundary evidence and fail-closed behavior;
7. storage identity is distinct from product identity.

Candidate families currently include:

- Combat;
- Ingest processing/review;
- SourceArtifact identity/provenance;
- generated-artifact project/draft lifecycles;
- Asset metadata + DungeonMindServer bytes;
- remaining `worldbuilding_source` / content;
- optional Agent task/proposal durability only if product correctness requires it;
- explicit Plan publish-to-corpus;
- optional Run mutation history.

These are **not** pre-authorized schemas or PR names.

---

## 7. Review and migration law for any successor

For each selected family:

- record exact branch/base SHA;
- use a bounded write lease;
- migrate one real consumer before broad abstraction;
- prove real PostgreSQL execution with zero silent skips;
- compare predecessor/current latency where table/user speed matters;
- fail closed on DB unavailability after switch;
- prove predecessor state adoption when real state exists;
- switch ordinary reads/writes fully;
- then demolish replaced topology rather than retaining a compatibility mode indefinitely;
- synchronize roadmap/anchor backward-looking only after merge truth exists.

Exact-head formal review and distinct-head review-cycle counting remain mandatory.

---

## 8. What remains false

- no AS6 has been selected;
- Combat durability is not implied by Play completion;
- Ingest/SourceArtifact/Asset/generated-artifact application-state families are not implemented merely because the substrate can support them;
- CUTOVER graph-engine demolition remains a separate lane;
- global product durability/CR-U17 is not complete merely because Play is durable.

The correct next APP-STATE action is therefore **wait for evidence**, not invent another migration slice.
