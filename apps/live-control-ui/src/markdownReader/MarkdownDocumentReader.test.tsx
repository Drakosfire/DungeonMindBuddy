import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MarkdownDocumentReader } from "./MarkdownDocumentReader";

const HESTA_FIXTURE = `---
title: Hesta Sample
world: glass-orchard
---

# Hesta at the Gate

She **walked** with *care* past the ~~old~~ new ward.

## Supplies

- rope
- lantern
1. check the hinges
2. listen for wings

| Role | Name |
| --- | --- |
| Gatekeeper | Hesta |
| Scribe | Orin |

See the [Convention notes](https://example.com/con) and mail [ops](mailto:ops@example.com).
Jump to [local heading](#supplies).
Also [rules][rules-ref].

![Hesta portrait](https://example.com/hesta.webp)

![Local art](assets/hesta.webp)

<section class="raw">visible html</section>

<script>alert(1)</script>

[x](javascript:alert(1))

[rules-ref]: https://example.com/rules "Rules"
`;

describe("MarkdownDocumentReader", () => {
  it("renders headings, prose, emphasis, lists, and tables semantically", () => {
    render(<MarkdownDocumentReader markdown={HESTA_FIXTURE} />);

    expect(screen.getByRole("heading", { level: 1, name: "Hesta at the Gate" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Supplies" })).toBeInTheDocument();
    expect(screen.getByText("walked").closest("strong")).not.toBeNull();
    expect(screen.getByText("care").closest("em")).not.toBeNull();
    expect(screen.getByText("old").closest("del")).not.toBeNull();
    expect(screen.getAllByRole("list").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Role" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Hesta" })).toBeInTheDocument();
  });

  it("omits leading YAML frontmatter from the prose view without mutating input authority", () => {
    const { container } = render(<MarkdownDocumentReader markdown={HESTA_FIXTURE} />);
    expect(container.textContent).not.toContain("world: glass-orchard");
    expect(container.textContent).not.toMatch(/^---/);
  });

  it("renders safe links and keeps unsafe schemes non-clickable", () => {
    render(<MarkdownDocumentReader markdown={HESTA_FIXTURE} />);

    const external = screen.getByRole("link", { name: "Convention notes" });
    expect(external).toHaveAttribute("href", "https://example.com/con");
    expect(external).toHaveAttribute("rel", "noopener noreferrer");

    expect(screen.getByRole("link", { name: "ops" })).toHaveAttribute("href", "mailto:ops@example.com");
    expect(screen.getByRole("link", { name: "local heading" })).toHaveAttribute("href", "#supplies");
    expect(screen.getByRole("link", { name: "rules" })).toHaveAttribute("href", "https://example.com/rules");

    const unsafe = screen.getByText("x");
    expect(unsafe.closest("a")).toBeNull();
    expect(unsafe.closest("[data-link-kind='unsafe']")).not.toBeNull();
  });

  it("renders safe images with alt text and unresolved relative media visibly", () => {
    render(<MarkdownDocumentReader markdown={HESTA_FIXTURE} />);

    const img = screen.getByRole("img", { name: "Hesta portrait" });
    expect(img).toHaveAttribute("src", "https://example.com/hesta.webp");

    const unresolved = screen.getAllByTestId("markdown-reader-unresolved-media");
    expect(unresolved.some((el) => el.textContent?.includes("assets/hesta.webp"))).toBe(true);
    expect(unresolved.some((el) => el.textContent?.includes("Local art"))).toBe(true);
    expect(document.querySelector('img[src*="assets/hesta"]')).toBeNull();
  });

  it("shows raw HTML as escaped literal source and never executes it", () => {
    render(<MarkdownDocumentReader markdown={HESTA_FIXTURE} />);

    const literals = screen.getAllByTestId("markdown-reader-html-literal");
    expect(literals.some((el) => el.textContent?.includes("<script>alert(1)</script>"))).toBe(true);
    expect(literals.some((el) => el.textContent?.includes('<section class="raw">'))).toBe(true);
    expect(document.querySelector("script")).toBeNull();
    expect(document.querySelector("section.raw")).toBeNull();
  });

  it("resolves reference-style links from parser definitions without a second Markdown parser", () => {
    render(
      <MarkdownDocumentReader
        markdown={`See [the gate][gate].\n\n[gate]: https://example.com/gate "Gate"`}
      />,
    );
    const link = screen.getByRole("link", { name: "the gate" });
    expect(link).toHaveAttribute("href", "https://example.com/gate");
    expect(link).toHaveAttribute("title", "Gate");
  });

  it("falls back visibly for unknown parsed constructs instead of silent omission", async () => {
    const { parseMarkdownAst } = await import("../tiptap/markdown/parseMarkdownAst");
    const spy = vi.spyOn(await import("../tiptap/markdown/parseMarkdownAst"), "parseMarkdownAst").mockReturnValue({
      type: "root",
      children: [
        {
          type: "mysteryBlock" as "paragraph",
          position: { start: { line: 1, column: 1, offset: 0 }, end: { line: 1, column: 12, offset: 11 } },
          children: [],
        },
      ],
    } as ReturnType<typeof parseMarkdownAst>);

    try {
      render(<MarkdownDocumentReader markdown={"exact slice"} />);
      expect(screen.getByText("exact slice")).toBeInTheDocument();
      expect(screen.getByText("exact slice").closest("[data-node-type='mysteryBlock']")).not.toBeNull();
    } finally {
      spy.mockRestore();
    }
  });
});
