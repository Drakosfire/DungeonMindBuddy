import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";

import { mockCatalog, mockLayout, mockPlanView, mockRollEvent, mockState } from "../test/fixtures";
import { SurfaceShell } from "./SurfaceShell";

describe("SurfaceShell", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });
  it("renders required Chat and Record from surface data", () => {
    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[mockRollEvent]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(screen.getByPlaceholderText(/Weather 7/)).toBeInTheDocument();
    expect(screen.getByText(/Resolved T-WX roll 7/)).toBeInTheDocument();
  });

  it("renders unsupported module placeholder for unknown catalog module", () => {
    const layoutWithFuture = {
      ...mockLayout,
      modules: mockLayout.modules.map((row) =>
        row.module_id === "future_panel" ? { ...row, enabled: true, collapsed: false } : row,
      ),
    };

    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={layoutWithFuture}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(screen.getAllByText(/Future panel/).length).toBeGreaterThan(0);
    expect(screen.getByText(/not implemented in this UI build/i)).toBeInTheDocument();
  });

  it("omits disabled roll_stack from the surface grid but keeps layout panel controls", () => {
    const layoutWithoutRoll = {
      ...mockLayout,
      modules: mockLayout.modules.map((row) =>
        row.module_id === "roll_stack" ? { ...row, enabled: false } : row,
      ),
    };

    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={layoutWithoutRoll}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(document.querySelector('.surface-grid [data-module-id="roll_stack"]')).toBeNull();
    expect(screen.queryByText("Storm weather")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Layout controls for Roll stack/i)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: /Hidden modules/i })).toBeInTheDocument();
  });

  it("removes roll_stack from the surface grid when disabled via embedded controls", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "putSurfaceLayout").mockImplementation(async (layout) => ({ layout }));

    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(document.querySelector('.surface-grid [data-module-id="roll_stack"]')).toBeTruthy();
    expect(screen.getByText("Storm weather")).toBeInTheDocument();

    const rollPanel = document.querySelector('.surface-grid [data-module-id="roll_stack"]')!;
    const checkbox = within(rollPanel as HTMLElement).getByRole("checkbox");
    await user.click(checkbox);
    await user.click(within(rollPanel as HTMLElement).getByRole("button", { name: /^Save$/i }));

    expect(document.querySelector('.surface-grid [data-module-id="roll_stack"]')).toBeNull();
    expect(screen.queryByText("Storm weather")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/Layout controls for Roll stack/i)).toBeInTheDocument();
  });

  it("renders timeline rows and typed ref chips as inert text", () => {
    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(screen.getAllByText("Timeline").length).toBeGreaterThan(0);
    expect(screen.getByText(/Travel Day 1 weather\/front beat/)).toBeInTheDocument();
    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /roll table · Travel weather table/i })).toBeNull();
  });

  it("does not remount ingestion when another pane expands", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/surface");

    const layout = {
      ...mockLayout,
      modules: mockLayout.modules.map((row) => {
        if (row.module_id === "ingestion") {
          return { ...row, enabled: true, collapsed: false, slot: "main" as const };
        }
        if (row.module_id === "record") {
          return { ...row, collapsed: true };
        }
        return row;
      }),
    };

    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={layout}
        state={mockState}
        events={[mockRollEvent]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    const navigation = await screen.findByRole("navigation", { name: "Ingest workspace navigation" });
    const ingestion = navigation.closest(".ingestion-module");
    expect(ingestion).not.toBeNull();
    const title = within(navigation).getByRole("textbox", { name: "Draft title (optional)" });
    await user.clear(title);
    await user.type(title, "Retained draft during pane expansion");
    expect(title).toHaveValue("Retained draft during pane expansion");

    const recordPanel = document.querySelector('.surface-grid [data-module-id="record"]')!;
    await user.click(within(recordPanel as HTMLElement).getByRole("button", { name: /^Expand$/i }));

    expect(screen.getByText(/Resolved T-WX roll 7/)).toBeInTheDocument();
    const navigationAfterExpand = await screen.findByRole("navigation", { name: "Ingest workspace navigation" });
    expect(navigationAfterExpand).toBe(navigation);
    expect(navigationAfterExpand.closest(".ingestion-module")).toBe(ingestion);
    expect(within(navigationAfterExpand).getByRole("textbox", { name: "Draft title (optional)" })).toBe(title);
    expect(title).toHaveValue("Retained draft during pane expansion");
  });

  it("selects timeline target via callback when enabled", async () => {
    const user = userEvent.setup();
    const onSelectTarget = vi.fn();
    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
        onSelectTarget={onSelectTarget}
      />,
    );

    await user.click(screen.getByRole("button", { name: /roll table · Travel weather table/i }));
    expect(onSelectTarget).toHaveBeenCalledWith(
      expect.objectContaining({
        target_type: "roll_table",
        target_id: "T-WX",
        label: "Travel weather table",
      }),
    );
  });
});
