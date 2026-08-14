---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — Captain and Thrin alias assertion package
  - Flow: CUTOVER
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md
  - Branch: cutover/alias-assertion-package-after-shadow-alias-remove

  ## Verification pointer
  - Semantic predecessor: PR #585 merge
    `0fe9f88cfafda38319145e88d0f8b354d53830ca`
  - Dispatch gate: merged lifecycle-proof state-sync / then-current main
  - Canonical input:
    `rev:0c644e56b45bcaac709012206e3e41c2`
  - PR #585 fixture:
    `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_identity_lifecycle_through_alias_remove_v1.json`
  - PR #585 fixture SHA:
    `c31e8c156b3d66f389f67dcdb92b28a4e7c4d0a6ae77e3f0604b99cf38940531`

  Reconstruct exactly the two remaining source-grounded current-node aliases,
  Captain and Thrin Branchborn, as revision-bound DungeonMind-compatible alias
  assertion package rows. Authorize classification only from a complete current
  package proof, then remeasure EVIDENCE_PROVENANCE.

  This PR is non-publishing and does not mutate Eldyrwild.
---

# HANDOFF — seal Captain and Thrin alias assertion package

**Created:** 2026-08-14
**Status:** READY AFTER LIFECYCLE-PROOF STATE-SYNC MERGES
**Canonical handoff path:** `Docs/Plans/HANDOFF-CUTOVER-alias-assertion-package-after-shadow-alias-remove.md`
**Conversation/workstream:** `CUTOVER — Captain and Thrin alias assertion package`
**Flow / owner:** `CUTOVER`
**Direction:** DESIGN → CODE → REVIEW
**Semantic predecessor:** PR #585 merge `0fe9f88cfafda38319145e88d0f8b354d53830ca`
**Suggested branch:** `cutover/alias-assertion-package-after-shadow-alias-remove`
**PR title:** `CUTOVER: seal Captain and Thrin alias assertion package`

> Do not dispatch from `0fe9f88…` directly.
>
> Re-anchor after the required DOCUMENTS state-sync merges, branch from that
> merge / current `main`, and record the actual dispatch-base SHA.
>
> PR #577 is forensic evidence only. Do not reopen it, merge it, extend it, or
> wholesale cherry-pick it.

---

## §1 Mission and merge-ready invariant

### Mission

Against the exact current Eldyrwild revision and the exact current #585
proof-derived source-history policy:

```text
1. enumerate current EVIDENCE_PROVENANCE alias blockers;
2. require exactly Captain + Thrin Branchborn;
3. reconstruct each current alias from revision-bound current-node Buddy
   assertion/support/evidence authority;
4. validate deterministic DungeonMind AliasAssertionV4Record-compatible rows;
5. produce alias-classification authority only from the complete passed proof;
6. re-run whole-world v5 analysis under both proof-derived policies;
7. measure EVIDENCE_PROVENANCE 2 → 0;
8. prove no World Graph mutation.
```

### Merge-ready invariant

```text
current alias blocker IDs
==
exact blocker IDs in passed alias-package proof
==
exact blocker IDs admitted by proof-derived alias policy

package residuals:
  []

package proof:
  passed = true

package rows:
  complete
  revision-bound
  source-grounded
  DungeonMind-valid

current whole-world remeasurement:
  ATTRIBUTE_ASSERTION = 0
  EVIDENCE_PROVENANCE = 0

history:
  IDENTITY_HISTORY = 20
  CONTRIBUTION_HISTORY = 5291

relationships:
  canonical = 323 / 314 / 9 / 3
  migration = 323 / 318 / 5 / 3

World Graph:
  unchanged
```

Expected exact current blocker elements:

```text
node:node:captain-lysandra-ironveil:field:aliases
node:node:thrin-branchborn:field:aliases
```

Those IDs are a **real-world acceptance pin**, not permission for the generic
classifier to hardcode “2”.

### Remaining falsehood

This PR does not clear:

```text
five dual-sense RELATIONSHIP_PREDICATE STOPs
DURABLE_ADOPTION_BOUNDARY
POSTGRES_ADOPTION
DungeonMind existing-world adoption
Buddy → DungeonMind authority transition
product dark-cutover gates
```

Therefore:

```text
CUTOVER_NOT_READY
```

remains expected after this slice.

---

## §2 Authority and boundaries

### Exact canonical input

```text
world:
  eldyrwild

revision:
  rev:0c644e56b45bcaac709012206e3e41c2

payload:
  0640d7ef8ce152ee4f656959e0e9a6c9c2fdf5ecc8bd721729b3019170d677f2
```

### Current lifecycle authority

PR #585 proves:

```text
identity lifecycle:
  28 / 28
  passed
  unresolved []

source-history policy:
  identity_lifecycle_history_v1

ATTRIBUTE_ASSERTION:
  0
```

Do not use the historical locked #575 allowlist.

Recreate/validate the current lifecycle proof against the exact loaded store
before constructing the alias package policy.

### Historical #577 evidence

PR #577 established a useful forensic fact on the earlier eight-alias world:

```text
source-grounded:
  Captain
  Thrin Branchborn

identity-derived:
  six merge-shadow aliases
```

The six merge-shadow aliases have since been retired through governed
`alias_remove`.

#577's source-lineage algorithm is design evidence only.

Current implementation must rederive everything against the current revision.

### Pinned DungeonMind contract

Current dependency:

```text
be76acc997c5fbcb8ceaa090969ec051afa6051d
```

Existing DungeonMind contract already admits alias assertions through the
current `AliasAssertionV4Record` semantics.

No DungeonMind schema change is expected.

A required DungeonMind contract change is:

```text
STOP
→ return to stewardship
```

---

## §3 Source-lineage contract

An alias package row may exist only when the exact current alias is explicitly
recoverable from current-node revision-bound Buddy authority.

For each alias require:

```text
target current node exists

source support:
  assertion_kind == alias OR node
  support_state == supported
  target matches graph_object_id
    OR graph_object_id is null and assertion subject exactly matches target

source contribution:
  exists
  accepted assertion exists
  assertion acceptance_state == accepted
  assertion subject == current target
  contribution active in exact revision replay manifest
  contribution ledger status == active
  computed source-payload digest
    ==
  revision-sealed source-payload digest
    ==
  replay-manifest source-payload digest

support lineage:
  contribution appears in active_contribution_ids
  per-contribution evidence refs exactly equal source assertion evidence refs
  per-contribution source artifact IDs exactly equal source assertion artifact IDs

alias value:
  explicitly present in the source assertion
  no substring/fuzzy/name inference

evidence:
  nonempty
  every ref resolves in current store

source artifacts:
  every referenced artifact resolves

DungeonMind record:
  validates against pinned alias assertion contract
```

No source-grounding through:

```text
merged-away identity
redirect history
old alias_remove rationale
Markdown search
node label coincidence
store.aliases lookup key alone
historical #577 row
```

### Direct alias source

For:

```text
assertion_kind = alias
```

preserve the Buddy assertion identity when compatible with the pinned
DungeonMind contract.

### Bundled node alias

For:

```text
assertion_kind = node
value.aliases contains exact alias
```

derive a deterministic child assertion ID from:

```text
world_id
target_node_id
source Buddy node assertion ID
exact alias value
```

The same inputs must always generate the same ID.

Different semantic claims must never collide.

### Multiple valid source assertions

Do not silently choose one.

If multiple distinct accepted source assertions independently ground the same
alias:

```text
preserve each distinct assertion as a distinct package row
```

provided DungeonMind admits the resulting rows and IDs remain unambiguous.

---

## §4 Files in scope — expected write lease

| Action | Path                                                                                                            |
| ------ | --------------------------------------------------------------------------------------------------------------- |
| Create | `apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py`            |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py`                        |
| Modify | `apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py`                        |
| Create | `apps/live_control_server/services/cutover_alias_assertion_package_after_shadow_alias_remove.py`                |
| Create | `scripts/build_cutover_alias_assertion_package_after_shadow_alias_remove.py`                                    |
| Create | `tests/test_alias_assertion_package_conformance_v1.py`                                                          |
| Create | `tests/test_cutover_alias_assertion_package_after_shadow_alias_remove.py`                                       |
| Create | `tests/fixtures/dungeonmind_kernel/eldyrwild_cutover_alias_assertion_package_after_shadow_alias_remove_v1.json` |

### Precisely bounded discovery

One existing whole-world-conformance test file may require modification if and
only if it owns verification of the new alias-policy plumbing through v4/v5.

Before editing it:

```text
name exact path in implementation handback
explain why existing §4 tests cannot own that boundary
confirm it is test-only
```

No other discovery exception exists.

### STOP path

Any required modification under:

```text
src/graph_memory/**
```

or the DungeonMind repository is a STOP.

---

## §5 Explicit exclusions

Do not:

```text
mutate Eldyrwild
add/remove aliases
add identity decisions
edit assertion support
edit contribution records
change contribution status
invent evidence
change relationship predicates
resolve the five dual-sense STOPs
start Case B adoption
change DungeonMind dependency
modify generic Kernel identity behavior
reuse #577's old eight-alias constants as current authority
```

Do not copy old #577 service behavior that intentionally kept:

```text
EVIDENCE_PROVENANCE = 8
```

That was correct for its historical STOP and is now obsolete.

---

## §6 Proof-derived alias policy

### Requirement

Do not modify generic classification by inserting:

```text
if element_id in {"Captain ID", "Thrin ID"}:
    clear blocker
```

Do not expose a public constructor that accepts arbitrary element-ID sets.

Create a private/proof-derived policy analogous to the lifecycle
source-history policy, but close the stale-proof weakness by retaining exact
revision identity.

Suggested shape:

```text
WholeWorldAliasAssertionPolicy

policy_id
world_id
canonical_revision_id
canonical_graph_payload_sha256
proven_alias_blocker_element_ids
package_proof_sha256 / equivalent deterministic proof identity
private constructor token
```

Default analysis gets an empty legacy policy.

Factory:

```text
alias_assertion_policy_from_proof(proof)
```

must validate at minimum:

```text
exact expected proof schema
proof.passed == true
proof.residuals == []
blocker IDs nonempty
blocker IDs unique
covered blocker IDs == blocker IDs
all package rows reconstructable
all rows refer to covered blocker IDs
all DM assertion IDs collision-safe
world/revision/payload pins nonblank
proof contains no incomplete blocker element
```

### Store/revision binding

Before applying the policy, analyzer/service must require:

```text
policy.world_id == analyzed world
policy.canonical_revision_id == analyzed revision
policy.canonical_graph_payload_sha256 == analyzed manifest payload
```

A policy minted from:

```text
world A
revision A
payload A
```

must fail closed on:

```text
world B
revision B
payload B
```

even if element IDs happen to match.

### Classification behavior

With no alias policy:

```text
current existing behavior unchanged
```

With a valid matching proof-derived alias policy:

```text
only exact covered current alias blocker elements:
  EVIDENCE_PROVENANCE
    →
  REPRESENTABLE_BY_EXPLICIT_ADAPTER
```

Use a note equivalent to:

```text
validated DungeonMind alias assertion package from revision-bound Buddy
source authority
```

Do not alter:

```text
canonical-label duplicate aliases
derivable store.aliases keys
unrelated EVIDENCE_PROVENANCE
source-domain/evidence contract blockers
```

---

## §7 Evidence required to merge

### 7.1 Current blocker inventory

Under:

```text
current lifecycle proof-derived source-history policy
legacy/empty alias policy
```

require current alias `EVIDENCE_PROVENANCE` inventory to be exactly:

```text
node:node:captain-lysandra-ironveil:field:aliases
node:node:thrin-branchborn:field:aliases
```

If not:

```text
STOP
```

### 7.2 Package proof

Require:

```text
passed = true
residuals = []
covered blocker IDs == current blocker IDs
```

Record exact package rows including:

```text
blocker_element_id
target_node_id
alias_value
source_form
Buddy source assertion ID
Buddy source contribution ID
Buddy source payload SHA
source evidence refs
source artifact IDs
DungeonMind assertion ID
DungeonMind alias record
metadata derivation
```

### 7.3 Adversarial unit evidence

At minimum:

```text
valid direct alias assertion
  PASS

valid bundled node alias
  PASS

missing target node
  FAIL

assertion subject != current target
  FAIL

support not supported
  FAIL

contribution absent from replay manifest
  FAIL

contribution inactive in revision
  FAIL

mutable contribution ledger inactive
  FAIL

source payload digest differs from revision seal
  FAIL

source payload digest differs from replay digest
  FAIL

per-contribution evidence lineage drift
  FAIL

per-contribution artifact lineage drift
  FAIL

empty evidence refs
  FAIL

dangling evidence ref
  FAIL

dangling source artifact
  FAIL

alias text not explicitly present in assertion
  FAIL

alias label/value disagreement
  FAIL

ambiguous derived assertion-ID collision
  FAIL

identity/redirect history is only source
  FAIL

partial package
  FAIL / no policy

wrong-world policy
  FAIL

wrong-revision policy
  FAIL

wrong-payload policy
  FAIL

arbitrary alias element allowlist
  impossible through public API
```

### 7.4 Current whole-world remeasurement

On one exact loaded store:

```text
1. prove current identity lifecycle through alias_remove
2. mint current source-history policy
3. analyze with:
     source-history policy
     empty alias policy
4. enumerate current EP alias blockers
5. prove current alias package
6. mint alias policy from complete proof
7. analyze again with:
     same source-history policy
     alias package policy
```

Require actual measured result:

```text
ATTRIBUTE_ASSERTION = 0
EVIDENCE_PROVENANCE = 0
IDENTITY_HISTORY = 20
CONTRIBUTION_HISTORY = 5291
```

Do not force those values inside the classifier.

### 7.5 Relationship invariants

Require unchanged:

```text
canonical:
  323 / 314 / 9 / 3

migration:
  323 / 318 / 5 / 3
```

The exact five migration residual edge IDs remain unchanged.

### 7.6 No mutation

Prove before/after equality for:

```text
canonical head
World Graph tree digest
loaded-store semantic digest
node aliases
identity decisions
identity redirects
assertion support
contribution-history fields
source authority
```

### 7.7 Sealed fixture

Create a deterministic checkout-portable report fixture.

Do not serialize absolute repository/worktree paths.

Verification from a second checkout path must reproduce identical semantic
bytes.

### 7.8 Focused verification

At minimum:

```bash
uv run pytest -q \
  tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_shadow_alias_remove.py \
  tests/test_identity_lifecycle_history_conformance_v1.py \
  tests/test_cutover_identity_lifecycle_through_alias_remove.py

uv run ruff check \
  apps/live_control_server/integrations/dungeonmind_kernel/alias_assertion_package_conformance_v1.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v4.py \
  apps/live_control_server/integrations/dungeonmind_kernel/whole_world_conformance_v5.py \
  apps/live_control_server/services/cutover_alias_assertion_package_after_shadow_alias_remove.py \
  scripts/build_cutover_alias_assertion_package_after_shadow_alias_remove.py \
  tests/test_alias_assertion_package_conformance_v1.py \
  tests/test_cutover_alias_assertion_package_after_shadow_alias_remove.py

git diff --check
git diff --name-only <dispatch-base>...HEAD
```

Record author-local, independent rerun, CI, and manual evidence separately.

---

## §8 Required review handback

```text
Review Cycle <N>

PR:
branch:
head SHA:
dispatch/base SHA:

actual changed paths:
lease deviations:

canonical input:
  world
  revision
  payload

current lifecycle proof:
  passed
  element count
  unresolved

current source-history policy:
  policy ID
  revision binding

pre-package EP inventory:
  exact IDs

alias package proof:
  passed
  residuals
  covered blocker IDs
  exact package row count
  exact package rows/source identities

alias policy:
  policy ID
  world
  revision
  payload
  proof/package digest
  proven blocker IDs

adversarial revision-binding tests:
  wrong world
  wrong revision
  wrong payload

remeasurement:
  ATTRIBUTE_ASSERTION
  EVIDENCE_PROVENANCE
  IDENTITY_HISTORY
  CONTRIBUTION_HISTORY

relationships:
  canonical
  migration
  exact five STOP IDs unchanged

mutation proof:
  head
  tree
  loaded store
  aliases
  identity
  support
  contribution history
  source authority

CUTOVER disposition:
next recommendation:
```

---

## §9 Acceptance rubric

* [ ] Branch starts from the merged state-sync/current-main descendant.
* [ ] Exact current revision/payload pins match.
* [ ] Current lifecycle proof is rerun and passed before alias packaging.
* [ ] Current lifecycle source-history policy is used; stale #575 policy is not.
* [ ] Pre-package alias EP inventory is exactly Captain + Thrin.
* [ ] Generic package proof discovers the blockers; it does not hardcode count=2 as generic correctness.
* [ ] Both blocker elements are completely reconstructed.
* [ ] Every alias row has revision-bound active contribution authority.
* [ ] Every alias row has exact support/evidence/artifact lineage.
* [ ] No row uses merged-away identity history as provenance.
* [ ] DungeonMind alias records validate against the pinned contract.
* [ ] Alias policy can be created only from a complete passed proof.
* [ ] Alias policy is world/revision/payload bound.
* [ ] Wrong-world/revision/payload policy application fails closed.
* [ ] Default analysis behavior remains unchanged without policy.
* [ ] Remeasurement records `ATTRIBUTE_ASSERTION=0`.
* [ ] Remeasurement records `EVIDENCE_PROVENANCE=0`.
* [ ] `IDENTITY_HISTORY=20`.
* [ ] `CONTRIBUTION_HISTORY=5291`.
* [ ] Relationship inventories unchanged.
* [ ] Five relationship STOPs remain.
* [ ] World Graph unchanged.
* [ ] Fixture is deterministic and checkout-portable.
* [ ] No generic Kernel or DungeonMind repo change occurred.
* [ ] `CUTOVER_NOT_READY` remains unless a refreshed complete blocker ledger proves otherwise.

---

## Stop conditions

Stop rather than broadening if:

```text
current EP alias blocker set != exact Captain + Thrin set

either alias lacks current revision-bound source authority

either package row requires evidence invention

source contribution digest does not match revision authority

support/evidence lineage is ambiguous or stale

current lifecycle proof no longer passes

ATTRIBUTE_ASSERTION reappears before alias packaging

correctness requires identity-history traversal as alias provenance

correctness requires src/graph_memory/** changes

correctness requires a DungeonMind contract change

correctness requires relationship STOP resolution

the proposed alias policy cannot be revision-bound

package proof is partial

World Graph mutation is proposed
```

A STOP preserves:

```text
EVIDENCE_PROVENANCE residual
CUTOVER_NOT_READY
```

rather than forcing the counter to zero.
