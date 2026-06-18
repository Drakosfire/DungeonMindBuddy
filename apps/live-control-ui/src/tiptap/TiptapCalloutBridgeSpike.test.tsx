import { render, screen } from "@testing-library/react";

import { TiptapCalloutBridgeSpike } from "./TiptapCalloutBridgeSpike";
import {
  normalizeCalloutKind,
  tiptapJsonToSemanticMarkdown,
} from "./markdown/calloutMarkdown";

describe("semantic callout Markdown bridge", () => {
  it.each([
    ["read-aloud", "read-aloud"],
    ["read-aloud-text", "read-aloud"],
    ["readaloud", "read-aloud"],
    ["gm-note", "gm-note"],
    ["dm", "gm-note"],
    ["rules", "rules"],
    ["rules-note", "rules"],
    ["rule", "rules"],
    ["warning", "warning"],
    ["warn", "warning"],
    ["danger", "warning"],
    ["unknown", "warning"],
  ] as const)("normalizes %s to %s", (input, expected) => {
    expect(normalizeCalloutKind(input)).toBe(expected);
  });

  it("serializes callout JSON to semantic Markdown", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "callout",
      attrs: { kind: "warning" },
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gate fails in 3 rounds." }],
        },
      ],
    });

    expect(markdown).toContain("> [!WARNING]\n> The gate fails in 3 rounds.");
  });

  it("serializes custom callout labels", () => {
    const markdown = tiptapJsonToSemanticMarkdown({
      type: "callout",
      attrs: { kind: "warning", label: "Breach clock" },
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gate fails in 3 rounds." }],
        },
      ],
    });

    expect(markdown).toContain("> [!WARNING] Breach clock");
  });

  it("renders the spike surface and initialized callouts", async () => {
    render(<TiptapCalloutBridgeSpike />);

    expect(screen.getByRole("heading", { name: "Tiptap Semantic Callout Bridge Spike" })).toBeInTheDocument();
    expect(screen.getByTestId("tiptap-editor")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Editor JSON" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Exported Markdown" })).toBeInTheDocument();
    expect(await screen.findAllByText("Read aloud")).not.toHaveLength(0);
  });
});
