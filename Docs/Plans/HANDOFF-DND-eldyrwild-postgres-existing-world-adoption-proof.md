---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: CUTOVER — Eldyrwild PostgreSQL existing-world adoption proof
  - Flow: DND
  - Direction: STEWARD → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md
  - Branch: dnd/cutover-eldyrwild-postgres-existing-world-adoption-proof
  - Repository: Drakosfire/DungeonMind

  ## Verification pointer
  - DungeonMind base: `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92`
  - Buddy input merge: `7922b6108cf9e05787f9c79cddcee9347edb0b44`
  - Sealed bundle Git blob: `274cdd9e6d38d5a00aa43d780779e95a7919d975`

  Prove unchanged DungeonMind #33 can adopt the exact post-#609 Eldyrwild
  bundle into a real empty PostgreSQL target atomically and replay/recover it
  without loss. Do not repair adoption runtime.
---

# HANDOFF — prove exact Eldyrwild PostgreSQL existing-world adoption

**Created:** 2026-08-16
**Status:** READY after the post-#609 DOCUMENTS state-sync merges; do not dispatch from `7922b610…` directly
**Canonical handoff path:** `Docs/Plans/HANDOFF-DND-eldyrwild-postgres-existing-world-adoption-proof.md`
**Conversation/workstream:** `CUTOVER — Eldyrwild PostgreSQL existing-world adoption proof`
**Flow / owner:** `DND`
**Repository:** `Drakosfire/DungeonMind`
**Direction:** STEWARD → CODE → REVIEW
**DungeonMind base revision:** `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92`
**Buddy input (post-#609 main at this writing):** `7922b6108cf9e05787f9c79cddcee9347edb0b44`
**Suggested branch:** `dnd/cutover-eldyrwild-postgres-existing-world-adoption-proof`
**PR title:** `DND: prove exact Eldyrwild PostgreSQL existing-world adoption`

> Repository law for Buddy sequencing: [`AGENTS.md`](../../AGENTS.md).
> Dispatch base for this implementation is the **merged post-#609 DOCUMENTS
> state-sync SHA / then-current Buddy `main`**, not `7922b610…` merely because
> it is recorded here. Re-anchor before opening the DungeonMind PR.
>
> This is an acceptance/proof slice over existing adoption runtime. It is not
> permission to redesign DungeonMind persistence.

---

## §1 Mission and merge-ready invariant

**Mission:** Starting from an empty PostgreSQL target, unchanged DungeonMind #33 adopts the exact sealed post-#609 Eldyrwild `dm_existing_world_adoption_bundle_v2` into exactly one durable world/head/revision with complete source, contribution, correction, identity, and graph state.

**Merge-ready invariant:** Exact raw sealed bundle bytes parse through the real v2 adoption/parser boundary; first PostgreSQL adoption writes one world, one first graph revision, and one terminal receipt; exact replay returns the original success without duplication; changed bytes under the same adoption identity conflict; precommit failure leaves no partial Eldyrwild state; postcommit response loss recovers the committed outcome; readback matches the sealed bundle, including contribution evidence refs with no same-ID/different-payload conflict.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed path? | **Yes**, if the slice stays acceptance-only. Runtime/schema repair is a split. |
| Most likely adversarial sequence | Bundle parses in memory, then PostgreSQL rejects a new durable-identity/schema class. |
| Will §7 detect that failure? | **Yes.** The owning boundary is real PostgreSQL adoption, not in-memory helpers. |
| Easiest boundary to under-test | Postcommit recovery and contribution-evidence uniqueness on the real evidence table. |
| Fact that forces stop/split | Any need to change DungeonMind runtime, migrations, `dm_evidence_ref_v1`, or the sealed Buddy bundle. |

---

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | Buddy tracker/status after the post-#609 DOCUMENTS sync; DungeonMind existing-world adoption contracts |
| DungeonMind base | `f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92` (PR #33) unless re-anchor proves a newer required pin |
| Buddy input merge | Re-anchor to the merged DOCUMENTS sync / then-current Buddy `main`. At this writing that predecessor is PR #609 merge `7922b6108cf9e05787f9c79cddcee9347edb0b44` |
| Exact input consumed | Buddy `graph_data/approved_existing_world_adoptions/eldyrwild/dungeonmind-v6/bundle.json` Git blob `274cdd9e6d38d5a00aa43d780779e95a7919d975` |
| Predecessor contract | Buddy #602 sealed the v2 bundle; first PostgreSQL attempt STOPped on evidence identity; Buddy #609 repaired export IDs. Author-reported PostgreSQL green is not the independent acceptance PR |
| Named successor | Correspondence / authority-transition design. Not product-authority switch |
| What remains false | Buddy reads/writes are not switched to DungeonMind; Plan/Play/Hermes do not automatically read DungeonMind; old Buddy graph authority is not deleted; no cutover flag is implied |
| Explicit non-goals | Patching persistence to make Eldyrwild pass; weakening idempotency; accepting same durable ID with different fingerprints; mutating the sealed bundle; product-authority switch |
| Branch / isolated checkout | `dnd/cutover-eldyrwild-postgres-existing-world-adoption-proof` in a DungeonMind worktree from `f2e27380…` |
| Parallel lanes / collision hotspots | Do not share the live `dungeonmind-postgres-dev` target with another mutating lane without serialization |
| Runtime/state ownership | Isolated empty PostgreSQL target. Suggested local DSN: `postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind` (`dungeonmind-postgres-dev`). Source isolation is not database isolation |
| State-authority sync set after merge | Buddy tracker/status/roadmap: mark this proof `DONE` and keep product cutover `BLOCKED`. Do not edit Buddy architecture |

Start review-cycle counting from the first formal judgment against a distinct DungeonMind PR head.

---

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Empty target | No Eldyrwild world/head/receipt | First adopt creates exactly one of each | Yes | PostgreSQL adoption |
| Exact retry | Should return original receipt | Same committed receipt; no duplicates | Yes | PostgreSQL adoption |
| Different bundle, same world/adoption identity | Conflict | `IdempotencyConflictError`; stored receipt unchanged | Yes | PostgreSQL adoption |
| Precommit injected failure | Unknown outcome | Zero Eldyrwild durable rows | Yes | PostgreSQL adoption |
| Postcommit response loss | Commit may have succeeded | Recovery returns the committed receipt | Yes | PostgreSQL adoption |
| Evidence extract | Pre-#609 collided on raw Buddy IDs | No same-ID/different-payload conflict on post-#609 IDs | Yes | PostgreSQL evidence persistence |
| In-memory adopt | Already green | May support but cannot prove this PR | Support only | Memory repository |

Required proof sequence:

```text
1. assert target world absent
2. consume exact raw sealed bundle bytes
3. parse through real DungeonMind v2 parser boundary
4. first PostgreSQL adoption
5. durable receipt
6. exact retry of identical bytes
7. same-world different bundle conflict
8. injected precommit failure
9. injected postcommit response-loss recovery
10. durable readback
```

Readback must prove at least:

```text
world_id = eldyrwild
graph schema = dm_union_graph_v6
one world head
one first adopted graph revision
one terminal adoption receipt
469 objects
323 current semantic relationships
3 secondary object aspects
5 aspect-selected relationships
complete source artifacts/revisions
complete GraphContributionV2 history
typed assertion correction history
complete IdentityDecisionV2 history
```

Also prove contribution evidence refs extract/insert without any same-ID/different-payload conflict.

---

## §4 Files in scope — write lease

Repository: `Drakosfire/DungeonMind`.

| Action | Path | Purpose |
|---|---|---|
| Create | `tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json` | Exact post-#609 Buddy bytes (blob `274cdd9e…`) |
| Create | `tests/unit/test_eldyrwild_existing_world_adoption_bundle_v2.py` | Parser/in-memory pins against those exact bytes |
| Create | `tests/integration/test_postgres_eldyrwild_existing_world_adoption.py` | Owning-boundary PostgreSQL matrix |

**Bounded discovery exception:** at most `tests/integration/conftest.py`, and only if TRUNCATE/CASCADE cannot empty `existing_world_adoptions` without naming that table. Do not use the exception to change production runtime.

A required path outside this lease is a STOP.

---

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/dungeonmind/**` | Adoption runtime is the thing under proof, not the thing to patch |
| `src/dungeonmind/infrastructure/postgres/evidence_extract.py` | Evidence uniqueness is the durable contract |
| `migrations/**` | Schema redesign is a successor decision |
| Buddy `graph_data/**` / producer | Sealed input; do not regenerate semantics inside DungeonMind |
| Buddy product surfaces | Authority switch is separately blocked |

STOP if the exact post-#609 bundle exposes a new PostgreSQL/runtime incompatibility, schema mismatch, durable identity collision, missing migration, missing replay/recovery, or any need to reinterpret the sealed Buddy bundle. Report the failing object/row/contract. Do not patch persistence merely to make Eldyrwild pass.

---

## §6 Implementation contract

```text
Input:
  exact raw bytes of Buddy bundle blob 274cdd9e6d38d5a00aa43d780779e95a7919d975
  DungeonMind f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92
  empty PostgreSQL target

Output:
  checked-in fixture + unit/integration proof that the matrix in §3 is true

Invariant:
  unchanged DungeonMind adopts exact post-#609 bytes atomically and recoverably

Failure behavior:
  new durable-contract failure → STOP, no runtime patch
  evidence_ref same-ID/different-payload → STOP (this class should already be gone)

Replay / idempotency:
  same bytes → original receipt, no duplicates
  changed bytes / same adoption identity → conflict
  retry after precommit failure → empty target remains empty
  retry after postcommit response loss → one committed receipt
```

```text
Commit point: adoption_repository.adopt returns after durable commit
Before commit: no Eldyrwild world/head/receipt/graph/contribution/identity/source rows
After commit: exactly one of each required durable object
Truthful result after post-commit failure: recovery probe returns the committed receipt
```

Trust boundary:

```text
Verifies: exact Buddy blob SHA-1, bundle SHA-256, producer_revision 4446b6d2…,
          source revision rev:0c644e56…, graph payload SHA 047214f1… (published v6),
          source graph payload SHA 0640d7ef…, published revision rev:34b1f8e2…
Records/trusts without proving: Buddy producer internals; product-authority switch
```

Copy the fixture from Buddy; do not recanonicalize the bytes.

---

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Exact bytes are the sealed Buddy blob | Fixture SHA | Contract | `git hash-object` / sha256 of fixture | blob `274cdd9e…` | Recanonicalized or different bytes |
| Parse/adopt in memory | Unit tests | Regression | focused unit pytest | parse + memory adopt/retry/conflict | Parser rejects sealed bytes |
| Empty → first adopt → one head/revision/receipt | PostgreSQL | Adversarial | focused integration pytest | counts + receipt pins | Partial write or evidence collision |
| Exact retry | PostgreSQL | Adversarial | same | original receipt, no duplicates | Second revision/receipt |
| Different bundle conflict | PostgreSQL | Adversarial | same | `IdempotencyConflictError` | Overwrite |
| Precommit rollback | PostgreSQL | Adversarial | failure_hook before commit | zero Eldyrwild rows | Leftover rows |
| Postcommit recovery | PostgreSQL | Adversarial | adopt then PersistenceUnavailableError | recovered receipt == committed | Duplicate or unknown-as-failure |
| Readback graph counts | PostgreSQL | Contract | stored revision payload | 469/323/3/5 | Count drift |
| Evidence identity closed | PostgreSQL | Contract | no conflicting evidence_ref | previous Session-10 error gone | New identity collision |

Exact verification commands (DungeonMind worktree):

```bash
git rev-parse HEAD
# must remain f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92 until this PR's own commits

python3 - <<'PY'
from pathlib import Path
import hashlib
raw = Path("tests/fixtures/dungeonmind_dnd/eldyrwild_existing_world_adoption_bundle_v2.json").read_bytes()
print("blob", hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest())
print("sha256", hashlib.sha256(raw).hexdigest())
PY
# expect blob 274cdd9e6d38d5a00aa43d780779e95a7919d975

uv run pytest -q tests/unit/test_eldyrwild_existing_world_adoption_bundle_v2.py

DUNGEONMIND_DATABASE_URL='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dungeonmind' \
  uv run pytest -q tests/integration/test_postgres_eldyrwild_existing_world_adoption.py

git diff --check
git diff --name-only f2e273804d7e4e2f5bcaf4c964525f8ccb0c4e92...HEAD
```

There is no pre-authorized baseline waiver.

---

## §8 Required review handback

```text
DungeonMind branch and final head
confirmation HEAD's only production-adjacent changes are the leased test/fixture paths
fixture blob SHA-1 and SHA-256
exact unit and PostgreSQL command outputs
readback counts
confirmation previous evidence_ref conflict is gone
any new STOP, with object/row/contract
confirmation no DungeonMind runtime/migration change
confirmation no Buddy product-authority claim
```

Do not merge a DungeonMind PR that repaired runtime to get green.

---

## §9 Acceptance checklist

- [ ] Fixture bytes are Git blob `274cdd9e6d38d5a00aa43d780779e95a7919d975`
- [ ] DungeonMind base is `f2e27380…` unless a documented re-anchor required a newer pin
- [ ] Empty target, first adopt, exact retry, conflict, precommit rollback, postcommit recovery, and readback all pass on real PostgreSQL
- [ ] 469 objects / 323 relationships / 3 aspects / 5 aspect-selected relationships
- [ ] No `contribution embeds conflicting evidence_ref`
- [ ] No DungeonMind `src/` or `migrations/` edits
- [ ] Product-authority switch remains false
