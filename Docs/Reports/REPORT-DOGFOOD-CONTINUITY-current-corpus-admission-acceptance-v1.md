# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — zero-cost harness/preflight evidence recorded; paid dogfood not yet executed  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Branch:** `dogfood-continuity/current-corpus-admission-acceptance-v1`  
**Dispatch base:** `68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Implementation head (this report):** `9d41691d81cc44b3b7e92c4b01bde30b30d5a3b5`  
**World ID:** `dogfood-current-corpus-acceptance-v1`  
**Database:** `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329`

> Structural acceptance only. Semantic truthfulness and model selection remain HOLD even after a future PASS.

---

## 1. Claim under review

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE: HOLD
```

Reason at report time: paid `--execute` dogfood has not been run. Direction is
`CODE → ZERO-COST REVIEW → PAID DOGFOOD → REVIEW`. This report records the
harness contract, deterministic evidence, and preflight observation so a
reviewer can approve the orchestration before model/runtime spend.

---

## 2. Changed paths (§4 lease)

```text
evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
tests/test_current_corpus_admission_acceptance.py
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md
```

No production extraction, admission, genesis, identity, ontology, model-policy,
or corpus path was modified.

---

## 3. Zero-cost deterministic evidence

```bash
uv run pytest \
  tests/test_current_corpus_admission_acceptance.py \
  tests/test_recap_world_genesis.py \
  tests/test_graph_preview_runner.py \
  tests/test_candidate_graph_admission_contract.py -q

uv run ruff check \
  evals/graph_memory_layer/run_current_corpus_admission_acceptance.py \
  tests/test_current_corpus_admission_acceptance.py

git diff --check
git diff --name-only 68577114b3c8ec7e06bc0b0a8d382143fdc570ec...HEAD
```

Owning harness tests prove:

- canonical manifest sorting + digest stability
- duplicate/gapped lineage rejection
- `normalized_from` containment / original-source authority
- source drift rejection before extraction
- DSN/world mismatch refusal
- non-pristine World refusal
- exact candidate forwarding without mutation
- eligibility dispositions do not trigger repair
- nonconfirmable admission stops before governed confirm
- first failed session prevents later sessions
- parent/head chaining matches receipts
- stale head stops without re-prepare
- incomplete run has no resume-as-PASS path (new run id + pristine probe)

---

## 4. Preflight observation

Command:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --preflight
```

Recorded fields (fill from command stdout / `preflight_report.json`):

| Field | Value |
|---|---|
| git head (dispatch base at freeze) | `68577114b3c8ec7e06bc0b0a8d382143fdc570ec` |
| manifest count | `44` |
| manifest digest | `d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c` |
| C1 / C2 ranges | `longmont-c1` sessions 1–17; `longmont-c2` sessions 1–27 |
| model-policy digest | `477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212` |
| resolved production model | `gpt-5.4-mini` (via `resolve_category_graph_model(None)`; not hard-coded in runner) |
| world / DB target | `dogfood-current-corpus-acceptance-v1` / `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329` |
| pristine probe | **blocked** — empty DB lacks migrated `dungeonmind.world_graph_heads`; harness fails closed with `recap_genesis_probe` and requires operator to create a **migrated pristine** acceptance database (runner never migrates/drops/resets) |
| model calls | `0` |
| durable graph writes | `0` |

---

## 5. Paid dogfood (pending)

Not executed in this zero-cost phase.

When executed from a pristine acceptance database:

```bash
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --execute
```

Update this section with either:

1. **PASS** — full frozen manifest completed; terminal head; ledger path; digests; or
2. **HOLD** — first failing campaign/session, boundary, last good head, diagnostics.

Do not repair production seams inside the same acceptance run.

---

## 6. Claims that remain false

```text
SEMANTIC MODEL SELECTION = HOLD
no model winner exists
no semantic recall/precision/truthfulness score exists
no claim that unsupported eligibility items should become supported
no unattended production batch ingestion exists
no resume/retry scheduler exists
no live Eldyrwild rewrite has occurred
```
