# HANDOFF — DOGFOOD-CONTINUITY admission endpoint-kind eligibility v1

**Created:** 2026-09-15  
**Status:** DONE — MERGED as PR #723 @ `ba0f781b6b3effb4770db3bf171a89da1ce18bae` (rebased head `70749ca8d4e6ae8c5c600218089dfaab47ace99d`); stewardship drain continues at #724  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Original design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Recovery authority:** `HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Activation gate:** `satisfied — #722 MERGED @ cba8242dee13220f1f8e41469cd6e0edc1e491fc; activation base main@cba8242dee13220f1f8e41469cd6e0edc1e491fc`  
**PR topology:** `serial`  
**PR authorization:** `ACTIVE — rebase/update/review existing PR #723 only; do not open another implementation PR`  
**PR title:** `DOGFOOD-CONTINUITY: fail closed on inexpressible edge endpoint kinds at admission`

**Activation facts:**
- Predecessor #722 merge SHA: `cba8242dee13220f1f8e41469cd6e0edc1e491fc`
- Rebased #722 head: `688852eab383e71a7380fd1efebc67617a811b33`
- Activation base: `main@cba8242dee13220f1f8e41469cd6e0edc1e491fc`
- Formal review cycles on #722 integration head: 1

> This handoff was originally created inside PR #723 instead of being landed on
> `main` before dispatch. The 2026-09-15 stewardship recovery makes the design
> durable and parks the already-open PR. BLOCKED means its §4 paths are not an
> active write lease until the steward activates this handoff at its queue turn.

## §1 Mission and merge-ready invariant

**Mission:** Candidate Graph Admission dispositions mapped Buddy edges whose
qualified DungeonMind endpoint kinds are not vocabulary-admitted, so confirm
never attempts a governed write that the write path will reject as
inexpressible.

**Merge-ready invariant:**

```text
exact immutable candidate
  → eligibility projection omits edges with endpoint_kind_not_admitted
    (and unmapped_predicate / vocabulary_missing_predicate)
  → every omission has a sealed disposition
  → confirmable projection only contains write-expressible edges
  → candidate digest still hashes the complete original candidate
```

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — admission eligibility only. |
| Most likely adversarial sequence | Mapped predicate + illegal endpoints remain confirmable → governed write rejects. |
| Will §7 detect that failure? | Candidate-admission contract tests plus later pristine acceptance. |
| Easiest owning boundary to under-test | Eligibility loop drifting from write-path endpoint admission. |
| PR topology | Serial recovery queue. #723 activates only after #722 closes. |
| Fact that forces stop/split | Ontology expansion or making unsupported predicates supported. |

## §2 Context and recovery sequencing

| Field | Content |
|---|---|
| Parent authority | Candidate integrity vs eligibility boundary (#721); acceptance harness #722. |
| Dogfood predecessor | C1S1 STOP at `dungeonmind_write` / `governed_write_inexpressible` / `endpoint_kind_not_admitted`. |
| Existing transport | PR #723, parked while this handoff is BLOCKED. |
| PR topology | `serial`. |
| Activation gate | #722 merged + synced; steward re-anchors and activates this handoff. |
| Action at activation | Rebase existing #723 onto exact current `main`; review the resulting exact head; merge only after formal approval. |
| Named successor | #724, which remains BLOCKED until #723 merges. |
| Explicit non-goals | Ontology expansion; extraction prompt changes; skip/resume; write-path softening; semantic scoring. |

Synthetic/cherry-picked combined dogfood heads are diagnostic evidence only. They do not replace review of #723 rebased onto actual `main`.

## §3 Observable paths

| Path | Current | Required | Owning boundary |
|---|---|---|---|
| `belongs_to` character→group when endpoint kinds are illegal | confirmable → write inexpressible | disposition `endpoint_kind_not_admitted` | candidate admission |
| `present_at` / `participates_in` illegal objects | same | same | candidate admission |
| legal `located_in` etc. | confirmable | still confirmable | candidate admission |
| exact candidate digest | hashes full input | unchanged | candidate admission |

## §4 Write lease — prospective while BLOCKED

```text
apps/live_control_server/integrations/dungeonmind/assertion_qualification.py
apps/live_control_server/services/candidate_graph_admission.py
tests/test_candidate_graph_admission_contract.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md
```

No path above is actively leased while this handoff is BLOCKED.

**Out of scope:** extraction runners, ontology vocabulary expansion,
`world_graph_writes.py` behavior changes, acceptance harness, corpus, model
policy, and opening any successor PR.

## §5–§6 Non-goals / stop signs

Do not expand DungeonMind predicate endpoint kinds to make dogfood pass. Do not
delete edges from the caller's candidate. Do not skip sessions. Do not open a
new repair PR from any newly observed STOP; return it to the steward.

## §7 Evidence

```bash
uv run pytest tests/test_candidate_graph_admission_contract.py tests/test_graph_preview_runner.py -q
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind/assertion_qualification.py \
  apps/live_control_server/services/candidate_graph_admission.py \
  tests/test_candidate_graph_admission_contract.py
git diff --check
git diff --name-only <activation-dispatch-base>...HEAD
```

The full paid acceptance rerun is **not** performed between every parked repair
in the recovery queue. After #722–#726 are merged onto real `main`, run one
fresh pristine full `--execute` from that actual integration state.

## §8 Review handback

Record exact rebased base/head, formal review cycle, evidence provenance, actual
changed paths, and confirmation that no additional PR was opened.

## §9 Acceptance rubric

- [ ] Handoff was activated only after #722 merge/sync/re-anchor.
- [ ] Existing #723 was rebased onto real current `main`.
- [ ] Exactly this eligibility invariant was delivered.
- [ ] No ontology/write-path softening occurred.
- [ ] No successor/repair PR was opened from this lane.
