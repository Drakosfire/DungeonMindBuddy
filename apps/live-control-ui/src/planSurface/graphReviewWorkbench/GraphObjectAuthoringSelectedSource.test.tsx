import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import { GraphObjectAuthoringSelectedSource } from "./GraphObjectAuthoringSelectedSource";

const selectionWithContext: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  surroundingTextBefore: "The",
  surroundingTextAfter: "survived the night",
  graphId: "graph-c1s2",
  laneRole: "live",
  sourceArtifactPath: "/tmp/recap.md",
  paragraphOrdinal: 3,
};

const selectionWithoutContext: GraphAuthoringSelection = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  selectionKind: "text_span",
  selectedText: "gang",
  normalizedSelectedText: "gang",
  graphId: "graph-c1s2",
  laneRole: "live",
  sourceArtifactPath: "/tmp/recap.md",
};

describe("GraphObjectAuthoringSelectedSource", () => {
  it("shows selected phrase and readable context in the primary view", () => {
    render(<GraphObjectAuthoringSelectedSource selection={selectionWithContext} />);

    expect(screen.getByText("Selected source")).toBeInTheDocument();
    expect(screen.getByText("“gang”")).toBeInTheDocument();
    expect(screen.getByText(/Context/i)).toBeInTheDocument();
    expect(screen.getByText(/The/)).toBeInTheDocument();
    expect(screen.getByText(/survived the night/)).toBeInTheDocument();
    expect(screen.getByText(/Draft only. Nothing has been written./i)).toBeInTheDocument();
  });

  it("shows fallback context copy when no surrounding text exists", () => {
    render(<GraphObjectAuthoringSelectedSource selection={selectionWithoutContext} />);

    expect(screen.getByText("Selected phrase from the recap.")).toBeInTheDocument();
  });

  it("shows manual-entry copy instead of a quoted phrase when there is no recap selection", () => {
    const manualSelection: GraphAuthoringSelection = {
      campaignId: "longmont-c1",
      sessionId: "session-2",
      selectionKind: "text_span",
      selectedText: "",
      normalizedSelectedText: "",
      graphId: "graph-c1s2",
      laneRole: "live",
    };
    render(<GraphObjectAuthoringSelectedSource selection={manualSelection} />);

    expect(screen.getByText("New object")).toBeInTheDocument();
    expect(screen.getByText(/Authored directly/i)).toBeInTheDocument();
    expect(screen.queryByText("Context")).not.toBeInTheDocument();
    expect(screen.queryByText("Selected phrase from the recap.")).not.toBeInTheDocument();
  });

  it("does not show technical metadata in the primary view", () => {
    render(<GraphObjectAuthoringSelectedSource selection={selectionWithContext} />);

    const details = screen.getByTestId("graph-object-authoring-source-details");
    expect(details).not.toHaveAttribute("open");
  });

  it("reveals technical metadata when Source details is expanded", async () => {
    const user = userEvent.setup();
    render(<GraphObjectAuthoringSelectedSource selection={selectionWithContext} />);

    const details = screen.getByTestId("graph-object-authoring-source-details");
    expect(details).not.toHaveAttribute("open");

    await user.click(screen.getByText("Source details"));

    expect(details).toHaveAttribute("open");
    expect(screen.getByText("graph-c1s2")).toBeInTheDocument();
    expect(screen.getByText("live")).toBeInTheDocument();
    expect(screen.getByText("/tmp/recap.md")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
