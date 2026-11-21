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

- **B03:** Hosted Build proposed exactly two prose paragraphs with no callout.
  The preview appeared before Arrival where the intended location was after
  the Arrival paragraph. Dismiss preserved the saved blocks and save status.
- **X01:** Hosted Build responded to the brainstorming request in chat and
  showed no page suggestion. The rendered saved blocks and save time matched
  their initial state. Server write-reservation records were not checked.

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
  so the request was ineligible for submission. The UI comparison confirms
  visible text and source identity. A byte-level comparison remains pending.

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
Replacement persistence remains unverified.

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
Adopting agent-authored P01 blocks, comparing the full parent Plan revision,
and testing preservation of table and image fixtures remain pending.

Hosted Home showed no conversation composer in Buddy Cloud Pilot, so H01 had
no eligible writer. Hosted Graph still reported unavailable native readback
and disabled object selection in the pilot. G01 requires a disposable native
Graph where the fixture object can be selected.
