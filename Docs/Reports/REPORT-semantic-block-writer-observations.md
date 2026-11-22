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
