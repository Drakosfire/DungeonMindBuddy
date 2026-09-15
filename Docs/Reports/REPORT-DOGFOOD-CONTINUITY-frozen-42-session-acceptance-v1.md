# REPORT — DOGFOOD-CONTINUITY frozen 42-session two-arm acceptance replay

**Recorded:** 2026-09-15
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md`
**Execution branch:** `dogfood-continuity/frozen-42-session-acceptance-replay-v1`
**Machine evidence:** `out/frozen_42_session_acceptance/ACCEPTANCE_RESULT.json`
**Disposition:** **DO NOT MERGE** this execution branch. **DO NOT MERGE** PR #715.

---

## Verdicts

```text
STRUCTURAL ACCEPTANCE PASS
SEMANTIC MODEL SELECTION HOLD
```

These are independent. Structural PASS means both frozen arms completed an uninterrupted genesis-plus-42-session governed replay with zero model calls. It does not select a model, prove graph quality, or authorize UI GO.

---

## 1. Pipeline / structural verdict

Both arms independently:

- started from a proven-empty rehearsal database on loopback `127.0.0.1:54329`;
- created a six-PC zero-parent `D_0` from the same canonical Campaign 1 party-registry digest `sha256:f0f49045df06f7baf61aa9c43f3739d16483eeb20ac8ed1bbf29f8209474af25`, roster key `"1"`;
- published C1 S1 as an ordinary existing-parent child of that `D_0` (no special first-recap path);
- published the remaining frozen sessions as one child-revision chain through C1 S17 then C2 S1–S25;
- ended with exactly one native World head equal to the final receipt child;
- performed `model_calls = 0` with model credentials stripped.

Authorities used:

```text
production_base_sha / genesis merge:
876123a3d197d426ce76e03a30f059093ba9b4f4

execution_head_sha:
04ff89083aabac75c4b7b135e685d1b1efefd44c

notebook_head_sha (#715, clean):
820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed

candidate_frozen_head_sha:
d6e2599bbabb9719bc92601f7bc1ad8b69411e98

acceptance_manifest_sha256:
d0f3cb66075f44abe417d5fe149dd31769d1c5b671d02c36534c4e5b43f6c1a1
```

Changed paths versus genesis `876123a3…` are only the leased acceptance files:

```text
Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md
tests/test_frozen_42_session_acceptance.py
tools/run_frozen_42_session_acceptance.py
```

plus this report and `out/frozen_42_session_acceptance/ACCEPTANCE_RESULT.json`. Production `apps/**` and `src/**` are unchanged.

OpenAI ran at runner `f24d109d0cc0c6b1607dc82034b535c8345681df`. DeepSeek ran after `04ff8908…`, which adds runner-local load sanitization for duplicate node IDs and invalid `node_type`. That sanitizer is a no-op on the frozen OpenAI graphs (zero load rejections). Production runtime is the same in both arms.

Partial / interrupted OpenAI and DeepSeek attempts were discarded. Failure evidence remains under `/tmp/frozen42-openai-partial-*` and `/tmp/frozen42-deepseek-partial-c2s9-failure`. Those databases were operator-reset before the official arms. Partial resume was not treated as a final run.

---

## 2. OpenAI terminal result

| Field | Value |
| --- | --- |
| database | `dmb_full_corpus_openai` |
| world_id | `dogfood-frozen42-openai-v1` |
| genesis `D_0` | `rev:615246aff38a6a53e43a64ffc716471f` |
| `D_0.parent_revision_id` | `null` |
| six PC object IDs | `node:baergrom` `node:bonogo` `node:caelynn` `node:ephanna` `node:karsemine` `node:stafl` |
| C1 S1 parent | `rev:615246aff38a6a53e43a64ffc716471f` (`== D_0`) |
| C1 S1 child | `rev:509e3c8989aa688f7f632d4eaf9b660c` |
| C1 S1 published relationships | 13 |
| receipt count | 42 |
| terminal revision | `rev:6f4667d9b17743860cd38cc8b605466e` |
| native head matches terminal | yes |
| candidate nodes / edges | 1265 / 463 |
| accepted assertions / published relationships | 1441 / 320 |
| terminal objects / relationships / evidence refs | 1115 / 320 / 410 |
| wall seconds (session publishes) | 252.463 |
| model_calls | 0 |
| load rejections | none |

Relationship rejections at the selection boundary:

```text
parent_binding_mismatch     132
unmapped_predicate            69
endpoint_kind_not_admitted    68
unmapped_kind                  5
```

Terminal objects by kind: `item` 332, `mystery` 302, `location` 224, `npc` 121, `group` 65, `faction` 33, `party` 30, `player_character` 6, `creature` 1, `thread` 1.

C1 S1 source admission used historical ID `full-corpus:longmont-c1:session-1:8e4c8600c194` with current-main recap digest `8e4c8600c194cf41641cdeb8c78d9ab20aec3c9b4c65cdb02170e20ecd9545cc`.

---

## 3. DeepSeek terminal result

| Field | Value |
| --- | --- |
| database | `dmb_full_corpus_deepseek` |
| world_id | `dogfood-frozen42-deepseek-v1` |
| genesis `D_0` | `rev:2e2d2a536cf8e1073f537e9286c10d0f` |
| `D_0.parent_revision_id` | `null` |
| six PC object IDs | same six `node:*` IDs as OpenAI |
| C1 S1 parent | `rev:2e2d2a536cf8e1073f537e9286c10d0f` (`== D_0`) |
| C1 S1 child | `rev:e0bf2048942f3209da9bf15d83e37f52` |
| C1 S1 published relationships | 15 |
| receipt count | 42 |
| terminal revision | `rev:bac4c82fb88afb061a9ba855d681ff85` |
| native head matches terminal | yes |
| candidate nodes / edges | 1079 / 636 |
| accepted assertions / published relationships | 1522 / 458 |
| terminal objects / relationships / evidence refs | 1064 / 458 / 402 |
| wall seconds (session publishes) | 179.966 |
| model_calls | 0 |

Load sanitization (frozen bytes unchanged; in-memory drop only):

```text
duplicate_node_id   4   (C2 S9: 3, C2 S12: 1)
invalid_node_type    1   (C2 S9 `sublocation` on candidate:medical-wing)
```

Relationship rejections at the selection boundary:

```text
endpoint_kind_not_admitted    87
unmapped_predicate            84
unmapped_kind                  4
parent_binding_mismatch        3
```

Terminal objects by kind: `mystery` 332, `item` 277, `location` 170, `npc` 161, `faction` 43, `group` 34, `event` 16, `creature` 13, `party` 9, `player_character` 6, `thread` 3.

C1 S1 source admission used the same historical artifact ID and current-main recap digest as OpenAI.

---

## 4. Direct comparison

Genesis semantics were equivalent: same registry digest, same six PC object IDs, same roster key, both `D_0` parents null, both Worlds isolated (no copied head, ledger, or graph body).

Both chains are complete. Native terminal heads match the final children. C1 S1 is an ordinary child of `D_0` in both arms, which is the proof that #715 no longer depends on a special bootstrap route.

Distinguish three difference classes:

**Candidate-generation (frozen input).** OpenAI proposed more nodes (1265 vs 1079) and fewer edges (463 vs 636). Only DeepSeek graphs contained duplicate node IDs and a `sublocation` type that current `load_typed_candidate_graph` rejects. Those are frozen-candidate defects, not production patches.

**Governed-publication (selection boundary).** OpenAI collided with existing object IDs far more often (`parent_binding_mismatch` 132 vs 3). That is identity reuse in the OpenAI candidates against an accumulating World, not a chronology fork. Predicate and endpoint-kind skips are similar in magnitude; DeepSeek published more of its denser edge set (458 vs 320).

**Terminal durable graph.** OpenAI finished with more objects (1115 vs 1064) and fewer relationships (320 vs 458). Kind mix differs: OpenAI carries more items, locations, groups, and parties; DeepSeek carries more NPCs, creatures, factions, and the only `event` population (16). Evidence-ref counts are close (410 vs 402).

More nodes or edges is not treated as better. No arm winner is claimed.

---

## 5. Semantic / query benchmark

Bounded discovery inspected:

```text
evals/sentence_routing_retrieval_falsification
apps/live_control_server/services/graph_gold_review.py
tests/test_cutover_native_genesis_continuity.py
```

None apply identically to these two rehearsal Worlds without new wiring or model calls. No benchmark was invented in this slice.

```text
SEMANTIC MODEL SELECTION HOLD
```

A dedicated evaluation-design successor is required before any arm GO.

---

## 6. What this experiment does not prove

- which frozen extractor is “better”;
- retrieval, query, or GM-facing usefulness of either terminal graph;
- that skipped assertions (unmapped kinds/predicates, colliding CREATE_NEW, duplicate/invalid nodes) should be published;
- that production qualification or candidate-preview validation should change;
- live Campaign 2 S26/S27 (explicitly excluded from the freeze);
- UI, planner, or live-play GO;
- that PR #715 is mergeable product.

---

## 7. Production behavior worth extracting (successors, not this slice)

Runner-local workarounds that protected production:

1. Recap `SourceArtifactV2.world_id` is required at admission; the production creator stays world-neutral. The runner binds World after create.
2. v2 sealed effects expose `accepted_proposals`, not `contribution_slices`.
3. Exact object-ID CREATE_NEW against a parent object is `parent_binding_mismatch`; the runner skips it instead of failing the session.
4. Node kinds with no DungeonMind mapping (`warning` and similar) are skipped at selection.
5. Frozen DeepSeek graphs can fail `load_typed_candidate_graph` on duplicate `node_id` and `node_type=sublocation`. The runner drops those nodes after digest proof so the rest of the session can publish.

None of those were production patches. Extracting any of them into product code is a later, separately leased slice.

---

## 8. #715 retirement recommendation

Keep PR #715 at `820fe3aa…` as the frozen notebook authority. **Do not merge it.** The execution branch must not rebase or cherry-pick it.

After independent evidence review of this report and `ACCEPTANCE_RESULT.json`, a successor may close #715 and retire the notebook worktree. That close is not this slice.

---

## Teardown

**Not started.** Rehearsal databases `dmb_full_corpus_openai` and `dmb_full_corpus_deepseek` remain on the isolated loopback server for independent review. Do not drop them until that review accepts the evidence. Do not drop the PostgreSQL server, volumes, live World authority, or APP-STATE.

---

## Nano-commit chronology (execution branch)

```text
1. 8e010a74  re-anchor frozen 42-session acceptance runner
2. 28345367  prove frozen input and authority fail-closed guards
3. 9c3e1634  bind recap source world before admission
4. ed6ac3fd  qualify v2 proposals and skip colliding CREATE_NEW
5. f24d109d  skip unmapped node kinds at confirm selection
6. 04ff8908  sanitize duplicate and invalid frozen candidate nodes before load
7. (this commit) record two-arm acceptance evidence
```
