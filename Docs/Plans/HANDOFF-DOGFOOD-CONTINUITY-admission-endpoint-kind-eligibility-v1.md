# HANDOFF — DOGFOOD-CONTINUITY admission endpoint-kind eligibility v1

**Created:** 2026-09-15  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`  
**Conversation/workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`  
**Flow / owner:** `DOGFOOD-CONTINUITY`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `main@68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Activation gate:** `none — satisfied` (predecessor dogfood STOP on #722 execute is observational evidence, not a merge gate)  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff; record exact implementation branch base at dispatch/review.  
**PR title:** `DOGFOOD-CONTINUITY: fail closed on inexpressible edge endpoint kinds at admission`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Successor to structural STOP recorded in
> `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`
> (`dungeonmind_write` / `governed_write_inexpressible` / `endpoint_kind_not_admitted`
> on `longmont-c1/session-1`).

## §1 Mission and merge-ready invariant

**Mission:** Candidate Graph Admission dispositions mapped Buddy edges whose
qualified DM endpoint kinds are not vocabulary-admitted, so confirm never
attempts a governed write that the write path will reject as inexpressible.

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
| Can one invariant govern every claimed observable path? | Yes — admission eligibility only |
| Most likely adversarial sequence | Mapped predicate + illegal endpoints still confirmable → write 409 |
| Will §7 actually detect that failure? | Contract test + dogfood candidate replay |
| Easiest owning boundary to under-test | Eligibility loop vs write-path `_assert_edge_endpoint_admission` drift |
| Fact that forces stop/split | Widening ontology / making unsupported predicates supported |

## §2 Context

| Field | Content |
|---|---|
| Parent authority | Candidate integrity vs eligibility boundary (#721); acceptance dogfood HOLD |
| Predecessor | Paid acceptance STOP at `dungeonmind_write` for three mapped-but-inexpressible edges |
| Named successor | Fresh current-corpus acceptance `--execute` from pristine authority |
| Explicit non-goals | Ontology expansion; extraction prompt changes; skip/resume; write-path softening; semantic scoring |
| State-authority sync set after merge | Consume this handoff; update acceptance REPORT after rerun (separate) |

## §3 Observable paths

| Path | Current | Required | Owning boundary |
|---|---|---|---|
| `belongs_to` character→group | confirmable → write inexpressible | disposition `endpoint_kind_not_admitted` | candidate admission |
| `present_at` / `participates_in` illegal objects | same | same | candidate admission |
| legal `located_in` etc. | confirmable | still confirmable | candidate admission |
| exact candidate digest | hashes full input | unchanged | candidate admission |

## §4 Write lease (exclusive while ACTIVE)

```text
apps/live_control_server/integrations/dungeonmind/assertion_qualification.py
apps/live_control_server/services/candidate_graph_admission.py
tests/test_candidate_graph_admission_contract.py
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md
```

**Out of scope:** extraction runners, ontology vocabulary expansion, `world_graph_writes.py`
behavior changes, acceptance harness, corpus, model policy.

## §5–§6 Non-goals / stop signs

Do not expand DungeonMind predicate endpoint kinds to “make the dogfood pass.”
Do not delete edges from the caller’s candidate. Do not skip sessions.

## §7 Evidence

```bash
uv run pytest tests/test_candidate_graph_admission_contract.py tests/test_graph_preview_runner.py -q
uv run ruff check \
  apps/live_control_server/integrations/dungeonmind/assertion_qualification.py \
  apps/live_control_server/services/candidate_graph_admission.py \
  tests/test_candidate_graph_admission_contract.py
```

Optional dogfood follow-up (after merge + pristine reset), using the acceptance harness:

```bash
# recreate migrated pristine dmb_current_corpus_acceptance_v1 @ 127.0.0.1:54329
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --execute --dsn "$DSN"
```

## §8 Done when

- Illegal endpoint edges receive sealed `endpoint_kind_not_admitted` dispositions
- Remaining legal edges stay confirmable
- Exact candidate digest unchanged
- Compact REPORT records the repair claim without semantic overclaim
