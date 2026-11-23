import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import { GuestReleaseDrawer } from "./GuestReleaseDrawer";

vi.mock("./GuestReleaseReview", () => ({ GuestReleaseReview: ({ worldId }: { worldId: string }) => <section>Review for {worldId}<input aria-label="Draft note" /></section> }));

it("opens and closes the owner review without replacing the graph", async () => {
  const user = userEvent.setup();
  render(<><main>Graph workspace</main><GuestReleaseDrawer worldId="world" /></>);
  const control = screen.getByText("Review guest copy").closest("summary")!;
  const drawer = control.closest("details")!;
  expect(drawer.open).toBe(false);
  await user.click(control);
  expect(drawer.open).toBe(true);
  expect(screen.getByText("Review for world")).toBeVisible();
  expect(screen.getByText("Graph workspace")).toBeVisible();
  await user.type(screen.getByLabelText("Draft note"), "keep this draft");
  await user.click(control);
  expect(drawer.open).toBe(false);
  expect(screen.getByText("Graph workspace")).toBeVisible();
  await user.click(control);
  expect(screen.getByLabelText("Draft note")).toHaveValue("keep this draft");
});
