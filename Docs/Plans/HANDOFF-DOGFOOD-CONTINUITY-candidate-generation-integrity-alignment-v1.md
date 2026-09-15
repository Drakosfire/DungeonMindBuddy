# HANDOFF — DOGFOOD-CONTINUITY candidate-generation integrity alignment v1

**Created:** 2026-09-15  
**Consumed:** 2026-09-15  
**Status:** CONSUMED — implementation merged; no implementation lane or write lease remains  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-candidate-generation-integrity-alignment-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Design authority base:** `main@55d0fbac467975d1e65ffc895f32619dac00e0a0`  
**Implementation branch base:** `1f3a814cd13ccd0ab5373b70b6234e11bb537525`  
**Reviewed implementation head:** `f8028a51dfb7c1fb5e9481559490fa39f6146249`  
**Review cycles:** 2 — Cycle 1 HOLD; Cycle 2 APPROVE after exact-head verification handback  
**Final review:** `5216154953`  
**Merged PR:** #721 — `DOGFOOD-CONTINUITY: align candidate generation integrity boundary`  
**Merge SHA:** `233c49f4cfe247c962def10446eee336ff9a042b`

> This file is now a consumed capability record, not dispatch authority. The full pre-merge implementation contract remains available in Git history. New work must consume the current ACTIVE successor handoff.

---

## 1. Shipped invariant

Production candidate generation and Candidate Graph Admission now share the same candidate-document integrity versus admission-eligibility boundary.

```text
fully assembled production candidate
  → shared typed candidate-document classification
  → true document-integrity failure: FAILED / non-reviewable
  → coherent admission-eligibility issue: REVIEWABLE unchanged
  → Candidate Graph Admission owns explicit eligibility disposition
```

The exact candidate remains immutable input. Unsupported but coherent concepts such as `sublocation` are not silently made supported, deleted, or rewritten; duplicate IDs, broken references, malformed typed parse, unexpected parse/classifier failure, and profile-owned post-extraction validation still fail closed.

---

## 2. Accepted evidence

Exact reviewed head:

```text
f8028a51dfb7c1fb5e9481559490fa39f6146249
```

Final exact-head handback reported:

```text
uv run pytest tests/test_graph_preview_runner.py tests/test_candidate_graph_admission_contract.py -q
33 passed

scoped Ruff
All checks passed!

git diff --check
clean
```

Owning regressions include:

- coherent `sublocation` reaches `REVIEWABLE` unchanged and #720 emits `unsupported_node_type`;
- duplicate node and duplicate edge IDs remain generation integrity failures;
- unexpected typed-parse/classifier exceptions persist a FAILED/non-reviewable extraction rather than escaping;
- integrity outranks eligibility when both exist;
- valid candidate semantics are unchanged by classification;
- profile post-extraction validation remains authoritative;
- Candidate Graph Admission compatibility remains intact.

---

## 3. What remains false

The merge of #721 removes the known producer/consumer classification mismatch. It does not prove long-horizon campaign ingestion.

Still false:

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = HOLD
SEMANTIC MODEL SELECTION = HOLD
no model winner exists
no semantic benchmark/truthfulness claim exists
no unattended batch-ingestion product loop exists
no broad ontology expansion exists
```

The historical frozen-42 result remains historical diagnostic evidence only; PR #715 remains closed unmerged.

---

## 4. Active successor

Current dispatch authority is:

`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`

That slice performs a fresh chronological current-corpus acceptance run through genesis → production generation → candidate admission → governed write with no caller-side repair.
