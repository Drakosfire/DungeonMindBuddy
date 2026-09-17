# HANDOFF — DOGFOOD-CONTINUITY: recap source-read continuity v1

**Created:** 2026-09-17
**Activated:** 2026-09-17
**Status:** ACTIVE — recap source-read continuity; serial implementation PR authorized
**Canonical path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md`
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY campaign memory`
**Flow / owner:** `DOGFOOD-CONTINUITY / product loadability / recap source navigation`
**Direction:** DESIGN → CODE → REVIEW → TARGETED PRODUCT LOADABILITY
**Design authority base:** `main@ba005c52d892020c4a0dd4a632db38f62c0fda9a` with PR #730 open at design time
**Predecessor PR:** `#730` — `DOGFOOD-CONTINUITY: replay accepted candidates into a pristine World`
**Predecessor merge:** `ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d`
**Reviewed predecessor head:** `634f8d4b0807058a8309d5b19978855b9c7d4cc5`
**Predecessor review:** Cycle 1 APPROVE (GitHub COMMENT fallback, self-review)
**Predecessor durable report path:** `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md`
**Dispatch base:** `main@ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d` — #730 merge; create the implementation branch from current `origin/main` at or after this activation commit
**PR topology:** `serial`
**Authorized branch:** `dogfood-continuity/recap-source-read-continuity-v1`
**Authorized PR title:** `DOGFOOD-CONTINUITY: make recap evidence source-readable`
**PR authorization:** open exactly one implementation PR for this capability. No replay rerun, model work, UI, Hermes, gauntlet, backfill, or successor PR from this worker.

> Repository law: [`AGENTS.md`](../../AGENTS.md). Sequencing authority: [`STEWARDS-ANCHOR-con-ready.md`](STEWARDS-ANCHOR-con-ready.md). Readiness doctrine: [`../Design/ACCEPTANCE-dogfood-readiness.md`](../Design/ACCEPTANCE-dogfood-readiness.md).

---

## §0 Activation gate

Activation is complete. The write lease in §6 is now exclusive for the one authorized PR.

```text
1. satisfied — PR #730 Review Cycle 1 APPROVE on head 634f8d4b0807058a8309d5b19978855b9c7d4cc5
2. satisfied — PR #730 merged as ec286369409bc7b0f86cc1d1c5ff9a31bdd8487d
3. satisfied — replay report durable on main; PASS / NOT_READY / source-read first owning boundary
4. satisfied — this activation records #730 merge/review and releases the replay lease
5. satisfied — no other open implementation PR owns the leased production paths
```

Historical activation requirements, now closed:

Activate only after all of the following are true on `main`:

1. PR #730 has received a formal steward review on its final merged head and is accepted for the bounded evaluation claim;
2. PR #730 is merged;
3. the candidate-replay report is durable on `main` and still establishes:

```text
PRISTINE ACCEPTED-CANDIDATE REPLAY = PASS
PRODUCT LOADABILITY                = NOT_READY
OPERATOR DOGFOOD                   = NOT_MEASURED
first owning boundary              = ordinary recap source-read locator/span continuity
```

4. predecessor state-authority sync records the #730 merge SHA/review count and closes/releases the replay lane;
5. no other open implementation PR in this workstream owns the production paths leased below.

The worker does not activate or materially rewrite this handoff itself.

---

## §1 Where this sits in the CON-READY journey

The line has progressively removed upstream ambiguity:

```text
44-session chronological governed writes
    PASS
        ↓
published-object addressability investigation
    native provenance failure found
        ↓
#729 governed recap source-provenance contract
    PASS for fresh writes
        ↓
#730 exact 44-candidate zero-model replay
    44/44 writes PASS
    campaign projections PASS
    emitted-ID round trip 1041/1041 PASS
    Mireward graph retrieval PASS
    historical revision pinning PASS
        ↓
ordinary recap source-read
    STOP: unsupported_locator / no digest
```

The remaining Gate B failure is no longer graph identity, graph admission, source catalog admission, or ordinary graph retrieval. A product-visible evidence anchor exists and identifies an admitted recap artifact/revision, but ordinary source-read cannot reopen the exact cited source span and therefore cannot return digest-verified source content.

Do not reopen solved upstream contracts merely because source navigation remains broken.

---

## §2 Accepted predecessor evidence

At design time #730 reports the following fresh replay witness:

```text
World:                    dogfood-current-corpus-replay-v1
Database:                 dmb_current_corpus_replay_v1 @ 127.0.0.1:54330
Replay:                   44 / 44 exact frozen candidates
Model calls:              0
Terminal head:            rev:aa435599cb957b666987503b7bef585c
C1 projection nodes:      514
C2 projection nodes:      527
Emitted-ID round trip:    1041 / 1041
C2S22 replay revision:    rev:2ab812818b3e6515b2055e5eb44f5f16
Mireward durable id:      node:location:mireward
C1S10 replay pin:         rev:6d6987d9b3c9d6417e3599888e8ab3f4
```

Mireward evidence/source witness:

```text
source anchor:
source-anchor:v1:5dcd51b3448f82fa92c235ff57b8616b5dca8ab548c05ceb26c84ed50282ca73

source-read outcome:
partial

diagnostic:
unsupported_locator

verified digest:
None

source domain:
session_recap

can_open_source:
True

source artifact:
artifact:recap:longmont-c2:session-21:ad4ecd013dad

source revision:
sha256:ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f

artifact URI / locator identity:
repo://out/registries/source_content/recap/longmont-c2/session-21/ad4ecd013dad92cdcb1a11d412c9f73adb446b15f2ce62cfc50a98358588423f.md

source_span_ref_id:
missing / empty

line-span information:
present only inside evidence_ref_id as `span:ad4ecd013dad:16-16`
```

This evidence is the starting witness, not permission to assume which production function is wrong.

---

## §3 Mission and merge-ready invariant

### Mission

Identify the exact production boundary at which verified recap span identity is lost between candidate/evidence provenance and ordinary product source-read, then repair that one contract without weakening digest verification, inventing evaluator-only locator semantics, or parsing source location out of opaque evidence IDs.

### Merge-ready invariant

> **Every provenance-valid `session_recap` evidence anchor exposed by ordinary Buddy graph reads carries a canonical source locator/span identity that ordinary source-read can resolve against the admitted source revision, returning digest-verified source content bound to the same World/campaign/revision.**

For the known replay witness:

```text
node:location:mireward
→ evidence anchor
→ admitted recap artifact + source revision
→ canonical span locator / source_span_ref_id
→ ordinary source-read
→ outcome = enough | truncated
→ returned digest = admitted source revision content_sha256
→ returned content is from the exact cited recap/span
```

`partial / unsupported_locator` is not success.

The fix must preserve truthful misses and unsupported schemes for genuinely unsupported sources.

---

## §4 Root-boundary localization — prove before editing

Before production edits, trace one Mireward evidence record across these representations at the exact C2S22 replay revision:

```text
A. frozen candidate evidence payload
B. candidate_graph_to_contribution / contribution evidence
C. governed write recap evidence view
D. EvidenceRefV2 passed into DungeonMind publication
E. stored/published DungeonMind evidence record
F. DungeonMind SourceAnchorMetadata returned by retrieval
G. Buddy WorldGraphSourceAnchor adaptation
H. _classify_locator_kind input
I. read_source_anchor_direct dispatch
```

Capture at every stage, when present:

```text
evidence_ref_id
source_artifact_id
source_revision_id
source_domain / source_domain_key
locator / locator_identity
source_span_ref_id
line_start / line_end or equivalent
URI
can_open_source
content_sha256
```

Then classify the first owning loss.

### Case R1 — write stamping drops canonical span identity

The candidate/contribution has a canonical `source_span_ref_id` or equivalent verified span identity, but `_recap_extraction_evidence_view` / EvidenceRefV2 publication does not carry it.

**Repair:** stamp the already-verified canonical span identity into recap EvidenceRefV2 at the governed write mapping boundary. Do not manufacture it from `evidence_ref_id`.

### Case R2 — DungeonMind stores the span, Buddy adaptation drops it

The stored evidence / `SourceAnchorMetadata` carries the canonical span identity but `_source_anchor_views`, `_classify_locator_kind`, or another Buddy direct-read adaptation loses or ignores it.

**Repair:** preserve and consume that explicit source-span field in the ordinary Buddy read path.

### Case R3 — recap source contract legitimately uses URI + explicit line span, but read dispatch lacks that supported form

The authoritative stored evidence carries explicit structured line-span fields but no `source_span_ref_id`, and the repository's recap source contract treats those fields as canonical.

**Repair:** add the smallest explicit recap locator classification/read path that consumes those structured fields and digest-verifies the admitted `repo://` source revision. This must be based on typed metadata, not string parsing of an opaque ID.

### Case R4 — span identity is absent before Buddy and DungeonMind cannot represent the required canonical locator

If the candidate/contribution contains the verified span but the pinned DungeonMind evidence/anchor contract cannot persist or expose it without a dependency/API change:

**STOP / dependency handback.** Record the exact fields present/lost and the minimum DungeonMind contract required. Do not change the dependency pin in this PR.

### Case R5 — the source span was never canonically verified upstream

If no structured verified span exists before publication and the only surviving location is embedded in `evidence_ref_id`, STOP and return an upstream evidence-contract handback. Do not promote opaque ID syntax into a new source-location API inside this slice.

---

## §5 Implementation contract

### 5.1 Explicit locator authority

The repair must use an explicit, already-verified source location field:

```text
source_span_ref_id
or
another typed structured recap span/line locator proven canonical by §4
```

Forbidden as authoritative location sources:

```text
regex/string parsing of evidence_ref_id
node/object labels
artifact-id suffixes
candidate IDs
best-effort text search
LLM/model reconstruction
```

`evidence_ref_id` remains identity, not a hidden locator protocol.

### 5.2 Digest verification remains mandatory

A successful source-read must prove source bytes against the admitted DungeonMind source revision digest.

Required success:

```text
outcome = enough | truncated
content_sha256 / digest present
returned digest == admitted source revision content_sha256
```

Do not turn `partial` into success merely because some bytes were found.

Do not bypass `SourceRepository`, skip revision lookup, or read arbitrary `repo://` files without digest binding.

### 5.3 Same authority context

Source-read must stay bound to the same:

```text
world_id
campaign_id
revision pin
admissibility
source anchor id
source artifact id
source revision id
```

No fallback to terminal head when reading a historical revision. No cross-campaign source rescue.

### 5.4 Preserve generic source behavior

This is a recap-specific continuity repair, not a global locator rewrite.

Existing supported source forms such as heading/json-pointer/worldbuilding spans must continue to behave unchanged. Truly unsupported locator schemes must remain truthful `unsupported_locator` results.

---

## §6 Files in scope — exclusive write lease

This table is the exclusive expected write set while this handoff is ACTIVE.

### Production paths

| Action | Path | Purpose |
|---|---|---|
| MODIFY if R1 proven | `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py` | preserve canonical verified recap span identity when building published evidence |
| MODIFY if R2/R3 proven | `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` | classify/resolve explicit recap span metadata and digest-verify ordinary source reads |

### Tests / report

| Action | Path | Purpose |
|---|---|---|
| CREATE | `tests/test_recap_source_read_continuity.py` | focused deterministic + real-boundary regression for recap anchor → verified source bytes |
| CREATE | `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-recap-source-read-continuity-v1.md` | localization ledger, repair, exact Mireward witness, Gate B verdict |

### Bounded discovery exception

The worker may request one additional production path only if §4 proves the first owning loss is in a directly adjacent typed evidence/source-anchor mapper. **Stop before editing it** and return the exact path + reason to the steward for lease expansion.

Do not self-expand into:

```text
src/graph_memory/extraction/**
source artifact registry semantics
Candidate Graph Admission
source-admission adapter
DungeonMind dependency/pin
UI
Hermes / Agent
benchmark gold
corpus bytes
historical accepted World
replay runner
```

unless the first owning boundary proves this handoff cannot be completed without a deliberate split/lease amendment.

---

## §7 Required regressions

At minimum prove:

1. Mireward-style `session_recap` evidence with canonical span identity produces an ordinary source anchor with that span identity preserved.
2. Ordinary source-read returns `enough` or `truncated`, not `partial/unsupported_locator`, for the recap witness.
3. Successful read returns a digest equal to the admitted source revision `content_sha256`.
4. Returned bytes/text correspond to the exact referenced recap span, not merely the correct file.
5. Same anchor at the same historical revision is deterministic.
6. Historical revision pin does not fall forward to terminal head.
7. Foreign World/campaign/revision anchor fails closed.
8. Missing source revision fails closed.
9. Digest drift/tampered local source bytes fails closed; no content is returned as verified.
10. Unknown span identity remains a truthful miss/partial result; no fuzzy text rescue.
11. `evidence_ref_id` containing a parseable-looking `span:...` string does **not** become readable when the explicit canonical span metadata is absent.
12. Existing supported non-recap heading/json-pointer locator behavior remains unchanged.
13. Genuinely unsupported schemes still return `unsupported_locator`.

At least one integration witness must exercise the real DungeonMind source repository + retrieval anchor + Buddy direct source-read boundary. Helper-only mapping tests do not prove Gate B.

---

## §8 Targeted real witness

After the deterministic suite is green, use a fresh disposable provenance-correct recap publication or, once #730 is merged and its replay World is available locally, a read-only witness against that replay World.

Preferred exact witness after activation:

```text
World:       dogfood-current-corpus-replay-v1
Campaign:    longmont-c2
Revision:    new replay C2S22 child from durable #730 report
Object:      node:location:mireward
```

Required chain:

```text
exact-object / complete-object
→ evidence anchor
→ source-read(anchor)
→ source outcome enough|truncated
→ digest present and equal to admitted revision digest
→ exact cited recap span returned
```

Also prove one `longmont-c1` recap source anchor at the replay C1S10 historical revision so the repair is not specific to Mireward/C2.

The test may read the fresh replay World. It must not mutate or backfill the historical `dogfood-current-corpus-acceptance-v1` World.

---

## §9 Gate B decision

This PR may claim:

```text
RECAP SOURCE-READ CONTINUITY = PASS
```

only when the targeted real witness and focused regression prove exact digest-verified source navigation.

It may advance:

```text
PRODUCT LOADABILITY = PASS
```

only if the durable #730 replay evidence already establishes all other Gate B requirements and this repair closes its sole remaining Gate B STOP without exposing another product-read failure.

It must not claim:

```text
OPERATOR DOGFOOD = PASS
SEMANTIC COVERAGE = measured
AGENT ANSWERABILITY = measured
SEMANTIC MODEL SELECTION = anything but HOLD
```

Those remain later gates.

If source-read goes green but ordinary product World/campaign mounting still fails, the next steward slice is Gate C mounting/context—not more graph/source repair.

---

## §10 Stop / split conditions

STOP and hand back if any of the following is required:

- changing the DungeonMind dependency/pin or source-anchor contract;
- mutating/backfilling the replay World or historical accepted World as the production fix;
- parsing `evidence_ref_id` as the canonical source locator;
- fuzzy searching recap text to reconstruct the cited span;
- weakening digest verification;
- reading arbitrary local paths without admitted revision binding;
- changing candidate semantics/extraction/model policy;
- changing source-admission identity/provenance semantics from #729;
- UI or mounting changes;
- Hermes/Agent/benchmark changes;
- more than the leased production seams without steward expansion.

---

## §11 Review decision signal

Formal review answers, in order:

1. Was the first span/locator loss localized across the full candidate → stored evidence → source-anchor → Buddy read chain?
2. Does the repair use explicit canonical span metadata rather than parsing opaque evidence identity?
3. Does ordinary source-read return digest-verified content from the exact cited recap span?
4. Is the returned source still bound to the same World/campaign/revision/source artifact/source revision?
5. Do tampered bytes, missing revision, foreign context, and unknown spans fail closed?
6. Are non-recap locator behaviors unchanged?
7. Does the real Mireward witness clear `unsupported_locator` without any accepted/replay World mutation?
8. Did the PR avoid reopening admission/write semantics except the narrow R1 evidence stamping seam if localization proved it owns the loss?

A merge-ready PASS closes the specific Gate B source-navigation defect exposed by #730. It does not establish Gate C/D/E.

---

## §12 Worker pickup after activation

Once ACTIVE, read in order:

1. `Docs/Plans/STEWARDS-ANCHOR-con-ready.md`;
2. this handoff;
3. merged `Docs/Reports/REPORT-DOGFOOD-CONTINUITY-current-corpus-candidate-replay-v1.md`;
4. `Docs/Design/ACCEPTANCE-dogfood-readiness.md`;
5. `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` source-anchor/read functions;
6. `apps/live_control_server/integrations/dungeonmind/world_graph_writes.py::_recap_extraction_evidence_view`;
7. relevant evidence/source-span models only as needed for §4 localization.

First worker action is the §4 localization ledger. Do not edit before identifying the first owning loss.
