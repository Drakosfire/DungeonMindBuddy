import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import * as liveApi from "../../api/liveApi";
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import type { PlanContextDescriptor } from "../types";
import { createSurfaceInformationChannel } from "../../surfaceInformation";
import type { ExtractionRunCatalogResponse } from "../../ingestSurface/ingestRunCatalogApi";
import type { ExactRunReviewPackage, RecapEvidenceCorrectionResponse, ExtractionRunRecord, WorldContainerRecord } from "../../api/types";
import {
  INGEST_RUN_CATALOG_DESCRIPTOR,
  mapIngestRunCatalogObservation,
} from "../../ingestSurface/ingestRunCatalogSurfaceInformation";
import { GraphReviewWorkbenchModule } from "./GraphReviewWorkbenchModule";
import { SelectedWorldProvider } from "../../selectedWorld/SelectedWorldContext";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  ingestSession: 23,
  headerLabel: "Ingest",
};

const managedWorlds: WorldContainerRecord[] = [
  {
    schema_version: "dmb_world_container_record_v1",
    world_id: "managed-world-a",
    name: "World A",
    source_root_relpath: "corpus/managed-world-a-markdown",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    schema_version: "dmb_world_container_record_v1",
    world_id: "managed-world-b",
    name: "World B",
    source_root_relpath: "corpus/managed-world-b-markdown",
    created_at: "2026-01-01T00:00:00Z",
  },
];

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

function readyCatalogChannel(runs: ExtractionRunRecord[] = []) {
  const channel = createSurfaceInformationChannel<ExtractionRunCatalogResponse>(
    INGEST_RUN_CATALOG_DESCRIPTOR,
  );
  const ticket = channel.beginObservation();
  if (ticket) {
    channel.commit(
      ticket,
      mapIngestRunCatalogObservation({
        response: { schema_version: "dmb_extraction_run_catalog_v1", runs },
      }),
    );
  }
  return channel;
}

function mockCatalogApis() {
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

// The app projection host owns projection state; mounting the workbench
// requires the provider exactly as production composition does.
function renderModule(
  runs: ExtractionRunRecord[] = [],
  selectedWorldId: string | null = "managed-world-a",
) {
  const workbench = (
    <AgentInteractionProvider>
      <GraphReviewWorkbenchModule
        context={context}
        catalogChannel={readyCatalogChannel(runs)}
        onCatalogRefresh={() => undefined}
      />
    </AgentInteractionProvider>
  );
  return render(
    selectedWorldId
      ? <SelectedWorldProvider locationSnapshot={`/ingest?world=${selectedWorldId}`}>{workbench}</SelectedWorldProvider>
      : workbench,
  );
}

describe("GraphReviewGenericRun", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({
      schema_version: "dmb_world_container_registry_v1",
      records: managedWorlds,
    }), { headers: { "Content-Type": "application/json" } }));
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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();

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

    renderModule();
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-not-promotable")).toBeInTheDocument();
    });
    expect(screen.getByTestId("graph-review-exact-run-not-promotable")).toHaveTextContent(
      /inspect-only/i,
    );
    expect(screen.getByText("Read-only")).toBeInTheDocument();
    expect(screen.getByText("Advanced details")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-first-world-publish-sheet")).not.toBeInTheDocument();
    expect(prepare).not.toHaveBeenCalled();
  });

  it("shows first-world publish sheet for eligible worldbuilding runs", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage({
      ...reviewPackage,
      worldId: "the-glass-orchard",
      worldState: "uninitialized",
      firstWorldPublishEligible: true,
      firstWorldPublishReason: null,
    });
    const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote");
    const firstWorldPrepare = vi.spyOn(extractPromoteApi, "prepareFirstWorldGraph");

    renderModule();
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-first-world-publish-sheet")).toBeInTheDocument();
    });
    expect(screen.getByText(/The Glass Orchard/i)).toBeInTheDocument();
    expect(screen.getByTestId("graph-review-first-world-create-cta")).toBeInTheDocument();
    expect(screen.queryByText("Read-only")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-not-promotable")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
    expect(prepare).not.toHaveBeenCalled();
    expect(firstWorldPrepare).not.toHaveBeenCalled();
  });

  it("requires a verified managed World before preparing a promotable recap run", async () => {
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

    const legacyView = renderModule([], null);
    const legacyPrepareButton = await screen.findByTestId("graph-review-exact-run-prepare");
    expect(legacyPrepareButton).toBeDisabled();
    expect(screen.getByTestId("graph-review-selected-world-guidance")).toHaveTextContent(
      "Select a verified managed World",
    );
    expect(prepare).not.toHaveBeenCalled();

    legacyView.unmount();
    renderModule();
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-prepare")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByTestId("graph-review-exact-run-prepare"));
    await waitFor(() => {
      expect(prepare).toHaveBeenCalledWith({
        runId: "extraction-run-recap-1",
        managedWorldId: "managed-world-a",
      });
    });
  });

  it("ignores an exact-run prepare response after switching to another managed World", async () => {
    const user = userEvent.setup();
    mockCatalogApis();
    const recapRun = {
      ...exactRun,
      run_id: "extraction-run-world-switch",
      source_artifact_id: "artifact:recap:longmont-c2:session-22:abcdef123456",
      source_domain: "recap" as const,
      session_id: "session-22",
    };
    const recapReview = {
      ...reviewPackage,
      runId: recapRun.run_id,
      sourceDomain: "recap",
      sourceArtifactId: recapRun.source_artifact_id,
      sessionId: recapRun.session_id,
      promotable: true,
      promotableReason: null,
    };
    window.history.replaceState(
      {},
      "",
      `/ingest?extractionRunId=${recapRun.run_id}`
        + "&sourceArtifactId=artifact:recap:longmont-c2:session-22:abcdef123456",
    );
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(recapRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({
      ...buildContext,
      run: recapRun,
      source_artifact_id: recapRun.source_artifact_id,
      graph_review_handoff: {
        ...buildContext.graph_review_handoff,
        href:
          `/ingest?extractionRunId=${recapRun.run_id}`
          + "&sourceArtifactId=artifact:recap:longmont-c2:session-22:abcdef123456",
        extraction_run_id: recapRun.run_id,
        source_artifact_id: recapRun.source_artifact_id,
      },
    });
    mockExactRunReviewPackage(recapReview);
    let resolvePrepare!: (value: Awaited<ReturnType<typeof extractPromoteApi.prepareExtractPromote>>) => void;
    const pending = new Promise<Awaited<ReturnType<typeof extractPromoteApi.prepareExtractPromote>>>(
      (resolve) => { resolvePrepare = resolve; },
    );
    const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote").mockReturnValue(pending);

    function SwitchableWorldWorkbench() {
      const [worldId, setWorldId] = useState("managed-world-a");
      return (
        <>
          <button type="button" data-testid="switch-managed-world" onClick={() => setWorldId("managed-world-b")}>
            Switch World
          </button>
          <SelectedWorldProvider locationSnapshot={`/ingest?world=${worldId}`}>
            <AgentInteractionProvider>
              <GraphReviewWorkbenchModule
                context={context}
                catalogChannel={readyCatalogChannel([])}
                onCatalogRefresh={() => undefined}
              />
            </AgentInteractionProvider>
          </SelectedWorldProvider>
        </>
      );
    }

    render(<SwitchableWorldWorkbench />);
    const prepareButton = await screen.findByTestId("graph-review-exact-run-prepare");
    await waitFor(() => expect(prepareButton).not.toBeDisabled());
    await user.click(prepareButton);
    expect(prepare).toHaveBeenCalledWith({
      runId: recapRun.run_id,
      managedWorldId: "managed-world-a",
    });

    await user.click(screen.getByTestId("switch-managed-world"));
    await waitFor(() => expect(prepareButton).not.toBeDisabled());

    await resolvePrepare({
      schema: "dmb_extract_promote_prepare_v1",
      proposalId: "proposal-for-world-a",
      proposalDigest: "digest-world-a",
      parentRevisionId: "revision-world-a",
      worldId: "native-world-a",
      acceptedProposalsCount: 1,
      unresolvedMentionsCount: 0,
      rejectedAssertionsCount: 0,
      reviewPackage: { effect: { world_id: "native-world-a" } },
      reviewItems: [],
      reviewSummary: {
        newObjectCount: 1,
        connectExistingCount: 0,
        relationshipCount: 0,
        unresolvedMentionCount: 0,
        rejectedAssertionCount: 0,
      },
      runId: recapRun.run_id,
      campaignId: "longmont-c2",
      sessionId: "session-22",
    });

    await waitFor(() => {
      expect(screen.queryByTestId("graph-review-extract-promote-sheet")).not.toBeInTheDocument();
    });
    expect(screen.queryByText(/digest-world-a/)).not.toBeInTheDocument();
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

    renderModule();
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

    renderModule();
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-unreviewable")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("keeps exact-run review primary without Load recap tooling", async () => {
    mockCatalogApis();
    vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(exactRun);
    vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue(buildContext);
    mockExactRunReviewPackage();

    renderModule();
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-banner")).toBeInTheDocument();
    });

    expect(screen.queryByRole("button", { name: "Load recap" })).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-review-exact-run-panel")).toBeInTheDocument();
    expect(screen.queryByLabelText("Published recap")).not.toBeInTheDocument();
    expect(window.location.search).toContain("extractionRunId=extraction-run-wb-1");
  });
});


const sha = (letter: string) => letter.repeat(64);
function recapFixture() {
  const parent: ExtractionRunRecord = {
    ...exactRun, run_id: "recap-parent", source_domain: "recap", session_id: "session-29",
    source_artifact_id: "artifact:recap:session-29", profile_id: "recap_category_v1@1.0",
    components: Object.fromEntries(["candidate_graph", "source_artifact", "source_span_index"].map((kind, index) => [kind, {
      kind, uri: `frozen/${kind}`, exists: true, sha256: sha(["a", "b", "c"][index]),
    }])),
  };
  const review: ExactRunReviewPackage = {
    ...reviewPackage, runId: parent.run_id, sourceDomain: "recap", sourceArtifactId: parent.source_artifact_id,
    sessionId: parent.session_id, sourceRevisionId: sha("b"), inspectionStatus: "invalid_evidence", invalidEvidenceCount: 1,
    assertions: [{ assertionId: "tunnel", kind: "object", label: "Tunnel", summary: "Tunnel under field", evidence: [{
      sourceArtifactId: parent.source_artifact_id, sourceSpanRefId: "span:39", paragraphText: "like the one they discovered in the tunnel under the field",
      anchorQuotes: ["the like of which they discovered in the tunnel under the field"],
      invalidAnchorQuotes: ["the like of which they discovered in the tunnel under the field"],
    }] }],
  };
  const receipt: RecapEvidenceCorrectionResponse = {
    schema: "dmb_recap_evidence_correction_response_v1", runId: "recap-child", parentRunId: parent.run_id,
    parentCandidateSha256: sha("a"), candidateSha256: sha("d"), correctionDigest: sha("e"), status: "reviewable",
    semanticState: "held", semanticBasisSha256: sha("f"),
  };
  const child: ExtractionRunRecord = {
    ...parent, run_id: receipt.runId, components: { ...parent.components, candidate_graph: { ...parent.components!.candidate_graph, sha256: sha("d") } },
    lineage: { derivation: "operator_recap_literal_evidence_correction_v1", parent_run_id: parent.run_id,
      parent_candidate_sha256: sha("a"), correction_digest: sha("e"), semantic_disposition: { version: 1, state: "held", basis_sha256: sha("f") } },
  };
  const childReview: ExactRunReviewPackage = { ...review, runId: child.run_id, derivedFromRunId: parent.run_id, inspectionStatus: "ready", assertions: [] };
  return { parent, review, receipt, child, childReview };
}
function pendingValue<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
function setupRecap() {
  const f = recapFixture(); mockCatalogApis();
  window.history.replaceState({}, "", "/ingest?world=managed-world-a&extractionRunId=recap-parent");
  const runs = vi.spyOn(liveApi, "getExtractionRun").mockImplementation(async id => id === f.child.run_id ? f.child : f.parent);
  vi.spyOn(liveApi, "getExtractionRunStatus").mockResolvedValue({ ...buildContext, run: f.parent });
  const reviews = vi.spyOn(extractPromoteApi, "getExactRunReviewPackage").mockImplementation(async id => id === f.child.run_id ? f.childReview : f.review);
  const save = vi.spyOn(extractPromoteApi, "correctRecapRunEvidence").mockResolvedValue(f.receipt);
  const prepare = vi.spyOn(extractPromoteApi, "prepareExtractPromote");
  return { ...f, runs, reviews, save, prepare };
}
function recapWorkbench(search = "?world=managed-world-a&extractionRunId=recap-parent", changed = vi.fn()) {
  return <SelectedWorldProvider locationSnapshot="/ingest?world=managed-world-a"><AgentInteractionProvider>
    <GraphReviewWorkbenchModule context={context} catalogChannel={readyCatalogChannel()} onCatalogRefresh={() => undefined}
      sourceReviewOnly sourceReviewRunId="recap-parent" locationSearch={search} onLocationSearchChange={changed} />
  </AgentInteractionProvider></SelectedWorldProvider>;
}
async function previewRecap(user: ReturnType<typeof userEvent.setup>, replacement = "LIKE THE ONE they discovered") {
  const field = await screen.findByRole("textbox", { name: /Literal replacement for Tunnel/ });
  await user.type(field, replacement);
  await user.click(screen.getByRole("button", { name: "Preview quote corrections" }));
  return field;
}

describe("recap quote correction owning UI", () => {
  beforeEach(() => {
    vi.restoreAllMocks(); window.sessionStorage.clear();
    vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ schema_version: "dmb_world_container_registry_v1", records: managedWorlds }));
  });
  afterEach(() => { window.sessionStorage.clear(); window.history.replaceState({}, "", "/"); });

  it.each(["held", "accepted", "rejected"] as const)("previews locally, saves once and keeps %s child source-only", async state => {
    const user = userEvent.setup(); const f = setupRecap(); f.receipt.semanticState = state;
    (f.child.lineage!.semantic_disposition as Record<string, unknown>).state = state;
    const changed = vi.fn(); const view = render(recapWorkbench(undefined, changed));
    const field = await screen.findByRole("textbox", { name: /Literal replacement for Tunnel/ });
    expect(screen.getByRole("button", { name: "Preview quote corrections" })).toBeDisabled();
    await user.type(field, f.review.assertions[0].evidence[0].anchorQuotes[0]);
    expect(screen.getByRole("button", { name: "Preview quote corrections" })).toBeDisabled();
    await user.clear(field); await user.type(field, "LIKE THE ONE they discovered");
    expect(f.save).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Preview quote corrections" }));
    expect(screen.getByRole("region", { name: "Preview quote corrections" })).toHaveTextContent("LIKE THE ONE");
    expect(f.save).not.toHaveBeenCalled();
    const post = pendingValue<RecapEvidenceCorrectionResponse>(); f.save.mockReturnValue(post.promise);
    const button = screen.getByRole("button", { name: "Save quote corrections" });
    fireEvent.submit(button.closest("form")!); fireEvent.submit(button.closest("form")!);
    expect(f.save).toHaveBeenCalledTimes(1);
    expect(f.save.mock.calls[0][0]).toMatchObject({ parentRunId: "recap-parent", parentCandidateSha256: sha("a"), corrections: [{
      assertionId: "tunnel", evidenceIndex: 0, quoteIndex: 0, sourceSpanRefId: "span:39", replacementQuote: "LIKE THE ONE they discovered",
    }] });
    await act(async () => { post.resolve(f.receipt); });
    await waitFor(() => expect(changed).toHaveBeenCalledWith(expect.stringContaining("extractionRunId=recap-child")));
    view.rerender(recapWorkbench("?world=managed-world-a&extractionRunId=recap-child", changed));
    expect(await screen.findByText(new RegExp(`Semantic review state: ${state}`))).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
    expect(f.prepare).not.toHaveBeenCalled(); expect(window.sessionStorage.length).toBe(0);
    view.unmount(); render(recapWorkbench("?world=managed-world-a&extractionRunId=recap-child"));
    expect(await screen.findByText(new RegExp(`Semantic review state: ${state}`))).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-exact-run-prepare")).not.toBeInTheDocument();
  });

  it("recovers frozen bytes after lost response and reload without using a newer draft", async () => {
    const user = userEvent.setup(); const f = setupRecap(); f.save.mockRejectedValueOnce(new TypeError("lost response"));
    const view = render(recapWorkbench()); await previewRecap(user);
    await user.click(screen.getByRole("button", { name: "Save quote corrections" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("lost response");
    const frozen = structuredClone(f.save.mock.calls[0][0]);
    expect(screen.getByRole("textbox", { name: /Literal replacement/ })).toBeDisabled();
    expect(f.save).toHaveBeenCalledTimes(1);
    view.unmount(); render(recapWorkbench());
    await user.click(await screen.findByRole("button", { name: "Retry saved quote corrections" }));
    await waitFor(() => expect(f.save).toHaveBeenCalledTimes(2));
    expect(f.save.mock.calls[1][0]).toEqual(frozen);
    await waitFor(() => expect(window.location.search).toContain("extractionRunId=recap-child"));
  });

  it.each(["parent", "candidate", "source", "span", "package", "missing-candidate", "GET403", "GET404"])("retains recovery and refuses a child with %s mismatch", async fault => {
    const user = userEvent.setup(); const f = setupRecap();
    if (fault === "parent") f.child.lineage!.parent_run_id = "another-parent";
    if (fault === "candidate") f.child.components!.candidate_graph.sha256 = sha("9");
    if (fault === "source") f.child.components = { ...f.child.components, source_artifact: { ...f.child.components!.source_artifact, uri: "wrong" } };
    if (fault === "span") f.child.components = { ...f.child.components, source_span_index: { ...f.child.components!.source_span_index, sha256: sha("9") } };
    if (fault === "package") f.childReview.runId = "wrong";
    if (fault === "missing-candidate") f.child.components!.candidate_graph.exists = false;
    if (fault.startsWith("GET")) f.runs.mockImplementation(async id => { if (id === "recap-child") throw new Error(fault); return f.parent; });
    const changed = vi.fn(); render(recapWorkbench(undefined, changed)); await previewRecap(user);
    await user.click(screen.getByRole("button", { name: "Save quote corrections" }));
    await screen.findByRole("alert");
    expect(changed).not.toHaveBeenCalled(); expect(window.location.search).toContain("recap-parent");
    expect(screen.getByRole("button", { name: "Retry saved quote corrections" })).toBeEnabled();
    expect(f.prepare).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Retry saved quote corrections" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry saved quote corrections" })).toBeEnabled());
    expect(f.save).toHaveBeenCalledTimes(1);
  });

  it.each(["POST", "child GET"])("fences stale %s completion across A → B → A", async stage => {
    const user = userEvent.setup(); const f = setupRecap(); const changed = vi.fn();
    const post = pendingValue<RecapEvidenceCorrectionResponse>(); const childRead = pendingValue<ExtractionRunRecord>();
    if (stage === "POST") f.save.mockReturnValue(post.promise);
    else f.runs.mockImplementation(async id => id === "recap-child" ? childRead.promise : f.parent);
    const view = render(recapWorkbench(undefined, changed)); await previewRecap(user);
    await user.click(screen.getByRole("button", { name: "Save quote corrections" }));
    if (stage === "child GET") await waitFor(() => expect(f.runs).toHaveBeenCalledWith("recap-child"));
    view.rerender(recapWorkbench("?extractionRunId=other-run", changed)); await act(async () => {});
    view.rerender(recapWorkbench(undefined, changed));
    await act(async () => { if (stage === "POST") post.resolve(f.receipt); else childRead.resolve(f.child); });
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry saved quote corrections" })).toBeEnabled());
    expect(changed).not.toHaveBeenCalled(); expect(f.save).toHaveBeenCalledTimes(1);
    expect(window.location.search).toContain("recap-parent");
  });
});


it("preserves the existing worldbuilding correction action", async () => {
  vi.restoreAllMocks(); mockCatalogApis();
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ records: managedWorlds }));
  const f = recapFixture();
  const run = { ...f.parent, run_id: "worldbuilding-parent", source_domain: "worldbuilding", profile_id: "worldbuilding_shepherds_flock_v0@0.1" };
  const review = { ...f.review, runId: run.run_id, sourceDomain: "worldbuilding" };
  window.history.replaceState({}, "", "/ingest?extractionRunId=worldbuilding-parent");
  vi.spyOn(liveApi, "getExtractionRun").mockResolvedValue(run);
  vi.spyOn(extractPromoteApi, "getExactRunReviewPackage").mockResolvedValue(review);
  const correction = vi.spyOn(extractPromoteApi, "correctExactRunEvidence").mockImplementation(() => new Promise(() => {}));
  const recap = vi.spyOn(extractPromoteApi, "correctRecapRunEvidence");
  renderModule(); const user = userEvent.setup();
  await user.type(await screen.findByRole("textbox", { name: /Literal replacement/ }), "literal words");
  await user.click(screen.getByRole("button", { name: "Create reviewed child candidate" }));
  expect(correction).toHaveBeenCalledTimes(1); expect(recap).not.toHaveBeenCalled();
});
