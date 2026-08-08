import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";
import { GraphObjectAuthoringPrepareCommitPanel } from "./GraphObjectAuthoringPrepareCommitPanel";

vi.mock("../../api/liveApi", () => ({
  prepareGraphObjectAuthoringWrite: vi.fn(),
  commitGraphObjectAuthoringWrite: vi.fn(),
}));

import {
  commitGraphObjectAuthoringWrite,
  prepareGraphObjectAuthoringWrite,
} from "../../api/liveApi";

const stagedProposal = {
  localProposalId: "local-object-1",
  proposalKind: "object",
  status: "staged_local",
  selection: {
    selectionKind: "text_span",
    selectedText: "gang",
    normalizedSelectedText: "gang",
  },
  objectRef: {
    label: "Questionable Company",
    kind: "party",
    role: null,
    aliases: ["gang"],
    summary: null,
  },
  visibility: { visibility: "gm_private", revealState: "unrevealed" },
  graphScopes: ["recap_graph", "campaign_memory_graph"],
  provenancePreview: {
    origin: "human_authored",
    authoringSurface: "memory_ingest_graph_authoring",
  },
} as GraphObjectAuthoringProposal;

const prepareResponse = {
  prepared: true,
  campaign_id: "longmont-c1",
  overlay_path: "/tmp/overlay.json",
  event_log_path: "/tmp/events.jsonl",
  current_overlay_token: "current-token",
  proposed_assertions_digest: "proposed-digest",
  confirm_token: "confirm-token",
  assertion_count: 1,
  event_count: 2,
  assertions_preview: [
    {
      assertion_id: "assert-1",
      assertion_kind: "object",
      operation: "create",
      local_proposal_id: "local-object-1",
      summary: "Object: Questionable Company",
    },
  ],
  overlay_summary: {
    existing_assertion_count: 0,
    proposed_assertion_count: 1,
    total_assertion_count: 1,
    object_count: 1,
    link_existing_count: 0,
    relationship_count: 0,
  },
  diagnostics: [],
  no_mutation_guarantees: [
    "Prepare wrote nothing.",
    "Source markdown was not mutated.",
  ],
};

const commitResponse = {
  committed: true,
  campaign_id: "longmont-c1",
  overlay_path: "/tmp/overlay.json",
  event_log_path: "/tmp/events.jsonl",
  backup_path: null,
  assertion_count: 1,
  event_count: 2,
  new_overlay_token: "new-token",
  diagnostics: [],
  no_mutation_guarantees: ["Committed authored graph memory."],
};

describe("GraphObjectAuthoringPrepareCommitPanel", () => {
  beforeEach(() => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockReset();
    vi.mocked(commitGraphObjectAuthoringWrite).mockReset();
  });

  it("renders nothing when there are no staged proposals", () => {
    const { container } = render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[]}
        onCommitted={() => undefined}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("shows prepare button enabled when proposals exist", () => {
    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );
    expect(screen.getByTestId("graph-object-authoring-prepare-button")).toBeEnabled();
    expect(screen.queryByTestId("graph-object-authoring-commit-button")).not.toBeInTheDocument();
  });

  it("calls prepare API and renders preview on success", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));

    await waitFor(() => {
      expect(prepareGraphObjectAuthoringWrite).toHaveBeenCalledWith(
        expect.objectContaining({
          campaignId: "longmont-c1",
          sessionId: "session-2",
          proposals: [stagedProposal],
        }),
      );
    });

    expect(screen.getByTestId("graph-object-authoring-prepare-preview")).toBeInTheDocument();
    expect(screen.getByText(/Safe write preview generated/i)).toBeInTheDocument();
    expect(screen.getByText(/1 new object/i)).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-write-safety-details")).not.toHaveAttribute("open");
    expect(screen.getByTestId("graph-object-authoring-technical-write-details")).not.toHaveAttribute("open");
    expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
  });

  it("shows technical write details only when expanded", async () => {
    const user = userEvent.setup();
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-prepare-preview")).toBeInTheDocument();
    });

    const safetyDetails = screen.getByTestId("graph-object-authoring-write-safety-details");
    const technicalDetails = screen.getByTestId("graph-object-authoring-technical-write-details");
    expect(safetyDetails).not.toHaveAttribute("open");
    expect(technicalDetails).not.toHaveAttribute("open");

    await user.click(screen.getByText("Write safety details"));
    expect(safetyDetails).toHaveAttribute("open");
    expect(within(safetyDetails).getByText(/Prepare wrote nothing/i)).toBeInTheDocument();

    await user.click(screen.getByText("Technical write details"));
    expect(technicalDetails).toHaveAttribute("open");
    expect(within(technicalDetails).getByText("/tmp/overlay.json")).toBeInTheDocument();
    expect(within(technicalDetails).getByText("/tmp/events.jsonl")).toBeInTheDocument();
  });

  it("clears prepared state when proposals change after prepare", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);

    const { rerender } = render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-prepare-preview")).toBeInTheDocument();
    });

    rerender(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[
          {
            ...stagedProposal,
            localProposalId: "local-object-2",
          } as GraphObjectAuthoringProposal,
        ]}
        onCommitted={() => undefined}
      />,
    );

    expect(screen.queryByTestId("graph-object-authoring-prepare-preview")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-commit-button")).not.toBeInTheDocument();
  });

  it("opens Recap View after commit success and keeps refresh available", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      configurable: true,
      value: { ...window.location, assign },
    });
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue(commitResponse);
    const onRefreshProjection = vi.fn().mockResolvedValue(undefined);

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
        onRefreshProjection={onRefreshProjection}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-summary")).toBeInTheDocument();
      expect(onRefreshProjection).toHaveBeenCalledTimes(1);
      expect(assign).toHaveBeenCalledWith("/plan?tool=recap&campaign=longmont-c1&session=session-2");
    });

    expect(screen.getByTestId("graph-object-authoring-open-recap-view")).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-refresh-projection")).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-commit-write-details")).not.toHaveAttribute("open");

    const summaryText = screen.getByTestId("graph-object-authoring-commit-summary").textContent ?? "";
    const openRecapIndex = summaryText.indexOf("Open Recap View");
    const writeDetailsIndex = summaryText.indexOf("Write details");
    expect(openRecapIndex).toBeGreaterThanOrEqual(0);
    expect(writeDetailsIndex).toBeGreaterThan(openRecapIndex);

    const writeDetails = screen.getByTestId("graph-object-authoring-commit-write-details");
    await user.click(screen.getByText("Write details"));
    expect(writeDetails).toHaveAttribute("open");
    expect(within(writeDetails).getByText("/tmp/overlay.json")).toBeInTheDocument();
    expect(within(writeDetails).getByText("/tmp/events.jsonl")).toBeInTheDocument();
  });

  it("commits successfully and notifies parent", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue(commitResponse);
    const onCommitted = vi.fn();

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        sourceRunId="run-c1s2"
        sourceGraphId="graph-c1s2"
        previewUnionStorePath="/stores/preview_union.json"
        proposals={[stagedProposal]}
        onCommitted={onCommitted}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });

    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(commitGraphObjectAuthoringWrite).toHaveBeenCalledWith(
        expect.objectContaining({
          sourceRunId: "run-c1s2",
          sourceGraphId: "graph-c1s2",
          previewUnionStorePath: "/stores/preview_union.json",
        }),
      );
      expect(onCommitted).toHaveBeenCalledWith(["local-object-1"]);
    });

    expect(screen.getByTestId("graph-object-authoring-commit-summary")).toBeInTheDocument();
    expect(screen.getByText(/Write succeeded/i)).toBeInTheDocument();
  });

  it("keeps commit success visible after parent clears staged proposals", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue(commitResponse);
    const onCommitted = vi.fn();

    const { rerender } = render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={onCommitted}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(onCommitted).toHaveBeenCalledWith(["local-object-1"]);
    });

    rerender(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[]}
        onCommitted={onCommitted}
      />,
    );

    expect(screen.getByTestId("graph-object-authoring-commit-summary")).toBeInTheDocument();
    expect(screen.getByText(/Write succeeded/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-prepare-button")).not.toBeInTheDocument();
  });

  it("renders prepare overlap warnings from diagnostics", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      ...prepareResponse,
      diagnostics: [
        {
          code: "authored_overlay_possible_duplicate_alias",
          message: 'Possible duplicate: "gang" is already an alias of authored object "Questionable Company".',
          local_proposal_id: "local-object-1",
          severity: "warning",
        },
      ],
    });

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-overlap-warnings")).toBeInTheDocument();
      expect(screen.getByText(/already an alias of authored object/i)).toBeInTheDocument();
    });
  });

  it("shows stale overlay message on commit failure", async () => {
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue(prepareResponse);
    vi.mocked(commitGraphObjectAuthoringWrite).mockRejectedValue(
      new Error('{"code":"stale_overlay","message":"changed since"}'),
    );

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        proposals={[stagedProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(
        screen.getByText(/Prepare again before committing/i),
      ).toBeInTheDocument();
    });
  });

  it("shows union graph materialization outcome after merge commit", async () => {
    const mergeProposal = {
      localProposalId: "local-merge-1",
      proposalKind: "merge_objects",
      status: "staged_local",
      survivorObjectRef: {
        refKind: "existing_graph_node",
        nodeId: "survivor-node",
        label: "Tripod Null-Calf",
        kind: "threat",
      },
      mergedObjectRefs: [
        {
          refKind: "existing_graph_node",
          nodeId: "merged-node",
          label: "Tripod Null Calf",
          kind: "threat",
        },
      ],
      mergeReason: "Exact normalized label match",
      matchedFeatures: ["Exact normalized label match"],
      aliasPolicy: "preserve_all_aliases",
      relationshipPolicy: "preserve_all_relationships",
      evidencePolicy: "preserve_all_evidence",
      visibility: { visibility: "gm_private", revealState: "unrevealed" },
      graphScopes: ["recap_graph", "campaign_memory_graph"],
      provenancePreview: {
        origin: "human_authored",
        authoringSurface: "memory_ingest_graph_authoring",
      },
    } as GraphObjectAuthoringProposal;

    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      ...prepareResponse,
      overlay_summary: {
        ...prepareResponse.overlay_summary,
        merge_objects_count: 1,
      },
    });
    vi.mocked(commitGraphObjectAuthoringWrite).mockResolvedValue({
      ...commitResponse,
      union_store_materialization: {
        attempted: true,
        applied: true,
        reason: "materialized",
        applied_assertion_ids: ["assert-merge-1"],
        redirects_added: 1,
        edges_rewired: 1,
        survivor_nodes_updated: 1,
        diagnostics: [],
      },
    });

    render(
      <GraphObjectAuthoringPrepareCommitPanel
        campaignId="longmont-c1"
        sessionId="session-2"
        previewUnionStorePath="/stores/preview_union.json"
        proposals={[mergeProposal]}
        onCommitted={() => undefined}
      />,
    );

    fireEvent.click(screen.getByTestId("graph-object-authoring-prepare-button"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-commit-button"));

    await waitFor(() => {
      expect(
        screen.getByTestId("graph-object-authoring-commit-materialization-outcome"),
      ).toHaveTextContent(/Merged directly into the union graph/i);
      expect(screen.getByText(/1 redirect/i)).toBeInTheDocument();
    });
  });
});
