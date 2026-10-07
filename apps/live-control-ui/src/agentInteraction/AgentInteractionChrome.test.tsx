import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMemo, type CSSProperties } from "react";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { URL as NodeURL } from "node:url";

import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { AskPluginSlotProvider, useRegisterAskPluginPresence } from "./AskPluginSlot";
import { usePublishAgentSurfaceContext } from "./usePublishAgentSurfaceContext";

function PublishBuildContext() {
  const context = useMemo(
    () => ({
      surfaceId: "build",
      label: "Build lore",
      campaignId: "longmont-c2",
      documentId: "doc-1",
      sessionNumber: 22,
      ambientSummary: "Build worldbuilding document",
      sourceEnvelope: null,
    }),
    [],
  );
  usePublishAgentSurfaceContext(context);
  return null;
}

function PublishIngestContext() {
  const context = useMemo(
    () => ({
      surfaceId: "ingest",
      label: "Memory Ingest",
      campaignId: "longmont-c2",
      documentId: null,
      sessionNumber: 22,
      ambientSummary: "Graph Review · longmont-c2 · session 22",
      sourceEnvelope: null,
    }),
    [],
  );
  usePublishAgentSurfaceContext(context);
  return null;
}

function PublishPlanContext() {
  const context = useMemo(
    () => ({
      surfaceId: "plan",
      label: "World Plan",
      campaignId: "world-plan:world-1",
      documentId: "plan-1",
      sessionNumber: null,
      ambientSummary: "Saved World Plan",
      sourceEnvelope: null,
    }),
    [],
  );
  usePublishAgentSurfaceContext(context);
  return null;
}

describe("AgentInteractionChrome", () => {
  function RegisterAsk({ present = true }: { present?: boolean }) {
    useRegisterAskPluginPresence(present);
    return null;
  }

  it("renders no Agent chrome or Open action without a registered Ask plugin", () => {
    render(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <PublishBuildContext />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );

    expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Plan" })).not.toBeInTheDocument();
  });

  it("derives presence from plugin registration rather than the published surface", () => {
    render(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <PublishIngestContext />
          <RegisterAsk />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );

    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute(
      "data-surface-id",
      "ingest",
    );
    const open = screen.getByRole("button", { name: "Open" });
    expect(open).toHaveAttribute("title");
    expect(open.getAttribute("title")).toMatch(/Ask DungeonBuddy · Ingest · New thread/i);
    expect(open.getAttribute("title")).toMatch(/Graph Review · longmont-c2/i);
    expect(open.querySelector("img")).toHaveAttribute("src", expect.stringContaining("dungeonbuddy-agent.png"));
    expect(screen.getByTestId("agent-interaction-bar")).toHaveTextContent("");
  });

  it("preserves pane state while plugin presence temporarily disappears", async () => {
    const user = userEvent.setup();
    const view = render(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <RegisterAsk />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );

    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveClass("open");
    expect(screen.getByRole("button", { name: "Close chat" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close chat" }));
    expect(screen.getByTestId("agent-interaction-chrome")).not.toHaveClass("open");
    await user.click(screen.getByRole("button", { name: "Open" }));

    view.rerender(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <RegisterAsk present={false} />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );
    expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();

    view.rerender(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <RegisterAsk />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveClass("open");
  });

  it("keeps the Plan conversation host mounted through close and reopen and exposes keyboard resize", async () => {
    const user = userEvent.setup();
    const originalInnerWidth = window.innerWidth;
    const style = document.createElement("style");
    style.textContent = readFileSync(new NodeURL("../styles.css", import.meta.url), "utf8")
      .match(/\.app-shell--edit-dock:has\(\.plan-agent-shell\.agent-interaction-shell--plan\.open\)\s+\.app-wrap\s+:is\(\.plan-surface-root,\s*\.world-owned-plan\)\s*\{[^}]*\}/s)?.[0] ?? "";
    document.head.appendChild(style);
    const renderPlanChrome = (present = true, surfaceId: "plan" | "build" = "plan") => (
      <div
        className="app-shell--edit-dock"
        style={{ "--agent-plan-panel-width": "512px" } as CSSProperties}
      >
        <div className="app-wrap">
          <div className="plan-surface-root" data-testid="plan-surface-content" />
          <AgentInteractionProvider>
            <AskPluginSlotProvider>
              {surfaceId === "plan" ? <PublishPlanContext /> : <PublishBuildContext />}
              <RegisterAsk present={present} />
              <AgentInteractionChrome />
            </AskPluginSlotProvider>
          </AgentInteractionProvider>
        </div>
      </div>
    );
    const view = render(renderPlanChrome());

    try {
      const appShell = screen.getByTestId("agent-interaction-chrome").closest(".app-shell--edit-dock") as HTMLElement;
      const planContent = screen.getByTestId("plan-surface-content");
      const host = screen.getByTestId("agent-interaction-ask-host");
      expect(host).toHaveAttribute("hidden");
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("512px");
      await user.click(screen.getByRole("button", { name: "Open" }));
      expect(host).not.toHaveAttribute("hidden");
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("440px");
      expect(getComputedStyle(planContent).width).toContain("var(--agent-plan-panel-width");

      const panelResizer = screen.getByRole("separator", { name: "Resize Buddy panel" });
      const startingWidth = Number(panelResizer.getAttribute("aria-valuenow"));
      panelResizer.focus();
      await user.keyboard("{ArrowLeft}");
      expect(Number(panelResizer.getAttribute("aria-valuenow"))).toBe(startingWidth + 24);
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("464px");

      Object.defineProperty(window, "innerWidth", { configurable: true, value: 500 });
      fireEvent.resize(window);
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("360px");
      Object.defineProperty(window, "innerWidth", { configurable: true, value: originalInnerWidth });
      fireEvent.resize(window);
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("464px");

      await user.click(screen.getByRole("button", { name: "Close chat" }));
      expect(screen.getByTestId("agent-interaction-ask-host")).toBe(host);
      expect(host).toHaveAttribute("hidden");
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("512px");
      await user.click(screen.getByRole("button", { name: "Open" }));
      expect(screen.getByTestId("agent-interaction-ask-host")).toBe(host);
      expect(host).not.toHaveAttribute("hidden");
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("464px");

      view.rerender(renderPlanChrome(false));
      expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("512px");
      view.rerender(renderPlanChrome(true));
      await waitFor(() => expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("464px"));

      view.rerender(renderPlanChrome(true, "build"));
      await waitFor(() => expect(screen.getByTestId("agent-interaction-chrome")).not.toHaveClass("agent-interaction-shell--plan"));
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("512px");
      view.rerender(renderPlanChrome(true, "plan"));
      await waitFor(() => expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("464px"));
      view.unmount();
      expect(appShell.style.getPropertyValue("--agent-plan-panel-width")).toBe("512px");
    } finally {
      view.unmount();
      style.remove();
      Object.defineProperty(window, "innerWidth", { configurable: true, value: originalInnerWidth });
    }
  });
});
