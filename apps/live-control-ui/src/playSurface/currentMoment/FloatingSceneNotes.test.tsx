import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FloatingSceneNotes } from "./FloatingSceneNotes";

describe("FloatingSceneNotes", () => {
  afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });
  it("opens with keyboard focus, retains mounted input on collapse and returns focus on Escape", async () => {
    const user = userEvent.setup();
    render(<FloatingSceneNotes sceneTitle="North Gate" status="Unsaved">
      <label>Scene note<textarea defaultValue="Kept draft" /></label>
    </FloatingSceneNotes>);
    const toggle = screen.getByRole("button", { name: /Scene notes — North Gate/ });
    const field = screen.getByLabelText("Scene note");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(field).not.toBeVisible();
    await user.tab(); await user.keyboard("{Enter}");
    expect(field).toHaveFocus();
    await user.type(field, " more");
    await user.keyboard("{Escape}");
    expect(toggle).toHaveFocus();
    expect(field).not.toBeVisible();
    await user.keyboard("{Enter}");
    expect(field).toHaveValue("Kept draft more");
  });

  it("shows current target and attention while closed and suspends for other compact panels", () => {
    const { rerender } = render(<FloatingSceneNotes sceneTitle="A" status="Needs attention"><span>Retained</span></FloatingSceneNotes>);
    expect(screen.getByRole("button")).toHaveTextContent("Needs attention");
    rerender(<FloatingSceneNotes sceneTitle="B" status="Saving…" suspended><span>Retained</span></FloatingSceneNotes>);
    expect(screen.getByTestId("floating-scene-notes")).not.toBeVisible();
    rerender(<FloatingSceneNotes sceneTitle="B" status="Saved"><span>Retained</span></FloatingSceneNotes>);
    expect(screen.getByRole("button")).toHaveTextContent("Scene notes — B");
  });

  it("hides the collapsed navbar-owned frame while retaining its mounted draft", () => {
    const content = <label>Scene note<textarea defaultValue="Retained draft" /></label>;
    const view = render(<FloatingSceneNotes sceneTitle="North Gate" status="Saved" hideToggle open={false}>{content}</FloatingSceneNotes>);
    const field = screen.getByLabelText("Scene note");
    expect(screen.getByTestId("floating-scene-notes")).not.toBeVisible();
    view.rerender(<FloatingSceneNotes sceneTitle="North Gate" status="Saved" hideToggle open>{content}</FloatingSceneNotes>);
    expect(screen.getByLabelText("Scene note")).toBe(field);
    expect(field).toBeVisible();
    expect(field).toHaveValue("Retained draft");
  });

  it("moves by pointer and keyboard, stops cancelled drags, clamps on resize and retains the draft", async () => {
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockImplementation(function(this: HTMLElement) {
      const x = Number.parseFloat(this.style.left) || 16;
      const y = Number.parseFloat(this.style.top) || 100;
      return { x, y, left: x, top: y, right: x + 200, bottom: y + 200, width: 200, height: 200, toJSON: () => ({}) };
    });
    const user = userEvent.setup();
    render(<FloatingSceneNotes sceneTitle="North Gate" status="Unsaved"><label>Scene note<textarea defaultValue="Retained draft" /></label></FloatingSceneNotes>);
    await user.click(screen.getByRole("button", { name: /Scene notes — North Gate/ }));
    const field = screen.getByLabelText("Scene note");
    const handle = screen.getByRole("button", { name: "Move scene notes" });
    const frame = screen.getByTestId("floating-scene-notes");
    const pointer = (kind: string, x: number, y: number) => {
      const event = new MouseEvent(kind, { bubbles: true, clientX: x, clientY: y, button: 0 });
      Object.defineProperty(event, "pointerId", { value: 7 });
      fireEvent(handle, event);
    };
    pointer("pointerdown", 50, 50); pointer("pointermove", 150, 130);
    expect(frame).toHaveStyle({ left: "116px", top: "180px" });
    pointer("pointercancel", 150, 130); pointer("pointermove", 200, 200);
    expect(frame).toHaveStyle({ left: "116px", top: "180px" });
    handle.focus(); await user.keyboard("{ArrowRight}");
    expect(frame).toHaveStyle({ left: "132px" });
    vi.stubGlobal("innerWidth", 240);
    act(() => window.dispatchEvent(new Event("resize")));
    expect(frame).toHaveStyle({ left: "32px" });
    await user.click(screen.getByRole("button", { name: "Collapse scene notes" }));
    await user.click(screen.getByRole("button", { name: /Scene notes — North Gate/ }));
    expect(screen.getByLabelText("Scene note")).toBe(field);
    expect(field).toHaveValue("Retained draft");
  });

  it("does not fabricate a target when no scene is current", () => {
    render(<FloatingSceneNotes sceneTitle={null} available={false} status="No current scene">None</FloatingSceneNotes>);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("No current scene");
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });
});
