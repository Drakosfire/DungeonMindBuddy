import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CompactAppNavigation } from "./CompactAppNavigation";

vi.mock("../selectedWorld/SelectedWorldContext", () => ({ useSelectedWorld: () => ({ kind: "managed", worldId: "elderwyld", name: "Elderwyld" }) }));
vi.mock("../selectedWorld/WorldSelector", () => ({ WorldSelector: () => <button>Switch World: Elderwyld</button> }));
vi.mock("./AppChromeWorldGraphStatus", () => ({ AppChromeWorldGraphStatus: () => <button>World graph: Elderwyld · Ready</button> }));

describe("compact command-board navigation", () => {
  it("starts collapsed with World selection and graph health always reachable", () => {
    render(<CompactAppNavigation activeRoute="plan" />);
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("link", { name: "Build" })).not.toBeInTheDocument();
    expect(document.querySelector(".app-nav-current")).toHaveTextContent("Plan");
    expect(screen.getByRole("button", { name: "Switch World: Elderwyld" })).toBeVisible();
    expect(screen.getByRole("button", { name: "World graph: Elderwyld · Ready" })).toBeVisible();
  });
  it("reveals World-scoped routes and dismisses them with Escape without navigation", () => {
    render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    const nav = screen.getByRole("navigation", { name: "Command board navigation" });
    expect(within(nav).getByRole("link", { name: "Plan" })).toHaveAttribute("href", "/plan?world=elderwyld");
    expect(within(nav).getByRole("link", { name: "Plan" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("link", { name: "Combat Tracker" })).toHaveAttribute("href", "/combat");
    fireEvent.keyDown(within(nav).getByRole("link", { name: "Build" }), { key: "Escape" });
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveFocus();
    expect(screen.queryByRole("link", { name: "Build" })).not.toBeInTheDocument();
  });
  it("preserves same-document World navigation and collapses after a normal click", () => {
    window.history.replaceState({}, "", "/plan?world=elderwyld");
    const history = vi.spyOn(window.history, "pushState");
    render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    fireEvent.click(screen.getByRole("link", { name: "Build" }));
    expect(history).toHaveBeenCalledTimes(1);
    expect(window.location.pathname + window.location.search).toBe("/build?world=elderwyld");
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    history.mockRestore();
  });
  it("collapses on a surface change without remounting the workspace", () => {
    const view = render(<CompactAppNavigation activeRoute="plan" />);
    fireEvent.click(screen.getByRole("button", { name: "Open navigation" }));
    view.rerender(<CompactAppNavigation activeRoute="build" />);
    expect(screen.getByRole("button", { name: "Open navigation" })).toHaveAttribute("aria-expanded", "false");
    expect(document.querySelector(".app-nav-current")).toHaveTextContent("Build");
  });
});
