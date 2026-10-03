# Session 29 — Plan / Play dogfood review

2026-10-03 · prepared for PRIME · prototype PR #887

## Judgment

Preserve this as **design v1**. The operator reports that the session went quite well, mostly worked, mostly felt good, and that the aesthetic is a major reason to preserve it. The operator believes the players also had a good experience; no independent player feedback was collected. This is meaningful acceptance of the direction, not proof that every feature worked or that the prototype is production-ready.

The central product finding is that a prepared session can be useful even when most of its material is unused. The operator estimates about 80% went unused. The design should support finding, using and leaving material freely rather than rewarding completion of an adventure outline. The successful unit appears to be a small, readable scene with optional depth, surrounded by navigation and a place to record emerging play.

Recommend preserving the visual and interaction baseline immediately, then graduating its content, writing and reference contracts into Buddy in bounded slices. Do not rebuild the current production long-document experience and merely apply these colors.

## Evidence and its limits

Reviewed the full-session export produced through the live page's Files → Back up full session at `2026-10-03T22:23:24.734Z`. The private backup is `/home/drakosfire/Downloads/DungeonBuddy-session-backup-2026-10-03 (1).json`. It contains two preparation drafts, four outcome rows, the shared notepad, pending choices, unexpected-action notes, completion marks and scene-note state. Raw play data remains outside this PR.

Three scenes have completion marks: Something Is Still Moving, Count the Living and “Oh Shit, the Rock.” This is not a scene-usage counter. Unmarked scenes may have been used, completed scenes may have been marked during setup, and no visit/dwell telemetry exists. Three of nineteen prepared session scenes therefore must not be presented as a measured utilization rate. The operator's approximately 80% estimate is the available usage assessment.

Two outcome rows explicitly say prototype rehearsal. Two more repeat Prioritize the sleepers at nearby times; they came from the earlier dogfood interaction and cannot be promoted automatically to played canon. The only nonempty unexpected-action note says that the players prioritized discussion/planning while the meat monsters began walking out. The scene-note map has one empty entry. The shared writing pad supplies the richest session evidence.

The completed-session tab was still running an earlier loaded bundle: it showed the Meat Mind shortcut rather than the later Threats button. Its export has no creature-notes or current-HP fields. Threat browsing and creature notes were implemented and verified separately, but this session does not demonstrate that the operator used them. Distinguish shipped prototype behavior from at-table adoption.

## What worked, and why

### A comfortable reading surface

The strongest explicit acceptance is visual. A dark slate workspace frames a warm parchment card; muted olive/sage controls and small node pills fit the fiction without becoming decorative noise. The card has a clear edge and comfortable reading measure. Warm content and cooler controls make it easy to distinguish the material being read from the tools used to navigate it.

Serif scene headings and sensory prose give the preparation an authored character; system text and compact controls remain practical. This mixed typography is more useful than rendering every tool as parchment or every scene as a generic application panel. The aesthetic contributes to willingness to stay in the tool during play. Treat that as product value, not a cosmetic layer to postpone until integration is done.

### Small focus, optional depth

Situation, Read aloud, Do now, GM only and Relevant let the operator approach the same scene from different table needs. Cards avoid the overwhelming long document without discarding it: Document remains an alternate view of the same preparation. Moving the scene title and preparation status into the local toolbar reduced repeated framing inside the card.

The operator repeatedly rejected redundant headings, enormous spacing and metadata in the main reading path. The eventual pattern is content first, tools around it, diagnostic/source detail behind disclosures. Compact choices with a visible expand affordance fit this pattern. Preserve the hierarchy, not the earlier redundant text.

### Navigation that does not demand obedience

The outline supplies orientation and fast return. Collapse controls return room to the card. Complete marks give memory support without locking a scene. Source-linked consequences can flag a later route as not planned while retaining access for the GM. Those are the correct semantics for improvisational play: guidance and recall, not enforcement.

Using only a fraction of the preparation is consistent with that value. The unused material may have provided confidence or optional responses, but the notes do not establish that claim. The next review should distinguish useful reserve material from preparation overhead rather than assuming all unused content was useful.

### Writing carried the emerging session

The shared pad recorded psychic contact with the Meat Mind, an improvised root/nerve/vein connection below it, a runner to Mossford concerning manufacture and misting of the cure, interest in Thrin's cloak, and ongoing potion work. These are not a neat traversal of the supplied decision tree. They are examples of the table making its own session.

The pad also held product observations about maps, music cues, NPC relationship changes and background threads. It succeeded as a low-friction capture surface precisely because it did not demand a scene, choice or node classification before allowing writing. Keep one global pad available from every card; scene and creature notes should add contextual writing, not replace it or fragment the only reliable session record.

Autosave visibility mattered enough for the operator to request it explicitly for both the pad and Something else. A visible saved-time receipt gives useful reassurance. Local storage still leaves recovery dependent on browser state and manual exports; a receipt must identify its durability boundary honestly.

### Spatial and character references were valuable expectations

Ironveil House gave preparation a concrete place with rooms, relationships and atmosphere. The operator's questions about where a scene happens show that location belongs in the glanceable card context. They should not have to infer it from a distant outline title.

Clicking Lysandra or a threat raised a much higher expectation than seeing preparation mentions: a coherent profile, relationships, history, statblock and current encounter information. The initial reference modal failed that expectation. The failure is itself a clear product contract: a node pill promises an entity, not a search excerpt. Better corpus views are a useful intermediate step, but incomplete chronology and unavailable live state must remain explicit.

## Failures and unfinished contracts

1. **The session log is not yet recap-ready.** Rehearsal and played records share one storage stream; duplicate decisions remain; pending unexpected-action text is separate from logged outcomes. A recap pipeline must preserve all of these as evidence with status, reconcile them with the operator, and never silently canonize tests or predictions.
2. **Persistence is reassuring but shallow.** The exported backup preserves work, yet no restore UI or server-backed autosave exists. Provide a tested restore round trip, clear save destination/status, versioned recovery and conflict handling before claiming crash-safe session continuity. A copy on the same machine is not protection from loss of that machine.
3. **References do not reach the actual graph.** Chronology, relationship changes, statblock revisions and threat HP cross content/Graph/combat owners. A generic modal of nearby text cannot satisfy that contract. Cached final Meat Mind HP remains a separate recovery investigation assigned to PRIME.
4. **The navigation composition remains prototype-specific.** Production must integrate primary navigation, surface context, outline, inspectors and writing panes without overlap or pushing the canvas sideways unpredictably. The user has already identified these failures on production Plan/Ingest.
5. **Late features lack play evidence.** Threat roster and creature notes need another live trial. Do not use their presence in the branch as proof of success in Session 29.
6. **The stylesheet is an exploratory cascade.** Repeated overrides achieved the accepted result but are not a maintainable design system. Consolidate only against the pinned baseline and visual comparison; cleanup must not erase the successful appearance.

## Design v1 preservation contract

The exact accepted stylesheet is copied to `design-v1/style.css`, with SHA-256 and the pre-report runtime head recorded in `design-v1/BASELINE.md`. Existing screenshots provide visual anchors; they are prototype examples, not proof of played events. This pins a recoverable reference without freezing runtime fixes.

Preserve: dark slate chrome, parchment reading surface, muted olive/sage accents, compact inline pills, restrained serif editorial hierarchy, modest rounded borders, readable line spacing, a focused central card, compact surface toolbar, collapsible peripheral navigation, visible choices, progressive disclosure, reversible completion, and an unobtrusive floating writing tool.

Do not preserve accidentally: redundant headings, repeated metadata, large empty card minimums, truncated or unformatted entity excerpts, toolbar collisions, and speculative threat presence. Responsive/mobile behavior and accessible contrast, focus and keyboard operation still need explicit owning verification. The operator accepted the desktop experience, not an untested universal layout.

## Sequenced recommendation for PRIME

**First: preserve the v1 baseline and recovery.** Keep the current PR/reference intact. Arrange private backup retention outside browser storage and a tested import/restore flow. Adoption is separate from merge authority.

**Next: port the card-reading and navigation contract.** Buddy owns runtime presentation; content owners supply stable scene/Beat/block identities and one document for Cards/Document. Keep source preparation separate from play records. Preserve selected context across refresh.

**Then: make writing a durable session evidence stream.** Global, scene and entity notes need shared session identity, timestamps, save receipts, export/restore and explicit rehearsal/played/proposed distinctions. Save unrestricted prose first; attach semantic references without making classification a prerequisite.

**Then: fulfill the entity-view promise.** Graph resolves identity, sourced relationships and chronology; the statblock owner resolves revision-pinned rules; combat owns current and historical encounter HP. Show when and where each value came from. Enable navigation between profile, timeline, statblock and encounter without losing the card.

**Finally: agent-assisted review and recap.** Give the agent preparation plus the operator's actual notes and decisions. Have it ask targeted reconciliation questions about ambiguous outcomes and unstructured threads, then propose recap/Graph updates for review. A list of checked options alone is insufficient, and the 80% unused preparation must not leak into a recap as events that happened.

Next-session follow-ups from the writing: make imported maps accessible in context; test music cues; support evolving background threads and NPC relationship history. These are design inputs, not authorization for unrelated implementation in this PR.

## Next trial

Observe whether the operator can find a location, open a coherent entity, write anywhere and recover the session without help. Collect direct player feedback separately. Ask which reserve cards reassured the GM, which were unreachable or irrelevant, and whether writing was interrupted by navigation. Use voluntary observations and saved artifacts; do not infer success from click totals or completion marks alone.
