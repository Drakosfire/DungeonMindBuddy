import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { FloatingSceneNotes } from "./FloatingSceneNotes";

describe("FloatingSceneNotes", () => {
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

  it("does not fabricate a target when no scene is current", () => {
    render(<FloatingSceneNotes sceneTitle={null} available={false} status="No current scene">None</FloatingSceneNotes>);
    expect(screen.getByRole("button")).toBeDisabled();
    expect(screen.getByRole("button")).toHaveTextContent("No current scene");
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByRole("button")).toHaveAttribute("aria-expanded", "false");
  });
});
