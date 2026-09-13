---
pr_body_template: |
  ## Active experiment handoff
  - Workstream: DOGFOOD-CONTINUITY / Stage 4J Campaign 2 DeepSeek graph rehearsal
  - PR: experimental notebook — **do not merge to `main`**
  - Handoff: `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4j-c2-deepseek-graph-rehearsal-v1.md`
  - Corpus prerequisite: PR #712 (`corpus/c2-session-26-27-recaps`)
  - Frozen predecessor: PR #711 (model/context selection notebook)

  ## Forcing question
  Would I rather prep Session 28 from this graph, or reopen twenty-seven recaps?

  This PR is an unmergeable experimental notebook. Success is a Session 28 dogfood query against an isolated World head, not production code to merge by inertia.
---

# HANDOFF — DOGFOOD-CONTINUITY: Stage 4J Campaign 2 DeepSeek graph rehearsal

**Created:** 2026-09-13  
**Status:** EXECUTING — experimental notebook; **DO NOT MERGE to `main` as product**  
**PR / branch:** draft notebook PR / `dogfood-continuity/stage4j-c2-deepseek-graph-rehearsal`  
**Corpus base:** `corpus/c2-session-26-27-recaps` (PR #712 — Sessions 26/27 observed recaps present)  
**Flow:** DOGFOOD-CONTINUITY / full-corpus rehearsal  
**Direction:** CORPUS MANIFEST → PATH B EXTRACT → EXTRACT-PROMOTE PREPARE → EXPERIMENT AUTO-CONFIRM → ISOLATED WORLD PUBLISH → SESSION 28 DOGFOOD

> Repository law: `AGENTS.md`. This is an explicitly non-merge experimental notebook lane. It exists to answer one product-shaped question about Campaign 2 continuity; it is not permission to promote experiment plumbing, auto-confirm behavior, or DeepSeek provider pins to production.

---

## §0 Steward ruling — experiment notebook role

### PR roles

```text
PR #710
  role: frozen historical Stage 4I baseline / salvage evidence
  state: close as historical; successor is Stage 4J
  writes: NO new implementation capability

PR #711
  role: frozen model/context selection notebook (Stage 4I.2)
  state: do not continue matrix work; Stage 4J is the successor
  merge: NO

PR #712
  role: corpus prerequisite — Campaign 2 Sessions 26/27 observed recaps
  state: keep draft / corpus-only; do not merge to main as product
  merge: NO (corpus lane)

Stage 4J (this notebook)
  role: Campaign 2 Session Recaps 1–27 DeepSeek graph rehearsal
  state: active experimental notebook
  merge: NO — evidence and dogfood only
```

### Open-PR budget

At most **two open experimental notebook PRs** may exist at once. Stage 4J supersedes active experimentation on #711. Close #710 as historical once this notebook is posted.

Experiment code is disposable by default. Useful ideas graduate by being reimplemented deliberately under a future production write lease, not because this notebook accumulated them.

---

## §1 Mission and forcing question

**Mission:** Ingest Campaign 2 Session Recaps 1–27 with the DeepSeek-none profile selected in Stage 4I.2, publish to an isolated DungeonMind rehearsal World, and dogfood Session 28 prep against that graph.

### Forcing question

> **Would I rather prep Session 28 from this graph, or reopen twenty-seven recaps?**

This is a product-shaped evaluation, not another benchmark percentage. It tests extraction quality, scale, identity fragmentation, authority, temporal accumulation, graph publication, projection, and GM workflow together.

### Success criterion

A Session 28 dogfood query against the isolated World head yields enough continuity, identity resolution, and table-usable object detail that the operator would choose the graph over reopening twenty-seven recaps.

---

## §2 Scope

### In scope

```text
Corpus
  Campaign 2 Session Recaps 1–27 only
  human-authored manifest excluding:
    _archive/
    _normalized/
    _breadcrumbed/
    _session_memory/
    _ingest_staging/
  plus a small external allowlist if required for exact source identity

Pipeline (Path B)
  category graph extract
  extract-promote prepare
  experiment auto-confirm (select-all assertionIds — experiment only)

Model / transport (from Stage 4I.2 evidence)
  model: deepseek/deepseek-v4.1-flash
  reasoning: disabled
  provider: OpenRouter with DeepSeek pinned
  allow_fallbacks: false
  transport: Chat Completions response_format={"type":"json_object"}
           + schema text in system message
           + local Pydantic validation (mandatory)
           + same-request resend on JSONDecodeError / ValidationError / empty-content
           + bound: DMB_JSON_OBJECT_MAX_ATTEMPTS default 5

Target environment
  isolated DungeonMind rehearsal DB
  refuse live Eldyrwild :54330

Dogfood
  Session 28 prep query against isolated World head
```

### Out of scope

```text
FactStore-as-World-authority
live World mutation on :54330
production MODEL_POLICY change
full non-session Campaign 2 corpus (planning docs, scaffolds, worldbuilding drafts)
continuing Stage 4I.2 three-arm model matrix on #711
production auto-confirm / select-all assertionIds behavior
```

---

## §3 Prerequisites

| Prerequisite | Owner | Requirement |
|---|---|---|
| PR #712 | corpus lane | Sessions 26/27 `observed_session_recap` promoted; never LLM-fabricated |
| PR #711 | frozen notebook | DeepSeek-none transport + json_object overlay available as reference; no further matrix runs |
| PR #710 | historical | Close as historical Stage 4I evidence; do not extend |
| Isolated rehearsal DB | operator | DungeonMind rehearsal instance distinct from live Eldyrwild |
| Stage 4I.2 profile | evidence | `deepseek/deepseek-v4.1-flash`, reasoning disabled, DeepSeek pin, json_object + local validation |

Staging notes for Sessions 26/27 (not ingested as canonical recaps):

```text
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_26_raw_notes.md
corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_ingest_staging/session_27_raw_notes.md
```

---

## §4 Execution phases

### Phase A — Corpus manifest and zero-cost census

1. Freeze the Campaign 2 Session Recaps 1–27 manifest on this branch.
2. Run zero-cost census (token/count/evidence-unit accounting) before any paid extraction.
3. Verify Sessions 26/27 match PR #712 promoted recaps, not staging notes.

### Phase B — Path B category graph extract

1. Run category graph extract on the frozen manifest with the DeepSeek profile above.
2. Keep raw extraction artifacts untouched for audit.
3. Record execution receipts: model slug, provider pin, attempt counts, json_object retries, cost, timing.

### Phase C — Extract-promote prepare

1. Run extract-promote prepare on raw extraction output.
2. Add deterministic reconciled candidate graph where required by the experiment contract.
3. Do not mutate live World or production publication paths.

### Phase D — Experiment auto-confirm

1. **Experiment only:** select-all `assertionIds` auto-confirm to unblock rehearsal publication.
2. This is not production product behavior and must not ship to `main` without a separate governed write lease.
3. Document exactly which assertions were auto-confirmed and why the experiment needed it.

### Phase E — Isolated World publish

1. Publish only to the isolated DungeonMind rehearsal DB.
2. **Refuse** live Eldyrwild `:54330` — fail closed if the target resolves to production World authority.
3. Capture World head revision identity for dogfood queries.

### Phase F — Session 28 dogfood

1. Prep Session 28 using the isolated World head as continuity authority.
2. Record whether the operator would prefer the graph over reopening twenty-seven recaps.
3. Capture identity fragmentation, missing continuity, and table-usable object gaps as qualitative debt.

---

## §5 Model and transport contract

Inherited from PR #711 / Stage 4I.2:

```text
Model slug:     deepseek/deepseek-v4.1-flash
Reasoning:      disabled
Provider route: OpenRouter
Provider pin:   order=["DeepSeek"], allow_fallbacks=false
API surface:    Chat Completions (not Responses JSON Schema)
Output mode:    response_format={"type":"json_object"}
Validation:     local Pydantic validation after every response
Retry policy:   same-request resend on parse/validation failure
Retry bound:    DMB_JSON_OBJECT_MAX_ATTEMPTS=5 (default)
Not allowed:    evaluator LLM repair, semantic rewrite, silent truncation
```

Do not change production `MODEL_POLICY.json` as part of this notebook.

---

## §6 Safety gates

```text
GATE 1 — Corpus scope
  Only Campaign 2 Session Recaps 1–27 in the manifest.
  No _archive / _normalized / _breadcrumbed / _session_memory / _ingest_staging paths.

GATE 2 — Target isolation
  Publication target MUST be isolated rehearsal DB.
  Any attempt to write Eldyrwild :54330 MUST fail closed.

GATE 3 — Auto-confirm boundary
  select-all assertionIds is experiment-only.
  Must be labeled non-production in code, receipts, and PR body.

GATE 4 — Merge refusal
  This notebook MUST NOT merge to main.
  Close unmerged when evidence is captured or superseded.

GATE 5 — Predecessor freeze
  Do not reopen #711 matrix work or extend #710 baseline runs.
```

---

## §7 Deliverables

| Deliverable | Location / form |
|---|---|
| This handoff | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage4j-c2-deepseek-graph-rehearsal-v1.md` |
| Frozen session manifest | committed on this branch |
| Zero-cost census artifact | `out/` or `extraction_lab/` (local; not required in PR if large) |
| Raw extraction store | local isolated store under `out/` |
| Rehearsal World head | isolated DungeonMind DB revision |
| Session 28 dogfood notes | PR comment or local report |
| Decision checkpoint | `REHEARSAL VERDICT — FROZEN` posted on this PR when complete |

---

## §8 Decision checkpoint

After Phase F, ask:

> **Would I rather prep Session 28 from this graph, or reopen twenty-seven recaps?**

If **YES (graph wins)**:

1. Post `REHEARSAL VERDICT — FROZEN` on this PR with qualitative evidence.
2. Record model/profile, identity debt, timing, cost, and publication gaps.
3. Close #710 and #711 unmerged if not already closed.
4. Open a clean production implementation PR from current `main` if a production ingestion profile change is warranted.

If **NO (recaps win)**:

1. Post the verdict with named failure modes (identity, temporal, authority, projection, GM workflow).
2. Keep this notebook as historical evidence.
3. Do not change production MODEL_POLICY without a separate evidence-backed decision.

---

## §9 References

- PR #712 — `corpus/c2-session-26-27-recaps` (Sessions 26/27 recaps)
- PR #711 — Stage 4I.2 DeepSeek quality/timing screen (frozen)
- PR #710 — Stage 4I Sol baseline (historical)
- `Backlog.md` — `[DOING] Campaign 2 DeepSeek-none rehearsal for Session 28 prep`
- `extraction_lab/campaign_memory_stage4i2_three_arm_quality_compare.md` — DeepSeek arm evidence
- `_ingest_staging/session_{26,27}_raw_notes.md` — staging only, not canonical recaps
