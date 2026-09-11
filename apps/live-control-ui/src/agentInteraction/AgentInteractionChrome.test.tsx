import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMemo } from "react";
import { describe, expect, it } from "vitest";

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
});
