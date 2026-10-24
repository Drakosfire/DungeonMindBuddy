# Nested proposal keyboard navigation

ACTIVE serial PRIME correction on codex/surface-proposal-keyboard, base
7ed38faf164bc016756ad6046c91412caf63fde5, same buddy-context-loop checkout.
Direct review is merged after exact Bugbot and protected API/UI delivery. Ordinary
rehearsal proved collapse/reveal but exposed native Ctrl+End escaping the nested
suggestion editor into the author page. Subsequent typing affected only the
synthetic rehearsal source; ordinary Undo/Save restored its exact original bytes
at revision5. No user source was touched. A fresh retained review on revision5
awaits resumed verification; do not regenerate it merely for deployment.

## One correction and exclusive writes
Own document-boundary keyboard navigation inside the shared rendered suggestion,
including extended selections. Prevent it from changing the outer page selection,
focus, bytes or Undo history. Keep ordinary direct typing, rich-text commands,
Tab access to review controls, original snapshot and placement gates intact.
- This handoff; HANDOFF-SURFACE-direct-proposal.md; Docs/Roadmaps/ROADMAP-demo.md.
- apps/live-control-ui/src/surface/SurfacePageProposal.tsx.
- apps/live-control-ui/src/buildSurface/BuildPageProposal.test.tsx.
No API/schema/provider change. No other active lane owns these files. PRIME owns
UI5202; API7ed38faf stays running. User tabs/drafts protected. One serial PR.

## Gates
Actual nested-editor tests assert Ctrl/Meta document navigation and Shift selection
stay inside the suggestion, source JSON remains unchanged, typing/Undo still
belong to review. Build/typecheck; exact cumulative independent Bugbot; PRIME
merge and protected UI-only delivery. Resume the existing fresh synthetic review:
click → document-end key → verify focused editing host → type directly → move by
native drag and accessible caret → save/reload → Keep/Save/reload. Discard remains
verified predecessor behavior; current direct-editing acceptance stays open until
ordinary focus and movement pass. Full goal remains active.
