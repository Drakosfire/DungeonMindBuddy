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

  it("prepares promotion with exact runId only", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
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
      runId: "extraction-run-wb-1",
      campaignId: "longmont-c2",
      sessionId: null,
    });

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-prepare")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId("graph-review-exact-run-prepare"));
    await waitFor(() => {
      expect(prepare).toHaveBeenCalledWith({ runId: "extraction-run-wb-1" });
    });
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

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-unreviewable")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });
});
