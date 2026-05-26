import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { mockCatalog, mockLayout } from "../test/fixtures";
import { LayoutControls } from "./LayoutControls";

describe("LayoutControls", () => {
  it("keeps required modules enabled and locked", async () => {
    const user = userEvent.setup();
    render(
      <LayoutControls layout={mockLayout} catalog={mockCatalog} onLayoutSaved={vi.fn()} />,
    );

    const checkboxes = screen.getAllByLabelText("Enabled");
    const chatCheckbox = checkboxes[0];
    expect(chatCheckbox).toBeDisabled();
    expect(chatCheckbox).toBeChecked();

    await user.click(chatCheckbox);
    expect(chatCheckbox).toBeChecked();
  });

  it("disables optional module and persists through PUT", async () => {
    const user = userEvent.setup();
    const putSpy = vi.spyOn(liveApi, "putSurfaceLayout").mockResolvedValue({
      layout: {
        ...mockLayout,
        modules: mockLayout.modules.map((row) =>
          row.module_id === "roll_stack" ? { ...row, enabled: false } : row,
        ),
      },
    });
    const onSaved = vi.fn();

    render(
      <LayoutControls layout={mockLayout} catalog={mockCatalog} onLayoutSaved={onSaved} />,
    );

    const rollToggle = screen
      .getAllByLabelText("Enabled")
      .find((input) => !input.hasAttribute("disabled"))!;
    await user.click(rollToggle);
    await user.click(screen.getByRole("button", { name: /save layout/i }));

    expect(putSpy).toHaveBeenCalledTimes(1);
    const savedLayout = putSpy.mock.calls[0][0];
    const rollRow = savedLayout.modules.find((row) => row.module_id === "roll_stack");
    expect(rollRow?.enabled).toBe(false);
    expect(onSaved).toHaveBeenCalled();
  });

  it("reorders module and PUTs changed layout", async () => {
    const user = userEvent.setup();
    const putSpy = vi.spyOn(liveApi, "putSurfaceLayout").mockImplementation(async (layout) => ({
      layout,
    }));

    render(
      <LayoutControls layout={mockLayout} catalog={mockCatalog} onLayoutSaved={vi.fn()} />,
    );

    const downButtons = screen.getAllByRole("button", { name: "Down" });
    await user.click(downButtons[0]);
    await user.click(screen.getByRole("button", { name: /save layout/i }));

    expect(putSpy).toHaveBeenCalled();
    putSpy.mockRestore();
  });
});
