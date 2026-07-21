import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it } from "vitest";

import { PlanGraphLensProvider } from "../PlanGraphLensContext";
import { PlanGraphLoadPanel } from "./PlanGraphLoadPanel";

function wrapper({ children }: { children: ReactNode }) {
  return createElement(PlanGraphLensProvider, { planCampaignId: "longmont-c2" }, children);
}

describe("PlanGraphLoadPanel", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/plan");
  });

  it("renders lens summary with node count when projection is ready", () => {
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper },
    );

    expect(screen.getByTestId("plan-graph-load-panel")).toBeInTheDocument();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · no session focus · 45 nodes · ready/i,
    );
  });

  it("shows loading status while projection loads", () => {
    render(
      <PlanGraphLoadPanel projectionState="loading" nodeCount={0} />,
      { wrapper },
    );

    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Loading/i);
  });

  it("toggles a campaign into the lens", async () => {
    const user = userEvent.setup();
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper },
    );

    const c1 = screen.getByRole("checkbox", { name: /Longmont C1/i });
    expect(c1).not.toBeChecked();
    await user.click(c1);
    expect(c1).toBeChecked();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Union · C1\+C2/i);
  });

  it("offers default Focus session options for selected campaigns", () => {
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper },
    );

    const focus = screen.getByLabelText("Focus session");
    expect(focus).toBeEnabled();
    expect(screen.getByRole("option", { name: "C2 · Session 1" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "C2 · Session 40" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "C1 · Session 1" })).not.toBeInTheDocument();
  });

  it("applies Focus session and updates the status line", async () => {
    const user = userEvent.setup();
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper },
    );

    await user.selectOptions(screen.getByLabelText("Focus session"), "longmont-c2:24");
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · C2 · Session 24 · 45 nodes · ready/i,
    );
  });
});
