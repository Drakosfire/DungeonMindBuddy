# REPORT — DOGFOOD-CONTINUITY frozen 42-session two-arm acceptance replay

**Recorded:** 2026-09-15
**Corrected:** 2026-09-15 (evidence-only; no rerun)
**Reviewed predecessor head:** `b0fa4dafe0faf24e94c20691132cd4dffc70e2b5`
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-frozen-42-session-acceptance-replay-v1.md`
**Execution branch:** `dogfood-continuity/frozen-42-session-acceptance-replay-v1`
**Machine evidence:** `out/frozen_42_session_acceptance/ACCEPTANCE_RESULT.json`
**Disposition:** **DO NOT MERGE** this execution branch. **DO NOT MERGE** PR #715. **DO NOT CLOSE** #715. **DO NOT TEARDOWN** rehearsal DBs.

---

## Verdicts

```text
STRUCTURAL ACCEPTANCE HOLD
SEMANTIC MODEL SELECTION HOLD
```

These are independent. Structural HOLD is the acceptance result of this experiment. Semantic HOLD is the intended outcome when no pre-existing deterministic benchmark applies identically; no arm winner is manufactured.

Stop conditions:

```text
candidate_needs_manual_repair
arms_not_run_under_one_execution_head
```

This experiment does **not** have one shared `execution_head_sha`. The arms ran under different runner heads:

```text
OpenAI   runner_head_at_run = f24d109d0cc0c6b1607dc82034b535c8345681df
DeepSeek runner_head_at_run = 04ff89083aabac75c4b7b135e685d1b1efefd44c
```

`04ff8908…` is not an acceptable shared execution head. It performs in-memory semantic candidate repair before `prepare_extract_promote`.

---

## 1. Pipeline / structural verdict

The actual experiment result is:

```text
OpenAI exact frozen replay:
  PASS through 42 sessions
  runner = f24d109d0cc0c6b1607dc82034b535c8345681df

DeepSeek exact frozen replay:
  STOP at C2 S9 because the frozen candidate violates
  the current typed candidate contract
  (duplicate node_id + unsupported sublocation)

DeepSeek sanitized continuation:
  DIAGNOSTIC ONLY
  runner = 04ff89083aabac75c4b7b135e685d1b1efefd44c
  candidate semantics were changed in memory before prepare_extract_promote
  must not count toward structural acceptance
```

Authorities used:

```text
production_base_sha / genesis merge:
876123a3d197d426ce76e03a30f059093ba9b4f4

shared execution_head_sha:
none; arms were not run under one execution head

notebook_head_sha (#715, clean):
820fe3aa5e8ca7301e71f0a4aad05d46e9b486ed

candidate_frozen_head_sha:
d6e2599bbabb9719bc92601f7bc1ad8b69411e98

acceptance_manifest_sha256:
d0f3cb66075f44abe417d5fe149dd31769d1c5b671d02c36534c4e5b43f6c1a1
```

Changed paths versus genesis `876123a3…` remain the leased acceptance files plus this report and `ACCEPTANCE_RESULT.json`. Production `apps/**` and `src/**` are unchanged.

`04ff8908…` is candidate repair, not representation-preserving load hygiene. It keeps the first duplicate `node_id` and drops later nodes, drops unsupported node types, then drops edges, beat references, and proposed writes that pointed at the removed nodes. Frozen DeepSeek C2 S9 shows this is semantic: `candidate:miss-thistlebottoms-emporium` appears as both a **location** and an **organization** with different descriptions; first-wins chooses one interpretation and deletes the other. `candidate:medical-wing` is a `sublocation` with direct source evidence and is deleted entirely.

Exact-frozen DeepSeek STOP evidence from the unsanitized run is preserved under `/tmp/frozen42-deepseek-partial-c2s9-failure` (25 receipts through C2 S8, then `CandidateGraphMappingError` at C2 S9). That failure, not the later sanitized Session-42 chain, is the DeepSeek acceptance result.

---

## 2. OpenAI exact frozen replay — PASS

This arm is acceptance evidence.

| Field | Value |
| --- | --- |
| evidence class | exact frozen replay **PASS** |
| runner | `f24d109d0cc0c6b1607dc82034b535c8345681df` |
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
| load sanitization | none |

Relationship rejections at the selection boundary (governed selection, not candidate repair):

```text
parent_binding_mismatch     132
unmapped_predicate            69
endpoint_kind_not_admitted    68
unmapped_kind                  5
```

Terminal objects by kind: `item` 332, `mystery` 302, `location` 224, `npc` 121, `group` 65, `faction` 33, `party` 30, `player_character` 6, `creature` 1, `thread` 1.

C1 S1 source admission used historical ID `full-corpus:longmont-c1:session-1:8e4c8600c194` with current-main recap digest `8e4c8600c194cf41641cdeb8c78d9ab20aec3c9b4c65cdb02170e20ecd9545cc`.

---

## 3. DeepSeek exact frozen replay — STOP at C2 S9

This is the DeepSeek acceptance result.

```text
exact frozen replay STOP at C2 S9
reason = candidate graph invalid under current typed loader:
         duplicate node_id + unsupported sublocation
```

Unsanitized publication produced 25 receipts (C1 S1–17 + C2 S1–8). C2 S8 child was `rev:50ad9c10ebd2d0bfbd3106317a79640e`. C2 S9 then failed:

```text
CandidateGraphMappingError:
  duplicate_node_id:candidate:miss-thistlebottoms-emporium
  duplicate_node_id:candidate:sputtering-flask
  invalid_semantic_state:candidate:medical-wing:invalid node_type
```

C2 S12 also contains a later duplicate (`candidate:crimson-chorus`) that the exact frozen path never reached.

Genesis through C2 S8 on that failed exact-frozen attempt used the same six PC IDs and the same registry digest as OpenAI. That prefix is not a completed 42-session acceptance chain.

---

## 4. DeepSeek sanitized chain — DIAGNOSTIC ONLY

These metrics are retained because they are useful diagnostics. They **must not** count toward structural acceptance.

| Field | Value |
| --- | --- |
| evidence class | **DIAGNOSTIC ONLY** |
| runner | `04ff89083aabac75c4b7b135e685d1b1efefd44c` |
| database | `dmb_full_corpus_deepseek` |
| world_id | `dogfood-frozen42-deepseek-v1` |
| genesis `D_0` | `rev:2e2d2a536cf8e1073f537e9286c10d0f` |
| C1 S1 parent / child | `rev:2e2d2a536cf8e1073f537e9286c10d0f` → `rev:e0bf2048942f3209da9bf15d83e37f52` |
| sanitized receipt count | 42 |
| diagnostic terminal | `rev:bac4c82fb88afb061a9ba855d681ff85` |
| candidate nodes / edges | 1079 / 636 |
| accepted assertions / published relationships | 1522 / 458 |
| diagnostic terminal objects / relationships / evidence refs | 1064 / 458 / 402 |
| wall seconds | 179.966 |
| model_calls | 0 |

In-memory candidate repair recorded as load rejections:

```text
duplicate_node_id   4   (C2 S9: 3, C2 S12: 1)
invalid_node_type    1   (C2 S9 `sublocation` on candidate:medical-wing)
```

That repair changed candidate semantics before `prepare_extract_promote`: first-wins on colliding IDs, deletion of `sublocation`, then cascade drops of edges / beat refs / proposed writes.

Diagnostic relationship rejections at the selection boundary:

```text
endpoint_kind_not_admitted    87
unmapped_predicate            84
unmapped_kind                  4
parent_binding_mismatch        3
```

Diagnostic terminal objects by kind: `mystery` 332, `item` 277, `location` 170, `npc` 161, `faction` 43, `group` 34, `event` 16, `creature` 13, `party` 9, `player_character` 6, `thread` 3.

---

## 5. Direct comparison

There is **no valid two-arm acceptance comparison**. OpenAI is an exact-frozen 42-session result. DeepSeek's Session-42 terminal is a sanitized diagnostic continuation.

What remains valid to record:

- Genesis semantics were equivalent where both arms actually genesis'd: same registry digest, same six PC object IDs, same roster key, both `D_0` parents null, isolated Worlds.
- OpenAI C1 S1 is an ordinary child of `D_0` with no special first-recap path.
- DeepSeek C1 S1 on the diagnostic chain was also an ordinary child of its `D_0`, but that chain is not acceptance evidence after C2 S9.

Frozen-input defects (not runner mutations, and not silently repairable here):

```text
DeepSeek C2 S9: duplicate node IDs with conflicting kinds/descriptions
DeepSeek C2 S9: unsupported node_type sublocation
DeepSeek C2 S12: duplicate node_id candidate:crimson-chorus
```

The earlier claim that “candidate-generation differences are frozen input differences, not runner mutations” was incomplete. Frozen DeepSeek C2 S9/S12 defects are input-contract findings; the sanitized continuation **was** a runner mutation and is diagnostic only.

`parent_binding_mismatch` 132 vs 3 is useful later semantic-evaluation material. It is **not** an acceptance verdict and cannot be read as DeepSeek being better, because the DeepSeek terminal is not acceptance evidence.

More nodes or edges is not treated as better. No arm winner is claimed.

---

## 6. Semantic / query benchmark

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

A dedicated evaluation-design successor is required before any arm GO. That successor is not this slice.

---

## 7. What this experiment does not prove

- two-arm structural acceptance of the frozen corpus;
- which frozen extractor is “better”;
- retrieval, query, or GM-facing usefulness of either terminal graph;
- that skipped assertions (unmapped kinds/predicates, colliding CREATE_NEW) should be published;
- that first-wins duplicate-ID repair or `sublocation` deletion is an acceptable product behavior;
- live Campaign 2 S26/S27 (explicitly excluded from the freeze);
- UI, planner, or live-play GO;
- that PR #715 is mergeable product or ready to close.

---

## 8. Production behavior worth extracting (not this slice)

Runner-local workarounds that are **in-scope as observations**, not product changes in this branch:

1. Recap `SourceArtifactV2.world_id` is required at admission; the production creator stays world-neutral. The runner binds World after create.
2. v2 sealed effects expose `accepted_proposals`, not `contribution_slices`.
3. Exact object-ID CREATE_NEW against a parent object is `parent_binding_mismatch`; the runner skips it at the selection boundary.
4. Node kinds with no DungeonMind mapping (`warning` and similar) are skipped at selection.
5. Frozen DeepSeek graphs can fail `load_typed_candidate_graph` on duplicate `node_id` and `node_type=sublocation`. Repairing those graphs inside the acceptance runner is forbidden by this handoff.

The designing steward owns any successor capability. This execution branch must not invent that fix.

---

## 9. #715 retirement recommendation

Keep PR #715 at `820fe3aa…` as the frozen notebook authority. **Do not merge it. Do not close it.** Structural acceptance is HOLD, so this handoff does not authorize closure.

---

## Teardown

**Not started.** Rehearsal databases `dmb_full_corpus_openai` and `dmb_full_corpus_deepseek` remain on the isolated loopback server. Do not drop them until a later explicit operator decision after this HOLD evidence is accepted. Do not drop the PostgreSQL server, volumes, live World authority, or APP-STATE.

---

## Nano-commit chronology (execution branch)

```text
1. 8e010a74  re-anchor frozen 42-session acceptance runner
2. 28345367  prove frozen input and authority fail-closed guards
3. 9c3e1634  bind recap source world before admission
4. ed6ac3fd  qualify v2 proposals and skip colliding CREATE_NEW
5. f24d109d  skip unmapped node kinds at confirm selection
6. 04ff8908  sanitize duplicate and invalid frozen candidate nodes before load
             (candidate repair; not an accepted shared execution head)
7. b0fa4daf  record two-arm acceptance evidence (PASS claim; superseded)
8. (this commit) evidence-only correction: HOLD; sanitized DeepSeek diagnostic
```
