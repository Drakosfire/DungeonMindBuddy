/**
 * Markdown ingress corpus — the permanent record of what the editor admits.
 *
 * Handoff: Docs/Plans/HANDOFF-BUILD-unify-markdown-structural-analysis.md
 *
 * Two corpora:
 *
 * 1. ADVERSARIAL_CASES — source the bounded editor grammar cannot faithfully
 *    round-trip. Every case here MUST end up behind a blocking (warning)
 *    diagnostic so the source seals instead of flattening into a saveable
 *    lossy projection. `blockedOnMain` is the post-rescue contract: every
 *    flag is `true`. The `note` field records which cases were holes in the
 *    pre-rescue handwritten line/regex grammar (PR #529 review cycles) that
 *    the AST admission boundary closed structurally.
 *
 * 2. PRESERVED_CLEAN_CASES — source that imports cleanly today and MUST stay
 *    clean after the rescue. The rescue changes how structure is recognized,
 *    not which structures are supported. Each case also asserts semantic
 *    model stability across import → serialize → reimport.
 */
import { normalizeMdast } from "../../test/normalizeMdast";
import { tiptapJsonToSemanticMarkdown } from "./calloutMarkdown";
import { hasBlockingMarkdownImportDiagnostics, markdownToTiptapDoc } from "./markdownToTiptap";
import { parseMarkdownAst } from "./parseMarkdownAst";

type AdversarialCase = {
  name: string;
  markdown: string;
  blockedOnMain: boolean;
  /** Hole class / provenance note (PR #529 review cycle or rescue decision). */
  note?: string;
};

const ADVERSARIAL_CASES: AdversarialCase[] = [
  // --- Code / indentation -------------------------------------------------
  { name: "indented code (4 spaces)", markdown: "    const gate = 'held'", blockedOnMain: true },
  { name: "indented code (tab)", markdown: "\tconst gate = 'held'", blockedOnMain: true },
  { name: "indented callout at root", markdown: "    > [!GM-NOTE]", blockedOnMain: true },
  { name: "indented list at root (2 spaces)", markdown: "  - item", blockedOnMain: true },
  { name: "indented ATX heading at root", markdown: "  ## Heading", blockedOnMain: true },
  { name: "indented thematic break at root", markdown: "  ---", blockedOnMain: true },
  { name: "indented paragraph continuation", markdown: "foo\n  bar", blockedOnMain: true },
  { name: "fenced code block", markdown: "```json\n{\"hp\": 95}\n```", blockedOnMain: true },

  // --- Containers ---------------------------------------------------------
  { name: "plain blockquote at root", markdown: "> just a quote", blockedOnMain: true },
  { name: "nested plain blockquote at root", markdown: ">> nested quote", blockedOnMain: true },
  { name: "blockquote nested in list item", markdown: "- Parent\n  > plain blockquote", blockedOnMain: true },
  { name: "heading nested in list item", markdown: "- Parent\n  ## Nested heading", blockedOnMain: true },
  { name: "nested bullet list", markdown: "- Parent\n  - Child", blockedOnMain: true },
  {
    name: "nested callout via doubled quote marker",
    markdown: "> [!GM-NOTE]\n>> [!WARNING]\n>> nested",
    blockedOnMain: true,
    note: "was a hole: inner marker flattened into callout prose; AST blockquote nesting closes it",
  },
  {
    name: "table indented 3 spaces",
    markdown: "   | a | b |\n   | --- | --- |\n   | 1 | 2 |",
    blockedOnMain: true,
    note: "was a hole: the table branch ran before the indent guard; AST column admission closes it",
  },

  // --- Lists --------------------------------------------------------------
  { name: "star bullet marker", markdown: "* item", blockedOnMain: true },
  { name: "plus bullet marker", markdown: "+ item", blockedOnMain: true },
  { name: "task-list item", markdown: "- [ ] Prepare encounter", blockedOnMain: true },

  // --- Links / images / references ----------------------------------------
  { name: "ordinary inline link", markdown: "[Rules](https://example.com/rules)", blockedOnMain: true },
  { name: "ordinary link inside heading", markdown: "# See [Rules](https://example.com)", blockedOnMain: true },
  { name: "inline image", markdown: "![Map](map.png)", blockedOnMain: true },
  {
    name: "reference-style image with definition",
    markdown: "![alt][img]\n\n[img]: pic.png",
    blockedOnMain: true,
  },
  {
    name: "reference-style link with definition",
    markdown: "[Rules][rules]\n\n[rules]: https://example.com/rules",
    blockedOnMain: true,
  },
  {
    name: "shortcut reference with definition",
    markdown: "[rules]\n\n[rules]: https://example.com/rules",
    blockedOnMain: true,
  },
  {
    name: "collapsed reference with definition",
    markdown: "[rules][]\n\n[rules]: https://example.com/rules",
    blockedOnMain: true,
  },
  {
    name: "definition with title",
    markdown: "[rules]: https://example.com/rules \"Title\"",
    blockedOnMain: true,
  },
  {
    name: "zero-space reference definition",
    markdown: "[rules]:https://example.com/rules",
    blockedOnMain: true,
    note: "was a hole (cycle 6): the handwritten recognizer required whitespace after the colon; the parser owns definitions now",
  },
  {
    name: "split-destination reference definition",
    markdown: "[rules]:\nhttps://example.com/rules",
    blockedOnMain: true,
    note: "was a hole (cycle 6): destination on the next line is legal CommonMark; the parser owns definitions now",
  },
  {
    name: "split-destination reference definition (indented continuation)",
    markdown: "[foo]:\n  /url",
    blockedOnMain: true,
    note: "blocked on main only by accident of the blunt indent guard; AST rejects the definition node itself",
  },
  {
    name: "escaped closing bracket in reference label",
    markdown: String.raw`[foo\]]: /url`,
    blockedOnMain: true,
    note: "was a hole (cycle 7): label ends at the first UNescaped ] per CommonMark; no DungeonBuddy regex owns this",
  },
  {
    name: "reference definition inside callout",
    markdown: "> [!GM-NOTE]\n> [rules]: https://example.com/rules",
    blockedOnMain: true,
    note: "was a hole (cycle 5): the callout continuation path only ran inline checks; callout bodies are parsed now",
  },
  {
    name: "zero-space reference definition inside callout",
    markdown: "> [!GM-NOTE]\n> [rules]:https://example.com/rules",
    blockedOnMain: true,
    note: "was a hole (cycles 5+6 combined)",
  },
  {
    name: "autolink at line start",
    markdown: "<https://example.com>",
    blockedOnMain: true,
    note: "blocked on main via the raw-HTML guard; AST classifies it as the link it actually is",
  },
  {
    name: "autolink mid-paragraph",
    markdown: "See <https://example.com> for detail",
    blockedOnMain: true,
    note: "was a hole: mid-paragraph autolinks escaped every inline regex; the parser classifies them as links",
  },
  {
    name: "malformed typed reference",
    markdown: "[label](#dmb-ref:BADTYPE:x)",
    blockedOnMain: true,
    note: "tightened: a #dmb- scheme link that fails validation seals instead of silently flattening to text",
  },
  {
    name: "typed reference with link title",
    markdown: "[a](#dmb-ref:npc:lysandro-ironveil \"title\")",
    blockedOnMain: true,
    note: "tightened: runbookReference has no title attribute; importing would drop it",
  },
  {
    name: "graph-node reference with link title",
    markdown: "[a](dmb-node:pc_caelynn \"title\")",
    blockedOnMain: true,
    note: "tightened: graphNodeReference has no title attribute; importing would drop it",
  },
  {
    name: "graph-node reference with empty node id",
    markdown: "[x](dmb-node:)",
    blockedOnMain: true,
    note: "was a hole (PR #535 cycle 1): empty nodeId serialized as bare label text, so the link disappeared durably on save",
  },
  {
    name: "graph-node reference with formatted label",
    markdown: "[**Caelynn**](dmb-node:pc_caelynn)",
    blockedOnMain: true,
    note: "was a hole (PR #535 cycle 1): the opaque reference node cannot preserve label marks; serialization dropped the emphasis",
  },
  {
    name: "typed reference with formatted label",
    markdown: "[**Lysandro**](#dmb-ref:npc:lysandro-ironveil)",
    blockedOnMain: true,
    note: "was a hole (PR #535 cycle 1): same label-flattening class on typed refs",
  },
  {
    name: "action reference with code label",
    markdown: "[`North Gate`](#dmb-action:combat:north-gate-combat)",
    blockedOnMain: true,
    note: "was a hole (PR #535 cycle 1): code labels flatten to plain text on the opaque node",
  },

  // --- Headings / breaks / HTML -------------------------------------------
  {
    name: "non-canonical thematic break (stars)",
    markdown: "***",
    blockedOnMain: true,
    note: "tightened (PR #535 cycle 1): the parser establishes a thematic break; admission must not reinterpret non---- spellings as literal prose without sealing",
  },
  {
    name: "non-canonical thematic break (underscores)",
    markdown: "___",
    blockedOnMain: true,
    note: "tightened (PR #535 cycle 1): same parser-established class as stars",
  },
  {
    name: "non-canonical thematic break (spaced hyphens)",
    markdown: "- - -",
    blockedOnMain: true,
    note: "tightened (PR #535 cycle 1): parses as a thematicBreak; only the canonical --- spelling is admitted",
  },
  { name: "setext heading (level 1)", markdown: "Heading\n===", blockedOnMain: true },
  { name: "setext heading (level 2)", markdown: "Heading\n-------", blockedOnMain: true },
  { name: "hard break (trailing spaces)", markdown: "Line one  \nLine two", blockedOnMain: true },
  { name: "hard break (backslash)", markdown: "Line one\\\nLine two", blockedOnMain: true },
  { name: "raw HTML block", markdown: "<div>unsafe</div>", blockedOnMain: true },
];

type PreservedCleanCase = {
  name: string;
  markdown: string;
  note?: string;
};

const PRESERVED_CLEAN_CASES: PreservedCleanCase[] = [
  { name: "ordinary prose", markdown: "A normal paragraph." },
  { name: "snake_case identifier", markdown: "Use snake_case_value here." },
  { name: "double-underscore identifier", markdown: "Use foo__bar__baz here." },
  { name: "escaped asterisk literal", markdown: String.raw`\*not italic\*` },
  { name: "escaped underscore literal", markdown: String.raw`\_literal\_` },
  { name: "escaped tilde literal", markdown: String.raw`\~\~literal\~\~` },
  { name: "escaped bracket literal", markdown: String.raw`\[not a link\]` },
  { name: "single-tilde text stays text", markdown: "~single tilde~", note: "GFM singleTilde must stay disabled" },
  { name: "bare URL stays plain text", markdown: "See https://example.com/rules for detail", note: "GFM autolink-literal must stay disabled" },
  { name: "bare www stays plain text", markdown: "See www.example.com for detail" },
  { name: "bare email stays plain text", markdown: "Mail ops@example.com today" },
  { name: "H1", markdown: "# One" },
  { name: "H2", markdown: "## Two" },
  { name: "H3", markdown: "### Three" },
  { name: "H4", markdown: "#### Four" },
  { name: "H5", markdown: "##### Five" },
  { name: "H6", markdown: "###### Six" },
  { name: "seven hashes stay prose", markdown: "####### seven" },
  { name: "bold", markdown: "**bold**" },
  { name: "underscore bold", markdown: "__bold__" },
  { name: "italic", markdown: "*italic*" },
  { name: "underscore italic", markdown: "_italic_" },
  { name: "strike", markdown: "~~strike~~" },
  { name: "inline code", markdown: "`code`" },
  { name: "code span with awkward backticks", markdown: "`` `awkward` ``" },
  { name: "typed runbook reference", markdown: "Talk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)." },
  { name: "typed action reference", markdown: "Launch [North Gate Combat](#dmb-action:combat:north-gate-combat)." },
  { name: "graph-node reference", markdown: "Inspect [Caelynn](dmb-node:pc_caelynn)." },
  { name: "thematic break", markdown: "# Before\n\n---\n\n## After" },
  { name: "frontmatter lookalike without YAML keys is a thematic break", markdown: "---\n\n# Body" },
  { name: "bullet list", markdown: "- First\n- Second" },
  { name: "ordered list", markdown: "1. one\n2. two" },
  { name: "ordered list with paren markers", markdown: "1) one\n2) two", note: "serializer canonicalizes ) to ." },
  { name: "ordered list with non-1 start", markdown: "3. three\n4. four" },
  {
    name: "loose list",
    markdown: "- foo\n\n- bar",
    note: "main models this as two sibling lists; the AST models one. Either way it stays clean and the item model round-trips.",
  },
  { name: "read-aloud callout", markdown: "> [!READ-ALOUD]\n> The gate groans." },
  { name: "gm-note callout", markdown: "> [!GM-NOTE]\n> Keep this about triage." },
  { name: "rules callout", markdown: "> [!RULES]\n> Difficult terrain." },
  { name: "warning callout", markdown: "> [!WARNING]\n> Do not split the party." },
  { name: "callout with custom label", markdown: "> [!WARNING] Custom label\n> body" },
  { name: "stacked sibling callouts", markdown: "> [!GM-NOTE]\n> First note.\n> [!WARNING]\n> Second note." },
  { name: "callout containing safe table", markdown: "> [!GM-NOTE]\n> A | B\n> --- | ---\n> 1 | 2" },
  { name: "safe table with escaped pipe", markdown: "Threat | Note\n--- | ---\nLatchling | A \\| B" },
  { name: "safe table with pipe inside code span", markdown: "Threat | Note\n--- | ---\nMeat Mind | `range \\| aura`" },
  { name: "empty document", markdown: "" },
  { name: "CRLF body", markdown: "# A\r\n\r\npara\r\n" },
];

describe("Markdown ingress corpus", () => {
  describe("adversarial structures fail closed", () => {
    for (const testCase of ADVERSARIAL_CASES) {
      it(`${testCase.name}${testCase.note ? ` — ${testCase.note}` : ""}`, () => {
        expect(
          hasBlockingMarkdownImportDiagnostics(testCase.markdown),
          `expected blockedOnMain=${testCase.blockedOnMain}`,
        ).toBe(testCase.blockedOnMain);
      });
    }
  });

  describe("supported structures stay clean and model-stable", () => {
    for (const testCase of PRESERVED_CLEAN_CASES) {
      it(testCase.name, () => {
        const imported = markdownToTiptapDoc(testCase.markdown);
        expect(imported.diagnostics).toEqual([]);
        const exported = tiptapJsonToSemanticMarkdown(imported.doc);
        const reimported = markdownToTiptapDoc(exported);
        expect(reimported.diagnostics).toEqual([]);
        expect(reimported.doc).toEqual(imported.doc);
      });
    }
  });

  describe("frontmatter diagnostics", () => {
    it("reports original-document line numbers for unsafe body nodes (handoff §7)", () => {
      // CRLF frontmatter occupies original lines 1-3, `# Body` is line 4, and
      // the fenced code block opens at original line 5. Diagnostics must point
      // at the original document, not the stripped body.
      const markdown = "---\r\ntitle: X\r\n---\r\n# Body\r\n```json\r\n{}\r\n```\r\n";
      const imported = markdownToTiptapDoc(markdown);
      expect(imported.diagnostics.map((diagnostic) => diagnostic.line)).toEqual([5]);
    });
  });

  describe("AST semantic equivalence (handoff §18/§19)", () => {
    it("keeps parse(exported) equivalent to parse(re-exported) for every preserved-clean case", () => {
      for (const testCase of PRESERVED_CLEAN_CASES) {
        const exported = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(testCase.markdown).doc);
        const reexported = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(exported).doc);
        expect(
          normalizeMdast(parseMarkdownAst(reexported)),
          `AST instability after re-export: ${testCase.name}`,
        ).toEqual(normalizeMdast(parseMarkdownAst(exported)));
      }
    });

    it("keeps parse(source) equivalent to parse(exported) for canonical-spelling fixtures", () => {
      // Fixtures whose source spelling is already serializer-canonical: the
      // admitted semantic model must survive source → AST → TipTap → Markdown
      // → AST unchanged (frontmatter fidelity is covered separately).
      const canonicalFixtures = [
        "# Heading",
        "- a\n- b",
        "1. one\n2. two",
        "**bold** and *italic* and ~~strike~~ and `code`",
        "# Before\n\n---\n\n## After",
        "> [!GM-NOTE]\n> Body text.",
        "> [!WARNING] Custom label\n> body",
        "A | B\n--- | ---\n1 | 2",
        "Talk to [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil).",
        "Inspect [Caelynn](dmb-node:pc_caelynn).",
      ];
      for (const markdown of canonicalFixtures) {
        const exported = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(markdown).doc);
        expect(
          normalizeMdast(parseMarkdownAst(exported)),
          `AST drift for canonical fixture: ${JSON.stringify(markdown)}`,
        ).toEqual(normalizeMdast(parseMarkdownAst(markdown)));
      }
    });
  });
});
