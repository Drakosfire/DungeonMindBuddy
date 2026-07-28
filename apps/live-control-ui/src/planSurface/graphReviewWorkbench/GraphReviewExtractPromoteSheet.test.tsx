import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useMemo, useState, type ComponentProps, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import { getUnionSupergraphProjection, postWorldGraphProjection } from "../../api/liveApi";
import type {
  ExtractPromoteConfirmReceipt,
  ExtractPromotePrepareResponse,
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import type { PlanContextDescriptor } from "../types";
import { AgentInteractionProjectionTestHost } from "../projection/projectionTestHost";
import { GraphReviewExtractPromoteSheet } from "./GraphReviewExtractPromoteSheet";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import {
  GraphReviewLiveStateProvider,
  useGraphReviewLiveState,
} from "./GraphReviewLiveStateContext";
import { catalogRunBindingKey } from "./graphReviewCommittedAuthority";
import { GraphReviewSessionToolbar } from "./GraphReviewSessionToolbar";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getUnionSupergraphProjection: vi.fn(),
    getGoldGraphProjection: vi.fn(),
    postWorldGraphProjection: vi.fn(),
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
    "object-1": {
      node_id: "object-1",
      label: "Candidate Hesta",
      kind: "npc",
      role: "character",
      summary: "Apothecary candidate",
      evidence_ref_ids: [],
      edge_ids: [],
      beat_ids: [],
      source_span_ids: [],
    },
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
    <AgentInteractionProjectionTestHost config={config}>
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
    </AgentInteractionProjectionTestHost>,
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
    vi.mocked(postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25", campaignId: "longmont-c2" },
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
      nodes: [
        {
          nodeId: "object-1",
          label: "Hesta Ironroot",
          kind: "npc",
          role: "character",
          aliases: ["Hesta"],
          sourceDomains: ["recap"],
          anchoredToFocusSession: true,
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
        },
      ],
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

    const config = createIngestSurfaceConfig(planContext);
    render(
      <ProjectionProvider config={config}>
        <GraphReviewLiveStateProvider
          campaignId=""
          sessionId=""
          liveRun={baseRun()}
          hasGold={false}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <GraphReviewExtractPromoteSheet
            prepared={prepareResponse({ campaignId: null, sessionId: null })}
            onClose={() => undefined}
          />
        </GraphReviewLiveStateProvider>
      </ProjectionProvider>,
    );
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

  it("does not offer confirm again after a degraded receipt", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({
        outcome: "published_audit_degraded",
        auditStatus: "degraded",
        warnings: ["Audit publish degraded."],
        affectedObjectIds: ["object-1"],
      }),
    );

    renderSheet();
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toHaveAttribute(
        "data-outcome",
        "published_audit_degraded",
      );
    });

    expect(screen.queryByTestId("graph-review-extract-promote-merge-cta")).toBeNull();
    expect(
      screen.getByTestId("graph-review-extract-promote-reload-revision"),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(postWorldGraphProjection).toHaveBeenCalled();
    });
  });

  it("post-confirm shows durable World Graph label over conflicting candidate label", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );

    renderWithLiveRun(
      baseRun(),
      <>
        <GraphReviewExtractPromoteSheet
          prepared={prepareResponse()}
          onClose={() => undefined}
        />
        <GraphReviewLiveProjectionPanel />
      </>,
    );

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-committed-projection-panel")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
    expect(screen.queryByText("Candidate Hesta")).toBeNull();
  });

  it("reload after terminal receipt reloads committed authority without re-confirming", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );

    renderSheet();
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
    expect(extractPromoteApi.confirmExtractPromote).toHaveBeenCalledTimes(1);
    const projectionCallsAfterConfirm = vi.mocked(postWorldGraphProjection).mock.calls.length;
    expect(projectionCallsAfterConfirm).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-reload-revision"));
    await waitFor(() => {
      expect(vi.mocked(postWorldGraphProjection).mock.calls.length).toBeGreaterThan(
        projectionCallsAfterConfirm,
      );
    });
    expect(extractPromoteApi.confirmExtractPromote).toHaveBeenCalledTimes(1);
  });

  it("preserves receipt when catalog refresh fails", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(confirmReceipt());
    const onCatalogRefresh = vi.fn().mockRejectedValue(new Error("catalog refresh failed"));

    renderSheet(prepareResponse(), { onCatalogRefresh });

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(onCatalogRefresh).toHaveBeenCalled();
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
  });

  it("keeps receipt phase when post-commit projection fails; reload retries projection only", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );
    vi.mocked(postWorldGraphProjection).mockRejectedValue(
      new Error("projection unavailable"),
    );

    renderSheet();
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    });
    expect(
      screen.queryByTestId("graph-review-extract-promote-retry-exact-confirm"),
    ).toBeNull();
    expect(
      screen.getByTestId("graph-review-extract-promote-reload-revision"),
    ).toBeInTheDocument();
    expect(extractPromoteApi.confirmExtractPromote).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(
        screen.getByTestId("graph-review-extract-promote-reload-error"),
      ).toBeInTheDocument();
    });
    const projectionCallsAfterConfirm = vi.mocked(postWorldGraphProjection).mock.calls.length;
    expect(projectionCallsAfterConfirm).toBeGreaterThan(0);

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-reload-revision"));
    await waitFor(() => {
      expect(vi.mocked(postWorldGraphProjection).mock.calls.length).toBeGreaterThan(
        projectionCallsAfterConfirm,
      );
    });
    expect(extractPromoteApi.confirmExtractPromote).toHaveBeenCalledTimes(1);
    expect(
      screen.queryByTestId("graph-review-extract-promote-retry-exact-confirm"),
    ).toBeNull();
    expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
  });

  it("adopts committed authority before catalog refresh", async () => {
    const order: string[] = [];
    let resolveRefresh!: () => void;
    const refreshGate = new Promise<void>((resolve) => {
      resolveRefresh = resolve;
    });

    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );
    vi.mocked(postWorldGraphProjection).mockImplementation(async () => {
      order.push("adopt");
      return {
        schema: "dmb_world_graph_projection_v1",
        snapshot: {
          worldId: "eldyrwild",
          campaignId: "longmont-c2",
          revisionId: "rev:committed",
          headRevisionId: "rev:committed",
          isHead: true,
          focus: { kind: "session", sessionId: "session-25", campaignId: "longmont-c2" },
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
        nodes: [
          {
            nodeId: "object-1",
            label: "Hesta Ironroot",
            kind: "npc",
            role: "character",
            aliases: [],
            sourceDomains: [],
            anchoredToFocusSession: true,
            evidenceBadges: [],
            adjacency: [],
            suggestedExpansions: [],
            evidenceRefIds: [],
            sourceArtifactIds: [],
          },
        ],
        relationships: [],
        attributes: [],
        evidence: [],
        sourceArtifacts: [],
        diagnostics: [],
      };
    });
    const onCatalogRefresh = vi.fn(async () => {
      order.push("refresh");
      await refreshGate;
    });

    renderSheet(prepareResponse(), { onCatalogRefresh });
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(order).toContain("adopt");
      expect(order).toContain("refresh");
    });
    expect(order.indexOf("adopt")).toBeLessThan(order.indexOf("refresh"));
    expect(screen.getByTestId("graph-review-extract-promote-receipt")).toBeInTheDocument();
    // Adoption already completed while refresh is still gated.
    expect(postWorldGraphProjection).toHaveBeenCalled();

    resolveRefresh();
    await waitFor(() => expect(onCatalogRefresh).toHaveBeenCalledTimes(1));
  });

  it("clears confirmInFlight when the sheet unmounts during terminal adoption", async () => {
    let resolveProjection!: (value: Awaited<ReturnType<typeof postWorldGraphProjection>>) => void;
    const deferredProjection = new Promise<Awaited<ReturnType<typeof postWorldGraphProjection>>>(
      (resolve) => {
        resolveProjection = resolve;
      },
    );
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );
    vi.mocked(postWorldGraphProjection).mockReturnValue(deferredProjection);

    function InFlightHarness() {
      const [inFlight, setInFlight] = useState(false);
      const { committedPhase } = useGraphReviewLiveState();
      return (
        <>
          <span data-testid="confirm-in-flight">{inFlight ? "yes" : "no"}</span>
          {committedPhase === "candidate" ? (
            <GraphReviewExtractPromoteSheet
              prepared={prepareResponse()}
              onClose={() => undefined}
              onConfirmInFlightChange={setInFlight}
            />
          ) : (
            <span data-testid="sheet-replaced-by-committed">replaced</span>
          )}
        </>
      );
    }

    renderWithLiveRun(baseRun(), <InFlightHarness />);
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("sheet-replaced-by-committed")).toBeInTheDocument();
      // Unmount cleanup must clear parent in-flight; otherwise run cleanup/selection stays blocked.
      expect(screen.getByTestId("confirm-in-flight")).toHaveTextContent("no");
    });

    resolveProjection({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25", campaignId: "longmont-c2" },
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
      nodes: [
        {
          nodeId: "object-1",
          label: "Hesta Ironroot",
          kind: "npc",
          role: "character",
          aliases: [],
          sourceDomains: [],
          anchoredToFocusSession: true,
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
        },
      ],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
  });

  it("does not adopt run A receipt onto run B after binding changes during deferred confirm", async () => {
    let resolveConfirm!: (value: ExtractPromoteConfirmReceipt) => void;
    const deferredConfirm = new Promise<ExtractPromoteConfirmReceipt>((resolve) => {
      resolveConfirm = resolve;
    });
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockReturnValue(deferredConfirm);
    vi.mocked(postWorldGraphProjection).mockClear();

    function BindingRaceHarness() {
      const [run, setRun] = useState(
        baseRun({
          run_id: "run-a",
          manifest_path: "artifacts/run-a/manifest.json",
        }),
      );
      const [confirmInFlight, setConfirmInFlight] = useState(false);
      const binding = useMemo(
        () => ({
          kind: "catalog_run" as const,
          key: catalogRunBindingKey({
            runId: run.run_id!,
            campaignId: "longmont-c2",
            sessionId: "session-25",
          }),
          runId: run.run_id!,
          campaignId: "longmont-c2",
          sessionId: "session-25",
        }),
        [run.run_id],
      );

      function AuthorityProbe() {
        const { committedPhase, committedReceipt, committedBinding } =
          useGraphReviewLiveState();
        return (
          <>
            <span data-testid="committed-phase">{committedPhase}</span>
            <span data-testid="committed-has-receipt">
              {committedReceipt ? "yes" : "no"}
            </span>
            <span data-testid="committed-binding-key">
              {committedBinding?.key ?? ""}
            </span>
            <span data-testid="committed-receipt-digest">
              {committedReceipt?.proposalDigest ?? ""}
            </span>
          </>
        );
      }

      return (
        <ProjectionProvider config={createIngestSurfaceConfig(planContext)}>
          <GraphReviewLiveStateProvider
            campaignId="longmont-c2"
            sessionId="session-25"
            liveRun={run}
            committedBinding={binding}
            hasGold={false}
            compare={null}
            compareStatus="idle"
            compareError={null}
            selection={null}
            onSelectSelection={() => undefined}
          >
            <AuthorityProbe />
            <button
              type="button"
              data-testid="load-run-b"
              onClick={() =>
                setRun(
                  baseRun({
                    run_id: "run-b",
                    manifest_path: "artifacts/run-b/manifest.json",
                  }),
                )
              }
            >
              Load B
            </button>
            {/* Retain prepared sheet while confirm is in flight (catalog toolbar behavior). */}
            {(confirmInFlight || run.run_id === "run-a") && (
              <GraphReviewExtractPromoteSheet
                prepared={prepareResponse({
                  runId: "run-a",
                  proposalDigest: "digest-run-a",
                  proposalId: "prop-run-a",
                })}
                onClose={() => undefined}
                onConfirmInFlightChange={setConfirmInFlight}
              />
            )}
          </GraphReviewLiveStateProvider>
        </ProjectionProvider>
      );
    }

    render(<BindingRaceHarness />);

    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-merge-cta")).toHaveTextContent(
        "Merging…",
      );
    });

    fireEvent.click(screen.getByTestId("load-run-b"));
    await waitFor(() => {
      expect(screen.getByTestId("committed-binding-key")).toHaveTextContent(
        catalogRunBindingKey({
          runId: "run-b",
          campaignId: "longmont-c2",
          sessionId: "session-25",
        }),
      );
      expect(screen.getByTestId("committed-phase")).toHaveTextContent("candidate");
    });

    resolveConfirm(
      confirmReceipt({
        proposalId: "prop-run-a",
        proposalDigest: "digest-run-a",
        affectedObjectIds: ["object-1"],
      }),
    );

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-reload-error")).toHaveTextContent(
        /binding changed/i,
      );
    });

    expect(screen.getByTestId("committed-phase")).toHaveTextContent("candidate");
    expect(screen.getByTestId("committed-has-receipt")).toHaveTextContent("no");
    expect(screen.getByTestId("committed-receipt-digest")).toHaveTextContent("");
    expect(screen.getByTestId("committed-binding-key")).toHaveTextContent(
      catalogRunBindingKey({
        runId: "run-b",
        campaignId: "longmont-c2",
        sessionId: "session-25",
      }),
    );
    expect(postWorldGraphProjection).not.toHaveBeenCalled();
  });
});

describe("GraphReviewSessionToolbar", () => {
  beforeEach(() => {
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);
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
          <AgentInteractionProjectionTestHost config={createIngestSurfaceConfig(planContext)}>
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
          </AgentInteractionProjectionTestHost>
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

  it("hides prepare after a terminal committed receipt for the binding", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({ affectedObjectIds: ["object-1"] }),
    );
    vi.mocked(postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:committed",
        headRevisionId: "rev:committed",
        isHead: true,
        focus: { kind: "session", sessionId: "session-25", campaignId: "longmont-c2" },
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
      nodes: [
        {
          nodeId: "object-1",
          label: "Hesta Ironroot",
          kind: "npc",
          role: "character",
          aliases: [],
          sourceDomains: [],
          anchoredToFocusSession: true,
          evidenceBadges: [],
          adjacency: [],
          suggestedExpansions: [],
          evidenceRefIds: [],
          sourceArtifactIds: [],
        },
      ],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });

    renderWithLiveRun(
      baseRun(),
      <>
        <GraphReviewSessionToolbar />
        <GraphReviewExtractPromoteSheet
          prepared={prepareResponse()}
          onClose={() => undefined}
        />
      </>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-review-and-merge")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(
        screen.getByTestId("graph-review-committed-prepare-suppressed"),
      ).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-review-and-merge")).toBeNull();
  });

  it("preserves terminal receipt when prepared/binding adoption validation fails and keeps prepare hidden", async () => {
    vi.mocked(extractPromoteApi.confirmExtractPromote).mockResolvedValue(
      confirmReceipt({
        proposalDigest: "digest-mismatch",
        affectedObjectIds: ["object-1"],
      }),
    );
    vi.mocked(postWorldGraphProjection).mockClear();

    function AuthorityProbe() {
      const { committedPhase, committedReceipt, committedError } = useGraphReviewLiveState();
      return (
        <>
          <span data-testid="committed-phase">{committedPhase}</span>
          <span data-testid="committed-has-receipt">
            {committedReceipt ? "yes" : "no"}
          </span>
          <span data-testid="committed-error">{committedError ?? ""}</span>
        </>
      );
    }

    renderWithLiveRun(
      baseRun(),
      <>
        <AuthorityProbe />
        <GraphReviewSessionToolbar />
        <GraphReviewExtractPromoteSheet
          prepared={prepareResponse()}
          onClose={() => undefined}
        />
      </>,
    );

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-review-and-merge")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("committed-has-receipt")).toHaveTextContent("yes");
      expect(screen.getByTestId("committed-phase")).toHaveTextContent("error");
    });
    expect(screen.getByTestId("committed-error")).toHaveTextContent(
      /proposalDigest does not match the prepared proposal/i,
    );
    expect(postWorldGraphProjection).not.toHaveBeenCalled();
    expect(
      screen.getByTestId("graph-review-committed-prepare-suppressed"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-review-and-merge")).toBeNull();
    expect(screen.queryByTestId("graph-review-extract-promote-merge-cta")).toBeNull();
    expect(screen.queryByTestId("graph-review-extract-promote-retry-exact-confirm")).toBeNull();
  });
});
