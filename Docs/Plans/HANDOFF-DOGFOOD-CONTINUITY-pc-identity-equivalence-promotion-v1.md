# HANDOFF — DOGFOOD-CONTINUITY: promote PC identity equivalence

**Status:** MERGED — consumed by governed recap World genesis
**Flow:** DOGFOOD-CONTINUITY  
**Base:** `efa3e5fd47bcd6e52193cb7d0a5b989156de137d`  
**Consumer:** governed recap World genesis

## §1 Mission

Promote the proven generic `pc ≡ player_character` identity compatibility rule
to `main` before recap World genesis. The invariant is: equivalent PC wire
representations resolve as the same durable identity, while genuine NPC and
creature collisions remain blocked.

## §2 Context and state authority

The predecessor is the experimental #715 branch's `8a90d75f` implementation.
This promotion merged as PR #716 at
`d85a3787d05fdb0cbf4292f4f1411833f952166a`; Review Cycle 1 was APPROVE
(recorded as GitHub COMMENT due self-review) with 18 independently rerun tests.
The active consumer is
`Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md`.
No other authority changed with this prerequisite.

## §3 Design

Normalize only identity-comparison kinds: `pc` becomes `player_character`
after the existing wire-kind normalization. Stored object kinds are unchanged.
This is not campaign-specific and does not alter fuzzy matching, aliases,
ontology, or source provenance.

## §4 Write lease

| Path | Purpose |
| --- | --- |
| `apps/live_control_server/models/world_graph_mutation_context.py` | Normalize PC representation aliases at the shared identity comparator. |
| `tests/test_pc_identity_normalization.py` | Positive equivalence and negative cross-kind regression coverage. |
| `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-pc-identity-equivalence-promotion-v1.md` | This handoff. |

## §5 Forbidden/collision paths

| Path | Rule |
| --- | --- |
| `src/graph_memory/party_context.py` | No roster or source-authority change. |
| `apps/live_control_server/integrations/dungeonmind/**` | No provider or publication change. |
| `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-governed-recap-world-genesis-v1.md` | Read-only until guarded post-merge sync. |

## §6 Runtime ownership

No database, server, model, source, or external state mutation is required.
This is pure shared identity-policy code.

## §7 Verification

```bash
/tmp/DungeonMindBuddy-full-corpus-world-graph-ingestion-v1/.venv/bin/python -m pytest -q tests/test_pc_identity_normalization.py tests/test_cutover_native_governed_write.py
```

## §8 Non-goals

No recap genesis implementation, PC roster creation, candidate replay, alias
cleanup, worldbuilding work, ontology widening, model call, or UI change.

## §9 Acceptance

- `pc`, `player_character`, and `dnd5e:player_character` compare as same-kind.
- NPC versus player-character remains a blocked collision.
- Existing governed-write tests pass.
- The successor recap-genesis design can consume this rule without duplicating it.
