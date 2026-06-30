# Graph Memory Vocabulary Ablation Dogfood — Expanded Test Beds

Generated: 2026-06-30T20:19:17Z

## 1. Scope

Dogfood run comparing `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` on two expanded test beds: C1S1 Stonebridge recap and Mirathorn city world doc. Packets are corpus/registry-derived, never gold-derived.

- Model: `gpt-5.4-mini`
- Beds: `c1s1-stonebridge`

## Bed: `c1s1-stonebridge`

- Campaign/session: `longmont-c1` / `session-1` (session_number=1)
- Gold fixture: `graph-memory:session-1-candidate-graph-gold:v0`
- Source spans: 8
- Packet: `packet:vocab:8a7c6a045ddb`

### Variant setup

| Variant | Node packet | Edge packet | Nodes | Edges | Cost USD |
|---|---:|---:|---:|---:|---:|
| baseline | no | no | 47 | 28 | 0.046659 |
| edge_packet | no | yes | 52 | 34 | 0.043816 |
| node_packet | yes | no | 46 | 27 | 0.042675 |
| edge_and_node_packet | yes | yes | 47 | 25 | 0.042651 |

### Comparison table

# Vocabulary ablation comparison

Packet: `packet:vocab:8a7c6a045ddb`
Best variant by heuristic score: `node_packet`

| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |
|---|---:|---:|---:|---:|---:|---:|
| baseline | -34 | 0.583 | 0 | 0 | 2 | 5 |
| edge_packet | -35 | 0.583 | 0 | 2 | 1 | 6 |
| node_packet | -24 | 0.667 | 0 | 0 | 1 | 4 |
| edge_and_node_packet | -34 | 0.667 | 0 | 4 | 7 | 7 |

Notes:
- Heuristic review score; not benchmark truth.
- Synthetic tests do not prove model improvement.

### Present vs absent partition

Present-set (7 names): `Stone Bridge`, `Glowkindle`, `Grishna`, `Wizard's Tower Brewing Co`, `The River's Edge Pub`, `Karsemine`, `Bonogo`.

Absent-set (4 names): `Captain Lysandra Ironveil`, `Mireward Reach`, `The Shepherd`, `Torbin Jove`.

| Variant | Recognition (present) | Contamination (absent) |
|---|---:|---:|
| baseline | 0.857 (6/7) | 0/4 |
| edge_packet | 0.857 (6/7) | 0/4 |
| node_packet | 1.000 (7/7) | 0/4 |
| edge_and_node_packet | 1.000 (7/7) | 0/4 |

### Gold recall (candidate graph gold)

| Variant | Node recall | Edge recall |
|---|---:|---:|
| baseline | 0.7692 | 0.2917 |
| edge_packet | 0.7308 | 0.3333 |
| node_packet | 0.7308 | 0.2917 |
| edge_and_node_packet | 0.6923 | 0.2917 |

### GO criteria (best clean variant vs baseline)

- Best clean variant: `node_packet`
- GO-1 (structural): yes
- GO-2 (edge drops): yes
- GO-3 (gold recall): no
- GO-4 (contamination): yes
- GO-5 (generalization): yes
- New gold nodes matched outside packet: `the cat owl`

### Recommendation

Prefer node_packet for further dogfood.

- Best pooled known-name pickup: `edge_and_node_packet`

## Separation Of Claims

Observed dogfood behavior: metrics above come from fresh LLM extraction runs over the two expanded beds.

Synthetic harness validation: unit tests validate comparison/diagnostics APIs; they do not prove model quality.

Speculation / recommendations: per-bed recommendations identify what to try next, not production defaults.

