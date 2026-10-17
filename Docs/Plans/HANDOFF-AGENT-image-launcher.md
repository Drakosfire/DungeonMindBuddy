# AGENT: image-only conversation entrance

Status: ACTIVE. Operator explicitly requested during live Build dogfood: remove the visible Conversation label and enlarge the existing image approximately 20%. PRIME implements; ARCHITECTURE independently reviews. Serial successor to merged conversation history repair #1370 at a8830ac9bb6356b605e6de4fbdbd13a0bfd532c5. Existing buddy-tool-denial-delivery checkout; branch codex/conversation-image-launcher from that fetched main. Open PR inspection found no overlapping active implementation (Combat adoption remains blocked; MEDIA #1306 held).

## Invariant and failure cases

The existing shared Build/Plan dock entrance is image-only, with its image 2.1rem instead of 1.75rem. Keep the existing accessible button name, title, keyboard opening, hit area, focus return and draft/history state. Removing the adjacent text must not remove the actual button or create a second launcher. No generic dock fallback or other surface changes.

## Exact write lease and delivery

This handoff; apps/live-control-ui/src/planSurface/components/PlanConversationDockAdapter.tsx and PlanConversationDockAdapter.css only. Remove adjacent visible span; enlarge image. Existing dock tests and UI typecheck, cumulative diff inspection, commit/push and one PR. Independent review before merge. No new tests for this reversible presentation-only change; verify actual rendered entrance and opening/closing without sending or modifying document content.

5202 static output remains /home/drakosfire/.local/state/dungeonmindbuddy/rollout-candidates/buddy-main-af6779d/ui-dist. Preserve current served baseline a93ff4d2f2dea2711bae65ebd3595e4e206031d3 plus reviewed #1370 components; overlay only the two leased files after review. Existing private pinned-source build tooling/output; no new worktree, source export, environment or server. API8000, native8001, APP0030 and user tabs/drafts unchanged; do not force reload. Foundation goal stays paused. Missing Edge history is a separately investigated dogfood issue, outside this implementation lease.
