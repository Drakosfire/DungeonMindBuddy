# REPORT — DOGFOOD-CONTINUITY: current-corpus candidate replay v1

**Status:** evaluation complete — replay PASS; product loadability NOT_READY
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md)
**Implementation branch:** `dogfood-continuity/current-corpus-candidate-replay-v1`
**Dispatch / activation:** `main@ba005c52d892020c4a0dd4a632db38f62c0fda9a`
**Predecessor:** PR #729 merged `074d4f66f94d4b391a7aaf485b69030a20d576e4` (reviewed head `5cc8a89ce67d2cc9abefe66c7f343f6dd3cb01c3`, review cycle 4 APPROVE `5230245572`)

## Claim

```text
STRUCTURAL CURRENT-CORPUS ACCEPTANCE            = PASS (historical result retained)
FRESH GOVERNED RECAP SOURCE PROVENANCE CONTRACT = PASS (#729)
PRISTINE ACCEPTED-CANDIDATE REPLAY              = PASS
PRODUCT LOADABILITY                             = NOT_READY
OPERATOR DOGFOOD                                = NOT_MEASURED
```

Still false / not established:

```text
semantic truthfulness / recall / precision
Agent usefulness
semantic model selection
historical accepted World repaired
historical backfill safety
```

Do not treat the predecessor's historical `4/16` oracle diagnostic as a replay semantic score.

---

## Exact run provenance

```text
git_head (execute World writes):     ba005c52d892020c4a0dd4a632db38f62c0fda9a
predecessor #729 merge:              074d4f66f94d4b391a7aaf485b69030a20d576e4
accepted source run:                 execute-2026-09-16T020204Z-6e3b812a
accepted artifact root:              out/graph_memory/current_corpus_admission_acceptance_v1/execute-2026-09-16T020204Z-6e3b812a/
accepted manifest count / digest:    44 / d21477c395f7093540491ca17c109a83bdf7e8a4e9f04517f5ef91f5d3d30e5c
candidate cohort verification:       PASS (preflight + execute; exact bytes/digests/order)
frozen model metadata only:          gpt-5.4-mini / 477b9f1541a675dbe1751b9e46c376208cd7a5052207c1059b6c62e981ca2212
model_calls:                         0
candidate_regenerations:             0
candidate_rewrites:                  0
World:                               dogfood-current-corpus-replay-v1
database:                            dmb_current_corpus_replay_v1 @ 127.0.0.1:54330
operator:                            current-corpus-candidate-replay-v1
new D0:                              rev:77fdd25fc46a0dc896a65b679f7dd68f  (null parent; production genesis)
terminal / last_good_head:           rev:aa435599cb957b666987503b7bef585c
graph_writes:                        45  (1 genesis + 44 confirms)
replay ledger rows:                  44 / 44
historical accepted World:           not targeted / not mutated
historical database:                 dmb_current_corpus_acceptance_v1 unused
historical terminal head:            rev:cce8d24621d65a018d3e2922552f56f2 (untouched)
replay execute run:                  execute-2026-09-17T042623Z-efa8bfd3
```

Local artifacts:

```text
out/graph_memory/current_corpus_candidate_replay_v1/execute-2026-09-17T042623Z-efa8bfd3/replay_ledger.json
out/graph_memory/current_corpus_candidate_replay_v1/execute-2026-09-17T042623Z-efa8bfd3/replay_report.json
out/graph_memory/current_corpus_candidate_replay_v1/execute-2026-09-17T042623Z-efa8bfd3/product_smoke_report.json
```

Every confirmable row recorded sealed source admission (`source_artifact_id`, Buddy revision token, DungeonMind `source_revision_id`, `content_sha256`, recap domain, campaign/session) plus exact parent → child head continuity.

---

## Product-loadability evidence

Ordinary Buddy DungeonMind read adapters only. No SQL/raw-payload fallback.

### Campaign projections at terminal head

```text
longmont-c1  nodes=514  relationships=307  revision=rev:aa435599cb957b666987503b7bef585c  diagnostics=[]
longmont-c2  nodes=527  relationships=307  revision=rev:aa435599cb957b666987503b7bef585c  diagnostics=[]
```

No `stored_provenance_invalid`, missing-source, or scope-unknown rejection of replayed recap-backed objects.

### Emitted-ID identity round-trip

A complete identity pass ran before source-navigation was fail-closed:

```text
attempted=1041  passed=1041
covers: exact-object / complete-object / neighborhood / evidence identity
generated_at: 2026-09-17T05:46:53Z
```

That run incorrectly treated source-read `outcome=partial` with no digest as success. Its **identity** totals remain evidence that emitted IDs reopen. Its **Gate B PASS** is withdrawn.

### Mireward at new C2S22

```text
C2S22 child:                         rev:2ab812818b3e6515b2055e5eb44f5f16
C2S22 admitted source artifact:      artifact:recap:longmont-c2:session-22:06c978131f31
C2S22 admitted content_sha256:       06c978131f31e6ec85ff6286fe550f07bd2a3c5972c86bf29533079aebbf7083
product-emitted id:                  node:location:mireward
exact-object:                        enough / resolved_node_id=node:location:mireward
complete-object / neighborhood:      present
evidence:                            enough; 1 session_recap source anchor
source-read:                         FAIL
```

Fail-closed `--product-smoke` (after requiring digest-verified `enough`/`truncated`):

```text
anchor:     source-anchor:v1:5dcd51b3448f82fa92c235ff57b8616b5dca8ab548c05ceb26c84ed50282ca73
outcome:    partial
digest:     None
diagnostic: unsupported_locator: This source anchor's locator/URI scheme is not supported for reading.
```

Resolved ordinary-product metadata for that anchor (not used as a substitute for source-read success):

```text
can_open_source:     True
source_domain:       session_recap
source_artifact_id:  artifact:recap:longmont-c2:session-21:ad4ecd013dad
source_revision_id:  sha256:ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f
artifact.uri / locator_identity:
  repo://out/registries/source_content/recap/longmont-c2/session-21/ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f.md
source_span_ref_id:  None
classified kind:     unsupported
evidence_ref_id contains span:ad4ecd013dad:16-16, which the read adapter does not consume
```

Mireward **opens**. Its admitted source navigation **dead-ends**. That is Gate B NOT_READY.

### C1S10 benchmark pin (recovered; gauntlet not run)

```text
C1S10 child:                 rev:6d6987d9b3c9d6417e3599888e8ab3f4
ancestor of terminal head:   yes (checked on the fail-closed smoke before Mireward source-read)
prior pin object smoke:      node:torbin at the C1S10 revision; no terminal-head leakage
16-question gauntlet:        not run
```

### Operator dogfood

Not attempted. Handoff: if §5 fails, do not reinterpret the failure from UI.

---

## First owning boundary

```text
boundary:     product_loadability / ordinary Buddy source-read
seam:         apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
              _classify_locator_kind / read_source_anchor_direct
related write stamping:
              apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
              _recap_extraction_evidence_view
```

Recap evidence is admitted and projects. The product source-read contract then classifies the recap locator as `unsupported` because:

1. `locator_identity` is the registered `repo://` file URI, not `heading:…` / `jsonptr:…`;
2. `source_span_ref_id` is empty, so the digest-pinned recap span join never runs;
3. the line span lives only inside `evidence_ref_id`.

This evaluation PR does **not** repair that production seam.

---

## PASS / STOP record

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
PRODUCT LOADABILITY                = NOT_READY
OPERATOR DOGFOOD                   = NOT_MEASURED
first owning boundary              = recap source-read locator classification
                                     (unsupported_locator, no digest verification)
```

Next steward slice owns production source-read / recap locator-span stamping. No repair, model-rerun, backfill, UI, Hermes, or successor PR from this worker.
