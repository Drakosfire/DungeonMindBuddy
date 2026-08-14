import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../../agentInteraction/AskPluginSlot";
import { WorldGraphLensProvider, WorldGraphLensProjectionProvider } from "../../graphLens";
import { LegacyProjectionHostAdapter } from "../../planSurface/projection/LegacyProjectionHostAdapter";
import { SurfaceContextProvider } from "../../surfaceInteraction/contextHost";
import { BeatsPanel } from "../beats/BeatsPanel";
import { PlayReferenceCapability } from "./PlayReferenceCapability";

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    AgentInteractionProvider,
    null,
    createElement(
      AskPluginSlotProvider,
      null,
      createElement(
        WorldGraphLensProvider,
        { planCampaignId: "of-conks-cons" },
        createElement(
          WorldGraphLensProjectionProvider,
          { defaultCampaignId: "of-conks-cons" },
          createElement(
            SurfaceContextProvider,
            null,
            createElement(PlayReferenceCapability, { panelId: "beats" }, children),
            createElement(LegacyProjectionHostAdapter),
          ),
        ),
      ),
    ),
  );
}

function mockRunStateApi() {
  const stored = {
    schema_version: "dmb_play_run_state_v1" as const,
    run_id: "of-conks-cons--hempholm",
    campaign_id: "of-conks-cons",
    adventure_id: "hempholm",
    updated_at: "2026-08-13T00:00:00Z",
    current_scene_id: "village-sandbox",
    branch: { hook: "hill" as const, aftermath: null },
    resolved_beat_ids: [] as string[],
    scene_notes: {},
  };

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (!url.includes("/api/live/play-run-state/")) {
        return new Response("not found", { status: 404 });
      }
      if ((init?.method ?? "GET").toUpperCase() === "PUT") {
        return new Response(JSON.stringify(stored), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify(stored), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
}

describe("PlayReferenceCapability", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it("opens a ProjectionHost sheet when a Beats chip is clicked", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("beats-panel")).toBeInTheDocument();
    });

    const scene = screen.getByLabelText(/^Scene$/i);
    await user.click(within(scene).getByRole("button", { name: /^The Shacks$/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/The Shacks projection/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("play-object-sheet")).toHaveTextContent(/Largest building/i);
  });

  it("opens Mark Jove play sheet with authored body from Beats chip", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("beats-panel")).toBeInTheDocument();
    });

    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Jove plea/i }));
    await waitFor(() => {
      expect(screen.getByTestId("beats-detail")).toBeInTheDocument();
    });

    await user.click(
      within(screen.getByTestId("beats-detail")).getByRole("button", { name: /^Mark Jove$/i }),
    );

    await waitFor(() => {
      expect(screen.getByLabelText(/Mark Jove projection/i)).toBeInTheDocument();
    });

    const sheet = await screen.findByTestId("play-object-sheet");
    expect(sheet).toHaveTextContent(/Father at the house/i);
    expect(sheet).toHaveTextContent(/bewitched/i);
  });

  it("opens Mark Jove from Connected now on another Play sheet", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("beats-panel")).toBeInTheDocument();
    });

    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Jove plea/i }));
    await waitFor(() => {
      expect(screen.getByTestId("beats-detail")).toBeInTheDocument();
    });

    await user.click(
      within(screen.getByTestId("beats-detail")).getByRole("button", { name: /^Torbin Jove$/i }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("play-object-sheet")).toHaveTextContent(/Mark’s son/i);
    });

    await user.click(screen.getByRole("button", { name: /^Open Mark Jove$/i }));

    await waitFor(() => {
      expect(screen.getByTestId("play-object-sheet")).toHaveTextContent(/Father at the house/i);
    });
    expect(screen.queryByTestId("play-reference-unresolved-card")).not.toBeInTheDocument();
  });

  it("opens The Shacks play sheet from ?beat=&node= deep-link", async () => {
    mockRunStateApi();
    render(
      createElement(BeatsPanel, {
        search: "?beat=shacks-arrival&node=location:the-shacks",
      }),
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByTestId("beats-panel")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("play-object-sheet")).toHaveTextContent(/Largest building|noggin-shaped nose/i);
    });
    expect(screen.getByTestId("beats-detail")).toBeInTheDocument();
  });
});
