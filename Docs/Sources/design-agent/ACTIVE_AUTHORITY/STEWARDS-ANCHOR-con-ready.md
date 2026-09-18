# STEWARD'S ANCHOR — CON-READY

**Status:** ACTIVE — MANDATORY PICKUP DOCUMENT  
**Line of work:** `CON-READY / DOGFOOD-CONTINUITY`  
**Updated:** 2026-09-18  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Re-anchor input base:** `main@fd9a42501c8616d27fa1436a7b66fc6a6dfe3347` — UI-04 / #733 merged  
**Current product frontier:** UI-05 floating world-object Peek inspector  
**Active implementation PR:** **NONE** — one serial PR is authorized by the ACTIVE UI-05 handoff, not yet opened  
**Active implementation handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md)  
**UI-language authority:** [`HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md)  
**Recorded operator pass:** [`../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](../Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md)  
**Completed dogfood handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md)  
**Readiness doctrine:** [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md)  
**Execution roadmap:** [`../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md)

> Repository truth supersedes chat reconstruction. The current instruction is: **implement UI-05 from the checked-in ACTIVE handoff; do not reopen #734; do not dispatch 7A1, the semantic gauntlet, or a second PR.**

---

## 0. Pickup rule

Begin with:

> **If the operator cannot dogfood it through the normal product, it is not ready.**

Read, in order:

1. this anchor;
2. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`;
3. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui-language-design-series-v1.md`;
4. `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ui03-responsive-secondary-context-v1.md` (persistent dismiss contract);
5. `Docs/Design/ui-language/DESIGN-interaction-layer-language.md`;
6. `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-guided-stage4-wow-operator-pass-v1.md`;
7. older campaign-memory reports only when diagnosing a concrete failure.

The ACTIVE write lease is **UI-05 §4**, not this anchor. Do not open a second PR. Do not open a PR for a queued successor.

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
#733 / UI-04   campaign-information glance + peek  MERGED
```

UI-04 made glance/Peek read as campaign information. Post-merge dogfood then exposed duplicate close chrome around recap Peek. Unauthorized #734 tried to collapse that chrome but regresssed UI-03's persistent dismiss guarantee and was closed without merge (HOLD on `a9b43ed7`).

---

## 2. What the sidequest established

Accepted foundation (unchanged):

```text
44-session structural current-corpus acceptance             PASS
candidate admission / governed write continuity             PASS
fresh recap source-provenance admission                     PASS  (#729)
exact 44-candidate zero-model pristine replay               PASS  (#730)
recap evidence → digest-verified exact source read           PASS  (#731)
published-memory browse authority                           PASS  (#732)
browse/write authority separation                           PASS  (#732)
campaign-information glance + peek                          MERGED (#733 / UI-04)
```

PR #733:

- accepted implementation head: `d10c66dcd980d3b9dd9d7594938feb22413677a0`;
- merged to `main`: `fd9a42501c8616d27fa1436a7b66fc6a6dfe3347`.

---

## 3. Current action — implement UI-05

**Do not redesign extraction. Do not dispatch 7A1 or the semantic gauntlet.**

The ACTIVE handoff is:

[`HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md`](HANDOFF-DOGFOOD-CONTINUITY-ui05-floating-world-object-peek-v1.md)

```text
recap pill
→ glance
→ Peek inspector (viewport-bounded; does not scroll with recap)
→ one identity-row × that stays reachable
→ close
→ same recap
```

UI-03's persistence guarantee remains in force. The fix is a floating Peek layout region, not resurrecting AppChrome `{label} Close` and not sticky-with-guessed chrome offsets.

Parked Backlog IDEA items (DeepSeek ablation; relationship rollup) are **not** authorized.

One serial implementation PR may be opened from that handoff.

---

## 4. Why the semantic gauntlet is not automatically next

Unchanged: presentation/chrome still blocks honest Stage 4 judgment. UI-05 is the bounded chrome successor. Semantic gauntlet / 7A1 remain queued.

---

## 5. Queued work that remains queued

Do not dispatch these merely because #733 merged:

- Stage 7A1 contextual Ask on the loaded recap;
- the 16-question semantic gauntlet as an automatic successor;
- DeepSeek recap node/edge ablation (Backlog IDEA only);
- predicate-family relationship rollup (Backlog IDEA only);
- Agent tuning;
- broad graph-ingestion redesign;
- Play parchment/whole-app paint rewrite;
- Combat;
- cleanup of legacy Graph Review catalog components;
- historical accepted-World backfill.

---

## 6. Current acceptance labels

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE             PASS
FRESH GOVERNED RECAP WRITE                       PASS
EXACT ACCEPTED-CANDIDATE REPLAY                  PASS
RECAP SOURCE-READ CONTINUITY                     PASS
PUBLISHED-MEMORY GRAPH REVIEW BROWSE AUTHORITY   PASS
GRAPH REVIEW BROWSE/WRITE AUTHORITY SEPARATION   PASS
UI-04 CAMPAIGN-INFORMATION GLANCE/PEEK           MERGED (#733)

STAGE 4 / RECAP WOW                              HOLD — human pass recorded; chrome successor in flight
OPERATOR DOGFOOD ON MERGED #732                  RECORDED
SEMANTIC COVERAGE                                NOT MEASURED
AGENT ANSWERABILITY                              NOT MEASURED
SEMANTIC MODEL SELECTION                         HOLD
```

Do not promote Stage 4 from automated evidence alone.

---

## 7. Next state transition

There is one authorized serial implementation PR, not yet opened. UI-04 is merged. UI-05 is ACTIVE.

```text
UI-04 campaign-information glance + peek     MERGED (#733)
#734 peek-close-chrome attempt               CLOSED without merge (HOLD)
UI-05 floating world-object Peek inspector   ACTIVE ← current
```
