# REPORT — DOGFOOD-CONTINUITY current-corpus admission acceptance v1

**Status:** PASS — structural current-corpus admission acceptance on real integrated `main`  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-admission-acceptance-v1.md`  
**Stewardship drain:** `Docs/Plans/HANDOFF-STEWARDSHIP-drain-dogfood-continuity-pr-queue.md`  
**Merged capability chain:** #722 · #723 · #724 · #725 · #726  
**Passing real-main SHA:** `26e40f1eb108544516160a97acc6627fac3fe39d`

## Claim

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE = PASS
SEMANTIC MODEL SELECTION = HOLD
SEMANTIC TRUTHFULNESS / PRECISION / RECALL = NOT ESTABLISHED
```

## Passing execute (post-#726 real main)

```text
run: execute-2026-09-16T020204Z-6e3b812a
git_head: 26e40f1eb108544516160a97acc6627fac3fe39d
manifest: 44 sessions / digest d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c
model: gpt-5.4-mini
model_policy_digest: 477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212
genesis_d0: rev:b31956daf4790c79426381b90cc3fc69
terminal_head: rev:cce8d24621d65a018d3e2922552f56f2
model_calls: 44
graph_writes: 45
stop: null
world: dogfood-current-corpus-acceptance-v1 @ 127.0.0.1:54329 / dmb_current_corpus_acceptance_v1
artifact: out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-16T020204Z-6e3b812a/
```

## Capability chain proven present on real main

| PR | Capability | Merge SHA |
|---:|---|---|
| #722 | Current-corpus structural acceptance harness | `cba8242dee13220f1f8e41469cd6e0edc1e491fc` |
| #723 | Admission endpoint-kind eligibility | `ba0f781b6b3effb4770db3bf171a89da1ce18bae` |
| #724 | Blocked cross-class ID disambiguation | `45c98d425bb61746564f151c2b5adccaa1591898` |
| #725 | Exact durable object-ID continuity | `28f4fb432c71553f2479e02fee851951e20c7ec9` |
| #726 | Exact durable relationship-ID continuity | `23a00dfd1d7eca788e9a3db7875e7443ac83a7dc` |

Synthetic/combined-head 44/44 evidence remains diagnostic history only.

## Remains false

```text
SEMANTIC MODEL SELECTION = HOLD
no model winner exists
no semantic recall/precision/truthfulness score exists
no unattended production batch ingestion exists
```
