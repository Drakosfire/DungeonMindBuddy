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

## Surface-menu probe

The [nine fixture cases](right_action_intent/surface-probe.json) pin Build or
Plan and the exact selection for in-place edit cases. Each case explains the
expected label. Preflight fails if the catalog cannot offer that label or the
selected text does not occur exactly once. Both arms derive their menu from
the product catalog. The full arm adds distinct actions from the other tested
surface while preserving local labels, definitions and order. The fixture,
instruction and model are identical within each pair.

```bash
python -m evals.right_action_intent.scope --validate-only
python -m evals.right_action_intent.scope --credential-file /path/to/.env --output /path/to/new-directory
```

On the updated runtime menu, Jev 1.14.0 scored Build 4/4 and Plan 5/5
in both arms. The earlier probe with the 18-choice Build catalog found
a Plan clarification error in the full arm. After the Build catalog
dropped five actions owned elsewhere, the combined menu also changed.
The small sample does not establish a latency trend. See the current
[pair results](right_action_intent/surface-probe-jev.json) and
[exact menus and prompt](right_action_intent/surface-probe-pin.json).

This probe uses the Build and contextual Plan menus. Play conversational routes
currently enter through a retrieval controller, so they still need an ordinary
first intent boundary and corresponding fixtures. An action's classification
here does not establish that its surface can carry it through.
