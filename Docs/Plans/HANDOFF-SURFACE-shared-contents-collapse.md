# Shared Contents book and collapse interaction

Status: COMPLETED; exclusive lease released. Owner: PRIME / Buddy surfaces. User explicitly authorizes shared
Plan/Play Contents implementation, review, merge and delivery on 5202.
Base: 5bfe65b77 (resolve full origin/main); branch codex/shared-contents-collapse.
Topology: serial, one PR, reused buddy-context-loop checkout. Open PRs inspected;
no overlapping current shared Contents lease. Predecessor #1473 completed.

## Exclusive write lease
- This handoff
- apps/live-control-ui/src/shared/Contents.tsx
- apps/live-control-ui/src/shared/Contents.css
- apps/live-control-ui/src/shared/Contents.test.tsx
- apps/live-control-ui/src/planSurface/components/PlanCardDeck.test.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCockpitPanels.tsx
- apps/live-control-ui/src/playSurface/currentMoment/PlayCurrentMomentCockpit.tsx
- apps/live-control-ui/src/playSurface/playSurface.css

## Contract and risks
One shared native book toggle and shared disclosure/focus behavior for both
surfaces. Escape collapses and returns focus. Narrow selection dismisses the
panel; desktop selection retains it. Retain each surface's responsive layout
owner and Play overlay coordination. Hiding Contents must not unmount editors,
change current Run progress, scene cursor, drafts, notes or saved documents.
No API/storage/provider changes. Shared IDs must remain unique. Preserve existing
Play focus refs and test hooks while removing its duplicate toggle markup.

## Gates
Focused shared/Plan deck/Play cockpit tests; production build; cumulative diff
review by Architecture; exact approved-head merge. Adopt existing 5202 UI dist
with prior assets retained, no API restart. Verify desktop/narrow both surfaces,
mouse/keyboard toggle and scene continuity; all protected stored responses and
active selection unchanged. Postmerge settle handoff and release lease.

## Rendered gate correction
PR #1474 merged at 51e1c0970eab2c512a59272116952921b1f342f2;
Architecture Cycle 1 approved 9e76fb3e6fca7306867fd95fea33f7c5818c2f8b.
Desktop source behavior and 76 tests passed, but narrow 666px rendered acceptance
found dismissal focus targeting a hidden navbar Contents opener. Delivery is not
accepted yet. Same bounded capability continues serially in correction branch
codex/shared-contents-focus-fallback from that merge, one correction PR. Existing
lease remains ACTIVE, including shared and Play files/tests. Add a visible-opener
fallback in the shared dismissal contract; Play supplies More as fallback. No API,
stored state or provider changes. Review correction independently before adoption.

## Final settlement — 2026-10-19
Correction #1475: Architecture Cycle 1 approved exact head
bd11e888a05fd94bb76720c2a00bb3194bf16495; merged
c9fae15c27e2e1d50e63f61d4408a0aaf731985e. Focused tests 77 pass and
production build passes. Both reviews independently reran their focused cohorts.
5202 index SHA256 64237a5be4d5b5dc8402d35f2121741fbba2d94df50cb5cac99486c5b833d532.
Desktop Plan/Play book collapse/keyboard expansion/Escape pass; collapsed rails
52px and book40px fit. Plan editor HTML and selected scene remain unchanged
through disclosure. At666px Plan selection dismisses and returns focus to book;
Document/Cards retains selected First sight scene, then restored Journey north.
At666px Play Escape/book-close returns focus to visible More; scene selection
closes panel and focuses inspected heading, retaining current-scene Notes.
No horizontal overflow. All13 protected responses (including Plan, Run, review,
notes and active selection) remain exactly unchanged before both rollouts and
after browser checks. No API restart/provider call. QA tabs closed, viewport reset.

Optional older integration test `retains the same editor, draft media, caret and
undo history while browsing scenes and switching views` fails looking for retired
`world-plan-scene-reader` on both correction head bd11e888a and untouched prefeature
base5bfe65b77f4566cda15fb5f9e8840a2b26c8c08b, same error line191. This inherited
test failure is not counted as passing. Rendered HTML/scene checks do not establish
full draft-media/caret/undo coverage. Auto-review initially rejected adoption on
that failure; after baseline comparison established inherited failure, normal
review accepted the guarded adoption. Logs retained in established private evidence
location as shared-contents-draft-continuity{,-base}.log. No unrelated test rewrite.
