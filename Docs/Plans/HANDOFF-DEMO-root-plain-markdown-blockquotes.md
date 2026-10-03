# DEMO handoff — root plain Markdown blockquotes

- **Status:** MERGED — Buddy PR #888; parser lease closed on 2026-10-03
- **Owner:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`
- **Authority:** PRIME activation on 2026-10-03; this handoff records the exact implementation lease
- **Repository/base:** `Drakosfire/DungeonMindBuddy`, `origin/main@1ded2275349f4e9ada1b67a6ab4f6061f9c2465e`
- **Branch:** `codex/demo-root-markdown-blockquotes`
- **Topology:** One independent grammar PR; no unmerged behavioral dependency on #886 or another open PR

## Merge settlement

PR #888 merged at `ea331ffee4e7f6b8603dcc8d2d2b18d4827f88cd` from reviewed code
head `0aa89e758bbe62014c23c20d112f7bad430aa118`. The parser lease is closed.
PRIME independently reported all 235 focused importer, serializer, safety, and
ingress-corpus tests passing. This closes only root plain-blockquote support;
unsupported Markdown still requires the separate World Plan Save guard in
[`HANDOFF-DEMO-world-plan-save-fidelity-guard.md`](HANDOFF-DEMO-world-plan-save-fidelity-guard.md).

## User-facing outcome

Ordinary root-level Markdown blockquotes in an imported World Plan remain quotes
through editor save and reload. The current importer turns their `>` content into
paragraphs, and the serializer has no quote node case, so ordinary quoted text
loses its quote boundary. The Session 29 Plan contains 22 root plain-quote
diagnostics that currently stop the reviewed Compose path before provider
dispatch.

## Accepted contract

- Admit ordinary blockquotes only at document root, with source opening column 1.
- Preserve only blockquotes whose direct children and inline content are already
  proven by the semantic Markdown grammar. Each admitted direct child is a
  paragraph; paragraph boundaries and supported inline marks/references survive
  import → serialize → re-import.
- Emit canonical quote prefixes (`> ` for content and `>` for blank separator
  lines), preserving paragraphs and supported inline serialization.
- Keep `[!READ-ALOUD]`, other supported callouts, Decision/Consequence blocks,
  custom labels and unknown-marker blocking behavior unchanged, including marker
  precedence.
- Keep nested quotes, list-item quotes, indented quotes, unsupported nested
  callouts, and quotes containing unsupported block/inline grammar blocked with
  diagnostics. Never turn a failed quote projection into a warning-free save.
- Do not claim byte-identical Markdown serialization; canonical normalization is
  allowed. The checked-in source corpus remains unchanged.

## Re-anchor and collision check

PRIME re-fetched and pinned `main` at `1ded2275349f4e9ada1b67a6ab4f6061f9c2465e`.
The managed implementation worktree starts at the same SHA. PRIME checked all
13 open Buddy PRs and found no changed-file overlap with the seven parser/test
paths below. The checked PRs were #887, #886, #869, #865, #844, #826, #798,
#781, #765, #764, #763, #761, and #760. #886 retains the separate exclusive
lease on `PlanSurfacePage.tsx` and its tests; its browser geometry gate remains
open. A RAKE recap lease is outside these paths. No other parser write lease is
known at activation.

## Exclusive expected-path write lease

Only these paths may change in this slice:

1. `apps/live-control-ui/src/tiptap/markdown/markdownAdmission.ts`
2. `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.ts`
3. `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.ts`
4. `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts`
5. `apps/live-control-ui/src/tiptap/markdown/calloutMarkdown.test.ts`
6. `apps/live-control-ui/src/tiptap/markdown/semanticMarkdownSafety.test.ts`
7. `apps/live-control-ui/src/tiptap/markdown/markdownIngressCorpus.test.ts`
8. `Docs/Plans/HANDOFF-DEMO-root-plain-markdown-blockquotes.md` (this handoff)

No `PlanSurfacePage`, its tests, editor host, Agent Compose component, API/state,
Graph, or corpus paths are in this lease. Only the existing admission,
serialization, safety, and grammar-test files listed above are in scope. The
World Plan save-on-warning guard remains a required follow-up after #886 releases
its file lease or PRIME explicitly transfers it.

## Runtime and data boundary

No service, port, database, provider, Graph, browser, or saved Plan state is used
or modified. Verification reads only the checked-in Session 29 source and linked
derivative as fixtures. The source SHA-256 is
`7628ff052ebb87e2e3a074e9a11b3f96753aab50b16c20a93a284a5ec76fc8d5`; the linked
derivative SHA-256 is
`a7674ace660d7d3c4b82847a3486cf15e0df8f4a357333ad3c9185ef8f698dd7`.

## Required verification

- Focused markdown importer, serializer, safety, and ingress-corpus Vitest suites
  pass.
- Both Session 29 files import with no root-quote diagnostics and no semantic
  serialization warnings; serialize/re-import preserves quote boundaries,
  paragraph text/marks, the linked Plan's 72 `dmb-node:` links across 8 IDs, and
  all 90 v2 playable markers in order.
- Existing callout, nested quote, list-item quote, unknown marker and nested
  callout cases remain covered and retain their current behavior.
- `git diff --check` passes. Inspect the full cumulative `origin/main` → head
  diff; commit, push and open one PR titled `DEMO: preserve root Markdown
  blockquotes`. Do not merge; PRIME owns review and merge.

## Verification completed

- Focused importer, serializer, safety and ingress-corpus suites: 235 passed.
- The exact checked-in source and linked Plan fixture import and re-import with
  no diagnostics or semantic-safety warnings. Both preserve quote paragraph
  boundaries and text/marks; the linked Plan preserves all 72 graph-link targets
  and labels across 8 IDs; both preserve all 90 v2 markers in order.
- `git diff --check`: passed.
- App TypeScript check reports only the inherited
  `TS2503: Cannot find namespace 'JSX'` at
  `src/statblocks/publication/ThreatPublicationPanel.tsx:553`, outside this
  lease. No changed implementation file reports a TypeScript error.

## Failure cases to keep closed

1. A root quote containing a nested/list block or an unsupported inline node must
   not be admitted merely because its outer AST node is a blockquote.
2. A quote nested in a list or another container must not become a root quote
   when projected.
3. A callout marker inside a quote must retain existing classification and
   unknown markers must not silently normalize into WARNING.
4. Serialization must not flatten paragraph breaks or accept a TipTap
   `blockquote` shape the importer could not have produced safely.
