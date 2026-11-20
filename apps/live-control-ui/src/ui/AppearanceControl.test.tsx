import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { AppearanceControl } from "./AppearanceControl";
import { appearanceAccentRequest, DEFAULT_APPEARANCE, displayAppearance } from "./appearanceSettings";

afterEach(() => {
  cleanup();
  displayAppearance(DEFAULT_APPEARANCE);
  localStorage.clear();
});

it("recognizes direct accent requests and leaves creative writing in conversation", () => {
  expect(appearanceAccentRequest("Set Buddy’s accent to Sky blue.")).toBe("sky");
  expect(appearanceAccentRequest("Change my app accent to the default")).toBe("preset");
  expect(appearanceAccentRequest("Make the bath house accent sky blue")).toBeNull();
  expect(appearanceAccentRequest("Write a line that says set Buddy's accent to sky blue")).toBeNull();
});

it("previews an offered accent and writes settings only on Apply", () => {
  displayAppearance({ preset: "deep-teal", accent: "preset" });
  render(<AppearanceControl proposedAccent="sky" />);
  const dialog = document.querySelector("dialog")!;
  dialog.showModal = () => { dialog.open = true; };
  dialog.close = () => {
    dialog.open = false;
    fireEvent(dialog, new Event("close"));
  };
  const preview = screen.getByRole("button", { name: "Preview accent" });
  fireEvent.click(preview);
  expect(document.documentElement.dataset.buddyAccent).toBe("sky");
  expect(localStorage.getItem("buddy.appearance.settings")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(document.documentElement.dataset.buddyAccent).toBeUndefined();
  fireEvent.click(preview);
  fireEvent.click(screen.getByRole("button", { name: "Apply" }));
  expect(JSON.parse(localStorage.getItem("buddy.appearance.settings")!)).toEqual({
    preset: "deep-teal", accent: "sky",
  });
});
