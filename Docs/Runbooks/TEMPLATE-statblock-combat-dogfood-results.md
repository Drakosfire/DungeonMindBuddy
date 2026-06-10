# Statblock → Combat Dogfood Results

**Run date:** YYYY-MM-DD  
**Tester:**  
**Branch / commit:**  
**Session dir:** `evals/c2_live_prep/live/session_22`  
**Backend URL:** `http://127.0.0.1:8000`  
**Frontend URL:** `http://127.0.0.1:5173`  
**Generation source validated:** lifecycle mechanics only / real DungeonMindServer generation / both

## Environment checks

- [ ] `uv sync` completed.
- [ ] Backend dependency import check passed.
- [ ] Backend started successfully.
- [ ] Frontend dependencies installed.
- [ ] Frontend build passed or blocker recorded below.
- [ ] Frontend dev server started successfully.
- [ ] Dogfood reset dry-run reviewed.
- [ ] Dogfood reset apply run completed, if needed.
- [ ] If generated corpus was purged, `--yes-delete-generated-corpus` was used intentionally after reviewing the printed file list.

## Lifecycle checklist

- [ ] Workbench loads.
- [ ] Generate/render draft.
- [ ] Store draft.
- [ ] Reload stored draft.
- [ ] Preview corpus promotion.
- [ ] Prepare corpus write.
- [ ] Confirm corpus write.
- [ ] Generated markdown file exists.
- [ ] Activate retrieval.
- [ ] Verify retrieval admits generated statblock evidence.
- [ ] Statblock View lists the generated statblock.
- [ ] Detail view reads corpus markdown.
- [ ] Add to current combat.
- [ ] Combat Roster shows entity.
- [ ] Sort initiative.
- [ ] Set active actor.
- [ ] Advance/rewind turn.
- [ ] Damage/heal/temp HP.
- [ ] Edit notes/conditions.
- [ ] Mark defeated.
- [ ] Refresh browser and confirm state persists.
- [ ] Restart backend and confirm state persists.

## Artifacts created

- Draft record: `<session_dir>/statblock_drafts/<artifact_id>.json`
- Retrieval manifest: `<session_dir>/statblock_retrieval/generated_statblocks_manifest.json`
- Combat state: `<session_dir>/combat/current_combat.json`
- Generated corpus markdown: `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Statblocks/generated/<slug>.md`

## Findings

| Step | Severity | Finding | Expected | Actual | Evidence / file / screenshot |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## Friction notes

- 

## Follow-up candidates

- [ ] Bug fix:
- [ ] UX improvement:
- [ ] Documentation update:
- [ ] Test coverage:

## Final verdict

- [ ] Ready for repeated GM dogfood.
- [ ] Needs fixes before another dogfood run.
- [ ] Blocked; blocker details above.
