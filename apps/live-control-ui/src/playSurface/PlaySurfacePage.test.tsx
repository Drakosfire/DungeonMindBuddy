import { render, screen, waitFor } from "@testing-library/react";
import { createElement, type ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { WorldGraphLensProvider, WorldGraphLensProjectionProvider } from "../graphLens";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { setAdmittedCampaignWorldOverlay } from "../worldGraph/admittedCampaignWorldOverlay";
import { PlaySurfacePage } from "./PlaySurfacePage";
import { resetPlayPrepAssetsForTests } from "./playPrepHost";

const prepApi = {
  initNav: vi.fn(),
  wireRepoLinks: vi.fn(),
  initMarkdownEmbeds: vi.fn(),
  initRollTableCorpusIndex: vi.fn(),
  initItemWorkspaceIndex: vi.fn(),
  initStatblockCorpusIndex: vi.fn(),
  initCombatTracker: vi.fn(),
};

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

function seedScopedCss(): void {
  if (document.getElementById("play-prep-scoped-css")) return;
  const style = document.createElement("style");
  style.id = "play-prep-scoped-css";
  document.head.appendChild(style);
}

function mockPrepHtmlFetch(): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/prep/combat")) {
        return new Response(
          `<!doctype html><html><body>
            <div class="wrap combat-wrap" id="combat-tracker"><h1>Combat</h1><table><tbody id="combat-rows"></tbody></table></div>
            <div class="combat-floating-controls"></div>
          </body></html>`,
          { status: 200, headers: { "Content-Type": "text/html" } },
        );
      }
      if (url.includes("/prep/roll")) {
        return new Response(
          `<!doctype html><html><body><div class="wrap"><h1>Roll</h1><div id="rolltable-corpus-index"></div></div></body></html>`,
          { status: 200, headers: { "Content-Type": "text/html" } },
        );
      }
      if (url.includes("/prep/statblocks")) {
        return new Response(
          `<!doctype html><html><body class="statblocks-page"><div class="wrap"><h1>Statblocks</h1><div id="statblock-corpus-index"></div></div></body></html>`,
          { status: 200, headers: { "Content-Type": "text/html" } },
        );
      }
      return new Response("not found", { status: 404 });
    }),
  );
}

describe("PlaySurfacePage", () => {
  beforeEach(() => {
    setAdmittedCampaignWorldOverlay([
      {
        campaign_id: "of-conks-cons",
        world_id: "of-conks-cons",
        label: "Of Conks & Cons",
        source: "seed",
      },
    ]);
    window.history.replaceState({}, "", "/play/combat?campaigns=of-conks-cons");
    Object.values(prepApi).forEach((fn) => fn.mockReset());
    window.MirewardPrep = prepApi;
    resetPlayPrepAssetsForTests();
    seedScopedCss();
    mockPrepHtmlFetch();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    delete window.MirewardPrep;
    resetPlayPrepAssetsForTests();
    document.getElementById("play-prep-scoped-css")?.remove();
    document.getElementById("play-prep-themes-css")?.remove();
  });

  it("renders AppChrome Play nav, tool tabs, and inlines the prep panel (no iframe)", async () => {
    render(createElement(PlaySurfacePage, { initialPanel: "combat" }), { wrapper });

    expect(screen.getByRole("navigation", { name: /command board navigation/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Play" })).toHaveClass("active");
    expect(screen.getByRole("navigation", { name: /play tools/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Combat" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByTestId("app-chrome-world-graph")).toBeInTheDocument();
    expect(screen.queryByTestId("play-surface-frame")).not.toBeInTheDocument();

    const host = screen.getByTestId("play-surface-host");
    expect(host.getAttribute("data-play-embed-src")).toContain("/prep/combat?");
    expect(host.getAttribute("data-play-embed-src")).toContain("embed=1");
    expect(host.getAttribute("data-play-embed-src")).toContain("campaigns=of-conks-cons");

    await waitFor(() => {
      expect(host.querySelector("h1")?.textContent).toBe("Combat");
    });
    expect(prepApi.initCombatTracker).toHaveBeenCalled();
  });

  it("switches panels in-place without dropping World Graph chrome", async () => {
    window.history.replaceState({}, "", "/play/statblocks?campaigns=of-conks-cons");
    const user = await import("@testing-library/user-event").then((m) => m.default.setup());
    render(createElement(PlaySurfacePage, { initialPanel: "statblocks" }), { wrapper });

    expect(screen.getByTestId("play-surface")).toHaveAttribute("data-play-panel", "statblocks");
    await waitFor(() => {
      expect(screen.getByTestId("play-surface-host").querySelector("h1")?.textContent).toBe("Statblocks");
    });

    await user.click(screen.getByRole("link", { name: "Roll" }));
    expect(window.location.pathname).toBe("/play/roll");
    expect(screen.getByTestId("play-surface")).toHaveAttribute("data-play-panel", "roll");
    expect(screen.getByTestId("play-surface-host").getAttribute("data-play-embed-src")).toContain(
      "/prep/roll?",
    );
    expect(screen.getByTestId("app-chrome-world-graph")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("play-surface-host").querySelector("h1")?.textContent).toBe("Roll");
    });

    await user.click(screen.getByRole("link", { name: "Statblocks" }));
    expect(window.location.pathname).toBe("/play/statblocks");
    expect(screen.getByTestId("play-surface")).toHaveAttribute("data-play-panel", "statblocks");
    expect(screen.getByTestId("play-surface-host").getAttribute("data-play-embed-src")).toContain(
      "/prep/statblocks?",
    );
    expect(screen.getByRole("link", { name: "Play" })).toHaveClass("active");
  });
});
