---
pr_body_template: |
  ## Handoff pointer
  - Workstream: CUTOVER / D.2C2 provenance compatibility — DESIGN
  - Flow: CUTOVER
  - Direction: DESIGN → REVIEW
  - Handoff: `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-compatibility.md`
  - Implementation repository for this design: `Drakosfire/DungeonMindBuddy`
  - First CODE successor: `Drakosfire/DungeonMind` (provider interpretation + replay)
  - Second CODE successor: Buddy producer stamp + DungeonMind pin
  - Then resume parked Buddy #651 (D.2C3)

  ## Outcome
  Freeze a DungeonMind-owned interpretation of #645 reviewed-init-v1 genesis
  evidence so a legitimate first-world `D_0` is natively projectable/retrievable
  without Buddy rewriting graph bytes, without mutating immutable revisions,
  and without a global "trust the artifact" waiver.

  ## Locked rules
  - #645 remains `DONE`; this is a consumer-discovered provenance incompatibility
  - old `D_0` bytes and `command_sha256` stay immutable
  - exact retry of an existing initialization_id still returns already_initialized
  - Buddy never rewrites `graph_payload.evidence_refs` on read
  - DungeonMind owns compatibility interpretation
  - only the known reviewed-init-v1 empty-parent OTHER stamp is interpreted
  - WorldGraphProjectionService builds GenesisEvidenceCompatibility above graph_scope
  - replay is proved by hashing OTHER-normalized C_new against stored command_sha256
  - descendant eligibility is canonical record equality, not evidence_ref_id alone
  - DungeonMind ADR is 0023 if free at CODE dispatch; ADR-0022 is taken
  - genuine unrelated provenance mismatch still fails closed
  - future first-world commands stop stamping OTHER
  - #651 stays parked until CODE lands; D.2C4 remains false

  ## Required proof (CODE successors, not this design PR)
  - DungeonMind: #645-shaped D_0 OTHER evidence is admitted by native projection
  - DungeonMind: session_recap-vs-worldbuilding mismatch still rejects
  - DungeonMind: adopted Eldyrwild OTHER-or-mismatch behavior unchanged
  - DungeonMind: WorldGraphProjectionService admits #645-shaped D_0 and content-identical descendant evidence; graph_scope stays a pure consumer
  - DungeonMind: receipt whose D_0 is missing/cross-world/wrong-schema/hash-mismatched is PersistenceIntegrityError, not silent no-compatibility
  - DungeonMind: descendant reusing a genesis evidence ID with any changed record field still rejects
  - DungeonMind: hash(C_new) match is ordinary replay; else hash(OTHER-normalized C_new) == stored command_sha256 is correction replay
  - Buddy: new D_0 stores artifact domain on v1 EvidenceRef.source_domain, not OTHER
  - Buddy: old-world exact retry remains already_initialized / same command_sha256 on the stored receipt
  - then #651 Cycle 4 restores admitted projection/search/get-object
---

# HANDOFF — CUTOVER D.2C2: first-world provenance compatibility DESIGN

**Created:** 2026-08-26  
**Status:** ACTIVE — DESIGN DISPATCH / awaiting Review Cycle 2  
**Review Cycle 1:** REQUEST-CHANGES-equivalent `5036355801` on `27512f88639f6497646a2398bc3a197da29957ae`  
**Workstream / flow:** `CUTOVER`  
**Direction:** DESIGN → REVIEW  
**Design repository:** `Drakosfire/DungeonMindBuddy`  
**Exact design base / current Buddy `main`:** `555a9c7965aca47a24536277b9b36ae569a7285a` — PLAY-SURFACE cockpit re-anchor  
**D.2C2 implementation predecessor:** Buddy #645 merge `3ff46922e679ad6bef2ef0cf37f0bf87e4542a6c`; accepted head `f772db17e00cbe2c0198ae53f169a10a6332a3ed`; Cycle 2 PASS-equivalent `5026532158`  
**D.2C3 design predecessor:** Buddy #647 merge `d96a21363fd0decbcb8c4390f951a6316b53060c`; accepted design head `1f5676c204ee917d18efd553106c07306541e820`; Cycle 7 PASS-equivalent `5034239255`  
**D.2C3 implementation:** Buddy #651 PARKED ON PREDECESSOR at reviewed head `cf453078a5c1950ec5f23a5d5b99001ee9e456db`; Review Cycle 3 `5035980646`  
**DungeonMind pin (unchanged until CODE):** `bf40e933bdedf3cf08bb23a07a135958bdb7cc6b`  
**Design branch:** `cutover/design-first-world-provenance-compatibility`  
**Design PR title:** `CUTOVER: design first-world provenance compatibility`  
**First CODE successor:** DungeonMind `cutover/reviewed-init-v1-genesis-provenance` — `CUTOVER: interpret reviewed-init-v1 genesis OTHER evidence`  
**Second CODE successor:** Buddy `cutover/first-world-provenance-producer` — stamp artifact domain on new commands + pin DungeonMind  
**Then:** resume Buddy #651 as Review Cycle 4  
**Named later successor:** D.2C4 manual Graph Review authoring (still false)

> **Dispatch ruling:** #645 accomplished its stated initialization-authority
> migration. D.2C3 then consumed the resulting `D_0` through the full native
> read stack and exposed a provenance incompatibility that #645's acceptance
> tests did not cover. That is a new predecessor, not a failed #645, and not
> another patch inside #651.
>
> Choosing the repair is architecture. This PR freezes the choice. It does
> not implement DungeonMind `graph_scope` or `WorldGraphProjectionService`,
> does not change Buddy command bytes, and does not resume #651.
>
> Review Cycle 1 required four freezes now recorded below: the projection
> authority-context seam, hash-reconstructable replay, content-bound
> descendant eligibility, and ADR-0023 (ADR-0022 is already taken).

---

## 1. Mission and merge-ready invariant

A reviewed first-world `D_0` created under landed #645 semantics is a real
immutable DungeonMind revision whose native projection currently rejects its
own legitimate facts, because contribution evidence was stamped
`SourceDomain.OTHER` while the corresponding `SourceArtifact` carries the
real domain (typically `WORLDBUILDING`).

**Merge-ready invariant (this design PR):** **The repository records one
frozen DungeonMind-owned interpretation of reviewed-init-v1 genesis OTHER
evidence, one frozen Buddy producer rule that stops creating that stamp on
new worlds, and an explicit non-goal list that forbids Buddy read-side
rewrites, in-place `D_0` mutation, and a global artifact-trust waiver.**

CODE successors, not this PR, make the invariant true in software.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes, once split into DESIGN (this PR) then DungeonMind CODE then Buddy producer CODE then #651 resume. |
| Most likely adversarial sequence | A generic "if domain disagrees, trust the artifact" rule admits genuine corruption on adopted worlds or later children. |
| Will CODE §7 detect that? | Yes: adopted Eldyrwild mismatch fixtures and a non-OTHER mismatch on a reviewed-init world must still reject. |
| Easiest owning boundary to under-test | WorldGraphProjectionService constructing GenesisEvidenceCompatibility (vs a graph_scope helper only); initialization retry after the producer stamp changes: same `initialization_id`, new command hash, old receipt. |
| Fact that forces stop/split | Any need to mutate immutable `D_0` bytes, add a generic source-mutation API, have Buddy rewrite graph truth on read, or have `graph_scope` reach into repositories. |

---

## 2. Why #645 `D_0` is unprojectable

D.2C2 initialization itself works:

```text
Buddy reviewed first-world material
        ↓
DungeonMind reviewed initialization
        ↓
D_0.parent_revision_id is None
head = D_0
reviewed-init receipt exists
exact retry → already_initialized / same command_sha256
```

The defect is inside the resulting graph evidence.

### Producer (Buddy #645)

`DungeonMindWorldGraphInitializationAdapter._map_contribution` maps the
reviewed contribution through `_map_contributions(_EmptyEvidenceView(), …)`.
There is no parent Buddy graph, so evidence lookup is always empty.

`_map_contribution_evidence_ref` then takes the missing-evidence fallback
and **hardcodes** `source_domain=SourceDomain.OTHER` onto a v1 `EvidenceRef`
whose `source_artifact_id` is the assertion's real artifact.

The same command's `source_artifacts` are built by `_store_artifact_v2`,
which maps Buddy `"worldbuilding"` to `SourceDomain.WORLDBUILDING` and
`source_domain_key="worldbuilding"`.

### Materialization (DungeonMind #46)

`_lift_evidence` copies that v1 OTHER stamp into v2 graph evidence:

```text
source_domain_key = "other"
source_domain     = OTHER
```

`D_0` is immutable. The receipt stores `command_sha256` over the entire
`ReviewedWorldInitializationCommandV1`, including those OTHER refs.

### Native read (DungeonMind `graph_scope` today)

`_resolve_v2_evidence_provenance` requires:

```text
artifact.source_domain_key == record.source_domain_key
artifact.source_domain     == record.source_domain
```

Disagreement is `ProvenanceRejection("evidence_source_domain_mismatch")`.
The assertion is excluded from scoped projection. This is intentional
fail-closed authority, not a bug in the checker.

### Observable split (Buddy #651 witness)

```text
WorldGraphAuthority.read_revision(D_0)
    → raw objects include obj_session22_vial

native projection(D_0)
    → does not admit obj_session22_vial / mystery_puddles
```

Descendant `D_1` that copies the same genesis evidence records fails
the same way. A descendant that keeps the id but changes any other
record field is a different, still-invalid chain.

#651's binder, raw read, publish, and retry work. Its merge contract
requires admitted projection/search/exact-object retrieval. That is why
#651 is parked rather than merged with a weakened rubric.

After CODE, native projection goes through `WorldGraphProjectionService`
(§4.0). `graph_scope` remains the policy consumer; it does not discover
the receipt itself.

---

## 3. Rejected repairs (do not revive)

### R1. Change the #645 command builder and ignore old receipts

Changing `_map_contribution_evidence_ref` so new commands stamp the
artifact domain is necessary for **future** worlds. It is not sufficient
for already-created worlds:

- `D_0` bytes are immutable.
- Exact retry rebuilds the full command (`initialize()` always calls
  `_build_command`, then `initialize_reviewed_world`).
- DungeonMind compares `initialization_id + command_sha256`.
- A different hash on the same id is `IdempotencyConflictError`, not
  `already_initialized`.

Buddy #651 Cycle 1 tried this as the sole fix and was correctly rejected.

### R2. Buddy rewrites evidence in memory before projection

`_SourceAlignedWorldGraphRepository` changed `evidence_refs.source_domain`
on the payload handed to DungeonMind while still reporting the original
`revision_id`. That:

- reconstructs graph truth on a pure-consumer path;
- broadens admissibility;
- would mask genuine provenance corruption on adopted worlds, descendants,
  and historical pins.

Buddy #651 Cycle 2 was correctly rejected. Do not reinstall any read-side
evidence rewrite.

### R3. Global "if domain disagrees, trust the artifact"

This disables the integrity check everywhere. Forbidden.

### R4. In-place mutation of published `D_0`

DungeonMind has no public API that rewrites a published graph revision.
Adoption V3→V4 (ADR-0021) repairs **source classification and receipt**,
explicitly not graph revisions or `evidence_refs`. A new graph truth
requires a descendant publish. A descendant that leaves `D_0` itself
unprojectable does not satisfy D.2C3 (`D_0` must be natively readable).

### R5. Buddy-only dual mapper (receipt exists → OTHER, else artifact domain)

That would keep old retries hashing to the stored command without a
DungeonMind replay rule, but it permanently encodes the defect in Buddy
and still leaves stored `D_0` unprojectable until something interprets
OTHER. Insufficient as the sole repair.

---

## 4. Frozen choice

**DungeonMind owns the historical interpretation. Buddy stops producing
the defect. Neither rewrites immutable graph bytes.**

```text
1. Projection compatibility (DungeonMind WorldGraphProjectionService)
   The service builds a verified GenesisEvidenceCompatibility value
   above graph_scope. graph_scope remains a pure policy consumer.

2. Replay compatibility (DungeonMind initialize_reviewed_world)
   Correction replay is proved by hashing a legacy-normalized copy of
   the new command against the stored receipt.command_sha256.
   The receipt does not store the old command.

3. Future producer (Buddy _map_contribution_evidence_ref fallback)
   Stamp v1 EvidenceRef.source_domain from the mapped SourceArtifact,
   not OTHER. Command refs have no source_domain_key; "other" appears
   later when DungeonMind lifts evidence into graph v2.

4. Buddy reads remain pure consumers of the exact stored revision.
```

This is the reviewed-init analogue of ADR-0021: a **named, closed
historical meaning**, not a generic mutation API. DungeonMind
**ADR-0022** is already taken
(`Docs/Decisions/ADR-0022-independent-library-and-agent-harness-boundary.md`
on pin / `main` `bf40e933…`). The CODE PR writes **ADR-0023** if that
number is still free at dispatch; otherwise the next free ADR, recorded
in the CODE handoff. Do not overwrite or reuse ADR-0022.

### 4.0 Projection authority-context seam

Current `WorldGraphProjectionService` is constructed from
`WorldGraphRepository + SourceRepository + GraphSnapshotReader` and
calls `project_scoped_snapshot(parsed, sources=source_snapshot, ...)`.
`graph_scope` receives a parsed graph plus source lookup/scope inputs.
It cannot independently know the reviewed-init receipt or the
authoritative `D_0` evidence set.

CODE must not invent a repository read inside `graph_scope`, a global
callback, a Buddy-provided hint, or an ad-hoc service-contract fork.

**Frozen DungeonMind-owned seam:**

```text
WorldGraphProjectionService
  + ReviewedWorldInitializationRepository   (required constructor dep)
  + existing WorldGraphRepository
        ↓
resolve reviewed-init compatibility context for request.world_id
        ↓
R = reviewed_world_initializations.get_for_world(world_id)
if R is None:
    genesis_compatibility = None          # adopted / uninitialized
else:
    D_0 = R.published_revision_id
    load exact immutable D_0 via WorldGraphRepository
    verify world/revision identity
    verify D_0 graph schema + payload sha against R
      (R.published_graph_schema, R.published_graph_payload_sha256)
    parse D_0 with the same GraphSnapshotReader
        ↓
    GenesisEvidenceCompatibility (pure immutable value)
        ↓
project_scoped_snapshot(..., genesis_compatibility=context)
```

`ReviewedWorldInitializationRepository` is a **required** constructor
argument. Absence of a receipt is `get_for_world → None`, not absence of
the repository. Tests inject a stub that returns `None`.

`GenesisEvidenceCompatibility` is a frozen application value. Suggested
shape (CODE may name fields equivalently):

```text
world_id: str
d0_revision_id: str
eligible_records: mapping evidence_ref_id → exact parsed D_0 GraphEvidenceRecordV2
```

Only `D_0` records with `source_domain == OTHER` and
`source_domain_key == "other"` (the exact #645 `_lift_evidence` of a v1
`EvidenceRef` whose `source_domain` was OTHER) enter the mapping.
The value binds the **entire canonical record**, not the id alone.

`graph_scope.project_scoped_snapshot` / `_resolve_v2_evidence_provenance`
remain pure consumers of that optional value. They must not reach into
PostgreSQL or repositories. They must not mutate the parsed snapshot.
Buddy must not pass a hint that substitutes for the receipt.

`WorldGraphRetrievalService` continues to go through
`WorldGraphProjectionService.open_read_context`; search / get-object
inherit the seam automatically.

**Failure semantics (frozen):**

| Observation | Outcome |
|---|---|
| no reviewed-init receipt | `genesis_compatibility=None`; ordinary projection |
| recognized receipt, `D_0` missing / cross-world / wrong schema / payload sha disagrees with `R.published_graph_payload_sha256` | `PersistenceIntegrityError` (provider integrity). Not "no compatibility". Not an ordinary provenance rejection. |
| Buddy omits or fabricates a compatibility hint | forbidden; not a CODE option |

Owning proof must exercise both `D_0` and a descendant through the
normal `WorldGraphProjectionService`, not a direct `graph_scope` helper
only.

Buddy producer+pin CODE, when consuming the DungeonMind pin, wires
`bundle.reviewed_world_initializations` into the existing
`WorldGraphProjectionService(...)` construction in
`direct_services_from_bundle`. That is constructor consumption of the
provider contract, not a Buddy authority hint.

### 4.1 Projection rule (must all hold)

Call the stored receipt `R = ReviewedWorldInitializationReceiptV1` for world `W`.
Call `D_0 = R.published_revision_id`.
Call `C = GenesisEvidenceCompatibility` built by §4.0 for `W`.

An evidence record `E` on a parsed revision of `W` is **genesis-OTHER
compatible** iff:

1. `C` is present for this world (`C.world_id == W`, `C.d0_revision_id == D_0`).
2. `E_0 = C.eligible_records[E.evidence_ref_id]` exists.
3. `canonical(E) == canonical(E_0)` — complete immutable fingerprint of
   every `GraphEvidenceRecordV2` / `EvidenceRefV2` field (id, artifact,
   revision, domain, domain_key, role, open/highlight flags, session id,
   span/locator/uri/line_ref, schema_version, and any other record
   field). ID match alone is not sufficient.
4. The live `SourceArtifactV2` for `E.source_artifact_id` exists, is in
   scope, and has `source_domain != OTHER` and
   `source_domain_key != "other"`.

Then, **for provenance domain comparison only**, compare the artifact's
domain/key to itself (the OTHER stamp is the known placeholder). Do not
rewrite `E` or the parsed snapshot. All other provenance checks
(visibility, schema, revision ownership, campaign scope) remain
unchanged.

New evidence ids on `D_1+` are not grandfathered, even if they also say
OTHER. Same id with any changed record field is not grandfathered.

CODE may implement `canonical(E)` as total Pydantic/model equality or as
`canonical_sha256` of the record's canonical dump. Either must be total
over the record.

### 4.2 What still fails closed

| Case | Outcome |
|---|---|
| `session_recap` vs artifact `worldbuilding` | reject (`evidence_source_domain_mismatch`) |
| OTHER on an evidence id **not** on eligible `D_0` records | reject |
| same genesis id, any changed record field on a descendant | reject; compatibility does not apply |
| OTHER whose artifact is also OTHER / key `other` | unchanged existing behavior (not this compatibility) |
| mismatch on an adopted world (no reviewed-init receipt) | reject; Eldyrwild unchanged |
| missing artifact, inactive source, revision owner mismatch | existing rejections |
| both genesis receipts | existing integrity; out of this slice |
| recognized receipt with broken `D_0` identity/hash | `PersistenceIntegrityError` |

### 4.3 Replay rule

`ReviewedWorldInitializationReceiptV1` stores `command_sha256`, not the
original command. `ReviewedWorldInitializationRepository` exposes
`get` / `get_for_world` / `initialize` — not historical-command
retrieval. Piecemeal field comparison against "stored command digest
inputs" is not an executable contract.

`initialize_reviewed_world` / `replay_conflict_if_present` today:

```text
same world + same initialization_id + same command_sha256 → reload receipt
same world + same initialization_id + different hash     → IdempotencyConflictError
```

Frozen correction-replay proof — **canonical legacy normalization of
the newly rebuilt command**:

```text
new corrected command C_new
stored receipt R for same world + initialization_id

if hash(C_new) == R.command_sha256:
    ordinary exact replay
else:
    build C_legacy_candidate from C_new by changing ONLY eligible
    reviewed-init evidence_ref.source_domain values
    artifact-domain → SourceDomain.OTHER

    # GraphContributionV2 / GraphContributionAssertionV2 evidence refs
    # are v1 EvidenceRef. source_domain_key is NOT a command field.
    # "other" is introduced later by _lift_evidence as
    # ref.source_domain.value.

    require hash(C_legacy_candidate) == R.command_sha256
    otherwise IdempotencyConflictError

    return stored receipt unchanged
```

`hash` is the existing `reviewed_world_initialization_command_sha256`
(`canonical_sha256` of the command JSON dump). Equality after
normalization is the proof that every other semantic command field —
plan, actor, timestamp, profile, source artifacts/revisions,
contribution/assertions, IDs, etc. — is byte-for-byte equivalent to the
historical command after exactly the known producer correction. Do not
implement piecemeal field comparison. Do not update `R.command_sha256`.

**Eligibility for reverse-normalization** is command-owned source
identity, not `D_0` graph evidence:

1. Build the command `SourceArtifactV2` map by `source_artifact_id`.
   Duplicate ids with disagreeing artifacts are ambiguous → fail closed
   (`IdempotencyConflictError`); do not guess.
2. For each v1 `EvidenceRef` on
   `C_new.reviewed_contribution.assertions[*].evidence_refs`:
   - already `source_domain == OTHER`: leave unchanged;
   - else the ref is eligible iff it resolves to exactly one command
     artifact, that artifact's `source_domain` is not `OTHER`, and
     `ref.source_domain == artifact.source_domain`;
   - eligible refs: copy the command and set **only**
     `source_domain = SourceDomain.OTHER`;
   - missing or ambiguous source closure: fail closed; do not
     normalize.

Any other delta remains `IdempotencyConflictError`. The historical
command remains the hashed authority.

### 4.4 Buddy producer rule (after DungeonMind CODE)

In `_map_contribution_evidence_ref`, when the parent evidence view misses
and `fallback_source_artifact_id` is set, stamp:

```text
source_domain = mapped SourceArtifact.source_domain
```

not `SourceDomain.OTHER`.

Command evidence is v1 `EvidenceRef`. It has `source_domain` and **does
not** have `source_domain_key`. Do not invent a key on the command.
DungeonMind `_lift_evidence` later sets
`source_domain_key = ref.source_domain.value`. After this producer
change that key is the real domain string (`"worldbuilding"`, …), not
`"other"`.

Pass the command's artifact map into that fallback. Do not guess a
domain from the Buddy string if the command artifact is missing; that
remains inexpressible.

New worlds: stored `D_0` evidence matches the artifact; projection
compatibility is a no-op.

Old worlds: stored `D_0` stays OTHER; projection compatibility admits
those genesis records when content-identical; retry sends corrected
`source_domain` values; replay compatibility returns
`already_initialized` because
`hash(OTHER-normalized C_new) == R.command_sha256`.

### 4.5 Explicitly not chosen

- Buddy in-memory graph rewrite
- mutating `D_0`
- publishing a corrective `D_1` as the only way to read first-world facts
- widening `graph_scope` to trust artifacts on arbitrary mismatch
- repository reads, callbacks, or Buddy hints inside `graph_scope`
- inheriting compatibility by `evidence_ref_id` without canonical record equality
- recovering or storing the historical command beside `command_sha256`
- piecemeal command-field comparison for replay
- overwriting or reusing ADR-0022
- changing adoption / V4 repair
- D.2C4 authoring or D.3 demolition

---

## 5. Sequence after this design merges

```text
this DESIGN PR
        ↓
DungeonMind CODE   interpret genesis OTHER + correction replay
        ↓
Buddy CODE         stamp artifact domain on new commands + pin DM
        ↓
resume #651        restore admitted projection/search/get-object
                   re-anchor; Review Cycle 4
        ↓
merge D.2C3
        ↓
D.2C4 Graph Review authoring
```

#651 remains `DOING` / PARKED. Do not weaken its §7/§9. Do not merge it
from the current fail-closed witness.

---

## 6. CODE successor contracts

### 6.1 DungeonMind (first)

| Field | Content |
|---|---|
| Base | current DungeonMind `main` / pin `bf40e933…` at dispatch, re-anchored |
| Suggested branch | `cutover/reviewed-init-v1-genesis-provenance` |
| Suggested title | `CUTOVER: interpret reviewed-init-v1 genesis OTHER evidence` |
| ADR | **ADR-0023** if still free at CODE dispatch (ADR-0022 is taken). If 0023 is taken by then, next free ADR; record the exact number in the CODE handoff. Named closed historical meaning. Do not reuse ADR-0022. |
| Primary paths | `src/dungeonmind/application/world_graph_projection.py` (authority-context seam); `src/dungeonmind/application/graph_scope.py` (pure consumer of `GenesisEvidenceCompatibility`); `src/dungeonmind/application/reviewed_world_initialization.py` (`replay_conflict_if_present` / command hash); ADR-0023; unit + PG tests through `WorldGraphProjectionService` |
| Non-goals | no Buddy product code; no graph revision mutation; no generic source update API; no repository I/O inside `graph_scope`; no Buddy hint |

Owning proofs:

- fixture: reviewed-init `D_0` with OTHER evidence + WORLDBUILDING artifact → **`WorldGraphProjectionService.project`** admits the object
- same fixture: `read` of raw revision still shows OTHER bytes (no snapshot rewrite)
- descendant carrying a **canonically identical** genesis evidence record admits; a new OTHER id on the child rejects
- adversarial: descendant reuses the genesis evidence ID with any changed record field (artifact, revision, role, locator, domain/key, flags, session, uri, …) → compatibility does not apply; ordinary provenance rejection remains
- recognized receipt whose `D_0` is missing, cross-world, wrong-schema, or payload-hash mismatched → `PersistenceIntegrityError`
- `session_recap` vs `worldbuilding` still rejects
- adopted-world provenance tests unchanged
- stored receipt + `C_new` whose hash already equals `R.command_sha256` → ordinary exact replay
- stored receipt + `C_new` whose only change is eligible v1 `EvidenceRef.source_domain` artifact-domain→OTHER-normalized hash match → correction replay; stored `command_sha256` unchanged
- same id + any other command change (including ineligible/ambiguous source closure) → `IdempotencyConflictError`

### 6.2 Buddy producer (second)

| Field | Content |
|---|---|
| Depends on | DungeonMind CODE merged and pinned |
| Suggested branch | `cutover/first-world-provenance-producer` |
| Suggested title | `CUTOVER: stamp first-world evidence from source artifacts` |
| Primary paths | `world_graph_initialization_adapter.py` / `_map_contribution_evidence_ref` fallback; `direct_services_from_bundle` constructor wiring of `ReviewedWorldInitializationRepository`; first-world PG tests; pin `pyproject.toml` / `uv.lock` |
| Non-goals | no read-side rewrite; do not resume #651 inside this PR; do not invent `source_domain_key` on v1 `EvidenceRef` |

Owning proofs:

- new first-world confirm: stored `D_0` evidence domains equal the artifact domain, not `{other}`
- new `D_0` native projection admits first-world facts without depending on the compatibility branch
- existing #645-shaped world (OTHER stored): exact retry `already_initialized`, receipt `command_sha256` unchanged (`hash(OTHER-normalized C_new)` matches)
- `WorldGraphProjectionService` construction passes `bundle.reviewed_world_initializations` (pin compile/wiring, not a Buddy hint)
- Eldyrwild adoption / D.2A / D.2B regressions green

### 6.3 Resume #651 (third)

Re-anchor onto then-current `main`. Restore the original PostgreSQL
witness:

- `obj_session22_vial` and `mystery_puddles` **in** native projection
- search + exact-object retrieval of `obj_session22_vial`
- child projection still admits genesis facts
- zero required skips

That distinct head is **Review Cycle 4**. Frozen #651 §7/§9 stay the
acceptance rubric.

---

## 7. Observable paths (DESIGN claims only)

| Path | Current | Required after CODE | Owner |
|---|---|---|---|
| #645 `D_0` native projection | OTHER mismatch excludes facts | admit genesis facts; bytes stay OTHER | DungeonMind `WorldGraphProjectionService` builds context; `graph_scope` consumes it |
| #645 `D_0` search / get-object | miss | hit | same seam via `WorldGraphRetrievalService` + Buddy consumer after pin |
| Raw `read_revision(D_0)` | sees objects | unchanged | already true |
| Exact retry of #645 world after producer stamp | digest conflict | `already_initialized`, stored hash unchanged (`hash(OTHER-normalized C_new)`) | DungeonMind `replay_conflict_if_present` |
| New first-world `D_0` | would stamp OTHER | stamps artifact `source_domain` on v1 `EvidenceRef` | Buddy producer |
| Adopted Eldyrwild mismatch | reject | reject | DungeonMind, no change |
| Descendant same id, changed record field | n/a (unprojectable today) | reject; no ID-only waiver | DungeonMind `graph_scope` consumer |
| Broken reviewed-init `D_0` identity/hash | n/a | `PersistenceIntegrityError` | DungeonMind `WorldGraphProjectionService` |
| Buddy native read adapter | must not rewrite evidence | still must not | #651 park + this design |

---

## 8. Files in scope — this design PR write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-CUTOVER-first-world-provenance-compatibility.md` | Frozen design |
| Modify | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` | Sequence: this DESIGN `DOING`; #651 parked; #645/#647 truthful `DONE` |
| Modify | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` | Same |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | Mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | Mirror |
| Modify | `Docs/Design/STATUS-world-graph-continuity-spine.md` | Active slice |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-cutover.md` | Remaining debt |
| Modify | `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` | Status/sequence metadata only; do not rewrite frozen D.2C3/D.2C4/D.3 semantics |

No production Python, no DungeonMind repository, no #651 resume, no pin change.

Parallel lanes: Buddy #651 parked (binder lease frozen; state docs transfer here for this predecessor). Open PLAY-SURFACE #652 does not overlap. Do not edit #651 branch.

---

## 9. State-authority sync (backward-looking)

Truthful as of this design dispatch:

- D.2C2 mounted first-world / #645 is `DONE` (merge `3ff46922…`).
- D.2C3 design / #647 is `DONE` (merge `d96a2136…`).
- D.2C2 provenance compatibility DESIGN is `DOING` / this PR (Review Cycle 1 `5036355801` REQUEST-CHANGES-equivalent on `27512f88…`; this head is Review Cycle 2). Do not invent its merge SHA.
- DungeonMind provenance CODE is `BLOCKED` on this design merge.
- Buddy producer CODE is `BLOCKED` on DungeonMind CODE merge.
- D.2C3 implementation / #651 is `DOING` / PARKED ON PREDECESSOR until those CODE slices land.
- D.2C4 / D.3A / D.3B remain `BLOCKED`. D.3 is not `DONE`.
- Current Buddy `main` is `555a9c7965aca47a24536277b9b36ae569a7285a`.
- DungeonMind pin remains `bf40e933…` until the DungeonMind CODE successor.

`main`'s tracker still claimed #645 `DOING` at this re-anchor. That is stale.
This PR records completed predecessors; it does not pre-mark this design or
any CODE successor `DONE`.

---

## 10. Acceptance rubric (this design PR)

- [ ] One frozen interpretation: reviewed-init-v1 genesis OTHER, not global artifact-trust.
- [ ] Projection compatibility context is built by `WorldGraphProjectionService` from `ReviewedWorldInitializationRepository` + exact `D_0`; `graph_scope` is a pure consumer.
- [ ] Broken reviewed-init `D_0` identity/schema/payload-hash is provider integrity, not silent no-compatibility.
- [ ] Replay is hash-reconstructable: `hash(C_new)` or `hash(OTHER-normalized C_new)` vs stored `command_sha256`; command evidence is v1 `EvidenceRef` (`source_domain` only).
- [ ] Descendant eligibility requires canonical record equality, not `evidence_ref_id` alone.
- [ ] ADR is **ADR-0023** if free at CODE dispatch; ADR-0022 is occupied and must not be reused.
- [ ] DungeonMind owns projection + replay compatibility; Buddy owns future producer stamp.
- [ ] Immutable `D_0` / stored `command_sha256` / exact already_initialized retry are preserved in the contract.
- [ ] Buddy read-side rewrite and in-place graph mutation are explicit non-goals.
- [ ] CODE sequence is parseable: DungeonMind → Buddy producer+pin → #651 Cycle 4.
- [ ] #645 remains `DONE`; #651 remains parked with unweakened §7/§9.
- [ ] Changed paths stay inside §8.
- [ ] State authorities agree with current `main` SHA and predecessor merge facts.

## Stop conditions

Stop and re-brief instead of implementing inside this design PR when:

- DungeonMind would need a generic `SourceRepository.update` or graph-revision rewrite;
- compatibility cannot be recognized from reviewed-init receipt + verified `D_0` + canonical record equality;
- replay cannot be proved from `command_sha256` plus reverse-normalization of eligible v1 `source_domain` fields;
- `graph_scope` would have to perform repository I/O or accept a Buddy hint;
- adopted-world provenance would have to change;
- ADR-0023 (or next free) cannot be allocated without overwriting ADR-0022;
- #651 or PLAY-SURFACE acquires these design paths concurrently.

```text
Stop condition:
Invariant clause affected:
Why current mission cannot absorb it:
Required evidence now missing:
Affected paths/ownership layers:
Proposed successor or re-brief:
State-authority update needed:
```
