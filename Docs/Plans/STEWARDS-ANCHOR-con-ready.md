# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-17  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor base:** `main@65b0c6a369a012dd1ba2c5a7a3410b07b7ac6345` — published-memory Graph Review browse handoff landed  
**Structural current-corpus acceptance:** PASS  
**Fresh governed recap source-provenance contract:** PASS — PR #729  
**Exact accepted-candidate replay:** PASS — PR #730  
**Recap source-read continuity:** PASS — PR #731 merged `9e739057540e52e763ba9fc6a62d2f1ef5ac2f96`  
**Product loadability contracts:** PASS for fresh provenance-correct publication/read path; historical/replay Worlds remain immutable witnesses  
**Operator dogfood:** successful on #732 spike behavior, not yet accepted as durable `main` authority  
**Active lane:** [`HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md)  
**Active PR:** existing #732 only — implementation may be substantially rewritten  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)  
**Benchmark authority:** [`../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md`](../Backlog/AGENT-GRAPH-QUERY-BENCHMARK.md)

> This is the current sequencing authority. Repository truth supersedes chat summaries, branch-only reports, and stale current-state prose elsewhere.

---

## 0. Pickup rule

Every steward/worker begins with:

> **If the operator cannot dogfood it through the normal product, it is not ready.**

Read, in order:

1. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
2. this anchor;
3. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`;
4. PR #732 Review Cycle 1 only as spike/review evidence, not implementation authority;
5. accepted predecessor reports when historical context is needed.

There is one serial implementation lane: **PR #732**.

Do not open a second PR.

---

## 1. Where we are

The campaign-memory line has removed the upstream structural blockers in sequence.

### Graph/write/read foundation

Accepted results:

```text
44-session structural ingestion                     PASS
fresh governed recap source provenance             PASS
exact 44-candidate zero-model replay                PASS
published object identity round-trip                PASS
recap evidence → digest-verified exact source span  PASS for fresh post-#731 writes
```

PR #731 closed the source-read contract:

```text
candidate canonical source_span_ref_id
→ governed recap evidence stamp
→ DungeonMind persisted locator + admitted repo URI
→ Buddy source anchor
→ digest-verified exact recap span
```

The graph machinery is no longer the current frontier.

### Gate C dogfood exposed the product-authority problem

The operator then attempted real Graph Review dogfood.

PR #732 changed the ordinary interaction so the operator could:

```text
select Campaign + Focus session
→ read published recap directly
→ click graph mentions
→ inspect complete durable objects + useful relationship/origin prose
→ switch C1/C2 and sessions
```

With those behaviors present, the operator was able to dogfood and reported satisfaction with the workflow.

That is accepted **empirical product evidence**.

PR #732's implementation itself is **not accepted architecture**. Formal Review Cycle 1 on head:

`dd4db027994f326af4434d2c0dd74f18abbb2509`

was HOLD, review:

`5242516505`

because:

1. no steward handoff had authorized the broad UI rewrite;
2. published recap selection could diverge from Graph Review's run/write authority;
3. the supposedly ordinary published-memory browse path still waited on ExtractionRun catalog settlement.

The correct conclusion is not “discard the dogfood result.”

It is:

> **Keep the interaction model that unlocked dogfood; redesign the authority boundaries deliberately.**

---

## 2. Current product model

The active handoff establishes two separate authorities.

### Published-memory browse authority

Ordinary Graph Review browsing is governed by:

```text
world
campaign
focus session
revision/head policy
admissibility
```

Its source is the published World Graph.

It does **not** require an ExtractionRun.

### Write/author authority

Anything capable of prepare/confirm/promote/write requires an explicit write-capable binding.

A visible published recap does not grant mutation authority.

Exact-run handoff remains a separate explicit authority path.

This distinction is the current design center:

```text
PublishedMemoryBrowseContext != GraphReviewWriteAuthority
```

---

## 3. ACTIVE lane

Canonical handoff:

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-published-memory-graph-review-browse-v1.md`

Topology:

`serial`

Authorized PR:

`#732`

Authorized branch:

`dogfood/graph-review-recap-campaign-session`

Required title after update:

`DOGFOOD-CONTINUITY: make published campaign memory the Graph Review browse authority`

The worker must rebase/update #732 onto the `main` commit containing the handoff.

The current #732 diff is disposable. The worker may replace it substantially.

The behavior/objectives are not disposable.

---

## 4. Merge-ready product invariants

The active slice must prove:

1. ordinary Graph Review loads published recap memory from Campaign + Focus session without run-selection ceremony;
2. valid published recap browsing mounts independently of ExtractionRun catalog latency/emptiness/failure;
3. recap projection, World Graph lens, URL, complete-object inspection, and revision context remain coherent;
4. graph mention click opens the complete durable World object at the same revision/focus;
5. useful relationship/source/origin context appears when complete-object returns it;
6. Ingest bare `?campaign=` is campaign-scoped;
7. legitimate world-union responses may omit a single campaign identity without false mismatch;
8. campaign-scoped mismatches still fail closed;
9. browsing does not silently acquire stale/default run/write authority;
10. explicit exact-run review remains exact-run authority and still fails closed on identity mismatch.

Do not solve ordinary browsing by weakening write authority.

Do not solve authoring by making browsing depend on ExtractionRun state again.

---

## 5. #732 disposition

PR #732 remains open and is intentionally reused as the one implementation lane.

The next worker action is:

```text
rebase/update #732 onto current main
read the new handoff
rewrite as needed
request formal review on a distinct head SHA
```

Do not preserve code merely because it existed in the spike.

Do not open a replacement PR.

The reviewer will judge the handoff invariants, not similarity to `dd4db027...`.

---

## 6. Human acceptance

The final Gate C witness must reproduce the interaction that worked during dogfood:

```text
pick campaign/session
read recap
click campaign-memory mentions
explore complete objects and relationships
follow provenance when useful
switch campaign/session
refresh
continue
```

And separately prove:

```text
browse-only context cannot mutate through stale run authority
explicit exact-run mode still works
```

If the intentional implementation reproduces the successful experience, steward may record:

```text
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY = PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION = PASS
OPERATOR DOGFOOD = PASS
```

for this campaign-memory exploration workflow.

---

## 7. After this slice

Once #732 is intentionally implemented, reviewed, merged, and re-dogfooded:

1. sync/re-anchor;
2. return to the fixed 16-question C1S1–10 semantic gauntlet on the provenance-correct World/revision;
3. distinguish semantic graph failures from Agent failures;
4. repair earliest A/B/C/E boundary before Agent tuning.

The next phase is intended to answer:

> **Now that a human can actually use campaign memory, is that memory semantically good enough?**
