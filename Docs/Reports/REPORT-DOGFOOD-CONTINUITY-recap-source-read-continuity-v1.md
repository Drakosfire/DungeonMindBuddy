# REPORT — DOGFOOD-CONTINUITY: recap source-read continuity v1

**Status:** OPEN — implementation PR for recap source-read continuity
**Handoff:** [`HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md)
**Implementation branch:** `dogfood-continuity/recap-source-read-continuity-v1`
**Dispatch base:** `main@bb1b59881e2d6c3a81bd80654b02d0e350c8e6ee` (at/after activation `ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d`)
**Predecessor:** PR #730 merged `ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d`
**Witness World:** disposable `world:recap-source-read-continuity` on `dmb_cutover_test`
**Replay World:** `dogfood-current-corpus-replay-v1` not mutated
**Historical accepted World:** not targeted / not mutated

```text
RECAP SOURCE-READ CONTINUITY = PASS
PRODUCT LOADABILITY          = NOT_READY
OPERATOR DOGFOOD             = NOT_MEASURED
SEMANTIC COVERAGE            = not measured
AGENT ANSWERABILITY          = not measured
SEMANTIC MODEL SELECTION     = HOLD
```

`PRODUCT LOADABILITY` stays `NOT_READY` because the frozen #730 replay World still carries pre-repair evidence stamps (`locator` = `repo://` file URI, `source_span_ref_id` empty, span surviving only inside `evidence_ref_id`). This PR does not parse that opaque ID and does not backfill the replay World. Fresh provenance-correct publications now source-read.

---

## §4 Localization ledger

Traced one Mireward-shaped recap evidence record from the frozen C2S22 candidate through publication and ordinary source-read. No corpus quotes.

### A. Frozen candidate evidence payload

C2S22 `loc:mireward` (and every C2S22 / C1S10 evidence ref inspected) already has first-class span identity:

```text
source_span_ref_id: artifact:recap:longmont-c2:session-22:06c978131f31:span:06c978131f31:14-14
can_highlight_span: True
can_open_source:    True
source_artifact_id: artifact:recap:longmont-c2:session-22:06c978131f31
```

C2S22: 139/139 evidence refs have `:span:<12-hex>:<start>-<end>`. C1S10: 100/100. Missing span count: 0.

The #730 live Mireward witness was session-21 (`ad4ecd013dad`, `span:ad4ecd013dad:16-16` inside `evidence_ref_id`) because the durable node was created there. Same first-class candidate field exists on that session's frozen candidate.

### B. candidate_graph_to_contribution

Mapping requires `source_span_ref_id` and embeds it on `assertion.value["evidence"]`:

```text
evidence_ref_id:     evidence:{artifact_id}:{source_span_ref_id}
source_span_ref_id:  <canonical span>
session_id:          present for recap → locator is not set on the embedded row
```

`evidence_ref_id` concatenates the span as identity. It is not the locator authority.

### C. Governed write recap evidence view — first owning loss (R1)

Before repair, `_recap_extraction_evidence_view` ignored `value["evidence"]` and stamped:

```text
locator:             revision.locator  (repo:// file URI)
uri:                 revision.locator
can_highlight_span:  False
source_span_ref_id:  not a published field
```

### D. EvidenceRefV2 passed into DungeonMind publication

Contribution mapping emits EvidenceRef **v1** (`locator`, `uri`, no `source_span_ref_id`). DungeonMind `review_materialization_v6._lift_evidence` copies `locator`/`uri` and hardcodes `source_span_ref_id=None`. Not R4: v1 `locator` is an existing typed durable pointer into the source body.

### E–F. Stored DungeonMind evidence / SourceAnchorMetadata

#730 replay witness after publication:

```text
source_span_ref_id:  None
locator_identity:    repo://out/registries/source_content/recap/longmont-c2/session-21/<digest>.md
can_open_source:     True
source_domain:       session_recap
evidence_ref_id:     contains span:ad4ecd013dad:16-16  (identity only)
```

Retrieval `_locator_identity` prefers `source_span_ref_id`, then `locator`, then `uri`. With empty span and locator=file URI, `locator_identity` is the file URI.

### G–I. Buddy adaptation / classifier / source-read

`_classify_locator_kind` required `source_span_ref_id` plus `repo://` for recap `source_span`. Heading/json-pointer did not match. Result:

```text
locator_kind:  unsupported
outcome:       partial
diagnostic:    unsupported_locator
digest:        None
```

### Classification

```text
R1 TRUE  — write stamping dropped the already-verified canonical span
R2/R3 TRUE after R1 — even once locator carries the span, Buddy reads ignored
                      locator_identity and required source_span_ref_id
R4 FALSE — DungeonMind persists locator without a pin change
R5 FALSE — candidate/contribution had first-class source_span_ref_id
```

Forbidden: regex on `evidence_ref_id`. Repair uses `assertion.value["evidence"][].source_span_ref_id` at write and typed `locator_identity` at read.

---

## Repair

### Write (`world_graph_writes.py`)

`_recap_extraction_evidence_view` now copies the embedded canonical `source_span_ref_id` onto:

```text
locator:             canonical source_span_ref_id (DungeonMind-persisted pointer)
uri:                 admitted repo:// revision locator (file to open)
can_highlight_span:  True when span present
```

If the embedded span is absent, behavior stays fail-closed: locator remains the file URI and no span is invented from `evidence_ref_id`.

### Read (`world_graph_reads.py`)

For `session_recap` / `recap` anchors, `_product_source_span_ref_id` uses explicit `source_span_ref_id` when present, otherwise a `locator_identity` that already matches the recap paragraph or digest-bound line-span forms. Classifier, source-anchor views, complete-object bindings, and `_read_admitted_repo_span` consume that product span. Heading / json-pointer / worldbuilding / unknown schemes are unchanged.

Digest verification is unchanged: parent bytes must match the admitted source-revision sha256 before any span is sliced.

---

## Witness

Fresh disposable World `world:recap-source-read-continuity` on `dmb_cutover_test` (not the replay DB, not the historical accepted DB):

```text
longmont-c2 / session-22 / node:location:mireward
  source-read outcome: enough
  digest:              admitted recap sha256
  content:             exact cited line ("Mireward sits on the river")

same Mireward anchor pinned at C2 child after a later C1S10 write
  snapshot.revision_id:      C2 child
  snapshot.head_revision_id: C1 child
  digest:                    still the C2 recap
  content:                   does not contain the later C1 sentence

longmont-c1 / session-10 / node:character:torbin
  source-read outcome: enough
  digest:              admitted C1 recap sha256

foreign campaign/revision pin of the C2 anchor
  no verified content returned
```

Deterministic suite also proves: write stamping, no `evidence_ref_id` parsing, replay-shaped file-URI still `unsupported`, heading/json-pointer unchanged, digest-bound extract, tampered bytes `source_integrity_error` with no content, missing revision fail-closed, unknown span miss.

---

## Verification

```text
DMB_CUTOVER_TEST_DATABASE_URL=postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dmb_cutover_test

python -m pytest tests/test_recap_source_read_continuity.py tests/test_candidate_graph_source_provenance_admission.py -m "not integration" -q
  30 passed, 4 deselected

python -m pytest tests/test_recap_source_read_continuity.py -m integration -q
  1 passed
```

---

## Gate B decision

This PR claims **recap source-read continuity PASS** for the production write+read contract and a provenance-correct fresh publication.

It does **not** claim:

```text
PRODUCT LOADABILITY = PASS   # frozen #730 replay World still has pre-repair stamps
OPERATOR DOGFOOD    = PASS
SEMANTIC COVERAGE   = measured
AGENT ANSWERABILITY = measured
```

A later steward slice may replay the 44 frozen candidates through this repaired seam (new World or explicit backfill decision). That is not this PR.

If ordinary World/campaign mounting still fails after a repaired replay, the next slice is Gate C mounting/context.
