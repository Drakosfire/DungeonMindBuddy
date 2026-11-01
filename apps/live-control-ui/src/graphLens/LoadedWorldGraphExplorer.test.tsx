import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";
import type { SelectedWorldState } from "../selectedWorld/SelectedWorldContext";
import { LoadedWorldGraphExplorer } from "./LoadedWorldGraphExplorer";

const state = vi.hoisted(() => ({ world: { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null } as SelectedWorldState, rejectLoad: false }));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({ useSelectedWorld: () => state.world }));
vi.mock("../ui/deferredComponent", async importOriginal => {
  const actual = await importOriginal<typeof import("../ui/deferredComponent")>();
  return { deferredComponent: (load: Parameters<typeof actual.deferredComponent>[0], label: string) =>
    actual.deferredComponent(() => {
      if (state.rejectLoad) {
        state.rejectLoad = false;
        return Promise.reject(new Error("Inspector chunk unavailable"));
      }
      return load();
    }, label) };
});
vi.mock("./NativeGraphInspection", () => ({ NativeGraphInspection: ({ worldId }: { worldId: string }) => <section aria-label="Native inspector">{worldId}</section> }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
beforeEach(() => { state.rejectLoad = false; state.world = { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null }; });
afterEach(cleanup);

it("mounts inspection only while open, closes with Escape and restores focus", async () => {
  render(<LoadedWorldGraphExplorer />);
  const launcher = screen.getByRole("button", { name: "Explore graph" });
  expect(screen.queryByRole("region", { name: "Native inspector" })).not.toBeInTheDocument();
  fireEvent.click(launcher);
  const dialog = screen.getByRole("dialog", { name: "Elderwyld World graph" });
  expect(await screen.findByRole("region", { name: "Native inspector" })).toHaveTextContent("elderwyld");
  expect(screen.queryByRole("group", { name: "Graph material" })).not.toBeInTheDocument();
  fireEvent(dialog, new Event("cancel", { cancelable: true }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Native inspector" })).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
  fireEvent.click(launcher);
  await screen.findByRole("region", { name: "Native inspector" });
  fireEvent.click(screen.getByRole("button", { name: "Close graph" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(launcher).toHaveFocus();
});

it("discards the inspector on managed World switch and opens the new World", async () => {
  const view = render(<LoadedWorldGraphExplorer />);
  fireEvent.click(screen.getByRole("button", { name: "Explore graph" }));
  await screen.findByRole("region", { name: "Native inspector" });
  state.world = { kind: "managed", worldId: "sheep", name: "Sheep", documentId: null };
  view.rerender(<LoadedWorldGraphExplorer />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.queryByText("elderwyld")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Explore graph" }));
  expect(screen.getByRole("dialog", { name: "Sheep World graph" })).toBeVisible();
  expect(await screen.findByRole("region", { name: "Native inspector" })).toHaveTextContent("sheep");
});

it.each(["legacy", "loading", "error"] as const)("does not infer an inspection World from %s selection", kind => {
  state.world = kind === "loading" ? { kind, requestedWorldId: "elderwyld" } : kind === "error" ? { kind, message: "Unavailable" } : { kind };
  render(<LoadedWorldGraphExplorer />);
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Native inspector" })).not.toBeInTheDocument();
});

it("contains a failed inspector download and retries inside the same modal", async () => {
  const errorLog = vi.spyOn(console, "error").mockImplementation(() => undefined);
  try {
    state.rejectLoad = true;
    render(<LoadedWorldGraphExplorer />);
    const launcher = screen.getByRole("button", { name: "Explore graph" });
    fireEvent.click(launcher);
    const dialog = screen.getByRole("dialog", { name: "Elderwyld World graph" });
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load World graph.");
    expect(dialog).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Retry World graph" }));
    expect(await screen.findByRole("region", { name: "Native inspector" })).toHaveTextContent("elderwyld");
    expect(screen.getByRole("dialog")).toBe(dialog);
    fireEvent.click(screen.getByRole("button", { name: "Close graph" }));
    expect(launcher).toHaveFocus();
  } finally { errorLog.mockRestore(); }
});
