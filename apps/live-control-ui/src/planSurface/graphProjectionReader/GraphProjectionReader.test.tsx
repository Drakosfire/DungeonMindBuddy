import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphProjectionReader } from "./GraphProjectionReader";

const aldenNode: GraphProjectionNodeView = {
  node_id: "alden",
  label: "Alden",
  kind: "npc",
  role: "gate warden",
  summary: "Alden guards the western gate.",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
};

describe("GraphProjectionReader", () => {
  it("does not render graph authoring UI when authoring is disabled", async () => {
    render(
      <GraphProjectionReader
        markdown="The gang arrived at the gate."
        nodeViews={{}}
        sourceSpans={[]}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText(/The gang arrived/)).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-authoring-action")).not.toBeInTheDocument();
  });

  it("delegates graph chip inspection to an external handler when provided", async () => {
    const onInspectNode = vi.fn();

    render(
      <GraphProjectionReader
        markdown="The party met [Alden](dmb-node:alden) at the gate."
        nodeViews={{ alden: aldenNode }}
        sourceSpans={[]}
        onInspectNode={onInspectNode}
      />,
    );

    const aldenPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Alden" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });

    fireEvent.click(aldenPill);
    expect(onInspectNode).toHaveBeenCalledWith("alden");
    expect(screen.queryByLabelText("Graph node explorer")).not.toBeInTheDocument();
  });

  it("opens the internal explorer when no external inspection handler is provided", async () => {
    render(
      <GraphProjectionReader
        markdown="The party met [Alden](dmb-node:alden) at the gate."
        nodeViews={{ alden: aldenNode }}
        sourceSpans={[]}
      />,
    );

    const aldenPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Alden" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });

    fireEvent.click(aldenPill);
    expect(screen.getByLabelText("Graph node explorer")).toBeInTheDocument();
  });

  it("shows the authoring action and forwards the callback when a valid selection exists", async () => {
    const onGraphAuthoringSelection = vi.fn();
    const onGraphAuthoringAction = vi.fn();

    render(
      <GraphProjectionReader
        markdown="The gang arrived at the gate."
        nodeViews={{}}
        sourceSpans={[]}
        authoringEnabled
        authoringContext={{
          campaignId: "longmont-c1",
          sessionId: "session-2",
          graphId: "graph-c1s2",
          laneRole: "live",
        }}
        onGraphAuthoringSelection={onGraphAuthoringSelection}
        onGraphAuthoringAction={onGraphAuthoringAction}
      />,
    );

    await waitFor(() => {
      expect(document.querySelector(".ProseMirror")).toBeTruthy();
    });

    const proseMirror = document.querySelector(".ProseMirror") as HTMLElement;
    const paragraph = proseMirror.querySelector("p");
    expect(paragraph).toBeTruthy();

    const range = document.createRange();
    const textNode = paragraph!.firstChild as Text;
    const startIndex = textNode.textContent!.indexOf("gang");
    range.setStart(textNode, startIndex);
    range.setEnd(textNode, startIndex + 4);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    fireEvent.mouseUp(proseMirror);

    await waitFor(() => {
      expect(onGraphAuthoringSelection).toHaveBeenCalledWith(
        expect.objectContaining({
          selectionKind: "text_span",
          selectedText: "gang",
          campaignId: "longmont-c1",
          sessionId: "session-2",
        }),
      );
    });

    fireEvent.click(screen.getByTestId("graph-authoring-action"));
    expect(onGraphAuthoringAction).toHaveBeenCalledWith(
      expect.objectContaining({
        selectionKind: "text_span",
        selectedText: "gang",
      }),
      "author_object",
    );
  });

  it("uses contained document scroll by default", async () => {
    render(
      <GraphProjectionReader
        markdown="The gang arrived at the gate."
        nodeViews={{}}
        sourceSpans={[]}
        documentLabel="Projected recap"
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Projected recap")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Projected recap")).not.toHaveClass(
      "recap-reader-document--page-scroll",
    );
  });

  it("supports page scroll mode for embedded workbench readers", async () => {
    render(
      <GraphProjectionReader
        markdown="The gang arrived at the gate."
        nodeViews={{}}
        sourceSpans={[]}
        documentLabel="Live run prose"
        documentScroll="page"
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText("Live run prose")).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Live run prose")).toHaveClass(
      "recap-reader-document--page-scroll",
    );
  });
});
