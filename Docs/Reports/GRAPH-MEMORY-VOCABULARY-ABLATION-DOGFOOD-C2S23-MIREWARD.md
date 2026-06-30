# Graph Memory Vocabulary Ablation Dogfood — C2S23 Mireward

Generated: 2026-06-30T12:58:33Z

## 1. Scope

Dogfood run grounded in the session 23 normalized recap (the canon source other S23 fixtures use), comparing `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` with the existing vocabulary ablation harness. This report is evidence from one dogfood slice, not a generalized benchmark claim.

The packet's known names are partitioned. The present-set uses S23 gold label forms for entities that genuinely recur this session; the absent-set is prior canon NOT in this session, retained to measure contamination. Pooled pickup conflates these; recognition (present) and contamination (absent) are reported separately in section 6.

## 2. Source Material Used

- Model: `gpt-5.4-mini`
- Source spans: 13 recap paragraphs
- Outputs: fresh LLM extraction runs, not precomputed fixtures
- Authority note: the source is a post-session recap fixture; observed behavior is dogfood extraction over canon recap text, not canon memory promotion.

- `evals/graph_memory_layer/examples/session_23_recap_ingest/expected_normalized_recap.md`

## 3. Packet Contents Summary

- Packet: `packet:vocab:4f671bfb39e9`
- Known names: 12
- Type hints: 12
- Predicate hint subjects: 6
- Combat encounter hints: First meat wave
- Do-not-merge hints: 2
- Containment hints: 1

Predicate replacements applied because the project catalog does not contain every handoff suggestion:

- `occurred_at` -> `present_at`
- `involved` -> `participates_in`
- `defended_by` -> `associated_with / located_in`
- `attacked_by` -> `attacks`
- `protects` -> `serves / associated_with`
- `corrupts` -> `threatens / associated_with`

## 4. Variant Setup

| Variant | Node packet | Edge packet | Nodes | Edges | Cost USD |
|---|---:|---:|---:|---:|---:|
| baseline | no | no | 54 | 42 | 0.067708 |
| edge_packet | no | yes | 43 | 38 | 0.045086 |
| node_packet | yes | no | 53 | 35 | 0.062285 |
| edge_and_node_packet | yes | yes | 40 | 38 | 0.046924 |

## 5. Comparison Table

# Vocabulary ablation comparison

Packet: `packet:vocab:4f671bfb39e9`
Best variant by heuristic score: `edge_and_node_packet`

| Variant | Score | Known pickup | Combat matched | Predicate matched | Edge drops | Unsafe blocked |
|---|---:|---:|---:|---:|---:|---:|
| baseline | -12 | 0.333 | 0 | 1 | 1 | 0 |
| edge_packet | -7 | 0.333 | 0 | 3 | 0 | 0 |
| node_packet | -6 | 0.417 | 0 | 2 | 0 | 0 |
| edge_and_node_packet | -4 | 0.417 | 0 | 3 | 0 | 0 |

Notes:
- Heuristic review score; not benchmark truth.
- Synthetic tests do not prove model improvement.

## 6. Present vs Absent Partition (primary signal)

Present-set (7 names, gold label forms): `Mireward Reach`, `Lysandra`, `Lysandro`, `Orik Tane`, `Edge`, `North gate`, `First meat wave`.

Absent-set (5 prior-canon names not in S23): `Maelthor`, `The Shepherd`, `Shepherds`, `Under-Hymn Brood`, `Mireward Council`.

| Variant | Recognition (present) | Recognized | Contamination (absent) | Contaminated |
|---|---:|---|---:|---|
| baseline | 0.571 (4/7) | Edge, Mireward Reach, North gate, Orik Tane | 0.000 (0/5) | (none) |
| edge_packet | 0.571 (4/7) | Edge, Mireward Reach, North gate, Orik Tane | 0.000 (0/5) | (none) |
| node_packet | 0.571 (4/7) | Edge, Mireward Reach, North gate, Orik Tane | 0.200 (1/5) | Mireward Council |
| edge_and_node_packet | 0.571 (4/7) | Edge, Mireward Reach, North gate, Orik Tane | 0.200 (1/5) | Mireward Council |

Reading: recognition should rise with the packet (the benefit); contamination must stay at 0 (any absent-set name extracted is a hallucination the injected vocabulary induced, not a pickup win).

## 6a. Observed Improvements (pooled, exact-label)

- Best pooled known-name pickup: `edge_and_node_packet` (pooled across present+absent; see section 6 for the partition).
- Best combat encounter pickup: `baseline`.
- Best predicate hint pickup: `edge_and_node_packet`.
- Treat these as exact-label diagnostics over one dogfood run, not a generalized model-quality claim.

Per-variant node kinds:

- `baseline`: `{"actor": 11, "collective": 8, "object": 12, "place": 13, "thread": 10}`
- `edge_packet`: `{"actor": 11, "collective": 8, "object": 11, "place": 11, "thread": 2}`
- `node_packet`: `{"actor": 18, "collective": 5, "object": 14, "place": 9, "thread": 7}`
- `edge_and_node_packet`: `{"actor": 12, "collective": 4, "object": 12, "place": 11, "thread": 1}`

Per-variant edge predicates:

- `baseline`: `{"attacks": 6, "carries": 1, "commands": 3, "contains": 2, "displaced_from": 1, "governs": 1, "knows_about": 1, "leads": 1, "leads_to": 1, "located_in": 1, "member_of": 10, "north_of": 1, "part_of": 2, "present_at": 1, "refers_to": 3, "sublocation_of": 1, "threatens": 3, "travels_to": 2, "within": 1}`
- `edge_packet`: `{"attacks": 1, "caused_by": 1, "commands": 3, "governs": 1, "knows_about": 2, "leads": 1, "located_in": 5, "member_of": 8, "part_of": 1, "participates_in": 2, "pursues": 1, "refers_to": 2, "reports_threat_in": 1, "routes_to": 1, "same_as": 1, "sublocation_of": 1, "threatens": 2, "travels_to": 2, "within": 2}`
- `node_packet`: `{"attacks": 1, "commands": 2, "contains": 1, "displaced_from": 1, "governs": 2, "identified_as": 1, "knows_about": 2, "leads_to": 1, "located_in": 4, "member_of": 8, "part_of_group": 5, "possesses": 1, "refers_to": 2, "same_as": 1, "threatens": 1, "travels_to": 2}`
- `edge_and_node_packet`: `{"attacks": 3, "carries_report_to": 1, "commands": 2, "contains": 1, "displaced_from": 1, "governs": 1, "holds": 1, "leads": 1, "leads_to": 1, "located_in": 4, "member_of": 8, "owns": 5, "present_at": 1, "refers_to": 2, "reports_threat_in": 1, "routes_to": 1, "threatens": 1, "travels_to": 2, "within": 1}`

## 7. Observed Regressions

- No harness-level regression warnings were emitted.
- Combat encounter pickup is exact-label sensitive: `baseline` won this lane; packet-assisted variants may emit a nearby label that does not match the gold form `First meat wave`.
- Combined packets changed final edge volume from 42 to 38 edges, with predicate validation issues changing from 0 to 0.

## 7a. Pickup Answers

- Best pooled known-name pickup: `edge_and_node_packet` (read section 6 for the present/absent split).
- Best present-set recognition: `baseline`, `edge_packet`, `node_packet`, and `edge_and_node_packet` at 0.571.
- Best combat encounter pickup: `baseline`.
- Contamination (absent-set names emitted) is reported per variant in the safety section; the target is zero.

## 7b. Edge Answers

- Predicate hint pickup improved most in `edge_and_node_packet`.
- Endpoint binding is inferred from final candidate edges and dropped-edge diagnostics; the category pipeline does not currently report a separate binding success counter.
- Dropped-edge reasons come from extraction run diagnostics when present; zero reported drops means no comparison-level drop reason is available.
- Obvious bad edges require raw edge review; this runner commits only compact metrics and the markdown report.

## 8. Ambiguous / Inconclusive Behavior

- The source is a post-session recap; combat encounters are session-novel, so a prior-canon packet would not normally carry `First meat wave` — it is included only to probe the combat lane.
- Recognition is exact-label against gold forms; if the extractor emits a near-variant label, it counts as a miss unless the exact form appears.
- This dogfood run scores against the packet partition, not against the full human candidate-graph gold; it does not measure overall extraction precision/recall.

## 9. Safety Observations

- `baseline`: duplicate labels=0, conflicting kinds=0, unsafe blocked=0, do-not-merge warnings=0, present recognition=0.571 (4/7), absent contamination=0/5 [(none)].
- `edge_packet`: duplicate labels=0, conflicting kinds=0, unsafe blocked=0, do-not-merge warnings=0, present recognition=0.571 (4/7), absent contamination=0/5 [(none)].
- `node_packet`: duplicate labels=0, conflicting kinds=0, unsafe blocked=0, do-not-merge warnings=0, present recognition=0.571 (4/7), absent contamination=1/5 [Mireward Council].
- `edge_and_node_packet`: duplicate labels=0, conflicting kinds=0, unsafe blocked=0, do-not-merge warnings=0, present recognition=0.571 (4/7), absent contamination=1/5 [Mireward Council].
- Duplicate label collisions changed from 0 in baseline to 0 in `edge_and_node_packet`.
- Conflicting kind collisions changed from 0 in baseline to 0 in `edge_and_node_packet`.
- Unsafe cross-class blocked counts changed from 0 in baseline to 0 in `edge_and_node_packet`.
- Do-not-merge collision warnings are reported per variant above.
- Absent-set contamination is the key safety lane: any absent name extracted means the injected vocabulary induced a hallucination.

## 10. Recommendation

Do not promote `edge_and_node_packet` from this run: present-set recognition tied baseline, while the heuristic winner contaminated absent-set names. If continuing packet-assisted dogfood, use `edge_packet` as the clean comparison and keep `baseline` as the safety control.

This recommendation is partition-aware for this dogfood run only. Treat it as a next-dogfood choice, not a production default.

## 11. Follow-up Tasks

- Add an alias-aware diagnostic lane so gold near-variants (e.g. `North gate` vs `north-gate crisis`) are credited without changing extractor output.
- Score against the full S23 candidate-graph gold (precision/recall) so claims extend beyond packet-name recognition.
- If recognition gains hold but contamination stays at zero, promote `node_packet`/`edge_and_node_packet` to a larger multi-session dogfood.
- Keep the present/absent partition as the standing contract for every future vocabulary run.

## Separation Of Claims

Observed dogfood behavior: the metrics and notes above come from the fresh C2S23 Mireward variant runs over the recap.

Synthetic harness validation: existing unit tests validate the comparison and diagnostics APIs; they do not prove model quality.

Speculation / recommendations: the follow-up tasks and recommendation identify what to try next, not what is generally proven.

