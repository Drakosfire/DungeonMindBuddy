# AUTHOR — explicit source link activation

Status: COMPLETE — PR1414 merged36697f5765d7d58d3901b91674681d2831324fcc, independent PASS and actual source navigation verified; delivered5202; lease ended.
Owner PRIME implementation/delivery; ARCHITECTURE independent review.
Base42055e92fa12fa3ed44df15bb5674d1826158812; branchcodex/activate-source-links; existing buddy-context-loop checkout.
Topology parallel-independent from DOGFOOD Plan autosave. Exclusive lease this handoff, tiptap/extensions/WebSourceLink.ts and .test.ts under apps/live-control-ui/src. Also settle Docs/Plans/HANDOFF-CHROME-compact-navbar-spacing.md after its merge; no product lease remains there. No shared Plan page edits.

## Invariant

Explicit admitted web-source links in the shared editor must open with ordinary unmodified primary click or Enter on a focused link. Open exact safe href in a new tab with noopener,noreferrer; preserve document, selection and dirty generation. Editing non-link content and keyboard Enter in prose remain unchanged. Modified clicks, context menu and drag remain native. Revalidate URL at activation time; unsafe mutated href cannot open. Only links rendered by this mark are intercepted; typed graph/reference links retain their own authority. No parser/serializer expansion, autolink, network fetch or node identity inference.

## Verification

Mount actual default Editor extensions, activate nested formatted link and keyboard-focused anchor; prove exactly one safe open and identical JSON/Markdown/no update. Exercise rejected mutable unsafe hrefs, unrelated anchors, modifiers, repeated mount/unmount, editable/read-only states. Run existing fidelity cases and shared editor regression; cumulative diff inspection; independent exact-head review; one PR then PRIME merge/reversible UI delivery. No live Plan content changes, graph/provider writes or new checkout/environment.

## Evidence

30 actual-editor link/shared editor tests pass, UI TypeScript and Vite build pass (existing chunk-size warning). Initial test fixture assumed mark nesting and jsdom scrolling geometry; corrected anchor target and disabled only test scroll-to-selection, no production workaround. Existing formatted link fidelity cases retained. Browser click on the Plan's Dustwalker source link in isolated5210 opened exact saved Build document2cd1f643-a070-4cec-bbb0-24c803e30b98 on5202 in a new tab; original editor HTML remained byte-identical. Target title verified; temporary tab closed. Keyboard activation verified in mounted editor tests, not separately browser-tested. No document write/provider call. Cumulative diff/check reviewed before commit; independent review pending.
