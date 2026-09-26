import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ToolHostView, type ToolHostViewGroup, type ToolHostViewTool } from "./ToolHostView";

function tool(id: string, disabledReason?: string): ToolHostViewTool {
  return {
    id,
    label: id,
    eyebrow: "Action",
    availability: disabledReason
      ? { status: "disabled", disabledReason }
      : { status: "enabled" },
  };
}

function group(...tools: ToolHostViewTool[]): ToolHostViewGroup {
  return { groupId: "group", groupLabel: "Group", groupOrder: 1, tools };
}

describe("ToolHostView", () => {
  it("renders ordered launcher content and emits only tool ids", () => {
    const onActivate = vi.fn();
    const first = tool("first");
    const second = tool("second");
    render(
      <ToolHostView
        groups={[group(first, second)]}
        isOpen
        usesIngestPeek={false}
        onToggle={vi.fn()}
        onDismiss={vi.fn()}
        onActivate={onActivate}
      />,
    );

    const drawer = screen.getByLabelText("Tools toolbar");
    expect(within(drawer).getByRole("navigation", { name: "Tool groups" })).toBeInTheDocument();
    expect(within(drawer).getByText("Group", { selector: "summary" })).toBeInTheDocument();
    const buttons = within(drawer).getAllByRole("button", { name: /first|second/ });
    expect(buttons.map((button) => button.textContent)).toEqual(["Actionfirst", "Actionsecond"]);
    fireEvent.click(buttons[1]);
    expect(onActivate).toHaveBeenCalledExactlyOnceWith("second");
  });

  it("preserves disabled reason, close controls, and legacy drawer structure", () => {
    const onDismiss = vi.fn();
    const onToggle = vi.fn();
    const onActivate = vi.fn();
    render(
      <ToolHostView
        groups={[group(tool("locked", "Not ready"))]}
        isOpen={false}
        usesIngestPeek={false}
        onToggle={onToggle}
        onDismiss={onDismiss}
        onActivate={onActivate}
      />,
    );

    const toggle = screen.getByRole("button", { name: "Tools" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(toggle).toHaveAttribute("aria-controls", "surface-tool-host-drawer");
    fireEvent.click(toggle);
    expect(onToggle).toHaveBeenCalledOnce();
    const locked = screen.getByRole("button", { name: "Action locked" });
    expect(locked).toBeDisabled();
    expect(locked).toHaveAttribute("title", "Not ready");
    fireEvent.click(locked);
    expect(onActivate).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Close Tools" }));
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(document.querySelector(".app-tools-toolbox-backdrop")).toHaveAttribute("hidden");
  });
});
