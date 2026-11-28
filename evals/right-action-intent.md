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

### Expanded Build and Plan comparison

The [expanded cohort](right_action_intent/surface-cohort.json) contains 43
cases, 36 Build and seven Plan. Nine pairs were reused with matching inputs,
menus and model. The [v2 disposition](right_action_intent/surface-cohort-v2-disposition.json)
accounts for all 89 v2 case IDs. It admits 32 cases and records why the other
57 await a different intent route, operator boundary or distinct source choice.
The remaining 11 cases are the nine original surface fixtures and two explicit
cross-surface comparisons.

| Surface | Full menu | Scoped menu |
| --- | ---: | ---: |
| Build | 33/36 | 32/36 |
| Plan | 7/7 | 7/7 |

Build's additional miss was the “Playful.” follow-up after the user requested
a draft and Buddy asked about tone. The full menu selected a chat draft and
the scoped menu selected discussion. Both arms also missed the same three
Build requests for a chat revision, a connected page, and saving a previously
reviewed statblock. See the [case and action-level evidence](right_action_intent/surface-cohort-jev.json).
The combined arm uses the union of the available Build and Plan menus, so it
does not establish performance against an all-surface menu.

### Surface coverage and dispatch boundaries

The [canonical action catalog](plan-authoring-benchmark.md#action-catalog)
records workflow capabilities and their strongest evidence. The table below
records which of those choices this benchmark can measure at the first
decision. It accounts for every surface ID in the
[agent turn request](../apps/live_control_server/models/agent_turn.py).

| Surface | First decision or operator boundary | Benchmark disposition |
| --- | --- | --- |
| Build | The [native Build owner](../src/application_state/agent_conversation/build_intentional_response.py) offers the scoped requested-work ballot. Specific proposal, review and save paths have their own authority. | 36 intent cases. Edits that refer to selected text pin the page and exact selection. |
| Plan | The [Plan harness](../apps/live_control_server/services/plan_jev_harness.py) uses a contextual opening. It can assemble more than the requested-work question, depending on the Plan request. | Seven cases measure the requested-work menu. Exact parity with the whole opening request still needs separate evidence. |
| Play | The [Play harness](../apps/live_control_server/services/play_jev_harness.py) sends the shared intent menu. Live scene revision goes through the [Play proposal control](../apps/live_control_server/routes/play_runs.py). | Discussion, lookup, clarification and handoff cases. Scene-edit intent scores referral to review. |
| Index | The [Index composer](../apps/live-control-ui/src/agentInteraction/IndexAgentConversation.tsx) submits an ordinary conversation turn with no work object and no Graph request. The [runtime selector](../apps/live_control_server/services/agent_turn_service.py) routes it to Hermes. | The [ordinary HTTP test](../tests/test_agent_turn_route.py) verifies a conversation-only Hermes dispatch, with a simulated host, an empty tool menu, and no Graph scope. Paired Jev scoring requires an Index intent route. |
| Ingest | The [Ingest surface](../apps/live-control-ui/src/ingestSurface/MemoryIngestPage.tsx) presents operator review and publication controls. A selected-knowledge conversation uses a distinct input contract in the agent turn request. | Score review and publication in workflow benchmarks. Qualify the selected-knowledge conversation separately before giving it an intent menu. |
| Combat | [Encounter creation, inspection and mechanics adoption](../apps/live_control_server/routes/combat_encounters.py) use explicit operator endpoints. | Score these controls as workflow steps. A Play request to switch to Combat can be scored as a handoff. |

[Image generation](../apps/live_control_server/routes/media_images.py) is an
Image Studio operator action. Build can choose to prepare an image direction.
That choice earns credit for preparation only.

### Play discussion and evidence lookup

The current surface cohort adds four Play intent cases. The ordinary Play
owner checks verify a single candidate-free intent request, a conversational
reply, an explicit Rules lookup, and exact replay. Explicit preselected source
references still use their established route. Edit and destination handoffs
remain unqualified for Play fulfillment.

| Surface | Combined menu | Scoped menu |
| --- | ---: | ---: |
| Build | 29/36 | 33/36 |
| Plan | 7/7 | 7/7 |
| Play | 4/4 | 4/4 |

The [new paired capture](right_action_intent/surface-cohort-play-jev.json)
pins all 47 cases and reports by action. The earlier Build/Plan result used
its 43-case ancestor and a different combined menu. Keep the records separate.

### Play clarification and edit handoffs

Three cases pin Play and the current scene title. They ask for clarification,
an edit to a named Build page, or a change to the current Play scene. The two
edit cases distinguish a cross-surface handoff from a handoff to the existing
Play scene review control. Neither case scores a saved edit.

The [50-case paired capture](right_action_intent/surface-cohort-play-handoff-jev.json)
reuses all 47 prior pairs with the same model, instructions, menus and case
state. Clarification and the current-scene handoff passed in both arms. Both
arms chose the current-scene edit for the named Build page. Keep this as a
classification miss. The requested destination, active surface, and current
scene were explicit.

| Surface | Combined correct | Scoped correct | Combined median | Scoped median |
| --- | ---: | ---: | ---: | ---: |
| Build | 29/36 | 33/36 | 211.01 ms | 189.38 ms |
| Plan | 7/7 | 7/7 | 186.91 ms | 188.30 ms |
| Play | 6/7 | 6/7 | 271.90 ms | 217.37 ms |

The Play timing mixes reused calls with the new cases and does not establish
a latency change in ordinary Buddy. The ordinary Play tests exercise the
serialized opening menu and the response path using simulated provider outputs.

#### Play request parity

The [runtime-request comparison](right_action_intent/surface-cohort-play-runtime-jev.json)
runs the same seven Play fixtures with the ordinary Play request builder.
The scoped arm uses its request unchanged. The combined arm replaces only
the options and their descriptions. The previous paired run used the generic
benchmark instruction, which named an unavailable deferral label, so this
comparison needed fresh calls.

Both arms again passed 6/7 and misclassified the explicit Build edit as a
current-scene edit. The mismatch persists with the actual Play instructions.
Median decision wall time was 278.32 ms combined and 179.78 ms scoped on
these seven pairs. This small sample measures provider decisions only.

#### Play destination wording experiment

The [treatment record](right_action_intent/surface-cohort-play-destination-jev.json)
keeps the seven development fixtures, model, question, labels and option order
fixed. It changes only two descriptions. A Play edit targets the current live
scene. Work targeting another surface or a separate operator control is a
handoff. Reproduce with the scope runner using `--surface play --play-destination-wording`.

Both arms improved from 6/7 to 7/7. Both recovered the explicit Build edit
handoff, and both retained the current-scene edit choice. Median decision
time was 311.78 ms combined and 177.90 ms scoped. The treatment was designed
after observing the Build handoff miss. It needs fresh destination contrasts
before a runtime adoption decision.

The [held-out comparison](right_action_intent/play-destination-holdout-jev.json)
was frozen at `ecea160a8504` before calling Jev. All eight fixtures pin Play
and a live scene. Run using `--surface play --tier play_destination_holdout`,
with and without `--play-destination-wording`.

| Wording | Combined correct | Scoped correct | Combined median | Scoped median |
| --- | ---: | ---: | ---: | ---: |
| Current | 6/8 | 7/8 | 253.70 ms | 182.62 ms |
| Treatment | 6/8 | 6/8 | 227.90 ms | 217.86 ms |

The scoped treatment fixed the Plan edit handoff but classified both the
Combat handoff and the ambiguous request as current-scene edits. The combined
treatment fixed the Build edit handoff but missed Combat and still missed
the Plan edit. Retain the current runtime wording. The development improvement
did not generalize to the held-out cases.

#### Contextual Plan wire control

The [ordinary synthetic Plan capture](right_action_intent/plan-contextual-ordinary-wire.json)
is from the existing ambiguous-placement test with a simulated Jev transport.
The first two requests have three questions each: page-edit intent, placement
relation and existing scope. The third has twelve questions, including
requested work, placement, a candidate vote and retrieval disposition. It
also receives the earlier page-edit intent. The seven paired Plan cases
measure requested work in isolation. Treat this capture as the control for
a future intent-first Plan route.

The first request contains no source candidates. The current Plan harness
still acquires explicit references and starts request-owned source discovery
before dispatch when the relevant authorities are available. The opening
admission validator requires settled discovery in the prefix. Moving source
work later therefore needs a coordinated change to orchestration and
admission, with replay coverage for the earlier ordering.

#### Reuse captured results for analysis

Run `python -m evals.right_action_intent.scope --summarize <capture.json>`
to analyze retained paired results without contacting a provider. The
report includes dispositions and median latency by surface, arm and expected
action. A correct clarification counts as a valid deferral. A clarification
where the pinned state establishes another action counts as an invalid
deferral. A tied top score is additional telemetry because Jev can still
return a selected action when scores tie. Provider failures remain separate
from classification errors.

The retained 50-case comparison includes four valid deferrals per Build arm,
two per Plan arm, and one per Play arm. These are included in the correct
totals in the earlier comparison tables.

#### Build request parity

The [ordinary attached-source Build request](right_action_intent/build-attached-source-opening.json)
was captured at the SDK transport boundary with a simulated provider. It
verifies that the 13 requested-work choices match the shared Build catalog.
Buddy places the choice descriptions inside the question instructions and
sends a separate source-need question. The state gives the current page,
conversation and reference labels. Contextual edits can have further
questions. The 36-case paired comparison measures the shared choices
under a simpler single-question request. Use this capture when designing the
full Build request comparison.

A [single captured-wire pair](right_action_intent/build-ordinary-wire-paired-jev.json)
replayed this Build request through GenerationEngine and Jev. The scoped
request retained both original questions. The combined arm appended the union
of other applicable action choices and descriptions to requested work only.
Both chose discussion and marked the reference as sufficient to anchor the
turn. This is evidence about classification on one captured request. It
does not qualify actual source use or reproduce the 36-case quality change.

#### Intent-only Plan request experiment

The [seven-case Plan comparison](right_action_intent/plan-intent-only-paired-jev.json)
uses the shared intent-only request builder with the fixtures' supplied
surface and editor context. The only change between arms is the action
menu. Reproduce with `--surface plan --plan-intent-only`. The scoped menu
passed 7/7 and the combined menu passed 6/7, with two valid clarifications
in each arm. The combined menu chose a live Play scene edit for the
highlighted-sentence edit on the current Plan. Median decision wall time
was 295.23 ms scoped and 303.19 ms combined.

The shared builder already serves Play. The Plan trial evaluates the request
before product integration. The contextual Plan wire control above shows
the ordinary Plan sequence that still needs to change.

The [typed Plan projection comparison](right_action_intent/plan-minimal-intent-paired-jev.json)
freezes the exact model-visible state per case. The page title and selected
sentence remain visible. The complete fixture page stays local to validate
the selection. No placement or retrieval questions are sent. This reproduced
7/7 scoped and 6/7 combined on the same seven cases. Median time was 188.45 ms
scoped and 294.12 ms combined. This is a prototype decision comparison.
Ordinary Plan still uses the earlier dispatch sequence.

The runtime draft now sends the shared intent-only request first on
contextual Plan turns. Transport checks cover contextual and composed
Plan, including saved placement replay, ambiguity, stale and foreign
targets, and the discussion path that skips placement interpretation.
The historical wire capture records the earlier sequence. The paired Jev
study remains a decision comparison on pinned fixtures, with simulated
provider responses used to verify the ordinary runtime separately.

### Preserved baselines

The [v1 Jev result](right_action_intent/jev-baseline.json) scored 93/103.
The [v2 Jev result at its pinned revision](https://github.com/Drakosfire/DungeonMindBuddy/blob/09c682e732ac42875af70e592bc483019ed570fa/evals/right_action_intent/jev-baseline-v2.json)
scored 86/89. Both captures match the SHA-256 of their corresponding case
file. The checked v2 disposition accounts for all 89 IDs, with 32 reused
and 57 parked. The result counts describe different cohorts and should
not be used as a before-and-after accuracy comparison.

### Dialogue follow-ups

The [paired dialogue fixtures](right_action_intent/surface-dialogue-intent-jev.json)
use the native intent request builders. Each arm receives the same visible
conversation. One Plan turn confirms a specific replacement on the pinned
selection, and one Play turn asks about a hypothetical outcome in the
current scene. Both arms chose correctly on both cases. Reproduce with
`--tier dialogue_followup` and the appropriate surface, adding
`--plan-intent-only` for Plan.
