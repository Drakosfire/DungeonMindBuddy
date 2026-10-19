# Plan/Play cards and navigation

Status: reviewed design, 2026-10-19. Merged as #1457 at `b7bf9976b`. Architecture owns this design-only serial
PR under PRIME's explicit assignment. Base: `15ea069459709b5b61f82ce88d89185f6d0cec83`.
Write lease: this file and the chosen-focus pointer in `ROADMAP-demo.md` only.
No implementation or runtime lease is activated. Synthetic examples below are
design fixtures, not campaign material. PRIME retains review/merge coordination.

## Recommendation

Use the **scene as the navigation anchor**, and a **card as a bounded reading or
editing presentation within that scene**. A scene may have several cards. Keep a
complete Document view and the same owning Markdown/save controller behind both
views. A linked creature, map or source has its own identity and detail view;
placing its reference on a card does not transfer that identity to the card.

Start with Plan Cards navigation and Cards/Document continuity. Then deliver
focused existing-scene editing in Plan, followed by the equivalent Play adapter.
Each is independently reviewable; no universal card store or new schema is needed
to start. This order establishes the visible target before expanding its edits.

## Observed baseline and gaps

Inspection at the base above, rather than a fresh rendered acceptance:

- [SceneCard](../../apps/live-control-ui/src/shared/SceneCard.tsx) already shares
  semantic Markdown, choices and media reading between Plan and Play. It renders
  an entire scene body; it is not a generic stored entity or an editor.
- [WorldPlanCardProjection](../../apps/live-control-ui/src/planSurface/components/WorldPlanCardProjection.tsx)
  derives marked Beat/Scene/Choice/Option projections. Its focused reader has
  body-level Previous/Outline/Next controls, repeated basis/target information,
  and “Select for Edit” for a Compose target. That button is not direct editing.
- [PlanSurfacePage](../../apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx)
  keeps its document editor mounted but hidden in Cards. The Cards projection
  itself unmounts on returning to Document; its local scene focus is not a durable
  cross-view cursor. Image insertion currently excludes Cards mode.
- [PlayCurrentMomentCockpit](../../apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx)
  already supplies compact shared-navbar scene traversal across Beats, explicit
  inspection versus Make Current, and current-scene notes. Reuse this behavior.
  Notes, progress, content editions and inspected position have different owners.
- [PlaySessionContentEditor](../../apps/live-control-ui/src/playSurface/content/PlaySessionContentEditor.tsx)
  edits the full session Markdown with visual/source modes, media and autosave;
  it can jump to the current scene. This does not yet establish editing the scene
  being inspected directly within its card.
- [Effective content admission](../../apps/live-control-ui/src/playSurface/playRunEffectiveContent.ts)
  validates the original Run basis and edition bytes before projection. The
  [scene-edit bridge](../../apps/live-control-ui/src/playSurface/agentEdit/playSceneEditBridge.ts)
  already checks exact saved scene/Run/edition context and reviewed Before/After.
  These are assets to preserve, not missing capabilities to rebuild.

The unresolved experience is a stable place to read, navigate and edit, including
dense content. Neither a new visual shell nor a “card saved” database would solve
the current target and continuity gaps.

## Decisions and alternatives

| Question | Alternatives | Recommended decision |
|---|---|---|
| Unit | Card always equals scene; every block is a card; arbitrary universal object | Scene is the stable navigation anchor; cards are purposeful facets within it. Existing semantic blocks/sections inform facets, not every paragraph. |
| Scene with too much content | Truncate; create scenes automatically; one unlimited undifferentiated card | Keep a primary scene card and named detail cards/disclosures. Preserve source order and expose all content. Splitting a view never changes scene structure. |
| Identity | Persist a parallel card hierarchy; reuse Graph IDs for UI sections | Use existing scene IDs. Facet locators are derived presentation state tied to the document/edition and structural anchor; invalidate them if the source changes. They are not durable Agent targets. |
| Editing | One editor/save controller per card; read-only Cards forever | One owning document editor/transaction history, presented at the selected scene. Plan and Play have separate save adapters. |
| Navigation | Another body toolbar; shared navbar plus repeated headers | Use established surface contributions for view, scene, traversal, edit and status. The content starts with its title and runnable material. |
| Media | Make the image object own location, roster, notes and navigation | Retain asset identity and occurrence presentation. Map semantics, pins and linked entities stay separately owned. Critique a concrete missing responsibility before extending the media object. |

## Information capacity

A card should answer one immediate table question: “What do I say?”, “What should
I track?”, “What can happen?”, or “Where do I look?”. The scene provides the common
context. Do not force every scene into the same fixed-height rectangle.

Use two reading levels: a primary face with title, authored Read Aloud and the
most immediate authored cues; then explicitly named detail. Target roughly one
desktop viewport for a short primary scene, and a readable single column on
narrow screens. As a starting fixture, three to five short cue bullets plus a
short Read Aloud block are scannable; these are comparison targets, not word
limits, save rules or permission to omit content. A long Read Aloud remains whole.
If it dominates the view, show its length and a clear full-reading state rather
than silently clipping it. Avoid nested scroll boxes for ordinary prose.

Long scenes get section links and named disclosures with counts/labels. Never
fold an immediate warning, current decision, selected consequence or unsaved
edit into an undisclosed overflow area. Defaults use explicit semantic blocks or
section boundaries; no LLM summary or guessed “important” paragraph is required.
Unmarked material remains reachable in original order through “Full scene” and
Document. Session-wide instructions need a visible “Session instructions” route;
they must not be reassigned to whichever scene happens to precede them.

| Synthetic fixture | Primary face | Detail/fold/open behavior |
|---|---|---|
| **Lantern Gate:** 90-word Read Aloud, four GM cues | Title; full Read Aloud; cues; immediate warning | No forced split. Notes remain session state, outside the source body. |
| **Glass Regent:** dense two-page boss mechanics | Scene cue and reference to the accepted creature; existing admitted glance fields only | Open complete statblock as linked detail, retaining scene position. If mechanics exist only as embedded source, show them in full scene detail; do not invent an entity or omit abilities. |
| **Harbor Census:** map and 18-row roster | Map occurrence at useful size; named “Roster · 18 entries” and “Arrival conditions” | Open map detail and complete table with headers; no silently dropped rows. On narrow view, large tables may scroll horizontally within a labelled region. |
| **Choose the crossing:** three authored options | Prompt, all option labels, selected outcome in Play | Option elaboration may fold; selecting remains an explicit existing Run command. Reading another option never selects it. |

Representative outlines (presentation only):

```text
Shared surface row:  Document / Cards   <  Lantern Gate  >   Edit   Images   Saved

LANTERN GATE                     [primary scene card]
Read Aloud — complete authored passage
GM cues: lantern signal / closed gate / approaching patrol
Warning: the patrol arrives after the third signal
Choice: wait / negotiate / take the canal
[Map]  [Roster · 18]  [Full scene] [Session instructions]

HARBOR MAP                       [opened detail; same scene remains selected]
Existing image occurrence       [back to Lantern Gate]
Roster · 18 entries             [complete table; optional separate detail]
```

The boss sheet is a linked object presentation when such an object exists; the
map is an asset occurrence; the roster is authored table content. A shared visual
frame does not make their storage, edits or permissions identical.

## Editing and human/Agent parity

“Edit scene” names the scene visible to the human, including an inspected scene.
Entering edit does not Make Current. Plan edits its document; Play edits the
versioned session copy and leaves the Plan and original accepted Run basis intact.
Keep the [edition](../Plans/HANDOFF-PLAY-run-local-content-editions.md) and
[editing](../Plans/HANDOFF-PLAY-session-copy-editing.md) contracts: exact bytes,
frontmatter, structural guards, CAS, journal-before-send and same-command recovery.
Existing scenes remain the first editing scope.

Use the existing whole-document editor as the sole draft/undo owner. A focused
editor is a constrained presentation of its scene range, not a separate fragment
with its own autosave. Resolve that range from canonical markers on each current
editor state; preserve other scenes and metadata. If the current editor cannot
provide safe scoped editing, first use the same mounted editor positioned at the
scene with clear boundaries, then separately review a bounded range adapter.
Do not claim a jump alone delivers inline editing.

Both visual Markdown and source editing must remain available. Source mode shows
the selected body with structural envelopes protected, plus an explicit route to
the full Document. Existing media resize, move, authored collapse and insertion
use the accepted document media bridge. Moving an image occurrence is not moving
its shared asset or changing a depicted location/Graph entity.

Switching Cards/Document or opening linked detail preserves the document owner,
draft generation, pending command, selection/caret bookmark, undo history and
scene focus. Restore bookmarks only for the same identity and compatible editor
generation; a removed/stale anchor gets a visible fallback. Do not recreate the
editor merely because the view changed. Acknowledgments of older drafts cannot
replace newer text. Conflict/unknown states remain actionable and recoverable;
reopen restores pending drafts before enabling another write. Undo is an editor
operation that may save a new revision, not deletion of accepted history.

The Agent must state its actual target and whether it sees saved content. The
current saved-context contract does not include unsaved keystrokes. Keep new
mutation requests blocked while their required source/notes are dirty or pending;
invalidate stale scene/World/Run/edition proposals, including A→B→A. Before/After
review applies through the same owning writer. Inspection alone must not silently
retarget the existing current-scene Play Agent bridge; a future inspected-scene
Agent target needs its own explicit adapter and tests. Human editing need not
wait for that extension. Editing reference placement/label in Markdown never
authorizes editing the referenced source or publishing Graph facts.

## Navigation and notes

Plan's shared surface row owns Document/Cards, scene selection and compact
Previous/Next, Edit, Images and the actual save status. Play retains its existing
Load, scene traversal and Return to current, and labels “Inspecting …” when needed.
Scope the scene selector by Beat with readable titles, not UUIDs. Scene traversal
follows the displayed scene. Presentation facets use compact local section links;
do not overload scene Previous/Next with map, creature or paragraph traversal.

Linked detail opens in the existing detail/peek mechanism with a clear return
target and keyboard focus restoration. It preserves the scene, draft and scroll
bookmark. On narrow screens use a full-width detail view with Back rather than
squeezing two columns; verify wrapped shared controls and reachable content below
the measured chrome. Tab/Enter operate controls and selects; shortcuts must not
steal arrow keys from text editing. Escape closes detail before returning from
inspection, and restores focus to its trigger. No duplicate control/status block
should precede the scene title.

Collapsed notes stay in the navbar, explicitly naming the **current** scene even
while another is inspected. Expanded notes remain movable, with the same mounted
writer and pending draft. Closing detail/editor/cards must not close or retarget
the note controller. Read-only notes for an inspected scene, if shown, must be
labelled separately; they are not an alternate write target.

## First implementation recommendation

**CARDS: retain Plan scene focus across shared navigation and view switches.**
One invariant: the same existing scene stays selected and reachable while the GM
navigates Cards and Document, without changing authored or Run state. Lift Plan
scene focus/bookmarks to the existing Page/controller identity and publish compact
scene controls through the shared surface host. Remove the duplicate reader nav
and move basis/Agent diagnostics into accessible details; retain visible errors.
Keep edit-target and saved-context truth explicit. Do not introduce a new writer.

Observable acceptance for the eventual implementation handoff:

1. A synthetic three-scene/two-Beat Plan: choose scene two, Previous/Next/select
   traverse predictable scenes; Document opens at its canonical heading; returning
   to Cards retains it. Repeat at desktop and narrow widths using real host controls.
2. Keep an unsaved Markdown/media edit, caret and undo history through those view
   changes and linked-detail open/close. Autosave/reopen retains exact content and
   occurrence attributes. Navigation without edits creates no content revision.
3. World/document replacement and stale callbacks, including A→B→A, cannot move
   the new selection or apply an old target. Late saves preserve newer drafts.
4. Keyboard/focus and long-scene access work without horizontal page overflow;
   no title is buried under duplicated state panels. Use all four fixtures above.
5. Existing Play current/inspection/notes behavior and accepted save/recovery
   regressions remain valid. No Run progress mutation is caused by Plan browsing.

The first slice does not close direct-card editing acceptance. Next, design one
Plan existing-scene edit adapter, then the Play session-copy adapter; prove each
with actual edit → autosave → switch → reopen and another-scene preservation.
Keep UI source leases serial around Page/SceneCard/navbar seams.

## Later boundaries and decisions

Later slices: the two focused edit adapters; dense-scene facet/detail presentation;
explicit create/reorder/remove with stable scene IDs (Plan first, Play requires a
separately reviewed structural contract); inspected-scene Agent edits; Graph-linked
map pins or richer shared-object editing. These need their own activation/leases.
No card database, universal entity, inferred publication, media redesign, combat
rewrite or automatic scene splitting is proposed here.

No blocking operator decision is needed to implement the first recommendation
after design review. Density defaults remain an operator acceptance judgment on
short and dense fixtures, not an excuse to freeze arbitrary truncation rules.
This proposal does not accept the broader J2/J5 or shared Plan/Play journey.
