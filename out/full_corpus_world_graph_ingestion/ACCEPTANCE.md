# PR #715 acceptance notebook — frozen 42-session corpus

**Permanent merge disposition: DO NOT MERGE.**  
Reviewed notebook head: `d6e2599bbabb9719bc92601f7bc1ad8b69411e98`

This experiment is worth finishing only as an acceptance notebook that consumes
current production after governed recap genesis lands.  Do not rehabilitate
this branch into a product PR.

## What this experiment proves

> two autoregressive, chronologically generated candidate arms, followed by
> zero-model governed replay into independently initialized Worlds.

It is **not** evidence that production Session N extraction sees only the
committed World through Session N−1.  During candidate generation,
`run_serial_ingest()` accumulated entities from each prior **candidate graph**
and fed them into the next extraction as `extra_known_entities`.  Errors or
identity choices in each model arm can therefore compound into later prompts.

## Frozen corpus

Exactly **C1 S1–17 + C2 S1–25 = 42 recaps**.  PR #717 already promoted C2
Sessions 26 and 27 to `main`.  Do not regenerate S26/S27 or make new model calls
just to restore the name “full corpus.”

Candidate-generation measurements (not graph-quality results):

| Arm | Candidates | Nodes | Edges | Cost |
| --- | ---: | ---: | ---: | ---: |
| OpenAI `gpt-5.4-mini` | 42 | 1,265 | 463 | ~$3.33 |
| DeepSeek V4.1 Flash | 42 | 1,079 | 636 | ~$0.60 |

Immutable candidate/source digests live in `ACCEPTANCE_MANIFEST.json`, frozen
from the reviewed notebook head above.  Replay must verify live bytes against
that manifest.  It must not compute a new hash and treat that newly computed
value as the seal.

## Manifest immutability

`ACCEPTANCE_MANIFEST.json` is immutable after the hardening commit that first
force-adds it.  If a later live candidate or source hash disagrees with that
file, replay fails.  Nobody updates the manifest to make it pass.  A changed
candidate is a different experiment, not a patch to this one.

The execution invariant is:

```text
#715 frozen candidate bytes
        +
current-main production contracts
        +
merged governed genesis
        ↓
two isolated zero-model acceptance replays
```

not `#715 branch code → production`.

## Pre-execution blockers

1. **Wait for PR #718.**  Do not manufacture a World head, use SQL, or copy
   another graph.  After #718 lands, re-anchor the **runner**, not this branch:
   current `main` supplies production code; this notebook supplies frozen
   candidates plus narrowly retained experiment tooling.
2. Rehearsal DSNs must be loopback `127.0.0.1:54329` (localhost/`::1`
   accepted as loopback).  `run_arm()` binds each arm to one database:
   `openai-gpt-5.4-mini` → `dmb_full_corpus_openai`,
   `deepseek-v4.1-flash` → `dmb_full_corpus_deepseek`.  Swapped pairings are
   rejected.  Live authority ports `54330`/`54331` are forbidden.
3. Historical candidate `source_artifact_id` values are rebound only inside
   the acceptance harness after freeze verification.  Production
   `create_recap_source_artifact()` does not accept a caller-selected identity.

## Closure evidence required before retiring #715

- identical canonical genesis-source digest semantics in both authorities
- six baseline PCs visible through native mutation context
- each arm's C1 S1 has `parent_revision_id == its own D_0`
- all 42 replay receipts form one exact uninterrupted parent chain
- all 42 recap sources are admitted with correct campaign/session/openable provenance
- candidate-edge vs rejected-edge vs published-edge totals
- terminal graph/entity/relationship health
- the intended continuity/query benchmark and direct OpenAI-vs-DeepSeek comparison
- explicit confirmation of **zero new model calls** during replay
- a final GO/HOLD assessment of the graph approach/model arm
- teardown of exactly the two rehearsal databases after evidence capture

Then extract any one genuinely reusable production behavior into a small PR,
preserve this bounded report, and **close #715 without merging it**.

## Salvage classification

- **Already promoted:** `pc ≡ player_character` via #716.  Do not extract it again.
- **Reject as product contract:** caller-selected recap `source_artifact_id`.
- **Reject/defer as-is:** generic `extra_known_entities: tuple[Any, ...]`.
- **Potential later focused PRs:** intra-document `node_pass_workers` + pass
  telemetry; DeepSeek/OpenRouter pass client only if provider diversity is itself
  a product requirement.
- **Notebook only:** census, ingest, publication tools, model outputs,
  receipts, scale reports, provisioning notes.
