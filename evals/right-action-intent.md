# Right Action

**Registry ID** `buddy.right-action-intent.v1`

Classify the user's intent at one decision point. This is the decision-model benchmark. [Right Action at the Right Time](right-action-coverage.md) measures ordinary Buddy fulfillment, including target binding, evidence, side effects, recovery, and delivery.

## Frozen v1

[Fixtures and local Gold](right_action_intent/cases.json) contain 103 classification instances over 42 choices. Each of the 41 action families has a direct request and a paraphrase. The suite also contains nine newly authored contrasts, the nine retained starter utterances, and three dialogue versions of ambiguous starter utterances. The retained variants are development evidence. V1 has no independently held-out family split.

The model sees one utterance, any pinned dialogue, one intent instruction, and the same ordered action definitions for every case. Resolve the requested action family and defer if the available text leaves it unclear. Corpus lookup, target resolution, permissions, and execution belong downstream. Gold labels and IDs stay in the local scorer.

### Catalog coverage

| Catalog area | First-action labels |
| --- | --- |
| Discussion and authoring | discuss, clarify_request, draft_in_conversation, write_current_page, read_source, read_rules, review_lore_page, review_connected_page, save_page |
| Plan | plan, continue_work_plan, plan_cards, choice_option |
| Graph, ingestion and publication | review_relationship, publish_relationships, name_correction, identity_review, publish_extraction |
| Statblocks and Combat | change_mechanics, review_variant_approval, link_statblock, build_encounter, preview_encounter, start_combat, update_combat |
| Images and map | prepare_image, generate_image, save_image, place_image, map_navigation, place_map_coordinates, reference_object, npc_art |
| Play, recap, and recovery | play_dispatch, play_edit, open_table, record_roll, record_session_note, played_recap, recover_request, operator_handoff |
| Insufficient input | needs_context_to_choose |

These labels describe requested actions across the [canonical action catalog](plan-authoring-benchmark.md#action-catalog), including operator-owned actions and requested capabilities. A correct label provides no evidence that Buddy can perform it. Where the fixtures overlap, the pinned expected label is the v1 scoring decision. In particular, audit the boundary between a prepared table and a reference-object table, an encounter preview and an operator handoff, and choosing a branch versus editing a running scene before using these cases as adoption gates.

## Reproduce and compare

```bash
python -m evals.right_action_intent.run --validate-only
python -m evals.right_action_intent.run --credential-file /path/to/.env --output /path/to/new-record.json
```

The shared scorer `evaluate_suite` accepts an async adapter that receives only the state, instruction, and ordered action definitions, and returns one label and its raw response. The CLI supplies a TypeSafe adapter using the existing GenerationEngine request converter. Additional providers can call the shared scorer with their own transport adapter. Compare the same suite digest and option order. Report adapter/model/runtime settings, response validity, provider errors, and latency. One inference per case, no transport retries. Provider errors remain in the attempt denominator and outside decision latency. The baseline used concurrency four, and latency excludes queue time.

## Jev baseline

One run with `jev-1.14.0` scored **93/103**. It returned nine wrong actions and one unnecessary deferral. There were zero invalid outputs or provider errors. Median decision latency was **207.28 ms**.

| Presentation | Correct |
| --- | ---: |
| Direct | 37/41 |
| Paraphrase | 36/41 |
| New contrasts | 8/9 |
| Retained utterance, including three expected deferrals | 9/9 |
| Retained dialogue | 3/3 |

The [case-level baseline record](right_action_intent/jev-baseline.json) retains the fixture digest, timing, score and choices. The full provider response capture was retained locally. Classifier accuracy is independent of workflow fulfillment.

## V2 supported-action cohort

**Registry ID** `buddy.right-action-intent.v2`

The [v2 fixtures](right_action_intent/cases-v2.json) revise twelve retained cases.
The current-page replacement includes a fixed page and one exact selected
sentence. The statblock save requests include the prior reviewed draft. Prompts
use the user's intended operation, such as inspecting the creatures already in
an encounter or continuing play along the selected negotiation outcome.

The [parked case ledger](right_action_intent/parked-v2.json) records 14 cases
excluded from v2 scoring and why. The v1 fixtures and baseline stay frozen.
The v2 menu has 37 choices. The same ordered menu applies to every v2 case.

```bash
python -m evals.right_action_intent.run --suite evals/right_action_intent/cases-v2.json --validate-only
python -m evals.right_action_intent.run --suite evals/right_action_intent/cases-v2.json --credential-file /path/to/.env --output /path/to/jev-v2.json
```

[Jev 1.14.0 v2 results](right_action_intent/jev-baseline-v2.json) are **86/89**
at **192.61 ms** median. Two wrong choices remain, on correcting an occurrence
before extraction and staging a Play scene edit. The pinned editor case returned
the expected action with equal top probabilities for current-page edit and Play
edit. The shared scorer counted that tie as invalid.

| Comparison | V1 | V2 |
| --- | ---: | ---: |
| Whole cohort | 93/103 | 86/89 |
| Same case IDs | 84/89 | 86/89 |
| Identical fixture input and Gold | 77/77 | 76/77 |
| Revised fixtures | 7/12 | 10/12 |

The v1 median was 207.28 ms on 103 cases. The cohort and menu changed together,
so these runs establish separate baselines. They do not isolate an effect of
wording, input context, or menu changes on accuracy or latency.
