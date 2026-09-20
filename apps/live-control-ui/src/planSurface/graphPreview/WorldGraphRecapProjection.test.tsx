import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
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
    expect(peek).toHaveAttribute("data-graph-object-card-mode", "campaign-memory");
    expect(within(peek).getByRole("button", { name: /Close Caelynn/i })).toBeInTheDocument();
    expect(within(peek).queryByText("Advanced")).not.toBeInTheDocument();
    expect(peek.querySelectorAll("details")).toHaveLength(1);
    fireEvent.click(within(peek).getByText("Source"));
    expect(within(peek).queryByText("Advanced")).not.toBeInTheDocument();
    expect(within(peek).getByText("World ID")).toBeInTheDocument();
    expect(peek.querySelectorAll("details details")).toHaveLength(0);

    fireEvent.click(within(peek).getByRole("button", { name: /Close Caelynn/i }));
    expect(screen.queryByTestId("graph-object-projection-card")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Published recap")).toBeInTheDocument();
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-existing-node-id",
      "pc_caelynn",
    );
    expect(screen.getByLabelText("Label")).toHaveValue("Caelynn");
    expect(liveApi.prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(liveApi.commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  }, 15000);
});
