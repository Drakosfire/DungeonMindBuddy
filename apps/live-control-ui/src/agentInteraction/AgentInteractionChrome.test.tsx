import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useMemo } from "react";
import { describe, expect, it } from "vitest";

import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { AskPluginSlotProvider } from "./AskPluginSlot";
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
  it("shows cross-surface bar and honest empty Ask without a Plan plugin", async () => {
    const user = userEvent.setup();
    render(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <PublishBuildContext />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );

    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute(
      "data-ask-available",
      "false",
    );
    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute(
      "data-surface-id",
      "build",
    );
    expect(screen.getByTestId("agent-interaction-bar")).toHaveTextContent(/Ask DungeonBuddy · Build/i);
    expect(screen.getByTestId("agent-interaction-bar")).toHaveTextContent(
      /Build worldbuilding document · Ask unavailable here/i,
    );

    await user.click(screen.getByTestId("agent-interaction-open"));
    expect(screen.getByText(/Ask is unavailable for the current surface/i)).toBeInTheDocument();
    expect(screen.getByTestId("agent-interaction-ask-empty")).toHaveTextContent(
      /No surface has registered an Ask plugin/i,
    );
    expect(screen.getByTestId("agent-interaction-current-surface")).toHaveTextContent(
      /Current surface: Build/i,
    );
  });

  it("labels the bar with published Ingest surface identity", () => {
    render(
      <AgentInteractionProvider>
        <AskPluginSlotProvider>
          <PublishIngestContext />
          <AgentInteractionChrome />
        </AskPluginSlotProvider>
      </AgentInteractionProvider>,
    );

    expect(screen.getByTestId("agent-interaction-chrome")).toHaveAttribute(
      "data-surface-id",
      "ingest",
    );
    expect(screen.getByTestId("agent-interaction-bar")).toHaveTextContent(/Ask DungeonBuddy · Ingest/i);
    expect(screen.getByTestId("agent-interaction-bar")).toHaveTextContent(/Graph Review · longmont-c2/i);
  });
});
