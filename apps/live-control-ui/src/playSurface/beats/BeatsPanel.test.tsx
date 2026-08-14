import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../../agentInteraction/AskPluginSlot";
import { WorldGraphLensProvider, WorldGraphLensProjectionProvider } from "../../graphLens";
import { SurfaceContextProvider } from "../../surfaceInteraction/contextHost";
import { BeatsPanel } from "./BeatsPanel";

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
          createElement(SurfaceContextProvider, null, children),
        ),
      ),
    ),
  );
}

function mockRunStateApi(initialNotes: Record<string, string> = {}) {
  let stored = {
    schema_version: "dmb_play_run_state_v1" as const,
    run_id: "of-conks-cons--hempholm",
    campaign_id: "of-conks-cons",
    adventure_id: "hempholm",
    updated_at: "2026-08-13T00:00:00Z",
    current_scene_id: "village-sandbox",
    branch: { hook: "hill" as const, aftermath: null },
    resolved_beat_ids: [] as string[],
    scene_notes: initialNotes,
  };

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (!url.includes("/api/live/play-run-state/")) {
      return new Response("not found", { status: 404 });
    }
    if ((init?.method ?? "GET").toUpperCase() === "PUT") {
      stored = JSON.parse(String(init?.body ?? "{}"));
      stored.updated_at = "2026-08-13T01:00:00Z";
      return new Response(JSON.stringify(stored), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response(JSON.stringify(stored), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return { fetchMock, getStored: () => stored };
}

describe("BeatsPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  it("loads scene, expands Maglubiyet beat detail, and persists notes + resolved", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const api = mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("beats-panel")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: /Village sandbox/i })).toBeInTheDocument();

    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Saladin's wagon/i }));
    expect(screen.getByTestId("beats-detail")).toBeInTheDocument();
    expect(within(screen.getByTestId("beats-detail")).getByRole("button", { name: /Maglubiyet/i })).toBeInTheDocument();

    await user.click(screen.getByRole("checkbox", { name: /Resolved: Saladin's wagon/i }));
    await user.clear(screen.getByTestId("beats-scene-notes"));
    await user.type(screen.getByTestId("beats-scene-notes"), "Dogfood note");

    await vi.advanceTimersByTimeAsync(500);
    await waitFor(() => {
      expect(api.getStored().resolved_beat_ids).toContain("saladin-wagon");
      expect(api.getStored().scene_notes["village-sandbox"]).toContain("Dogfood note");
    });
  });

  it("surfaces firefighting RULES from aftermath-fire beat", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });
    await waitFor(() => expect(screen.getByTestId("beats-panel")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /^Surface tree fight$/i }));
    const chooser = screen.getByLabelText(/Aftermath choice/i);
    await user.click(within(chooser).getByRole("button", { name: /^Firefighting$/i }));
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: /Hempholm caught fire/i })).toBeInTheDocument();
    });
    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Firefighting/i }));
    expect(screen.getByTestId("beats-detail-rules")).toHaveTextContent(/DC 12/i);
  });

  it("opens Marrow chamber RA and resin RULES without Build", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });
    await waitFor(() => expect(screen.getByTestId("beats-panel")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: /^The Marrow$/i }));
    expect(screen.getByText(/sickly green light/i)).toBeInTheDocument();
    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Resin harvest/i }));
    expect(screen.getByTestId("beats-detail-rules")).toHaveTextContent(/200 gp/i);
    expect(
      within(screen.getByTestId("beats-detail")).getByRole("button", { name: /The Marrow/i }),
    ).toBeInTheDocument();
  });

  it("renders Jove plea run card with multi labeled read-alouds", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockRunStateApi();
    render(createElement(BeatsPanel), { wrapper });
    await waitFor(() => expect(screen.getByTestId("beats-panel")).toBeInTheDocument());

    const rail = screen.getByLabelText(/^Beats$/i);
    await user.click(within(rail).getByRole("button", { name: /Jove plea/i }));
    const detail = screen.getByTestId("beats-detail");
    expect(within(detail).getByTestId("beats-detail-at-table")).toHaveTextContent(/Area 4/i);
    const ras = within(detail).getAllByTestId("beats-detail-read-aloud");
    expect(ras.length).toBeGreaterThanOrEqual(3);
    expect(ras.some((el) => /Mark Jove/i.test(el.textContent ?? ""))).toBe(true);
    expect(ras.some((el) => /Torbin Jove/i.test(el.textContent ?? ""))).toBe(true);
    expect(within(detail).getByRole("button", { name: /^Mark Jove$/i })).toBeInTheDocument();
  });

  it("selects a beat from ?beat= on hydrate", async () => {
    mockRunStateApi();
    render(createElement(BeatsPanel, { search: "?beat=shacks-arrival" }), { wrapper });
    await waitFor(() => expect(screen.getByTestId("beats-panel")).toBeInTheDocument());
    await waitFor(() => {
      expect(screen.getByTestId("beats-detail")).toBeInTheDocument();
    });
    expect(screen.getByTestId("beats-detail")).toHaveTextContent(/Largest building|Shacks/i);
  });
});
