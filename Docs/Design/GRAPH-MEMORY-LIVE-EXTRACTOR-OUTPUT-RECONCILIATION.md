# Graph Memory Live Extractor Output Reconciliation

## Problem

Three schemas diverged on the Session 23 dogfood path:

1. **Canonical IR** (`dmb_candidate_graph_preview_v0` in `src/graph_memory/candidate_graph_preview.py`) — nodes/edges/beats with nested `semantic_state`, rich `EvidenceRef`, closed vocabs.
2. **Live prompt target** — flat `candidate_nodes` / `session_beats` sections with light `source_span_ref_id` evidence.
3. **Gold fixture** — canonical IR with `source_anchor_id` evidence from `source_span_seed_refs.json`.

The weak live validator only checked section presence and known sprefs, so “green” did not mean comparable to gold.

## Decision

### Output envelope: `dmb_live_extractor_candidate_envelope_v0`

```json
{
  "schema": "dmb_live_extractor_candidate_envelope_v0",
  "version": "0.1",
  "candidate_graph": { "... dmb_candidate_graph_preview_v0 ..." },
  "review_sidecar": {
    "high_risk_claims": [...],
    "notes": [...]
  }
}
```

High-risk audit material lives in `review_sidecar`, not in the canonical IR.

### Model-facing evidence

The model cites only:

```json
{"source_span_ref_id": "spref:session-23:pNNN"}
```

No anchor catalog in prompts (anti-oracle-leakage).

### Deterministic bridge: `reconcile_live_candidate.py`

1. Read run bundle `source_span_index.json` for line/char spans per spref.
2. Map spref → `SourceSpanRef` on normalized recap artifact IDs (`source-artifact:session-23-normalized-recap`).
3. Resolve via `resolve_many_source_span_refs` to set `can_open_source` / `can_highlight_span` and optional `source_anchor_id` overlap.
4. Parse with `candidate_graph_preview_from_dict` and run `validate_candidate_graph_preview` (strict).

Legacy flat sections (`candidate_nodes`, etc.) are migrated before reconciliation.

### Live vs gold comparison

`live_vs_gold_compare.py` fuzzy-matches by normalized label + `node_type` + evidence line-span overlap instead of exact `node_id` equality.

## Recap spelling variants (Session 23)

`expected_normalized_recap.md` preserves source spellings:

- `Kasemine` / `Karsemine` / `Karesmine` (PC name variants)
- `Baergrom` / `Baergorm` (PC name variants)
- `Lysandro` vs unnamed father on the wall (high-risk identity-binding case)

Rationale: alias-deferral and spelling-variant extraction tests require source-faithful text; normalization would collapse meaningful benchmark signal.

## Harness reference

- Reconcile: `evals/graph_memory_layer/reconcile_live_candidate.py`
- Validate: `evals/graph_memory_layer/validate_live_extractor_candidate_output.py`
- Compare: `evals/graph_memory_layer/live_vs_gold_compare.py`
- Prompts: `evals/graph_memory_layer/live_extractor_prompt_harness.py`
