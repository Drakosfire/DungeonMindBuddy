import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { mockCatalog, mockLayout, mockState } from "../test/fixtures";
import { LayoutDraftProvider } from "./LayoutDraftContext";
import { ModuleLayoutControls } from "./ModuleLayoutControls";
import { SurfaceShell } from "./SurfaceShell";

function renderWithDraft(ui: ReactElement, onSaved = vi.fn()) {
  return render(
    <LayoutDraftProvider layout={mockLayout} catalog={mockCatalog} onLayoutSaved={onSaved}>
      {ui}
    </LayoutDraftProvider>,
  );
}

describe("ModuleLayoutControls", () => {
  it("keeps required chat module enabled and locked", async () => {
    const user = userEvent.setup();
    renderWithDraft(<ModuleLayoutControls moduleId="chat" />);

    const controls = screen.getByLabelText(/Layout controls for Chat/i);
    const enabled = within(controls).getByRole("checkbox");
    expect(enabled).toBeDisabled();
    expect(enabled).toBeChecked();
    await user.click(enabled);
    expect(enabled).toBeChecked();
  });

  it("disables optional roll_stack and persists through PUT", async () => {
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

    renderWithDraft(<ModuleLayoutControls moduleId="roll_stack" />, onSaved);

    const controls = screen.getByLabelText(/Layout controls for Roll stack/i);
    await user.click(within(controls).getByRole("checkbox"));
    await user.click(within(controls).getByRole("button", { name: /^Save$/i }));

    expect(putSpy).toHaveBeenCalledTimes(1);
    const rollRow = putSpy.mock.calls[0][0].modules.find((row) => row.module_id === "roll_stack");
    expect(rollRow?.enabled).toBe(false);
    expect(onSaved).toHaveBeenCalled();
  });

  it("reorders module via embedded down control and PUTs layout", async () => {
    const user = userEvent.setup();
    const putSpy = vi.spyOn(liveApi, "putSurfaceLayout").mockImplementation(async (layout) => ({
      layout,
    }));

    renderWithDraft(<ModuleLayoutControls moduleId="chat" />);
    const controls = screen.getByLabelText(/Layout controls for Chat/i);
    await user.click(within(controls).getByRole("button", { name: /Move Chat down/i }));
    await user.click(within(controls).getByRole("button", { name: /^Save$/i }));

    expect(putSpy).toHaveBeenCalled();
    putSpy.mockRestore();
  });
});

describe("SurfaceShell embedded layout controls", () => {
  it("renders layout controls inside each module header", () => {
    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[]}
        jobs={[]}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    const chatPanel = document.querySelector('[data-module-id="chat"]')!;
    expect(within(chatPanel as HTMLElement).getByLabelText(/Layout controls for Chat/i)).toBeTruthy();
    const recordPanel = document.querySelector('[data-module-id="record"]')!;
    expect(
      within(recordPanel as HTMLElement).getByLabelText(/Layout controls for Record/i),
    ).toBeTruthy();
  });
});
