import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { mockCatalog, mockLayout, mockRollEvent, mockState } from "../test/fixtures";
import { SurfaceShell } from "./SurfaceShell";

describe("SurfaceShell", () => {
  it("renders required Chat and Record from surface data", () => {
    render(
      <SurfaceShell
        catalog={mockCatalog}
        layout={mockLayout}
        state={mockState}
        events={[mockRollEvent]}
        jobs={[]}
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
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );

    expect(screen.getAllByText(/Future panel/).length).toBeGreaterThan(0);
    expect(screen.getByText(/not implemented in this UI build/i)).toBeInTheDocument();
  });
});
