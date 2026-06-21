import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { EditCapabilityProvider, useEditCapability } from "./editCapability";

function LockProbe() {
  const { isLocked, toggleLock, canEdit } = useEditCapability();
  return (
    <div>
      <span data-testid="locked">{String(isLocked)}</span>
      <span data-testid="can-edit">{String(canEdit)}</span>
      <button type="button" onClick={toggleLock}>
        Toggle
      </button>
    </div>
  );
}

describe("editCapability", () => {
  it("defaults to locked read-only and toggles edit", async () => {
    const user = userEvent.setup();
    render(
      <EditCapabilityProvider>
        <LockProbe />
      </EditCapabilityProvider>,
    );

    expect(screen.getByTestId("locked")).toHaveTextContent("true");
    expect(screen.getByTestId("can-edit")).toHaveTextContent("false");

    await user.click(screen.getByRole("button", { name: "Toggle" }));

    expect(screen.getByTestId("locked")).toHaveTextContent("false");
    expect(screen.getByTestId("can-edit")).toHaveTextContent("true");
  });
});
