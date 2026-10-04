# DOGFOOD card adoption inventory

Bounded adoption support · 2026-10-03. This inventory consumes Buddy main `d9b7d1e1ef9c1ad4401e107694260ad4f19455b6` (`ROADMAP-demo.md`, Card adoption direction; `STEWARDS-HANDOFF-demo.md`) and OverMind main `de0cd3b7e7907db46219186b3e3a0092f6e97bbc` (Buddy card adoption coordination). Prototype reference: PR #887 at `5e2ef9f144e18f643dc1caa8316904dbfc801236`. Frozen comparative renderer: `f11be03c70f0c7f7f7cfb2c89933853cb7f49c87`. Source/operator gold acceptance and J1–J6 acceptance remain separate.

No production implementation or runtime replacement is authorized by this inventory. Keep operator 5202 and DOGFOOD 5203 running. Current production collision surfaces include #904 Agent composer, #886 navigation/EditHost, and #869 movement controls. DEMO owns the first ACTIVE production card handoff; APP-STATE owns durable Run state, SERVER runtime/auth, ARCHITECTURE contract critique, and PRIME exact-head review/merge.

## Behavior worth adopting

| Behavior | Existing prototype witness | First production implication |
| --- | --- | --- |
| Card / Document | Small scene card and long-form view consume the same preparation. Session29 edits preserve scene boundaries and stable markers. | Project the selected saved World Plan; prove equivalence, supported edit → Apply → Save → fresh reopen. Do not create another document authority. |
| Lenses | Situation, Read aloud, Do now, GM only, Relevant; source boards expose Missing reference only when present. Explicitly author a missing lens. | Reuse existing scene/block/callout grammar where lossless; absence must not become generic filler or fabricated content. |
| Choices | Prominent compact disclosure, simultaneous checkboxes, default unexpected-action writing, explicit decision log. Existing effects flag later scenes without hiding or locking them. | Separate authored alternatives, pending selections, submitted decisions and actual outcomes. Preserve option IDs and nonexclusive choices. |
| Navigation | Grouped collapsible outline, search, current title in local toolbar, reversible Complete mark and strike-through. Conks/Sheep use nonlinear groups and cited conditional links. | Coherent selected-card identity across outline, editor, references and Agent; completion is recall support, not an access rule. Source order is not canonical chronology. |
| Place / maps | Glanceable location; House room focus; selected map/image inspection with source identity and audience. | Use admitted location/media references; a map association does not prove adjacency. Preserve audience and source; unavailable reference stays explicit. |
| Entity / threat | Compact pills, contextual profiles, scene/statblock/history references and creature notes. | A pill promises coherent entity inspection. Corpus excerpts do not equal live Graph, chronology or encounter state; HP must bind to the actual encounter. |
| Writing | Floating shared pad across cards, contextual scene/creature notes, choice notes and visible saving/saved/error receipts. | Keep low-friction global writing plus contextual writing; saved receipt must name durable destination. Do not make classification a prerequisite to typing. |
| Construction / styling | Direct typed blocks, source-media selector, reorder/undo, live resizable pane; colors/fonts/spacing controls with Advanced JSON, explicit Apply/reset. | Useful later evidence. Full style controls are not required for first saved-Plan card projection; preserve accepted visual hierarchy. |

## Representative fixtures and existing evidence

- **Session29, primary:** `content.json`, `scene-flavor.json`, `model.js`; 19 session scenes, 10 Beats, nine choices / 52 options. “Something Is Still Moving” exercises multiple choices and unexpected direction; “The Warehouse Becomes a Clinic” exercises location context; Ironveil House adds seven marked scenes / nine spaces. Original source/90 markers and reversible supplied-node links are checked by `verify_fixture.py`. See `SESSION-29-REVIEW.md` and existing public evidence screenshots.
- **Conks, comparative/private:** 19 source pages / 114 retained OCR units / 47 cards, including reference/back matter. Use opening/exploration, separately triggered family dialogue, conditional escalation, tactical map and tree statblock. Two C045 reviewed corrections are explicit derivatives; original OCR remains readable. Do not equate 47 cards with playable-scene count.
- **Sheep, comparative/private:** six source pages / 135 retained units / 23 cards, including references. Use opening/read-aloud, compound map, conditional retreat, contextual entity profile and direct prose + media construction. Do not equate 23 cards with playable-scene count.
- Private frozen candidates contain board/manifest/PDF/media/play/config/history and renderer: Conks 19 files, Sheep 21. All hashes verified, including exact Git renderer correspondence. `capture_candidate.py --verify` checks the same reviewed snapshot. Private corpora, media, snapshots and session exports stay outside Git; no new provider treatment is implied.

## Browser-local boundary and round-trip risks

Session29 uses `dmb-plan-play-cards-v1`: edited Markdown drafts, document/scene/lens/view selection, completion, pending choices, outcomes, unexpected notes, global/scene/creature writing and local encounter adjustments. Private boards use `dmb-private-board-v1:<adventure>:<dataset-pin>`: authored overlays, typed composition drafts/history, theme, navigation, completion, choices/decisions and writing. These are single-browser rehearsal state, not committed World documents, durable Runs or Graph canon.

Session29 full-session export was inspected after operator play; it includes rehearsal/duplicate decisions and must not be silently canonized into recap. Its original runtime export differs from later shipped threat features. Private-board current Download → file → Review → Restore → re-export proved exact state equality. Previous-revision recovery archives current state and copies explicitly; unmatched references remain. These later recovery checks do not retroactively prove every Session29 feature or crash-safe/cloud/multi-user persistence.

Production risks to prove at the owning boundary:

1. Card/document projection must preserve source bytes or supported semantic equivalence, playable IDs, links, callout audience and protected structure through editing and Save/reopen. Prototype parsing is purpose-built Markdown, not the production semantic editor.
2. Switching World/document/card during an async proposal must fence late results against exact revision/draft/selection and active Agent binding. Local proposal guards are design evidence, not native integration proof.
3. Authored adaptation, source OCR, reviewed correction and proposed connective text must remain distinct. Joining contiguous compatible spans improves reading but does not establish semantic correctness or player-safe disclosure.
4. Keep preparation and actual Run actions separate. Choice selections, notes, rolls and combat values need durable identity/recovery; browser state must not be copied wholesale into production authority.
5. Sparse entity relations, flattened source typography, unresolved rule-version bindings and incomplete chronology remain. Maps and supplied statblocks are not full Graph/asset adoption.

## Observed usability and first adoption witness

The operator reported Session29 mostly worked and felt good, strongly accepted the aesthetic, and estimated about 80% of preparation went unused. That supports small focus, optional depth, nonlinear access and writing—not a measured scene-utilization rate or acceptance of every feature. Metadata, duplicate headings and giant spacing repeatedly failed. Initial node inspection failed the expected profile/timeline/statblock experience. Scene location and visible autosave were explicit requirements.

Agent-run construction/style/refresh/recovery trials are recorded in `PRESENTATION-GOLD.md` and `EVIDENCE.md`; they are not independent operator speed/fidelity acceptance. Preserve slate workspace, warm content card, compact sage controls, small pills, readable measure and tool/content distinction in design-v1.

DEMO's first witness should use the existing saved Session29 World Plan: select a card and lens; compare Document; make one supported edit; explicit Save; fresh reopen; verify unchanged IDs/links/audience and coherent navigation. Keep Agent card targeting, durable Play/Run actions and COMPOSITOR admission in their bounded successor contracts. No first-card dependency on full adventure ingestion or every style control.
