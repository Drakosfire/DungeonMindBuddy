# Plan bottom conversation — integration evidence

Base: merged `de22fdefd5b3d8265f85c6b1109f5edd67db660f`. Branch: `codex/dogfood-plan-bottom-dock`. Review the cumulative base-to-head diff; this evidence is source/fixture verification, not operator-runtime acceptance.

## Actual composition

`PlanBottomDock.stories.tsx` mounts the actual PlanSurfacePage, AppChrome, WorldPlanAgentConversation and AgentInteractionChrome with their providers. Every fetch is intercepted; unhandled requests receive a synthetic 503 and are never forwarded. The document, identity, digest and completed answer are fixtures. No provider call, operator database mutation or live authentication change was performed.

Desktop inspection at 1280×720 and narrow inspection at 390×844 verified one controlled composer, one existing dragon launcher, a separate scrollable reader and message area, retained typed text across Document/Cards and collapse, keyboard resize, and contained settings/context. Viewport overrides were reset afterward. `desktop.png` shows actual readable fixture answer prose; `mobile.png` shows the narrow reader and composer visible together.

The first narrow inspection caught inherited `.app-shell-layout { display:block }` forcing the dock below the long page. The final opted-in bounded layout restores flex only for the owning Plan shell. The oversized inherited dragon bar was also corrected with adapter-scoped rules. These defects were caught in the mounted composition, not by isolated slot tests.

## Verification

- ConversationDock, adapter, World history, Agent chrome, AppChrome and surface-interaction tests: 123 tests pass after new tests use the required Peek provider. Exact request/target/recovery guards remain exercised.
- 61 PlanSurfacePage tests pass and cover the owning integration and preserve existing exact IDs, digests, receipts and no-dispatch assertions. Four inherited assertions were migrated to current merged-main wording/read counts; the same failures were independently reproduced from an exact archived base before migration.
- Production `npm run build` passes. Existing bundle-size warning remains (main JavaScript chunk about 2.19 MB).
- `git diff --check` passes.

## Limits

This adopts bottom conversation layout, not the complete successful prototype. Cards remain the existing production cards. Discuss/Propose intent, Graph opt-in, full committed-Plan context and backend request limits are unchanged. Existing recovery warnings remain visible; the unpublished terminal recovery repair was not copied, inherited or recreated. No source entitlement, native chronology or statblock linkage is established by this UI fixture.

## Independent geometry correction

PRIME held the first head's open allocation: the conversation dominated the reader. The correction starts open chat at 220px (resizing remains deliberate); actual default desktop reader is272.67px and narrow reader263.83px. The composer is visible inside both viewports with one launcher and no horizontal overflow. `geometry.json` captures full measured rectangles. Closed management controls are under More, normal transcript heading/caught-up copy is reduced, and turn metadata shares one compact row. Settings/context were opened and closed with a retained draft and enabled Send; no request was submitted. A pointer drag expanded chat to310px, shown separately in `deliberately-expanded.png`; this is a user-selected allocation, not the default.

After the correction, the affected adapter and owning Page suites pass64tests. Unchanged boundary suites remain as previously verified. The actual branch parent/mergebase is merged de22fdefd5b3d8265f85c6b1109f5edd67db660f (includes #996); the earlier25914 label was incorrect and is corrected here and in the handoff. No unpublished recovery repair was inherited.
