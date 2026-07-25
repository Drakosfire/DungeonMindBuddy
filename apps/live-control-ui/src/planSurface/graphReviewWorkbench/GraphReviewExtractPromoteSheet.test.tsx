import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState, type ComponentProps, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import { getUnionSupergraphProjection, postWorldGraphProjection, postWorldGraphRecapProjection } from "../../api/liveApi";
import type {
  ExtractPromoteConfirmReceipt,
  ExtractPromotePrepareResponse,
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import type { PlanContextDescriptor } from "../types";
import { ProjectionProvider } from "../projection/projectionContext";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";
import { GraphReviewSessionToolbar } from "./GraphReviewSessionToolbar";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getUnionSupergraphProjection: vi.fn(),
    getGoldGraphProjection: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    postWorldGraphRecapProjection: vi.fn(),
  };
});

vi.mock("../../api/extractPromoteApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/extractPromoteApi")>(
      "../../api/extractPromoteApi",
    );
  return {
    ...actual,
    getExtractPromoteStatus: vi.fn(),
    prepareExtractPromote: vi.fn(),
    confirmExtractPromote: vi.fn(),
  };
});

const planContext: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 25,
  ingestSession: 25,
  headerLabel: "Ingest",
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-25",
  graph_id: "graph-a",
  markdown: "# Projected",
  focus: {
    focus_session_id: "session-25",
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  node_views: {
    "obj-hesta": {
      node_id: "obj-hesta",
      label: "Hesta",
      kind: "npc",
      role: "character",
      summary: "Apothecary",
      evidence_ref_ids: [],
      edge_ids: [],
      beat_ids: [],
      source_span_ids: [],
    },
  },
  source_spans: [],
  mentions: [],
};

function baseRun(overrides: Partial<GraphIngestRunSummary> = {}): GraphIngestRunSummary {
  return {
    manifest_path: "artifacts/run-a/manifest.json",
    run_dir: "artifacts/run-a",
    campaign_id: "longmont-c2",
    session_id: "session-25",
    status: "preview_union_store_ready",
    updated_at: null,
    created_at: null,
    preview_union_store_path: "artifacts/run-a/preview-union.json",
    preview_union_store_valid: true,
    node_count: 2,
    edge_count: 1,
    evidence_ref_count: 3,
    next_actions: [],
    run_id: "graph-ingest:longmont-c2:session-25:run-a",
    run_label: "Run A",
    generated_at: null,
    model_id: null,
    model_provider: null,
    extraction_profile: "baseline",
    extraction_mode: null,
    vocabulary_mode: "node",
    runner_options_summary: {},
    diagnostics_summary: { candidate_graph_valid: true },
    preview_union_available: true,
    promotable: true,
    promotable_reason: null,
    ...overrides,
  };
}

function prepareResponse(
  overrides: Partial<ExtractPromotePrepareResponse> = {},
): ExtractPromotePrepareResponse {
  return {
    schema: "dmb_extract_promote_prepare_v1",
    proposalId: "prop-1",
    proposalDigest: "digest-a",
    parentRevisionId: "rev:parent",
    worldId: "eldyrwild",
    acceptedProposalsCount: 2,
    unresolvedMentionsCount: 0,
    rejectedAssertionsCount: 0,
    reviewPackage: { schema: "dmb_extract_promote_proposal_v1" },
    reviewItems: [
      {
        assertionId: "a-hesta",
        sliceQualifiedId: "0:source_extraction::a-hesta",
        kind: "object",
        label: "Hesta",
        action: "create",
        identityOutcome: "created_new",
        summary: "Create new object: Hesta",
        warnings: [],
        selectable: true,
        selectedByDefault: true,
        dependsOnAssertionIds: [],
        dependsOnSliceQualifiedIds: [],
      },
      {
        assertionId: "a-edge",
        sliceQualifiedId: "0:source_extraction::a-edge",
        kind: "relationship",
        label: "Hesta —works_at→ Apothecary",
        action: "create",
        identityOutcome: "created_new",
        summary: "Add relationship: Hesta —works_at→ Apothecary",
        warnings: [],
        selectable: true,
        selectedByDefault: true,
        dependsOnAssertionIds: ["a-hesta"],
        dependsOnSliceQualifiedIds: ["0:source_extraction::a-hesta"],
      },
    ],
    reviewSummary: {
      newObjectCount: 1,
      connectExistingCount: 0,
      relationshipCount: 1,
      unresolvedMentionCount: 0,
      rejectedAssertionCount: 0,
    },
    runId: "graph-ingest:longmont-c2:session-25:run-a",
    campaignId: "longmont-c2",
    sessionId: "session-25",
    ...overrides,
  };
}

function confirmReceipt(
  overrides: Partial<ExtractPromoteConfirmReceipt> = {},
): ExtractPromoteConfirmReceipt {
  return {
    schema: "dmb_extract_promote_confirm_v2",
    outcome: "committed",
    worldId: "eldyrwild",
    proposalId: "prop-1",
    proposalDigest: "digest-a",
    parentRevisionId: "rev:parent",
    committedRevisionId: "rev:committed",
    headAdvanced: true,
    selectedAssertionIds: ["a-hesta", "a-edge"],
    acceptedAssertionIds: ["a-hesta", "a-edge"],
    affectedObjectIds: ["obj-hesta"],
    appliedAssertionCount: 2,
    auditStatus: "ok",
    warnings: [],
    ...overrides,
  };
}

function renderWithLiveRun(liveRun: GraphIngestRunSummary, children: ReactNode) {
  const config = createIngestSurfaceConfig(planContext);
  return render(
    <ProjectionProvider config={config}>
      <GraphReviewLiveStateProvider
        campaignId="longmont-c2"
        sessionId="session-25"
        liveRun={liveRun}
        hasGold={false}
        compare={null}
        compareStatus="idle"
        compareError={null}
        selection={null}
        onSelectSelection={() => undefined}
      >
        {children}
      </GraphReviewLiveStateProvider>
    </ProjectionProvider>,
  );
}

function renderSheet(
  prepared = prepareResponse(),
  props: Partial<ComponentProps<typeof GraphReviewExtractPromoteSheet>> = {},
) {
  return renderWithLiveRun(
    baseRun(),
    <GraphReviewExtractPromoteSheet prepared={prepared} onClose={() => undefined} {...props} />,
  );
}

describe("GraphReviewExtractPromoteSheet", () => {
  beforeEach(() => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);
    vi.mocked(postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25" },
        admissibility: "gm",
      },
      summary: {
        nodeCount: 1,
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
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockReset();
  });

  it("cascades selection dependencies and disables merge CTA at zero selection", () => {
    renderSheet();

    const hesta = screen.getByRole("checkbox", { name: "Select Hesta" });
    const edge = screen.getByRole("checkbox", {
      name: "Select Hesta —works_at→ Apothecary",
    });
    expect(hesta).toBeChecked();
    expect(edge).toBeChecked();

    fireEvent.click(hesta);
    expect(hesta).not.toBeChecked();
    expect(edge).not.toBeChecked();

    const mergeCta = screen.getByTestId("graph-review-extract-promote-merge-cta");
    expect(mergeCta).toBeDisabled();
    const status = screen.getByTestId("graph-review-extract-promote-selection-status");
    expect(status).toHaveAttribute("data-selected-count", "0");
    expect(status).toHaveAttribute("data-review-package-digest", "digest-a");
    expect(status).toHaveTextContent("Select at least one accepted change");
  });

  it("calls confirm with exact selected slice-qualified assertion ids", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());

    renderSheet();

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(extractPromoteApi.confirmExtractPromote).toHaveBeenCalledWith({
        reviewPackage: { schema: "dmb_extract_promote_proposal_v1" },
        assertionIds: [
          "0:source_extraction::a-hesta",
          "0:source_extraction::a-edge",
        ],
      });
    });
    expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
  });

  it("preserves campaignless receipt and reports degraded read without projecting a campaign", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());
    vi.mocked(postWorldGraphProjection).mockClear();

    renderSheet(prepareResponse({ campaignId: null, sessionId: null }));
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
    expect(postWorldGraphProjection).not.toHaveBeenCalled();
    expect(screen.getByTestId("graph-review-extract-promote-reload-error")).toHaveTextContent(
      /campaignless exact runs cannot be reloaded through a campaign projection lens/i,
    );
  });

  it("freezes selection during deferred confirm", async () => {
    let resolveConfirm!: (value: ExtractPromoteConfirmReceipt) => void;
    const deferred = new Promise<ExtractPromoteConfirmReceipt>((resolve) => {
      resolveConfirm = resolve;
    });
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockReturnValue(deferred);

    renderSheet();

    const hesta = screen.getByRole("checkbox", { name: "Select Hesta" });
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-merge-cta")).toHaveTextContent(
        "Merging…",
      );
    });

    fireEvent.click(hesta);
    expect(hesta).toBeChecked();

    resolveConfirm(confirmReceipt());
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
  });

  it("disables Close while confirming", async () => {
    let resolveConfirm!: (value: ExtractPromoteConfirmReceipt) => void;
    const deferred = new Promise<ExtractPromoteConfirmReceipt>((resolve) => {
      resolveConfirm = resolve;
    });
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockReturnValue(deferred);

    renderSheet();

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));
    expect(screen.getByRole("button", { name: "Close" })).toBeDisabled();

    resolveConfirm(confirmReceipt());
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Close" })).not.toBeDisabled();
  });

  it("shows an unmistakable success receipt and starts World Graph sync in the background", async () => {
    const worldProjection = {
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25" },
        admissibility: "gm",
      },
      summary: {
        nodeCount: 1,
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
    } as Awaited<ReturnType<typeof postWorldGraphProjection>>;
    let resolveReload!: (value: Awaited<ReturnType<typeof postWorldGraphProjection>>) => void;
    const deferredReload = new Promise<Awaited<ReturnType<typeof postWorldGraphProjection>>>(
      (resolve) => {
        resolveReload = resolve;
      },
    );
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());
    vi.mocked(postWorldGraphProjection).mockReturnValue(deferredReload);
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);

    renderSheet();
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(
        screen.getByTestId("graph-review-extract-promote-receipt-headline"),
      ).toHaveTextContent("Merged into campaign memory");
    });
    expect(screen.getByTestId("graph-review-extract-promote-receipt")).toHaveAttribute(
      "data-projection-sync",
      "syncing",
    );
    expect(screen.getByTestId("graph-review-extract-promote-projection-sync")).toHaveTextContent(
      "Updating World Graph view in the background",
    );
    expect(screen.getByTestId("graph-review-extract-promote-done")).toHaveTextContent(
      "Done — view still updating",
    );

    resolveReload(worldProjection);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toHaveAttribute(
        "data-projection-sync",
        "ready",
      );
    });
    expect(screen.getByTestId("graph-review-extract-promote-done")).toHaveTextContent("Done");
  });

  it("does not offer confirm again after a degraded receipt, and still auto-syncs the view", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({
        outcome: "published_audit_degraded",
        auditStatus: "degraded",
        warnings: ["Audit publish degraded."],
      }),
    );
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);

    renderSheet();
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toHaveAttribute(
        "data-outcome",
        "published_audit_degraded",
      );
    });

    expect(screen.queryByTestId("graph-review-extract-promote-merge-cta")).toBeNull();
    expect(screen.getByTestId("graph-review-extract-promote-receipt-headline")).toHaveTextContent(
      "Merged into campaign memory",
    );
    expect(screen.getByTestId("graph-review-extract-promote-done")).toBeInTheDocument();
    await waitFor(() => {
      expect(postWorldGraphRecapProjection).toHaveBeenCalled();
    });
  });

  it("preserves receipt when catalog refresh fails", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);
    const onCatalogRefresh = vi.fn().mockRejectedValue(new Error("catalog refresh failed"));

    renderSheet(prepareResponse(), { onCatalogRefresh });

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(onCatalogRefresh).toHaveBeenCalled();
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
  });

  it("keeps Done available while background sync is still running", async () => {
    let resolveReload!: (value: Awaited<ReturnType<typeof postWorldGraphProjection>>) => void;
    const deferredReload = new Promise<Awaited<ReturnType<typeof postWorldGraphProjection>>>(
      (resolve) => {
        resolveReload = resolve;
      },
    );
    const onClose = vi.fn();
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());
    vi.mocked(postWorldGraphProjection).mockReturnValue(deferredReload);
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);

    renderSheet(prepareResponse(), { onClose });
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-done")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-done"));
    expect(onClose).toHaveBeenCalled();
    resolveReload({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25" },
        admissibility: "gm",
      },
      summary: {
        nodeCount: 1,
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
    } as Awaited<ReturnType<typeof postWorldGraphProjection>>);
  });
});

describe("GraphReviewSessionToolbar", () => {
  beforeEach(() => {
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(postWorldGraphRecapProjection).mockReset();
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
    vi.mocked(postWorldGraphRecapProjection).mockResolvedValue(projection);
    vi.mocked(extractPromoteApi.getExtractPromoteStatus).mockReset();
    vi.mocked(extractPromoteApi.prepareExtractPromote).mockReset();
    vi.mocked(extractPromoteApi.getExtractPromoteStatus).mockResolvedValue({
      schema: "dmb_extract_promote_status_v1",
      worldId: "eldyrwild",
      initialized: true,
      worldState: "initialized",
      headRevisionId: "rev:head",
      diagnostics: [],
    });
  });

  it("hides Review & merge when already on World Graph head", async () => {
    renderWithLiveRun(
      baseRun({ projection_authority: "world_graph" }),
      <GraphReviewSessionToolbar />,
    );

    await waitFor(() => {
      expect(screen.queryByTestId("graph-review-review-and-merge")).toBeNull();
    });
    expect(screen.queryByTestId("graph-review-merged-world-status")).toBeNull();
    expect(postWorldGraphRecapProjection).toHaveBeenCalled();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("disables Review & merge when the server marks the run non-promotable", async () => {
    renderWithLiveRun(
      baseRun({
        promotable: false,
        promotable_reason: "candidate graph is not valid",
      }),
      <GraphReviewSessionToolbar />,
    );

    const button = await screen.findByTestId("graph-review-review-and-merge");
    await waitFor(() => expect(button).toBeDisabled());
    expect(button).toHaveAttribute("title", "candidate graph is not valid");
  });

  it("ignores a stale prepare response after the selected run changes", async () => {
    let resolvePrepare!: (value: ExtractPromotePrepareResponse) => void;
    const deferred = new Promise<ExtractPromotePrepareResponse>((resolve) => {
      resolvePrepare = resolve;
    });
    vi.mocked(extractPromoteApi.prepareExtractPromote).mockReturnValue(deferred);

    function StatefulToolbar() {
      const [run, setRun] = useState(
        baseRun({
          run_id: "run-a",
          manifest_path: "artifacts/run-a/manifest.json",
        }),
      );
      return (
        <>
          <button
            type="button"
            data-testid="switch-run"
            onClick={() =>
              setRun(
                baseRun({
                  run_id: "run-b",
                  manifest_path: "artifacts/run-b/manifest.json",
                }),
              )
            }
          >
            Switch
          </button>
          <ProjectionProvider config={createIngestSurfaceConfig(planContext)}>
            <GraphReviewLiveStateProvider
              campaignId="longmont-c2"
              sessionId="session-25"
              liveRun={run}
              hasGold={false}
              compare={null}
              compareStatus="idle"
              compareError={null}
              selection={null}
              onSelectSelection={() => undefined}
            >
              <GraphReviewSessionToolbar />
            </GraphReviewLiveStateProvider>
          </ProjectionProvider>
        </>
      );
    }

    render(<StatefulToolbar />);

    const reviewButton = await screen.findByTestId("graph-review-review-and-merge");
    await waitFor(() => expect(reviewButton).not.toBeDisabled());
    fireEvent.click(reviewButton);
    expect(extractPromoteApi.prepareExtractPromote).toHaveBeenCalledWith({ runId: "run-a" });

    fireEvent.click(screen.getByTestId("switch-run"));
    expect(screen.queryByTestId("graph-review-extract-promote-sheet")).toBeNull();

    resolvePrepare(
      prepareResponse({
        runId: "run-a",
        proposalDigest: "digest-stale-a",
        proposalId: "prop-stale-a",
      }),
    );

    await waitFor(() => {
      expect(screen.queryByTestId("graph-review-extract-promote-sheet")).toBeNull();
    });
    expect(screen.queryByText(/digest-stale-a/)).toBeNull();
  });

  it("opens the review sheet for a successful prepare on the current run", async () => {
    vi.mocked(extractPromoteApi.prepareExtractPromote).mockResolvedValue(
      prepareResponse(),
    );

    renderWithLiveRun(baseRun(), <GraphReviewSessionToolbar />);

    const reviewButton = await screen.findByTestId("graph-review-review-and-merge");
    await waitFor(() => expect(reviewButton).not.toBeDisabled());
    fireEvent.click(reviewButton);

    const sheet = await screen.findByTestId("graph-review-extract-promote-sheet");
    expect(sheet).toHaveAttribute("data-proposal-digest", "digest-a");
    expect(
      screen.getByRole("checkbox", { name: "Select Hesta —works_at→ Apothecary" }),
    ).toBeInTheDocument();
  });
});
