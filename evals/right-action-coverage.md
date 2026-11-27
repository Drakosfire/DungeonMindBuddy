# Right Action at the Right Time coverage

This matrix expands the [canonical action catalog](plan-authoring-benchmark.md#action-catalog).
Each row defines three distinct cases, identified by the row ID and tier
(for example, `CLARIFY-1`). Tier 1 supplies the context needed for a direct
choice. Tier 2 introduces a close competing choice or a missing prerequisite.
Tier 3 adds prior state, a competing destination, stale evidence, or interruption.
Qualify each case on its owning Buddy surface. These are fixture specifications.
The catalog records which capabilities have verification evidence.

| Action ID | 1 · Direct | 2 · Contrast | 3 · Workflow |
| --- | --- | --- | --- |
| DISCUSS | Brainstorm from an invented premise in chat with zero reads. | Discuss a supplied excerpt without opening a page proposal. | After page writing, resume Sheep discussion with no new retrieval or proposal. |
| CLARIFY | Ask two preference questions and wait without reads. | One preference is missing from an otherwise complete work request. Ask just that question. | Reopen a pending clarification, answer it, and continue the same task once. |
| CHAT-DRAFT | Create one editable draft from supplied prose. | Produce two alternatives in chat with the page editable. Leave the page alone. | Reopen two separately edited drafts, then stage only the explicitly selected revision on request. |
| PAGE-EDIT | Tighten the exact selection and stage review without retrieval. | Stage a six-row table at the requested location while protecting adjacent text. | Apply a review and save once. Refuse a stale target and reconcile a lost acknowledgement through readback. |
| SOURCE-READ | Open one requested source and cite its exact passage. | Answer from supplied evidence when a competing relevant source is available. Zero new acquisition. | Reuse earlier supports and read only the missing source for a newly requested claim. Reopen all citations. |
| PLAN-CARDS | Stage one card from a supplied source passage. | Use a targeted missing source to stage the aftermath cards with exact citations. | Build and review the full Conks Plan with optional scenes, branching and conditional triggers, then reopen. |
| STANDALONE-PAGE | Stage a new draft from the user’s complete supplied description. | Use the Maelthor prefix with zero discovery and retain both original citations. | Confirm once, reopen, and return the same receipt on retry. A foreign or stale review cannot create another page. |
| CONNECTED-PAGE | Stage a connected Location review from an exact supplied origin. | Distinguish connected page, standalone page and edit to the origin page. | Confirm the intended edge and page once. A changed origin requires renewed review. |
| STATBLOCK-PREVIEW | Open and explain the exact selected statblock. | Draft an incidental NPC from supplied traits in Plan or Play, with proposed mechanics labeled. | Brainstorm the Meat Mind variant across turns, reuse the admitted base, and draft only when asked. |
| STATBLOCK-SAVE | Save the reviewed exact revision once at operator confirmation. | Link the saved variant from Edge without changing the base statblock. | Resume after save but before link, reopen the exact variant from a fresh context, and use the same revision in Combat. |
| NAME-CORRECTION | Show and apply one accepted typo correction with original input preserved. | Fix a single Dustwalker possessive without changing the legitimate plural. | Reopen a review after effective input changes. Apply only corrections still bound to the reviewed occurrences. |
| IDENTITY-REVIEW | Reuse one explicitly selected existing identity. | Ask which Karsemine the operator means when two candidates match. | Resume the reviewed merge and prove no duplicate identity or stale binding, with exact citation reopen. |
| PUBLICATION | Publish an exactly supported reviewed candidate after confirmation. | Missing exact support blocks publication and preserves the candidate. | Replace a reviewed session revision, preserve authored/shared material, and reopen the prior revision. |
| IMAGE-DIRECTION | Prepare an illustration prompt from supplied details. Zero jobs. | Route a map direction to the right purpose. Distinguish a request for a prompt from Generate. | Reopen a prior direction, use a changed premise, and prepare a revised prompt without repeating research or generating. |
| IMAGE-GENERATION | Explicit Generate yields one private preview. | Generate from a supplied edit direction on the exact selected asset, preserving the original. | Select, save and bind the generated asset to the exact revision. Recover an unknown outcome without duplicating the job. |
| IMAGE-PLACEMENT | Apply a chosen asset at the exact destination, then save. | Move an existing image without generating, replacing it, or displacing neighboring prose. | Refuse a stale placement after preview, preserve the candidate and reopen the original page unchanged. |
| MAP-NAVIGATION | Open a supplied map reference at its exact source. | Excerpt or generate an appropriate map and preserve source versus authored status. | Save, reopen, and navigate from several map labels to exact location nodes. |
| REFERENCE-OBJECT | Open an exact Item or Table from a card. | Review an edit to one source-backed record, preserving source identity. | Reopen the same revision from both Graph and card and verify the edited values and source. |
| NPC-ART | Open a saved portrait for the exact NPC identity. | Choose between adopting existing art and requesting a new portrait. | Reopen scenes with two similar NPCs and show each exact portrait only where that NPC appears. |
| RULES | Look up and cite one explicit public rules question. | A lore-only request uses World evidence with zero Rules calls. | Answer a mixed mechanics and campaign question with separately owned citations that reopen. |
| RELATIONSHIP | Discuss a relationship idea with no review or publication. | Stage an exact edge review between selected saved pages. | Confirm only the verified edge. Missing support blocks mutation; retry returns the original receipt. |
| WORK-PLAN | Prepare a short editable checklist without executing it. | Resume one explicitly selected step while leaving another deferred. | Reopen after interruption and recover the accepted step without running a deferred or completed action again. |
| CHOICE-OPTION | Add a reviewed option to a selected Choice. | A request for scene detail edits prose rather than adding a branch. | Insert a new Choice between existing scenes and verify neighboring prose stays bound after save and reopen. |
| PLAY-DISPATCH | Open a saved Plan in Play with the selected PCs and exact scene. | Take a different branch while preserving the original Plan. | Reopen the active Run and verify the chosen branch, scene and exact references after interruption. |
| PLAY-EDIT | Stage a reviewed edit to the current session copy. | Distinguish a session-local change from a request to edit long-term Plan prep. | Refuse a stale Run or scene target after switching. Reopen and verify only the intended edition changed. |
| RECORDED-ROLL | Open an exact prepared table with no roll effect. | Record an explicitly supplied roll once and show the result. | Retry after restart and verify the same outcome and note with no second roll. |
| COMBAT | Preview an exact saved roster without starting Combat. | Handle parley without starting, then start the encounter on explicit authorization. | Reopen after a round and HP edit. Preserve exact mechanics and protect the prepared encounter from running-copy writes. |
| PLAYED-RECAP | Draft a recap from supplied played notes and leave it in review. | A competing unused Plan branch stays prep and is excluded from the played recap. | Confirm and publish the selected played Events, then answer a fresh continuity question with exact citations. |
| RECOVERY | Restore an unsent draft without dispatching it. | Distinguish a lost acknowledgement from a known failed action before offering Retry. | Recover a committed action receipt on reopen and prove retry creates no second mutation. |
| OPERATOR-HANDOFF | Give the correct operator control for an unsupported direct Save. | Contrast suggesting mechanics or map coordinates with directly changing them. | After a reviewed relationship or roster handoff, verify Buddy waits for the owner's confirmation and reports only observed results. |

See the [closed baseline record](right-action-baseline.md) for case grades and
unscored fixture and workflow findings.

## Baseline sequence

1. Pin the product build, ordinary tool presentation, model settings, fixtures,
   source admissions and expected journals. Qualify direct cases first, using
   retained cases where they match. Pin the companion contrasts before tuning.
2. Run the qualified cases through ordinary Buddy. Reuse provider-free owner
   tests for technical retry controls. Mark unavailable capabilities and
   missing telemetry explicitly. Keep them in the catalog and report the
   eligible denominator separately.
3. Report choice, forbidden reads and effects, fulfillment, and exact reopen
   per action and tier. Include read counts by type, time to first action,
   time in retrieval, total latency and tokens. A missing trace cannot prove
   zero retrieval. Compare multi-turn reuse with a changed-evidence or
   explicitly requested research control.
4. Change one aspect of tool presentation at a time after the baseline.
   Test descriptions, visible prerequisites, destination, confirmation,
   or which tools appear at that step. Use the same frozen development
   cases and separately pinned validation variants. Require improved action
   choice or fewer unnecessary reads with preserved required retrieval,
   fulfillment, and side-effect safety.

Use the shared action capture and scorer. Register each executable fixture
under its stable case ID with exact input and expected ordered observations
before execution. When a new action lands, add its three tiers and closest
competing action using this same format.
