# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-17  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor input base:** `main@4ee958a70a6f43b7fdca6c34476f56aae28c78b6` — guided Stage 4 WOW operator pass recorded  
**Current product frontier:** Stage 4 recap / UI-language — **human pass HOLD**; next slice is steward/design  
**Active implementation PR:** **NONE**  
**UI-language authority:** [`HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md)  
**Recorded operator pass:** [`../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md)  
**Completed dogfood handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md)  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)  
**Execution roadmap:** [`../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md)

> Repository truth supersedes chat reconstruction. The current instruction is: **design the next UI-language slice from the recorded human pass; do not dispatch 7A1 or the semantic gauntlet automatically.**

---

## 0. Pickup rule

Begin with:

> **If the operator cannot dogfood it through the normal product, it is not ready.**

Read, in order:

1. this anchor;
2. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`;
3. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`;
4. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`;
5. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`;
6. `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`, Stage 4;
7. older campaign-memory reports only when diagnosing a concrete failure.

There is **no active implementation lease** from this anchor.

Do not open a PR merely because an old successor was queued.

---

## 1. What journey we were actually on

The product-level mission before the campaign-memory detour was the UI-language / Stage 4 WOW pass.

The accepted design grammar was:

```text
cheap chrome
expensive current work
chip → glance → peek
related objects do not navigate away
one coherent secondary context
Agent cheap/absent when not useful
```

That line produced:

```text
#700 / UI-01   shared Peek                         MERGED
#701 / UI-02   truthful Agent dock/presence        MERGED
#702 / UI-03   responsive secondary context        MERGED
#704 / Stage4B recap World-reference glance        MERGED
```

Stage 4B then reached its **human WOW gate** and exposed a deeper problem:

> the interaction mechanics were becoming testable, but accumulated campaign memory was inaccessible, incomplete in ordinary product reads, or too awkwardly addressed to judge the UX honestly.

That was the sidequest.

It did **not** replace the UX roadmap.

---

## 2. What the sidequest established

The detour progressively made real campaign memory usable enough to return to product design.

Accepted foundation:

```text
44-session structural current-corpus acceptance             PASS
candidate admission / governed write continuity             PASS
fresh recap source-provenance admission                     PASS  (#729)
exact 44-candidate zero-model pristine replay               PASS  (#730)
recap evidence → digest-verified exact source read           PASS  (#731)
published-memory browse authority                           PASS  (#732)
browse/write authority separation                           PASS  (#732)
```

PR #732:

- accepted implementation head: `2ae0718f2976a1fee5ee299a997ec3292d64fab1`;
- formal Review Cycle 5: **APPROVE**, review `5243724921`;
- merged to `main`: `b3d1a146f6ccc8ff84e5b4be65d8a84a4d98cb44`.

#732 makes ordinary Graph Review browsing mean:

```text
Campaign + Focus session
→ published recap
→ token/glance
→ complete durable World object
→ relationships / origin / evidence
```

without requiring ExtractionRun selection and without granting implicit write authority.

The operator had already demonstrated that the spike version of this interaction model unlocked useful dogfood. The intentional rewrite is merged. The post-merge human UX witness is **recorded**.

---

## 3. Current action — design from the recorded human pass

**Do not code first. Do not dispatch 7A1 or the semantic gauntlet automatically.**

The guided operator pass is recorded in [`../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md).

Recommended steward outcome from that report: **B** — one UI-language successor for chip → glance → peek as campaign information. The `longmont-c2:27` session-identity abort may be serialized immediately before or inside that slice. Semantic thinness/wrong kind is real and is not the first dispatch.

---

## 4. Why the semantic gauntlet is not automatically next

The fixed C1S1–10 question gauntlet remains useful evidence.

It is **not the current dispatch**.

The old anchor said to run it after #732. That sequencing was written while the primary question was still whether campaign memory could be product-loaded at all.

The sidequest now answers enough of that substrate question to resume the UI pass that originally triggered it.

The human pass showed both presentation failure on the first object *and* real semantic thinness/wrong kind. Presentation spoiled the first minutes; later C1 cultists still created pull. The gauntlet remains useful and is **not** the current dispatch unless the steward rejects B.

---

## 5. Queued work that remains queued

Do not dispatch these merely because #732 merged:

- Stage 7A1 contextual Ask on the loaded recap;
- the 16-question semantic gauntlet as an automatic successor;
- Agent tuning;
- broad graph-ingestion redesign;
- Play parchment/whole-app paint rewrite;
- Combat;
- cleanup of legacy Graph Review catalog components;
- historical accepted-World backfill.

7A1 remains a valid capability. It was explicitly queued **behind the UI design series**. That sequencing still applies.

---

## 6. Current acceptance labels

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE             PASS
FRESH GOVERNED RECAP WRITE                       PASS
EXACT ACCEPTED-CANDIDATE REPLAY                  PASS
RECAP SOURCE-READ CONTINUITY                     PASS
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY   PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION   PASS

STAGE 4 / RECAP WOW                              HOLD — human pass recorded, not satisfying
OPERATOR DOGFOOD ON MERGED #732                  RECORDED
SEMANTIC COVERAGE                                NOT MEASURED
AGENT ANSWERABILITY                              NOT MEASURED
SEMANTIC MODEL SELECTION                         HOLD
```

Do not promote Stage 4 or operator dogfood from automated evidence alone.

---

## 7. Next state transition

There is intentionally no preselected implementation PR.

The human UX/WOW pass is recorded. The operator-pass report recommends **B**. The steward still chooses the dispatched outcome; do not treat the report as a write lease.

```text
A. UX is good; semantic memory quality is now the earliest blocker
   → design/dispatch semantic gauntlet or semantic repair.

B. One bounded UX defect dominates          ← report recommendation
   → design one UI-language successor slice and land its handoff.

C. Product path still fails structurally
   → localize earliest broken boundary and repair only that boundary.

D. UX is satisfying and no immediate blocker dominates
   → record Stage 4 disposition, re-anchor, then choose between
      remaining UI-language work, semantic evaluation, and queued 7A1.
```
