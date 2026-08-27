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
  - genuine unrelated provenance mismatch still fails closed
  - future first-world commands stop stamping OTHER
  - #651 stays parked until CODE lands; D.2C4 remains false

  ## Required proof (CODE successors, not this design PR)
  - DungeonMind: #645-shaped D_0 OTHER evidence is admitted by native projection
  - DungeonMind: session_recap-vs-worldbuilding mismatch still rejects
  - DungeonMind: adopted Eldyrwild OTHER-or-mismatch behavior unchanged
  - DungeonMind: old receipt + rebuilt command whose only delta is genesis OTHER→artifact domain is exact replay
  - Buddy: new D_0 stores artifact domain, not OTHER
  - Buddy: old-world exact retry remains already_initialized / same command_sha256 on the stored receipt
  - then #651 Cycle 4 restores admitted projection/search/get-object
---

# HANDOFF — CUTOVER D.2C2: first-world provenance compatibility DESIGN

**Created:** 2026-08-26  
**Status:** ACTIVE — DESIGN DISPATCH / awaiting Review Cycle 1  
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
> not implement DungeonMind `graph_scope`, does not change Buddy command
> bytes, and does not resume #651.

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
| Easiest owning boundary to under-test | Initialization retry after the producer stamp changes: same `initialization_id`, new command hash, old receipt. |
| Fact that forces stop/split | Any need to mutate immutable `D_0` bytes, add a generic source-mutation API, or have Buddy rewrite graph truth on read. |

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

### Native read (DungeonMind `graph_scope`)

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

Descendant `D_1` copies the same genesis `evidence_ref_id`s, so child
projection fails the same way.

#651's binder, raw read, publish, and retry work. Its merge contract
requires admitted projection/search/exact-object retrieval. That is why
#651 is parked rather than merged with a weakened rubric.

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
1. Projection compatibility (DungeonMind graph_scope)
   A reviewed-init-v1 genesis OTHER evidence record is valid provenance
   when it is exactly the known empty-parent fallback.

2. Replay compatibility (DungeonMind initialize_reviewed_world)
   If a stored receipt exists and the rebuilt command differs only by
   replacing those genesis OTHER stamps with the SourceArtifact domains,
   treat it as exact replay (return the stored receipt).

3. Future producer (Buddy _map_contribution_evidence_ref fallback)
   Stamp the mapped SourceArtifact domain / domain_key, not OTHER.
   New D_0s are native-clean. Old D_0s stay OTHER forever.

4. Buddy reads remain pure consumers of the exact stored revision.
```

This is the reviewed-init analogue of ADR-0021: a **named, closed
historical meaning**, not a generic mutation API. Suggested DungeonMind
ADR number: **ADR-0022** (next free after ADR-0021). The CODE PR writes
the ADR; this design freezes the decision.

### 4.1 Projection rule (must all hold)

Call the stored receipt `R = ReviewedWorldInitializationReceiptV1` for world `W`.
Call `D_0 = R.published_revision_id`.

An evidence record `E` on a parsed revision of `W` is **genesis-OTHER
compatible** iff:

1. `W` has a reviewed-init receipt and that receipt's published revision is `D_0`.
2. `E.evidence_ref_id` is present on `D_0`'s stored `graph_payload.evidence_refs`.
3. On `D_0`, that record has `source_domain == OTHER` and
   `source_domain_key == "other"` (the exact #645 lift).
4. `E.source_artifact_id` equals the `D_0` record's artifact id.
5. The live `SourceArtifactV2` for that id exists, is in scope, and has
   `source_domain != OTHER` and `source_domain_key != "other"`.

Then, **for provenance domain comparison only**, compare the artifact's
domain/key to itself (the OTHER stamp is the known placeholder). All other
provenance checks (visibility, schema, revision ownership, campaign scope)
remain unchanged.

Apply the same `evidence_ref_id` set on descendants. New evidence ids on
`D_1+` are not grandfathered, even if they also say OTHER.

### 4.2 What still fails closed

| Case | Outcome |
|---|---|
| `session_recap` vs artifact `worldbuilding` | reject (`evidence_source_domain_mismatch`) |
| OTHER on an evidence id **not** on `D_0` | reject |
| OTHER whose artifact is also OTHER / key `other` | unchanged existing behavior (not this compatibility) |
| mismatch on an adopted world (no reviewed-init receipt) | reject; Eldyrwild unchanged |
| missing artifact, inactive source, revision owner mismatch | existing rejections |
| both genesis receipts | existing integrity; out of this slice |

### 4.3 Replay rule

`initialize_reviewed_world` today:

```text
same world + same initialization_id + same command_sha256 → reload receipt
same world + same initialization_id + different hash     → IdempotencyConflictError
```

Add one closed exception, computed from the **stored** `D_0` evidence and
the **command's** `source_artifacts` / contribution evidence_refs:

The new command is a **genesis-OTHER correction replay** iff the only
semantic delta versus the stored command digest inputs is replacing
genesis-OTHER compatible evidence domains/keys with the corresponding
`SourceArtifact` domain/key. Then return the stored receipt (same
`published_revision_id`, same stored `command_sha256`).

Any other delta (plan hash, contribution assertions, actor, extra
artifacts, non-genesis evidence, different initialization_id) remains
`IdempotencyConflictError`. Do not update the stored `command_sha256`.
The historical command remains the hashed authority.

### 4.4 Buddy producer rule (after DungeonMind CODE)

In `_map_contribution_evidence_ref`, when the parent evidence view misses
and `fallback_source_artifact_id` is set, stamp:

```text
source_domain     = mapped SourceArtifact.source_domain
source_domain_key = mapped SourceArtifact.source_domain_key  # via lift
```

not `SourceDomain.OTHER`.

Pass the command's artifact map into that fallback. Do not guess a domain
from the Buddy string if the command artifact is missing; that remains
inexpressible.

New worlds: stored `D_0` evidence matches the artifact; projection
compatibility is a no-op.

Old worlds: stored `D_0` stays OTHER; projection compatibility admits
those genesis ids; retry sends corrected domains; replay compatibility
returns `already_initialized`.

### 4.5 Explicitly not chosen

- Buddy in-memory graph rewrite
- mutating `D_0`
- publishing a corrective `D_1` as the only way to read first-world facts
- widening `graph_scope` to trust artifacts on arbitrary mismatch
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
| ADR | ADR-0022 (or next free), named closed historical meaning |
| Primary paths | `src/dungeonmind/application/graph_scope.py`; `src/dungeonmind/application/reviewed_world_initialization.py`; unit + PG tests |
| Non-goals | no Buddy product code; no graph revision mutation; no generic source update API |

Owning proofs:

- fixture: reviewed-init `D_0` with OTHER evidence + WORLDBUILDING artifact → projection admits the object
- same fixture: `read` of raw revision still shows OTHER bytes
- descendant carrying the same `evidence_ref_id` admits; a new OTHER id on the child rejects
- `session_recap` vs `worldbuilding` still rejects
- adopted-world provenance tests unchanged
- stored receipt + command whose only change is genesis OTHER→artifact domain → exact replay, stored `command_sha256` unchanged
- same id + any other command change → `IdempotencyConflictError`

### 6.2 Buddy producer (second)

| Field | Content |
|---|---|
| Depends on | DungeonMind CODE merged and pinned |
| Suggested branch | `cutover/first-world-provenance-producer` |
| Suggested title | `CUTOVER: stamp first-world evidence from source artifacts` |
| Primary paths | `world_graph_initialization_adapter.py` / `_map_contribution_evidence_ref` fallback; first-world PG tests; pin `pyproject.toml` / `uv.lock` |
| Non-goals | no read-side rewrite; do not resume #651 inside this PR |

Owning proofs:

- new first-world confirm: stored `D_0` evidence domains equal the artifact domain, not `{other}`
- new `D_0` native projection admits first-world facts without depending on the compatibility branch
- existing #645-shaped world (OTHER stored): exact retry `already_initialized`, receipt `command_sha256` unchanged
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
| #645 `D_0` native projection | OTHER mismatch excludes facts | admit genesis facts; bytes stay OTHER | DungeonMind `graph_scope` |
| #645 `D_0` search / get-object | miss | hit | DungeonMind projection + Buddy consumer after pin |
| Raw `read_revision(D_0)` | sees objects | unchanged | already true |
| Exact retry of #645 world after producer stamp | digest conflict | `already_initialized`, stored hash unchanged | DungeonMind replay |
| New first-world `D_0` | would stamp OTHER | stamps artifact domain | Buddy producer |
| Adopted Eldyrwild mismatch | reject | reject | DungeonMind, no change |
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
- D.2C2 provenance compatibility DESIGN is `DOING` / this PR. Do not invent its merge SHA.
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
- compatibility cannot be recognized from reviewed-init receipt + `D_0` OTHER evidence ids;
- adopted-world provenance would have to change;
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
