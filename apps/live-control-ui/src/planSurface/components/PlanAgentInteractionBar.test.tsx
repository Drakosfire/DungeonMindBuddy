import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createElement, useEffect, type ReactNode } from "react";

import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../../agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "../../agentInteraction/AgentInteractionChrome";
import { buildPlanSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
import { fixturePlanSessionDescriptor, FIXTURE_DOC_ID } from "../config/planSessionDescriptor";
import { PlanGraphLensProvider } from "../PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import { PlanAgentInteractionBar } from "./PlanAgentInteractionBar";
import { PlanGraphLoadPanel } from "./PlanGraphLoadPanel";
import type { PlanViewProjection } from "../../api/types";
import * as liveApi from "../../api/liveApi";

const planView = {
  campaign_id: "longmont-c2",
  session: 22,
} as PlanViewProjection;

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: null });

function PlanLeasePublisher({ children }: { children: ReactNode }) {
  const { publishProjectionSurface } = useAgentInteraction();
  useEffect(() => {
    return publishProjectionSurface({
      identity: buildPlanSurfaceIdentity({
        documentId: FIXTURE_DOC_ID,
        campaignId: "longmont-c2",
        liveSession: 22,
        memorySession: null,
      }),
      config: {
        id: "plan",
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "C2 Session 27 Prep — ambient must not ship",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: { themeId: "mireward" },
      },
    });
  }, [publishProjectionSurface]);
  return createElement("div", null, children);
}

function wrapper({ children }: { children: ReactNode }) {
  return createElement(
    AgentInteractionProvider,
    null,
    createElement(
      AskPluginSlotProvider,
      null,
      createElement(
        PlanGraphLensProvider,
        { planCampaignId: sessionDescriptor.campaignId },
        createElement(
          PlanGraphReferenceResolverProvider,
          { sessionDescriptor },
          createElement(AgentInteractionChrome),
          createElement(PlanLeasePublisher, null, children),
        ),
      ),
    ),
  );
}

describe("PlanAgentInteractionBar graph lens", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan");
  });

  it("asks with campaign scope when only C1 is selected", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/plan?campaigns=longmont-c1");
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c1",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue({
      schema: "dmb_ingestion_source_bundle_v1",
      units: [],
      artifacts: [],
      diagnostics: [],
      coverage: {},
    } as never);

    const askCorpus = vi.fn().mockResolvedValue({
      answer: "C1 only answer",
      mode: "hermes_graph_agent",
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: { backend: "hermes" },
      citations: [],
    });

    render(
      createElement(PlanAgentInteractionBar, {
        planView,
        sessionDescriptor,
        askCorpus,
        loadBundle: liveApi.getSourceBundle,
      }),
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText(/C1 only · no session focus/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Tell me about campaign 1");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    await waitFor(() => expect(askCorpus).toHaveBeenCalled());
    const [, campaignId, session, , options] = askCorpus.mock.calls[0];
    // Outer live-query campaign/session stay on the Plan packet; lens is nested only.
    expect(campaignId).toBe("longmont-c2");
    expect(session).toBe(22);
    expect(options.worldGraphContext).toMatchObject({
      campaign_id: "longmont-c1",
      scope_mode: "campaign",
    });
    expect(options.surfaceContext).toEqual({
      schema: "dmb_agent_surface_context_request_v1",
      surface_id: "plan",
      campaign_id: "longmont-c2",
      document_id: FIXTURE_DOC_ID,
      session_number: 22,
      pointers: [],
    });
    expect(JSON.stringify(options.surfaceContext)).not.toContain("ambient must not ship");
    expect(JSON.stringify(options.surfaceContext)).not.toContain("C2 Session 27 Prep");

    await waitFor(() => {
      expect(screen.getByText("C1 only answer")).toBeInTheDocument();
    });
    expect(document.querySelector(".plan-agent-chat-row-user")).toBeTruthy();
    expect(document.querySelector(".plan-agent-chat-row-assistant")).toBeTruthy();
    expect(document.querySelector(".plan-agent-chat-bubble-user")).toBeTruthy();
    expect(document.querySelector(".plan-agent-chat-bubble-assistant")).toBeTruthy();
    // R10b chrome owns the open shell; Plan Ask pane portals into the host.
    expect(screen.getByLabelText("DungeonBuddy agent").className).toContain("open");
    expect(screen.getByLabelText("Ask DungeonBuddy").className).toContain("plan-agent-pane");
  });

  it("disables Ask and shows warning when no campaigns are selected", async () => {
    const user = userEvent.setup();
    render(
      createElement(
        "div",
        null,
        createElement(PlanGraphLoadPanel, {
          projectionState: "ready",
          nodeCount: 0,
        }),
        createElement(PlanAgentInteractionBar, {
          planView,
          sessionDescriptor,
          askCorpus: vi.fn(),
          loadBundle: liveApi.getSourceBundle,
        }),
      ),
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: "Open" }));
    const c2 = screen.getByRole("checkbox", { name: /Longmont C2/i });
    await user.click(c2);

    expect(screen.getByText("Select at least one campaign.")).toBeInTheDocument();
    expect(screen.getByText("Select at least one campaign on Plan Board.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask DungeonBuddy" })).toBeDisabled();
  });

  it("shows active-campaign disclosure label by default (not world union)", async () => {
    const user = userEvent.setup();
    render(
      createElement(PlanAgentInteractionBar, {
        planView,
        sessionDescriptor,
        askCorpus: vi.fn(),
        loadBundle: liveApi.getSourceBundle,
      }),
      { wrapper },
    );

    await user.click(screen.getByRole("button", { name: "Open" }));
    expect(screen.getByText(/C2 only · no session focus/)).toBeInTheDocument();
    expect(screen.queryByText(/Union · C1\+C2/)).not.toBeInTheDocument();
  });
});
