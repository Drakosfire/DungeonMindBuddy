# Plan bottom conversation — integration evidence

Base: merged `25914c4d9e944f3f951053a7b1ac5656bc0c5ceb`. Branch: `codex/dogfood-plan-bottom-dock`. Review the cumulative base-to-head diff; this evidence is source/fixture verification, not operator-runtime acceptance.

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
