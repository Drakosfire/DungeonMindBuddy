# HANDOFF — Prime Design: Graph Review Workbench is toolboxed and live-only; authoring is next

**Created:** 2026-07-05
**Repo:** `Drakosfire/DungeonMindBuddy`
**Branch at handoff time:** `cursor/ingest-surface`, tip `6c26487`
**Mode:** Prime Design — the mechanical cleanup and live-only unblock are done; what remains is a real design decision about where authoring writes should land, plus several smaller interaction-quality follow-ups that don't need Prime Design judgment.
**From:** the dogfooding agent (toolbox-ify, metadata cleanup, load dialog, pill-rendering fix, live-only unblock, C1S2 dogfood)
**To:** the next design agent picking up Graph Review + Gold Authoring Workbench

---

## 0. Copyable pickup prompt

```markdown
You are the next-phase Prime Design agent for DungeonMindBuddy's Graph Review + Gold
Authoring Workbench.

Read first (in this order):

1. This file: `Docs/Plans/HANDOFF-prime-design-graph-review-workbench-authoring-next.md`
2. `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` — the governing roadmap
   (R0-R11). Read §4 of this handoff before trusting its milestone table; the live-only
   pivot is a real deviation from what the roadmap assumed.
3. `Docs/Plans/DOGFOOD-graph-review-authoring-loop-session-1.md` — the last real dogfood of
   the Author Draft loop (2026-07-03), still mostly unresolved at the interaction-quality
   level even after this handoff's cleanup pass.
4. `Docs/Plans/AUDIT-ingest-surface-page-inventory.md` — the audit that drove the toolbox
   cutover (2026-07-05), for the "what got removed and why" record.
5. `Backlog.md` — search `## [READY] Graph Review node-info duplication` and
   `## [IDEA] Tiptap-backed processed markdown reader` for the two items this handoff
   explicitly defers to you.

Mission: decide where Author Draft's committed writes should land now that live-only
review works without a gold fixture. Today, commit only ever writes a candidate-graph-gold
JSON fixture (`prepare_graph_gold_authoring_write` / `commit_graph_gold_authoring_write`) —
there is no path from a staged `node_from_span` proposal to the corpus recap markdown
itself, which is what the operator explicitly asked to "play with" (§5 of this handoff).
Decide: gold-fixture-only (current), corpus-markdown-only, both depending on session
state, or something else — and write down falsification criteria, not just a preference.

This is not a green light to change the two-phase write-safety pattern
(`src/agent/corpus_writer.py`), the union-supergraph contract, or add an LLM write path.
```

---

## 1. Executive summary — what shipped since the roadmap was written

The roadmap (`ROADMAP-graph-review-gold-authoring-workbench.md`, 2026-07-02) predicted the
tool would still feel metadata-first and not yet "magical." The 2026-07-03 dogfood
(`DOGFOOD-graph-review-authoring-loop-session-1.md`) confirmed that verdict directly from
the operator: too much metadata, duplicate node-info surfaces, unable to complete several
authoring exercises, old competing toolbox destinations still visible.

This handoff's work (2026-07-05, same day as an audit + four implementation passes) closed
the *page-level* clutter gap and unblocked a real architectural constraint the roadmap never
anticipated: **gold was a hard prerequisite for loading a session into the workbench at
all**, which blocked reviewing session 2 of Campaign 1 (C1S2) — there was no gold fixture
for it yet, and the operator clarified gold was never supposed to be required to review
ingested objects.

**What's true today that wasn't true on 2026-07-02:**

1. `/ingest` has its own three-tool toolbox (Ingest Recap, Diagnostics, Author Draft) —
   the nine always-on diagnostic panels and the mock scaffold are gone from the default
   scroll; the default view is pickers + a load button + two-lane (or one-lane) prose.
2. A session with a live graph-ingest run but **no gold fixture** is now fully reviewable:
   discoverable in the load dialog, rendered as a single silent prose lane, clickable pills,
   Author Draft staging all work without a gold fixture existing.
3. `dmb-node` pill rendering is unified across gold and live lanes on a single regex-based
   parse of embedded `[label](dmb-node:id)` links — the offset-based rendering path that
   caused missing pills has been deleted, not just worked around.
4. `IngestionModule` (the recap-paste tool) has its own campaign picker — it no longer
   silently inherits whatever campaign the `/plan` surface happened to be on, which is what
   blocked dogfooding a `longmont-c1` session while `/plan` was pointed at `longmont-c2`.
5. **Proof, not just claim:** raw C1S2 notes were pasted into Ingest Recap, extracted to a
   graph, and reviewed on `/ingest` with pills rendering correctly — with zero gold fixture
   for session 2 existing anywhere in the repo. See §5 and the artifacts listed in §9.

**What's still true from the 2026-07-03 dogfood verdict, unchanged by this pass:** the
duplicate node-popover/game-card surfaces, the long scroll from node click to the actual
stage-node/relationship controls, and the still-only-gold-fixture-shaped write path. These
were out of scope for a toolbox/load-dialog/live-only pass and are the load-bearing input to
this handoff's mission (§5).

---

## 2. Chronology (this session, 2026-07-05)

1. **Audit** (`AUDIT-ingest-surface-page-inventory.md`) — inventoried all 21 sections
   rendered unconditionally on `/ingest`; decided to fold 9 diagnostic panels into one
   toolbox tool, make Author Draft its own toolbox tool, delete the mock scaffold, and trim
   the default landing view to pickers + lane summary + two-lane prose.
2. **Toolbox-ify implementation** — stood up `ProjectionProvider` /
   `AdaptiveProjectionContainer` on `/ingest` (previously `/plan`-only machinery), wired
   `Diagnostics` and `Author Draft` as toolbox tools, deleted the mock scaffold module.
3. **Metadata cleanup pass** — stripped the comparison strip and lane counts from the
   default view, collapsed pill delta badges to mismatch-only, added an `Ingest Recap`
   toolbox tool so the page has an honest path to ingestion instead of just review.
4. **Load dialog pass** — replaced the always-on campaign/session/run picker block and lane
   cards with a single "Load session" button and a modal dialog (same interaction pattern as
   the object viewer), with a two-line summary instead of full `GraphReviewLaneCards`. Empty
   first-visit state, silent prose lanes (no mention counts/warnings), workbench lede removed.
5. **Pill-rendering deep dive and fix** — traced missing pills to two root causes: (a) gold
   lane markdown never had `dmb-node` links spliced in (only live/preview markdown did), and
   (b) the live lane's rendering path used pre-computed character offsets that drift out of
   sync the moment any upstream text transform changes string length. Fixed by (a) unifying
   both lanes through `splice_node_link_spans` on the backend so both always carry embedded
   links, and (b) deleting the offset-based rendering path entirely in favor of parsing
   `[label](dmb-node:id)` directly out of the markdown with a regex — the same mechanism the
   backend already used to write the links, closing the loop instead of maintaining two
   representations of the same fact.
6. **Header simplification** — collapsed the `/ingest` page header's "Advanced" dropdown and
   descriptive copy down to a static "Memory Ingest" title, since the surface itself had
   gotten simple enough not to need it explained.
7. **Live-first Graph Review Workbench plan** — designed and implemented against explicit
   user stories ("I can drop the raw recap into the ingest flow, ingest, then view in the
   Graph Review Workbench," with gold optional). Five slices: run-first catalog
   (`GraphReviewCatalogSession` / `buildGraphReviewCatalog`), workbench load path gated on
   `hasGold` rather than gold-session-existence, single-lane live-only canvas, an ingest→
   workbench "Review in workbench" handoff CTA, and Author Draft commit gating
   (`hasGold` required to commit — staging still works either way).
8. **Ingest campaign-selection fix** — added `ReviewCampaignPicker` to `IngestionModule`
   itself, so the campaign being ingested into is explicit and independent of whatever the
   `/plan` view happens to be showing.
9. **C1S2 dogfood** — raw notes → staged → normalized/canonical recap → graph extract →
   loaded on `/ingest` without a session-2 gold fixture. See §9 for exact artifact paths.

All frontend unit tests and TypeScript compilation passed after each slice; one pre-existing,
unrelated backend test failure (`test_registry_discovers_checked_in_session_1_eval_dogfood`)
was present before this work and is not caused by it.

---

## 3. Current architecture map

**Toolbox (`/ingest`):**
- `apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts` — three tools:
  `ingest-recap`, `graph-review-diagnostics`, `graph-review-author-draft`. This is a
  dedicated config, separate from `/plan`'s `planSurfaceConfig.ts` (which still has the
  older `Graph Preview` / `Graph Gold Review` / `Vocabulary Review` / `Party Registry` /
  `Statblock` tools — those live on `/plan`, not `/ingest`; R11's "remove old surfaces" has
  not started and does not need to for `/ingest` to be clean).

**Session catalog / load path:**
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts`
  — `GraphReviewCatalogSession`, `buildGraphReviewCatalog(runs, goldSessions)`,
  `GRAPH_REVIEW_RUNS_CHANGED_EVENT`.
- `GraphReviewWorkbenchModule.tsx` — fetches `getGraphIngestRuns({ requirePreviewUnionStore:
  true })` and `getGoldReviewSessions()` in parallel, merges via the catalog builder, listens
  for the refresh event.
- `GraphReviewLoadSurface.tsx` / `GraphReviewLanePicker.tsx` / `GraphReviewLoadLaneSummary.tsx`
  / `GraphReviewLoadBar.tsx` — the load-dialog UI.

**Live-only rendering:**
- `GraphReviewLiveStateContext.tsx` / `graphReviewLiveReviewState.ts` — `hasGold` flag skips
  `getGoldGraphProjection` entirely rather than calling and 404ing.
- `GraphReviewLiveProjectionPanel.tsx` + `planSurface.css` (`.graph-review-live-only-projections`)
  — single-column layout, live lane titled "Ingested recap" when no gold.

**Pill rendering (unified, regex-based):**
- Backend: `src/graph_memory/projection/recap_projection.py` (`splice_node_link_spans`),
  consumed by `apps/live_control_server/services/graph_gold_review.py` for the gold lane too
  — both lanes now always carry embedded `[label](dmb-node:id)` links in their markdown.
- Frontend: `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewProjectionLane.tsx`
  parses `dmb-node` links directly from the markdown with a regex. No offsets, no mention
  props, no "unanchored" warning state — deleted, not hidden.

**Ingestion entry point:**
- `apps/live-control-ui/src/modules/IngestionModule.tsx` — own `ingestCampaignId` state
  seeded from `resolveInitialReviewCampaignId`, its own `ReviewCampaignPicker`, a "Review in
  workbench" CTA once `preview_union_store_ready` is true.

**Authoring (staging works; commit is gold-fixture-only):**
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorDraftToolPanel.tsx`
  / `GraphReviewAuthoringPreparePreviewPanel.tsx` — staging (`node_from_span`, relationship,
  link-intent proposals) is local/client-side and works regardless of `hasGold`. Prepare/
  commit is hidden behind a "Gold fixture required to commit authoring changes" message when
  `!hasGold`, because the write target genuinely is gold-fixture-shaped today (§5).
- Backend: `apps/live_control_server/services/graph_gold_authoring_prepare.py` /
  `graph_gold_authoring_commit.py` — `GraphGoldAuthoringCommitResponse.fixture_relpath` is
  always a candidate-graph-gold JSON path. There is no code path from a committed proposal
  to the corpus recap markdown.

---

## 4. Reconciling this work with the roadmap (do this before designing further)

`ROADMAP-graph-review-gold-authoring-workbench.md`'s dependency chain (R0→R1→R2→R3→R4/R5→
R6→R7...) assumed the default review experience is **always** gold-vs-live two-lane
comparison, with authoring (R6+) building on top of that comparison view. This handoff's
live-only pivot means that assumption is no longer universally true:

- **R2 (gold projection endpoint)** and **R3 (two-lane projected review)** are done, but only
  exercised when a session has gold. A live-only session skips both entirely — there is no
  comparison, by design, because there's nothing to compare against.
- **R1 (mode/state information architecture)**'s lane-state vocabulary
  (`gold_fixture`/`live_run`/`gold_draft`/etc.) is still accurate for gold-backed sessions but
  was never extended to describe a live-only session's single lane explicitly as a first-
  class state — it currently just conditionally renders less UI rather than naming the state.
- **R6 (authoring primitives)** is partially built (staging) but its acceptance criterion —
  "the user can create a node and an edge from rendered prose and see them as committed
  draft pills before saving" — has only ever been exercised against a gold-fixture commit
  target, never against a live-only session, because commit is gated on `hasGold`.

**Action for the next agent:** either (a) formally amend the roadmap to treat "gold-backed
two-lane" and "live-only single-lane" as two parallel, permanently-coexisting modes (not one
subsuming the other), or (b) decide gold-backed review is the "real" path and live-only is
explicitly a reduced/temporary mode pending gold authorship — but say so in the roadmap
itself rather than leaving R1's state vocabulary silently incomplete. This is a naming/scope
decision, not an implementation task.

---

## 5. The open design question: where should authored writes land?

This is the mission (§0) and the reason the user asked for this handoff. Restated precisely:

> "We don't NEED gold, now we want to be able to review the ingested objects, and play with
> the authoring idea to add objects to the markdown from the ingest surface."

**What exists today:** Author Draft lets a GM select a span of live-projected prose and stage
a `node_from_span` proposal, a relationship proposal, or a resolver link-intent — all
client-side, no writes. Prepare/commit turns staged proposals into a
`GraphGoldAuthoringCommitResponse` that is written to a **candidate-graph-gold JSON file**
(`prepare_graph_gold_authoring_write` / `commit_graph_gold_authoring_write`, mirroring the
Party Registry two-phase write pattern per the roadmap's R7 precedent). This requires a gold
fixture to exist as the write target, which is exactly why commit is gated on `hasGold` — not
an arbitrary UI restriction, a real constraint of what the write path currently does.

**What the user is asking to "play with" instead:** a staged `node_from_span` proposal
becoming a `[label](dmb-node:id)` link **spliced directly into the session's recap markdown**
(the same `splice_node_link_spans` mechanism this handoff's pill fix already unified gold and
live rendering around, §2 item 5) — i.e. authoring that edits the corpus recap itself, not a
side-channel gold fixture, for sessions that have no gold and may never get one.

**These are different products with different risk profiles:**

| | Gold-fixture write (current) | Corpus-markdown write (requested) |
|---|---|---|
| Target file | `evals/graph_memory_layer/examples/.../candidate_graph_gold.json` | `corpus/eldyrwild-markdown/.../Session N - ....md` |
| Blast radius if wrong | Eval fixture — wrong, but not canon | Canon campaign markdown — directly GM-facing |
| Existing write-safety precedent | R7 (mirrors Party Registry two-phase write) | `src/agent/corpus_writer.py` two-phase pattern exists but is not wired to graph-authoring proposals at all |
| Requires gold to exist | Yes | No |
| Produces a reviewable node the union supergraph can later ingest | Only via a future gold→graph promotion step (not built) | Only if the graph-ingest pipeline is rerun over the edited markdown afterward (not automatic) |

**What this handoff is not deciding for you:** whether corpus-markdown authoring should
replace, sit alongside, or feed into gold-fixture authoring; whether a spliced `dmb-node` link
written straight into markdown should also require a corresponding node to exist in the
*current* graph-ingest run's preview union store (to avoid a pill linking to nothing); and
whether this needs its own two-phase prepare/commit surface or can reuse
`graph_gold_authoring_prepare.py`'s diagnostics/fingerprint machinery with a different write
target. Write these decisions down with falsification criteria (§0) before implementing.

**Non-negotiable regardless of the decision:** two-phase prepare/diff/confirm/commit,
stale-file-token rejection, and append-only authoring event logging (roadmap §5, R7, R10) all
still apply to any corpus-markdown write path — corpus write safety does not get relaxed just
because the target moved from a fixture to canon markdown; if anything it tightens, per
`.cursor/rules/corpus-pii-and-llm-payloads.mdc`.

---

## 6. Backlog review (per this handoff's request)

Reviewed `Backlog.md` for every Graph Review / Ingest Surface entry captured 2026-06-30
through 2026-07-05. Changes made directly (not just recommended) as part of this handoff:

- **Closed → `Backlog-DONE.md`:** `[READY] Live-only graph load on Ingest Surface (no gold
  required)` — all five of its action items are done and dogfooded (§9). Also closed the
  informal "Reader regressions addressed in PR 11E" notes (frontmatter stripping, stale
  single-lane header) — both confirmed fixed by code inspection, they were sitting under a
  `[TODO]` heading despite already being past tense.
- **Updated in place:** `[IDEA] C1S2 candidate graph gold` — dropped the "defer until
  live-only dogfood is unblocked" language (it's unblocked now) and flagged that the C1S2
  canonical recap filename (`Session 2 - Stonebridge and Glowkindle Rats.md`) mismatches its
  own subtitle ("Finishing the Job") — almost certainly a copy-paste of the Session 1 slug
  during this handoff's own dogfood run. Rename before treating it as canon; not fixed as
  part of this handoff since it's a corpus content decision, not a code change.
- **Reformatted into proper blocks:** the loose "Interaction redesign" / "Future ingestion
  flow" bullets under the old `[TODO] Ingest Surface follow-ups after PR 11E` heading, now
  split into `[READY] Graph Review node-info duplication + authoring-action fold distance`
  (still open, unchanged by this pass — see §1) and `[IDEA] Tiptap-backed processed markdown
  reader with graph projection overlay` (explicitly deferred pending §5's decision).
- **Left open, unreviewed here (out of this handoff's scope, still relevant elsewhere):**
  `[IDEA] Rename Ingest Surface / Memory Ingest chrome` — still true, small, independent of
  the authoring decision; `[DOING] Graph memory encounter/job extraction spike` and
  `[DOING] Graph memory vocabulary ablation` — separate extraction-taxonomy workstream, its
  own Prime Design handoff already exists
  (`HANDOFF-prime-design-graph-memory-extraction-taxonomy.md`); not touched here.
- **Not in `Backlog.md` but still open, found via `Docs/Plans/`:**
  `FOLLOWUP-raw-dmb-node-links-and-duplicate-projected-objects.md` (raw edge-as-node-link
  rendering, duplicate same-label objects) — predates this handoff's pill-rendering fix and
  addresses a different symptom (data-quality/duplication, not rendering mechanism); not
  confirmed resolved, not captured in `Backlog.md` at all. Recommend giving it a proper
  backlog entry next time it's touched rather than leaving it as an orphaned doc.

---

## 7. Non-negotiables and guardrails to carry forward

From the roadmap (§5, "Implementation guardrails") and `.cursor/rules/`, still governing:

- The source prose remains the visual focus; evidence/debug stays an explicit drill-in.
- Review lanes stay read-only unless explicitly toggled into Author Draft.
- Existing-object linking is backend-assisted; the UI does not invent identity merges.
- Two-phase prepare/diff/confirm/commit for any write, gold-fixture or corpus markdown.
- Authoring event logs stay local / git-ignored (roadmap R10).
- No LLM write path yet (R8/R9 are explicitly sequenced after manual authoring is stable —
  do not let §5's decision quietly pull LLM assist forward).
- Corpus content is real-person-adjacent GM/player data — see
  `.cursor/rules/corpus-pii-and-llm-payloads.mdc` before any external tool call touches it.

---

## 8. Suggested first tasks for the next agent

1. Read §4 and decide how to reconcile the roadmap's gold-vs-live-only mode split before
   touching authoring — this affects R1's state vocabulary either way.
2. Make the §5 decision (gold-fixture / corpus-markdown / both) with falsification criteria:
   what would prove a corpus-markdown write path is/isn't safe enough to ship past staging.
3. If corpus-markdown authoring is chosen, scope whether it reuses
   `graph_gold_authoring_prepare.py`'s diagnostics/fingerprint machinery with a new write
   target, or needs its own prepare/commit pair following `src/agent/corpus_writer.py`'s
   pattern more directly.
4. Independently of §5, the `[READY]` node-info-duplication backlog item (§6) is safe to
   delegate as a narrower UI-only fix per `.cursor/rules/subagent-delegation.mdc` — it does
   not require the authoring-target decision to land first.
5. Rename the C1S2 canonical recap file (§6) once the GM confirms the correct title — small,
   corpus-only, independent of everything else in this handoff.
6. Re-run `DOGFOOD-graph-review-authoring-loop-session-1.md`'s checklist end-to-end (it was
   never fully completed) once §5 lands, this time against a live-only session with no gold,
   to get real signal on rows 7-18 that were "not exercised" in the 2026-07-03 pass.

---

## 9. C1S2 dogfood proof (artifacts, this handoff)

- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_ingest_staging/session_2_raw_notes.md`
  — raw pasted notes.
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 2 - Stonebridge and Glowkindle Rats.md`
  — canonical recap (filename issue noted in §6).
- `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/_archive/Session 02 - Stonebridge and Glowkindle Rats__20260706T023942Z.md`
  — archived normalized copy from the ingest run.
- No file exists under `evals/graph_memory_layer/examples/session_2_candidate_graph_gold*` —
  confirms the review happened without a gold fixture.

---

## 10. Reference index (all paths repo-relative)

**This workstream's docs, read in this order for full context:**
- `Docs/Plans/AUDIT-ingest-surface-page-inventory.md` — the toolbox-cutover audit + decisions
- `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md` — governing roadmap (R0-R11)
- `Docs/Plans/DOGFOOD-graph-review-authoring-loop-session-1.md` — last full authoring dogfood
- `Docs/Plans/FOLLOWUP-raw-dmb-node-links-and-duplicate-projected-objects.md` — orphaned,
  not yet resolved or backlog-tracked (§6)
- `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md` — design doc the roadmap
  implements

**Backlog:**
- `Backlog.md` → `[READY] Graph Review node-info duplication...`, `[IDEA] Tiptap-backed
  processed markdown reader...`, `[IDEA] C1S2 candidate graph gold...`, `[IDEA] Rename
  Ingest Surface...`
- `Backlog-DONE.md` → `[DONE] Live-only graph load on Ingest Surface...`, `[DONE] Ingest
  Surface reader regressions after PR 11E...`

**Code (frontend):**
- `apps/live-control-ui/src/modules/IngestionModule.tsx`
- `apps/live-control-ui/src/planSurface/config/ingestSurfaceConfig.ts`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/` (workbench, load dialog,
  catalog utils, live state, author draft panels)
- `apps/live-control-ui/src/planSurface/graphProjectionReader/` (shared markdown reader)

**Code (backend):**
- `src/graph_memory/projection/recap_projection.py` (`splice_node_link_spans`)
- `apps/live_control_server/services/graph_gold_review.py`
- `apps/live_control_server/services/graph_gold_authoring_prepare.py` /
  `graph_gold_authoring_commit.py`
- `apps/live_control_server/routes/graph_preview.py`
- `src/live_play/recap_stage_paths.py` (canonical/normalized/staging path derivation)
- `src/agent/corpus_writer.py` (the two-phase write pattern any corpus-markdown authoring
  path must follow)

**Current branch tip at handoff time:** `6c26487` on `cursor/ingest-surface`.
