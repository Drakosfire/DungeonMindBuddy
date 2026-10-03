# Rendered acceptance evidence

Verified against the running isolated prototype http://127.0.0.1:5203/ through native in-app-browser controls. These are labeled rehearsal edits/outcomes, not actual campaign events. Existing production Plan revision 5 and both source files were not written by these experiments.

## 1. Opening → rescue choice → aftermath

Opened Something Is Still Moving, switched to Play, selected `option:save-sleepers` and `option:rally-mireward` together, recorded a local note that sleepers were rescued while townsfolk blocked the route and a carrier escaped, then used Next scene to reach Count the Living. Accessibility state confirmed `scene:count-living`, the outcome text, and both selected IDs. Source-linked optional follow-ups to the clinic and recovery scene now render in the journal; the underlying activate/suppress attributes are preserved and all navigation remains available.

![Opening card and separate local outcome](evidence/opening.png)

## 2. House map → room → interaction / discovery

Traversed Session29's Connected place → Ironveil House → The House. Floor-grouped map lists the nine source-described spaces, explicitly without inferred adjacency/residence. Opened Lysandra's Old Room, reviewed its source material, selected `option:room-ask` in Play and recorded a clearly labeled rehearsal about asking after the repaired practice sword and respecting private papers. Reload showed the saved outcome. After refinement, the room offers Character/context, Current contents, Still hers, Papers/investigation, Possible finds and key tone separately. Also traversed Family Kitchen → related Kitchen Table → Read aloud and verified the existing breakfast dialogue.

![House map](evidence/house-map.png)
![Focused room and local discovery record](evidence/room.png)
![Kitchen read aloud](evidence/kitchen.png)

## 3. Plan edit → Play → outcome → Plan

Edited only the opening scene in the local preparation buffer to add `PROPOSED — prototype rehearsal: A runner holds a spare blanket beside the gate.` Applied through the card editor, switched to Play and performed the simultaneous rescue test above. Returned to Plan: the proposed sentence remained in Situation while the journal retained its separate `RECORDED · LOCAL` record. Reload preserved both. No production apply, native graph call, database mutation or model call occurred.

Attempted changing `option:save-sleepers` to a new ID: Apply rejected the edit and displayed the exact marker to preserve. Cancel kept the prior preparation intact. Attempted adding `node:invented-prototype-check`: Apply rejected the unverified node reference. Verified insertion control added the exact existing `loc:ironveil-warehouse` Markdown link at the cursor; canceled that test before saving.

## 4. Cards ↔ full document

Switched opening card → Document → Return to focused card → Edit. Compared the text area before/after: exact equality. Full-document rendered text included the proposed sentence, The Failed Rain, and the original final Session29 success-condition sentence. The House full document retained its original ending, all named House scenes, and the newly authored local rehearsal scene. Return restored Kitchen Table's Read aloud block. The renderer reads one canonical local Markdown buffer per source; it does not produce a second slide document.

An unfinished outcome note survived block navigation and reload (both DOM value checks true); the temporary test note was then cleared. Action selections have the same per-scene local persistence.

## Guided creation / deterministic validation

Create scene rejected advancing with an empty required field. Completed the six-step workflow with a labeled Sharing blankets rehearsal, structured action/consequence pairs and unlinked reference notes. The scene appeared in the index and focused-card view, with generated local IDs, proposed status, simultaneous actions, and a generated unexpected path. The source fixtures retain their original 19/7 scene counts; only this browser's prototype state includes the additional scene.

![Locally authored scene](evidence/created-scene.png)

## Automated owning-model evidence

`verify_fixture.py`: exact source/fixture equality, original source hashes, reversible 72 node links, original 90 markers. `model.test.mjs`: 19 scenes/10 Beats/9 choices/52 options; seven House scenes/nine spaces; precise scene edit boundaries; exact marker preservation; simultaneous outcomes without prep mutation; serialization; guided block/choice validation; unexpected-action generation; room focus; rejection of unknown node links and acceptance of explicitly verified identities. Tests passed after final model edits.

## Honest limits

This is a usable standalone prototype with browser-local authoring/session state. It does not integrate with production Agent, Graph, semantic editor or Combat Tracker. Source status labels are preserved author claims; a rendered ESTABLISHED label is not new verification. The original imported documents and active product owner leases remain untouched. Review/adoption into production is a separate owner decision.

Final preservation audit limit: a fresh read-only request to the previously known production API on 7866 returned connection refused, and the historical runtime checkout path was absent in this execution environment. No production restart/reconstruction was attempted. Preservation claims are bounded to this lane's no-write/no-call behavior, unchanged repository source hashes, and the earlier saved revision receipt; current external runtime availability/revision cannot be re-certified here. The prototype remains independently accessible on 5203.

Final boundary repair: source-level H1/H2 reference sections (GM Running Notes / House Tone) are outside scene edit ranges rather than accidentally bundled into the last option. Model checks prove editing either last scene leaves the global section intact. Browser verification showed the storm editor excludes GM Running Notes while Intent/source context → Document still contains it. The opening screenshot was refreshed after this repair. Verified-reference select now has an explicit accessible label.

## Compact layout follow-up

Renamed the scene index Outline and the outcome journal Play notes. Added independently persisted panel toggles (notes closed by default), explicit grid placement so content reclaims hidden columns, and a compact scene toolbar containing title, block/count and prep status. Removed repeated card heading and only matching leading block labels; source Markdown is unchanged.

Syntax, model and fixture checks pass. This follow-up could not receive fresh browser acceptance: the in-app browser returned connection refused for 5203 despite the restored host listener returning HTTP 200. Existing screenshots above show the prior accepted layout, not this follow-up. Toggle/reload visual acceptance remains pending.

## Node context and choice clarity follow-up

Browser connectivity recovered. Verified Warehouse inspection shows two connected scenes with source excerpts and scene navigation controls; IDs/provenance are behind Advanced. Choice disclosure has an Explore choices callout and explicit expansion hint. Expanded rescue consequences show victims recovered / possible creature escape and later effect, with no repeated option label or choice title. Source Markdown remains unchanged. Screenshots: `evidence/node-context.png`, `evidence/choice-callout.png`. Syntax, model and fixture checks pass.

## Direction checklist follow-up

Compact single-line Choices disclosure; source Location remains visible across block tabs. Browser checked a rescue option in Plan and logged it, showing a new separate local direction record and preserved prior notes. Fixture/model checks pass, including suppression across Beat scenes, later activation and document isolation. Export retains stable choice IDs plus readable labels/timestamps for later recap input. Flags never disable scene navigation.

## Retained decisions and unexpected action notes

Fixed clearing of logged checklist selections; migrated existing logs back into scene selections once. Browser verified Prioritize the sleepers remains checked after Next → Previous and refresh. Renamed the optional sidebar Decision log and explained browser-local storage / Files export. Logging no longer forces the sidebar open; unchanged repeated submissions are guarded. Something else has a persistent note field that selects that action while typing and stores its text with the direction record. Screenshot: `evidence/retained-decisions.png`.

## Shared writing pad and default unexpected action

Added a bottom floating Notes button and resizable non-modal writing pad, shared across scenes and documents. Browser verified typed text survives Next and refresh; removed only the test text and returned to the original scene. Open state also persists. Markdown export is separate. Every choice group now supplies the unexpected-action note UI, reusing an explicit source option or a local fallback. Source fixtures remain unchanged. Screenshot: `evidence/shared-notepad.png`.

## Lysandra character view

Replaced the preparation-only Lysandra popup with a source-backed character view: role, formatted family/ally ties, dossier, Mireward family/place history, saved routed Session 20 timeline and CR4 statblock with baseline CR2 link. Copied sources verbatim into node-sources, with original paths in provenance.json. Browser verified character and statblock tabs. Timeline explicitly declares partial saved coverage; this is not live Graph integration, current statblock lifecycle resolution or a full cross-session chronology. Rank disagreement is preserved in Sources & coverage. Generic context excerpts now use Markdown formatting. Screenshot: evidence/lysandra-character.png.

## Scene completion

Added a reversible Complete checkbox to the scene toolbar. Browser verified opening scene shows a checkmark and computed line-through style after refresh and remains clickable after navigation. State keys include document and scene identity; no source or decision record is changed. Screenshot: evidence/scene-completion.png.

## Full session backup

Added Files → Back up full session. Browser downloaded the operator snapshot into Downloads; file validation confirmed format and drafts/outcomes/actions/completedScenes/playPad/otherNotes keys. Private backup contents are not committed. Restore-file UI is not yet implemented.

## Sensory situation prose

Situation cards now include an At the table passage using existing quoted read-aloud text. Added preparation flavor for nine scenes without read-aloud passages in scene-flavor.json; source fixtures and operator drafts remain unchanged. Browser verified both clinic source prose and newly authored claim-hours prose. Screenshot: evidence/sensory-situation.png.

## Visible Play notes autosave

The writing pad displays Saving… then a successful save timestamp in operator America/Denver time. Storage failures show Not saved and suggest export; the prior successful timestamp is retained internally. Browser verified Saving… and timestamp receipt while preserving the exact existing note text. Operator notes/screenshot remain outside Git.

## Choice-note autosave and Hybrid reference

Something else fields show Saving… then a saved timestamp, with per-choice receipt persistence and explicit storage failure feedback. Browser verified the transition with exact operator note text preserved; private screenshot stays outside Git. Opening scene now exposes Fleshborn Hybrid CR3 through a monster-reference pill. Source copied verbatim with provenance; browser verified AC13, HP45, actions including Flesh Lash and Consume the Weak. This is a corpus reference, not verified native Graph binding to the transformed refugees.

## Scene-specific notes

Added Scene notes under each card, keyed by document and scene. Browser verified text field and save receipt survives refresh. Removed only verification text; operator writing pad remains unchanged. Scene note state is included in full-session backup. Private screenshot stays outside Git.

## Meat Mind HP comparison

Added a toolbar creature view with the saved Session 26 round 4 provisional 155/200 HP snapshot, graph-backed creature description, known statblock binding, and an autosaved operator current-HP field included in full-session backups. Current HP is explicitly a local play record, not live combat synchronization. Exact spawn costs remain unverified; no capacity is invented. Separate browser tab verified the snapshot, empty-current state and mechanics disclosure without editing active play data. Module syntax, model tests, fixture verification and diff whitespace checks passed.

## Scene threat browser

Replaced the single Meat Mind toolbar shortcut with Threats: scene threats are distinguished from session references, with creature/HP and Hybrid statblock views and return navigation. Presence is limited to explicit prepared warehouse and Meat Mind investigation scenes; conditional references do not imply an active encounter. Browser verified opening the roster, Meat Mind details and return without changing active play state. Syntax, model and fixture checks passed.
