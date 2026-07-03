import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphProjectionReader } from "./GraphProjectionReader";

function nodeView(overrides: Partial<GraphProjectionNodeView> & { node_id: string; label: string }): GraphProjectionNodeView {
  return {
    kind: "npc",
    role: "npc",
    aliases: [overrides.label],
    source_domains: ["recap"],
    anchored_to_focus_session: false,
    evidence_badges: [],
    adjacency: [],
    ...overrides,
  };
}

describe("GraphProjectionReader", () => {
  it("keeps node views, active selection, and delta presentations isolated across two simultaneously mounted readers", async () => {
    // Regression test for the module-singleton runtime bug: two readers used
    // to share one global store, so whichever reader's effect ran last would
    // clobber the other's nodeViews/deltaByNodeId for every rendered token.
    const goldNode = nodeView({ node_id: "n1", label: "Karsemine" });
    const liveNode = nodeView({ node_id: "n1", label: "Karsemine the Ranger" });

    render(
      <>
        <GraphProjectionReader
          markdown="[Karsemine](dmb-node:n1) scouted ahead."
          nodeViews={{ n1: goldNode }}
          sourceSpans={[]}
          nodeDeltaPresentations={{ n1: { status: "gold_only", label: "Gold-only" } }}
          disableInlineExplorer
          documentLabel="Gold lane"
        />
        <GraphProjectionReader
          markdown="[Karsemine the Ranger](dmb-node:n1) scouted ahead."
          nodeViews={{ n1: liveNode }}
          sourceSpans={[]}
          nodeDeltaPresentations={{ n1: { status: "live_only", label: "Live-only" } }}
          disableInlineExplorer
          documentLabel="Live lane"
        />
      </>,
    );

    const findPill = (predicate: (text: string) => boolean) =>
      waitFor(() => {
        const pill = screen
          .getAllByRole("button")
          .find((button) => button.classList.contains("recap-node-token") && predicate(button.textContent ?? ""));
        expect(pill).toBeTruthy();
        return pill as HTMLButtonElement;
      });

    const goldPill = await findPill((text) => text.startsWith("Karsemine") && !text.includes("Ranger"));
    const livePill = await findPill((text) => text.includes("Karsemine the Ranger"));

    expect(goldPill).toHaveAttribute("data-delta-status", "gold_only");
    expect(livePill).toHaveAttribute("data-delta-status", "live_only");
    expect(goldPill.textContent).toContain("Gold-only");
    expect(livePill.textContent).toContain("Live-only");
  });

  it("propagates cross-lane highlighting via highlightedNodeId without a shared global store", async () => {
    const node = nodeView({ node_id: "n1", label: "Stafl" });

    render(
      <GraphProjectionReader
        markdown="[Stafl](dmb-node:n1) tuned his lute."
        nodeViews={{ n1: node }}
        sourceSpans={[]}
        highlightedNodeId="n1"
        disableInlineExplorer
      />,
    );

    const pill = await waitFor(() => {
      const found = screen.getByRole("button", { name: "Stafl" });
      expect(found).toBeInTheDocument();
      return found;
    });
    expect(pill).toHaveClass("counterpart-highlighted");
    expect(pill).toHaveAttribute("data-counterpart-highlighted", "true");
  });

  it("fires onHoverNode on hover/unhover and onActiveNodeChange on click while disableInlineExplorer suppresses the flyout panel", async () => {
    const node = nodeView({ node_id: "n1", label: "Bonogo" });
    const onHoverNode = vi.fn();
    const onActiveNodeChange = vi.fn();

    render(
      <GraphProjectionReader
        markdown="[Bonogo](dmb-node:n1) picked the lock."
        nodeViews={{ n1: node }}
        sourceSpans={[]}
        disableInlineExplorer
        onHoverNode={onHoverNode}
        onActiveNodeChange={onActiveNodeChange}
      />,
    );

    const pill = await waitFor(() => {
      const found = screen.getByRole("button", { name: "Bonogo" });
      expect(found).toBeInTheDocument();
      return found;
    });

    fireEvent.mouseEnter(pill);
    expect(onHoverNode).toHaveBeenCalledWith("n1");
    fireEvent.mouseLeave(pill);
    expect(onHoverNode).toHaveBeenCalledWith(null);

    fireEvent.click(pill);
    expect(onActiveNodeChange).toHaveBeenCalledWith("n1");
    expect(screen.queryByLabelText("Graph node explorer")).not.toBeInTheDocument();
  });

  it("reports selected text via onSelectText on mouseup", () => {
    const onSelectText = vi.fn();
    render(
      <GraphProjectionReader
        markdown="Plain prose with no graph mentions."
        nodeViews={{}}
        sourceSpans={[]}
        onSelectText={onSelectText}
      />,
    );

    vi.spyOn(window, "getSelection").mockReturnValue({
      toString: () => "Plain prose",
    } as unknown as Selection);

    fireEvent.mouseUp(screen.getByLabelText("Projected recap"));
    expect(onSelectText).toHaveBeenCalledWith("Plain prose");
  });
});
