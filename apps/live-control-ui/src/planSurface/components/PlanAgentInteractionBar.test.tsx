import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createElement, type ReactNode } from "react";

import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../../agentInteraction/AskPluginSlot";
import { AgentInteractionChrome } from "../../agentInteraction/AgentInteractionChrome";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { PlanGraphLensProvider } from "../PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import { PlanAgentInteractionBar } from "./PlanAgentInteractionBar";
import { PlanGraphLoadPanel } from "./PlanGraphLoadPanel";
import type { PlanViewProjection } from "../../api/types";
import * as liveApi from "../../api/liveApi";
import { setAdmittedCampaignWorldOverlay } from "../../worldGraph/admittedCampaignWorldOverlay";

const planView = {
  campaign_id: "longmont-c2",
  session: 22,
} as PlanViewProjection;

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: null });

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
          children,
        ),
      ),
    ),
  );
}

describe("PlanAgentInteractionBar graph lens", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/plan");
    setAdmittedCampaignWorldOverlay([]);
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

  it("keeps outer live-packet identity when planning campaign is Of Conks", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/plan?campaigns=of-conks-cons");
    setAdmittedCampaignWorldOverlay([
      { campaign_id: "of-conks-cons", world_id: "of-conks-cons", source: "seed" },
    ]);
    const ofConksDescriptor = fixturePlanSessionDescriptor({
      memorySession: null,
      campaignId: "of-conks-cons",
      campaignLabel: "Of Conks & Cons",
    });
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "of-conks-cons",
        campaignId: "of-conks-cons",
        revisionId: "rev-of-conks",
        headRevisionId: "rev-of-conks",
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
      answer: "Tree has metal leaves.",
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
      createElement(
        AgentInteractionProvider,
        null,
        createElement(
          AskPluginSlotProvider,
          null,
          createElement(
            PlanGraphLensProvider,
            { planCampaignId: ofConksDescriptor.campaignId },
            createElement(
              PlanGraphReferenceResolverProvider,
              { sessionDescriptor: ofConksDescriptor },
              createElement(AgentInteractionChrome),
              createElement(PlanAgentInteractionBar, {
                planView,
                sessionDescriptor: ofConksDescriptor,
                askCorpus,
                loadBundle: liveApi.getSourceBundle,
              }),
            ),
          ),
        ),
      ),
    );

    await user.click(screen.getByRole("button", { name: "Open" }));
    await user.type(screen.getByLabelText("Question"), "Metal leaves on the tree?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    await waitFor(() => expect(askCorpus).toHaveBeenCalled());
    const [, campaignId, session, , options] = askCorpus.mock.calls[0];
    expect(campaignId).toBe("longmont-c2");
    expect(session).toBe(22);
    expect(options.worldGraphContext).toMatchObject({
      campaign_id: "of-conks-cons",
      scope_mode: "campaign",
    });
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
