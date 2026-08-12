# HANDOFF — Eldyrwild Relationship Semantic Closure

**Created:** 2026-08-12
**Updated:** 2026-08-12 — P1 repair pass (kind-miscoding STOP, authority-safe resume, finalizer chain, live seals)
**Status:** BUILD repair in progress on PR #563 — merge only after P1 proofs green on current `main`
**Canonical handoff path:** `Docs/Plans/HANDOFF-eldyrwild-relationship-semantic-closure.md`
**Conversation name:** `DUNGEONMIND-CUTOVER`
**Flow / agent:** `BUILD`
**PR:** [#563](https://github.com/Drakosfire/DungeonMindBuddy/pull/563)
**Branch:** `build/eldyrwild-relationship-semantic-closure`

**Required predecessors:**

* PR #559 C₄ false-hires — merged `8abfca285a780adb33797c71fd5ff6878caa6a76` + canonical `Q₃→Q₄` live exit
* Exact Q₄ effective re-anchor absorbed as first implementation commit of this PR

---

## §0 Mission

Resolve every Q₄ residual that existing Kernel seams can govern, without deleting supported campaign truth that only a Buddy node-kind retype can admit, and leave a head that is reproducible from durable authority.

**One-sentence invariant:** zero remaining *mutable* residual under Kernel authority — not zero remaining semantics by contradiction of repairable facts.

## §1 Exit inventory (locked)

```text
Base Q₄:   366 / 311 / 55 / 3
Final:     323 / 314 / 9 / 3
```

* 46 mutable units applied (54 ordered operations)
* 9 deferred `deferred_buddy_kind_repair` residuals remain open (exact edge-id set in manifest)
* Uses-statblock mechanics unchanged at 3

## §2 Closure classes

| Kind | Count | Kernel seam |
|---|---|---|
| `identity_merge` | 7 | `contradict` + `merge_identity` + `publish_world_revision` |
| `contradicts_and_replaces` | 2 | `correct_edge_assertion_support` |
| `compound_decomposition` | 1 | `contradict` + `merge_contribution_to_revision` |
| `contradiction_only` | 36 | `contradict_edge_assertion_support` |
| `deferred_buddy_kind_repair` | 9 | **STOP** — no Kernel node-kind retype |

## §3 Kind-miscoding STOP (P1)

Kernel cannot retype node kinds (edge-only correct/contradict; additive node merges refuse disagreeing fingerprints; existing-node apply ignores `kind`). The nine rows whose adjudications require an endpoint retype are inventoried and sealed but **never contradicted**. Successor: Buddy source-repair retype + re-admission.

## §4 Authority contracts (P1)

1. **Applied detection** mirrors C₄: revision digest **value**, active replay-manifest entry with same digest, mutable ledger digest+`status==active`, contribution-index coherence, plus op-specific support/identity shape. Shape/digest without full authority → `integrity_failure`, never `already_applied`.
2. **Resume** is an exact prefix of the flat `operation_plan` (not merely fully completed units). Intra-unit op2-without-op1 is refused. Target-source seals run for **every** manifest unit before any `state.applied` early exit — original contribution authority remains sealed across the whole prefix-resume program.
3. **Finalizer** requires inventory match, deferred residual set equality, Q₄ ancestry via `prove_revision_is_anchor_or_descendant_v1`, **exact post-Q₄ revision chain ownership** (descendant count == 54 and forward `operation_ids` == locked contribution/identity-decision IDs from `operation_plan`), pinned + unpinned `rebuild_from_contributions` equivalence, revision-bound closure contributions, durable active identity decisions, and live source + target-source seals for **all 55** rows.
4. **Preflight** re-verifies sealed source artifacts via `resolve_evidence_excerpt` / `verify_excerpt_against_seal` and seals target contribution payloads against locked `target_source_payload_sha256`.

## §5 Artifacts

```text
graph_data/approved_graph_corrections/eldyrwild/relationship-semantic-closure-v1/
  manifest.json
  source-corrections.json
  compound-decompositions.json
  identity-migrations.json
  unsupported-assertions.json
```

Manifest sha256 is locked in `eldyrwild_relationship_semantic_closure.py` (`LOCKED_MANIFEST_SHA256`).

## §6 Explicit non-goals

* Inventing Kernel node-kind correction
* Scheduling individual C₅+ semantic slices for the 46 mutable residuals
* Claiming residual=0 while kind-miscoding facts remain unfixed
* Mutating the canonical live world without `--allow-live-world`

## §7 Post-merge live gate

```bash
uv run python scripts/apply_eldyrwild_relationship_semantic_closure.py apply \
  --expected-base-revision-id rev:3759d8d6a02f09306397918234a2ded2 \
  --allow-live-world
uv run python scripts/apply_eldyrwild_relationship_semantic_closure.py finalize \
  --allow-live-world
```

Requires explicit operator authorization. Then re-anchor `R_current` to the emitted pin.

## §8 Successor

Buddy source-repair for the 9 deferred kind-miscoding residuals, then a bounded re-admission / residual-clearing slice once kinds are correct.
