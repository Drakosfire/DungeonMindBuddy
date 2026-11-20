import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BuildSourceReader } from "./BuildSourceReader";

describe("BuildSourceReader", () => {
  it("presents the record title and exact snapshot Markdown through the rich reader", () => {
    render(
      <BuildSourceReader
        title="The Glass Orchard — Convention One-Shot"
        markdown={"# Orchard\n\nA **quiet** grove with a [map](https://example.com/map).\n"}
        dirty={false}
      />,
    );

    expect(
      screen.getByRole("heading", { level: 1, name: "The Glass Orchard — Convention One-Shot" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("markdown-document-reader")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Orchard" })).toBeInTheDocument();
    expect(screen.getByText("quiet").closest("strong")).not.toBeNull();
    expect(screen.getByRole("link", { name: "map" })).toHaveAttribute("href", "https://example.com/map");
    expect(screen.queryByTestId("build-source-reader-dirty-warning")).not.toBeInTheDocument();
  });

  it("warns when dirty that Read shows the last saved source only", () => {
    render(
      <BuildSourceReader
        title="Orchard Gate Notes"
        markdown={"# Saved\n"}
        dirty
      />,
    );

    const warning = screen.getByTestId("build-source-reader-dirty-warning");
    expect(warning).toHaveTextContent(/last saved source/i);
    expect(warning).toHaveTextContent(/unsaved edits are not shown/i);
    expect(screen.getByRole("heading", { level: 1, name: "Saved" })).toBeInTheDocument();
  });

  it("strips leading frontmatter from prose while keeping title from the record", () => {
    render(
      <BuildSourceReader
        title="Record Title Wins"
        markdown={"---\ntitle: Frontmatter Title\n---\n\nBody only.\n"}
        dirty={false}
      />,
    );

    expect(screen.getByRole("heading", { level: 1, name: "Record Title Wins" })).toBeInTheDocument();
    expect(screen.queryByText("Frontmatter Title")).not.toBeInTheDocument();
    expect(screen.getByText("Body only.")).toBeInTheDocument();
  });

  it("passes exact line targets to the reader and omits them when stale", () => {
    const { rerender } = render(
      <BuildSourceReader
        title="Gate Notes"
        markdown={"# Gate\n\nTarget paragraph.\n"}
        dirty={false}
        navigationTarget={{
          status: "exact",
          startLine: 3,
          endLine: 3,
          targetKey: "artifact:span",
        }}
      />,
    );

    expect(screen.getByText("Target paragraph.").closest("[data-source-block='true']")).not.toBeNull();
    expect(screen.queryByTestId("build-source-reader-navigation-status")).not.toBeInTheDocument();

    rerender(
      <BuildSourceReader
        title="Gate Notes"
        markdown={"# Gate\n\nTarget paragraph.\n"}
        dirty={false}
        navigationTarget={{
          status: "stale",
          message: "Source drift detected.",
          targetKey: "artifact:span",
        }}
      />,
    );

    const status = screen.getByTestId("build-source-reader-navigation-status");
    expect(status).toHaveAttribute("data-navigation-status", "stale");
    expect(status).toHaveTextContent(/source drift detected/i);
    expect(document.querySelector("[data-source-block='true']")).toBeNull();
  });

  it("shows document mismatch status without highlight props", () => {
    render(
      <BuildSourceReader
        title="Gate Notes"
        markdown={"# Gate\n\nTarget paragraph.\n"}
        dirty={false}
        navigationTarget={{
          status: "document_mismatch",
          message: "Wrong document open.",
          targetKey: "artifact:span",
        }}
      />,
    );

    const status = screen.getByTestId("build-source-reader-navigation-status");
    expect(status).toHaveAttribute("data-navigation-status", "document_mismatch");
    expect(status).toHaveTextContent(/wrong document open/i);
    expect(document.querySelector("[data-source-block='true']")).toBeNull();
  });
});


describe("saved Build source navigation", () => {
  it("links parsed headings to rendered IDs, including duplicate and formatted headings", () => {
    const markdown = "---\ntitle: Hidden metadata\n---\n\n# City\n\n## **Guard** headquarters\n\n> ### Signals\n\n## Guard headquarters\n\n```md\n# Not a section\n```\n";
    render(<BuildSourceReader title="Mirathorn" markdown={markdown} dirty={false} />);
    const nav = screen.getByRole("navigation", { name: "Source sections" });
    const links = within(nav).getAllByRole("link");
    expect(links).toHaveLength(4);
    expect(links.map(link => link.getAttribute("href"))).toEqual([
      "#city", "#guard-headquarters", "#signals", "#guard-headquarters-1",
    ]);
    for (const link of links) {
      const target = document.getElementById(link.getAttribute("href")!.slice(1));
      expect(target).not.toBeNull();
      expect(target!.textContent).toBe(link.textContent);
    }
    expect(within(nav).queryByText("Not a section")).not.toBeInTheDocument();
    const disclosure = nav.closest("details")!;
    disclosure.open = true;
    fireEvent.click(links[3]);
    expect(disclosure.open).toBe(false);
  });

  it("updates routes on saved-source replacement and leaves short sources quiet", () => {
    const { rerender } = render(<BuildSourceReader title="City" markdown={"# City\n\n## Gates\n\n## Guard\n"} dirty={false} />);
    expect(screen.getByRole("navigation", { name: "Source sections" })).toBeInTheDocument();
    rerender(<BuildSourceReader title="Other source" markdown={"# Village\n\n## Inn\n"} dirty={false} />);
    expect(screen.queryByRole("navigation", { name: "Source sections" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Inn" })).toBeInTheDocument();
  });
});
