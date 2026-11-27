# Right Action at the Right Time baseline

The baseline closed with 75 graded cases and 15 unscored findings across the
[90-case coverage matrix](right-action-coverage.md). The frozen product anchor
was `ff8046517a267b399043f111248f2678947130e5`. The grades include ordinary
Buddy turns, mounted workflows with operator confirmation, and owner controls.
Historical comparisons and later harness verification have separate provenance.
The retained report and raw captures stay in the local benchmark evidence archive.

| Pass | Partial | Fail | Unproven | Unscored |
| ---: | ---: | ---: | ---: | ---: |
| 34 | 12 | 27 | 2 | 15 |

First controller choice was observed in 25 of the 75 graded cases. The
other 50 have no verified first-choice vote. A fulfillment grade can cover an
operator-selected action, so a pass alone does not establish correct autonomous
choice.

The retained Jev-only review found unnecessary source opens in 8 of 24
assessed cases, including one historical result that could not be tied to a
case ID. The case-level audit found 20 failures among 23 cases checked for zero
new retrieval, including Buddy's own Graph discovery and search. These counts
use different criteria and denominators.

The two unproven grades have different causes. PLAN-CARDS-1 returned HTTP 503
after 95.06 seconds with no recorded client disconnect. Trace readback returned
HTTP 409, leaving the underlying delivery failure unknown. RELATIONSHIP-1
delivered discussion without a typed review, but lacked a complete effects
journal to prove nothing was staged or published.

## Case results

Cell IDs are the action ID followed by the tier number. Unscored cases retain
their reason below.

| Action | 1 · Direct | 2 · Contrast | 3 · Workflow |
| --- | --- | --- | --- |
| DISCUSS | Fail | Partial | Fail |
| CLARIFY | Fail | Pass | Partial |
| CHAT-DRAFT | Pass | Pass | Unscored |
| PAGE-EDIT | Fail | Pass | Partial |
| SOURCE-READ | Pass | Fail | Partial |
| PLAN-CARDS | Unproven | Unscored | Unscored |
| STANDALONE-PAGE | Pass | Pass | Pass |
| CONNECTED-PAGE | Fail | Fail | Fail |
| STATBLOCK-PREVIEW | Partial | Partial | Partial |
| STATBLOCK-SAVE | Pass | Pass | Pass |
| NAME-CORRECTION | Pass | Pass | Pass |
| IDENTITY-REVIEW | Pass | Unscored | Unscored |
| PUBLICATION | Unscored | Pass | Unscored |
| IMAGE-DIRECTION | Fail | Pass | Pass |
| IMAGE-GENERATION | Pass | Pass | Partial |
| IMAGE-PLACEMENT | Pass | Pass | Pass |
| MAP-NAVIGATION | Fail | Fail | Unscored |
| REFERENCE-OBJECT | Unscored | Unscored | Unscored |
| NPC-ART | Fail | Pass | Fail |
| RULES | Fail | Pass | Fail |
| RELATIONSHIP | Unproven | Fail | Unscored |
| WORK-PLAN | Fail | Pass | Pass |
| CHOICE-OPTION | Fail | Pass | Fail |
| PLAY-DISPATCH | Unscored | Fail | Partial |
| PLAY-EDIT | Fail | Partial | Pass |
| RECORDED-ROLL | Fail | Fail | Partial |
| COMBAT | Fail | Fail | Fail |
| PLAYED-RECAP | Fail | Partial | Unscored |
| RECOVERY | Pass | Pass | Pass |
| OPERATOR-HANDOFF | Pass | Pass | Unscored |

## Unscored fixture and workflow gaps

### Read-only Core fixture for Conks

- **PLAN-CARDS-2** — Restore a Conks App World and clean Plan alongside the 13 reviewed Event revisions and exact PDF in a matching isolated read-only Core snapshot. The retained restorable inputs are pinned.
- **PLAN-CARDS-3** — Restore a Conks App World and clean Plan alongside the 13 reviewed Event revisions and exact PDF in a matching isolated read-only Core snapshot. The retained restorable inputs are pinned.

### Read-only Core fixture for identity review

- **IDENTITY-REVIEW-2** — Supply a read-only benchmark Core snapshot admitting two separate, independently inspectable Karsemine identities in the same World. Verify both appear in ordinary selection before testing clarification.

### Isolated writable Core fixture

- **IDENTITY-REVIEW-3** — The exact current identity is pinned. Need a recoverable reviewed merge with authorized isolated publication and checks for duplicate creation and exact source reopening.
- **PUBLICATION-1** — Current C2S30 review context and admitted source support reopen. Fresh publish requires isolated writable Core authority and explicit confirmation/readback. Retained publication receipt is preserved.
- **PUBLICATION-3** — Historical C2S30 receipt and reviewable input are present and independently pinned. A replacement case needs the joined current replacement route, authored-content preservation, and original revision readback.
- **RELATIONSHIP-3** — Qualify the intended relation and explicit operator endpoint selections. Run support-refusal and confirmation/retry controls. A successful publication requires an isolated writable Core snapshot.
- **PLAYED-RECAP-3** — Admit the exact played note and reviewed Event on an isolated writable Core snapshot. Then capture ordinary continuity and reopen the delivered citation against the published revision.

### Owning product workflow

- **CHAT-DRAFT-3** — Separate drafts can be edited and reopened. The pinned draft editor's placement action inserts a saved statblock link only. Qualify a generic selected-draft revision staging route before running the full workflow.
- **MAP-NAVIGATION-3** — The Build action is recognized but its executor is unavailable on the pinned route. Linked location markers in Conks are design evidence. A saved Buddy map with stable node bindings and reopen must be qualified.
- **REFERENCE-OBJECT-1** — The mounted Plan roll-table action has no product caller. Play prepared tables are a separate owner. A Plan card linked to an exact saved source-backed Table or Item remains unqualified.
- **REFERENCE-OBJECT-2** — No joined Plan card and exact source-backed object revision is qualified for reviewed editing and owner readback.
- **REFERENCE-OBJECT-3** — No qualified edit receipt to compare through independent Graph and mounted Plan reopen.
- **PLAY-DISPATCH-1** — The exact scene is admitted by Play launch. Party Registry prepares and commits a campaign/session roster and exposes no Run ID. A joined benchmark needs an owning contract and readback binding the selected PCs to the exact new Run. A campaign/session roster confirmation is component evidence.
- **OPERATOR-HANDOFF-3** — Qualify a reviewed roster with a matching ordinary owner confirmation, or use a relationship with exact supported endpoints and isolated writable Core.
