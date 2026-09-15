# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** HOLD — paid dogfood stopped on first owning-boundary failure (post endpoint-kind repair)  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Branch (harness):** `dogfood-continuity/current-corpus-admission-acceptance-v1` (#722)  
**Rerun head:** `560a5eb92501334b5ef48558fe0ea91f022e0239` (acceptance tip + endpoint-kind eligibility cherry-pick `213e0cc5` / #723)  
**World ID:** `dogfood-current-corpus-acceptance-v1`  
**Database:** `dmb_current_corpus_acceptance_v1` @ `127.0.0.1:54329`

> Structural acceptance only. Semantic truthfulness and model selection remain HOLD.

---

## 1. Claim under review

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE: HOLD
```

Fresh pristine `--execute` after the admission endpoint-kind eligibility repair
cleared the prior `dungeonmind_write` STOP on `longmont-c1/session-1`, then
stopped on the next owning boundary.

---

## 2. Changed paths (§4 lease — harness)

```text
evals/graph_memory_layer/run_current_corpus_admission_acceptance.py
tests/test_current_corpus_admission_acceptance.py
Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md
```

Production admission repair is owned by #723 / handoff
`HANDOFF-DOGFOOD-CONTINUITY-admission-endpoint-kind-eligibility-v1.md`.

---

## 3. Zero-cost deterministic evidence

Unchanged from harness implementation on #722 (owning harness tests + ruff).

---

## 4. Preflight observation (rerun)

| Field | Value |
|---|---|
| git head | `560a5eb92501334b5ef48558fe0ea91f022e0239` |
| manifest count | `44` |
| manifest digest | `d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c` |
| model-policy digest | `477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212` |
| resolved model | `gpt-5.4-mini` |
| pristine probe | **ok** (DB recreated + alembic upgraded before rerun) |
| model calls | `0` |
| durable graph writes | `0` |

---

## 5. Paid dogfood results

### 5a. First execute (pre-repair) — STOP `dungeonmind_write`

```text
run: execute-2026-09-15T222551Z-0370aaca
session: longmont-c1 / session-1
boundary: dungeonmind_write
error: confirmed edge endpoint kinds are not admitted for the qualified predicate
last good head: rev:b31956daf4790c79426381b90cc3fc69 (genesis only)
```

### 5b. Fresh execute after endpoint-kind eligibility repair — STOP `production_extraction`

```text
STRUCTURAL ACCEPTANCE: HOLD
run: execute-2026-09-15T223508Z-ebcaaa0b
first failing campaign/session: longmont-c1 / session-2
last verified good head: rev:3596dd0e49da7867a2ff352ab1334441
failure boundary: production_extraction
production error: production extraction failed: validation
diagnostic: candidate graph typed validation failed: duplicate_node_id: duplicate id: node:glowkindle
candidate preserved: yes (extraction/session-2 artifacts)
model calls already spent: 1 counted at STOP envelope (session-1 sealed; session-2 failed inside extraction)
graph writes completed: 2 (genesis D0 + session-1 child)
sessions sealed before STOP: 1 (longmont-c1/session-1)
sessions not attempted: 43 (including failing session-2)
```

| Field | Value |
|---|---|
| genesis D0 | `rev:b31956daf4790c79426381b90cc3fc69` |
| session-1 child / current head at STOP | `rev:3596dd0e49da7867a2ff352ab1334441` |
| session-1 candidate digest | `ed0aa5602d1abcf2a0780e6255a583df3a10be17fe7a424c6c9239a095f153bf` |
| session-1 accepted proposals | `57` |
| session-1 dispositions | 3× `endpoint_kind_not_admitted`, 2× `unmapped_predicate` (eligibility; confirm proceeded) |

Prior `dungeonmind_write` / endpoint-kind STOP is cleared by #723 behavior under dogfood.

### Immediate successor

Narrow repair for **production extraction** duplicate `node_id` integrity
(`duplicate_node_id: node:glowkindle` on `longmont-c1/session-2`), then fresh
pristine acceptance rerun. Do not widen ontology or skip sessions.

---

## 6. Claims that remain false

```text
SEMANTIC MODEL SELECTION = HOLD
STRUCTURAL CURRENT-CORPUS ACCEPTANCE remains HOLD
no unattended production batch ingestion
no live Eldyrwild rewrite has occurred
```
