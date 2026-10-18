# INGEST: source-anchored recap beat summaries

Status: ACTIVE — PRIME authorized this bounded design and implementation after ARCHITECTURE critique on 2026-10-17.

Base: `origin/main@f1045c2c4d05fe2fb9fc64f99d566ba50c315769` (verified against GitHub; local `origin/main` matches).
Branch: `codex/ingest-extractive-beat-summaries`.
Checkout: `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`.
Topology: serial; one INGEST implementation PR. PRIME owns merge and rollout. ARCHITECTURE reviews the exact cumulative diff.

The first implementation commit is this handoff plus settlement of the predecessor handoff only. No extractor or test code changes may precede it.

## Capability and invariant

For recap extraction only, a candidate `SessionBeat.summary` must be copied in full from one exact, eligible host paragraph in the pinned `source_text`. A model-provided title or summary is never user-facing beat prose. Model evidence span IDs and anchor quotes only nominate a location; they do not authorize a paraphrase or source claim.

The host selects one eligible paragraph only when the model's exact anchor quote(s) uniquely resolve to that same paragraph in the host source and the nominated paragraph span agrees. Read paragraph content from `source_text` using the verified span bounds; text stored in the span index is only locator metadata and never content authority. The host emits the entire paragraph unchanged, a neutral ordinal title (`Source excerpt N`), and evidence pointing to that exact span and full excerpt.

Missing source text, absent or forged nomination, non-paragraph span, stale/mismatched digest, invalid bounds, repeated/ambiguous anchor, or a multi-span nomination deterministically defers the beat with an ordinal label and stable diagnostic code. Never fall back to model prose, index text, nearest matches, clips, ellipses, joined paragraphs, fuzzy matches, or source-wide search. No model-authored title or summary may leak through either success or deferral.

This establishes excerpt provenance only. It does not establish event completion, intent, attribution, purpose, location, identity, participant membership, or cross-span entailment. Existing beat `order` and participant IDs remain outside this correction and retain their existing preview-only status. `candidate_graph_to_contribution` currently maps nodes and edges, not beats; the encounter-job prompt consumes beats as source-local context and explicitly says a recap beat is not itself an encounter. Candidate diagnostics are legacy preview flags, not provider-execution evidence: do not flip `extraction_performed` or `llm_used` in this slice.

## Predecessors and current limits

- Prompt-only source-faithfulness PR #1359 merged at `ca0d0a7b7a1ea0e9510b075000f28f31bf933cdd`. Its tests prove prompt construction, not model compliance; the previous handoff is settled in this implementation PR.
- PRIME inspected open #1148 head `c2e5e1b6efcf2102b99cb8c3eb1e44bd0e834db8` and #1149 head `7c8d9493c1b5ce007e35696c1766e80dd1f7638d`, withdrew their old overlapping extractor write lease, and placed explicit holds in their PR bodies. Preserve those unmerged refs and do not cherry-pick, adopt, or claim their behavior is on current main. They reserve no current-main paths for this slice.
- The current exact Session 29 run had structurally complete evidence but semantic modality errors. The saved output/source bundle must be recomposed offline before review to show that the exact `will cast` and `decides to camp` passages survive verbatim and that the old bundle hash is unchanged. Do not call a provider.
- Unsupported edge extraction, source-purpose/location/identity claims, graph admission/publication, and remaining linking/coverage issues remain open. This slice is the first bounded correction, not completion of the semantic goal.

## Exclusive expected write set

| Path | Purpose |
| --- | --- |
| `Docs/Plans/HANDOFF-INGEST-extractive-beat-summaries.md` | This ACTIVE contract, evidence, and truthful settlement |
| `Docs/Plans/HANDOFF-INGEST-recap-source-faithfulness.md` | Settle merged PR #1359 only |
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Host-side recap-beat excerpt selection, copy, and deterministic defer diagnostics |
| `tests/test_recap_source_quote_beat_summary.py` | New extractor-boundary and typed `SessionBeat` regression tests |
| `tests/test_category_candidate_graph_extractor.py` | Existing fixture contract updates only if required by the new source-text requirement |

No other paths are leased. If source authority, source-span production, schema, UI, API, publication, graph-node/edge behavior, or a new consumer must change, stop and return the exact boundary and paths to PRIME.

## Consumer and failure-case gate

Tests must exercise the actual category extractor through host consolidation into typed `SessionBeat`, with an intentionally contradictory model title/summary. Prove the rendered beat contains the exact whole host paragraph and neutral title. Cover a negation outside a tempting substring, future/conditional language, reported attribution, an attempt/failed action, a decision versus follow-through, repeated identical anchors in different paragraphs, missing/forged nomination, invalid/missing source span, stale source digest, ambiguous anchor, and multi-span nomination. Every invalid case must defer deterministically without model prose. Prove the contribution mapper does not turn a beat into an occurred event.

Before PR review, recompose the saved eight-pass Session 29 result and exact source offline into new private evidence. Show that the known intended spell and camp-decision passages are emitted verbatim, no contradictory model title/summary survives, and the prior retained bundle hash is unchanged. If the exact saved pass bundle is unavailable, do not substitute an old or synthetic bundle; report the missing evidence to PRIME. No provider or model call is needed or authorized.

## Verification and limits

- Run the new regression tests, the owning category-extractor tests, and related typed candidate-preview tests that consume `SessionBeat`.
- Run `git diff --check` and inspect the exact `origin/main` → PR-head diff against this allowlist.
- Keep fixtures synthetic except for the offline recomposition evidence, which stays private and is bound to the exact saved source/run digests.
- No automatic publication, operator acceptance, app/API/database mutation, runtime restart, provider execution, or 5202 change is authorized.
- Commit, push, and open one PR. Send PRIME the exact base/head, handoff-first commit, cumulative diff summary, test results, recomposition hashes, and remaining limits. ARCHITECTURE reviews the exact head; PRIME decides merge and any live follow-through.
