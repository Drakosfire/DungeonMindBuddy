import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import * as liveApi from "../../api/liveApi";
import type { PlanContextDescriptor } from "../types";
import { GraphReviewWorkbenchModule } from "./GraphReviewWorkbenchModule";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  ingestSession: 23,
  headerLabel: "Ingest",
};

const exactRun = {
  schema_version: "dmb_extraction_run_v1" as const,
  version: "1.0",
  run_id: "extraction-run-wb-1",
  source_artifact_id: "artifact:worldbuilding:doc:r1:abcdef123456",
  source_domain: "worldbuilding",
  status: "reviewable" as const,
  campaign_id: "longmont-c2",
  session_id: null,
  profile_id: "worldbuilding_plumbing_v0@0.1",
  components: {
    candidate_graph: {
      kind: "candidate_graph",
      uri: "out/graph_memory/runs/extraction/wb1/candidate_graph.json",
      exists: true,
    },
  },
};

const buildContext = {
  schema_version: "dmb_extraction_run_status_v1" as const,
  run: exactRun,
  source_artifact_id: exactRun.source_artifact_id,
  document_id: "doc-1",
  document_revision: 3,
  source_content_sha256: "sha256:abc",
  graph_review_handoff: {
    href:
      "/ingest?extractionRunId=extraction-run-wb-1"
      + "&sourceArtifactId=artifact:worldbuilding:doc:r1:abcdef123456"
      + "&documentId=doc-1&revision=3",
    extraction_run_id: exactRun.run_id,
    source_artifact_id: exactRun.source_artifact_id,
    document_id: "doc-1",
    document_revision: 3,
  },
};

const reviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1" as const,
  runId: exactRun.run_id,
  sourceDomain: "worldbuilding",
  sourceArtifactId: exactRun.source_artifact_id,
  sourceRevisionId: "sha256:abc",
  campaignId: "longmont-c2",
  sessionId: null,
  sourceProse: "# Lore\n\nWorldbuilding source for promote.\n\nA second paragraph.\n",
  assertions: [
    {
      assertionId: "obj_session22_vial",
      kind: "object" as const,
      label: "vial",
      summary: "Puddle sample vial",
      evidence: [
        {
          sourceArtifactId: exactRun.source_artifact_id,
          sourceSpanRefId: "span:worldbuilding:abc:p1",
          paragraphText: "Worldbuilding source for promote.",
          anchorQuotes: ["Worldbuilding source for promote."],
          startLine: 3,
          endLine: 3,
        },
      ],
    },
  ],
  diagnostics: [],
  promotable: false,
  promotableReason:
    "Worldbuilding ExtractionRuns are inspect-only in this slice. "
    + "Assertions stamped worldbuilding_draft are not eligible for World Graph "
    + "prepare/confirm until an approved authority-elevation contract lands.",
};

function mockCatalogApis() {
  vi.spyOn(liveApi, "getGraphIngestRuns").mockResolvedValue({
    schema_version: "dmb_graph_ingest_run_registry_v1",
    version: "0.1",
    runs: [],
  });
  vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
    schema_version: "dmb_graph_gold_review_sessions_v1",
    version: "0.1",
    sessions: [],
  });
  vi.spyOn(liveApi, "getManualReviewBeds").mockResolvedValue({
    schema_version: "dmb_graph_manual_review_beds_v1",
    version: "0.1",
    beds: [],
  });
}

function mockExactRunReviewPackage(
  packageResponse: typeof reviewPackage = reviewPackage,
) {
  return vi
    .spyOn(extractPromoteApi, "getExactRunReviewPackage")
    .mockResolvedValue(packageResponse);
}

describe("GraphReviewGenericRun", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState(
      {},
      "",
      "/ingest?extractionRunId=extraction-run-wb-1"
        + "&sourceArtifactId=artifact:worldbuilding:doc:r1:abcdef123456"
        + "&documentId=doc-1&revision=3",
    );
  });

  afterEach(() => {
    window.history.replaceState({}, "", "/");
  });

  it("loads exact worldbuilding run without inventing a session lens", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("graph-review-exact-run-scope")).toHaveTextContent(
      "campaign longmont-c2 · no session",
    );
    expect(screen.getByTestId("graph-review-exact-run-banner")).toHaveTextContent(
      "doc doc-1 r3",
    );
    expect(screen.queryByText(/session-23/i)).not.toBeInTheDocument();
    expect(liveApi.getExtractionRun).toHaveBeenCalledWith("extraction-run-wb-1");
    expect(liveApi.getExtractionRun).toHaveBeenCalledTimes(1);
  });

  it("does not inherit Plan context campaign for a campaignless exact run", async () => {
    mockCatalogApis();
    const campaignlessRun = { ...exactRun, campaign_id: null };
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(campaignlessRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      run: campaignlessRun,
    });
    mockExactRunReviewPackage({
      ...reviewPackage,
      campaignId: null,
    });

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-scope")).toHaveTextContent(
        "world / source authority · no session",
      );
    });
    expect(screen.getByTestId("graph-review-exact-run-scope")).not.toHaveTextContent(
      "longmont-c2",
    );
  });

  it("rejects a review package whose SourceArtifact disagrees with the loaded run", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage({
      ...reviewPackage,
      sourceArtifactId: "artifact:worldbuilding:other",
    });

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-review-error")).toHaveTextContent(
        "exact-run review package identity does not match the loaded ExtractionRun",
      );
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("displays canonical source prose and assertion evidence for the exact run", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-source-prose")).toHaveTextContent(
        "Worldbuilding source for promote.",
      );
    });
    expect(screen.getByTestId("graph-review-exact-run-evidence-paragraph")).toHaveTextContent(
      "Worldbuilding source for promote.",
    );
    expect(screen.getByTestId("graph-review-exact-run-evidence-quote")).toHaveTextContent(
      "Worldbuilding source for promote.",
    );
    await userEvent.click(screen.getByTestId("graph-review-exact-run-assertion-obj_session22_vial"));
    expect(screen.getByTestId("graph-review-exact-run-evidence")).toHaveAttribute(
      "data-assertion-id",
      "obj_session22_vial",
    );
  });

  it("rejects a handoff whose document lineage the server does not confirm", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      document_revision: 4,
    });

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-error")).toHaveTextContent(
        "handoff document lineage does not match the server-resolved run",
      );
    });
    expect(screen.queryByTestId("graph-review-exact-run-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("fails closed when claimed document lineage cannot be verified", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockRejectedValue(
      new Error("build context unavailable"),
    );

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-error")).toHaveTextContent(
        "handoff document lineage could not be verified",
      );
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("loads a recap handoff that claims no workspace lineage", async () => {
    mockCatalogApis();
    window.history.replaceState({}, "", "/ingest?extractionRunId=recap-run-1");
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue({
      ...exactRun,
      run_id: "recap-run-1",
      source_domain: "recap",
      campaign_id: "longmont-c2",
      session_id: "session-22",
    });
    mockExactRunReviewPackage({
      ...reviewPackage,
      runId: "recap-run-1",
      sourceDomain: "recap",
      sessionId: "session-22",
    });
    const buildContextSpy = vi.spyOn(liveApi, "getExtractionRunStatus");

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-scope")).toHaveTextContent(
        "campaign longmont-c2 · session session-22",
      );
    });
    expect(screen.getByTestId("graph-review-exact-run-banner")).not.toHaveTextContent("doc ");
    expect(buildContextSpy).not.toHaveBeenCalled();
  });

  it("rejects a duplicated run identifier before calling any run API", async () => {
    mockCatalogApis();
    window.history.replaceState(
      {},
      "",
      "/ingest?extractionRunId=run-a&extractionRunId=run-b",
    );
    const getRun = vi.spyOn(liveApi, "getExtractionRun");

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-error")).toHaveTextContent(
        "extractionRunId must appear at most once",
      );
    });
    expect(getRun).not.toHaveBeenCalled();
  });

  it("rejects latest-run style handoff identifiers", async () => {
    mockCatalogApis();
    window.history.replaceState({}, "", "/ingest?extractionRunId=latest");
    const getRun = vi.spyOn(liveApi, "getExtractionRun");

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-error")).toHaveTextContent(
        'extractionRunId must be an exact identifier, not "latest"',
      );
    });
    expect(getRun).not.toHaveBeenCalled();
  });

  it("shows inspect-only state for worldbuilding runs without merge action", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();
    const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote");

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-not-promotable")).toBeInTheDocument();
    });
    expect(screen.getByTestId("graph-review-exact-run-not-promotable")).toHaveTextContent(
      /inspect-only/i,
    );
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
    expect(prepare).not.toHaveBeenCalled();
  });

  it("prepares promotion with exact runId only for promotable recap runs", async () => {
    mockCatalogApis();
    const recapRun = {
      ...exactRun,
      run_id: "extraction-run-recap-1",
      source_artifact_id: "artifact:recap:longmont-c2:session-22:abcdef123456",
      source_domain: "recap",
      session_id: "session-22",
      profile_id: "recap_extraction_v0@0.1",
    };
    const recapReview = {
      ...reviewPackage,
      runId: recapRun.run_id,
      sourceDomain: "recap",
      sourceArtifactId: recapRun.source_artifact_id,
      sessionId: "session-22",
      promotable: true,
      promotableReason: null,
    };
    window.history.replaceState(
      {},
      "",
      "/ingest?extractionRunId=extraction-run-recap-1"
        + "&sourceArtifactId=artifact:recap:longmont-c2:session-22:abcdef123456"
        + "&documentId=doc-1&revision=3",
    );
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(recapRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      run: recapRun,
      source_artifact_id: recapRun.source_artifact_id,
      graph_review_handoff: {
        ...buildContext.graph_review_handoff,
        href:
          "/ingest?extractionRunId=extraction-run-recap-1"
          + "&sourceArtifactId=artifact:recap:longmont-c2:session-22:abcdef123456"
          + "&documentId=doc-1&revision=3",
        extraction_run_id: recapRun.run_id,
        source_artifact_id: recapRun.source_artifact_id,
      },
    });
    mockExactRunReviewPackage(recapReview);
    const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote").mockResolvedValue({
      schema: "dmb_extract_promote_prepare_v1",
      proposalId: "prop-1",
      proposalDigest: "digest-1",
      parentRevisionId: "rev:1",
      worldId: "eldyrwild",
      acceptedProposalsCount: 1,
      unresolvedMentionsCount: 0,
      rejectedAssertionsCount: 0,
      reviewPackage: { effect: {} },
      reviewItems: [
        {
          assertionId: "a1",
          sliceQualifiedId: "slice:a1",
          contributionSliceId: "slice",
          kind: "object",
          label: "Vial",
          summary: "sample",
          selectable: true,
          selectedByDefault: true,
          dependsOnAssertionIds: [],
          dependsOnSliceQualifiedIds: [],
          warnings: [],
        },
      ],
      reviewSummary: {
        newObjectCount: 1,
        connectExistingCount: 0,
        relationshipCount: 0,
        unresolvedMentionCount: 0,
        rejectedAssertionCount: 0,
      },
      runId: "extraction-run-recap-1",
      campaignId: "longmont-c2",
      sessionId: "session-22",
    });

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-prepare")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId("graph-review-exact-run-prepare"));
    await waitFor(() => {
      expect(prepare).toHaveBeenCalledWith({ runId: "extraction-run-recap-1" });
    });
  });

  it("campaignless worldbuilding exact-run stays inspect-only without campaign projection", async () => {
    mockCatalogApis();
    const campaignlessRun = { ...exactRun, campaign_id: null };
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(campaignlessRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      run: campaignlessRun,
    });
    mockExactRunReviewPackage({ ...reviewPackage, campaignId: null });
    const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote");
    const projectionSpy = vi.spyOn(liveApi, "postWorldGraphProjection");

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-not-promotable")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
    expect(prepare).not.toHaveBeenCalled();
    expect(projectionSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("graph-review-exact-run-scope")).toHaveTextContent(
      "world / source authority · no session",
    );
  });

  it("shows unreviewable state without prepare action", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue({
      ...exactRun,
      status: "prepared",
    });
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      run: { ...exactRun, status: "prepared" },
    });
    mockExactRunReviewPackage();

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-unreviewable")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("Load recap clears exact-run mode and removes handoff query params", async () => {
    vi.spyOn(liveApi, "getWorldGraphSessions").mockResolvedValue({
      schema_version: "dmb_world_graph_sessions_v1",
      version: "0.1",
      world_id: "eldyrwild",
      head_revision_id: "rev:test",
      sessions: [
        {
          world_id: "eldyrwild",
          campaign_id: "longmont-c2",
          session_id: "session-23",
          session_number: 23,
          contribution_count: 1,
          contribution_ids: ["contribution:test"],
          source_artifact_ids: ["artifact:recap:longmont-c2:session-23"],
          head_revision_id: "rev:test",
          recap_available: true,
          browseable: true,
        },
      ],
    });
    vi.spyOn(liveApi, "getManualReviewBeds").mockResolvedValue({
      schema_version: "dmb_graph_manual_review_beds_v1",
      version: "0.1",
      beds: [],
    });
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
      schema: "dmb_world_graph_recap_projection_v1",
      campaignId: "longmont-c2",
      sessionId: "session-23",
      graphId: "graph-a",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev:test",
        headRevisionId: "rev:test",
        isHead: true,
        focus: {
          kind: "session",
          sessionId: "session-23",
          campaignId: "longmont-c2",
        },
        admissibility: "gm",
        scopeMode: "campaign",
      },
      markdown: "Recap prose after load",
      focus: {
        focusSessionId: "session-23",
        focusedEvidenceRefIds: [],
        focusedEdgeIds: [],
        focusedNodeIds: [],
      },
      nodeViews: {},
      sourceSpans: [],
      mentions: [],
      diagnostics: [],
      trustBoundary: { canTrust: [], cannotTrust: [] },
    });

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-panel")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "Load recap" }));
    await userEvent.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() => {
      expect(screen.queryByTestId("graph-review-exact-run-panel")).not.toBeInTheDocument();
    });
    expect(window.location.search).not.toContain("extractionRunId=");
    expect(window.location.search).not.toContain("sourceArtifactId=");
    expect(window.location.search).not.toContain("documentId=");
    expect(screen.queryByTestId("graph-review-exact-run-banner")).not.toBeInTheDocument();
  });
});
