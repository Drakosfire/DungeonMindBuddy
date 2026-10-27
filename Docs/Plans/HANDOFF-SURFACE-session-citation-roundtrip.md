# SURFACE — session citation editor round trip

Status: ACTIVE after independent invariant critique at6a23052b0, clarified ordinary-link title scope with independent approval. PRIME owns design and the serial successor branch codex/session-citation-editor-roundtrip, base57d611ad65b785578feb566c9a7b254c921cfe2a in existing buddy-context-loop checkout. Standing operator authoring/dogfood authority applies. One independently reviewed implementation PR; no new worktree/environment. Runtime5202 remains the delivered1835 source; the Sheep proposal is staged and unsaved. Hosted1828 and held1764 stay separate.

## Observed boundary and invariant

PR1835 host session_summary projection emits numbered root-relative /play?world=…&run=…&evidence_revision=…#source-… links with a source-name title. The shared Markdown admission currently excludes both that relative route and every ordinary link title, so the staged proposal displays raw Markdown. Unit checks of fragment strings and provider binding did not exercise the actual default editor. Fix the shared editor/navigation representation; do not hand-repair private citations or rewrite retained text.

A typed host citation must import to the mounted link mark, retain the complete href and optional plain-text title through direct editing, semantic Markdown export, Save/reload, and activate once without mutating the editor. A URL is a navigation request, never evidence authority. Existing immutable viewer packet/source/entry checks remain the only target validation. No new provenance store, model URL authority or executable Markdown node.

Admit root-relative session-evidence navigation only with exact /play path, World/Run/positive review selectors (nonempty trimmed World, UUID Run and canonical positive safe-integer review; no invented World slug restriction), no duplicates/unknown selectors, and an optional exact host source-fragment shape. Ordinary absolute safe web links retain existing href admission and activation rules; optional inert plain-text titles belong to the shared ordinary link mark, not a route-specific metadata exception. Add optional title to the existing link mark; Markdown import, HTML import, render, serialization and safety validation must agree. Plain text only, preserve quote/backslash escaping, reject control characters/unknown mark attributes. Keep unsupported schemes, credentials, protocol-relative links, arbitrary local paths, non-text labels and typed DungeonBuddy-reference title restrictions intact. No arbitrary title length cap or historical rewrite/fallback.

## Exclusive writes and owner

UI tiptap/markdown/webSourceHref.ts, markdownAdmission.ts, calloutMarkdown.ts, semanticMarkdownSafety.ts; extensions/WebSourceLink.ts and colocated tests; a focused pure session-evidence navigation syntax helper under playSurface/review; shared/sessionEvidenceCitation.ts for the same pure syntax check at host-target construction, shared/sessionEvidenceCitation.test.tsx or a mounted SurfacePageProposal integration test to join actual host summary projection to the default editor. Amend allowlist before another owner join. This handoff and predecessor HANDOFF-PLAN-cited-session-briefing.md are mutable authority to settle.

## Verification and delivery

1. Before implementation critique the invariant/failure cases. Reproduce actual host-generated titled session link failure through the default editor.
2. Mounted proposal/editor import → direct edit → semantic export → reimport preserves exact source href/title and clickable numbered anchors, with unchanged outside nodes. Test both saved entries and multiple paragraphs.
3. Negative URI/title/attribute and non-text-label tests remain; existing web/document links, source activation and Markdown safety tests pass. TypeScript/build and exact cumulative Bugbot/hosted gates before protected delivery.
4. Resume the retained ordinary Sheep page proposal without regenerating or losing it, edit, Save, reload, open each exact original, and prove outside Plan identities/content unchanged. Preserve all original failures. Do not count the earlier discussion misroute as success; it is a separate bounded routing investigation after this correction. No new corpus publication, Run rebasing, model policy, graph writes or broad performance work.
