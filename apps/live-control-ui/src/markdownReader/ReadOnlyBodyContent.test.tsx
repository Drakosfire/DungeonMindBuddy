import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { JSONContent } from "@tiptap/core";
import { ReadOnlyBodyContent } from "./ReadOnlyBodyContent";

const graphContent: JSONContent[] = [{
  type: "paragraph",
  content: [
    { type: "text", text: "Consult " },
    { type: "graphNodeReference", attrs: { nodeId: "loc:ironveil-warehouse", label: "Ironveil Warehouse" } },
    { type: "text", text: " before entering." },
  ],
}];

describe("ReadOnlyBodyContent Graph-reference activation", () => {
  it("keeps Graph references inert by default", () => {
    render(<ReadOnlyBodyContent content={graphContent} />);

    const reference = screen.getByText("Ironveil Warehouse");
    expect(reference.tagName).toBe("SPAN");
    expect(reference.closest("button")).toBeNull();
    expect(reference).toHaveAttribute("data-graph-node-id", "loc:ironveil-warehouse");
  });

  it("opts into a native keyboard-accessible button and sends its exact node ID", async () => {
    const onActivateGraphNode = vi.fn();
    const user = userEvent.setup();
    render(<ReadOnlyBodyContent content={graphContent} onActivateGraphNode={onActivateGraphNode} />);

    const reference = screen.getByRole("button", { name: "Ironveil Warehouse" });
    expect(reference).toHaveAttribute("data-graph-node-id", "loc:ironveil-warehouse");
    await user.tab();
    expect(reference).toHaveFocus();
    await user.keyboard("{Enter}");

    expect(onActivateGraphNode).toHaveBeenCalledTimes(1);
    expect(onActivateGraphNode).toHaveBeenCalledWith("loc:ironveil-warehouse");
  });

  it("does not activate references when authored content fails the safe-rendering checks", () => {
    const onActivateGraphNode = vi.fn();
    const unsafeContent: JSONContent[] = [
      ...graphContent,
      { type: "image", attrs: { src: "javascript:alert(1)" } },
    ];
    render(<ReadOnlyBodyContent content={unsafeContent} onActivateGraphNode={onActivateGraphNode} />);

    expect(screen.getByRole("status")).toHaveTextContent("cannot be displayed safely");
    expect(screen.queryByRole("button", { name: "Ironveil Warehouse" })).not.toBeInTheDocument();
    expect(onActivateGraphNode).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("status"));
    expect(onActivateGraphNode).not.toHaveBeenCalled();
  });
});
