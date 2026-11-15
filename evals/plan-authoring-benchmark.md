# Plan authoring benchmark

Use ordinary Plan turns in isolated state. These cases test destination and
side effects, in addition to whether Buddy produces a useful response. Use the
existing Plan authoring contract and retained APP turn evidence. Keep the
assessment local.

## Cohort

| Case | Request and starting state | Required result |
| --- | --- | --- |
| PA01 — Sheep discussion | Replay exact turn `65f25721-cb00-4041-95a2-ecb57fedfbd7` from the private capture `experiments/plan-discussion-routing-20261027`. Restore the exact six prior dialogue messages in order, ending in the prior writing request, with the original Plan, draft and placement catalogue. | Answer in conversation. Zero page proposals, write reservations, insertion attempts or page mutations. The original `write_current_page/before:6` outcome fails even though dismissal restored the page. |
| PA02 — explicit page write | Use the neighboring retained Sheep writing control from the same handoff. Restore its own history and destination. | Stage exactly one editable proposal at the requested `before:6` boundary. Leave the saved page unchanged until explicit Save. Dismissal restores the draft. Preserve the original provider-outcome-unknown attempt separately from the later successful retry. |
| PA03 — editable drafts in conversation | From a saved Plan with an eligible page target, ask: “Draft two versions here in the conversation so I can edit and discuss them. Keep both here for review.” Give the turn prior page-writing history. | Present two separately reviewable drafts in the conversation. Verify they can be edited there. Zero page proposals, write reservations, insertion attempts or page mutations. If inline editing is unavailable, report that capability gap separately from routing and page integrity. |

PA01 and PA02 use the [retained Sheep evidence](../Docs/Plans/HANDOFF-PLAN-current-request-intent.md#current-evidence-and-diagnosis).
PA03 is a new contrast. The historical capture is private. Resolve the exact
turn and history locally, record the fixture digest, and mark results
unqualified if any original input is missing. A paraphrase or conversation
without the preceding writing request cannot qualify the historical case.

## Assessment

Take before and after snapshots of the draft and saved Plan. Inspect the
complete turn event sequence, proposal journal and UI surface **before any
dismissal or cleanup**. Record operation selection, reservation, proposal
creation, render destination, draft and saved-page changes, and reopen result.
A transient or subsequently dismissed page proposal fails either
conversation-only case. Missing action telemetry makes the negative result
unproven. For the positive control, inspect the staged placement first and
then record the result of Dismiss separately.

Score conversational fulfillment separately from side-effect integrity. A
reply that omits the requested drafts can pass the no-write check but fails
fulfillment. Retain failed attempts with their original outcomes. Use the
[Plan authoring owner tests](../tests/test_plan_jev_authoring.py) for
provider-free boundary checks and ordinary captured turns for routing and
surface evidence.
