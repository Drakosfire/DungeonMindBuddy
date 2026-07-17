# Corpus Expansion GPT Luna Decision Record

Generated: `2026-07-17T21:40:00Z` (updated with reasoning ablations)

## Decision / Conviction

**`gpt-5.4-mini` is well suited for production category graph extraction.** Keep it as the production model at provider-default reasoning (`none` / unset). Defer Luna promotion.

Do not raise Mini reasoning effort for routine ingest. Do not treat Luna as a quality upgrade over Mini for this pipeline.

## Why Mini fits

1. **Competitive frozen quality.** On four gold fixtures × three trials, Mini mean node recall `0.615` and evidence coverage `0.889` vs Luna `0.602` / `0.864`. Luna's edge-recall advantage (`+0.070`) does not outweigh node/evidence tradeoffs for the default ingest job.
2. **Better cost/latency for batch ingest.** Frozen mean cost `$0.075`/run and `~80s` vs Luna `$0.114` and `~87s`. Shadow samples show the same direction.
3. **Default reasoning is the right Mini setpoint.** session-1 Mini `medium` (n=1) vs unset/none mean (n=3): cost `$0.097` vs `$0.048`, latency `108s` vs `52s`, nodes `28` vs `~49`, node recall `0.630` vs `0.691`. Medium buys selectivity/precision, not a better overall extract.
4. **Higher Luna reasoning is not a rescue.** session-1 Luna `high` vs `medium`: cost `$0.159` vs `$0.080`, latency `149s` vs `61s`, node recall `0.593` vs `0.667`, node precision `0.400` vs `0.487`.
5. **Already the production contract.** Policy action `graph_memory_category_extraction` resolves to `gpt-5.4-mini`. Runtime path matches Live Control category extraction.

## Resolved models

- GPT Luna: `gpt-5.6-luna` via OpenAI API. Unset reasoning defaults to `medium`.
- Primary GPT-5 mini comparison: `gpt-5.4-mini` via the `graph_memory_category_extraction` policy action. Unset reasoning defaults to `none`.
- Luna pricing per 1M tokens: input `$1.00`, cached input `$0.10`, cache writes `$1.25`, output `$6.00`.

## Frozen evidence

- Four checked-in gold fixtures, three trials per model/fixture, publication disabled; dataset revision `sha256:b0a96e3c25978caba544cd39f2f144111fe3996caeb9d6596204d38c192643ae`.
- Luna minus GPT-5.4 mini: node recall `-0.012825`, edge recall `0.070366`, node precision proxy `0.055591`, edge precision proxy `0.0768`, evidence coverage `-0.02518`, cost `0.039843` USD/run, latency `7143.280833` ms/run.
- Frozen runs used unset reasoning (Mini≈none, Luna≈medium). Treat that as the fair default-vs-default comparison.

Artifact: `evals/graph_memory_layer/artifacts/corpus_expansion_luna_benchmark/2026-07-17/phase2_frozen_benchmark/benchmark_report.json`

## Reasoning ablation evidence (session-1)

| Ablation | Node recall | Node precision | Cost | Latency | Nodes | Reading |
|---|---:|---:|---:|---:|---:|---|
| Mini none mean → medium | 0.691 → 0.630 | 0.381 → 0.607 | $0.048 → $0.097 | 52s → 108s | ~49 → 28 | Real setting change; not a free quality upgrade |
| Luna unset mean → medium | 0.568 → 0.667 | 0.442 → 0.487 | $0.075 → $0.080 | 70s → 61s | ~35 → 37 | Near-duplicate; Luna unset already ≈ medium |
| Luna medium → high | 0.667 → 0.593 | 0.487 → 0.400 | $0.080 → $0.159 | 61s → 149s | 37 → 40 | Pays ~2×; recall and precision drop |

Artifacts:

- `phase2_mini_medium_session1/benchmark_report.json`
- `phase2_luna_medium_session1/benchmark_report.json`
- `phase2_luna_high_session1/benchmark_report.json`

Max/`xhigh` was abandoned after multi-minute per-pass stalls and extreme reasoning-token spend; it is not a production setpoint.

## Shadow evidence

- Eight source-family samples, three trials per model/document, 48/48 completed, publication disabled.
- Luna generally emitted fewer nodes/edges and had higher cost/latency; the shadow has no gold quality score and must not be read as a quality ranking.

Artifact: `evals/graph_memory_layer/artifacts/corpus_expansion_luna_benchmark/2026-07-17/phase3_representative_shadow/benchmark_report.json`

## Publication and canon boundary

- First recommended family: Campaign 2 canonical recaps.
- No material was published to the **live** Eldyrwild head during the Luna benchmark.
- The portable-object candidate was `blocked_before_publication` at phase4 time (identity unresolved; phase4 also incorrectly claimed no head fixture).
- **Correction (phase6):** an Eldyrwild World Supergraph head already exists at `out/graph_memory/worlds/eldyrwild/` (`rev:5cadc979…`, bootstrap 12 nodes / 11 edges). The real blockers were mapper + identity acceptance + operator promote — not missing Kernel publish.
- All benchmark outputs and the portable candidate remain non-canon local artifacts. Phase6 tmp-world proof is also non-canon (live head untouched).

## Required next gates

**Closed by phase6 publish-path spike:**

- Fixed-candidate identity scorer with unresolved ambiguity / duplicate-risk diagnostics (`extract_identity_gate`).
- Candidate-to-GraphContribution mapping with evidence + source revision fail-closed (`candidate_graph_to_contribution`).
- Sealed promote proposal v2 (`proposal_id` / `proposal_version=2` / `proposal_digest` / confirming principal): digest covers complete durable effect including `contribution_meta` + `verified_source_uri`; confirm reconstructs contribution only from sealed fields (no `contribution_candidate` envelope; no confirm-time `--authored-by`).
- `selection_digest` in contribution identity so partial assertion subsets under the same proposal cannot collide.
- Single-artifact evidence gate until per-artifact `{artifact_id, URI, revision}` verification exists.
- Typed CandidateGraphPreview input + played_canon semantic promote matrix (fail closed on planning/diagnostic/llm-default semantics).
- Kernel publication, replay, and projection verification on a tmp copy of the Eldyrwild head (`scripts/promote_extract_contribution.py`; proof under `phase6_publish_path/`); CLI exits nonzero when `published=False`.

**Still open:**

- Align category extractor `DEFAULT_SEMANTIC_STATE` / evidence completeness to typed CandidateGraphPreview IR so raw Luna extracts are promote-eligible without a hand IR fixture.
- Unsupported-assertion and operator-review-burden scoring for batch ingest.
- Live-head batch promotion of C2 canonical recaps (after operator review).
- Ingest UI “promote to World Supergraph” button (calls the same service path; not part of this spike).
- Usefulness-at-scale eval once the head is substantially larger.
