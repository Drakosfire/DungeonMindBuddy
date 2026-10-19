# Titled collapsible callouts

Status: ACTIVE, 2026-10-19. Operator dogfood requests collapsible Rules and Read
Aloud blocks with explanatory titles. PRIME owns a serial branch
codex/collapsible-callout-blocks from f73453692 in buddy-context-loop; no overlapping
active callout PR.

Use existing callout kinds and existing optional Markdown labels:
`> [!RULES] Traveling`, `> [!READ-ALOUD] North of Mireward Reach`.
Headers retain both kind and optional authored title. Support Rules, Read Aloud,
GM note and Warning through the shared node/reader. No new document format.
Collapse is local presentation state, not an authored attribute or autosave.
Existing untitled blocks remain readable and initially expanded. Do not infer
new titles or change the real campaign Plan merely to demonstrate the feature.

Invariant: folding in an editor or reader does not change JSON/Markdown, drafts,
selection, undo history, saves, Run progress or note target. Editable content stays
in the same node/view. Native summary is keyboard accessible. Existing/legacy
callout HTML and optional labels round-trip safely; closed state is never parsed
as a content change. No backend, Graph, schema or stored-history mutation.

Exclusive paths: this handoff; tiptap/extensions/CalloutNode.ts and new CSS/tests;
tiptap/markdown/calloutMarkdown.test.ts for existing label round-trip proof;
markdownReader callout rendering tests; planSurface/components/PlanMarkdownSource.tsx
help examples only. No dependency/lockfile or other block redesign.

Verify editor mutations/undo/selection and Markdown bytes while folding; keyboard
reader folding and text-safe titles; existing callout/import/reader tests;
production build; independent Architecture exact-head review; disposable titled
blocks and existing untitled Plan/Play blocks on5202 desktop/narrow. Keep real
Plan/session/notes/reflections/media responses exact. UI-only atomic lease,
prior index877c2da063ed4229847e2f7bfc278579bdb55993f7d8c07cdae4bc6899ca3e77;
retain rollback assets/index; no API restart. One reviewed PR then settlement.
