# MEDIA: one-row Image Studio toolbar

ACTIVE · PRIME · serial small UI-only slice, branch codex/studio-single-row-toolbar
from fetched main1c238dcaa9d549afc3d292c02709fab9b3dc5b57. Reuse buddy-context-loop.
Lease: MediaImageWizard.tsx/.css and this handoff. Existing tests adopted unchanged.
Replace title/status/action rows with one flex header. Preserve existing handlers,
labels, library/edit/place/download controls and cancellation. On narrow screens
only the action strip scrolls; library/collapse/close remain reachable.
No generation, map editor, API/schema, media persistence or model changes.
Map editor stays backlog; toolbar feedback is immediate authorized delivery.
Verify existing media tests, exact localhosted/discovered baseline comparison,
independent review, UI-only protected delivery and browser geometry in ordinary
empty/library/result/collapsed states at desktop and narrow width. Do not generate
paid artwork for a layout check. Preserve current draft/review and API.
