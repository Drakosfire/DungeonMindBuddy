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
