import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { WorldGraphProjection } from "../../api/types";
import {
  WorldGraphLensProjectionProvider,
  WorldGraphLensProvider,
} from "../../graphLens";
import { WorldGraphRecapProjectionView } from "./WorldGraphRecapProjection";
import { session23WorldGraphRecapFixture } from "./worldGraphRecapFixture";

const recapRecord = {
  schema_version: "dmb_recap_artifact_record_v1" as const,
  artifact_id: "longmont-c2/session-23",
  campaign_id: "longmont-c2",
  session_id: "session-23",
  source_artifact_id: null,
  source_recap_path: "corpus/eldyrwild-markdown/Session 23 - Recap.md",
  breadcrumb_seed_path: null,
  session_memory_records_path: null,
  run_bundle_uri: "",
  run_manifest_uri: "",
  source_span_index_uri: "",
  provenance_index_uri: null,
  graph_run_refs: [],
  default_graph_run_uri: null,
  default_projection_mode: "recap_graph",
  source_sha256: "sha256:session-23",
  registered_at: "2026-06-28T00:00:00Z",
  updated_at: "2026-06-28T00:00:00Z",
  registry_source: "scan" as const,
};

describe("WorldGraphRecapProjectionView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockImplementation(async (request) => {
      const node = session23WorldGraphRecapFixture.nodeViews[request.nodeId] ?? null;
      return {
        schema: "dmb_world_graph_object_projection_v1",
        found: Boolean(node),
        completeness: { status: "complete", truncatedFields: [] },
        snapshot: session23WorldGraphRecapFixture.snapshot,
        requestedNodeId: request.nodeId,
        resolvedNodeId: node ? request.nodeId : null,
        node,
        relatedNodes: [],
        semanticFingerprint: "fp-test",
      };
    });
    vi.spyOn(liveApi, "prepareGraphObjectAuthoringWrite");
    vi.spyOn(liveApi, "commitGraphObjectAuthoringWrite");
    vi.spyOn(liveApi, "resolveGraphReviewExistingObjectCandidates").mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      selected_node_id: "selection",
      selected_label: "selection",
      candidates: [],
      warnings: [],
      diagnostics: [],
      scopes_searched: [],
    });
  });

  it("opens a campaign-memory Peek without World Object chrome or Continue in Build", async () => {
    render(
      <WorldGraphRecapProjectionView
        payload={session23WorldGraphRecapFixture}
        selectedSessionId="session-23"
        onSelectSession={vi.fn()}
        sessionOptions={["session-23"]}
        selectedCampaignId="longmont-c2"
        onSelectCampaign={vi.fn()}
        recapRecord={recapRecord}
      />,
    );

    const pill = await waitFor(() => {
      const button = screen
        .getAllByRole("button", { name: /Caelynn/i })
        .find((item) => item.classList.contains("recap-node-token"));
      expect(button).toBeTruthy();
      return button as HTMLButtonElement;
    });
    fireEvent.click(pill);
    await waitFor(() => {
      expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalled();
    });

    expect(screen.queryByText("World object")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Continue in Build/i })).not.toBeInTheDocument();
    expect(document.querySelector(".recap-graph-object-panel__header")).not.toBeInTheDocument();
    const peek = screen.getByLabelText("Caelynn graph object");
    expect(within(peek).getByRole("heading", { level: 4 })).toHaveTextContent("Caelynn");
    expect(within(peek).getByRole("region", { name: "Campaign summary" })).toHaveTextContent(
      "Held the Mireward gate during Session 23.",
    );
    expect(peek).toHaveAttribute("data-graph-object-card-mode", "campaign-memory");
    expect(within(peek).getByRole("button", { name: /Close Caelynn/i })).toBeInTheDocument();
    expect(within(peek).queryByText("Advanced")).not.toBeInTheDocument();
    expect(peek.querySelectorAll("details")).toHaveLength(1);
    fireEvent.click(within(peek).getByText("Source"));
    expect(within(peek).queryByText("Advanced")).not.toBeInTheDocument();
    expect(within(peek).getByText("World ID")).toBeInTheDocument();
    expect(peek.querySelectorAll("details details")).toHaveLength(0);

    fireEvent.click(within(peek).getByRole("button", { name: /Open related object.*Mirathorn/i }));
    expect(within(peek).getByRole("heading", { level: 4, name: "Caelynn" })).toBeInTheDocument();
    expect(screen.getByTestId("recap-graph-related-object-expansion")).toHaveTextContent(
      "Mirathorn",
    );
    expect(screen.getByTestId("recap-graph-related-object-expansion")).toHaveTextContent(
      "Durable location referenced from earlier campaign context.",
    );

    fireEvent.click(within(peek).getByRole("button", { name: /Close Caelynn/i }));
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Published recap")).toBeInTheDocument();
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-existing-node-id",
      "pc_caelynn",
    );
    const authorNodeToggle = screen.getByRole("button", { name: "Author Node" });
    if (authorNodeToggle.getAttribute("aria-expanded") !== "true") {
      fireEvent.click(authorNodeToggle);
    }
    expect(screen.getByTestId("graph-object-authoring-published-wizard")).toHaveAttribute(
      "data-wizard-step",
      "resolve",
    );
    expect(document.querySelector(".graph-object-authoring-selected-source-phrase")).toHaveTextContent(
      "Caelynn",
    );
    expect(liveApi.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(liveApi.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  }, 15000);

  it("shows a truthful local state instead of World-memory loading for a local object", async () => {
    sessionStorage.setItem(
      "graph-object-authoring-staged:longmont-c2:session-23",
      JSON.stringify([
        {
          localProposalId: "local-object-world-graph-test",
          proposalKind: "object",
          status: "staged_local",
          selection: {
            campaignId: "longmont-c2",
            sessionId: "session-23",
            selectionKind: "graph_node_reference",
            selectedText: "Caelynn",
            normalizedSelectedText: "caelynn",
            existingNodeId: "pc_caelynn",
            graphId: session23WorldGraphRecapFixture.graphId,
            laneRole: "live",
          },
          objectRef: {
            label: "Caelynn",
            kind: "concept",
            role: null,
            aliases: [],
            summary: "A local authoring draft for the working projection.",
          },
          visibility: {
            visibility: "gm_private",
            revealState: "unrevealed",
            visibilityNote: null,
          },
          graphScopes: ["recap_graph", "campaign_memory_graph"],
          provenancePreview: {
            origin: "human_authored",
            authoringSurface: "memory_ingest_graph_authoring",
            sourceGraphId: session23WorldGraphRecapFixture.graphId,
            sourceArtifactPath: null,
            operatorNote: null,
          },
        },
      ]),
    );

    render(
      <WorldGraphRecapProjectionView
        payload={session23WorldGraphRecapFixture}
        selectedSessionId="session-23"
        onSelectSession={vi.fn()}
        sessionOptions={["session-23"]}
        selectedCampaignId="longmont-c2"
        onSelectCampaign={vi.fn()}
        recapRecord={recapRecord}
      />,
    );

    const pill = await waitFor(() => {
      const button = screen
        .getAllByRole("button", { name: /Caelynn/i })
        .find((item) => item.classList.contains("recap-node-token"));
      expect(button).toBeTruthy();
      return button as HTMLButtonElement;
    });
    fireEvent.click(pill);

    const peek = await screen.findByLabelText("Caelynn graph object");
    expect(liveApi.postWorldGraphCompleteObject).not.toHaveBeenCalled();
    expect(screen.getByTestId("recap-graph-local-object-state")).toHaveTextContent(
      "World memory was not loaded",
    );
    expect(screen.queryByText("Loading campaign memory…")).not.toBeInTheDocument();
    expect(within(peek).getByRole("region", { name: "Campaign summary" })).toHaveTextContent(
      "A local authoring draft for the working projection.",
    );
  });

  it("keeps root prose visible when a related-object expansion is unavailable", async () => {
    const root = session23WorldGraphRecapFixture.nodeViews.pc_caelynn;
    const { node_id: missingTargetNodeId, ...missingTargetEdge } = {
      ...root.adjacency[0]!,
      node_id: "loc_missing",
    };
    const missingTargetPayload = {
      ...session23WorldGraphRecapFixture,
      nodeViews: {
        ...session23WorldGraphRecapFixture.nodeViews,
        pc_caelynn: {
          ...root,
          adjacency: [
            { ...missingTargetEdge, nodeId: missingTargetNodeId, label: "Missing place" },
          ],
        },
      },
    };
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockImplementation(async (request) => {
      const node = missingTargetPayload.nodeViews[request.nodeId] ?? null;
      return {
        schema: "dmb_world_graph_object_projection_v1",
        found: Boolean(node),
        completeness: { status: "complete", truncatedFields: [] },
        snapshot: missingTargetPayload.snapshot,
        requestedNodeId: request.nodeId,
        resolvedNodeId: node ? request.nodeId : null,
        node,
        relatedNodes: [],
        semanticFingerprint: "fp-missing-related-test",
      };
    });

    render(
      <WorldGraphRecapProjectionView
        payload={missingTargetPayload}
        selectedSessionId="session-23"
        onSelectSession={vi.fn()}
        sessionOptions={["session-23"]}
        selectedCampaignId="longmont-c2"
        onSelectCampaign={vi.fn()}
        recapRecord={recapRecord}
      />,
    );

    const pill = await waitFor(() => {
      const button = screen
        .getAllByRole("button", { name: /Caelynn/i })
        .find((item) => item.classList.contains("recap-node-token"));
      expect(button).toBeTruthy();
      return button as HTMLButtonElement;
    });
    fireEvent.click(pill);
    const peek = await screen.findByLabelText("Caelynn graph object");
    expect(within(peek).getByRole("region", { name: "Campaign summary" })).toHaveTextContent(
      "Held the Mireward gate during Session 23.",
    );

    fireEvent.click(within(peek).getByRole("button", { name: /Missing place/i }));

    expect(screen.getByTestId("recap-graph-related-object-unavailable")).toHaveTextContent(
      "The connected object is unavailable",
    );
    expect(within(peek).getByRole("heading", { level: 4, name: "Caelynn" })).toBeInTheDocument();
    expect(within(peek).getByRole("region", { name: "Campaign summary" })).toHaveTextContent(
      "Held the Mireward gate during Session 23.",
    );
  }, 15000);

  it("reads a durable object through the shared World lens, not the recap focus", async () => {
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c1&session=session-1");
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue({
      schema: "dmb_ingestion_source_bundle_v1",
      campaigns: {},
    } as never);
    const worldProjection: WorldGraphProjection = {
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-world-union",
        headRevisionId: "rev-world-union",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "world",
      },
      summary: {
        nodeCount: 1,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [{
        nodeId: "pc_caelynn",
        label: "Caelynn",
        kind: "pc",
        role: "pc",
        aliases: ["Caelynn"],
        sourceDomains: ["party_pc"],
        anchoredToFocusSession: false,
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [],
      }],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    };
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(worldProjection);

    render(
      <WorldGraphLensProvider planCampaignId="longmont-c2">
        <WorldGraphLensProjectionProvider defaultCampaignId="longmont-c2">
          <WorldGraphRecapProjectionView
            payload={session23WorldGraphRecapFixture}
            selectedSessionId="session-1"
            onSelectSession={vi.fn()}
            sessionOptions={["session-1"]}
            selectedCampaignId="longmont-c1"
            onSelectCampaign={vi.fn()}
            recapRecord={recapRecord}
          />
        </WorldGraphLensProjectionProvider>
      </WorldGraphLensProvider>,
    );

    const pill = await waitFor(() => {
      const button = screen
        .getAllByRole("button", { name: /Caelynn/i })
        .find((item) => item.classList.contains("recap-node-token"));
      expect(button).toBeTruthy();
      return button as HTMLButtonElement;
    });
    fireEvent.click(pill);

    await waitFor(() => {
      expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledWith(
        expect.objectContaining({
          worldId: "eldyrwild",
          campaignId: "longmont-c2",
          revisionPin: "rev-world-union",
          focus: { kind: "none", sessionId: null },
        }),
      );
    });
  }, 15000);
});
