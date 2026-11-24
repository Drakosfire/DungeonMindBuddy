# Semantic block writer observations

November 20, 2026. Three repetitions per prompt and writer, with synthetic
Boardwalk material on hosted Buddy release `22179520` and `gpt-6-luna`.
The candidate comparison used the shared prompt text from #4277 with the same
provider client and response schema. The serving application was left unchanged.

| Case | Writer boundary | Both canonical callouts before | Both after |
| --- | --- | ---: | ---: |
| B01 | Build system prompt and schema with a synthetic provider packet | 0/3 | 3/3 |
| P01 | Reviewed Plan caret proposal with the production prompt assembler | 3/3 | 3/3 |
| PL01 | Play scene system prompt and schema with a synthetic scene packet | 3/3 | 3/3 |

The three baseline Build responses all emitted Read Aloud. Two expressed the
private cue as bold prose, and one used `[!GM NOTE]`. The three candidate
responses used `[!GM-NOTE]` and kept the private cue outside Read Aloud.
Play retained its existing First sight title in all six samples.

Prompt SHA-256 before and after:

- B01: `9d2f3e7ee758a8ccc21cfeeaee9e1f148ee28e863f9143f2276a848ace45c4c9` and `095d7fed70c966215302117147556def310df234aa9b04dd1cdb2bb66f7639ce`
- P01: `d2aeab297a873b8bc0c9b58e72f19779c097208407a6c7949f10cd53f9378a48` and `8937222d94659eed7187f8db455c7c6dd275d3854182bebc30d1f2af57d68740`
- PL01: `53528005bf554f147904df41e8dcfaaec9d0a0e7eaa835a4c31385a7e6f81153` and `0b60f469e4b0d444032ded30c655720f92912584a15fdb3d01740c7c1392a2ad`

The Build deterministic Apply control separately preserved both titled callouts
and their distinct sentences through serialization and parsing, in order at
the end of the Arrival paragraph. The adjacent Departure section remained
intact. A mid-paragraph attempt was rejected by the existing save-safety guard.

Live routing, grounded Plan authoring, protected scene editing, save through
the mounted application and cross-surface negative controls are still pending.
The 5202 browser requires local Graph authorization. The local provider
returned HTTP 401 in isolation, and the disposable World's Play preparation
returned HTTP 409 because reviewed Graph publication is pending.

## Surface eligibility observations

- Home loaded on 5202 in the disposable World without a conversation composer.
  H01 has no eligible writer in that state.
- Combat Tracker displayed an unavailable local Graph session and no open
  encounter. C01 is incomplete.
- The fully prepared Play control Plan contains two marked scenes and both
  named callouts. The authenticated preparation endpoint returned 409 pending
  reviewed Graph publication. No run was created.

The [benchmark suite](../../evals/semantic-block-authoring-benchmark.md) defines
the outstanding acceptance cases. See [writer PR #4277](https://github.com/Drakosfire/DungeonMindBuddy/pull/4277) for the shared contract and Build regression.

## Hosted semantic block verification

Observed November 20, 2026 on Buddy release `1c19c89e1403a2a584c7e60ad1959f7ffd7935e1`. The Build and Plan runs used synthetic Boardwalk pages in Buddy Cloud Pilot. The matched writer samples and their limits are recorded in [#4279](https://github.com/Drakosfire/DungeonMindBuddy/pull/4279).

| Case | Hosted observation | Status |
| --- | --- | --- |
| B01 | Both canonical blocks appeared in the review and survived Save and reload. The original Arrival paragraph survived, and the private cue stayed separate. | One persistence pass. Full fixture, placement scoring, and repetitions pending. |
| P01 | The original wording returned both markers in chat. A fresh conversation with an explicit saved-Plan edit request produced both blocks in an inline suggestion. Both survived Save and reopening via the World picker. Departure text remained intact. | One persistence pass, placement failure. Blocks landed after Departure instead of under Arrival. |
| PL01 and PL02 | Plan-to-Play preparation reported that reviewed Graph publication is pending and disabled Start session from Plan. | No hosted Play run created. |
| G01 | Pilot Graph unavailable. | Object selection and chat-only check pending. |
| H01 | Hosted Home had no conversation composer. | No eligible writer in the observed state. |
| I01 | Hosted Ingest offered Open Build as its authoring entry point. | No proposal composer in the observed Ingest state. Retained-source control pending. |
| C01 | Combat Tracker reported pending Graph publication and had no open encounter. | Encounter destination and no-mutation checks pending. |

Plan's direct reload returned `owned_world_access_required`. Navigating through the top-level Plan route and choosing Buddy Cloud Pilot reopened the saved document. The two Plan edit-history reads independently returned HTTP 403 with `hosted_world_route_policy_unverified`. That response does not establish why placement fell outside Arrival.

The focused mounted Plan editor control passed. It staged, reviewed, saved,
and reloaded a canned canonical Read Aloud edit. This control exercised the
editor integration and did not test hosted model placement.

### Plan placement reproduction

On a fresh hosted conversation with the two-section fixture restored, the
browser caret was at offset 38, the last character boundary of the Arrival
paragraph. The retained proposal carried editor anchor and head 81, but its
resolved insertion was position 119 at root boundary 5, after Departure.
The preview showed both blocks at that boundary. Dismiss removed the
suggestion and retained the saved Arrival and Departure paragraphs.

The Plan decision packet already distinguishes the captured caret, named
section boundaries, and page end. The stored coordinates rule out loss of
the original selection and a later save-time relocation. A placement change
needs to preserve the versioned decision packet used to verify older turns.

### Build controls

- **B03:** Hosted Build returned two ordinary paragraphs without a callout.
  The preview appeared before Arrival in the initial and follow-up runs,
  which were dismissed. The retained follow-up review kept the writer's
  captured caret. The inline review card uses a visual anchor before the
  containing block. In the save-and-reopen run on `09631231`, both exact
  proposed paragraphs were saved immediately after Arrival. The existing
  Warning, Rules, Read Aloud, and GM Note remained present.
- **X01:** Hosted Build responded to the brainstorming request in chat and
  showed no page suggestion. The rendered saved blocks and save time matched
  their initial state. A subsequent read-only check found zero Build write
  reservations for the completed turn.
- **X01, Plan:** The first attempt hit an uncertain new-conversation command
  and admitted no turn. Reopening the existing synthetic conversation allowed
  the exact prompt to complete in chat with no page suggestion. The Plan
  Markdown matched before and after. The retained decision was `discuss`,
  with zero authoring reservations.

## Hosted Play and Combat follow-up

The [hosted extraction fix](https://github.com/Drakosfire/DungeonMindBuddy/pull/4291)
produced reviewable run `a979e5f6-89c8-4f93-bea4-6ec87320b2bf` on the synthetic
Boardwalk source. On release `ddfd7ea3`, the
[first Graph transport fix](https://github.com/Drakosfire/DungeonMindBuddy/pull/4294)
enabled publication of the four grounded locations and one grounded relationship
in Buddy Cloud Pilot. Review excluded the unsupported west-of relationship.

| Case | Observed in hosted Buddy Cloud Pilot |
| --- | --- |
| PL01 | A saved two-scene Plan started Play. Default chat returned proposed wording without a scene edit, including after an explicit request to edit. Selecting **Propose scene edit** and sending the exact benchmark prompt produced separate Read Aloud and GM Note blocks. Apply saved them to the session copy, and they rendered after reload alongside the original First sight block. The neighboring Departure sentinel remained readable. One live round trip. Additional repetitions and parent Plan revision comparison are pending. |
| PL02 control | A fresh Play session adopted First sight and a manually seeded private GM Note from an exact saved Plan. The benchmark chat prompt returned First sight, omitted the private cue, and showed no staged edit. The joined case with both blocks authored by Buddy in Plan is still pending. |
| C01 | The disposable Combat encounter reopened at saved revision 1. The surface offered no page-authoring composer or delegation control. The request was therefore ineligible for submission, and the encounter remained at revision 1. |
| G01 | On subsequent release `d7be68ed`, the pilot Graph explorer returned HTTP 503. Read-only checks against the same database found that the active binding points to the committed classic Graph revision, while the native repository used by the explorer has no head for that World. Object selection and the Graph chat control remain pending. |

The deployed [Build body rewrite fix](https://github.com/Drakosfire/DungeonMindBuddy/pull/4286)
preserved the Read Aloud kind and title and the neighboring GM Note in two
hosted saves and reloads. One stored selection excluded the final period despite
the visible selection including it, which left duplicate punctuation after
the rewrite. The second run captured all 119 selected characters and saved
the exact two requested sentences. The earlier capture mismatch remains open.

### Hosted additive Play rerun and Ingest control

- **PL01 before #4299, release `d7be68ed`:** On the synthetic Arrival scene
  with two existing callouts, the exact benchmark prompt rewrote both callout
  bodies and dropped the opening paragraph. The proposal was left unapplied.
- **PL01 after [#4299](https://github.com/Drakosfire/DungeonMindBuddy/pull/4299),
  release `f84b93e7`:** The same Play session and exact prompt produced two
  separate callouts, Read Aloud **At the boardwalk** and GM Note **Pause for
  response**. After Apply, the session reported Saved. Reopening the same run
  rendered both new callouts. All original Arrival paragraphs matched exactly
  and in order, including the bodies of **First sight** and **Private
  benchmark cue**. Both titles and the red-gate choice remained present. The
  Departure card still showed its sentinel sentence. This is one matched
  rerun. Further repetitions and a parent Plan revision comparison are pending.
- **I01, release `d7be68ed`:** Reopening exact extraction run
  `a979e5f6-89c8-4f93-bea4-6ec87320b2bf` in Buddy Cloud Pilot Ingest showed
  the same revision 5 source text, its two saved callouts, and five accepted
  Graph changes. No authoring composer or delegation was offered in the review,
  so the request was ineligible for submission. After later Build edits, the
  retained extraction source still matched all 237 UTF-8 bytes and the
  SHA-256 digest of the original immutable content revision. Workspace
  revision 5 identified the extraction input, and content revision 4 stored
  its matching bytes.

### Hosted Plan selected-callout rewrite

On release `f84b93e7`, the P02 fixture in Buddy Cloud Pilot had a marked
Arrival scene, the titled **First sight** Read Aloud, a private GM Note,
the red-gate choice, and the sibling Departure scene. The editor selection
was confirmed by copying the exact First sight body before opening the
composer. The ordinary Send request was “Rewrite this to emphasize the
three lanterns.”

The proposal retained Read Aloud and the First sight title. A read-only check
of the retained opening decision confirmed `write_current_page` with the
captured replacement target. The selected text matched the complete First
sight body at positions 143–186, and the original and resolved capture
digests matched. The review card appeared above the original, which remained
visible while the proposal was pending. The card position does not establish
where Save applies the change.

The proposal included the host's partial-retrieval disclosure as editable
text, which fails document-content isolation. It was dismissed before Save.
The original passage, private note, and Departure sentinel remained visible.
A follow-up on `09631231` selected the same exact body and used the same
P02 prompt. The proposal contained a replacement sentence and the host
disclosure. The operator removed the disclosure in the suggestion editor
and verified that it was absent before Save. Reopening the Plan through its
World route showed the new sentence inside the original titled **First
sight** Read Aloud, with the original sentence and disclosure absent. The
red-gate option marker and Departure sentinel remained present. This
verifies replacement persistence after manual cleanup. Clean proposal
generation remains open.

A fresh P01 run against saved Plan revision 5 retained the original editor
capture and offered 17 placements. Its opening decision selected `clarify`
with no placement. The turn completed with a player-facing passage and a
private cue in chat, with no page proposal. This run failed at routing before
placement or persistence could be scored. A prior exact P01 run selected
`write_current_page` with `under:1`, which shows that the same request can
reach the authoring branch on a different fixture state.

[Plan placement PR #4264](https://github.com/Drakosfire/DungeonMindBuddy/pull/4264)
covers selection binding and keeping retrieval disclosure in conversation.
A hosted P02 rerun still needs to prove exact replacement, save and reopen
on the same fixture.

### Hosted Play repetition results and remaining surface coverage

Two fresh Play sessions from the saved synthetic Plan passed the same PL01
prompt after the first matched rerun. This makes three observed save-and-reopen
passes after #4299. In each pass, the two new callouts rendered separately,
existing Arrival paragraphs matched exactly and in order, the original callout
titles and red-gate choice remained present, and the Departure card retained
its sentinel sentence. The two fresh sessions used Play's scene edit mode.
They confirm session-copy persistence with manually seeded Plan callouts.
A read-only comparison of all three stored run editions verified that each
pinned immutable parent Plan revision 5 with its matching content digest and
saved the edit as session-copy revision 1. The new Pause for response note
appeared only in the edited copies, and no parent Plan revision matched any
edited session digest. The later hosted table pass is recorded below. The hosted
artwork check is recorded below.
The separate adoption diagnostic below covers reviewed agent-authored blocks.

A fresh hosted Play run in Buddy Cloud Pilot
(`2918d339-782b-470e-9df5-51e51f50cb1f`) started from Plan version 9. A two-column
table was saved to session-copy revision 1. The exact PL01 prompt in
**Propose scene edit** mode produced **Read Aloud · Arrival** and **GM Note ·
Pause**, with the table visible in review. After Apply and reload, both
callouts and the original table rendered. Removing only the two additions
from the reopened revision 2 Markdown reproduced revision 1 exactly,
including the table, original scene text, choice and Departure scene. This
check exercised a table and did not include an image.

The same synthetic run then saved a privately retained boardwalk illustration
to session-copy revision 3. Image Studio reported a fetch error after
generation, but the image was available in its library and could be placed
without regeneration or public CDN upload. A reviewed scene-edit request
added **Read Aloud · Lantern reflection** and **GM Note · Wait at the rail**.
After Apply and reload, both blocks, the table, and the 1,024-pixel image
rendered in revision 4. Removing only the two new blocks from reopened
Markdown reproduced revision 3 exactly, including the artwork reference,
scene text, choice, and Departure scene.

Hosted Home showed no conversation composer in Buddy Cloud Pilot, so H01 had
no eligible writer. Hosted Graph still reported unavailable native readback
and disabled object selection in the pilot. G01 requires a disposable native
Graph where the fixture object can be selected.

### Hosted Plan-to-Play adoption diagnostic

An explicit request to edit the synthetic Plan in Arrival produced two
canonical callouts, Read Aloud **Boardwalk** and GM Note **Tower**. The draft
also contained the host retrieval disclosure, which was removed manually
before Save. The blocks were saved before the opening paragraph, one
paragraph earlier than requested. This diagnostic leaves ordinary P01
routing, placement, and clean proposal generation open.

The document-specific Plan reload returned `owned_world_access_required`.
Reopening through the World-scoped Plan entry recovered the saved blocks.
Starting Play from that saved Plan carried both authored callouts, the
previous callouts, the red-gate choice, and the Departure sentinel into
a fresh session. The exact PL02 chat request quoted **Boardwalk**, omitted
both private notes, and staged no scene edit. This checks adoption and the
chat-only boundary after the manually reviewed save.

The separate deterministic Play control in
[#4309](https://github.com/Drakosfire/DungeonMindBuddy/pull/4309) verifies that
both titled additions, a sibling table and image reference, and the exact
parent Plan record survive session-copy Save and readback. The separate hosted artwork run above verified rendering after reopen.

### Hosted Build Warning and Rules controls

On release `f84b93e7`, the exact X02 Warning request produced a **Read
Aloud** titled Boardwalk warning. The Rules request used the unsupported
`[!NOTE]` marker inside a blockquote. Both proposals were dismissed.

On release `09631231`, which includes
[#4314](https://github.com/Drakosfire/DungeonMindBuddy/pull/4314), the same
requests produced actual **Warning** and **Rules** blocks. The Warning
saved at its proposed location. The Rules body contained only the supplied
sentence. The editor rejected the proposed Rules insertion as unsafe;
moving it to the boundary after the Arrival paragraph let it save.
Both blocks, the original Arrival paragraph, and the existing callouts
remained visible after reopening the saved Build page. This verifies
block choice and persistence in one live repetition per kind. Safe
automatic Rules placement and equivalent Plan runs remain open.

### Hosted Plan Warning and Rules controls

On release `09631231`, both exact X02 requests completed against the
synthetic Plan with an original editor capture.

| Case | Retained decision | Observed result |
| --- | --- | --- |
| Warning | `clarify`, no placement | Buddy returned a warning in chat. No editable callout was staged. |
| Rules | `write_current_page`, captured placement | The editable suggestion had a canonical Rules block containing only the supplied rule. The host retrieval disclosure also appeared as a separate editable paragraph. |

The Rules suggestion was dismissed before Save. The saved Plan still
showed its original callouts, red-gate choice, and Departure scene. This
confirms block choice for the Rules proposal. Clean save and reopening,
and routing the Warning request to the page, remain to be verified.

### Hosted Plan card-body save and native Graph fixture checks

The exact P03 prompt on the focused Arrival card produced **GM Note ·
Gate**. The retained application identified a playable-body replacement.
After Save and reopening, the note, existing First sight block, scene and
choice markers, and Departure text were present. The proposal included the
retrieval disclosure. An attempted deletion in the suggestion editor did
not reach the saved application. A read-only inspection confirmed the
footer was absent from the original capture and present in the review
Markdown and applied revision. The footer was subsequently removed through
the synthetic Plan Markdown editor and verified absent on reopen.

[#4320](https://github.com/Drakosfire/DungeonMindBuddy/pull/4320) verifies that
a direct editor transaction followed immediately by Save passes the edited
Markdown into the review command. It uses mocked persistence. The hosted
keyboard-path discrepancy remains open, as does a clean, unassisted P03 run.

The mounted native first-World HTTP publication test passed locally with
Buddy's pinned DungeonMind Core source and an isolated pgvector database.
It exercises hosted ownership, publication, and signed recovery. The cloud
release still uses classic first-World publication. The local test does not
supply the disposable native Graph or exercise the hosted G01 chat case.

A later read-only capability check used the existing hosted Elderwyld native
Graph on release `096312313`. The explorer loaded 3,012 objects. Selecting an
object through Find opened its details, and its action menu offered no chat
composer. The Graph workspace had no conversation launcher. G01 was therefore
ineligible for submission on that hosted surface. No prompt was sent and no
Graph update was attempted. This provides capability evidence on a loaded
native Graph independently of the Pilot Graph availability failure.

### Hosted Build selected-callout rewrite with artwork

A fresh Buddy Cloud Pilot Build page
(`b7d7d0c2-b01c-4e5e-94c2-b6e55e2e410d`) was saved and reopened with a
three-sentence Read Aloud titled **First sight**, a table, neighboring
Departure text, and the private boardwalk illustration used for Play.
Selecting the whole callout body and sending the exact B02 prompt produced
two quieter sentences in a replacement preview. After Save and reload, the
new body was present in a Read Aloud still titled **First sight** and the old
body was absent. The original table headers and cells, Departure sentence,
and rendered 1,024-pixel illustration were present after reopening.

### Plan placement controls on the staged source

On November 22, 2026 UTC, two focused pytest runs used Buddy
`774aa06344eb0a9411855eccdc7e33e7fead89c4`, the DungeonMind Core pin
`34032dc83a873b77e07eac0a397b9fe7ae682086`, and synthetic fixtures on
the disposable local PostgreSQL service. Both runs completed without
calling a model. The initial sandboxed run could not connect to that
service, so its 14 setup errors provide no behavioral evidence.

| Selected checks | Result | What they prove |
| --- | --- | --- |
| `rules_fragment_excludes_host_status or bound_selected_rewrite or under_heading or unresolved_relation_retains_anchor` in `test_plan_placement.py` and `test_plan_contextual_targets.py` | 14 passed | Scripted proposal text excludes the host retrieval status. Placement stays inside the intended section, and incomplete location or missing selection cannot silently authorize the edit. |
| `survives_dispatch_decision_sql or reader_fence_refuses_older_application or current_native_caller_v2_paragraph_proposal` in `test_plan_placement.py` | 8 passed | The placement catalog survives database readback. A scripted proposal follows the explicit Save boundary, and the reader fence rejects older code and downgrade. |

The serving image was observed at `84df46088596fd45771b12158fa62c4500be102d`
and lacked the new placement code. The staged source results can guide the
next run. They leave live model choice, hosted rollout, and the combined
two-block save and reopen case unverified.

### Remaining live benchmark evidence

| Cases | Next evidence to collect |
| --- | --- |
| Build B01, B02, B03 and X02 | Complete three independent repetitions for each supported path with the protected fixture. Score exact placement separately from block choice. Check that Rules saves at the requested boundary without manual movement. |
| Plan P01, P02, P03 and X02 | Run P01 by ordinary Send through each supported Plan writer, with a caret under Arrival. Verify role separation, accepted placement and no retrieval footer. For P02 and P03, capture title, scene and choice markers before the request, and compare them after clean Save and reopen. Rerun both X02 cases. |
| Play PL01 and PL02 | Keep the three PL01 scene-copy passes and the separate artwork evidence. Repeat PL02 from the clean P01 result and verify no private cue or staged edit in chat. |
| Build and Plan X01 | Repeat the discussion controls from fresh conversations and compare proposals, reservations and saved revisions. |
| Home H01, Ingest I01, Graph G01 and Combat C01 | Record the observed surface capability when it offers no eligible writer. If a newer release exposes an eligible path, run the exact prompt and check its destination and unchanged unrelated state. |

Use the [benchmark suite](../../evals/semantic-block-authoring-benchmark.md)
for the fixture, exact prompts and scoring. Keep deterministic checks,
live authoring repetitions, and surface eligibility observations separate.

### Hosted ordinary Send follow-up

These runs used synthetic pages in Buddy Cloud Pilot. Each exact prompt ran
in a fresh conversation. Some fixtures contained earlier benchmark blocks
and edits, so the runs do not form a clean matched three-repetition set.

| Case | Live result |
| --- | --- |
| Build B01 | The reviewed proposal contained a Read Aloud and a separate GM Note. The spoken text omitted the private cue. Save and direct reload kept both blocks immediately after the Arrival paragraph, along with the existing First sight block, table, Departure text, and rendered artwork. |
| Build B03, serving revision `03055f24` | The suggestion contained exactly two ordinary paragraphs. Save and reload placed them immediately after the Arrival paragraph. Removing only the two additions from the rendered workspace comparison reproduced the pre-send view. |
| Build X02, serving revision `03055f24` | Separate Rules and Warning requests produced their corresponding blocks. The Rules body contained only “Travel pace is set by the GM.” Both were saved at the boundary after the Arrival paragraph without moving either suggestion. After each reload, removing the new block from the rendered comparison reproduced the prior workspace, including the table, Departure, and artwork. |
| Build and Plan X01 | Both replies stayed in chat with no visible proposal. Each rendered workspace and Saved timestamp matched its own baseline. This browser observation leaves server-side write reservations unverified for these repetitions. |
| Plan P01 | Ordinary Send eventually showed an editable Read Aloud and GM Note with no retrieval disclosure in the suggestion. Both survived explicit Save and reopening through the World picker. The blocks landed at the start of Arrival, before the target paragraph. The existing choice and Departure text survived. Direct reload still returned `owned_world_access_required` on the serving release. This is a persistence pass and a placement and direct-reopen failure. |

The Plan X01 reply completed even though the browser showed
`hosted_world_route_policy_unverified`. The two denied legacy action history
reads are addressed in [#4392](https://github.com/Drakosfire/DungeonMindBuddy/pull/4392).
The separate 403 on direct Plan entry came from the Build document record
route. [#4394](https://github.com/Drakosfire/DungeonMindBuddy/pull/4394) switches
hosted Plan links to the existing owned Plan snapshot route. Both fixes were
merged and staged on serving-line candidate `8e057a04`. The table records
behavior observed before their cutover. It leaves their hosted verification,
correct ordinary Plan placement, and the remaining independent repetitions
open.

### Hosted Build clean B01 placement and persistence

On serving revision `03055f24`, a clean synthetic Arrival and Departure
page in Buddy Cloud Pilot contained one Arrival paragraph, one Departure
paragraph, and a two-column table. It had no artwork or earlier callouts.
I verified the caret by copying the final six characters of the Arrival
paragraph (`reeds.`) and collapsing the selection to its end. I sent the
exact B01 prompt in a fresh conversation.

The proposal contained a titled Read Aloud followed by a GM Note. The
private instruction to wait for the players' decision appeared only in
the GM Note. After Save and a direct reload, the rendered document order
was Arrival heading, the intact original paragraph, Read Aloud, GM Note,
Departure heading, the intact Departure paragraph, and the unchanged
table. The page showed Saved. This is one clean placement and persistence
pass. The illustrated fixture above covers artwork preservation separately.

Two discrepancies remain. The review displayed the proposal above the
Arrival paragraph even though Save placed it below. After Save, the page
briefly asked to check the insertion despite showing Saved. That prompt
was absent after reload. An earlier attempt in the same narrow viewport
used the End key without verifying the caret and split a word in the
Arrival paragraph. The synthetic fixture was restored before the scored
run. That earlier attempt provides no paragraph-end placement evidence.

### Hosted Play chat after adopting the ordinary Plan result

On serving revision `03055f24`, starting Play from a stale open Plan tab
reported that the selected Plan no longer matched its verified saved
revision. Opening the World-scoped Plan route loaded the current saved
document and allowed the normal Start session from Plan flow.

The new Buddy Cloud Pilot session adopted the ordinary P01 output
**At the Boardwalk** and its **Tower** GM Note. Arrival retained the older
callouts and red-gate choice, and Departure was still available. The
adopted source includes prior benchmark work, and the P01 blocks still
precede the intended paragraph. This run therefore checks downstream
adoption and chat without closing the clean Plan placement case.

The exact PL02 request ran once in a continued World conversation and
once in a fresh one. Both replies quoted **At the Boardwalk** and omitted
the Tower instruction, lantern signal, and gate cue. Both displayed the
literal `[!READ-ALOUD]` marker in chat. The fresh turn briefly showed a
reply-details mismatch during generation and then completed. Refreshing
the visible scene-proposal panel showed no edit. Arrival's rendered text
was identical before the requests and after direct Play reload, and
Departure remained selectable. Server-side edit reservations were not
independently inspected.

### Hosted Build protected fixture checks

Both checks used serving revision `03055f24` and fresh conversations in
Buddy Cloud Pilot.

- **B01, protected Arrival fixture.** A separate saved page contained the
  titled First sight Read Aloud, the ordinary Arrival and Departure
  paragraphs, a table, and the retained boardwalk illustration. The fixture
  was reopened before Send. The clipboard confirmed the last six characters
  of Arrival (`reeds.`) before collapsing the selection to the paragraph
  end. Ordinary Send proposed one Read Aloud followed by one GM Note. Only
  the GM Note told the GM to wait for the players' choice. Save and direct
  reload left both blocks immediately after Arrival and before Departure.
  Removing just those two blocks from the rendered comparison reproduced
  the entire baseline, including First sight, the table, Departure, and the
  1,024-pixel illustration.
- **B02, existing illustrated fixture.** The clipboard matched the complete
  First sight body, including its closing punctuation. The request produced
  two quieter sentences. Save and direct reload preserved the Read Aloud
  kind, First sight title, table, Departure sentence, and loaded artwork.
  Substituting the original passage into the comparison reproduced all
  top-level rendered blocks. This was a fresh turn on a fixture that already
  had benchmark edits, so it does not count as a clean matched repetition.

The hosted build still showed Check insertion briefly after a successful
Save. The B01 fixture also showed an artwork insertion inspection warning
during setup. Direct reload confirmed the artwork was retained before the
benchmark began. The remaining independent repetitions are open.

### Hosted Build ordinary prose, Warning, and Rules controls

On serving revision `03055f24`, each run used a fresh conversation and a
verified insertion point after the Arrival paragraph on the protected
illustrated Pilot fixture. Earlier synthetic benchmark blocks were already
present. Each comparison used the state immediately before its own Send.

- **B03.** The review contained two ordinary paragraphs and no new callout.
  Save inserted them at the intended boundary. The browser then reported a
  fetch failure, and Check insertion could not reconcile the retained draft.
  The conflict viewer showed identical Markdown in the browser draft based
  on version 4 and saved version 5. Opening the saved version showed each
  paragraph exactly once. Removing the pair from the rendered comparison
  reproduced the prior page, including the previous callouts, table,
  Departure, and artwork. This verifies placement and persistence through
  recovery. It leaves the clean Save acknowledgment failing on this release.
  [#4407](https://github.com/Drakosfire/DungeonMindBuddy/pull/4407) adds exact
  commit retry for a lost transport response. Hosted verification is pending.
- **X02 Warning.** The exact request produced one Warning with the sentence
  “The boardwalk is slippery.” Save and direct reload kept it at the boundary.
  The remaining rendered page matched the pre-send comparison.
- **X02 Rules.** The first request stopped before proposing a change and
  left the rendered page and Saved timestamp unchanged. A fresh independent
  conversation with the same prompt produced one Rules block containing
  only “Travel pace is set by the GM.” Save and direct reload retained it
  at the boundary, with the Warning and all other rendered content intact.
  The interrupted turn remains a failed repetition.

### Hosted Build and Plan discussion-only controls

On serving revision `03055f24`, the exact X01 prompt ran in fresh Pilot
conversations on both surfaces. Both replies suggested revised wording in
chat. No page suggestion appeared.

- Build used a separate illustrated fixture. The saved First sight Read
  Aloud was immediately followed by a GM Note containing “Wait for the
  players to choose.” The rendered content and Saved timestamp matched their
  baselines after direct reload, including the table and loaded artwork.
- Plan reused the existing benchmark Plan, which already had several
  callouts, a seeded private cue, the red-gate choice, and Departure.
  The full Markdown editor value and Saved timestamp matched before and
  after the reply. Reopening through the World route returned identical
  Markdown, including the scene identities and choice markers. The old
  history warning `hosted_world_route_policy_unverified` still appeared.

These are observable chat-routing and no-change checks. Server-side write
reservations were not independently inspected. The reused Plan is not a
clean matched fixture repetition.

### Hosted checks after the Actions deployment

On November 22, [Actions run 45059452118](https://github.com/Drakosfire/DungeonMindBuddy/actions/runs/45059452118)
activated revision `cda681c1ac4250343217b4ac7133889643a3f6e8`. The serving
container was healthy, public readiness returned 200, and the live application
schema remained `20261120_0170`. All fixtures below were in Buddy Cloud Pilot.

- **Plan direct reopen and history.** A fresh tab opened the exact saved
  Plan deep link while signed in. Arrival and Departure rendered, including
  the existing Read Aloud and GM Note blocks. Opening the composer loaded
  the saved discussion without the previous history warning. This checks
  reopen and history. The 0172 placement benchmark is still separate.
- **PL02.** Reopened the same synthetic Play run directly and started a
  fresh conversation. The exact chat-only prompt produced a saved-scene
  excerpt with a readable Read Aloud label and the At the Boardwalk passage.
  The reply omitted the private tower, lantern, and gate cues. Refreshing
  the scene-proposal panel showed no staged edit. This is an observable
  no-proposal check. Server-side edit reservations were not inspected.
- **B01.** On the illustrated synthetic fixture, verified a collapsed
  selection at the final character of the Arrival paragraph. The exact
  prompt previewed Read Aloud followed by GM Note immediately after that
  paragraph. The private wait instruction appeared only in the GM Note.
  After Save and direct reload, both blocks rendered at the same boundary.
  Removing only the two new blocks from the rendered comparison reproduced
  the entire baseline, including the table, Departure, and the 1,024-pixel
  illustration. The reused fixture already contained earlier benchmark
  blocks, so this does not count as a clean matched repetition.
- **Save acknowledgement.** Build showed Saved and still displayed Check
  insertion after reload. Activating Check insertion cleared the warning
  with identical rendered content and exactly one copy of the new passage.
  Recovery worked. Automatic acknowledgement remains unresolved.

### Hosted Plan placement on schema 0187

On November 22, production revision `60c19c08` reported application schema
`20261122_0187` after a separate rollout. A new synthetic Buddy Cloud Pilot
Plan had Arrival and Departure scenes, the original First sight Read Aloud,
a choice and its red-gate option, and a two-column table. It did not include
artwork. The exact saved Markdown was captured before sending.

- **P01, ordinary Send.** With a collapsed caret verified at the end of
  the Arrival paragraph, the exact benchmark prompt completed in a fresh
  thread and asked which paragraph or heading to use. There was no writable
  proposal. A follow-up naming both the paragraph and its successor also
  returned a before-or-after clarification. Neither reached Save.
- **Single named-target follow-up.** A follow-up in the same thread named
  only the first words of the Arrival paragraph and asked to add both
  blocks after it. The preview showed Read Aloud and GM Note after that
  paragraph, before the choice. Save confirmed the suggestion was saved
  to this Plan. After exact-route reload, both rendered and their canonical
  Markdown was present. Removing only the two added blocks reproduced
  the baseline Markdown byte for byte, including the original Read Aloud,
  scene and choice identities, Departure prose, and table.

The named-target success verifies placement and persistence for that follow-up.
Ordinary caret-based P01 still fails at routing, and matched independent
repetitions are still open.

#### Retained placement decisions

Read-only inspection scoped to the three synthetic Plan turns found the
same collapsed caret at position 179 in all three retained opening decisions.
All three classified the request as a page edit. They differed in location
resolution:

| Request | Author interpretation | Source selection | Outcome |
| --- | --- | --- | --- |
| Exact ordinary P01 | Unscoped, placement unresolved | Unresolved, zero compatible passage or anchor votes | Missing target, clarified |
| First follow-up with two textual boundaries | Named scope, after paragraph | One passage vote, relation unresolved and no compatible anchor | Missing target, clarified |
| Follow-up with one paragraph locator | Named scope, after paragraph | After paragraph, one passage and one compatible anchor | Unique target, writable proposal |

The first turn preserved the caret and reached the opening decision. The
decision contract treats an omitted relation and genuinely ambiguous
placement as unresolved. An exact caret can currently be selected through
the explicit caret relation. A fix for ordinary Send needs a distinct
decision for a page edit with no stated placement constraint. Explicit
directions, unresolved constraints, and selected-text replacement still
need to retain their existing checks.

#### Selected Read Aloud rewrite

In a fresh conversation on the same synthetic Plan, the exact P02 request
followed a verified selection of the full First sight body, including the
period. Buddy asked whether to replace the current selection. No suggestion
appeared, and the saved Markdown still matched the pre-turn snapshot exactly.

The retained V2 opening decision recorded a page edit with a 30-character
replacement capture and a captured-target option in its catalog. The source
selection voted for the capture. The independent author interpretation
reported unresolved placement, so the combined decision admitted no anchor
and clarified. This run did not reach the writer or test preservation of the
callout title through a rewrite.

#### Add a private note to an existing scene

On hosted revision `60c19c08`, a fresh conversation on the same synthetic
Plan started from the Arrival card in Cards view. The request was “Add a
private reminder that the guide waits at the gate. Leave the spoken material
alone.”

The writable preview preserved both spoken passages and added a GM Note with
“The guide waits at the gate.” It omitted the existing GM Note, “Keep the
tower sealed unless the players investigate it.” I dismissed the preview
before saving. After reopening the exact Plan, its Markdown matched the
baseline byte for byte. The existing note was present and the new note had
not been saved.

The retained opening selected `replace_playable_body` for the captured scene
and authorized the writer. This case reached a preview. It failed the
preservation check because the proposed scene body dropped unrelated material
during an additive edit.

### Hosted rerun after the 0189 cutover

On November 22, Buddy served revision `4101fa98` with schema
`20261122_0189`. Public readiness passed. All cases below used saved
synthetic Buddy Cloud Pilot fixtures and fresh conversations.

- **P03, add a private note in Cards.** On the same Arrival card as the
  earlier failed run, the exact prompt proposed a separate GM Note,
  “The guide waits at the gate.” The preview retained the previous tower
  reminder, the titled First sight block, and both spoken passages. Save
  confirmed the suggestion was saved to the Plan. Opening its exact link
  in a fresh tab rendered both notes, unchanged spoken passages, and the
  existing choice. This was one save-and-reopen pass on a reused fixture.
- **P01, ordinary Plan insertion.** Verified a collapsed caret at the
  final character of the Arrival paragraph. Ordinary Send asked which
  paragraph or heading to use. No writable proposal appeared.
- **P02, ordinary selected-text rewrite.** Selected the entire First
  sight body, “Mist hangs low near the marsh.” Ordinary Send asked whether
  to replace the current selection. No writable proposal appeared, and
  the existing title, body, notes, choice, and table still rendered.
- **B01, illustrated Build fixture.** Verified the caret at the end of the
  Arrival paragraph. The exact request once reported that it had no
  captured writing destination and once returned the material in chat.
  A third request explicitly asked to insert two new blocks at the caret
  and again reported no captured destination. None produced a writable
  proposal, so this run could not score the insertion acknowledgment fix.
  The fixture already contained earlier benchmark material.

The retained P01 and P02 openings both had two author observations of
`page_edit` with unscoped `unresolved` placement. In both cases the
independent source decision voted for the offered capture, with one direct
anchor and no passage votes. The host clarified because the author vote did
not agree. P01 now reaches the captured source vote, correcting one side of
the earlier routing failure. P02 still has the same author-side blocker.

All three Build turns reached the server without a write capability. Two
were classified as current-page writing and one as a connected-page
request. All stayed on the source-answer path.

Build currently requires contextual placement support for ordinary Send
with a collapsed caret. Its client check rejects pages containing root
callouts, tables, or artwork. The server catalog likewise accepts root
prose, headings, and horizontal rules. The verified caret alone therefore
did not produce a capability on this saved fixture.

A mounted-editor control used a page containing two existing callouts,
a table, and artwork. The contextual paragraph-boundary transaction
also rejected a canned Read Aloud and GM Note because it only permits
one prose paragraph. The editor remained unchanged. With the caret
placed at the same paragraph end, the existing exact-caret apply path
preserved each original node and serialized both new blocks. This
control leaves ordinary Send, server placement admission, and hosted
save and reopen unverified.

### Plan author interpretation with editor focus

The hosted P01 and P02 failures reached explicit page-edit intent with
unresolved placement. The source-aware opening voted for the captured target.
The earlier author-only calls had no indication that the editor held a
selection or caret. The candidate supplies that fact from the frozen editor
capture and keeps the exact target and selected text at the owning boundary.

On November 22, the configured Jev provider received synthetic P01 and P02
requests through the same decision SDK as hosted Buddy. Each arm used three
runs of the initial author question and three runs of the quote-context
recheck, with empty dialogue and the same model and choices.

| Author interpretation | Before | With editor focus |
| --- | --- | --- |
| P01, open insertion location | 0/6 recognized, all unresolved | 6/6 recognized as an insertion with no stated location |
| P02, rewrite the current selection | 0/6 recognized, all unresolved | 6/6 recognized as a selection rewrite |
| Chat-only rewrite with selected text | 6/6 discussion | 6/6 discussion |

An early candidate sometimes dropped Arrival from an explicitly located
insertion during recheck. The final contract omits the editor focus hint for
recognized explicit locations. A serialized request comparison for the named
Arrival control proves its initial and recheck wires match the baseline.
Synthetic native SDK tests exercise independent target selection, discussion
veto, and rejection of a focus that disagrees with the frozen editor capture.

This comparison covers author interpretation. Hosted proposal, explicit Save,
and cold reopen remain to be scored through ordinary Plan Send.

### Durable chat-only controls

On November 22, while Buddy served `590e45a2` at schema 0189, a read-only
audit of Buddy Cloud Pilot matched completed turns to the exact X01 and PL02
benchmark prompts. The saved turns span multiple releases and some used
earlier fixtures.

| Case | Completed turns | Matching write reservations |
| --- | ---: | ---: |
| X01, Build | 3 | 0 |
| X01, Plan | 3 | 0 |
| PL02, Play | 6 across 4 runs | 0 |

Build reservations were checked by World, conversation, and retained turn
origin or exact instruction. Plan actions were checked by World and retained
turn origin or exact instruction. Play proposals were checked by World,
receipt-bound Run, and exact instruction. All six Play turns carried a
content digest. No run-edition revision was committed between the acceptance
and completion of any of those turns. The stored Play replies contained none
of the seeded tower, lantern-signal, or gate cue phrases checked in the
earlier browser runs.

This audit supplies durable no-write evidence for the recorded discussion
controls. The clean P01-to-PL02 adoption check and the combined release's
Build and Plan save-and-reopen cases are still pending.

### Hosted authoring and reopen on a5c7599c

The hosted container served
`a5c7599c3c32731785de4562ced073cadf392e07` with application schema
`20261122_0192`. The container was healthy and public readiness returned
`ready`. All writing checks used existing synthetic Buddy Cloud Pilot
fixtures. These are checks against the serving release on reused fixtures,
not independent repetitions on clean fixtures.

| Case | Writer and observed result |
| --- | --- |
| B01 | Ordinary Build Send, with the caret after the Arrival paragraph, produced a reviewed Read Aloud followed by a GM Note. Save and full reload preserved their position. With those two additions removed, the ordered rendered editor blocks matched the baseline after saved artwork loaded, including Departure, the table and the image. |
| P01 | Ordinary Plan Send from Document view surfaced a writable suggestion after the reply settled. Review showed a titled Read Aloud and a separate GM Note. Save acknowledged the suggestion and full reload showed both blocks within Arrival. The 13 pre-existing rendered editor blocks matched in order after excluding the two additions. |
| P02 | Two attempts used the exact selection-rewrite request after selecting the First sight sentence, once before opening conversation and once with conversation already open. Both asked for clarification and surfaced no writable suggestion. These attempts do not establish whether the server admitted a replacement capture. The title and original body remained visible. |
| PL01 | Ordinary Run chat returned existing spoken material and a proposed cue in chat. With **Propose scene edit** selected, the exact request produced a titled Read Aloud and a separate GM Note. The scene was unchanged while review was pending. Apply advanced the session copy from revision 0 to 1, still based on Plan version 10. On reload both blocks rendered, and all pre-existing Arrival text from the first original callout through the existing choice matched. |
| C01 | The saved synthetic encounter opened at revision 1. The surface exposed no conversation or page writer, so the prompt had no eligible entry point. Save remained disabled and the encounter stayed at revision 1. |

The successful Build, Plan and Play checks establish live persistence for the
tested insertion paths. The selected-text Plan path and the full matrix of
clean-fixture repetitions remain open.

### Hosted PL02 from the agent-authored Plan revision

Serving revision `a5c7599c`: opened the saved P01 Plan
`98fe9569-b94c-46af-b031-8bc9de565e77` at revision 4, then used **Start Play
from this Plan** to create a new Buddy Cloud Pilot Run,
`cb10b9c7-a05d-4c22-884e-1537ce102fb0`. Arrival rendered the agent-authored
Boardwalk Read Aloud and its separate GM Note after adoption.

In a fresh Run conversation, the exact PL02 request returned the saved
First sight and Boardwalk spoken passages. The reply omitted the tower
investigation and gate cues. Refreshing scene proposals showed none.
Reloading the exact Run preserved the rendered Arrival scene and the
saved chat reply reopened.

The read-only check of turn `dcf55d5b-40d1-4c07-9d5c-4da82b5ab2c4`
confirmed completion, pinned Plan revision 4, a matching adopted content
digest, and an unedited Run at revision 1 with edition revision 0. The
Run had zero scene edit proposals and zero committed edition revisions.
This is one end-to-end PL02 pass on a fresh Run from the reused P01 Plan.

### Hosted Build selected rewrite on a5c7599c

On the existing illustrated Buddy Cloud Pilot Build fixture
`526ee2a9-8339-4ae1-b23e-df894cafc537`, a fresh conversation used the exact
B02 request after selecting the complete First sight Read Aloud body.
The clipboard matched all 132 characters, including the final period, and
retained turn `fefdc366-b2d1-4887-bd71-d8e72e536025` confirmed the same
selection length, final character, and native writer authorization.

The preview offered two quieter sentences and left the page unchanged
before Save. After Save and cold reopen, the document reported Saved.
The ordered comparison contained 18 rendered blocks before and after.
Only the First sight block body differed, preserving its Read Aloud kind
and title, the other callouts, Departure text, table and loaded artwork.
This is one pass in a fresh conversation on the reused protected fixture.

The B03 insertion control on the same release stopped before the writer
in two turns, `233518c4-3578-4605-9e2e-cfd0872ba383` and
`e7075447-02db-4d0f-b59f-3e76a400f01d`. Both retained the same collapsed
caret and selected current-page insertion. The offered placement required
an existing paragraph and a before/after relation. Both dispositions
were unresolved, and no writable proposal appeared or changed the page.
[Buddy #4485](https://github.com/Drakosfire/DungeonMindBuddy/pull/4485)
adds the captured caret option for an unqualified insertion. Its hosted
B03 proposal, Save, and cold-reopen proof remains pending.

### Hosted Graph fixture and eligibility

On serving release `a5c7599c`, Buddy Cloud Pilot opened the native Graph
with zero selectable objects. Build saved and admitted a dedicated fictional
Sealed Tower source. Extraction run `85c89399-1026-4404-a970-949116b24c7a`
classified Sealed Tower as a Location. The native profile review prepared
successfully, but confirming it and retrying the original packet both
returned HTTP 409. PostgreSQL logged duplicate IDs in
`dungeonmind.knowledge_head_events` at the two confirmation timestamps.
The Pilot remained on semantic profile revision 1, and the object was
still absent when the Graph reopened.

On this release, Graph object selection opens the details pane. The World
conversation mounts a visible composer on Build, Plan, and Play. Graph
does not offer the G01 chat submission path. The live selected-object
control remains pending because the Pilot fixture is not published.

### Hosted Plan Save and matched editor controls

On hosted release `a3a7cfc4`, the synthetic Plan reopened as Saved and
accepted new requests. P02 selected the complete body of First sight. The
proposal repeated the Read Aloud wrapper and title around the new body.
The Save guard refused it. The Warning proposal also reached review and
was refused at Save. Both proposals were dismissed, and the reopened
Plan matched its original text.

Mounted Save preparation with the saved fixture Markdown reproduced P02.
Replacing the selected body with a whole callout produced a nested
callout that semantic Markdown cannot reopen. The same body as prose
prepared successfully under the existing Read Aloud wrapper. The Warning
prepared successfully when inserted at the exact end of the Arrival
paragraph. The Warning control does not explain why the hosted turn's
Save was refused.

Build B03 asked for an insertion location on two hosted attempts, including
one with a verified caret at the end of Arrival. Neither staged a page
proposal. Reopened text and artwork matched the baseline.

### Verified on hosted release `ac553f77`

The November 23, 2026 repeat used the deployed image from
[#4534](https://github.com/Drakosfire/DungeonMindBuddy/pull/4534) and synthetic
Buddy Cloud Pilot fixtures. Public readiness and the serving image identity
matched the release. The table reports individual hosted runs on that image.

| Case | Earlier observed failure or limit | Result on `ac553f77` |
| --- | --- | --- |
| B01 | On `2ac2d8be`, the exact request at the end of Arrival asked which paragraph to use. The retained turn stopped before writer dispatch. | The same request on the same saved Build fixture produced separate Read Aloud and GM Note blocks immediately after Arrival. Both survived Save and reload. The remaining blocks and table matched, and the original 1,024-pixel illustration loaded after reload. |
| P01 | An earlier ordinary Send either discussed the wording in chat or staged a suggestion after Departure. | Ordinary Send produced and saved separate Read Aloud and GM Note blocks directly after Arrival. The retained selection recorded an insertion at offsets 210–210. After reload, removing the two additions from the editor text yielded the original text, and the existing callouts matched in order. |
| P02 | On `a3a7cfc4`, the model returned the matching Read Aloud wrapper and Save refused it. | The exact whole-body selection again produced the matching wrapper. Save accepted it without manual cleanup. Reload showed the rewritten body inside the single original **Read Aloud: First Sight** block. The rest of the rendered Plan matched, including Departure, the red-gate choice, and the table. |
| PL02 | Earlier adoption runs used an agent-authored pair whose Plan placement missed Arrival. | A fresh Play session adopted the saved P01 revision 8. The exact chat prompt quoted the new player-facing passage and omitted the GM cue. No scene edit appeared, and the scene matched after reload. |
| PL01 | An older release rewrote existing callouts and dropped the opening paragraph. Later isolated Play runs passed. | On that adopted session, explicit scene-edit mode staged two new blocks. Applying and reloading retained both blocks and the original scene text in order. Database readback confirmed the parent Plan digest matched, the new private cue existed only in session-copy revision 1, and Departure was retained. |

The baseline and after results use the same request and saved Build fixture for
B01. The Plan before and after observations use the developed Pilot fixture,
which accumulated earlier benchmark edits. These are individual observed
outcomes. The per-route repetition target in the
[benchmark](../../evals/semantic-block-authoring-benchmark.md) remains open for
Build and Plan, including a clean P03 run and the remaining prose, Warning and
Rules repetitions. The Play scene edit used the existing explicit proposal
mode. The evidence does not score implicit scene edits from default Play chat.

### Hosted Build prose insertion after #4581

On November 23, 2026 (America/Denver), B03 passed in Buddy Cloud Pilot on
serving revision `ab642ad0`. This release contains Build
[#4581](https://github.com/Drakosfire/DungeonMindBuddy/pull/4581) and the
subsequent guest Graph delivery. The completed synthetic turn
`b6d8465c-8c76-41f5-9a6d-7a3a67af189e` started after the serving container's
recorded startup.

The test placed the caret at the end of the Arrival paragraph on the
saved **Protected Arrival** page and sent the exact B03 request in a fresh
conversation. The retained trace records Jev 1.14.0 decisions and an OpenAI
Responses writer call to `gpt-6-luna`. It also records
`controller_finished_with_gaps` before the writer call. The turn completed
and the suggestion preview offered two ordinary paragraphs at that boundary.
Save acknowledged the proposal. After a full reload, the two paragraphs
were the next two editor blocks after Arrival. Removing those additions
from the rendered-block comparison recovered all 18 original blocks in
order, including the callouts, Departure text and table. Scrolling the
reopened page loaded the saved 1,024-pixel illustration.

The older protected-fixture attempts stopped at placement guidance or could
not reconcile Save. This run verifies proposal, placement and persistence
for one repetition on the current serving lineage. The remaining independent
repetitions and the Plan P03 check remain open.

### Hosted Build rewrite and callout controls on ab642ad0

On November 23, 2026 (America/Denver), three synthetic turns completed in
Buddy Cloud Pilot on `ab642ad0` through the OpenAI Responses writer with
`gpt-6-luna`. Each request used a fresh conversation and the existing
fixture's saved state as its baseline.

| Case | Retained turn | Result after Save and reload |
| --- | --- | --- |
| B02, Artwork Rewrite | `293f2c6c-5c4a-4b93-971c-642351c1178d` | Replaced only the selected First sight body with the proposed two sentences. The Read Aloud kind and title, all 16 neighboring rendered blocks, the table, and Departure matched the baseline. The saved illustration loaded at 1,024 pixels. |
| X02, Warning, Clean Arrival | `1d12e1b9-9d66-483f-becb-40ed8ba6358d` | The semantic Warning was saved directly after Arrival. Removing that one addition recovered all seven original rendered blocks in order. |
| X02, Rules, Clean Arrival | `7ceb4349-3d1a-4083-a196-4330d4388be2` | The semantic Rules block was saved at the same paragraph boundary and contained only the supplied rule. Reload briefly showed a retained insertion check. **Check insertion** cleared the prompt with no change to the reopened blocks. The earlier Warning was retained once. |

These are individual checks on reused fixtures. They do not fill the
independent repetition matrix.

### Three independent hosted P03 card-body runs on ab642ad0

On November 23, 2026 (America/Denver), the exact P03 request passed on
three newly saved synthetic Plans in Buddy Cloud Pilot on serving revision
`ab642ad0`. Each run used a fresh conversation and the marked Arrival card
in Cards view. The retained turns recorded the OpenAI Responses writer
with `gpt-6-luna`.

| Fixture | Retained turn |
| --- | --- |
| P03 Baseline, one titled Read Aloud and an ordinary Arrival paragraph | `08616e2a-9f5f-4567-9deb-01834505a731` |
| P03 Mixed Blocks, with a second titled Read Aloud, a pre-existing GM Note, Warning and Rules | `be838025-2c48-4ccc-9f47-b3fb24185f49` |
| P03 Mixed Blocks Repeat, separately seeded from the same mixed baseline | `123c76a9-0fef-489f-9a83-03b76a287d92` |

Each suggestion was saved without editing it. After reload, the Plan
Markdown contained exactly one new GM Note. Removing that note and
comparing trimmed nonblank lines reproduced the original Markdown in
order, including both scene markers, the choice and option markers,
Departure prose and the table. No retrieval footer was found. These are
three passes for the exercised Cards writer route. They do not exercise
the historical writer response that duplicated a whole replacement body.

### Hosted Plan document edits and Play adoption on ab642ad0

On November 23, 2026 (America/Denver), two fresh synthetic Plans and one
fresh Play session in Buddy Cloud Pilot exercised the document writer
and adopted scene on `ab642ad0`.

| Case | Retained turn | Observed result |
| --- | --- | --- |
| P01, ordinary Plan Document Send | `e5626769-2feb-400a-9536-d3049f84f373` | Save and reload placed a separate Read Aloud and GM Note immediately after the Arrival paragraph. The spoken passage omitted the private instruction. Removing the new blocks recovered all original nonblank Markdown lines and playable markers. |
| P02, selected First sight body | `2bf61211-28b9-4eea-b7d8-4837dcfaf4d9` | The proposal displayed the same titled Read Aloud wrapper. Save and reload retained one original wrapper with the new body. All other nonblank Markdown lines and playable markers matched. |
| PL02, exact generic chat request | `ac937d42-fa3b-4d4e-afad-10f46c3bc6e7` | Play adopted both P01 blocks. The reply quoted the earlier First sight block. It omitted the private cue and opened no edit proposal. Reload preserved the scene. This missed the newly authored passage expected by the case. |
| PL02, named diagnostic in the same Run | `82eadd78-873a-4132-b1b3-9dd3b6081456` | Asking for the Boardwalk read-aloud returned the exact new passage. It omitted the private cue, opened no edit proposal, and left the scene unchanged. |

The Plan proposals used the OpenAI Responses writer with `gpt-6-luna`.
Both Play requests recorded a Jev 1.14.0 decision and an OpenAI Responses
call with `gpt-6-luna`. Two eligible read-aloud blocks were present in the
adopted scene. The named diagnostic verifies selection by title. The
generic request still needs an explicit expectation for scenes with
multiple eligible passages.

### Hosted Play scene edit and Pilot Graph publication on ab642ad0

On November 23, 2026 (America/Denver), PL01 passed in the fresh Pilot
Run adopted from the P01 Plan. **Propose scene edit** produced two
distinct blocks, Read Aloud and GM Note. The current scene matched its
baseline during review. Apply and reload retained both additions.
Excluding their rendered lines recovered the original scene lines in
order. The retained proposal `5a64dfe2-7ffd-4596-9f30-470283fde8a4`
records the observed writer `gpt-6-luna`. The session edition advanced
from 0 to 1. Read-only comparison confirmed the parent Plan still matched
its pinned revision 2 and digest, and the Departure text matched exactly.
The new GM cue was present in the session edition and absent from the
parent Plan.

G01 remains blocked at fixture preparation. The Pilot Graph showed zero
objects. A new Sealed Tower extraction
(`81f6ecbd-6b7c-580c-9b9a-9ad6987a43d3`) classified it as a Location and
showed its quote. Publication still offered no selectable supporting
excerpt. A read-only check opened the exact admitted source span at the
current head and found one matching evidence reference with role
`context`. The extraction publication picker requires `support`.
The manual authoring path retained an earlier signed profile transition.
Retrying that exact confirmation returned HTTP 409. The UI retained the
original operation and kept fresh authoring unavailable. This observation
does not identify the exact rejection code or establish the earlier
submission's outcome. No candidate reached Graph publication.

### Hosted B01 after the Build caret and rich-paste Save fixes

On November 23, 2026 (America/Denver), two independent Buddy Cloud
Pilot documents exercised the exact B01 prompt with a collapsed caret
at the end of the Arrival paragraph on serving revision `8b4f848f`.
Each baseline contained the titled First sight callout, Arrival and
Departure prose, and the Signal and State table. The rich-pasted
baseline was committed before Send.

| Editor setup | Pilot document | Placement and reopen | Save acknowledgment |
| --- | --- | --- | --- |
| Same editor session from rich paste through review | `a23a8d8b-7295-43e8-8f8b-358eb7a8b87e` | Read Aloud: Arrival followed by one GM Note immediately after the original Arrival paragraph. Both survived cold reopen and retained their bodies when collapsed and expanded. | Save committed the document and then displayed a change warning. The first receipt check in the mounted editor remained unresolved. After cold reopen, Check insertion reconciled the receipt and the page still contained one GM Note. |
| Same rich-pasted baseline, cold reopened before Send | `d6122af9-4caa-48d0-9636-c2582d8259c0` | The same block kinds and order survived another cold reopen. | Save cleared the proposal and showed Saved without a receipt warning or a separate check. |

In both runs, removing the two new rendered blocks recovered the
baseline, including its headings, existing titled callout, paragraphs
and table. The private reminder was absent from the new Read Aloud.
The first arm passed placement and persistence and failed immediate
acknowledgment. The cold-editor control passed all three checks.
Buddy #4606 fixes the receipt digest mismatch in a deterministic
regression. Its serving carry, #4608, is verified in the follow-up
below.

### Hosted mounted Build Save and single-passage Play on 931ce3e1

On November 23, 2026 (America/Denver), hosted Buddy served the reviewed
Save fix with App schema `20261123_0207` and the existing guest settings.
Both checks used synthetic Buddy Cloud Pilot content.

- **B01.** On document `650a1761-a7c3-40f0-a835-ea9df4b290fb`, pasted the
  same baseline, let it commit, and sent the original prompt at the end of
  Arrival without reloading the editor. Review offered Read Aloud: Arrival
  followed by GM Note. Save cleared review and reached Saved without an
  insertion warning or receipt recovery. Cold reopen preserved both blocks
  in order, exactly one GM Note, and all other rendered content including
  First sight and the table. The private instruction was absent from the
  spoken passage.
- **PL02.** Adopted the saved P01 Plan version 2 into fresh Play session
  `708fcb43-7f1d-481a-b8cd-3e5e8caf0d69`. Removed only First sight from the
  session copy and reopened revision 1. With Boardwalk as the only Read
  Aloud in Arrival, a fresh conversation quoted that passage in response
  to the exact PL02 prompt. It omitted the Tower GM Note and staged no
  scene edit. Reopening recovered the expected Markdown byte for byte,
  including the scene and choice markers, Departure, and the table. The
  parent Plan still contained its two Read Aloud blocks and GM Note.

The earlier two-passage result remains part of the record. This Play
rerun measures retrieval of an unambiguous passage from the saved copy.
