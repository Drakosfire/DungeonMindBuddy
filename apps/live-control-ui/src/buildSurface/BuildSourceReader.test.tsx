import { render, screen } from "@testing-library/react";
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
});
