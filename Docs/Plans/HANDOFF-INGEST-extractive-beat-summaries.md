# INGEST: source-anchored recap beat summaries

Status: SETTLED — PR #1391 merged to `main` at `eadef26d7951f3384042f0144085f9676c41be7e` on 2026-10-18 UTC. Its implementation lease is closed.

Implementation base: `origin/main@f1045c2c4d05fe2fb9fc64f99d566ba50c315769`.
Merged PR head: `d1185dfc53de367571e1f8f5e988a9e7bec80929`.
Branch: `codex/ingest-extractive-beat-summaries` (settled).
Checkout: `/home/drakosfire/.codex/worktrees/996b/DungeonMindBuddy`.
Topology: serial; PR #1391 was the implementation PR for this slice. PRIME owns deployment. ARCHITECTURE reviewed the exact cumulative diff.

## Settlement

PR #1391 delivered the source-faithful recap beat correction and was deployed by PRIME on the existing API 8000. The deployed extractor module SHA-256 is `668f0ce40f4a5b1333b12bfef71d78434bcf5b82ac21462a5c4ea369e95afa42`.

The first fresh deployed Session 29 Process after merge is recorded in the successor handoff, `HANDOFF-INGEST-disposition-node-type-tolerance.md`. The recap source was reused unchanged. Extraction reached OpenRouter/DeepSeek, but the thread pass's single conformance repair still failed the strict disposition schema, so no candidate graph was produced and nothing was published. This is a successor defect and does not reopen this settled beat-summary lease.

PR #1391's first implementation commit contained this handoff plus settlement of its predecessor; no extractor or test code changes preceded it.

PRIME expanded the ACTIVE test lease on 2026-10-17 to include one fixture-only update in `tests/test_category_extractor_promote_evidence_refs.py`: its category-pipeline persistence test must provide authoritative pinned `source_text` with a matching source digest so it continues to validate beat persistence under the new input contract. No other test in that file is in scope.

## Capability and invariant

For recap extraction only, a candidate `SessionBeat.summary` must be copied in full from one exact, eligible host paragraph in the pinned `source_text`. A model-provided title or summary is never user-facing beat prose. Model evidence span IDs and anchor quotes only nominate a location; they do not authorize a paraphrase or source claim.

The host selects one eligible paragraph only when the model's exact anchor quote(s) uniquely resolve to that same paragraph in the host source and the nominated paragraph span agrees. Read paragraph content from `source_text` using the verified span bounds; text stored in the span index is only locator metadata and never content authority. The host emits the entire paragraph unchanged, a neutral ordinal title (`Source excerpt N`), and evidence pointing to that exact span and full excerpt.

Missing source text, absent or forged nomination, non-paragraph span, stale/mismatched digest, invalid bounds, repeated/ambiguous anchor, or a multi-span nomination deterministically defers the beat with an ordinal label and stable diagnostic code. Never fall back to model prose, index text, nearest matches, clips, ellipses, joined paragraphs, fuzzy matches, or source-wide search. No model-authored title or summary may leak through either success or deferral.

This establishes excerpt provenance only. It does not establish event completion, intent, attribution, purpose, location, identity, participant membership, or cross-span entailment. Existing beat `order` and participant IDs remain outside this correction and retain their existing preview-only status. `candidate_graph_to_contribution` currently maps nodes and edges, not beats. The encounter-job prompt and staged-edge relation-observation prompt consume beats as model context, so later model outputs may change when beat context becomes source-faithful. Replaying the saved eight passes preserves their already-recorded node/edge outputs by construction; it cannot establish that a new provider run would produce identical edges. Candidate diagnostics are legacy preview flags, not provider-execution evidence: do not flip `extraction_performed` or `llm_used` in this slice.

## Predecessors and current limits

- Prompt-only source-faithfulness PR #1359 merged at `ca0d0a7b7a1ea0e9510b075000f28f31bf933cdd`. Its tests prove prompt construction, not model compliance; the previous handoff is settled in this implementation PR.
- PRIME inspected open #1148 head `c2e5e1b6efcf2102b99cb8c3eb1e44bd0e834db8` and #1149 head `7c8d9493c1b5ce007e35696c1766e80dd1f7638d`, withdrew their old overlapping extractor write lease, and placed explicit holds in their PR bodies. Preserve those unmerged refs and do not cherry-pick, adopt, or claim their behavior is on current main. They reserve no current-main paths for this slice.
- The current exact Session 29 run had structurally complete evidence but semantic modality errors. Its saved output/source bundle was recomposed offline before review; the corrected replay record below shows the exact `will cast` and `decides to camp` passages survive verbatim and the old bundle hash is unchanged. No provider was called.
- Unsupported edge extraction, source-purpose/location/identity claims, graph admission/publication, and remaining linking/coverage issues remain open. This slice is the first bounded correction, not completion of the semantic goal.

## Exclusive expected write set

| Path | Purpose |
| --- | --- |
| `Docs/Plans/HANDOFF-INGEST-extractive-beat-summaries.md` | This ACTIVE contract, evidence, and truthful settlement |
| `Docs/Plans/HANDOFF-INGEST-recap-source-faithfulness.md` | Settle merged PR #1359 only |
| `src/graph_memory/extraction/category_candidate_graph_extractor.py` | Host-side recap-beat excerpt selection, copy, and deterministic defer diagnostics |
| `tests/test_recap_source_quote_beat_summary.py` | New extractor-boundary and typed `SessionBeat` regression tests |
| `tests/test_category_candidate_graph_extractor.py` | Existing fixture contract updates only if required by the new source-text requirement |
| `tests/test_category_extractor_promote_evidence_refs.py` | One fixture-only source-text/digest update in `test_party_registry_category_pipeline_persists_promotable_for_resolve`, authorized by PRIME |

No other paths are leased. If source authority, source-span production, schema, UI, API, publication, graph-node/edge behavior, or a new consumer must change, stop and return the exact boundary and paths to PRIME.

## Consumer and failure-case gate

Tests must exercise the actual category extractor through host consolidation into typed `SessionBeat`, with an intentionally contradictory model title/summary. Prove the rendered beat contains the exact whole host paragraph and neutral title. Cover a negation outside a tempting substring, future/conditional language, reported attribution, an attempt/failed action, a decision versus follow-through, repeated identical anchors in different paragraphs, missing/forged nomination, invalid/missing source span, stale source digest, ambiguous anchor, and multi-span nomination. Every invalid case must defer deterministically without model prose. Prove the contribution mapper does not turn a beat into an occurred event. The offline saved-pass replay is a deterministic regression of the host excerpt-selection boundary, not evidence about what a future encounter or staged-edge provider call will infer from the changed beat context.

## Implementation evidence

- The recap-only host selector is implemented in `category_candidate_graph_extractor.py`. It verifies the pinned source digest, resolves exact unique anchors against eligible indexed spans, copies the complete source span into the beat, assigns a neutral `Source excerpt N` title, and deterministically defers unsafe nominations without model-authored beat prose. The sanitizer also retains an exact full-span quote match when leading indentation would otherwise be trimmed by the shared quote normalizer.
- The new owning-boundary suite covers future/conditional wording, negation, reported speech, failed attempts, intent versus follow-through, contradictory model prose, ambiguous/repeated anchors, missing/forged/non-paragraph/multi-span nominations, unavailable or stale source authority, line-only bounds with CRLF, typed `SessionBeat`, and contribution mapping. `45 passed` across that suite plus category extraction, typed preview, and contribution-mapper suites; Ruff and `git diff --check` pass.
- The authorized persistence-test fixture supplies exact source text and its matching digest; the stale helper import was repaired to use the existing fixture module. PRIME ran the ordinary owning test against its disposable PostgreSQL fixture using pytest's standard `application_state_dsn` fixture: `1 passed in 0.48s`, including persist-and-reopen. No module alias or retained database was used.
- Corrected offline recomposition evidence is retained privately at `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016/session29-extractive-beat-offline-replay-corrected.json` (SHA-256 `9b649c00050734ae4d9e10ea134b0c315f7ce0574ba9ad3a744e87ac05be1175`). It supersedes `/home/drakosfire/.local/state/dungeonmindbuddy/experiments/jev-evidence-loop-20261016/session29-extractive-beat-offline-replay.json`, which used an incomplete reconstruction. The exact saved source SHA-256 is `2bfe3db6a204de5b8638a041027eb71e5d61159f80f8c209ece848e043d6ebbf`; the source-span-index SHA-256 is `fb2508cd17355ce12476f0f674d9e61db8b8265bdc58ca4834fd0cf9dcd8c8c5`. The saved host-normalized `actor_pass` artifact at `.private/generationengine_attempts/01-actor_pass-normalized.json` has SHA-256 `76b6c95fa29f16de8a4cc7220c7a73550ac226152878d2139d8e82a12969b840`. This normalization binds the seven raw actor-pass nodes' `source_quote_ids` to paragraph `source_span_ref_id` evidence; replay used its `parsed` payload rather than the raw actor response.
- Corrected offline replay used all seven other exact saved pass responses plus the captured normalized actor-pass payload, exact source/index, `current_default` profile, and session-29 party registry/carry-forward context. On pinned base `f1045c2c4d05fe2fb9fc64f99d566ba50c315769`, the output is 62 nodes / 64 edges / 15 beats / 3 deferred / 2 ignored and every candidate-graph field matches the saved candidate exactly. On the patched branch with the same inputs, all nodes and edges match the saved candidate byte-for-byte; all 15 beat summaries change to exact source paragraphs with neutral titles and full-span evidence, preserving the source's future-modality and decision/intent passages. The original saved candidate SHA-256 `6258b886f9dcc7ed33bb6a380534f0daed06c0839b38519f071714aee9fae7dd` remained unchanged.
- The earlier 55-node / 45-edge replay was a reconstruction error: it fed the raw actor response and omitted the retained host-normalized actor artifact, which removed exactly seven actor nodes and their 19 dependent edges. Those counts are superseded and are not evidence of a product regression or historical drift. The separate staged-edge and encounter-job provider calls may still infer differently from source-faithful beats.
- The canonical line-only preview-runner test fails identically on base and patched code with `party enrichment incomplete for 1 nodes`. Its prompt/source-span assertions pass; the failure is the inherited party-fill validation path and is not caused by this excerpt change. Do not relax its fixture in this slice.
- The independent extractor/contribution/typed-preview suites pass (`45 passed`). PRIME separately ran the combined owning suite, including the full promote-evidence-ref module with the standard `application_state_dsn` fixture: `54 passed in 6.98s` against the disposable database, including persist-and-reopen. Ruff and `git diff --check` pass.

The exact saved eight-pass Session 29 result and source were recomposed offline into the private evidence record above. It shows the known spell and camp-decision passages are emitted verbatim, no contradictory model title/summary survives, and the prior retained bundle hash is unchanged. No provider or model call was made.

## Verification and limits

- Run the new regression tests, the owning category-extractor tests, and related typed candidate-preview tests that consume `SessionBeat`.
- Run `git diff --check` and inspect the exact `origin/main` → PR-head diff against this allowlist.
- Keep fixtures synthetic except for the offline recomposition evidence, which stays private and is bound to the exact saved source/run digests.
- The owning persistence/reopen test uses only PRIME's disposable PostgreSQL fixture on port `54329` (512 MiB tmpfs, existing image, no retained data). PRIME owns its startup and cleanup. Do not use the retained fixture on `54331`; clean up `54329` after the author and independent-review consumers finish.
- No automatic publication, operator acceptance, retained application/graph database mutation, runtime restart, provider execution, or 5202 change is authorized. The disposable database fixture is authorized only for persistence/reopen verification and is owned and cleaned up by PRIME after author and review consumers finish.
- Commit, push, and open one PR. Send PRIME the exact base/head, handoff-first commit, cumulative diff summary, test results, recomposition hashes, and remaining limits. ARCHITECTURE reviews the exact head; PRIME decides merge and any live follow-through.
