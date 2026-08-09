/**
 * Parser characterization — the mdast behaviors DungeonBuddy's admission
 * boundary depends on. If a dependency upgrade changes any of these, the
 * admission policy must be re-reviewed before the build goes green again.
 *
 * Handoff §6: the parser is the recognizer; DungeonBuddy owns admission.
 */
import { parseMarkdownAst } from "./parseMarkdownAst";

type MdastNode = {
  type: string;
  value?: string;
  url?: string;
  title?: string | null;
  identifier?: string;
  lang?: string | null;
  depth?: number;
  ordered?: boolean | null;
  start?: number | null;
  spread?: boolean | null;
  checked?: boolean | null;
  align?: Array<string | null>;
  children?: MdastNode[];
  position?: { start: { line: number; column: number }; end: { line: number; column: number } };
};

function root(markdown: string): MdastNode {
  return parseMarkdownAst(markdown) as unknown as MdastNode;
}

function onlyChild(markdown: string): MdastNode {
  const children = root(markdown).children ?? [];
  expect(children.length).toBe(1);
  return children[0];
}

describe("parseMarkdownAst characterization", () => {
  it("recognizes reference definitions with escaped closing brackets in the label", () => {
    // The PR #529 cycle-7 case. No DungeonBuddy regex may own this construct.
    const node = onlyChild(String.raw`[foo\]]: /url`);
    expect(node.type).toBe("definition");
    expect(node.url).toBe("/url");
  });

  it("recognizes zero-space and split-destination reference definitions", () => {
    expect(onlyChild("[rules]:https://example.com/rules").type).toBe("definition");
    expect(onlyChild("[rules]:\nhttps://example.com/rules").type).toBe("definition");
  });

  it("keeps bare URLs, www prefixes, and emails as plain text (no autolink-literal)", () => {
    for (const markdown of [
      "See https://example.com/rules for detail",
      "See www.example.com for detail",
      "Mail ops@example.com today",
    ]) {
      const paragraph = onlyChild(markdown);
      expect(paragraph.type).toBe("paragraph");
      expect((paragraph.children ?? []).every((child) => child.type === "text")).toBe(true);
    }
  });

  it("parses CommonMark <url> autolinks as link nodes", () => {
    const paragraph = onlyChild("See <https://example.com> for detail");
    const link = (paragraph.children ?? []).find((child) => child.type === "link");
    expect(link?.url).toBe("https://example.com");
  });

  it("parses ~~strike~~ but leaves ~single~ as literal text", () => {
    const single = onlyChild("~foo~");
    expect((single.children ?? []).every((child) => child.type === "text")).toBe(true);
    const double = onlyChild("~~foo~~");
    expect(double.children?.[0]?.type).toBe("delete");
  });

  it("marks task-list items with a checked flag so admission can reject them structurally", () => {
    const list = onlyChild("- [ ] Prepare encounter\n- [x] Done thing");
    expect(list.type).toBe("list");
    expect(list.children?.[0]?.checked).toBe(false);
    expect(list.children?.[1]?.checked).toBe(true);
  });

  it("parses *** and ___ as thematic breaks (admission decides spelling policy)", () => {
    expect(onlyChild("***").type).toBe("thematicBreak");
    expect(onlyChild("___").type).toBe("thematicBreak");
    expect(onlyChild("---").type).toBe("thematicBreak");
  });

  it("preserves actual table row widths so uneven rows stay detectable", () => {
    const wide = onlyChild("A | B\n--- | ---\n1 | 2 | 3");
    expect(wide.type).toBe("table");
    expect(wide.children?.[1]?.children?.length).toBe(3);
    const narrow = onlyChild("A | B | C\n--- | --- | ---\n1 | 2");
    expect(narrow.children?.[1]?.children?.length).toBe(2);
  });

  it("exposes table alignment as metadata instead of delimiter-row regexes", () => {
    const table = onlyChild("Name | Role\n:--- | ---:\nLysandra | Captain");
    expect(table.align).toEqual(["left", "right"]);
  });

  it("resolves escaped pipes inside code spans in table cells", () => {
    const table = onlyChild("Threat | Note\n--- | ---\nMeat Mind | `range \\| aura`");
    const cell = table.children?.[1]?.children?.[1];
    expect(cell?.children?.[0]?.type).toBe("inlineCode");
    expect(cell?.children?.[0]?.value).toBe("range | aura");
  });

  it("models a blank-line-separated list as one spread list", () => {
    const list = onlyChild("- foo\n\n- bar");
    expect(list.type).toBe("list");
    expect(list.spread).toBe(true);
    expect(list.children?.length).toBe(2);
  });

  it("accepts paren ordered-list markers and non-1 starts", () => {
    const paren = onlyChild("1) one\n2) two");
    expect(paren.ordered).toBe(true);
    expect(paren.start).toBe(1);
    const three = onlyChild("3. three\n4. four");
    expect(three.start).toBe(3);
  });

  it("spans setext headings across both source lines", () => {
    const heading = onlyChild("Heading\n-------");
    expect(heading.type).toBe("heading");
    expect(heading.depth).toBe(2);
    expect(heading.position?.start.line).toBe(1);
    expect(heading.position?.end.line).toBe(2);
  });

  it("groups stacked sibling callout markers into one blockquote container", () => {
    const quote = onlyChild("> [!GM-NOTE]\n> First note.\n> [!WARNING]\n> Second note.");
    expect(quote.type).toBe("blockquote");
    expect(quote.position?.start.line).toBe(1);
    expect(quote.position?.end.line).toBe(4);
  });

  it("nests doubled-quote-marker callouts as blockquote inside blockquote", () => {
    const quote = onlyChild("> [!GM-NOTE]\n>> [!WARNING]\n>> nested");
    expect(quote.type).toBe("blockquote");
    expect((quote.children ?? []).map((child) => child.type)).toContain("blockquote");
  });

  it("keeps blockquote tables as parsed table nodes inside the container", () => {
    const quote = onlyChild("> [!GM-NOTE]\n> A | B\n> --- | ---\n> 1 | 2");
    expect((quote.children ?? []).map((child) => child.type)).toContain("table");
  });

  it("distinguishes indented code from fenced code by source form", () => {
    const indented = onlyChild("    const gate = 'held'");
    expect(indented.type).toBe("code");
    expect(indented.lang).toBeNull();
    const fenced = onlyChild("```json\n{\"hp\": 95}\n```");
    expect(fenced.type).toBe("code");
    expect(fenced.lang).toBe("json");
  });

  it("parses images, image references, and definitions as distinct node types", () => {
    const image = onlyChild("![Map](map.png)");
    expect(image.children?.[0]?.type).toBe("image");
    const refDoc = root("![alt][img]\n\n[img]: pic.png");
    expect(refDoc.children?.[0]?.children?.[0]?.type).toBe("imageReference");
    expect(refDoc.children?.[1]?.type).toBe("definition");
  });

  it("parses block and inline HTML as html nodes", () => {
    expect(onlyChild("<div>unsafe</div>").type).toBe("html");
    const paragraph = onlyChild("Text with <span>inline</span> html");
    expect((paragraph.children ?? []).some((child) => child.type === "html")).toBe(true);
  });

  it("parses both hard-break spellings as break nodes", () => {
    for (const markdown of ["Line one  \nLine two", "Line one\\\nLine two"]) {
      const paragraph = onlyChild(markdown);
      expect((paragraph.children ?? []).some((child) => child.type === "break")).toBe(true);
    }
  });

  it("preserves link titles so admission can reject unrepresentable attributes", () => {
    const paragraph = onlyChild("[a](#dmb-ref:npc:x \"title\")");
    const link = paragraph.children?.[0];
    expect(link?.type).toBe("link");
    expect(link?.title).toBe("title");
  });

  it("parses nested lists and blockquotes as list-item children", () => {
    const nested = onlyChild("- Parent\n  - Child");
    expect(nested.children?.[0]?.children?.map((child) => child.type)).toContain("list");
    const quote = onlyChild("- Parent\n  > quote");
    expect(quote.children?.[0]?.children?.map((child) => child.type)).toContain("blockquote");
  });

  it("resolves CommonMark escapes and intraword emphasis in text values", () => {
    const snake = onlyChild("Use snake_case_value and foo__bar__baz here");
    expect(snake.children?.length).toBe(1);
    expect(snake.children?.[0]?.type).toBe("text");
    const escaped = onlyChild(String.raw`Keep \_literal\_ unmarked`);
    expect(escaped.children?.[0]?.value).toBe("Keep _literal_ unmarked");
  });
});
