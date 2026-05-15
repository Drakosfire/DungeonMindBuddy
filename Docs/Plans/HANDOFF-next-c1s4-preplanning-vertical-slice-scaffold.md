# HANDOFF — Next C1S4 preplanning vertical slice scaffold

Status: READY — PR #24 has landed; implementation agents should use `src/session_memory/` as the canonical session-memory ingestion package.

## 1) Goal

Ship an implementation-ready deterministic scaffold for C1S4 preplanning:
- Planner-visible KB input is strictly C1S1–C1S3.
- C1S4 remains oracle-only held-out material.
- First implementation PR proves deterministic KB + retrieval context-bundle plumbing only.

## 2) Canonical dependencies

PR #24 has landed. Use `src/session_memory/` as the canonical package for session-memory ingestion helpers. Do not import ingestion code from `evals/sentence_routing_retrieval_falsification` except where existing compatibility shims are explicitly being tested.

## 3) Oracle boundary policy

Planner-visible KB must exclude all C1S4 source and derivative surfaces, including:
- original C1S4 recap
- normalized C1S4 recap
- breadcrumbed C1S4 recap, if present
- session-memory C1S4 records/meta, if present
- any generated C1S4 oracle target files

For grading, prefer normalized C1S4 recap as oracle source if present, matching recap-normalization authority. Original C1S4 recap remains fallback oracle reference and forbidden planner-visible source.

Example policy payload:

```json
{
  "schema": "dmb_c1s4_preplanning_kb_policy_v1",
  "campaign_id": "longmont-c1",
  "kb_id": "longmont-c1-sessions-01-03-preplanning-kb-v1",
  "included_sessions": [1, 2, 3],
  "heldout_sessions": [4],
  "included_session_memory_relpaths": [],
  "forbidden_oracle_relpaths": [
    "Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md",
    "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 04 - The Grotesque Tree of Hempholm.md",
    "Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 04 - The Grotesque Tree of Hempholm.breadcrumbed.md"
  ],
  "preferred_oracle_source_relpath": "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 04 - The Grotesque Tree of Hempholm.md",
  "fallback_oracle_source_relpath": "Longmont Campaign/Campaign 1/Session Recaps/Session 4 - The Grotesque Tree of Hempholm.md"
}
```

Implementation note: where derivative filenames vary, resolve via existing path helpers instead of brittle hardcoded guesses.

## 4) Scope for first implementation PR

In scope:
- deterministic KB materialization for C1S1–C1S3
- deterministic retrieval context bundle generation
- policy assertions around C1S4 holdout/oracle paths

Not in scope:
- live planner run
- oracle grading
- retrieval tuning
- corpus changes
- baseline regeneration

## 5) Verification intent

The scaffold PR must prove deterministic boundary enforcement before any live planner or grading step.

## 6) Mandatory verification commands

```bash
uv run pytest tests/test_c1s4_preplanning_vertical_slice.py -q
uv run pytest tests/test_session_memory_canonical_location.py -q
uv run python evals/c1s4_preplanning_vertical_slice/step0_kb_materialize.py
uv run python evals/c1s4_preplanning_vertical_slice/step1_retrieval_context.py
uv run python scripts/materialize_session_memory.py --all-blessed --check
```
