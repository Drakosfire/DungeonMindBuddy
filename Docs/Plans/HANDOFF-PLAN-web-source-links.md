# PLAN: preserve web source links through the shared Markdown editor

Status: ACTIVE. PRIME designs/implements under the operator's Build→Plan→Play
continuity goal. ARCHITECTURE independently reviews the exact cumulative head.
Base: origin/main@63b6297cd253ac4c8bc017caaf3ca9616afdd2bc.
Branch: codex/markdown-web-source-links, existing buddy-context-loop/dependencies.
Topology: serial Markdown slice; independent of DOGFOOD's Session29 operational
acceptance. Open link PRs764/869 do not own the shared Markdown parser/schema.

Live evidence: on5202 a new disposable Plan paste with headings, exact Mirathorn
source quotations and an inline HTTP Build-source link remains literal text.
Existing parser independently reports that ordinary links are unmounted. Do not
remove that guard without mounting the corresponding mark and proving fidelity.

Outcome: inline absolute HTTP/HTTPS source links retain href and label through
actual mounted editor, semantic paste/import/export, normal Save and reopen.
They are navigation only: no source admission, revision pin, citation authority,
Graph identity or automatic Build→Plan conversion is implied. Keep typed Buddy
references unchanged. No autolink creation or provider request. Unsupported URL
schemes, titles, unresolved reference links and non-text link label constructs
remain diagnosed/protected, not silently flattened. No unsafe HTML href, mark
or URL attribute may bypass the same admission/serialization boundary.

Exclusive expected write lease:
- this handoff
- Docs/Plans/HANDOFF-MEDIA-studio-workspace.md (settle merged lease)
- Docs/Plans/HANDOFF-BUILD-protected-draft-recovery.md (settle merged lease)
- apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx
- apps/live-control-ui/src/tiptap/extensions/WebSourceLink.ts (new)
- apps/live-control-ui/src/tiptap/extensions/WebSourceLink.test.ts (new mounted boundary tests)
- apps/live-control-ui/src/tiptap/markdown/webSourceHref.ts (new shared URL admission)
- apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts
- apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts
- apps/live-control-ui/src/tiptap/markdown/markdownIngressCorpus.test.ts (move newly supported web links into preserved-clean corpus after independent review found old blocked expectations)
- apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts
- apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts
- apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.test.ts
- apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.ts (recognize a supported link-only paragraph as semantic paste)
- apps/live-control-ui/src/tiptap/extensions/SemanticMarkdownPaste.test.ts

Verify actual mounted default schema, hyperlink href/label roundtrip in paragraphs,
headings/tables/callouts, formatted labels, hostile schemes/HTML, unsupported title
and non-text labels fail closed; real paste admission; existing typed reference
and source seal/Save fences. Focused owning suites/typecheck/build/cumulative diff,
independent review, PR and coordinated UI5202 delivery. Then continue normal UI
Plan Save→Play→reload acceptance with authored quotations; existing Edge/Mirathorn
sources and old Plans/Runs remain untouched. Existing checkout cache/private
state only; no /tmp, checkout/env/package or extra preview creation.
