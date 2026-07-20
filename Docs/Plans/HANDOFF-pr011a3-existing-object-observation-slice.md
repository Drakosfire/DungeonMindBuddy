# HANDOFF — PR011A3 slice 2: existing-object observation

**Status:** `DOING` (GitHub PR #370)  
**Base:** `main` @ `c8f436c4`  
**Branch:** `agent/pr011a3-existing-object-observation`  
**Tip:** `4d137f6a` (+ review fixes in working tree)  
**Umbrella:** #367 (DO NOT MERGE fat tip `eb509dae`)

## §1 Mission

Close REQUEST CHANGES blockers for connect-existing **support-only** observation on promote:

- Break the `contribution_merge` ↔ `candidate_graph_to_contribution` import cycle via neutral `source_artifact_domains`.
- Preserve edge projection integrity while ignoring additive session stamps (`value.session_ids`, `temporal_scope.session_id`) but not other temporal qualifiers.
- Wire `CandidateNode.aliases` so extract-only spellings publish as `alias` assertions with evidence.
- Fail-closed Session 24 PC overlap repair script guards before filtering assertions.
- Prove alias + support assertions survive publish and revision-pinned projection.

## §2 Invariant

Live A3 acceptance remains **PARTIAL / NOT_READY_FOR_CANONICAL_RECAP_BACKFILL** until a fresh prepare→confirm→**exact committed revision reload** (+ Hermes retrieve if claimed) is recorded on the repaired head. This slice removes known integrity blockers; it does not declare full A3 acceptance.

## §3 Observable paths

- `graph_memory.kernel` and `candidate_graph_to_contribution` import in either order without partial-init failure.
- `map_connect_existing_support_assertions` emits attribute + alias support for `resolved_existing` nodes; no competing node assert.
- `_edge_core_semantic_fingerprint` includes stripped `temporal_scope` (session_id removed).
- `supersede_session24_overlapping_pc_node_assertions.py` validates campaign/source revision + drop-subject presence before mutation.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `src/graph_memory/source_artifact_domains.py` | Neutral `CAMPAIGN_STABLE_SOURCE_DOMAINS` constant |
| Modify | `src/graph_memory/kernel/contribution_merge.py` | Import stable domains from neutral module |
| Modify | `src/graph_memory/candidate_graph_to_contribution.py` | Re-export stable domains; alias wiring on connect-existing |
| Modify | `src/graph_memory/kernel/world_projection.py` | Edge fingerprint temporal_scope policy |
| Modify | `src/graph_memory/candidate_graph_preview.py` | `CandidateNode.aliases` + dict parse |
| Modify | `scripts/supersede_session24_overlapping_pc_node_assertions.py` | `_validate_repair_target` fail-closed guards |
| Modify | `tests/test_source_artifact_compatible_stable_domains.py` | Neutral import + import-order smoke |
| Modify | `tests/test_extract_identity_gate.py` | Publish + revision-pinned projection proof |
| Create | `tests/test_edge_core_semantic_fingerprint.py` | Edge fingerprint agree/disagree cases |
| Create | `tests/test_supersede_session24_repair_guards.py` | Repair validation unit tests |
| Create | `Docs/Plans/HANDOFF-pr011a3-existing-object-observation-slice.md` | This handoff |

**Bounded discovery exception:** Not applicable — paths enumerated above.

## §5 Files and capabilities explicitly out of scope

| Path, layer, or capability | Why this slice must not touch or claim it |
|---|---|
| `src/prompts/*.py` | Prompt behavior outside connect-existing publish proof |
| `evals/*/gold/*.json` | No oracle/gold drift |
| Plan UI / hover / Author Node / standing_context | Product slices |
| Atomic multi-contribution confirm | Successor work |
| Fat tip `eb509dae` reconstitution beyond these fixes | Read-only reference |
| Dogfood report Head SHA update | Point authority at PR #370 instead |

## §6 Implementation contract

```text
Input:
  Candidate graph with resolved_existing nodes (+ optional aliases)
  Session 24 contribution contribution:a01be11c6967afd9 for repair script

Output:
  Support-only attribute + alias assertions on durable ids
  Edge fingerprints that ignore session stamps only
  Repair script refuses wrong contribution before filtering

Invariant:
  No competing node assert for connect-existing
  temporal_scope.as_of (etc.) still disagrees across active edge asserts

Failure behavior:
  Repair script exits nonzero on campaign/source/drop-subject mismatch
  Projection integrity error when non-session temporal fields disagree

Replay / idempotency:
  Repair script idempotent when successor carries repair diagnostic marker
```

## §7 Verification ownership map and commands

| Guarantee | Owning boundary | Command or manual scenario | Expected evidence |
|---|---|---|---|
| Import cycle broken | neutral module + merge import | import-order smoke + stable-domain tests | both import orders succeed |
| Edge session-stamp fingerprint | world_projection | `test_edge_core_semantic_fingerprint.py` | agree on session_id drift; disagree on as_of |
| Alias publish proof | identity gate + kernel merge | `test_extract_identity_gate.py` alias publish test | alias + attribute at pinned revision |
| Repair guards | supersede script | `test_supersede_session24_repair_guards.py` | ValueError on mismatch |
| Focused allowlist integrity | git | `git diff --stat` on §4 paths only | no scope creep |

```bash
python -m pytest \
  tests/test_source_artifact_compatible_stable_domains.py \
  tests/test_extract_identity_gate.py \
  tests/test_candidate_graph_to_contribution.py \
  tests/test_supersede_session24_repair_guards.py \
  tests/test_edge_core_semantic_fingerprint.py \
  -q --tb=short

python -c "import graph_memory.kernel; import graph_memory.candidate_graph_to_contribution; print('ok1')"
python -c "import graph_memory.candidate_graph_to_contribution; import graph_memory.kernel; print('ok2')"
```

**GitHub PR:** https://github.com/Drakosfire/DungeonMindBuddy/pull/370
