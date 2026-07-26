# HANDOFF — SBW06 Candidate revise/regenerate and lineage

**Created:** 2026-07-22
**Updated:** 2026-07-25 — `SBW07` COMPLETE (`#409` / `455daf49`); `SBW06-contract` active (doc-only freeze)
**Status:** `SBW06a` — IN PROGRESS (exact edited `source_definition` adapter + revise journal)
**Canonical handoff path:** `Docs/Plans/HANDOFF-sbw06-candidate-revise-lineage.md`
**Workstream:** `SBW06`
**Repository:** `Drakosfire/DungeonMindBuddy`
**PR base / repository tip:** `742415e7` on `main` (includes `#409` SBW07c merge)
**Logical SBW predecessor:** `#409` / `455daf49897bce0235972e7b9f07c3656a3fe27b` — `SBW07c` Accept UI + corpus demolition (SBW07 COMPLETE)
**This PR:** `SBW06-contract` — revise journal, source identity, lineage, status, capacity, partial completion
**Next after this PR merges:** `SBW06a` (only if §12.11 Server revise recovery gate is closed)

> Dispatch one capability across a contract PR plus four code PRs: create a new candidate proposal from an exact source and preserve lineage. Do not persist mechanics, compare accepted revisions, update graph bindings, or generate media.

## Bite schedule

| Bite | Status | PR mission | Allowlist focus | Still false |
|---|---|---|---|---|
| `SBW06-contract` | **this PR** | Doc-only: freeze §12 revise authority tables | Docs only; no implementation | All code |
| `SBW06a` | after contract + §12.11 gate | Exact edited `source_definition` adapter + revise journal | Client + revision service + tests | Status UI, accepted-revision source, ThreatDraft lineage attach as ordinary success |
| `SBW06b` | after `SBW06a` | Durable candidate ref with embedded `CandidateLineageV1`, status transitions | Draft store/ref transitions + tests implementing frozen §12.8 | UI, accepted-revision revise |
| `SBW06c` | after `SBW06b` | Workbench revise UX | Workbench + liveApi | Accepted-revision source, compare, append |
| `SBW06d` | after `SBW06c` | Exact accepted `source_locator` revise | Service/route/UI using SBW07 locators | Graph, SBW13 append, compare, media |

**Why after SBW07:** accepted-revision source needs exact locators; revise durability is deferred until first mechanics save is proven (SBW03 / SBW07b–c lesson).

## §12 Revise contract freeze (normative — `SBW06-contract`)

This section is the **approve-or-reject contract** for `SBW06-contract`. Implementation (`SBW06a–d`) may not invent alternate journals, latest/name source selection, local abandon, replacement `request_id` while claim existence is unresolved, automatic source supersede, or SBW07 second-save / SBW13 append behavior.

**Re-anchor evidence (2026-07-25):**

| Fact | Value |
|---|---|
| Buddy vendored OpenAPI fingerprint | `sha256:770cb3ae5e72b0997b3b9a99462bc64f53a632a94aa2bc21dffa6bc7297662fe` |
| Current DungeonMindServer OpenAPI fingerprint (on disk) | `sha256:d51883b9495f8f42db88abdcb7d5290ca3790519eaf63c6350dbe91c3122a09c` |
| `ReviseCandidateRequestV1` / `ExactRevisionLocatorV1` equality across fingerprints | **Equal** (revise transport shapes match; full OpenAPI still lags — separate backlog vendor sync) |
| Server revise route | `POST /api/internal/dungeonbuddy/v1/statblock-candidates:revise` (`revise_statblock_candidate_v1`) |
| Server revise idempotency | **Same-key replay / changed-body conflict** (Server PR #24; §12.11 gate closed for `SBW06a`) |
| Buddy revise fixtures / transcripts | Captured under `tests/fixtures/statblocks/v1/server_revise_transcripts/` (`SBW06a`) |
| Design-only revise fixture (Server, non-v1 API shape) | `DungeonMindServer/Docs/Design/fixtures/statblockgenerator-command-board-contract/revise_existing.latch_harrow_weaker.json` — **not** a v1 transport fixture |
| Candidate-ref capacity | `ThreatDraftV1.candidate_refs` `max_length=64` (`_MAX_LIST`) |

### 12.1 Server transport source-variant inventory

Exactly one mechanics source is supplied on `ReviseCandidateRequestV1`:

| Variant | Schema | Required fields | Forbidden |
|---|---|---|---|
| `source_definition` | `StatblockDefinitionV1-Input` | Complete typed definition body | Pairing with `source_locator` |
| `source_locator` | `ExactRevisionLocatorV1` | `statblock_id` (`^sb_[a-z0-9]+$`), `revision_id` (`^rev_[a-z0-9]+$`) | Pairing with `source_definition`; latest/name/slug lookup |

Server model validator (`exactly_one_revision_source`): both absent or both present → `invalid_request` / 422.

**Not a third transport source:** optional `source: SourceSnapshotV1 | null` is descriptive context (`name_hint`, `description`, optional `description_digest`). It is never a selection key and never substitutes for `source_definition` / `source_locator`.

**Additional Server request fields (closed for SBW06):**

| Field | Contract |
|---|---|
| `request_id` | Required; Buddy revise journal key |
| `ruleset` | Required `RulesetRef` |
| `revision_instructions` | `string[]` with `minItems: 1` (empty instructions invalid) |
| `preserve_element_keys` | `bool` default `true` — **boolean only**; no `preserve_sections` / per-key list in current OpenAPI |
| `intent` / `context` / `asset_options` / `actor` | Pass-through; `asset_options.generate_images` must remain `false` for SBW06 (no media) |

Success response: `GeneratedStatblockCandidateV1` (new `candidate_id`). Error envelopes use typed `ErrorDetailV1.code` (404 source missing, 422 invalid/validation, 429 rate limit, 500 unexpected, 504 timeout, 503 persistence when applicable). **No 409 idempotency conflict** is advertised for revise.

### 12.2 Transport variant ↔ Buddy lineage origin mapping

Do not invent a third Server request variant because Buddy has three lineage origins.

| Buddy lineage origin | Server transport | Lineage must record (required fields) |
|---|---|---|
| `edited_working_copy` | `source_definition` | `draft_id`; `source_draft_version` (ThreatDraft `version` at submit); `editor_state_revision` (SBW05 editor `stateRevision`); canonical **revise-source** definition digest of the submitted body |
| `candidate` | `source_definition` (payload read from exact `candidate_id`) | Exact `source_candidate_id`; that candidate’s generating `request_id`; `draft_id` + `generated_from_draft_version` from the source candidate ref; canonical **revise-source** definition digest of the exact payload/body used to build `source_definition` (**required** — not optional / not “when available”). Does **not** require editor `stateRevision`. |
| `accepted_revision` | `source_locator` (`statblock_id` + `revision_id` only) | Full SBW07 six-field locator: `provider`, `statblock_id`, `revision_id`, `contract`, `contract_version`, `definition_digest` |

Buddy must:

- validate the full accepted locator before mapping down to Server `ExactRevisionLocatorV1`;
- perform exact revision reads where required and reject digest disagreement;
- refuse `candidate` origin when the exact payload cannot be read or its revise-source digest cannot be computed;
- never fall back to latest / display-name / slug / corpus-path.

### 12.3 Canonical source identity and digest rules

These digests are **not interchangeable**:

| Digest / identity | Authority | Authorizes |
|---|---|---|
| **Revise-source definition digest** | Canonical digest of the exact `source_definition` body submitted (or resolved from locator before provider call) | Exact source identity for lineage + request digest inputs |
| SBW05 local editor fingerprint | Client-local working-copy fingerprint | UI dirty/undo only |
| SBW05 authoritative validation digest | Server validate receipt / `definition_digest` | Mechanics accept eligibility (SBW07) — **not** revise dispatch by itself |
| Candidate-cache envelope digest | Buddy cache boundary | Payload integrity in cache |
| Accepted mechanics `definition_digest` | SBW07 locator field | Exact accepted revision identity; required for `accepted_revision` origin |

A revise-source digest proves exact source identity. It does **not** authorize mechanics persistence.

### 12.4 Instructions and request digest / idempotency inputs

**Buddy-owned bounds** (Server OpenAPI currently has no max length/max items on instructions):

| Rule | Closed decision |
|---|---|
| Maximum instructions | ≤ 16 non-empty strings after normalization |
| Maximum length per instruction | ≤ 500 Unicode code points |
| Maximum total instructions payload | ≤ 4000 Unicode code points |
| Normalization for digest | Trim each string; drop empty; preserve order; **do not** collapse internal whitespace; join with `\n` for digest material |
| Empty after normalization | Reject before journal claim (`revise_blocked` / validation) — aligns with Server `minItems: 1` |
| Whitespace vs replay identity | Changing only trimming-significant whitespace that normalization removes does **not** change digest; changing internal whitespace **does** |
| `preserve_element_keys` | Included in request digest as boolean |
| Logs / ordinary diagnostics | Record instruction digest, instruction count/length, `preserve_element_keys` — not full private prose by default |

**Request digest inputs** (canonical JSON / byte recipe frozen in `SBW06a` to match journal claim):

```text
request_id is the durable key (not digested into itself as a changing field)
digest covers:
  source variant tag (definition | locator)
  revise-source definition digest OR full accepted locator fields used for mapping
  normalized revision_instructions
  preserve_element_keys
  ruleset
  intent / context / asset_options / optional source snapshot fields actually sent
```

**Replay rules (Buddy journal authority):**

| Case | Behavior |
|---|---|
| same `request_id` + same exact request body/digest | Same logical revise operation; return stored authority / continue recovery — **do not** mint a new candidate identity locally |
| same `request_id` + changed body/digest | `acceptance`-style input conflict: original journal authority intact; no mutation |
| new `request_id` | New proposal **only** when no unresolved same-operation recovery blocks the draft/UI |

The revise journal retains the exact bounded request body needed for same-key replay.

### 12.5 Separate-versus-reused journal decision

**Decision: SEPARATE revise-operation journal**, sibling to the SBW03 generation journal and SBW07 acceptance journal under the draft state root. Distinct schema namespace (expected: `dmb_statblock_revise_operation_v1`).

**Rationale:** Server revise is non-idempotent and has distinct source XOR rules, instruction digest inputs, lineage, and source-status materialization. Reusing the generation journal would conflate active-slot rules, terminal inventories (`terminal_expired` / tombstones / claim TTL), and recovery actions.

**Patterns that may be reused:** strict versioned models, path confinement, atomic file replacement, file locking, canonical request-body digest, same-key replay, changed-body conflict, failure injection, materialization-state tracking, reload validation, durable recovery pointer.

**Patterns that must not be copied without explicit approval:** claim TTL, local abandon, `terminal_expired`, tombstones, compaction, generation-specific terminal error inventory, generation-specific record limits, silent history eviction.

### 12.6 Closed revise operation transition table

Journal owns operation authority. ThreatDraft owns reconciled candidate refs + embedded lineage only after materialization succeeds.

**Active-slot rule (closed):** at most **one unresolved revise operation per draft**. An unresolved revise is any journal row for that `draft_id` whose status is not `reconciled` and not `terminal_failure`. A second distinct `request_id` that attempts to claim while one unresolved revise exists receives **`revise_busy`** and must not create a journal claim, must not dispatch, and must not reserve capacity.

**Write-ahead dispatch rule (closed):** Server revise I/O is forbidden while the journal status is `claimed`. Required sequence for a fresh dispatch:

```text
claimed
  → durably write status = dispatched_unknown (same request_id / body / digest)
  → only after that journal replace succeeds, begin the HTTP revise request
```

Recovery that observes `claimed` must **not** treat “Allowed retry: dispatch” as permission to POST. It may only perform the durable `claimed → dispatched_unknown` write-ahead step, after which the §12.11 no-re-POST rule applies. Observing `claimed` after a crash is **not** proof that Server I/O never began if a prior process skipped write-ahead (implementation defect); implementations must not skip write-ahead, and recovery must still refuse re-POST from `claimed` by first advancing to `dispatched_unknown` without HTTP, then applying §12.11.


| State | Durable evidence required | `candidate_id` permitted? | Candidate payload permitted? | Cache mat. | Draft-ref mat. | Source-status mat. | Allowed retry | Same-key replay | New `request_id` allowed? | Terminal proof required | Client-visible result |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `claimed` | Journal row with exact body/digest; holds active revise slot + capacity reservation; **Server I/O has not begun** | no | no | `missing` | `missing` | `none` | write-ahead transition to `dispatched_unknown` only — **never** HTTP revise from this state | retain body | no | no | `revise_claimed` / pre-dispatch |
| `dispatched_unknown` | Durable write-ahead proof that Server I/O was authorized to begin (or already began); transport/outcome may be unknown; slot+reservation retained | only if later observed | only if later observed | `missing`/`failed` | `missing` | `none` | bounded lookup / reconcile only; **re-POST forbidden** while §12.11 gate open | retain | no | no | `dispatched_unknown` |
| `candidate_received` | Exact `candidate_id` (+ payload or exact-read handle) recorded on journal; reservation retained until draft attach | yes | yes if stored | `missing`/`stored`/`failed` | `missing`/`failed` | `none` | materialize cache then one CAS attach | return recorded candidate | no | no | partial; not ordinary product success |
| `cache_stored_ref_pending` | Cache has payload; draft ref not attached; reservation retained | yes | yes | `stored` | `missing`/`failed` | `none` | one ThreatDraft CAS: append ref+lineage and any requested source-status together | same | no | no | partial |
| `reconciled` | Candidate ref + required embedded lineage visible on ThreatDraft read path; requested source-status applied in that same CAS or proven `none` was requested | yes | yes or honest unavailable | `stored` or honest miss after attach | `attached` | `applied`/`none` | read-only reload | return reconciled | yes (new proposal) | no | ordinary revise success |
| `terminal_failure` | Owning boundary proves non-begin or terminal failure for **this** `request_id`; active slot and capacity reservation released | no | no | `missing` | `missing` | `none` | start **new** `request_id` only after this proof | n/a | yes | **yes** | `terminal_failure` |
| `revise_blocked` (pre-claim) | Validation / version / source identity failure **before** journal claim; no slot taken | no | no | n/a | n/a | n/a | correct inputs; new attempt may mint new id | n/a | yes | n/a (no claim) | ephemeral block |
| `revise_busy` | Another unresolved revise already occupies this draft’s active revise slot | no | no | prior unchanged | prior unchanged | prior unchanged | wait / resume the occupying `request_id` | n/a | **no** | no | `revise_busy` |
| `revise_history_full` | Capacity admission failed under lock (§12.10); no claim | no | no | prior unchanged | prior unchanged | prior unchanged | free capacity then new attempt | n/a | yes (no claim held) | no | `revise_history_full` |
| `revise_input_conflict` | Same `request_id` + changed body against existing journal authority | no new | no | prior unchanged | prior unchanged | prior unchanged | resume original body only | original retained | no | no | `revise_input_conflict` |
| `revise_draft_unavailable` | Draft missing/unreadable for claim or reconcile | no | no | prior unchanged | prior unchanged | prior unchanged | restore draft then resume same `request_id` | retain if claimed | no while claim may exist | no | `revise_draft_unavailable` |

**Removed state:** `ref_attached_status_pending` does not exist. Requested source-status transitions are not a separate post-attach journal product state.

There is **no** local “abandon revise” action. Local storage deletion is not backend closure. A replacement `request_id` is allowed only after backend-proven `terminal_failure` / non-begin for the prior operation (SBW07c lesson), which also releases the active slot and reservation.

### 12.7 Closed materialization / recovery table

| Window | Truthful behavior | Recovery key |
|---|---|---|
| Crash after `claimed` write, before write-ahead | Resume same `request_id`; perform durable `claimed → dispatched_unknown` only; **do not POST** from `claimed` | same `request_id` |
| Crash after durable `dispatched_unknown`, before/during/after HTTP, before candidate recorded | Remain `dispatched_unknown`; **re-POST forbidden** until §12.11 gate closes; slot+reservation retained | same `request_id` |
| Server candidate exists, response lost (after write-ahead) | Remain `dispatched_unknown` until candidate identity is known by an approved recovery path (§12.11); never claim ordinary success; slot+reservation retained | same `request_id` |
| Server candidate returned, journal update fails | Retry journal write; do not delete Server candidate | same `request_id` |
| Journal has candidate, cache write fails | `candidate_received` + cache `failed`; exact-read handle retained | same `request_id` |
| Cache succeeds, draft-ref append fails | `cache_stored_ref_pending`; no ordinary success; reservation retained | same `request_id` |
| ThreatDraft CAS for ref+lineage(+requested status) fails | Leave journal at `cache_stored_ref_pending`; retry the **same** both-or-neither CAS; never attach ref without the requested status (or without lineage) | same `request_id` + draft version CAS |
| ThreatDraft CAS succeeds; journal reconcile write fails | Reread draft; if ref+lineage(+requested status) already present for this `request_id`/`candidate_id`, mark journal `reconciled` and release reservation. This is **not** a product state with ref attached and status unapplied | same `request_id` |
| Draft mutation commits, client response lost | Reload via journal + draft read converges to reconciled | same `request_id` |
| Reload during any window | Restore journal pointer; classify; continue same operation | same `request_id` |

**Atomic draft-mutation invariant (closed):** one ThreatDraft CAS either (a) appends the new candidate ref **with required embedded lineage** and applies any explicitly requested source-status transition, or (b) applies none of those writes. There is no durable product state where the new ref is attached while a requested source-status transition remains unapplied.

**Ordinary product success** means: ThreatDraft read path shows the new candidate ref with required embedded lineage, cache/payload availability is honest, and any explicitly requested source-status transition is applied. Downstream Server success alone is never ordinary product success.

### 12.8 Candidate lineage persistence

**Durable ownership (closed):** Buddy lineage for a revise-created candidate is stored **on the ThreatDraft candidate ref itself** as a required nested object (`lineage`), not as a sibling draft record and not deferred to a later schema choice in `SBW06b`. `SBW06b` implements this frozen shape; it does not reopen ownership.

Pre-SBW06 generate refs may have `lineage: null`. Every revise-created ref **must** include `lineage` or the CAS must fail closed (no append).

**Request-identity binding (closed):** for every revise-created candidate ref:

```text
candidate_ref.request_id
  = lineage.revise_request_id
  = revise journal request_id
  = Server ReviseCandidateRequestV1.request_id
```

A mismatch fails validation / CAS fail-closed. Deduplication, recovery, and reservation release must consult this single identity (via `candidate_ref.request_id`, which equals `lineage.revise_request_id`).

**Frozen schema `CandidateLineageV1` (structurally closed by `source_origin_kind`):**

```text
schema: dmb_candidate_lineage_v1
common required:
  revise_request_id
  source_origin_kind: edited_working_copy | candidate | accepted_revision
  instruction_options_digest
  created_at
  # optional, never a substitute for Buddy lineage:
  #   server_generation_receipt_excerpt / provenance pointer

exactly one origin variant object present; fields of other variants absent:

edited_working_copy:
  draft_id
  source_draft_version          # ThreatDraft.version at submit (single definition)
  editor_state_revision         # SBW05 editor stateRevision
  source_definition_digest

candidate:
  source_candidate_id
  source_candidate_request_id   # request_id that created the source candidate
  draft_id
  source_generated_from_draft_version
  source_definition_digest      # digest of exact payload used for Server source_definition

accepted_revision:
  provider
  statblock_id
  revision_id
  contract
  contract_version
  definition_digest
```

Validation fail-closed if: more than one origin variant present; required fields for the declared kind missing; fields belonging to another kind present; or `revise_request_id != candidate_ref.request_id`.

Rules:

- Lineage is additive with the new ref; never rewrites the source candidate payload or identity.
- Full working definition is not duplicated into ThreatDraft merely for lineage.
- Exact replay material lives in the revise journal / cache boundary.
- A candidate ref that cannot identify its exact source must not be appended.
- New candidate ref + required lineage (+ requested status) become visible atomically on the ThreatDraft read path via the single CAS in §12.7.
- Dedupe keys for attach: `candidate_id` and bound `request_id` / `revise_request_id` (same-key recovery must not append a second ref).
- Lifecycle status remains on the same `ThreatDraftCandidateRefV1` object as `lineage` (§12.9).

### 12.9 Closed candidate-status transition table + `accepted_source` decision

Current vocabulary on `ThreatDraftCandidateRefV1.status`:

`active | superseded | rejected | expired | accepted_source`

**`accepted_source` decision:** remains a **mutually exclusive lifecycle state** on the candidate ref (not a separate parallel provenance channel). It is **not** prior contract approval merely because the literal exists today; SBW06 freezes transitions as follows.

| From | To | Who may request | Preconditions | Idempotency | Invalid response |
|---|---|---|---|---|---|
| `active` | `superseded` | Explicit revise/status API with `expected_draft_version` | Ref exists; payload availability does **not** block | Same transition no-op | 409 invalid transition / stale version |
| `active` | `rejected` | Explicit API | Ref exists | Same no-op | 409 / stale |
| `active` | `expired` | System/reconcile only when candidate expiry proven | Exact expiry evidence | Same no-op | fail closed if unproven |
| `active` | `accepted_source` | Only when draft holds `accepted_mechanics_ref` whose `accepted_from_candidate_id` equals this `candidate_id` (SBW07 path or explicit repair) | Exact mechanics ref proof | Same no-op | 409 if proof missing |
| `accepted_source` | any other | **Forbidden in SBW06** | — | — | 409 |
| `superseded` / `rejected` / `expired` | any other | **Forbidden in SBW06** | — | — | 409 |
| any | same status | Explicit retry | — | Idempotent success | — |

**Required invariant:** creating a new revise candidate does **not** automatically supersede or reject its source.

If a revise request asks to supersede its source after success:

```text
append new candidate ref + lineage
AND
apply requested source-status transition
```

must occur in **one atomic ThreatDraft CAS mutation** and one draft-version increment. If no source-status transition was requested, the source remains unchanged.

### 12.10 Candidate-history capacity and admission reservation

Hard bound: `ThreatDraftV1.candidate_refs` `max_length = 64`.

**Admission formula (evaluated under the draft-scoped lock at claim time):**

```text
attached = len(draft.candidate_refs)
reserved = count of unresolved Buddy journal operations for this draft_id
           that will append a candidate ref and have not yet attached one
           (includes this draft’s unresolved revise ops, and any unresolved
            SBW03 generation ops that will append a ref)
admit revise claim only if attached + reserved < 64
```

The durable capacity reservation **is** the unresolved journal claim itself (no separate reservation file). Claiming a revise increments `reserved` until attach or terminal release.

**Reservation release:**

| Event | Reservation | Active revise slot |
|---|---|---|
| ThreatDraft CAS attaches this operation’s ref (`reconciled` path) | released (capacity now counted in `attached`) | released |
| `terminal_failure` / proven non-begin | released without consuming an attached ref | released |
| Local abandon / storage clear | **does not** release | **does not** release |

**History-full behavior:**

```text
attached + reserved >= 64
→ return revise_history_full before journal claim and before Server dispatch
→ create no Server candidate
→ delete no historical ref
→ preserve current draft and instructions
```

Combined with §12.6’s one-unresolved-revise rule, two distinct revise `request_id`s cannot both pass admission against the final open slot: the second receives `revise_busy` (if a revise is already unresolved) or `revise_history_full` (if reservation/attached already saturates capacity).

Do not drop oldest refs, compact silently, reuse `candidate_id`, overwrite superseded/rejected refs, or call Server then discover no admission capacity. Archival model requires a separate design review (stop condition).

### 12.11 Partial completion, Server non-idempotency, and SBW06a gate

Expected orchestration:

```text
1. Validate exact source + local admission capacity + instruction bounds + draft version.
2. Durably claim revise request_id with exact request body/digest (status=claimed).
3. Durably write claimed → dispatched_unknown (write-ahead).
4. Only after step 3 succeeds: HTTP revise dispatch (or Buddy same-key local replay of an already-recorded candidate — never a second POST while gate open).
5. Durably record returned candidate identity/payload or exact-read handle.
6. Store/read candidate through Buddy cache boundary.
7. Atomically append new candidate ref + lineage and any explicitly requested source-status transition.
8. Mark revise operation reconciled.
9. Return ordinary success only when the promised product read path is available.
```

**Server fact:** revise is currently **non-idempotent**. Blind re-POST of the same `request_id` after any Server-reaching attempt can create orphan Server candidates.

**Closed recovery rule for SBW06:**

1. Buddy journal provides same-key / changed-body authority locally.
2. Recovery that sees `claimed` performs write-ahead to `dispatched_unknown` only; it does **not** POST from `claimed`.
3. When `candidate_id` is already recorded, recovery uses exact `GET /statblock-candidates/{candidate_id}` (or cache) — never a speculative re-revise.
4. While `dispatched_unknown` and `candidate_id` is unknown, retain `request_id`; UI may retry lookup/reconcile only.
5. **Automatic re-POST of revise is forbidden** from `dispatched_unknown` (and therefore also after write-ahead from a recovered `claimed`) until one of the following gates is proven and recorded in the `SBW06a` PR evidence:
   - Server ships revise same-key replay / changed-body conflict comparable to generate; **or**
   - Server exposes an exact `request_id` → candidate index Buddy can read without creating a new candidate; **or**
   - a reviewed, evidence-backed recovery protocol that cannot orphan-duplicate (design review required).

**`SBW06a` implementation gate:** do not merge `SBW06a` while gate (5) is unmet. The contract PR may still be approved with this gate explicit.

Truthful partial-completion invariants otherwise match SBW03/07:

- Downstream success is never rolled back by deleting the Server candidate.
- Partial local failure never claims ordinary product success.
- Same `request_id` remains the recovery key; recovery does not mint a replacement id.
- Changed-body retry conflicts without mutating original authority.
- Reconciliation converges to one candidate ref and one lineage record.

### 12.12 Lock ordering and atomic draft-mutation boundary

```text
1. Draft-scoped lock (prevent concurrent writers)
2. Pre-claim gates under that lock:
     - source/instruction/version validation → revise_blocked (no claim)
     - active revise slot free → else revise_busy (no claim)
     - capacity admission (attached + reserved < 64) → else revise_history_full (no claim)
3. Journal claim (single-record atomic replace) acquires active revise slot + capacity reservation (status=claimed)
4. Durably write claimed → dispatched_unknown (still under lock or as the next atomic journal replace)
5. Release draft lock only after step 4 succeeds
6. Begin Server HTTP revise (or local same-key replay of recorded candidate)
7. On Server success: re-acquire → journal candidate_received → cache write
8. ThreatDraft CAS is the only product mutation boundary:
     append ref with required embedded lineage
     AND apply any requested source-status transition
     OR apply neither
     (candidate_ref.request_id == lineage.revise_request_id == journal/Server request_id)
9. Journal reconcile to reconciled; release reservation + active slot
10. On terminal/non-begin proof: journal terminal_failure; release reservation + active slot
```

Journal and ThreatDraft are separate durable records; ordering is restart-recoverable, not multi-record transactional. The active-slot and reservation rules exist specifically so lock release during Server I/O cannot overbook the final candidate-ref slot.

### 12.13 No-abandon / no-replacement-ID rule

Copied from proven SBW07c recovery:

- No UI “abandon revise” that only clears local storage.
- No replacement `request_id` while prior operation may still claim or while `dispatched_unknown`.
- Replacement only after owning-boundary terminal/non-begin proof.

### 12.14 First-save versus append-revision product boundary

| Draft state | SBW06 may | SBW06 must not |
|---|---|---|
| Unsaved (`drafting` / `candidate_ready`) | Revise → edit → validate → later SBW07 first-save of selected definition | Imply mechanics already saved |
| `mechanics_saved` | Revise from exact accepted locator → new proposal → edit/validate | Offer SBW07 “Accept again”; append immutable child (SBW13) |

`SBW06d` product language (required):

```text
Revised proposal created from saved revision.
The saved revision is unchanged.
Appending this proposal as a new immutable revision is not available until SBW13.
```

### 12.15 Final allowlists and merge bars for SBW06a–d

| Bite | Success claim | In allowlist | Out |
|---|---|---|---|
| `SBW06a` | Exact typed `source_definition` + instructions under one stable `request_id`; recover/classify downstream result without mutating ThreatDraft or source candidate; journal + adapter + fixtures | generated Server types; revise journal; mapper; focused service tests; captured revise transcripts | UI; accepted locator; candidate-ref status mutation; ordinary success claiming lineage attached |
| `SBW06b` | One revise candidate becomes one durable ThreatDraft candidate ref with required embedded `CandidateLineageV1`; requested source-status transition validated and CAS-atomic | implement frozen §12.8 lineage-on-ref; draft CAS; capacity reservation; status table; store/route tests | UI; accepted-revision source; sibling lineage store |
| `SBW06c` | GM revises exact current working definition; new candidate; lineage + prior candidates inspectable; edits/instructions survive failure/reload | workbench + liveApi + tests | accepted-revision source; compare; append; graph |
| `SBW06d` | GM revises from exact SBW07 accepted locator; no latest fallback; accepted revision unchanged; SBW13 boundary copy shown | locator mapping + UI disclosure + tests | SBW07 second-save; SBW13 append; compare; binding |

Bounded discovery exception (implementation bites only): ≤3 additional paths under generated contract / adapter / one captured revise fixture directory, reported in the PR.

### 12.16 Review questions (must be answerable yes/no from this section)

| Question | Contract answer |
|---|---|
| Can one request identify one exact source without latest fallback? | **Yes** |
| Can a candidate-origin revise retain exact `source_candidate_id` plus required source-definition digest? | **Yes** |
| Is the source digest authority unambiguous (non-interchangeable digests)? | **Yes** |
| Does same-key replay use the exact original body? | **Yes** |
| Can changed-body replay mutate original authority? | **No** |
| After `candidate_id` is journaled, can every later local failure window recover with the same `request_id`? | **Yes** |
| Before `candidate_id` is known, can Buddy recover a Server-created revise candidate without closing §12.11? | **No** |
| Can cache/ref partial completion be represented without inventing `ref_attached_status_pending`? | **Yes** |
| Can a new revise `request_id` claim while another revise on the same draft is unresolved? | **No** |
| Can two revise `request_id`s both dispatch against the final open candidate-ref slot? | **No** |
| Does `revise_busy` mean “another unresolved revise occupies this draft’s active slot”? | **Yes** |
| Can candidate history fill (admission fail) before Server dispatch? | **Yes** |
| Can any status transition silently occur because a new candidate was generated? | **No** |
| Must new-ref append, required lineage, and requested source-status commit in one ThreatDraft CAS? | **Yes** |
| Can a source candidate or accepted revision be overwritten? | **No** |
| Is revise lineage stored on the ThreatDraft candidate ref (not a deferred sibling record)? | **Yes** |
| Can an accepted-source revise accidentally invoke SBW07 first-save again? | **No** |
| Can the UI ever select latest or display-name source? | **No** |
| Can the implementation fit within the named bites without absorbing SBW13? | **Yes** |
| Must `claimed → dispatched_unknown` be durably written before Server HTTP begins? | **Yes** |
| May recovery POST revise while journal status is still `claimed`? | **No** |
| Must `candidate_ref.request_id`, `lineage.revise_request_id`, journal `request_id`, and Server `request_id` be equal? | **Yes** |
| May a lineage object include fields from more than one source-origin variant? | **No** |
| Is the working-copy draft version field exactly `source_draft_version`? | **Yes** |

### 12.17 Metadata freeze for this contract PR

```text
SBW07: COMPLETE — #409 / 455daf49897bce0235972e7b9f07c3656a3fe27b
logical predecessor: #409 / 455daf49
current slice: SBW06-contract
next after approval: SBW06a (blocked on §12.11 gate evidence)
```

## §0 Capability decomposition decision

| Candidate outcome | Independently useful? | Durable contract? | Surface changed? | Decision |
|---|---:|---:|---:|---|
| Revise/regenerate from exact edited definition or accepted revision | Yes | Yes | Yes | Include |
| Preserve candidate lineage and superseded/rejected statuses | No; required for truthful revision | Yes | Yes | Include under same invariant |
| Save immutable mechanics | Already required | Yes | Yes | **Predecessor `SBW07` (must be merged first)** |
| Compare accepted revisions | Yes | No | Yes | Successor `SBW13` |
| Upgrade graph bindings/embeds | Yes | Yes | Yes | Successor `SBW14` |

**Selected capability:** the GM can ask for a revised candidate from one exact source while every prior proposal remains identifiable and inspectable.

## §1 Mission

A GM can produce a new typed candidate from an exact working definition or accepted revision so model-assisted iteration never silently overwrites earlier proposals or durable mechanics.

**Invariant**

```text
Every revise/regenerate operation creates a new candidate_id whose lineage names one exact source and explicit revision instructions; prior candidates and accepted revisions are never mutated.
```

**Mission falsification test**

```text
This is not one slice if implementation must also create/append a durable statblock revision, compare accepted revisions, change graph bindings, or manage images.
```

## §2 Context, authority, and boundaries

| Field | Required content |
|---|---|
| Parent authority | Integration design §6.4; tracker `SBW06`; DungeonMindServer revise-candidate contract |
| Repository rules | `AGENTS.md`; external-agent PR loop rules/template |
| Base revision | Actual merged SHA containing `SBW01–05` **and `SBW07`** |
| Predecessor contract | Exact candidate refs; complete typed editor working copy; validation digest/receipt state; **`SBW07` accepted-mechanics locators for `source_locator` revise** |
| Exact input consumed | Source kind + exact source locator/value + explicit revision instructions + request/idempotency key |
| Named successor | `SBW13` accepted revision append/compare (not `SBW07` — save precedes this slice) |
| What remains false | New candidate remains a proposal; no new mechanics identity or graph truth is changed |
| Explicit non-goals | First immutable save (already `SBW07`), append accepted revision, compare view, graph, embed, combat, media, silent latest selection |

Read in order:

1. integration design and tracker
2. merged `SBW05` editor/validation contracts
3. merged `SBW07` accepted-mechanics ref / locator contract
4. current DungeonMindServer revise-candidate generated API/types/fixtures
5. `SBW03` generation/cache/ref lifecycle
6. workbench candidate state tests

## §3 Observable-path inventory

| Path | Current | Required | Same invariant? | Owner |
|---|---|---|---:|---|
| Revise edited working copy | No model iteration | Submit complete typed definition + instructions | Yes | service/route/UI |
| Revise exact accepted revision | Not yet productized | Submit exact statblock/revision locator + instructions | Yes | service/route/UI |
| Preserve selected elements | Undefined | Pass Server `preserve_element_keys: bool` only (no preserve-sections list in current OpenAPI) | Yes | request mapper |
| Success | Potential replace-in-place UX | New candidate ref; prior source remains | Yes | orchestration/store/UI |
| Provider failure | Could lose working state | Typed error; source and instructions retained | Yes | service/UI |
| Stale source | Undefined | Reject before call or map Server conflict; no silent latest | Yes | service |
| Supersede/reject candidate | Not modeled fully | Explicit review-status transition; mechanics unchanged | Yes | draft candidate-ref store |
| Duplicate/replay | Undefined | Stable idempotency and candidate-ref dedupe | Yes | orchestration/store |
| Reload lineage | No product lineage view | Exact parent/source/status visible after reload | Yes | store/UI |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live_control_server/models/statblock_candidate_workflow.py` | Strict revise request/lineage/status types |
| Create/Modify | `apps/live_control_server/services/statblock_candidate_revision.py` | Exact source mapping and downstream orchestration |
| Modify | `apps/live_control_server/services/statblock_candidate_cache.py` | Store/read new candidate and lineage metadata |
| Modify | `apps/live_control_server/services/threat_draft_store.py` | Atomic candidate-ref status/lineage update |
| Modify | `apps/live_control_server/routes/statblock_candidates.py` | Revise and status-transition endpoints |
| Create | `tests/test_statblock_candidate_revision.py` | source/stale/replay/failure proof |
| Modify | `tests/test_statblock_candidate_routes.py` | route/status proof |
| Modify | `apps/live-control-ui/src/api/types.ts` | revise/status request/response types |
| Modify | `apps/live-control-ui/src/api/liveApi.ts` | revise/status calls |
| Modify | `apps/live-control-ui/src/api/liveApi.test.ts` | mapping proof |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx` | revision instructions, lineage, supersede/reject UX |
| Modify | `apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.test.tsx` | workflow and failure preservation proof |

### Bounded discovery exception

```text
Directory: merged SBW01 integration package and generated v1 contract fixtures
Maximum additional paths: 3
Allowed path kinds: adapter method, generated type export, one captured revise success/error fixture
Decision rule: required to consume the current Server revise contract exactly
Required report: identify exact source variants and idempotency/error vocabulary
```

## §5 Explicitly out of scope

| Capability | Why excluded |
|---|---|
| create first immutable statblock revision | Predecessor `SBW07` (already merged; this slice consumes locators only) |
| append accepted child revision | `SBW13` |
| accepted revision comparison | `SBW13` |
| preferred/binding/embed upgrade | `SBW14` |
| graph publication | `SBW08–09` |
| image generation or selection | `SBW16–17` |
| merge divergent revision branches | later design if dogfood requires it |
| automatic overwrite of active candidate | prohibited by invariant |

## §6 Implementation contract

```text
Input:
  source_kind = edited_definition | candidate | accepted_revision
  exact source payload/locator
  revision_instructions
  preserve_element_keys (bool only; current Server contract)
  draft_id + expected draft version/status token
  revise request_id

Output:
  new GeneratedStatblockCandidateV1
  lineage record naming exact source, request, instructions digest, and timestamps
  explicit review status updates for source candidate when requested

Invariant:
  new candidate identity; exact source remains unchanged and inspectable

Failure behavior:
  stale draft/status/source -> conflict before unsafe state change
  missing exact revision/candidate -> not found; no fallback to latest
  validation/provider/refusal/timeout -> typed failure; source/editor/instructions retained
  malformed result -> fail closed; no active candidate ref appended
  downstream success + local ref-write failure -> truthful partial completion retaining candidate locator for reconciliation

Replay / idempotency:
  same idempotency key + same exact source/instructions -> same result
  same key + changed source/instructions -> conflict
  new key -> new candidate proposal
  duplicate candidate response -> ref dedupe by candidate_id

Trust boundary:
  Verifies: exact source identity/digest, complete typed definition, instruction bounds, generated response shape
  Records without proving: whether revision improves balance or fulfills intent
  Rejects: display-name source selection, implicit latest, hidden corpus search, in-place candidate mutation
```

### Lineage decisions

- `source_kind=edited_working_copy` records `source_draft_version`, `editor_state_revision`, and required source-definition digest (§12.2 / §12.8); it does not persist the full working copy as a new authority beyond existing candidate cache needs. `source_kind=candidate` requires exact `source_candidate_id`, source request id, draft/ref version identity, and required source-definition digest. All revise request IDs are one bound identity (§12.8).
- `source_kind=accepted_revision` requires the full SBW07 six-field locator including `definition_digest` (§12.2 / §12.8).
- Source candidate status transitions follow §12.9; transitions are explicit and atomic. A new candidate does not automatically reject its source.
- Lineage is review metadata and must remain distinct from Server generation provenance while preserving both.
- Instructions are bounded user content; logs record digest/length, not full hidden prose.

### §6A State and fallback matrix

| Path | Loading | Success | Miss | Downstream unavailable | Integrity failure | Stale | Retry |
|---|---|---|---|---|---|---|---|
| Revise edited definition | retain working copy | new candidate/ref | N/A | typed failure; edits retained | fail closed | stale draft/status conflict | idempotent by key |
| Revise candidate | exact source read | new candidate/ref | 404 | typed failure | fail closed | expired/superseded policy explicit | new key for new proposal |
| Revise accepted revision | exact revision read | new candidate/ref | 404 | typed failure | digest mismatch fail | stale/missing exact source | safe |
| Status transition | current ref load | atomic transition | 404 | N/A | fail closed | invalid transition conflict | same transition idempotent |

No fallback to current/latest candidate or revision.

### §6B Identity matrix

| Situation | Rule | Ambiguity | Fallback? | Consequence |
|---|---|---|---|---|
| Source candidate | exact `candidate_id` | none | No | immutable source ref |
| Edited definition | deterministic digest + originating candidate/draft locator | mismatch = stale | No | lineage source |
| Accepted revision | exact statblock/revision IDs and digest | none | No | no latest |
| New candidate | exact returned candidate ID | collision with different payload = integrity failure | No | new ref |
| Instructions | digest over normalized bounded text/options | changed instructions distinct | No | replay key input |
| Display name | informational | duplicates irrelevant | No | never selection key |

### §6C Persistence and replay matrix

| Operation | Durable representation | Round-trip | Duplicate/replay | Compatibility | Recovery |
|---|---|---|---|---|---|
| Append lineage/ref | versioned draft candidate-ref metadata | source/new IDs/status preserved | dedupe new candidate ID | additive schema version | reconcile by candidate ID/request ID |
| Status transition | atomic ref update | exact status retained | same transition idempotent | invalid transitions rejected | reread current draft |
| Revision request replay | idempotency record/downstream contract | same source/instructions | same result; changed conflict | real Server semantics preserved | exact-read candidate |

### §6D Predecessor-to-consumer mapping

**Grounding source:** current generated revise-candidate request/response and error fixtures.

Required implementation mapping:

| Predecessor field/outcome | Consumer behavior | Rule | Proof |
|---|---|---|---|
| source definition or exact revision locator | mutually exclusive source variant | no implicit latest | fixture tests |
| revision instructions | bounded request field | exact copy/normalization declared | request snapshot |
| preserve element keys/options | explicit controls | pass only supported values | fixture |
| candidate ID/receipts | new candidate/ref | preserve exact IDs | route test |
| source/provenance | lineage disclosure | preserve Server + Buddy metadata separately | reload test |
| conflict/not found/refusal | typed UI state | stable mapping | error fixtures |

## §7 Verification ownership map

| Guarantee | Boundary | Command/scenario | Evidence |
|---|---|---|---|
| New candidate never overwrites source | service/store | focused tests | distinct IDs; source readable |
| Exact source/no latest fallback | service | stale/missing source tests | typed 404/409; zero alternate read |
| Working state retained on failure | UI/service | timeout/refusal tests | edits/instructions remain |
| Status transitions valid/idempotent | store/route | transition matrix tests | invalid conflict; same safe |
| Replay semantics | integration | duplicate/changed key tests | same result or conflict |
| Lineage reload | store/UI | reload test | exact source/instruction digest visible |
| Real Server contract | adapter/fixture | contract/fingerprint tests | no invented fields |

Required commands:

```bash
uv run pytest tests/test_statblock_candidate_revision.py tests/test_statblock_candidate_routes.py -q
cd apps/live-control-ui && npm test -- --run src/surface/modules/StatblockWorkbenchModule.test.tsx src/api/liveApi.test.ts
cd apps/live-control-ui && npm run build
git diff --check
git diff --name-only <base>...HEAD
```

### Minimal live proof

From the existing workbench, revise one edited attack with explicit instructions, show a new candidate ID and lineage, inspect the original candidate, then simulate timeout and prove the edited definition/instructions remain. Reject or supersede one candidate and reload.

## §8 Required handback

Include source-variant mapping, transition table, base/head, actual paths, commands/results/provenance, live candidate IDs/statuses, partial-completion handling, baseline failures/waivers, and confirmation that no mechanics save/graph/compare/upgrade/media ships.

## §9 Acceptance rubric

- [ ] Every revision creates a new candidate ID.
- [ ] Exact source and instruction digest are reloadable.
- [ ] No latest/display-name fallback exists.
- [ ] Prior candidates and accepted revisions remain unchanged.
- [ ] Failure retains editor/source/instructions.
- [ ] Status transitions are explicit, validated, and replay-safe.
- [ ] Downstream-success/local-failure state is recoverable and truthful.
- [ ] No immutable save, accepted compare, graph update, or media capability ships.

## §10 Reviewer protocol

Trace source identity and every state transition. Search for assignment replacing candidate bodies, `latest`, name matching, auto-reject, silent source switching, and save/append calls.

## §11 Re-review protocol

Re-run all source variants, transition matrix, replay, stale, timeout, and partial-completion tests after every fix.

## Stop conditions

Stop if:

- Server revise semantics cannot identify an exact source;
- the candidate cache/ref model cannot preserve lineage/status distinctly;
- an accepted revision source requires implicit latest;
- idempotency is undefined for revise operations;
- a new candidate cannot be recovered after downstream success/local write failure;
- a path outside the allowlist is required.

## Final dispatch check

- [x] Re-anchor after `SBW07` COMPLETE (`#409` / `455daf49`) and `SBW05`.
- [x] Inventory Server revise source variants from vendored OpenAPI (`source_definition` XOR `source_locator`).
- [ ] Capture real v1 revise success/error/replay fixtures (required in `SBW06a`; none in Buddy yet).
- [x] Confirm first-save is already true via `SBW07`; graph, compare, upgrade, and media remain false.
- [ ] `SBW06-contract` §12 approved before `SBW06a+` code.
- [ ] §12.11 Server revise recovery gate closed with evidence before merging `SBW06a`.
