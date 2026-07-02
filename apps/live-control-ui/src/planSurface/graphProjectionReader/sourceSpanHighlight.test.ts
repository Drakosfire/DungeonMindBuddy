import type { RecapProjectionSourceSpan } from "../../api/types";
import { attachSourceSpanDataAttributes, normalizeEvidenceText } from "./sourceSpanHighlight";

function renderRoot(markup: string): HTMLElement {
  const root = document.createElement("div");
  root.innerHTML = `<div class="ProseMirror">${markup}</div>`;
  document.body.append(root);
  return root;
}

function span(overrides: Partial<RecapProjectionSourceSpan>): RecapProjectionSourceSpan {
  return {
    span_id: "span-1",
    kind: "paragraph",
    ordinal: null,
    text_excerpt: null,
    line_start: null,
    line_end: null,
    ...overrides,
  };
}

describe("sourceSpanHighlight", () => {
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("collapses whitespace and lowercases evidence text", () => {
    expect(normalizeEvidenceText("  The\nQuick\tFox  ")).toBe("the quick fox");
  });

  it("claims the right paragraph with an exact normalized text match", () => {
    const root = renderRoot("<p>First paragraph.</p><p>The exact evidence.</p>");

    attachSourceSpanDataAttributes(root, [span({ span_id: "exact", text_excerpt: "the EXACT evidence." })], null);

    const paragraphs = root.querySelectorAll<HTMLElement>("p");
    expect(paragraphs[0].dataset.sourceSpanId).toBeUndefined();
    expect(paragraphs[1].dataset.sourceSpanId).toBe("exact");
  });

  it("claims the right paragraph with a unique included excerpt match", () => {
    const root = renderRoot("<p>Nothing useful.</p><p>The recap contains a unique clue in a longer paragraph.</p>");

    attachSourceSpanDataAttributes(root, [span({ span_id: "excerpt", text_excerpt: "unique clue" })], null);

    expect(root.querySelectorAll<HTMLElement>("p")[1].dataset.sourceSpanId).toBe("excerpt");
  });

  it("does not claim ambiguous text matches and can fall back to ordinal", () => {
    const root = renderRoot("<p>Repeated clue appears here.</p><p>Repeated clue appears there.</p>");

    attachSourceSpanDataAttributes(root, [span({ span_id: "ambiguous", text_excerpt: "Repeated clue", ordinal: 2 })], null);

    const paragraphs = root.querySelectorAll<HTMLElement>("p");
    expect(paragraphs[0].dataset.sourceSpanId).toBeUndefined();
    expect(paragraphs[1].dataset.sourceSpanId).toBe("ambiguous");
  });

  it("adds the highlight class to the selected source span and returns it", () => {
    const root = renderRoot("<p>Evidence paragraph.</p>");

    const highlighted = attachSourceSpanDataAttributes(
      root,
      [span({ span_id: "selected", text_excerpt: "Evidence paragraph." })],
      "selected",
    );

    expect(highlighted).toBe(root.querySelector("p"));
    expect(highlighted).toHaveClass("recap-source-span-highlight");
  });

  it("clears previous source span attributes and highlights before reapplying", () => {
    const root = renderRoot(
      '<p data-source-span-id="stale" class="recap-source-span-highlight">Old paragraph.</p><p>New paragraph.</p>',
    );

    attachSourceSpanDataAttributes(root, [span({ span_id: "new", text_excerpt: "New paragraph." })], null);

    const paragraphs = root.querySelectorAll<HTMLElement>("p");
    expect(paragraphs[0].dataset.sourceSpanId).toBeUndefined();
    expect(paragraphs[0]).not.toHaveClass("recap-source-span-highlight");
    expect(paragraphs[1].dataset.sourceSpanId).toBe("new");
  });

  it("uses one-based ordinal fallback for an unclaimed paragraph", () => {
    const root = renderRoot("<p>First paragraph.</p><p>Second paragraph.</p><p>Third paragraph.</p>");

    attachSourceSpanDataAttributes(root, [span({ span_id: "ordinal", ordinal: 3 })], null);

    expect(root.querySelectorAll<HTMLElement>("p")[2].dataset.sourceSpanId).toBe("ordinal");
  });
});
