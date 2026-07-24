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

  it("prepares promotion with exact runId only", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();
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
    mockExactRunReviewPackage();

    render(<GraphReviewWorkbenchModule context={context} />);
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-unreviewable")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("Load recap clears exact-run mode and removes handoff query params", async () => {
    const sessionRun = {
      manifest_path: "artifacts/run-a/manifest.json",
      run_dir: "artifacts/run-a",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      status: "preview_union_store_ready",
      updated_at: null,
      created_at: null,
      preview_union_store_path: "artifacts/run-a/preview-union.json",
      preview_union_store_valid: true,
      node_count: 2,
      edge_count: 1,
      evidence_ref_count: 1,
      next_actions: [],
      run_id: "run-a",
      run_label: "Run A",
      generated_at: null,
      model_id: null,
      model_provider: null,
      extraction_profile: "baseline",
      extraction_mode: null,
      vocabulary_mode: "node",
      runner_options_summary: {},
      diagnostics_summary: {},
      preview_union_available: true,
    };
    vi.spyOn(liveApi, "getGraphIngestRuns").mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "0.1",
      runs: [sessionRun],
    });
    vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "0.1",
      sessions: [
        {
          session_id: "session-23",
          session_number: 23,
          campaign_id: "longmont-c2",
          gold_fixture_id: "gold-23",
          gold_manifest_path: "m23",
          gold_graph_path: "g23",
          gold_counts: { nodes: 2, edges: 1, evidence_refs: 1, beats: 0 },
          available_runs: [sessionRun],
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
    vi.spyOn(liveApi, "getGoldReviewCompare").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_compare_v1",
      version: "0.1",
      session_id: "session-23",
      campaign_id: "longmont-c2",
      gold_fixture_id: "gold-23",
      gold_manifest_path: "m23",
      gold_graph_path: "g23",
      live_run: null,
      comparison: {
        scores: {
          node_recall: 0,
          edge_recall: 0,
          beat_recall: 0,
          proposed_write_recall: 0,
        },
        coverage: {
          missing_gold_nodes: [],
          gold_nodes_total: 0,
          candidate_nodes_total: 0,
          matched_nodes: [],
        },
        soft_misses: [],
      },
      object_index: { gold: {}, live: {} },
      match_pairs: {},
    });
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue({
      campaign_id: "longmont-c2",
      session_id: "session-23",
      graph_id: "graph-a",
      markdown: "Recap prose after load",
      focus: {
        focus_session_id: "session-23",
        focused_evidence_ref_ids: [],
        focused_edge_ids: [],
        focused_node_ids: [],
      },
      node_views: {},
      source_spans: [],
      mentions: [],
    });
    vi.spyOn(liveApi, "getGoldGraphProjection").mockResolvedValue({
      campaign_id: "longmont-c2",
      session_id: "session-23",
      graph_id: "gold-graph",
      markdown: "Gold prose",
      focus: {
        focus_session_id: "session-23",
        focused_evidence_ref_ids: [],
        focused_edge_ids: [],
        focused_node_ids: [],
      },
      node_views: {},
      source_spans: [],
      mentions: [],
      source_kind: "gold_fixture",
      gold_fixture_id: "gold-23",
      gold_fixture_relpath: "gold/session-23.json",
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
