# REPORT — DOGFOOD-CONTINUITY admission endpoint-kind eligibility v1

**Status:** CODE complete — awaiting review / dogfood rerun  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`  
**Branch:** `dogfood-continuity/admission-endpoint-kind-eligibility-v1`  
**Design authority base:** `68577114b3c8ec7e06bc0b0a8d382143fdc570ec`

## Claim

```text
ADMISSION ENDPOINT-KIND ELIGIBILITY: implemented
```

Candidate Graph Admission now shares the write-path endpoint-kind gate via
`edge_endpoint_kind_admission_reason`. Mapped Buddy edges whose qualified DM
subject/object kinds are not vocabulary-admitted receive sealed dispositions
(`endpoint_kind_not_admitted`) and are omitted from the eligibility projection.
The exact candidate digest still hashes the complete original candidate.

## Dogfood witness (pre-repair)

Preserved `longmont-c1/session-1` candidate from acceptance HOLD:

- 4× `unmapped_predicate` (unchanged)
- 3× newly dispositioned `endpoint_kind_not_admitted`
  (`belongs_to` npc→group, `participates_in` creature→group, `present_at` npc→creature)
- 12 remaining edges: zero endpoint-kind failures under the shared helper

## Verification

```text
uv run pytest tests/test_candidate_graph_admission_contract.py tests/test_graph_preview_runner.py -q
34 passed
```

## Remains false

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = HOLD until fresh pristine --execute PASS
no ontology expansion
no semantic model selection
```
