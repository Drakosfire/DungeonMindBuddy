# HANDOFF — DOGFOOD-CONTINUITY candidate graph admission contract v1

**Created:** 2026-09-15  
**Consumed:** 2026-09-15  
**Status:** CONSUMED — implementation merged; no implementation lane or write lease remains  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-graph-admission-contract-v1.md`  
**Conversation/workstream:** `DOGFOOD-CONTINUITY / campaign-memory ingestion`  
**Design authority base:** `68a4abae9635211bc773d8480ec6ce46b10ada5e`  
**Reviewed implementation head:** `1d490928b556a8672b56d9f4b6c4fca35e3c4e54`  
**Final review:** Cycle 4 APPROVE — review `5213358854`  
**Merged PR:** #720 — `DOGFOOD-CONTINUITY: establish candidate graph admission contract`  
**Merge SHA:** `2e054ce928f4a7de14a4a7b745460c85a90f8ee1`  
**Historical frozen notebook:** PR #715, head `820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed`, CLOSED UNMERGED

> This file is now a consumed capability record, not dispatch authority. The full pre-merge implementation contract remains available in Git history. New work must receive a new steward-owned handoff.

---

## 1. Shipped invariant

The production boundary is now:

```text
exact candidate artifact
  → candidate-document integrity
  → candidate admission qualification
  → sealed admission decision
  → governed confirmation
  → existing DungeonMind World write
```

The binding rule is:

> Candidate input is immutable authority. Admission may accept, reject, or leave candidate meaning unresolved, but it may not rewrite candidate semantics merely to make graph publication succeed.

The implementation distinguishes:

- **candidate integrity failure** — the candidate itself is incoherent, such as conflicting duplicate IDs;
- **admission eligibility** — a coherent candidate concept cannot currently be represented or admitted, such as unsupported `sublocation`, an unmapped predicate, or unresolved identity;
- **governed confirmation** — only the exact sealed candidate/source/parent decision may advance the World.

A plan is `confirmable` only when the final sealed accepted-assertion union contains at least one truthfully admissible assertion. This is evaluated after identity resolution and across contribution slices, including standing context.

---

## 2. Production authority now on `main`

Primary owning paths:

```text
apps/live_control_server/models/candidate_graph_admission.py
apps/live_control_server/services/candidate_graph_admission.py
apps/live_control_server/services/extract_promote.py
src/graph_memory/extract_promote_ops.py
src/graph_memory/extract_promote_proposal.py
tests/test_candidate_graph_admission_contract.py
tests/fixtures/candidate_admission/pr715_failure_witnesses.json
```

The existing DungeonMind-backed source-admission and governed World-write paths remain authoritative. #720 did not create a second source-authority system or graph-write engine.

---

## 3. Accepted evidence

Exact reviewed head:

```text
1d490928b556a8672b56d9f4b6c4fca35e3c4e54
```

Final handback reported:

```text
53 tests
0 failures
0 errors
0 skipped
fresh disposable PostgreSQL D0 → D1 → D2 witness
DungeonMind pin 63ec810a02f18c4e25af228f6fdb19d99d12579e
Ruff clean
git diff --check clean
model calls: 0
```

No GitHub Actions workflow run was attached to the reviewed head or merge commit; the accepted verification is the exact-head author-produced evidence plus independent review.

Owning regressions include:

- conflicting duplicate candidate IDs fail closed;
- unsupported `sublocation` remains in exact candidate identity and receives an explicit admission rejection;
- dependent edges, beats, and proposed writes receive explicit dispositions rather than disappearing;
- candidate drift blocks confirm;
- zero-admissible candidates seal `confirmable=false` and cannot reach the governed callback;
- identity ambiguity with zero accepted assertions is nonconfirmable;
- accepted standing-context assertions can keep a multi-contribution plan confirmable even when the recap slice admits nothing;
- exact governed retry retains provider idempotency semantics.

---

## 4. PR #715 lifecycle — complete

The accepted decision was:

```text
PR715_DISPOSITION = ARCHIVE_MINIMUM_WITNESS_THEN_CLOSE_UNMERGED
```

That decision has now been executed.

```text
PR #715
state: CLOSED UNMERGED
head: 820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed
closed: 2026-09-15
```

Durable replacement authority on `main`:

```text
tests/fixtures/candidate_admission/pr715_failure_witnesses.json
tests/test_candidate_graph_admission_contract.py
```

The branch/history may remain available as historical experiment evidence, but #715 is no longer active authority or an open lane.

The historical frozen-42 experiment remains truthfully:

```text
OpenAI exact-frozen replay: PASS
DeepSeek exact-frozen replay: STOP at C2 S9
DeepSeek sanitized continuation: DIAGNOSTIC ONLY
STRUCTURAL ACCEPTANCE: HOLD
SEMANTIC MODEL SELECTION: HOLD
```

Closing #715 does not convert that experiment into a PASS.

---

## 5. What remains false

The merge of #720 proves the admission seam, not long-horizon corpus success.

Still false:

- no fresh chronological campaign replay has exercised the merged admission boundary end-to-end;
- no current-corpus structural acceptance PASS exists;
- no semantic benchmark or model winner exists;
- the old frozen 42-session candidate set is historical evidence, not a corpus that should be repaired or rerun to manufacture a PASS;
- no unattended batch-ingestion product loop is authorized;
- no broad ontology decision has been made for currently unsupported candidate concepts such as `sublocation`.

---

## 6. Named successor

The next design question is:

> **Fresh chronological batch admission acceptance:** now that candidate → admission → governed write is a production boundary, what is the smallest trustworthy current-corpus experiment that proves long-horizon continuity without reintroducing caller-side semantic repair?

This successor is **not yet designed or dispatchable**.

A fresh Designing agent must re-anchor current `main`, re-census current canonical recaps rather than assuming the historical 42-session count, inspect current open lanes, and decide whether candidate-generation hardening is a prerequisite or a separately bounded successor.

Do not resurrect #715 as implementation authority. Do not sanitize historical candidates. Do not claim semantic model selection without a pre-existing evaluation contract.
