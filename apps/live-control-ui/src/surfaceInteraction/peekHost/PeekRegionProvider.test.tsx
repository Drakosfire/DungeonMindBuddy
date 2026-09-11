import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { PeekClaim, PeekRegionProvider, PeekRegionSlot } from "./PeekRegionProvider";

function StatefulObject() {
  const [count, setCount] = useState(0);
  return <button onClick={() => setCount((value) => value + 1)}>Object state {count}</button>;
}

function Harness() {
  const [tools, setTools] = useState(false);
  const [projection, setProjection] = useState(false);
  return (
    <PeekRegionProvider>
      <button onClick={() => setTools((value) => !value)}>Toggle tools</button>
      <button onClick={() => setProjection((value) => !value)}>Toggle projection</button>
      <PeekRegionSlot />
      <PeekClaim kind="world-object" active><StatefulObject /></PeekClaim>
      <PeekClaim kind="tools" active={tools}><p>Tools content</p></PeekClaim>
      <PeekClaim kind="projection" active={projection}><p>Projection content</p></PeekClaim>
    </PeekRegionProvider>
  );
}

describe("PeekRegionProvider", () => {
  it("shows one highest-priority claim while retaining lower-priority mounted state", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    const slot = screen.getByTestId("app-peek-region");
    await user.click(screen.getByRole("button", { name: "Object state 0" }));
    expect(slot).toHaveAttribute("data-active-peek", "world-object");

    await user.click(screen.getByRole("button", { name: "Toggle tools" }));
    expect(slot).toHaveAttribute("data-active-peek", "tools");
    expect(screen.getByText("Tools content")).toBeVisible();
    expect(screen.getByRole("button", { name: "Object state 1", hidden: true })).not.toBeVisible();

    await user.click(screen.getByRole("button", { name: "Toggle projection" }));
    expect(slot).toHaveAttribute("data-active-peek", "projection");
    expect(screen.getByText("Projection content")).toBeVisible();
    expect(screen.getByText("Tools content")).not.toBeVisible();

    await user.click(screen.getByRole("button", { name: "Toggle projection" }));
    expect(slot).toHaveAttribute("data-active-peek", "tools");
    await user.click(screen.getByRole("button", { name: "Toggle tools" }));
    expect(slot).toHaveAttribute("data-active-peek", "world-object");
    expect(screen.getByRole("button", { name: "Object state 1" })).toBeVisible();
  });

  it("collapses the physical slot when no claim is active", () => {
    render(
      <PeekRegionProvider>
        <PeekRegionSlot />
      </PeekRegionProvider>,
    );
    expect(screen.getByTestId("app-peek-region")).toHaveAttribute("hidden");
  });
});
