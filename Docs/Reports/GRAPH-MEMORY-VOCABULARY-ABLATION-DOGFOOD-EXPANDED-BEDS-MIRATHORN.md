# Graph Memory Vocabulary Ablation Dogfood — Expanded Test Beds

Generated: 2026-06-30T17:20:46Z

## 1. Scope

Dogfood run comparing `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` on two expanded test beds: C1S1 Stonebridge recap and Mirathorn city world doc. Packets are corpus/registry-derived, never gold-derived.

- Model: `gpt-5.4-mini`
- Beds: `mirathorn-city`

## Bed: `mirathorn-city`

- Campaign/session: `elderwyld` / `mirathorn-city` (session_number=0)
- Gold fixture: `graph-memory:mirathorn-city-candidate-graph-gold:v0`
- Source spans: 133
- Packet: `packet:vocab:baf8726327fd`

### Variant setup

| Variant | Node packet | Edge packet | Nodes | Edges | Cost USD |
|---|---:|---:|---:|---:|---:|
| baseline | no | no | 90 | 36 | 0.129137 |
| edge_packet | no | yes | 105 | 30 | 0.089989 |
| node_packet | yes | no | 81 | 30 | 0.108077 |
| edge_and_node_packet | yes | yes | 72 | 46 | 0.090278 |

### Comparison table

# Vocabulary ablation comparison

Packet: `packet:vocab:baf8726327fd`
Best variant by heuristic score: `edge_and_node_packet`

| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |
|---|---:|---:|---:|---:|---:|---:|
| baseline | -58 | 0.462 | 0 | 4 | 0 | 10 |
| edge_packet | -74 | 0.462 | 0 | 5 | 0 | 12 |
| node_packet | -55 | 0.692 | 0 | 4 | 0 | 11 |
| edge_and_node_packet | -23 | 0.538 | 0 | 5 | 0 | 5 |

Notes:
- Heuristic review score; not benchmark truth.
- Synthetic tests do not prove model improvement.

### Present vs absent partition

Present-set (7 names): `Mirathorn`, `Stormspire Peaks`, `Lake Mirathorn`, `Lundayell Empire`, `Festival of Expansion`, `Shepherd's Flock`, `Wizard's Tower Brewing Co`.

Absent-set (4 names): `Stone Bridge`, `Glowkindle`, `Mireward Reach`, `Karsemine`.

| Variant | Recognition (present) | Contamination (absent) |
|---|---:|---:|
| baseline | 0.714 (5/7) | 0/4 |
| edge_packet | 0.714 (5/7) | 0/4 |
| node_packet | 1.000 (7/7) | 0/4 |
| edge_and_node_packet | 0.714 (5/7) | 0/4 |

### Gold recall (candidate graph gold)

| Variant | Node recall | Edge recall |
|---|---:|---:|
| baseline | 0.6786 | 0.1154 |
| edge_packet | 0.7143 | 0.1538 |
| node_packet | 0.7143 | 0.2308 |
| edge_and_node_packet | 0.6429 | 0.1923 |

### GO criteria (best clean variant vs baseline)

- Best clean variant: `edge_and_node_packet`
- GO-1 (structural): yes
- GO-2 (edge drops): no
- GO-3 (gold recall): no
- GO-4 (contamination): yes
- GO-5 (generalization): yes
- New gold nodes matched outside packet: `the Lundayell Empire`

### Recommendation

Prefer edge_and_node_packet for further dogfood.

- Best pooled known-name pickup: `node_packet`

## Separation Of Claims

Observed dogfood behavior: metrics above come from fresh LLM extraction runs over the two expanded beds.

Synthetic harness validation: unit tests validate comparison/diagnostics APIs; they do not prove model quality.

Speculation / recommendations: per-bed recommendations identify what to try next, not production defaults.

