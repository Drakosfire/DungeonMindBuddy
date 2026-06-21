import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockPlanView } from "../test/fixtures";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

describe("PlanSurfaceShell", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nav, toolbar, edit bar, and canvas regions", () => {
    render(<PlanSurfaceShell planView={mockPlanView} />);

    expect(screen.getByRole("navigation", { name: "Plan surface navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Toolbox tools" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Edit bar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(screen.getByText(/preparing Session 23 · ingesting Session 21/i)).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Plan toolbox" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live Play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );
    expect(screen.getByText(/Document controls for the selected planning canvas/i)).toBeInTheDocument();
  });

  it("applies spike theme tokens at the surface root", () => {
    const { container } = render(<PlanSurfaceShell planView={mockPlanView} />);
    const root = container.querySelector(".plan-surface-root");
    expect(root).toHaveAttribute("data-md-theme", "mireward-runbook");
    expect(root).toHaveStyle({ "--accent": "#7aa2f7" });
  });

  it("opens ingestion projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("complementary", { name: /Ingest Recap projection/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Raw Recap Ingestion/i })).toBeInTheDocument();
  });

  it("opens statblock projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Statblock" }));

    expect(screen.getByRole("complementary", { name: /Statblock projection/i })).toBeInTheDocument();
  });

  it("projects reference chip resolution through the shared container", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        locations: [{
          index_id: "north-reach-gate",
          title: "North Reach Gate",
          corpus_display_path: "corpus/locations/north_reach_gate.md",
        }],
      }),
    } as Response);

    render(<PlanSurfaceShell planView={mockPlanView} />);

    const canvas = screen.getByTestId("plan-surface-canvas-editor");
    const chip = canvas.querySelector(".md-ref-chip") as HTMLElement;
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: /North Reach Gate projection/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/Resolved from live location index/i)).toBeInTheDocument();
  });
});
