# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — paid dogfood stopped on first owning-boundary failure  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Branch:** `dogfood-continuity/current-corpus-admission-acceptance-v1`  
**Dispatch base:** `68577114b3c8ec7e06bc0b0a8d382143fdc570ec`  
**Implementation / execute head:** `67c4c9759df277017c94351c488253e98a9df54a`  
**World ID:** `dogfood-current-corpus-acceptance-v1`  
**Database:** `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329`

> Structural acceptance only. Semantic truthfulness and model selection remain HOLD even after a future PASS.

---

## 1. Claim under review

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE: HOLD
```

Paid `--execute` ran fresh from a migrated pristine acceptance database and
stopped on the first owning-boundary failure. This is not a partial PASS.

---

## 2. Changed paths (§4 lease)

```text
evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
tests/test_current_corpus_admission_acceptance.py
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md
```

No production extraction, admission, genesis, identity, ontology, model-policy,
or corpus path was modified for this dogfood observation.

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

Command (after operator created migrated pristine DB; runner does not migrate):

```bash
DSN='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dmb_current_corpus_acceptance_v1'
export DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL="$DSN"
export DUNGEONMIND_DATABASE_URL="$DSN"
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --preflight --dsn "$DSN"
```

| Field | Value |
|---|---|
| git head | `67c4c9759df277017c94351c488253e98a9df54a` |
| manifest count | `44` |
| manifest digest | `d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c` |
| C1 / C2 ranges | `longmont-c1` sessions 1–17; `longmont-c2` sessions 1–27 |
| model-policy digest | `477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212` |
| resolved production model | `gpt-5.4-mini` (via `resolve_category_graph_model(None)`; not hard-coded) |
| world / DB target | `dogfood-current-corpus-acceptance-v1` / `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329` |
| pristine probe | **ok** (migrated empty authority; zero worlds before execute) |
| model calls | `0` |
| durable graph writes | `0` |
| preflight output | `out/graph_memory/current_corpus_admission_acceptance_v1/preflight-2026-09-15T222522Z-45defb00` |

---

## 5. Paid dogfood result — HOLD (first STOP)

Command:

```bash
DSN='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dmb_current_corpus_acceptance_v1'
export DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL="$DSN"
export DUNGEONMIND_DATABASE_URL="$DSN"
# APP-STATE postgres required for extraction artifact seams (127.0.0.1:54331)
uv run python evals/graph_memory_layer/run_current_corpus_admission_acceptance.py --execute --dsn "$DSN"
```

```text
STRUCTURAL ACCEPTANCE: HOLD
first failing campaign/session: longmont-c1 / session-1
last verified good head: rev:b31956daf4790c79426381b90cc3fc69  (genesis D0 only)
failure boundary: dungeonmind_write
production error: governed write failed: confirmed edge endpoint kinds are not admitted for the qualified predicate
diagnostic: governed_write_inexpressible
candidate preserved: yes
model calls already spent: 1
graph writes completed: 1 (genesis only; no session child sealed)
sessions not attempted: 44 (including the failing session-1; no later session extraction)
```

| Field | Value |
|---|---|
| run id / output | `execute-2026-09-15T222551Z-0370aaca` under `out/graph_memory/current_corpus_admission_acceptance_v1/` |
| git head | `67c4c9759df277017c94351c488253e98a9df54a` |
| manifest digest | `d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c` |
| model-policy digest | `477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212` |
| resolved model | `gpt-5.4-mini` |
| genesis D0 | `rev:b31956daf4790c79426381b90cc3fc69` |
| current World head after STOP | `rev:b31956daf4790c79426381b90cc3fc69` (unchanged; write refused) |
| candidate locator | `…/candidates/longmont-c1-session-1.json` |
| candidate digest | `339999f9efcfa1aa912fdd35f397484be696a50fc1f48b53032e2fbccc0bf2a6` |
| candidate shape | 53 nodes / 19 edges / 7 beats / 0 proposed_writes |
| acceptance_report.json | present under the run output dir |

Sanitized candidate edge endpoint inventory (no labels/corpus text):

```text
within: location -> location (5)
located_in: location -> location
governs: character -> location
owns: character -> item
located_in: item -> location
knows_about: character -> character
reports_threat_in: character -> location
north_of: location -> location
near: location -> location
same_as: location -> location
located_in: group -> location
belongs_to: character -> group
participates_in: creature -> group
located_in: creature -> location
present_at: character -> creature
```

No production repair, skip, resume, or selective regenerate was performed.
Live Eldyrwild / cutover authority DBs were not targeted (`54329` acceptance DB only;
process env pinned `DUNGEONMIND_*_DATABASE_URL` to the same DSN).

**Cost:** 1 production extraction model call (`gpt-5.4-mini`) before STOP. No
`scenario_estimated_cost_usd` sidecar was emitted by this harness; dollar cost not
recorded in run artifacts.

### Immediate successor (per handoff)

One narrowly scoped repair handoff for the first failing production boundary
(`dungeonmind_write` / qualified-predicate endpoint-kind admission), then a
**fresh** structural acceptance rerun from a pristine authority. Do not proceed
to semantic evaluation until structural PASS.

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
STRUCTURAL CURRENT-CORPUS ACCEPTANCE remains HOLD
```
