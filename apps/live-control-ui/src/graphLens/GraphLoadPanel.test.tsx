import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PlanGraphLoadPanel } from "./GraphLoadPanel";
import { PlanGraphLensProvider } from "./WorldGraphLensContext";

function wrapper(
  loadSessions?: (campaignId: string) => Promise<number[]>,
  focusOptions?: [],
) {
  return function ProviderWrapper({ children }: { children: ReactNode }) {
    return createElement(
      PlanGraphLensProvider,
      {
        planCampaignId: "longmont-c2",
        ...(loadSessions ? { loadSessions: loadSessions as never } : {}),
        ...(focusOptions !== undefined ? { focusOptions } : {}),
      },
      children,
    );
  };
}





describe("PlanGraphLoadPanel", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/plan");
  });

  it("renders lens summary with node count when projection is ready", () => {
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(undefined, []) },
    );

    expect(screen.getByTestId("plan-graph-load-panel")).toBeInTheDocument();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · no session focus · 45 nodes · ready/i,
    );
  });

  it("shows loading status while projection loads", () => {
    render(
      <PlanGraphLoadPanel projectionState="loading" nodeCount={0} />,
      { wrapper: wrapper(undefined, []) },
    );

    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Loading/i);
  });

  it("toggles a campaign into the lens", async () => {
    const user = userEvent.setup();
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(undefined, []) },
    );

    const c1 = screen.getByRole("checkbox", { name: /Longmont C1/i });
    expect(c1).not.toBeChecked();
    await user.click(c1);
    expect(c1).toBeChecked();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Union · C1\+C2/i);
  });

  it("offers Focus session options from ingest bundles only", async () => {
    const loadSessions = vi.fn(async (campaignId: string) => {
      if (campaignId === "longmont-c2") return [24, 22, 1];
      if (campaignId === "longmont-c1") return [3];
      return [];
    });

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: "C2 · Session 22" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "C2 · Session 1" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "C2 · Session 40" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "C1 · Session 3" })).not.toBeInTheDocument();
    expect(loadSessions).toHaveBeenCalledWith("longmont-c2", expect.any(AbortSignal));
  });

  it("applies Focus session and updates the status line", async () => {
    const user = userEvent.setup();
    const loadSessions = vi.fn(async () => [24, 22]);

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Focus session"), "longmont-c2:24");
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · C2 · Session 24 · 45 nodes · ready/i,
    );
  });

  it("clears stale URL focus that is absent from ingest bundles", async () => {
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:40",
    );
    const loadSessions = vi.fn(async () => [24, 22, 1]);

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
        /C2 only · no session focus · 45 nodes · ready/i,
      );
    });
    expect(screen.queryByRole("option", { name: "C2 · Session 40" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Focus session")).toHaveValue("");
    expect(window.location.search).not.toMatch(/session=longmont-c2:40/);
    expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
  });

  it("keeps valid URL focus that is present in ingest bundles", async () => {
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:24",
    );
    const loadSessions = vi.fn(async () => [24, 22, 1]);

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
        /C2 only · C2 · Session 24 · 45 nodes · ready/i,
      );
    });
    expect(screen.getByLabelText("Focus session")).toHaveValue("longmont-c2:24");
    expect(window.location.search).toMatch(/session=longmont-c2%3A24|session=longmont-c2:24/);
  });

  it("keeps URL focus gated when the focused campaign bundle fails to load", async () => {
    const user = userEvent.setup();
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:40",
    );
    const loadSessions = vi.fn(async () => {
      throw new Error("bundle unavailable");
    });

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-focus-validation-unavailable")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · C2 · Session 40 · focus validation unavailable · gated/i,
    );
    expect(window.location.search).toMatch(/session=longmont-c2%3A40|session=longmont-c2:40/);
    expect(screen.getByLabelText("Focus session")).toHaveValue("longmont-c2:40");
    expect(screen.getByRole("option", { name: /C2 · Session 40 \(unverified\)/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Clear focus" }));
    await waitFor(() => {
      expect(screen.queryByTestId("plan-graph-focus-validation-unavailable")).not.toBeInTheDocument();
    });
    expect(screen.getByLabelText("Focus session")).toHaveValue("");
    expect(window.location.search).not.toMatch(/session=longmont-c2:40/);
  });

  it("retains successful campaign sessions when retrying another campaign", async () => {
    window.history.replaceState({}, "", "/plan?campaigns=longmont-c1,longmont-c2&session=longmont-c2:24");
    let c2Calls = 0;
    const loadSessions = vi.fn(async (campaignId: string) => {
      if (campaignId === "longmont-c1") return [3];
      if (++c2Calls === 1) throw new Error("bundle unavailable");
      return [24];
    });
    render(<PlanGraphLoadPanel projectionState="ready" nodeCount={45} />, { wrapper: wrapper(loadSessions) });
    await screen.findByRole("option", { name: "C1 · Session 3" });
    await userEvent.click(screen.getByRole("button", { name: "Retry validation" }));
    await screen.findByRole("option", { name: "C2 · Session 24" });
    expect(screen.getByRole("option", { name: "C1 · Session 3" })).toBeInTheDocument();
    expect(loadSessions.mock.calls.map(([campaignId]) => campaignId)).toEqual([
      "longmont-c1", "longmont-c2", "longmont-c2",
    ]);
  });

  it("retries focus validation after a bundle outage", async () => {
    const user = userEvent.setup();
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:24",
    );
    const loadSessions = vi
      .fn()
      .mockRejectedValueOnce(new Error("bundle unavailable"))
      .mockResolvedValueOnce([24, 22]);

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-focus-validation-unavailable")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Retry validation" }));
    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
        /C2 only · C2 · Session 24 · 45 nodes · ready/i,
      );
    });
    expect(screen.queryByTestId("plan-graph-focus-validation-unavailable")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Focus session")).toHaveValue("longmont-c2:24");
    expect(loadSessions).toHaveBeenCalledTimes(2);
  });

  it("accepts unverified focus via intentional operator override", async () => {
    const user = userEvent.setup();
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:40",
    );
    const loadSessions = vi.fn(async () => {
      throw new Error("bundle unavailable");
    });

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} />,
      { wrapper: wrapper(loadSessions) },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-focus-validation-unavailable")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Use focus anyway" }));
    await waitFor(() => {
      expect(screen.queryByTestId("plan-graph-focus-validation-unavailable")).not.toBeInTheDocument();
    });
    expect(window.location.search).toMatch(/session=longmont-c2%3A40|session=longmont-c2:40/);
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · C2 · Session 40 · 45 nodes · ready/i,
    );
    expect(screen.getByLabelText("Focus session")).toHaveValue("longmont-c2:40");
    expect(
      screen.getByRole("option", { name: /C2 · Session 40 \(accepted unverified\)/i }),
    ).toBeInTheDocument();
  });

  it("shows fail-closed status when graph lens context is missing", () => {
    render(<PlanGraphLoadPanel projectionState="ready" nodeCount={0} />);

    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /Graph lens unavailable/i,
    );
  });
});
