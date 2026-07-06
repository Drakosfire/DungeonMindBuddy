import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    expect(screen.getByText(/Prepare wrote nothing/i)).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-commit-button")).toBeEnabled();
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
});
