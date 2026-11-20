# Semantic block authoring benchmark

Use these ordinary Buddy requests to test whether the writer chooses the right
block, whether the editor puts it in the right location, and whether the saved
revision preserves it. Run the suite before and after changing writing guidance.
Read Aloud in Approach to Edge Session Prep is the design reference. The fixtures
use synthetic content and disposable Worlds.

## Fixtures and runs

Create one disposable World with a saved Build page and a saved Plan. Each has
two sections titled Arrival and Departure. Arrival describes a maintained
boardwalk, a sealed tower, and three blue lanterns. Departure contains the
distinct sentinel sentence “The ferryman waits beside the red gate.” Seed
one titled Read Aloud callout, “First sight,” under Arrival, followed by a
normal paragraph. Keep an existing table and image elsewhere in each document.
Create a Play scene from the Plan through normal adoption and use a separate
clone for each Play case. Ingest a plain-text copy as retained source material
for the Ingest case. Capture exact saved and draft snapshots before each run.
Restore fixtures and begin a fresh conversation for independent repetitions.

Use normal text requests through each surface. The harness or operator supplies
the indicated selection or caret. Expected results stay outside model input.
Where a surface has multiple production writer routes, record the actual writer
and repeat with fixtures that reach each eligible route. An unavailable route
needs a recorded disposition. A fixture that missed a supported route is incomplete.

## Cases

| ID | Surface and setup | Request | Required result |
| --- | --- | --- | --- |
| B01 | Build, caret at end of Arrival | “Add what I should say to the players when they reach the boardwalk. Then give me a private reminder to wait for them to choose whether to approach the tower.” | One Read Aloud and one GM Note, in that order and in Arrival. Player-facing prose excludes the private reminder. |
| B02 | Build, select only the First sight block | “Make the description quieter and cut it to two sentences.” | Same block type and title with the revised body. Departure, table, and image stay intact. |
| B03 | Build, caret under Arrival | “Add two ordinary paragraphs about how the station maintains this road.” | Prose at the caret, with no callout. |
| P01 | Plan, caret under Arrival | “Add what the players see and hear at the boardwalk. Give me a private reminder to leave the tower sealed unless the players investigate.” | Read Aloud and GM Note with distinct contents. Exercise the grounded writer and the reviewed Plan writer wherever both are supported. |
| P02 | Plan, select the titled First sight block inside a marked scene | “Rewrite this to emphasize the three lanterns.” | Read Aloud kind and title survive. Scene identity, edges, and sibling content stay intact. |
| P03 | Plan, select a marked card body | “Add a private reminder that the guide waits at the gate. Leave the spoken material alone.” | A GM Note appears inside the selected body, with existing Read Aloud and protected markers preserved. |
| PL01 | Play, current editable scene | “Add something I can read to the players as they reach the boardwalk, then a private cue to pause for their response.” | The scene edit path proposes both callouts in the current scene before review. It preserves the committed Plan and neighboring scenes. |
| PL02 | Play, adopt the saved P01 Plan through the ordinary flow | “Read me the arrival passage from this scene here in chat.” | The scene shows the saved callouts. Chat returns the player-facing passage and omits the GM cue. No write is staged. |
| I01 | Ingest, retained fixture selected | “Draft the Arrival material on a new Build page. Include what I say to players and a private GM reminder.” | If the surface supports handing off authored proposals, verify the named Build destination and both blocks through save and reopen. Retained source bytes stay identical. Record unsupported capability explicitly. |
| G01 | Graph, fixture object selected | “Give me a passage to read to players when they see this tower. Keep it here in chat.” | Player-facing prose in chat, with no page proposal or graph mutation. |
| H01 | Home, no page selected | “Give me a short passage to read out when the party arrives at a sealed tower. Keep it here in chat.” | If chat is offered, player-facing prose in chat with no write. Otherwise record that Home has no eligible writer. |
| C01 | Combat Tracker, encounter open | “Add a read-aloud block to the current page about three lanterns coming on.” | If no page writer is offered, report the unavailable destination and verify no encounter mutation. If delegation is supported, require an explicit destination before staging a proposal. |
| X01 | Build and Plan, existing private note and spoken passage on page | “What would you change about the spoken passage? Brainstorm here and leave my page alone.” | Helpful discussion with zero page proposals, write reservations, or mutations. |
| X02 | Build and Plan, controls for supported block kinds | “Add a warning that the boardwalk is slippery.” Separately ask “Add a Rules callout containing only this supplied rule: travel pace is set by the GM.” | The requested supported callout has the correct meaning. For a surface without that kind, record its actual supported outcome. No invented official rule or unsupported marker. |

## Evidence and scoring

Use the [ordinary benchmark workflow](../Docs/Guides/ordinary-benchmark-workflow.md)
for retained turn evidence and the [Plan authoring benchmark](plan-authoring-benchmark.md)
for before and after state and action journals. Keep evidence private when it
contains raw prompts. The case table is a manual fixture manifest.

1. Capture the proposal before Apply. Mark routing, block kind, title, order,
   and body semantics separately. Require actual callout nodes or canonical
   semantic Markdown. A heading that says Read Aloud is a block-choice failure.
2. For positive writes, verify that the saved revision remains unchanged before
   Save. On an independent run, dismiss and compare with the original draft.
   On the acceptance run, Apply, inspect the real editor nodes, Save, reopen the
   exact revision, and confirm the collapsed/expanded reader preserves body text.
3. Compare content outside the requested target and protected identities before
   and after. Record exact destination and count any transient proposals on
   negative cases. A wrong target, spoiler in player-facing prose, unauthorized
   save, or dropped protected content is a hard failure.
4. Run a deterministic round-trip control with canned canonical Markdown through
   the same proposal and editor adapter. Report that result separately from live
   generation. A failed live case with a passing control points to routing or
   generation. A valid proposal that loses structure points to admission,
   placement, persistence, or rendering.
5. Run at least three live repetitions per supported writer route and report
   passes and failures by case and stage. Record exact source revision, writer
   route, model, prompt revision, and fixture identity. Keep service errors,
   unsupported capabilities, and missing evidence distinct. Use a blind human
   review for whether prose sounds natural aloud and whether GM-only information
   is separated. Compare against the baseline under the same conditions.
