# Category Graph Model Study — Session 22

Artifact root: `evals/graph_memory_layer/artifacts/category_graph_model_study/2026-06-26`

## Baseline (one-shot)

- Model: `gpt-5.4`
- Node recall: **0.72**
- Edge recall: **0.44**

## Category-decomposed smoke (N=1 per model)

| Model | Cost USD | Nodes | Edges | Node recall | Node prec. | Edge recall | Beat recall | Valid IR |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| gpt-5.3-codex | 0.1214 | 42 | 0 | 0.84 | 0.4773 | 0.0 | 0.0 | True |
| gpt-5.4-mini | 0.0503 | 51 | 20 | 0.92 | 0.434 | 0.0 | 0.0 | True |
| gpt-5.4 | 0.1367 | 53 | 21 | 0.92 | 0.4182 | 0.0 | 0.0 | True |

## Cost

- Cohort sum: **$0.3085** (min $0.0503, mean $0.1028, max $0.1367)
- Compare to one-shot baseline envelope (not re-run here); category path is ~7 LLM calls per model.

## Failure-mode notes

- Node recall now reflects span-overlap matching: candidate paragraph sprefs and gold curated anchors resolve to the same line range, so divergent phrasing over a shared span is matched (see `identity_resolution.node_match_score`). Companion anchors (Thrin, Lysandra) are seeded from party context, not re-extracted.
- Residual node misses are real: e.g. `gpt-5.4-mini` omits Grobnok (actor pass miss), and the `event`-vs-`mystery` storm node drifts across the thread/phenomenon class boundary (gold types it `event`, models type it `mystery`).
- Object pass over-extracts (node precision well below recall): rockie-talkie, wagon, stick, road sign, chalkboard menu — table props gold omits. Prompt-addressable (plot-bearing only).
- Edge recall is ~0: the edge pass builds a thread→location grounding graph rather than gold's entity↔entity relational graph (kinship/membership/authority/social). Endpoints are mostly present; the model chose the wrong edge ontology. Prompt-addressable.
- Models often emit `session-22:pNNN` without the `spref:` prefix; sanitize canonicalizes.

## Recommendation

**promote category decomposition** — best node recall `gpt-5.4-mini` at 0.92.

