import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import * as candidateApi from "../api/exactRunCandidateProjectionApi";
import type {ExactRunCandidateProjection} from "../api/exactRunCandidateProjectionApi";
import * as recapIngestApi from "../api/recapIngestApi";
import type { HistoricalRecapWorldProjectionResponse, RecapIngestStatus } from "../api/types";
import { mockCatalog, mockLayout, mockPlanView, mockState } from "../test/fixtures";
import { SurfaceShell } from "../surface/SurfaceShell";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import { IngestionModule } from "./IngestionModule";

vi.mock("../playSurface/review/SessionEvidencePicker",()=>({SessionEvidencePicker:({onChange}:{onChange:(refs:unknown[])=>void})=><button onClick={()=>onChange([{run_id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",review_revision:54,sha256:"a".repeat(64)}])}>Attach saved session evidence</button>}));

function makeStatus(overrides: Partial<RecapIngestStatus> = {}): RecapIngestStatus {
  const result: RecapIngestStatus = {
    schema: "dmb_raw_recap_ingest_status_v1",
    campaign_id: "longmont-c2",
    session: 22,
    status: "recap_applied",
    states: ["recap_applied", "normalized_created", "normalized_current"],
    paths: {
      canonical_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
      normalized_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
    },
    authority: {
      canonical_recap: "canon_play",
      normalized_recap: "canon_play_prepared",
    },
    warnings: [],
    errors: [],
    next_actions: [],
    ingest_report: {
      corpus_impact: [
        { key: "canonical_recap", relpath: "Session 22.md", exists: true },
        { key: "normalized_recap", relpath: "Session 22.md", exists: true },
      ],
    },
    entity_spelling_audit: [
      {
        canonical_guess: "Caelynn",
        variants: ["Caeylynn", "Caelynn"],
        action: "review_only",
      },
    ],
    ...overrides,
  };
  const hasNormalizedSourceState = result.states.some((state) =>
    ["recap_applied", "recap_reused", "normalized_created", "normalized_reused"].includes(state),
  );
  const lineageBlocked = result.states.some((state) =>
    ["normalized_stale", "normalized_provenance_unknown"].includes(state),
  );
  const proofRows = Array.isArray(result.ingest_report?.corpus_impact)
    ? result.ingest_report.corpus_impact.filter(
        (row): row is Record<string, unknown> => typeof row === "object" && row !== null,
      )
    : [];
  const canonicalConfirmed = proofRows.some(
    (row) => row.key === "canonical_recap" && row.exists === true,
  );
  const normalizedConfirmed = proofRows.some(
    (row) => row.key === "normalized_recap" && row.exists === true,
  );
  if (hasNormalizedSourceState && !lineageBlocked) {
    if (proofRows.length === 0 && !Object.prototype.hasOwnProperty.call(overrides.ingest_report ?? {}, "corpus_impact")) {
      result.ingest_report = {
        ...result.ingest_report,
        corpus_impact: [
          { key: "canonical_recap", relpath: result.paths.canonical_recap, exists: true },
          { key: "normalized_recap", relpath: result.paths.normalized_recap, exists: true },
        ],
      };
    }
    const hasCurrentProof =
      (proofRows.length === 0 && !Object.prototype.hasOwnProperty.call(overrides.ingest_report ?? {}, "corpus_impact")) ||
      (canonicalConfirmed && normalizedConfirmed);
    if (hasCurrentProof && !result.states.includes("normalized_current")) {
      result.states = [...result.states, "normalized_current"];
    }
  }
  return result;
}

function mockRecapIngestWithInspect(
  handler: (
    body: Parameters<typeof recapIngestApi.postRecapIngest>[0],
  ) => RecapIngestStatus | Promise<RecapIngestStatus>,
) {
  return vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
    if (body.operation === "inspect_status") {
      return makeStatus({
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      });
    }
    return handler(body);
  });
}

function historicalRecapProjectionForRun(runId: string): HistoricalRecapWorldProjectionResponse {
  const sessionNumber = Number(runId.match(/session-(\d+)/i)?.[1] ?? 22);
  const sessionId = `session-${sessionNumber}`;
  const sourceArtifactId = `artifact:recap:longmont-c2:${sessionId}`;
  const graphId = `fixture-world-head-${sessionNumber}`;
  const nodeId = "loc_mireward";
  return {
    ...session23WorldGraphRecapFixture,
    schema: "dmb_historical_recap_world_projection_v1",
    runId,
    runStatus: "candidate_validation_ready",
    sourceDomain: "recap",
    sourceArtifactId,
    sourceRevisionId: `source-revision-${sessionNumber}`,
    campaignId: "longmont-c2",
    sessionId,
    worldId: "world:elderwyld",
    managedWorldId: "elderwyld",
    bindingVersion: 3,
    sourceSha256: `sha256:${"a".repeat(64)}`,
    sourceStatus: "available",
    graphStatus: "available",
    graphId,
    markdown: `# Session ${sessionNumber} — Mireward Road\n\nThe party presses on near [Mireward](dmb-node:${nodeId}).`,
    focus: {
      focusSessionId: sessionId,
      focusedEvidenceRefIds: [],
      focusedEdgeIds: [],
      focusedNodeIds: [nodeId],
    },
    nodeViews: {
      [nodeId]: {
        nodeId,
        label: "Mireward",
        kind: "location",
        role: "place",
        aliases: ["Mireward"],
        sourceDomains: ["recap"],
        summary: "A road in the synthetic exact-run fixture.",
        anchoredToFocusSession: true,
        campaignScope: "longmont-c2",
        evidenceBadges: [],
        adjacency: [],
        suggestedExpansions: [],
        evidenceRefIds: [],
        sourceArtifactIds: [sourceArtifactId],
      },
    },
    mentions: [{
      mentionId: `mention:${sessionId}:mireward`,
      nodeId,
      label: "Mireward",
      startOffset: null,
      endOffset: null,
      evidenceRefIds: [],
    }],
    snapshot: {
      ...session23WorldGraphRecapFixture.snapshot,
      revisionId: graphId,
      headRevisionId: graphId,
      worldId: "world:elderwyld",
      focus: { kind: "session", campaignId: "longmont-c2", sessionId },
    },
  };
}

function candidateRecapProjectionForRun(runId: string): ExactRunCandidateProjection {
  const prior=historicalRecapProjectionForRun(runId);
  const key=`candidate:${runId}:${"c".repeat(64)}:${"d".repeat(64)}`;
  const source=prior.markdown.replace("[Mireward](dmb-node:loc_mireward)","Mireward");
  return {schema:"dmb_exact_run_candidate_projection_v1",trustBoundary:"unpublished_candidate",runId,runRevision:5,runStatus:"reviewable",profileId:"recap_category_v1@1.0",sourceDomain:"recap",
    sourceArtifactId:prior.sourceArtifactId,sourceRevisionId:prior.sourceSha256,sourceSha256:prior.sourceSha256,candidateSha256:"sha256:"+"c".repeat(64),spanIndexSha256:"sha256:"+"e".repeat(64),
    campaignId:prior.campaignId,sessionId:prior.sessionId,managedWorldId:"elderwyld",nativeWorldId:"world:elderwyld",bindingVersion:3,runWorldBindingStatus:"source_only",
    sourceMarkdown:source,narrativeMarkdown:source,projectedMarkdown:source.replace("Mireward.",`[Mireward](dmb-node:${key}).`),sourceDisplaySegments:[],
    nodes:[{viewKey:key,candidateNodeId:"loc_mireward",label:"Mireward",nodeType:"location",description:"Candidate-only place",confidence:"medium",semanticState:{},warnings:[],evidence:[]}],edges:[],
    nodeViews:{[key]:{node_id:key,label:"Mireward",kind:"candidate",role:"unpublished_candidate",aliases:[],source_domains:["recap"],evidence_badges:[],adjacency:[],anchored_to_focus_session:false}},
    sourceSpans:[],mentionsCount:1,unlinkedNodeCount:0,beatCount:0,diagnostics:[]};
}

function makeRecapArtifactRecord(campaignId: string, sessionNumber: number) {
  const sessionId = `session-${sessionNumber}`;
  return {
    schema_version: "dmb_recap_artifact_record_v1" as const,
    artifact_id: `artifact:recap:${campaignId}:${sessionId}`,
    campaign_id: campaignId,
    session_id: sessionId,
    source_recap_path: `corpus/${campaignId}/Session ${sessionNumber}.md`,
    run_bundle_uri: "bundle",
    run_manifest_uri: "manifest",
    source_span_index_uri: "index",
    graph_run_refs: [],
    default_projection_mode: "preview_union" as const,
    registered_at: "2026-06-29T00:00:00Z",
    updated_at: "2026-06-29T00:00:00Z",
    registry_source: "scan" as const,
  };
}

function makeRecapArtifactRegistry(records: ReturnType<typeof makeRecapArtifactRecord>[]) {
  return {
    schema_version: "dmb_recap_artifacts_registry_v1" as const,
    version: "1",
    records,
  };
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function setupIngestUser() {
  return userEvent.setup({ delay: null });
}

async function fillRecapInputs(
  user: ReturnType<typeof setupIngestUser>,
  rawText: string,
  sessionTitle: string,
) {
  const rawField = screen.getByLabelText("Write or paste a recap");
  await user.click(rawField);
  fireEvent.change(rawField, { target: { value: rawText } });

  const titleField = screen.getByLabelText("Session title");
  await user.click(titleField);
  fireEvent.change(titleField, { target: { value: sessionTitle } });
}

describe("IngestionModule", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    window.localStorage.clear();
    vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({ ...session23WorldGraphRecapFixture, campaignId: "longmont-c2", sessionId: "session-22", snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: { kind: "session", sessionId: "session-22", campaignId: "longmont-c2" } } });
    vi.spyOn(liveApi, "getHistoricalRecapWorldProjection").mockImplementation(async (runId) => historicalRecapProjectionForRun(runId));
    vi.spyOn(candidateApi, "getExactRunCandidateProjection").mockImplementation(async (runId) => candidateRecapProjectionForRun(runId));
    vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [],
    });
    vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (request) =>
      makeStatus({
        session: request.session,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("passes explicitly attached session refs separately from unchanged external recap text",async()=>{
    const user=setupIngestUser();
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async request=>makeStatus({session:30,status:"initialized",states:["ingest_status_inspected"],entity_spelling_audit:[]}));
    render(<IngestionModule campaignId="longmont-c2" session={30} managedWorldId="elderwyld" initialSourceSession={30}/>);
    await fillRecapInputs(user,"External authored recap stays exact.","Session 30 — Edge aftermath");
    await user.click(screen.getByRole("button",{name:"Attach saved session evidence"}));
    await waitFor(()=>expect(screen.getByRole("button",{name:"Process recap"})).toBeEnabled());
    await user.click(screen.getByRole("button",{name:"Process recap"}));
    await waitFor(()=>expect(recapIngestApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({operation:"generate_recap_memory",raw_text:"External authored recap stays exact.",session_evidence:[{run_id:"aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",review_revision:54,sha256:"a".repeat(64)}]})));
  });
  it("lets the operator choose the ingest campaign", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest");
    render(<IngestionModule campaignId="longmont-c2" session={24} />);

    const campaignPicker = await screen.findByLabelText("Campaign");
    expect(campaignPicker).toHaveValue("longmont-c2");

    await user.selectOptions(campaignPicker, "longmont-c1");
    expect(campaignPicker).toHaveValue("longmont-c1");
    expect(window.location.search).toContain("campaign=longmont-c1");
  });

  it("uses an explicit source session for a standalone recap entry", async () => {
    render(<IngestionModule campaignId="longmont-c2" session={29} initialSourceSession={29} />);
    expect(await screen.findByLabelText("Recap/source session")).toHaveValue(29);
  });

  it.each([
    {
      name: "a blank recap that has only been inspected",
      label: "Not run",
      result: makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }),
    },
    {
      name: "a saved recap with no graph preview",
      label: "Graph unavailable",
      result: makeStatus({
        session: 29,
        status: "recap_applied",
        states: ["recap_applied", "normalized_current"],
        entity_spelling_audit: [],
      }),
    },
    {
      name: "a run whose source cannot be verified",
      label: "Source unverified",
      result: makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        ingest_report: { graph_preview: { status: "source_unverified" } },
        entity_spelling_audit: [],
      }),
    },
    {
      name: "a completed graph extraction",
      label: "Graph ready",
      result: makeStatus({
        session: 29,
        status: "ready_for_planning_activation",
        states: ["recap_applied", "preview_union_store_ready"],
        ingest_report: { graph_preview: { status: "preview_union_store_ready" } },
        entity_spelling_audit: [],
      }),
    },
    {
      name: "a failed run",
      label: "Failed",
      result: makeStatus({
        session: 29,
        status: "error",
        states: ["ingest_status_inspected"],
        errors: ["Extraction failed"],
        entity_spelling_audit: [],
      }),
    },
  ])("shows $label for $name", async ({ result, label }) => {
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(result);

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={29}
        managedWorldId="elderwyld"
        initialSourceSession={29}
      />,
    );

    expect(await screen.findByText(label)).toBeInTheDocument();
    expect(screen.queryByText("in progress")).not.toBeInTheDocument();
  });

  it.each(["source_unverified", "candidate_validation_ready"] as const)(
    "explains that a retained unverified graph result (%s) is history and does not start processing",
    async (graphStatus) => {
      const inspectSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
        session: 29,
        status: "source_unverified",
        states: ["ingest_status_inspected", "source_unverified"],
        paths: { canonical_recap: null, normalized_recap: null },
        ingest_report: {
          corpus_impact: [],
          graph_preview: {
            status: graphStatus,
            extraction_run_id: "retained-session-29-run",
            blocked_reason: "selected normalized recap is unavailable for content verification",
          },
        },
        entity_spelling_audit: [],
      }));

      render(
        <IngestionModule
          campaignId="longmont-c2"
          session={29}
          managedWorldId="elderwyld"
          initialSourceSession={29}
        />,
      );

      const guidance = await screen.findByRole("status", { name: "Recap source verification guidance" });
      expect(guidance).toHaveAttribute("data-retained-graph-run", "true");
      expect(guidance).toHaveTextContent("Saved graph result kept as history");
      expect(guidance).toHaveTextContent("cannot be matched to a verified recap");
      expect(guidance).toHaveTextContent("Load the correct saved recap or use Paste recap above");
      expect(guidance).not.toHaveTextContent("retained-session-29-run");
      expect(screen.queryByRole("button", { name: "Process recap" })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Open Graph Review" })).not.toBeInTheDocument();
      expect(inspectSpy.mock.calls.every(([request]) => request.operation === "inspect_status")).toBe(true);
    },
  );

  it("treats a verified saved recap with a missing graph preview as ready for first extraction", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
      session: 10,
      status: "recap_applied",
      states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "normalized_current"],
      ingest_report: {
        corpus_impact: [
          { key: "canonical_recap", relpath: "Session 10.md", exists: true },
          { key: "normalized_recap", relpath: "Session 10 normalized.md", exists: true },
        ],
        graph_preview: {
          status: "missing",
          run_dir: null,
          manifest_path: null,
          candidate_graph_path: null,
          preview_union_store_path: null,
          preview_union_store_valid: null,
          node_count: 0,
          edge_count: 0,
          evidence_ref_count: 0,
          extracted_nodes: [],
          next_actions: ["build_graph_preview_bundle"],
          can_open_union_graph: false,
          blocked_reason: null,
        },
      },
      entity_spelling_audit: [],
    }));

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={10}
        managedWorldId="elderwyld"
        initialSourceSession={10}
      />,
    );

    await userEvent.setup().click(await screen.findByText("Evidence & details"));
    const graphPanel = await screen.findByRole("region", { name: "Graph preview status" });
    expect(await screen.findByText("Not extracted")).toBeInTheDocument();
    expect(within(graphPanel).getByText("Graph extraction: not run")).toBeInTheDocument();
    expect(within(graphPanel).getByRole("status")).toHaveTextContent(
      "Source ready. Choose Process in the Ingest navigation to extract graph candidates.",
    );
    expect(within(graphPanel).queryByText(/status: missing|nodes: 0|edges: 0/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Process recap" })).toBeEnabled();
  });

  it("shows only reported metrics after a partial graph extraction", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
      session: 10,
      status: "recap_applied",
      states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "normalized_current"],
      ingest_report: {
        graph_preview: {
          status: "source_span_bundle_ready",
          extraction_run_id: "session-10-run",
        },
      },
      entity_spelling_audit: [],
    }));

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={10}
        managedWorldId="elderwyld"
        initialSourceSession={10}
      />,
    );

    await userEvent.setup().click(await screen.findByText("Evidence & details"));
    const graphPanel = await screen.findByRole("region", { name: "Graph preview status" });
    expect(graphPanel).toHaveTextContent("Graph extraction: candidate pending");
    expect(within(graphPanel).getByText("status: source_span_bundle_ready")).toBeInTheDocument();
    expect(within(graphPanel).queryByText(/nodes: 0|edges: 0/)).not.toBeInTheDocument();
  });

  it("does not confuse a source-check error with a graph extraction failure", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
      session: 10,
      status: "source_unverified",
      states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "source_unverified"],
      errors: ["The normalized recap is missing."],
      ingest_report: {
        corpus_impact: [],
        graph_preview: {
          status: "missing",
          run_dir: null,
          manifest_path: null,
          candidate_graph_path: null,
          preview_union_store_path: null,
          preview_union_store_valid: null,
          node_count: 0,
          edge_count: 0,
          evidence_ref_count: 0,
          extracted_nodes: [],
          next_actions: ["restore_or_load_verified_source"],
          can_open_union_graph: false,
          blocked_reason: "normalized recap missing",
        },
      },
      entity_spelling_audit: [],
    }));

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={10}
        managedWorldId="elderwyld"
        initialSourceSession={10}
      />,
    );

    await userEvent.setup().click(await screen.findByText("Evidence & details"));
    const graphPanel = await screen.findByRole("region", { name: "Graph preview status" });
    expect(await screen.findByText("Source unverified")).toBeInTheDocument();
    const guidance = await screen.findByRole("status", { name: "Recap source verification guidance" });
    expect(guidance).toHaveAttribute("data-retained-graph-run", "false");
    expect(guidance).toHaveTextContent("Recap source needs verification");
    expect(guidance).not.toHaveTextContent("Saved graph result kept as history");
    expect(graphPanel).toHaveTextContent("Graph extraction: not run");
    expect(within(graphPanel).getByText(
      "Graph extraction has not run yet. Complete the source checks before processing.",
    )).toBeInTheDocument();
    expect(within(graphPanel).queryByText(/Source ready/)).not.toBeInTheDocument();
    expect(within(graphPanel).queryByText("Graph extraction: failed")).not.toBeInTheDocument();
    expect(within(graphPanel).queryByText("Graph extraction: blocked")).not.toBeInTheDocument();
    const processButton = within(screen.getByRole("navigation", { name: "Ingest workspace navigation" }))
      .queryByRole("button", { name: "Process recap" });
    expect(processButton === null || (processButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("keeps a current extraction error distinct from the no-run state", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
      session: 10,
      status: "error",
      states: ["ingest_status_inspected", "graph_preview_failed"],
      errors: ["Graph extraction failed during setup."],
      ingest_report: {
        graph_preview: {
          status: "failed",
          extraction_run_id: "session-10-run",
          node_count: 0,
          edge_count: 0,
        },
      },
      entity_spelling_audit: [],
    }));

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={10}
        managedWorldId="elderwyld"
        initialSourceSession={10}
      />,
    );

    await userEvent.setup().click(await screen.findByText("Evidence & details"));
    const graphPanel = await screen.findByRole("region", { name: "Graph preview status" });
    expect(within(graphPanel).getByText("Graph extraction: failed")).toBeInTheDocument();
    expect(within(graphPanel).queryByText("Graph extraction: not run")).not.toBeInTheDocument();
    expect(within(graphPanel).queryByText(/Source ready/)).not.toBeInTheDocument();
  });

  it("keeps a real blocked extraction distinct from the no-run state", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus({
      session: 10,
      status: "recap_applied",
      states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "graph_source_bundle_ready"],
      ingest_report: {
        graph_preview: {
          status: "source_span_bundle_ready",
          extraction_run_id: "session-10-run",
          extraction_mode: "llm_blocked",
          blocked_reason: "Graph provider is unavailable.",
        },
      },
      entity_spelling_audit: [],
    }));

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={10}
        managedWorldId="elderwyld"
        initialSourceSession={10}
      />,
    );

    await userEvent.setup().click(await screen.findByText("Evidence & details"));
    const graphPanel = await screen.findByRole("region", { name: "Graph preview status" });
    expect(graphPanel).toHaveTextContent("Graph extraction: blocked");
    expect(within(graphPanel).getByText("Graph provider is unavailable.")).toBeInTheDocument();
    expect(within(graphPanel).queryByText("Graph extraction: not run")).not.toBeInTheDocument();
  });

  it("shows Processing only while recap work is active", async () => {
    const user = setupIngestUser();
    const pendingProcess = deferred<RecapIngestStatus>();
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "generate_recap_memory") return pendingProcess.promise;
      return makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      });
    });

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={29}
        managedWorldId="elderwyld"
        initialSourceSession={29}
      />,
    );
    await fillRecapInputs(user, "The group explored the old city and met its watch.", "Session 29 — The City Watch");
    const processButton = await screen.findByRole("button", { name: "Process recap" });
    await waitFor(() => expect(processButton).toBeEnabled());
    await user.click(processButton);

    expect(await screen.findByText("Processing")).toBeInTheDocument();
    await act(async () => {
      pendingProcess.resolve(makeStatus({
        session: 29,
        status: "ready_for_planning_activation",
        states: ["recap_applied", "preview_union_store_ready"],
        ingest_report: { graph_preview: { status: "preview_union_store_ready" } },
        entity_spelling_audit: [],
      }));
    });
    expect(await screen.findByText("Graph ready")).toBeInTheDocument();
  });

  it("shows Processing during a retry even when the previous result failed", async () => {
    const user = setupIngestUser();
    const pendingRetry = deferred<RecapIngestStatus>();
    let processAttempts = 0;
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "generate_recap_memory") {
        processAttempts += 1;
        if (processAttempts === 1) {
          return makeStatus({
            session: 29,
            status: "error",
            states: ["recap_generation_failed"],
            errors: ["Temporary extraction failure"],
            entity_spelling_audit: [],
          });
        }
        return pendingRetry.promise;
      }
      return makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      });
    });

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={29}
        managedWorldId="elderwyld"
        initialSourceSession={29}
      />,
    );
    await fillRecapInputs(user, "The watch found a tunnel beneath the north road.", "Session 29 — The North Road");
    await user.click(await screen.findByRole("button", { name: "Process recap" }));
    expect(await screen.findByText("Failed")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Process recap" }));
    expect(await screen.findByText("Processing")).toBeInTheDocument();

    await act(async () => {
      pendingRetry.resolve(makeStatus({
        session: 29,
        status: "ready_for_planning_activation",
        states: ["recap_applied", "preview_union_store_ready"],
        ingest_report: { graph_preview: { status: "preview_union_store_ready" } },
        entity_spelling_audit: [],
      }));
    });
    expect(await screen.findByText("Graph ready")).toBeInTheDocument();
  });

  it.each([
    {
      name: "an LLM-blocked candidate preview",
      graphPreview: {
        status: "candidate_validation_ready" as const,
        extraction_mode: "llm_blocked",
        blocked_reason: "OPENAI_API_KEY is not configured",
      },
    },
    {
      name: "a materialized preview with a blocking reason",
      graphPreview: {
        status: "preview_union_store_ready" as const,
        blocked_reason: "Graph validation is blocked.",
      },
    },
  ])("shows blocked instead of ready for $name", async ({ graphPreview }) => {
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(
      makeStatus({
        session: 29,
        status: "ready_for_planning_activation",
        states: ["recap_applied", graphPreview.status],
        ingest_report: { graph_preview: graphPreview },
        entity_spelling_audit: [],
      }),
    );

    render(
      <IngestionModule
        campaignId="longmont-c2"
        session={29}
        managedWorldId="elderwyld"
        initialSourceSession={29}
      />,
    );

    expect(await screen.findByText("Blocked")).toBeInTheDocument();
    expect(screen.queryByText("Graph ready")).not.toBeInTheDocument();
  });

  it("defaults the prior recap selector only to the exact campaign and requested session", async () => {
    const session10 = makeRecapArtifactRecord("longmont-c2", 10);
    const session27 = makeRecapArtifactRecord("longmont-c2", 27);
    const otherCampaignSession10 = makeRecapArtifactRecord("longmont-c1", 10);
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10",
    );
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(
      makeRecapArtifactRegistry([session10, session27, otherCampaignSession10]),
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    const priorRecap = await screen.findByLabelText("Prior processed recap");
    await waitFor(() => expect(priorRecap).toHaveValue(session10.artifact_id));
    expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load processed recap" })).toBeInTheDocument();
    expect(priorRecap.querySelector(`option[value="${otherCampaignSession10.artifact_id}"]`)).toBeNull();
  });

  it("leaves the prior recap selector empty when the requested session has no exact match", async () => {
    const session27 = makeRecapArtifactRecord("longmont-c2", 27);
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10",
    );
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(
      makeRecapArtifactRegistry([session27]),
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    const priorRecap = await screen.findByLabelText("Prior processed recap");
    await waitFor(() => expect(priorRecap).toHaveDisplayValue("Load a processed recap…"));
    expect(screen.queryByRole("button", { name: "Load processed recap" })).not.toBeInTheDocument();
  });

  it("reselects only the matching prior recap when the mounted route changes sessions", async () => {
    const session10 = makeRecapArtifactRecord("longmont-c2", 10);
    const session27 = makeRecapArtifactRecord("longmont-c2", 27);
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(
      makeRecapArtifactRegistry([session10, session27]),
    );
    const route = (sessionNumber: number) =>
      `/ingest?world=elderwyld&campaign=longmont-c2&session=session-${sessionNumber}`;
    window.history.replaceState({}, "", route(27));
    const props = { campaignId: "longmont-c2", session: 29, managedWorldId: "elderwyld" } as const;
    const { rerender } = render(<IngestionModule {...props} />);
    const priorRecap = await screen.findByLabelText("Prior processed recap");
    await waitFor(() => expect(priorRecap).toHaveValue(session27.artifact_id));

    window.history.replaceState({}, "", route(10));
    rerender(<IngestionModule {...props} />);

    await waitFor(() => expect(priorRecap).toHaveValue(session10.artifact_id));
    expect(screen.getByRole("button", { name: "Load processed recap" })).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toHaveValue("");
    expect(vi.mocked(recapIngestApi.postRecapIngest).mock.calls.every(
      ([request]) => request.operation !== "generate_recap_memory",
    )).toBe(true);
  });

  it("follows mounted route session changes and ignores an earlier A response after A→B→A", async () => {
    const firstA = deferred<RecapIngestStatus>();
    const sessionB = deferred<RecapIngestStatus>();
    const secondA = deferred<RecapIngestStatus>();
    const requests = vi.mocked(recapIngestApi.postRecapIngest);
    let hasVisitedB = false;
    const statusFor = (sessionNumber: number, path: string) => makeStatus({
      session: sessionNumber,
      status: "initialized",
      states: ["ingest_status_inspected"],
      warnings: [path],
      entity_spelling_audit: [],
    });
    requests.mockImplementation((body) => {
      if (body.operation !== "inspect_status") return Promise.resolve(makeStatus({ session: body.session }));
      if (body.session === 10) return hasVisitedB ? secondA.promise : firstA.promise;
      if (body.session === 11) {
        hasVisitedB = true;
        return sessionB.promise;
      }
      return Promise.resolve(makeStatus({ session: body.session }));
    });

    const route = (sessionNumber: number) =>
      `/ingest?world=elderwyld&campaign=longmont-c2&session=session-${sessionNumber}`;
    window.history.replaceState({}, "", route(10));
    const props = { campaignId: "longmont-c2", session: 29, managedWorldId: "elderwyld" } as const;
    const { rerender } = render(<IngestionModule {...props} />);

    await waitFor(() => expect(requests).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status", session: 10 })));
    await act(async () => { await Promise.resolve(); });
    const initialACallCount = requests.mock.calls.filter(([request]) => request.operation === "inspect_status" && request.session === 10).length;
    window.history.replaceState({}, "", route(11));
    rerender(<IngestionModule {...props} />);
    await waitFor(() => expect(requests).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status", session: 11 })));
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(11);

    window.history.replaceState({}, "", route(10));
    rerender(<IngestionModule {...props} />);
    await waitFor(() => expect(requests.mock.calls.filter(([request]) => request.operation === "inspect_status" && request.session === 10).length).toBeGreaterThan(initialACallCount));
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(10);

    await act(async () => {
      firstA.resolve(makeStatus({
        ...statusFor(10, "stale-first-A-session-10.md"),
        status: "source_unverified",
        states: ["ingest_status_inspected", "source_unverified"],
        ingest_report: {
          graph_preview: {
            status: "source_unverified",
            extraction_run_id: "stale-first-A-run",
          },
        },
      }));
      await firstA.promise;
    });
    expect(document.body).not.toHaveTextContent("stale-first-A-session-10.md");
    expect(screen.queryByRole("status", { name: "Recap source verification guidance" })).not.toBeInTheDocument();

    await act(async () => {
      secondA.resolve(makeStatus({
        ...statusFor(10, "current-second-A-session-10.md"),
      }));
      await secondA.promise;
    });
    await waitFor(() => expect(document.body).toHaveTextContent("current-second-A-session-10.md"));
    await act(async () => {
      sessionB.resolve(makeStatus({
        ...statusFor(11, "stale-B-session-11.md"),
        status: "source_unverified",
        states: ["ingest_status_inspected", "source_unverified"],
        ingest_report: {
          graph_preview: {
            status: "source_unverified",
            extraction_run_id: "stale-session-B-run",
          },
        },
      }));
      await sessionB.promise;
    });
    expect(document.body).not.toHaveTextContent("stale-B-session-11.md");
    expect(screen.queryByRole("status", { name: "Recap source verification guidance" })).not.toBeInTheDocument();
  });

  it("ignores deferred Process results across mounted World A→B→A and preserves the recap draft", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const pendingWorldAProcess = deferred<RecapIngestStatus>();
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (request) => {
      if (request.operation === "generate_recap_memory") return pendingWorldAProcess.promise;
      return makeStatus({
        campaign_id: request.campaign_id,
        session: request.session,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      });
    });

    const props = { campaignId: "longmont-c2", session: 22 } as const;
    const { rerender } = render(<IngestionModule {...props} managedWorldId="elderwyld" />);
    const recap = "Session 22 — A draft that must survive World navigation.";
    await fillRecapInputs(user, recap, "Session 22 — Route safety");
    await user.click(await screen.findByRole("button", { name: "Process recap" }));
    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({
      operation: "generate_recap_memory",
      managed_world_id: "elderwyld",
      session: 22,
    })));

    rerender(<IngestionModule {...props} managedWorldId="conks-and-cons" />);
    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue(recap);
    rerender(<IngestionModule {...props} managedWorldId="elderwyld" />);
    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue(recap);

    await act(async () => {
      pendingWorldAProcess.resolve(makeStatus({
        campaign_id: "longmont-c2",
        session: 22,
        status: "ready_for_planning_activation",
        states: ["recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
        ingest_report: {
          graph_preview: {
            status: "candidate_validation_ready",
            extraction_run_id: "world-a-stale-run",
            candidate_node_count: 3,
            candidate_edge_count: 2,
          },
        },
      }));
      await pendingWorldAProcess.promise;
    });

    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue(recap);
    expect(screen.queryByRole("region", { name: "Graph-enriched recap" })).not.toBeInTheDocument();
    expect(screen.queryByText("Recap processed")).not.toBeInTheDocument();
  });

  it("drops a deferred saved-reader projection when the mounted route changes sessions", async () => {
    const oldSessionProjection = deferred<ExactRunCandidateProjection>();
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(
      makeRecapArtifactRegistry([
        makeRecapArtifactRecord("longmont-c2", 10),
        makeRecapArtifactRecord("longmont-c2", 11),
      ]),
    );
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      campaign_id: request.campaign_id,
      session: request.session,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: {
        ...makeStatus().paths,
        canonical_recap: `Session ${request.session}.md`,
        normalized_recap: `Session ${request.session}.md`,
      },
    }));
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockImplementation((runId) =>
      runId === "run-session-10"
        ? oldSessionProjection.promise
        : Promise.resolve(candidateRecapProjectionForRun(runId)),
    );

    const route = (sessionNumber: number) =>
      `/ingest?world=elderwyld&campaign=longmont-c2&session=session-${sessionNumber}&view=recap&recapReviewRunId=run-session-${sessionNumber}`;
    window.history.replaceState({}, "", route(10));
    const props = { campaignId: "longmont-c2", session: 29, managedWorldId: "elderwyld" } as const;
    const { rerender } = render(<IngestionModule {...props} />);
    await waitFor(() => expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-10", "elderwyld"));

    window.history.replaceState({}, "", route(11));
    rerender(<IngestionModule {...props} />);
    await waitFor(() => expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-11", "elderwyld"));
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(11);
    expect(await screen.findByText("Session 11 — Mireward Road")).toBeInTheDocument();

    await act(async () => {
      oldSessionProjection.resolve(candidateRecapProjectionForRun("run-session-10"));
      await oldSessionProjection.promise;
    });
    expect(screen.getByText("Session 11 — Mireward Road")).toBeInTheDocument();
    expect(screen.queryByText("Session 10 — Mireward Road")).not.toBeInTheDocument();
  });

  it("waits for the exact saved-recap list before restoring an addressless cold reader route", async () => {
    const pendingList = deferred<Awaited<ReturnType<typeof liveApi.getRecapArtifacts>>>();
    vi.mocked(liveApi.getRecapArtifacts).mockReturnValue(pendingList.promise);
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      campaign_id: request.campaign_id,
      session: request.session,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: { canonical_recap: null, normalized_recap: null },
      ingest_report: { corpus_impact: [] },
      entity_spelling_audit: [],
    }));
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap",
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);
    await waitFor(() => expect(liveApi.getRecapArtifacts).toHaveBeenCalledWith("longmont-c2"));
    await waitFor(() => expect(recapIngestApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({
      operation: "inspect_status",
      campaign_id: "longmont-c2",
      session: 10,
    })));

    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    const exactArtifact = makeRecapArtifactRecord("longmont-c2", 10);
    await act(async () => {
      pendingList.resolve(makeRecapArtifactRegistry([exactArtifact]));
      await pendingList.promise;
    });

    const recapReader = await screen.findByRole("region", { name: "Graph-enriched recap" });
    expect(within(recapReader).queryByLabelText("Focus session")).not.toBeInTheDocument();
    expect(within(recapReader).queryByRole("button", { name: "Load" })).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Campaign")).toHaveLength(1);
    expect(screen.getByLabelText("Prior processed recap")).toBeInTheDocument();
    expect(within(recapReader).getByTestId("published-recap-local-authoring")).toBeInTheDocument();
    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledWith(
      expect.objectContaining({ campaignId: "longmont-c2", focus: expect.objectContaining({ sessionId: "session-10" }) }),
    ));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not let early Graph availability consume a cold reader attempt before source hydration", async () => {
    const pendingGraphSession = deferred<string>();
    const pendingStatus = deferred<RecapIngestStatus>();
    const pendingList = deferred<Awaited<ReturnType<typeof liveApi.getRecapArtifacts>>>();
    vi.spyOn(liveApi, "ensureNativeGraphSession").mockReturnValue(pendingGraphSession.promise);
    vi.mocked(liveApi.getRecapArtifacts).mockReturnValue(pendingList.promise);
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "inspect_status") return pendingStatus.promise;
      return makeStatus({ campaign_id: request.campaign_id, session: request.session });
    });
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap",
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);
    await waitFor(() => expect(liveApi.ensureNativeGraphSession).toHaveBeenCalled());
    await waitFor(() => expect(recapIngestApi.postRecapIngest).toHaveBeenCalledWith(expect.objectContaining({
      operation: "inspect_status",
      campaign_id: "longmont-c2",
      session: 10,
    })));

    await act(async () => {
      pendingGraphSession.resolve("csrf-token");
      await pendingGraphSession.promise;
    });
    expect(screen.queryByText("No saved recap is available for this session.")).not.toBeInTheDocument();
    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();

    const exactArtifact = makeRecapArtifactRecord("longmont-c2", 10);
    await act(async () => {
      pendingStatus.resolve(makeStatus({
        campaign_id: "longmont-c2",
        session: 10,
        status: "recap_reused",
        states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
        paths: { canonical_recap: null, normalized_recap: null },
        ingest_report: { corpus_impact: [] },
        entity_spelling_audit: [],
      }));
      await pendingStatus.promise;
    });
    await waitFor(() => expect(liveApi.getRecapArtifacts).toHaveBeenCalledWith("longmont-c2"));
    await act(async () => {
      pendingList.resolve(makeRecapArtifactRegistry([exactArtifact]));
      await pendingList.promise;
    });

    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledWith(
      expect.objectContaining({ campaignId: "longmont-c2", focus: expect.objectContaining({ sessionId: "session-10" }) }),
    ));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    expect(screen.queryByText("No saved recap is available for this session.")).not.toBeInTheDocument();
  });

  it("retries a failed cold reader when the native Graph session is reconnected", async () => {
    const user = setupIngestUser();
    const exactArtifact = makeRecapArtifactRecord("longmont-c2", 10);
    vi.spyOn(liveApi, "ensureNativeGraphSession").mockRejectedValue(new Error("Local Graph session unavailable"));
    vi.spyOn(liveApi, "connectNativeGraphSession").mockResolvedValue("csrf-token");
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(makeRecapArtifactRegistry([exactArtifact]));
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      campaign_id: request.campaign_id,
      session: request.session,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: { canonical_recap: null, normalized_recap: null },
      ingest_report: { corpus_impact: [] },
      entity_spelling_audit: [],
    }));
    vi.mocked(liveApi.postWorldGraphRecapProjection)
      .mockRejectedValueOnce(new Error("Local Graph session unavailable"))
      .mockImplementation(async (request) => ({
        ...session23WorldGraphRecapFixture,
        campaignId: request.campaignId,
        sessionId: request.focus.sessionId!,
        snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
      }));
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap",
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);
    expect(await screen.findByText("Local Graph session unavailable.")).toBeInTheDocument();
    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledTimes(1));
    expect(await screen.findByText("Local Graph session unavailable")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Connect local Graph session" }));
    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
  });

  it("restores a successfully opened reader after Graph access is revoked and reconnected", async () => {
    const user = setupIngestUser();
    const exactArtifact = makeRecapArtifactRecord("longmont-c2", 10);
    vi.spyOn(liveApi, "ensureNativeGraphSession").mockResolvedValue("csrf-token");
    vi.spyOn(liveApi, "revokeNativeGraphSession").mockResolvedValue();
    vi.spyOn(liveApi, "connectNativeGraphSession").mockResolvedValue("csrf-token");
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(makeRecapArtifactRegistry([exactArtifact]));
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      campaign_id: request.campaign_id,
      session: request.session,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: { canonical_recap: null, normalized_recap: null },
      ingest_report: { corpus_impact: [] },
      entity_spelling_audit: [],
    }));
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap",
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);
    expect(await screen.findByText(/Held the Mireward gate during Session 23/)).toBeInTheDocument();
    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Revoke local Graph session" }));
    expect(await screen.findByText("Local Graph session revoked.")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Held the Mireward gate during Session 23/)).not.toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Connect local Graph session" }));
    await waitFor(() => expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/Held the Mireward gate during Session 23/)).toBeInTheDocument();
  });

  it.each([
    ["empty", makeRecapArtifactRegistry([]), "No saved recap is available for this session."],
    ["unavailable", new Error("Registry unavailable"), "Saved recaps could not be checked."],
  ] as const)("reports an addressless cold reader route after the saved-recap list is %s", async (_state, lookupResult, message) => {
    if (lookupResult instanceof Error) {
      vi.mocked(liveApi.getRecapArtifacts).mockRejectedValue(lookupResult);
    } else {
      vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue(lookupResult);
    }
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      campaign_id: request.campaign_id,
      session: request.session,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: { canonical_recap: null, normalized_recap: null },
      ingest_report: { corpus_impact: [] },
      entity_spelling_audit: [],
    }));
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10&view=recap",
    );

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
  });

  it("preserves the recap draft under its original session when the operator changes sessions", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10");
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => makeStatus({
      session: request.session,
      status: "initialized",
      states: ["ingest_status_inspected"],
      entity_spelling_audit: [],
    }));
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    const recapInput = await screen.findByRole("textbox", { name: "Write or paste a recap" });
    await user.type(recapInput, "Session 10 source text that must stay bound to Session 10.");
    await user.clear(screen.getByLabelText("Session title"));
    await user.type(screen.getByLabelText("Session title"), "Session 10 - The Guard Arrives");
    await act(async () => {
      fireEvent.change(screen.getByLabelText("Recap/source session"), { target: { value: "11" } });
    });

    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(await screen.findByText(/Draft preserved · Session 10/)).toBeInTheDocument();
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await user.click(within(toolbar).getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(
      "Session 10 source text that must stay bound to Session 10.",
    );
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(10);
  });

  it("uses the latest session target when a prior recap list resolves late", async () => {
    const user = setupIngestUser();
    const pendingList = deferred<Awaited<ReturnType<typeof liveApi.getRecapArtifacts>>>();
    const getRecapArtifacts = vi.mocked(liveApi.getRecapArtifacts);
    getRecapArtifacts.mockReturnValue(pendingList.promise);
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2",
    );
    render(
      <IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" initialSourceSession={10} />,
    );
    await waitFor(() => expect(getRecapArtifacts).toHaveBeenCalledTimes(1));

    const sessionInput = screen.getByLabelText("Recap/source session");
    await user.clear(sessionInput);
    fireEvent.change(sessionInput, { target: { value: "11" } });
    await waitFor(() => expect(sessionInput).toHaveValue(11));
    expect(getRecapArtifacts).toHaveBeenCalledTimes(1);

    const exactChangedSession = makeRecapArtifactRecord("longmont-c2", 11);
    await act(async () => {
      pendingList.resolve(
        makeRecapArtifactRegistry([
          makeRecapArtifactRecord("longmont-c2", 10),
          exactChangedSession,
          makeRecapArtifactRecord("longmont-c2", 27),
        ]),
      );
      await Promise.resolve();
    });
    const changedSessionSelector = await screen.findByLabelText("Prior processed recap");
    await waitFor(() => expect(changedSessionSelector).toHaveValue(exactChangedSession.artifact_id));
  });

  it("ignores prior recap lists returned after the campaign changes", async () => {
    const user = setupIngestUser();
    const oldCampaignList = deferred<Awaited<ReturnType<typeof liveApi.getRecapArtifacts>>>();
    const newCampaignList = deferred<Awaited<ReturnType<typeof liveApi.getRecapArtifacts>>>();
    const getRecapArtifacts = vi.mocked(liveApi.getRecapArtifacts);
    getRecapArtifacts.mockImplementation((campaignId) =>
      campaignId === "longmont-c2" ? oldCampaignList.promise : newCampaignList.promise,
    );
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10",
    );
    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);
    await waitFor(() => expect(getRecapArtifacts).toHaveBeenCalledTimes(1));

    await user.selectOptions(screen.getByLabelText("Campaign"), "longmont-c1");
    await waitFor(() =>
      expect(getRecapArtifacts.mock.calls.some(([campaignId]) => campaignId === "longmont-c1")).toBe(true),
    );
    expect(screen.queryByLabelText("Prior processed recap")).not.toBeInTheDocument();

    await act(async () => {
      oldCampaignList.resolve(makeRecapArtifactRegistry([makeRecapArtifactRecord("longmont-c2", 10)]));
      await Promise.resolve();
    });
    expect(screen.queryByLabelText("Prior processed recap")).not.toBeInTheDocument();

    const exactNewTarget = makeRecapArtifactRecord("longmont-c1", 10);
    await act(async () => {
      newCampaignList.resolve(
        makeRecapArtifactRegistry([
          exactNewTarget,
          makeRecapArtifactRecord("longmont-c1", 27),
        ]),
      );
      await Promise.resolve();
    });

    const priorRecap = await screen.findByLabelText("Prior processed recap");
    await waitFor(() => expect(priorRecap).toHaveValue(exactNewTarget.artifact_id));
    expect(within(priorRecap).queryByRole("option", { name: /Session 27/ })).toBeInTheDocument();
    expect(priorRecap.querySelector('option[value="artifact:recap:longmont-c2:session-10"]')).toBeNull();
  });

  it("keeps a blank recap editor empty and its prompt independent of session examples", async () => {
    render(<IngestionModule campaignId="longmont-c2" session={29} initialSourceSession={29} />);

    const rawField = await screen.findByRole("textbox", { name: "Write or paste a recap" });
    expect(rawField).toHaveValue("");
    expect(rawField).toHaveAttribute("placeholder", "Write or paste a session recap here…");
  });

  it("welcomes a blank Elderwyld recap entry without trying to restore a saved recap route", async () => {
    const user = setupIngestUser();
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    vi.spyOn(liveApi, "ensureNativeGraphSession").mockResolvedValue("csrf-token");
    const inspection = vi.spyOn(liveApi, "getHistoricalRecapInspection");
    const ingest = vi.mocked(recapIngestApi.postRecapIngest);
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [{
        schema_version: "dmb_recap_artifact_record_v1",
        artifact_id: "recap-session-29",
        campaign_id: "longmont-c2",
        session_id: "session-29",
        source_recap_path: "corpus/eldyrwild-markdown/Session 29 - The Meat Mind.md",
        run_bundle_uri: "bundle",
        run_manifest_uri: "manifest",
        source_span_index_uri: "index",
        graph_run_refs: [],
        default_projection_mode: "preview_union",
        registered_at: "2026-06-29T00:00:00Z",
        updated_at: "2026-06-29T00:00:00Z",
        registry_source: "scan",
      }],
    });

    render(<IngestionModule campaignId="longmont-c2" session={30} managedWorldId="elderwyld" initialSourceSession={29} />);

    expect(await screen.findByRole("heading", { name: "Bring your table’s story into the World." })).toBeInTheDocument();
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    expect(toolbar).toBeInTheDocument();
    expect(within(toolbar).getByLabelText("Campaign")).toBeInTheDocument();
    expect(within(toolbar).getByLabelText("Recap/source session")).toHaveValue(null);
    expect(within(toolbar).getByLabelText("Session title")).toHaveValue("");
    expect(within(toolbar).getByLabelText("Prior processed recap")).toBeInTheDocument();
    expect(within(toolbar).getByRole("button", { name: "Paste recap" })).toBeInTheDocument();
    expect(within(toolbar).queryByRole("button", { name: "Prep for ingest" })).not.toBeInTheDocument();
    expect(within(toolbar).queryByRole("button", { name: "Process recap" })).not.toBeInTheDocument();
    expect(within(toolbar).queryByRole("status")).not.toBeInTheDocument();
    expect(screen.queryByText("Operator prep tool over the PR92 ingestion orchestrator.")).not.toBeInTheDocument();
    expect(screen.queryByText("Current next action")).not.toBeInTheDocument();
    expect(screen.queryByText(/Next: Review the extracted candidate/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(null);
    expect(screen.getByLabelText("Session title")).toHaveValue("");
    await waitFor(() => expect(screen.getByLabelText("Prior processed recap")).toHaveDisplayValue("Load a processed recap…"));
    expect(ingest).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Load processed recap" })).not.toBeInTheDocument();
    expect(screen.queryByRole("list", { name: "From recap to World memory" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Write a recap" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Paste recap" }));
    const rawField = screen.getByRole("textbox", { name: "Write or paste a recap" });
    expect(rawField).toHaveFocus();
    expect(rawField).toHaveValue("");
    expect(rawField).toHaveAttribute("placeholder", "Write or paste a session recap here…");

    await waitFor(() => expect(screen.queryByText("Saved recap route has an invalid campaign or session.")).not.toBeInTheDocument());
    expect(inspection).not.toHaveBeenCalled();
    expect(ingest).not.toHaveBeenCalled();
    expect(window.location.search).toBe("?world=elderwyld");
  });

  it.each([
    ["one confirmed file", [{ key: "canonical_recap", relpath: "corpus/session-29.md", exists: true }]],
    ["a source row without a path", [
      { key: "canonical_recap", relpath: "", exists: true },
      { key: "normalized_recap", relpath: "corpus/normalized-session-29.md", exists: true },
    ]],
    ["malformed existence values", [
      { key: "canonical_recap", relpath: "corpus/session-29.md", exists: "true" },
      { key: "normalized_recap", relpath: "corpus/normalized-session-29.md", exists: true },
    ]],
    ["no file proof", undefined],
  ])("keeps the saved recap unavailable when source-file proof is incomplete: %s", async (_case, corpusImpact) => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "",
      recapSession: 29,
      slug: "",
      title: "Session 29 - The Meat Mind of Mireward Reach",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: null,
      state: { status: "idle" },
      ignoreDiskResume: false,
    }));
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(makeStatus({
      session: 29,
      status: "recap_applied",
      states: ["ingest_status_inspected", "recap_applied", "recap_reused", "normalized_reused"],
      ingest_report: { corpus_impact: corpusImpact ?? [] },
    }));

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    const nav = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(nav).getByRole("status")).toHaveTextContent("Recap file presence is unverified"));
    expect(within(nav).getByRole("status")).not.toHaveTextContent("Recap source missing");
    expect(within(nav).queryByRole("group", { name: "Extraction actions" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("button", { name: "Prep for ingest" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("button", { name: "Process recap" })).not.toBeInTheDocument();
    expect(vi.mocked(recapIngestApi.postRecapIngest).mock.calls.every(([request]) => request.operation === "inspect_status")).toBe(true);
    expect(screen.queryByRole("note", { name: "Prepared recap source" })).not.toBeInTheDocument();
    expect(within(nav).getByRole("status")).toHaveTextContent("Recap file presence is unverified");
    await userEvent.setup().click(within(nav).getByRole("link", { name: "Evidence" }));
    const proof = screen.getByRole("region", { name: "Ingestion proof artifacts" });
    const recapProofRows = ["canonical recap", "normalized recap"].map((label) =>
      within(proof).getByText(label, { exact: true }).closest("li"),
    );
    expect(recapProofRows.some((row) => row?.textContent?.includes("Unverified"))).toBe(true);
    expect(recapProofRows.every((row) => !row?.textContent?.includes("Missing"))).toBe(true);
  });

  it("blocks disk-backed actions when recap files exist but normalized lineage is stale", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "",
      recapSession: 29,
      slug: "",
      title: "Session 29 - The Meat Mind of Mireward Reach",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: null,
      state: { status: "idle" },
      ignoreDiskResume: false,
    }));
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(makeStatus({
      session: 29,
      status: "recap_applied",
      states: [
        "ingest_status_inspected",
        "recap_applied",
        "recap_reused",
        "normalized_reused",
        "normalized_stale",
        "derivative_reconciliation_required",
      ],
      ingest_report: {
        corpus_impact: [
          { key: "canonical_recap", relpath: "corpus/session-29.md", exists: true },
          { key: "normalized_recap", relpath: "corpus/normalized-session-29.md", exists: true },
        ],
      },
    }));

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    const nav = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(nav).getByRole("status")).toHaveTextContent(/normalized recap is stale/i));
    expect(within(nav).queryByRole("group", { name: "Extraction actions" })).not.toBeInTheDocument();
    expect(screen.queryByRole("note", { name: "Prepared recap source" })).not.toBeInTheDocument();
    expect(vi.mocked(recapIngestApi.postRecapIngest).mock.calls.every(([request]) => request.operation === "inspect_status")).toBe(true);
  });

  it("blocks advanced graph extraction and materialization when reused status has no file proof", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "",
      recapSession: 29,
      slug: "",
      title: "Session 29 - The Meat Mind of Mireward Reach",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: null,
      state: { status: "idle" },
      ignoreDiskResume: false,
    }));
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(makeStatus({
      session: 29,
      status: "recap_applied",
      states: ["ingest_status_inspected", "recap_applied", "recap_reused", "normalized_reused"],
      ingest_report: { corpus_impact: [] },
    }));

    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    await waitFor(() => expect(screen.getByText(/recap file presence is unverified/i)).toBeInTheDocument());
    await user.click(screen.getByText("Evidence & details"));
    await user.click(screen.getByText("Advanced graph tools"));
    await user.type(screen.getByLabelText("Candidate graph path"), "out/candidate.json");

    const buildPreview = screen.getByRole("button", { name: "Build Graph Preview" });
    const materializePreview = screen.getByRole("button", { name: "Materialize Preview Supergraph" });
    expect(buildPreview).toBeDisabled();
    expect(materializePreview).toBeDisabled();

    // Exercise both handler guards independently of the disabled-button affordance.
    buildPreview.removeAttribute("disabled");
    materializePreview.removeAttribute("disabled");
    fireEvent.click(buildPreview);
    fireEvent.click(materializePreview);
    expect(vi.mocked(recapIngestApi.postRecapIngest).mock.calls.every(([request]) => request.operation === "inspect_status")).toBe(true);
  });

  it("invalidates source proof when the selected session changes", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-23");
    const inspectSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (request) => {
      if (request.operation !== "inspect_status") {
        throw new Error(`Unexpected ingestion write: ${request.operation}`);
      }
      if (request.session === 23) {
        return makeStatus({
          session: 23,
          status: "recap_applied",
          states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "recap_applied"],
        });
      }
      return makeStatus({
        session: 24,
        status: "recap_applied",
        states: ["ingest_status_inspected", "recap_reused", "normalized_reused", "recap_applied"],
        ingest_report: { corpus_impact: [] },
      });
    });

    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" initialSourceSession={23} />);

    await waitFor(() => expect(inspectSpy).toHaveBeenCalledWith(expect.objectContaining({
      operation: "inspect_status",
      campaign_id: "longmont-c2",
      session: 23,
    })));
    await user.click(screen.getByText("Evidence & details"));
    await user.click(screen.getByText("Advanced graph tools"));
    await user.type(screen.getByLabelText("Candidate graph path"), "out/candidate.json");

    const buildPreview = screen.getByRole("button", { name: "Build Graph Preview" });
    const materializePreview = screen.getByRole("button", { name: "Materialize Preview Supergraph" });
    expect(buildPreview).toBeEnabled();
    expect(materializePreview).toBeEnabled();

    const sessionInput = screen.getByLabelText("Recap/source session");
    fireEvent.change(sessionInput, { target: { value: "24" } });
    expect(sessionInput).toHaveValue(24);
    expect(buildPreview).toBeDisabled();
    expect(materializePreview).toBeDisabled();
    const extract = screen.queryByRole("button", { name: /run ingest|extract/i });
    if (extract) expect(extract).toBeDisabled();

    fireEvent.blur(sessionInput);
    await waitFor(() => expect(inspectSpy).toHaveBeenCalledWith(expect.objectContaining({
      operation: "inspect_status",
      campaign_id: "longmont-c2",
      session: 24,
    })));
    await waitFor(() => {
      expect(buildPreview).toBeDisabled();
      expect(materializePreview).toBeDisabled();
      const currentExtract = screen.queryByRole("button", { name: /run ingest|extract/i });
      if (currentExtract) expect(currentExtract).toBeDisabled();
    });
    expect(inspectSpy).toHaveBeenCalledTimes(2);
  });

  it("discards a Process response when its selected session changed in flight", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-23");
    let finishProcess!: (result: RecapIngestStatus) => void;
    const ingest = vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "inspect_status") {
        return makeStatus({
          session: request.session,
          status: "initialized",
          states: ["ingest_status_inspected"],
        });
      }
      if (request.operation === "generate_recap_memory") {
        return new Promise((resolve) => { finishProcess = resolve; });
      }
      throw new Error(`Unexpected ingest operation: ${request.operation}`);
    });

    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Write or paste a recap"), "Session 23 recap\n\nThe party arrives.");
    await user.type(screen.getByLabelText("Session title"), "Session 23 - Arrival");
    await user.click(screen.getByRole("button", { name: "Process recap" }));
    await waitFor(() => expect(ingest).toHaveBeenCalledWith(expect.objectContaining({
      operation: "generate_recap_memory",
      campaign_id: "longmont-c2",
      session: 23,
    })));

    fireEvent.change(screen.getByLabelText("Recap/source session"), { target: { value: "24" } });
    await act(async () => finishProcess(makeStatus({
      session: 23,
      status: "recap_applied",
      states: ["recap_applied", "normalized_created", "normalized_current"],
    })));

    expect(screen.queryByText("Recap processed")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Graph-enriched recap" })).not.toBeInTheDocument();
  });

  it("keeps a late same-session response out of a new recap draft", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-23");
    let finishProcess!: (result: RecapIngestStatus) => void;
    const ingest = vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "inspect_status") {
        return makeStatus({
          session: request.session,
          status: "initialized",
          states: ["ingest_status_inspected"],
        });
      }
      if (request.operation === "generate_recap_memory") {
        return new Promise((resolve) => { finishProcess = resolve; });
      }
      throw new Error(`Unexpected ingest operation: ${request.operation}`);
    });

    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Write or paste a recap"), "Old draft recap\n\nThe party arrives.");
    await user.type(screen.getByLabelText("Session title"), "Session 23 - Old draft");
    await user.click(screen.getByRole("button", { name: "Process recap" }));
    await waitFor(() => expect(ingest).toHaveBeenCalledWith(expect.objectContaining({
      operation: "generate_recap_memory",
      campaign_id: "longmont-c2",
      session: 23,
    })));

    // New recap keeps the same campaign/session, so target identity alone
    // cannot distinguish this cleared draft from the one in flight.
    await user.click(screen.getByRole("button", { name: "New recap" }));
    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue("");
    expect(screen.getByLabelText("Session title")).toHaveValue("");

    await act(async () => finishProcess(makeStatus({
      session: 23,
      status: "recap_applied",
      states: ["recap_applied", "normalized_created", "normalized_current"],
    })));

    expect(screen.getByLabelText("Write or paste a recap")).toHaveValue("");
    expect(screen.getByLabelText("Session title")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Paste recap" })).toBeInTheDocument();
  });

  it("reports an operation response bound to a different campaign or session", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-23");
    const ingest = vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
      if (request.operation === "inspect_status") {
        return makeStatus({
          session: request.session,
          status: "initialized",
          states: ["ingest_status_inspected"],
        });
      }
      if (request.operation === "generate_recap_memory") {
        return makeStatus({
          session: 24,
          status: "recap_applied",
          states: ["recap_applied", "normalized_created", "normalized_current"],
        });
      }
      throw new Error(`Unexpected ingest operation: ${request.operation}`);
    });

    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Write or paste a recap"), "Session 23 recap\n\nThe party arrives.");
    await user.type(screen.getByLabelText("Session title"), "Session 23 - Arrival");
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    expect(await screen.findByText("Response did not match this recap")).toBeInTheDocument();
    expect(ingest).toHaveBeenCalledWith(expect.objectContaining({
      operation: "generate_recap_memory",
      campaign_id: "longmont-c2",
      session: 23,
    }));
    await user.click(screen.getByText("Details"));
    expect(screen.getByText(/different campaign or session/i)).toBeInTheDocument();
  });

  it("renders editable recap/source session input", async () => {
    const user = setupIngestUser();
    render(<IngestionModule campaignId="longmont-c2" session={23} />);

    const recapSessionInput = screen.getByLabelText("Recap/source session");
    expect(recapSessionInput).toHaveValue(22);
    expect(screen.getAllByText("Required")).toHaveLength(1);
    expect(screen.queryByText(/Used for the canonical recap filename/)).not.toBeInTheDocument();
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road\n\nThe group travels.",
      "Session 22 - Mireward Road",
    );
    expect(screen.queryByText("Required")).not.toBeInTheDocument();
    await user.clear(recapSessionInput);
    fireEvent.change(recapSessionInput, { target: { value: "21" } });
    expect(recapSessionInput).toHaveValue(21);
  });

  it("renders from surface catalog when ingestion module is enabled", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(
      makeStatus({
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }),
    );
    const catalog = [
      ...mockCatalog,
      {
        module_id: "ingestion",
        title: "Ingestion",
        default_slot: "sidebar" as const,
        required: false,
        enabled_by_default: false,
        description: "Raw recap ingest operator pane",
        config_schema: null,
      },
    ];
    const layout = {
      ...mockLayout,
      modules: [
        ...mockLayout.modules,
        {
          module_id: "ingestion",
          slot: "sidebar" as const,
          order: 10,
          enabled: true,
          collapsed: false,
          size: null,
          config: {},
        },
      ],
    };
    render(
      <SurfaceShell
        catalog={catalog}
        layout={layout}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );
    expect(await screen.findByRole("navigation", { name: "Ingest workspace navigation" })).toBeInTheDocument();
  });

  it("keeps the empty local navigation focused on recap identity", async () => {
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    const nav = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    expect(within(nav).getByLabelText("Campaign")).toBeInTheDocument();
    expect(within(nav).getByLabelText("Recap/source session")).toBeInTheDocument();
    expect(within(nav).getByLabelText("Session title")).toBeInTheDocument();
    expect(within(nav).queryByLabelText("Prior processed recap")).not.toBeInTheDocument();
    expect(within(nav).queryByRole("button", { name: "Load processed recap" })).not.toBeInTheDocument();
    expect(within(nav).queryByRole("group", { name: "Extraction actions" })).not.toBeInTheDocument();
    expect(within(nav).queryByText("No recap source loaded.")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toHaveValue("");
  });

  it("asks for a specific session title before processing", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);

    await user.type(screen.getByLabelText("Write or paste a recap"), "Session 22 Recap\n\n...");
    const title = screen.getByLabelText("Session title");
    await user.type(title, "ingest");

    expect(screen.getByRole("button", { name: "Process recap" })).toBeDisabled();
    expect(screen.getByText("Add a specific session title before processing.")).toBeInTheDocument();

    await user.clear(title);
    await user.type(title, "Session 22 - Mireward Gate Approach");
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(toolbar).getByRole("status")).toHaveTextContent(/Choose Process to build the enriched recap and graph context/i));
    expect(screen.getByRole("button", { name: "Process recap" })).toBeEnabled();
  });

  it("opens a saved Session 10 as the enriched World Graph view", async () => {
    const user = setupIngestUser();
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10");
    const draftText = "Session 11 draft that must survive a direct Session 10 route.";
    const storageKey = "dmb.ingestion.longmont-c2.session.11";
    window.localStorage.setItem(storageKey, JSON.stringify({
      version: 3,
      rawText: draftText,
      recapSession: 11,
      slug: "",
      title: "Session 11 - Draft in progress",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      ignoreDiskResume: false,
    }));
    const status = makeStatus({
      session: 10,
      status: "recap_reused",
      states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
      paths: {
        ...makeStatus().paths,
        canonical_recap: "Longmont Campaign/Campaign 2/Session Recaps/Session 10 - Mireward.md",
        normalized_recap: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 10 - Mireward.md",
      },
      ingest_report: {
        corpus_impact: [
          { key: "canonical_recap", relpath: "Session 10 - Mireward.md", exists: true },
          { key: "normalized_recap", relpath: "Session 10 - Mireward.md", exists: true },
        ],
      },
      entity_spelling_audit: [],
    });
    const ingest = vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(status);
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    const initialView = render(<IngestionModule campaignId="longmont-c2" session={11} managedWorldId="elderwyld" initialSourceSession={10} />);

    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(toolbar).getByRole("status")).toHaveTextContent("Viewing saved recap · Session 10."));
    expect(within(toolbar).queryByText(/Choose Process to build the enriched recap/i)).not.toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("view")).toBe("recap");
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}")).toMatchObject({ rawText: draftText, recapSession: 11 });
    expect(within(toolbar).getByRole("button", { name: "Return to draft" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("button.recap-node-token")).toBeTruthy());
    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Normalized recap preview")).not.toBeInTheDocument();
    expect(ingest.mock.calls.every(([body]) => body.operation === "inspect_status")).toBe(true);
    expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledWith(
      expect.objectContaining({ focus: expect.objectContaining({ sessionId: "session-10" }) }),
    );

    initialView.unmount();
    render(<IngestionModule campaignId="longmont-c2" session={11} managedWorldId="elderwyld" initialSourceSession={10} />);
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("button.recap-node-token")).toBeTruthy());
    await waitFor(() => expect(screen.getByRole("button", { name: "Return to draft" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Return to draft" }));
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("session")).toBe("session-11"));
    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText);
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(11);
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(draftText);
  });

  it("keeps a mismatched draft recoverable when a direct saved recap route cannot be verified", async () => {
    const user = setupIngestUser();
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10");
    const draftText = "Session 11 draft that must survive an unverified Session 10 route.";
    const storageKey = "dmb.ingestion.longmont-c2.session.11";
    window.localStorage.setItem(storageKey, JSON.stringify({
      version: 3,
      rawText: draftText,
      recapSession: 11,
      slug: "",
      title: "Session 11 - Draft in progress",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      ignoreDiskResume: false,
    }));
    vi.mocked(recapIngestApi.postRecapIngest).mockResolvedValue(makeStatus({
      campaign_id: "longmont-c2",
      session: 10,
      status: "initialized",
      states: ["ingest_status_inspected"],
      entity_spelling_audit: [],
    }));

    render(<IngestionModule campaignId="longmont-c2" session={11} managedWorldId="elderwyld" initialSourceSession={10} />);

    expect(await screen.findByRole("status")).toHaveTextContent("Draft preserved · Session 11");
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    expect(within(toolbar).getByRole("button", { name: "Return to draft" })).toBeInTheDocument();
    expect(within(toolbar).queryByRole("button", { name: "New recap" })).not.toBeInTheDocument();
    expect(within(toolbar).queryByRole("button", { name: "Paste recap" })).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}")).toMatchObject({
      rawText: draftText,
      recapSession: 11,
    });

    await user.click(within(toolbar).getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText);
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(11);
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(draftText);
  });

  it("keeps a matching draft editable and offers its saved reader without losing text", async () => {
    const user = setupIngestUser();
    const draftText = "Unfinished notes that must survive opening the saved recap.";
    const artifact = {
      schema_version: "dmb_recap_artifact_record_v1" as const,
      artifact_id: "artifact:recap:longmont-c2:session-10",
      campaign_id: "longmont-c2",
      session_id: "session-10",
      source_recap_path: "Session 10 - Mireward.md",
      run_bundle_uri: "bundle",
      run_manifest_uri: "manifest",
      source_span_index_uri: "index",
      graph_run_refs: [],
      default_projection_mode: "preview_union" as const,
      registered_at: "2026-06-29T00:00:00Z",
      updated_at: "2026-06-29T00:00:00Z",
      registry_source: "scan" as const,
    };
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-10");
    const storageKey = "dmb.ingestion.longmont-c2.session.29";
    window.localStorage.setItem(storageKey, JSON.stringify({
      version: 3,
      rawText: draftText,
      recapSession: 10,
      slug: "",
      title: "Session 10 - Draft in progress",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      ignoreDiskResume: false,
    }));
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [artifact],
    });
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (body) =>
      makeStatus({
        campaign_id: body.campaign_id,
        session: body.session,
        status: "recap_reused",
        states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
        paths: {
          ...makeStatus().paths,
          canonical_recap: "Session 10 - Mireward.md",
          normalized_recap: "Session 10 - Mireward.md",
        },
        ingest_report: {
          corpus_impact: [
            { key: "canonical_recap", relpath: "Session 10 - Mireward.md", exists: true },
            { key: "normalized_recap", relpath: "Session 10 - Mireward.md", exists: true },
          ],
        },
        entity_spelling_audit: [],
      }),
    );
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" />);

    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText);
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(toolbar).getByRole("status")).toHaveTextContent(/Unsaved draft open/i));
    expect(within(toolbar).getByRole("button", { name: "View saved recap" })).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("view")).toBeNull();

    await user.click(within(toolbar).getByRole("button", { name: "View saved recap" }));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(draftText);
    expect(within(toolbar).getByRole("button", { name: "Return to draft" })).toBeInTheDocument();

    await user.click(within(toolbar).getByRole("button", { name: "Return to draft" }));
    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText);
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(10);
    expect(new URLSearchParams(window.location.search).get("view")).toBeNull();
  });

  it("Process uses the combined operation and opens the node-bearing recap", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "run-session-22",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    const ingest = mockRecapIngestWithInspect(() => result);
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    render(<IngestionModule campaignId="longmont-c2" session={23} managedWorldId="elderwyld" />);
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
      "Session 22 - Mireward Road and Lysandro",
    );
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    await waitFor(() =>
      expect(ingest).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "generate_recap_memory",
          session: 22,
          raw_text: "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
          include_graph_extraction: true,
          graph_model_id: "deepseek/deepseek-v4.1-flash-1017",
        }),
      ),
    );
    expect(ingest.mock.calls.filter(([body]) => body.operation !== "inspect_status")).toHaveLength(1);
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Session 22 — Mireward Road" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("button.recap-node-token")).toBeTruthy());
    expect(document.querySelector("button.recap-node-token")).toHaveTextContent("Mireward");
    expect(screen.getByText(/Extraction candidate · 1 nodes · 0 relationships/)).toBeInTheDocument();
    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(screen.queryByText("The party pressed on.")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Stage + Preview" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply + Normalize" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Build Frontmatter Seed" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run Breadcrumb Ingest" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Materialize Session Memory" })).not.toBeInTheDocument();
    expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-22", "elderwyld");
    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
    expect(liveApi.getHistoricalRecapWorldProjection).not.toHaveBeenCalled();
    await user.click(document.querySelector("button.recap-node-token")!);
    expect(await screen.findByRole("complementary",{name:"Candidate: Mireward"})).toBeInTheDocument();
    expect(screen.getByText("Candidate-only place")).toBeInTheDocument();
    expect(screen.getByLabelText("Candidate reader advanced details").querySelector("pre")?.textContent).toContain("The party presses on near Mireward.");
    await user.click(screen.getByRole("button",{name:"View admitted memory"}));
    expect(await screen.findByText(/current admitted World Graph/)).toBeInTheDocument();
    expect(liveApi.getHistoricalRecapWorldProjection).toHaveBeenCalledWith("run-session-22","elderwyld");
    await user.click(screen.getByRole("button",{name:"View extracted candidates"}));
    expect(await screen.findByText(/Extraction candidate · 1 nodes/)).toBeInTheDocument();
  });

  it("opens Graph Review for the exact Process run and current source context", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "run-session-22",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    mockRecapIngestWithInspect(() => result);
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockImplementation(async (runId, managedWorldId) => ({
      ...candidateRecapProjectionForRun(runId),
      managedWorldId: managedWorldId ?? "elderwyld",
    }));
    const onPopState = vi.fn();
    window.addEventListener("popstate", onPopState);

    render(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />);
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
      "Session 22 - Mireward Road and Lysandro",
    );
    await user.click(screen.getByRole("button", { name: "Process recap" }));
    const graphReview = await screen.findByRole("button", { name: "Open Graph Review" });
    expect(graphReview).toBeEnabled();

    await user.click(graphReview);

    const params = new URLSearchParams(window.location.search);
    expect(window.location.pathname).toBe("/ingest");
    expect(params.get("world")).toBe("elderwyld");
    expect(params.get("campaign")).toBe("longmont-c2");
    expect(params.get("session")).toBe("session-22");
    expect(params.get("extractionRunId")).toBe("run-session-22");
    expect(params.get("sourceArtifactId")).toBe("artifact:recap:longmont-c2:session-22");
    expect(onPopState).toHaveBeenCalledTimes(1);

    window.removeEventListener("popstate", onPopState);
  });

  it("keeps Graph Review unavailable when the current result has no exact run ID", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    mockRecapIngestWithInspect(() => result);
    render(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />);
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
      "Session 22 - Mireward Road and Lysandro",
    );
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    const unavailable = await screen.findByRole("button", { name: "Graph Review unavailable: exact extraction run required" });
    expect(unavailable).toBeDisabled();
    expect(screen.getByText("Graph Review needs an exact extraction run for this session.")).toBeInTheDocument();
    expect(new URLSearchParams(window.location.search).get("extractionRunId")).toBeNull();
  });

  it("does not substitute the current session projection when the exact extraction run is unavailable", async () => {
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "run-session-22",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    mockRecapIngestWithInspect(() => result);
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockRejectedValueOnce(
      new Error("Exact extraction run source is unavailable."),
    );
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");

    render(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />);
    await fillRecapInputs(user, "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.", "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Exact extraction run source is unavailable.");
    expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-22", "elderwyld");
    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: /recap node/i })).not.toBeInTheDocument();
  });

  it("rejects an exact projection that echoes a different managed World", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "run-session-22",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    mockRecapIngestWithInspect(() => result);
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockResolvedValueOnce({
      ...candidateRecapProjectionForRun("run-session-22"),
      managedWorldId: "conks-and-cons",
    });

    render(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />);
    await fillRecapInputs(user, "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.", "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("does not match the selected managed World binding");
    expect(candidateApi.getExactRunCandidateProjection).toHaveBeenCalledWith("run-session-22", "elderwyld");
    expect(liveApi.postWorldGraphRecapProjection).not.toHaveBeenCalled();
  });

  it("ignores an old exact-run reply across an A→B→A managed-World selection", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    const user = setupIngestUser();
    const result = makeStatus({
      status: "ready_for_planning_activation",
      states: ["raw_text_received", "recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "run-session-22",
          candidate_node_count: 3,
          candidate_edge_count: 2,
        },
      },
    });
    mockRecapIngestWithInspect(() => result);
    const oldWorldA = deferred<ExactRunCandidateProjection>();
    const worldB = deferred<ExactRunCandidateProjection>();
    const newWorldA = deferred<ExactRunCandidateProjection>();
    const managedWorldIds: string[] = [];
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockImplementation((_runId, managedId) => {
      managedWorldIds.push(managedId ?? "");
      if (managedWorldIds.length === 1) return oldWorldA.promise;
      if (managedWorldIds.length === 2) return worldB.promise;
      return newWorldA.promise;
    });

    const { rerender } = render(
      <IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />,
    );
    await fillRecapInputs(user, "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.", "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Process recap" }));
    await waitFor(() => expect(managedWorldIds).toEqual(["elderwyld"]));

    rerender(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="conks-and-cons" />);
    await waitFor(() => expect(managedWorldIds).toEqual(["elderwyld", "conks-and-cons"]));
    rerender(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" />);
    await waitFor(() => expect(managedWorldIds).toEqual(["elderwyld", "conks-and-cons", "elderwyld"]));

    await act(async () => {
      oldWorldA.resolve({
        ...candidateRecapProjectionForRun("run-session-22"),
        managedWorldId: "wrong-old-world",
      });
      await oldWorldA.promise;
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();

    await act(async () => {
      newWorldA.resolve(candidateRecapProjectionForRun("run-session-22"));
      await newWorldA.promise;
    });
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("stops Process on a saved-source conflict and keeps the pasted recap in the editor", async () => {
    const user = setupIngestUser();
    const ingest = mockRecapIngestWithInspect(() =>
      makeStatus({
        status: "recap_applied",
        states: ["staged_raw_notes_conflict", "staged_raw_notes_reused"],
        warnings: ["staged raw notes already exists; pasted raw text was not used"],
      }),
    );

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    const pasted = "Session 22 - Mireward Road and Lysandro\n\nDifferent pasted text.";
    await fillRecapInputs(user, pasted, "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    expect(await screen.findByText("Saved recap needs your attention")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(pasted);
    expect(screen.queryByRole("region", { name: "Graph-enriched recap" })).not.toBeInTheDocument();
    expect(ingest.mock.calls.filter(([body]) => body.operation !== "inspect_status")).toHaveLength(1);
  });

  it("keeps a Process error concise and exposes diagnostics only on demand", async () => {
    const user = setupIngestUser();
    mockRecapIngestWithInspect(() => makeStatus({
      status: "error",
      states: ["recap_generation_failed"],
      errors: ["The recap could not be prepared."],
    }));

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
      "Session 22 - Mireward Road and Lysandro",
    );
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Processing failed"));
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    const feedbackDetails = within(toolbar).getByText("Details").closest("details");
    expect(feedbackDetails).not.toHaveAttribute("open");
    const errorDetail = within(feedbackDetails as HTMLElement).getByText("The recap could not be prepared.");
    expect(errorDetail).not.toBeVisible();
    await user.click(within(toolbar).getByText("Details"));
    expect(errorDetail).toBeVisible();
    expect(within(screen.getByRole("region", { name: "Graph preview status" })).queryByText(/Last ingest error:/)).not.toBeInTheDocument();
  });

  it("reports blocked graph extraction after one Process action", async () => {
    const user = setupIngestUser();
    const ingest = mockRecapIngestWithInspect(() =>
      makeStatus({
        status: "ready_for_planning_activation",
        states: ["recap_applied", "normalized_created", "graph_source_bundle_ready"],
        ingest_report: {
          graph_preview: {
            status: "source_span_bundle_ready",
            extraction_mode: "llm_blocked",
            blocked_reason: "OPENAI_API_KEY is not configured",
            can_open_union_graph: false,
          },
        },
      }),
    );

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await fillRecapInputs(
      user,
      "Session 22 - Mireward Road and Lysandro\n\nThe party pressed on.",
      "Session 22 - Mireward Road and Lysandro",
    );
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    expect(
      await screen.findByText(
        /Graph extract was blocked: OPENAI_API_KEY is not configured/,
        {},
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(ingest.mock.calls.filter(([body]) => body.operation !== "inspect_status")).toHaveLength(1);
    expect(screen.queryByRole("button", { name: "Open Recap View" })).not.toBeInTheDocument();
  });

  it("submits build_graph_preview_bundle and shows source bundle blocked state", async () => {
    const user = setupIngestUser();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["recap_applied", "normalized_created"],
        });
      }
      if (body.operation === "build_graph_preview_bundle") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["graph_source_bundle_ready"],
          ingest_report: {
            graph_preview: {
              status: "source_span_bundle_ready",
              manifest_path: "out/graph_memory/runs/longmont-c2/session-22/run/graph_ingest_run_manifest.json",
              blocked_reason: "Graph source bundle ready. Candidate graph extraction has not run yet.",
            },
          },
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: [],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.click(screen.getByText("Advanced graph tools"));
    const extractToggle = await screen.findByLabelText(
      "Extract graph from recap with category extraction (DeepSeek V4.1 Flash 1017 · pinned)",
    );
    expect(extractToggle).toBeInTheDocument();
    await user.click(extractToggle);
    await waitFor(
      () => expect(screen.getByRole("button", { name: "Build Graph Preview" })).toBeEnabled(),
      { timeout: 5000 },
    );
    await user.click(screen.getByRole("button", { name: "Build Graph Preview" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          operation: "build_graph_preview_bundle",
          session: 22,
          extract_graph: true,
          graph_model_id: "deepseek/deepseek-v4.1-flash-1017",
        }),
      ),
    );
    expect(screen.getAllByText("Graph").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Graph source bundle ready. Candidate graph extraction has not run yet.").length).toBeGreaterThan(0);
    await user.click(screen.getByText("Evidence & details"));
    const graphPanel = screen.getByRole("region", { name: "Graph preview status" });
    expect(graphPanel).toHaveTextContent("Graph extraction: candidate pending");
    expect(graphPanel).not.toHaveTextContent("Graph extraction: blocked");
  });

  it("enables materialize_preview_supergraph with category extraction and no candidate path", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["recap_applied", "normalized_created"],
        });
      }
      if (body.operation === "materialize_preview_supergraph") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["preview_union_store_ready"],
          ingest_report: {
            graph_preview: {
              status: "preview_union_store_ready",
              preview_union_store_path: "out/graph_memory/runs/longmont-c2/session-22/run/preview_union_supergraph.json",
              can_open_union_graph: true,
              extraction_mode: "category_decomposed",
            },
          },
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: [],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.click(screen.getByText("Advanced graph tools"));
    await user.type(screen.getByLabelText("Candidate graph path"), "out/candidate.json");
    await user.click(screen.getByLabelText("Extract graph from recap with category extraction (DeepSeek V4.1 Flash 1017 · pinned)"));
    expect(screen.getByLabelText("Candidate graph path")).toBeDisabled();
    expect(screen.getByLabelText("Candidate graph path")).toHaveValue("");
    await waitFor(() => expect(screen.getByRole("button", { name: "Materialize Preview Supergraph" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Materialize Preview Supergraph" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          operation: "materialize_preview_supergraph",
          session: 22,
          candidate_graph_path: undefined,
          extract_graph: true,
          graph_model_id: "deepseek/deepseek-v4.1-flash-1017",
          materialize_after_extract: true,
        }),
      ),
    );
  });

  it("submits materialize_preview_supergraph with a candidate graph path", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["recap_applied", "normalized_created"],
        });
      }
      if (body.operation === "materialize_preview_supergraph") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["preview_union_store_ready"],
          ingest_report: {
            graph_preview: {
              status: "preview_union_store_ready",
              candidate_graph_path: "out/candidate.json",
              preview_union_store_path: "out/graph_memory/runs/longmont-c2/session-22/run/preview_union_supergraph.json",
              can_open_union_graph: true,
              node_count: 2,
              edge_count: 1,
              extracted_nodes: [
                { node_id: "character_stafl", kind: "character", label: "Stafl" },
                { node_id: "location_mireward_gate", kind: "location", label: "Mireward Gate" },
              ],
            },
          },
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: [],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.click(screen.getByText("Advanced graph tools"));
    await user.type(screen.getByLabelText("Candidate graph path"), "out/candidate.json");
    await waitFor(() => expect(screen.getByRole("button", { name: "Materialize Preview Supergraph" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Materialize Preview Supergraph" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          operation: "materialize_preview_supergraph",
          session: 22,
          candidate_graph_path: "out/candidate.json",
        }),
      ),
    );
    expect(screen.getByText("status: preview_union_store_ready")).toBeInTheDocument();
    expect(screen.getByText(/Nodes in this preview union \(2\)/)).toBeInTheDocument();
    expect(screen.getByText("Stafl")).toBeInTheDocument();
    expect(screen.getByText("Mireward Gate")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Graph preview status" })).toHaveTextContent("preview graph materialized");
  });

  it("keeps file replacement controls behind explicit advanced disclosure", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    expect(screen.queryByText(/Replace saved raw notes/)).not.toBeInTheDocument();
    await user.click(screen.getByText("Advanced file controls"));
    await user.click(screen.getByLabelText(/Show file replacement/));
    expect(screen.getByText(/Replace saved raw notes/)).toBeInTheDocument();
    expect(screen.getByText(/Replace existing canonical recap file/)).toBeInTheDocument();
    expect(screen.getByLabelText("Canonical file name override")).toBeInTheDocument();
  });

  it("offers a reconciliation card and repairs duplicate normalized recaps", async () => {
    const user = userEvent.setup();
    const candidates = [
      {
        basename: "Session 23 - Mireward Gate Battle",
        relpath:
          "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md",
        size_bytes: 9746,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: false,
        recommended: true,
      },
      {
        basename: "Session 23 - ingest",
        relpath:
          "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - ingest.md",
        size_bytes: 10476,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: true,
        recommended: false,
      },
    ];
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "reconcile_normalized_recap") {
        return makeStatus({
          session: 23,
          status: "recap_applied",
          states: ["ingest_status_inspected", "normalized_recap_reconciled", "recap_reused"],
          ingest_report: {
            reconciled_kept_basename: body.keep_basename,
            reconciled_archived: [{ from: "a", to: "b" }],
          },
        });
      }
      return makeStatus({
        session: 23,
        status: "initialized",
        states: ["ingest_status_inspected", "normalized_recap_duplicates"],
        entity_spelling_audit: [],
        ingest_report: { normalized_recap_candidates: candidates },
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={24} />);

    await screen.findByText("Resolve duplicate normalized recaps");
    expect(screen.getAllByText("Session 23 - Mireward Gate Battle").length).toBeGreaterThan(0);
    expect(screen.getByText("Session 23 - ingest")).toBeInTheDocument();
    expect(screen.getByText("recommended")).toBeInTheDocument();
    expect(screen.getByText("tool-shaped")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Repair and Prove" }));

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "reconcile_normalized_recap",
          keep_basename: "Session 23 - Mireward Gate Battle",
          session: 23,
        }),
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText("Resolve duplicate normalized recaps")).not.toBeInTheDocument(),
    );
  });

  it("clears reconciliation loading when the selected session changes", async () => {
    const user = userEvent.setup();
    const candidates = [
      {
        basename: "Session 23 - Mireward Gate Battle",
        relpath: "Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md",
        size_bytes: 9000,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: false,
        recommended: true,
      },
      {
        basename: "Session 23 - ingest",
        relpath: "Session Recaps/_normalized/Session 23 - ingest.md",
        size_bytes: 10000,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: true,
        recommended: false,
      },
    ];
    let finishReconcile!: (result: RecapIngestStatus) => void;
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (request) => {
      if (request.operation === "reconcile_normalized_recap") {
        return new Promise((resolve) => { finishReconcile = resolve; });
      }
      return makeStatus({
        campaign_id: request.campaign_id,
        session: request.session,
        status: "initialized",
        states: ["ingest_status_inspected", "normalized_recap_duplicates"],
        ingest_report: { normalized_recap_candidates: request.session === 23 ? candidates : [] },
        entity_spelling_audit: [],
      });
    });

    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-23");
    render(<IngestionModule campaignId="longmont-c2" session={24} />);
    await screen.findByText("Resolve duplicate normalized recaps");
    await user.click(screen.getByRole("button", { name: "Repair and Prove" }));
    await waitFor(() => expect(finishReconcile).toBeTypeOf("function"));
    expect(screen.getByRole("button", { name: "Repairing..." })).toBeDisabled();

    const sessionInput = screen.getByLabelText("Recap/source session");
    fireEvent.change(sessionInput, { target: { value: "24" } });
    fireEvent.blur(sessionInput);
    fireEvent.change(sessionInput, { target: { value: "23" } });
    fireEvent.blur(sessionInput);
    await screen.findByText("Resolve duplicate normalized recaps");

    expect(screen.getByRole("button", { name: "Repair and Prove" })).toBeEnabled();
    await act(async () => finishReconcile(makeStatus({
      session: 23,
      status: "recap_applied",
      states: ["normalized_recap_reconciled", "recap_reused"],
    })));
    expect(screen.getByRole("button", { name: "Repair and Prove" })).toBeEnabled();
    expect(spy).toHaveBeenCalledWith(expect.objectContaining({
      operation: "reconcile_normalized_recap",
      campaign_id: "longmont-c2",
      session: 23,
    }));
  });

  it("loads a prior processed recap directly into the enriched graph view", async () => {
    const user = setupIngestUser();
    const artifact = {
      schema_version: "dmb_recap_artifact_record_v1" as const,
      artifact_id: "artifact:recap:longmont-c2:session-23",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      source_recap_path: "corpus/eldyrwild-markdown/Session 23 - Mireward Gate Battle.md",
      run_bundle_uri: "bundle",
      run_manifest_uri: "manifest",
      source_span_index_uri: "index",
      graph_run_refs: [],
      default_projection_mode: "preview_union" as const,
      registered_at: "2026-06-29T00:00:00Z",
      updated_at: "2026-06-29T00:00:00Z",
      registry_source: "scan" as const,
    };
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [artifact],
    });
    const ingest = vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (body) =>
      makeStatus({
        campaign_id: body.campaign_id,
        session: body.session,
        status: "recap_reused",
        states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
        paths: {
          ...makeStatus().paths,
          canonical_recap: "Session 23 - Mireward Gate Battle.md",
          normalized_recap: "Session 23 - Mireward Gate Battle.md",
        },
        ingest_report: {
          corpus_impact: [
            { key: "canonical_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
            { key: "normalized_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
          ],
        },
        entity_spelling_audit: [],
      }),
    );
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    const draftText = "Session 24 draft that must survive reading Session 23.";
    const storageKey = "dmb.ingestion.longmont-c2.session.24";
    window.localStorage.setItem(storageKey, JSON.stringify({
      version: 3,
      rawText: draftText,
      recapSession: 24,
      slug: "",
      title: "Session 24 - Draft in progress",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      ignoreDiskResume: false,
    }));
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    const initialView = render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
    await screen.findByRole("option", { name: /Session 23/ });
    await user.selectOptions(screen.getByLabelText("Prior processed recap"), artifact.artifact_id);
    await user.click(screen.getByRole("button", { name: "Load processed recap" }));

    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("button.recap-node-token")).toBeTruthy());
    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(screen.queryByText("The party held the gate.")).not.toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(draftText);
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").recapSession).toBe(24);
    expect(screen.getByRole("button", { name: "Return to draft" })).toBeInTheDocument();
    expect(ingest.mock.calls.every(([body]) => body.operation === "inspect_status")).toBe(true);

    initialView.unmount();
    render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
    await waitFor(() => expect(document.querySelector("button.recap-node-token")).toBeTruthy());
    await waitFor(() => expect(screen.getByRole("button", { name: "Return to draft" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Return to draft" }));
    await waitFor(() => expect(new URLSearchParams(window.location.search).get("session")).toBe("session-24"));
    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText);
    expect(screen.getByLabelText("Recap/source session")).toHaveValue(24);
    expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(draftText);
  });

  it.each(["late resolution", "late rejection"] as const)(
    "persists edits after returning to a draft before a pending recap inspection's %s",
    async (completion) => {
      const user = setupIngestUser();
      const artifact = {
        schema_version: "dmb_recap_artifact_record_v1" as const,
        artifact_id: "artifact:recap:longmont-c2:session-23",
        campaign_id: "longmont-c2",
        session_id: "session-23",
        source_recap_path: "corpus/eldyrwild-markdown/Session 23 - Mireward Gate Battle.md",
        run_bundle_uri: "bundle",
        run_manifest_uri: "manifest",
        source_span_index_uri: "index",
        graph_run_refs: [],
        default_projection_mode: "preview_union" as const,
        registered_at: "2026-06-29T00:00:00Z",
        updated_at: "2026-06-29T00:00:00Z",
        registry_source: "scan" as const,
      };
      vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
        schema_version: "dmb_recap_artifacts_registry_v1",
        version: "1",
        records: [artifact],
      });
      const pendingInspection = deferred<RecapIngestStatus>();
      vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (request) => {
        if (request.operation !== "inspect_status") {
          throw new Error(`Unexpected ingestion write: ${request.operation}`);
        }
        if (request.session === 23) return pendingInspection.promise;
        return makeStatus({
          campaign_id: request.campaign_id,
          session: request.session,
          status: "initialized",
          states: ["ingest_status_inspected"],
          entity_spelling_audit: [],
        });
      });

      const draftText = "Session 24 draft that must survive reading Session 23.";
      const updatedDraft = `${draftText} New edits after returning.`;
      const storageKey = "dmb.ingestion.longmont-c2.session.24";
      window.localStorage.setItem(storageKey, JSON.stringify({
        version: 3,
        rawText: draftText,
        recapSession: 24,
        slug: "",
        title: "Session 24 - Draft in progress",
        showAdvanced: false,
        forceStage: false,
        forceRecap: false,
        ignoreDiskResume: false,
      }));
      window.history.replaceState({}, "", "/ingest?world=elderwyld");
      const firstView = render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
      await screen.findByRole("option", { name: /Session 23/ });
      await waitFor(() =>
        expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(draftText),
      );
      await user.selectOptions(screen.getByLabelText("Prior processed recap"), artifact.artifact_id);
      await user.click(screen.getByRole("button", { name: "Load processed recap" }));
      await user.click(await screen.findByRole("button", { name: "Return to draft" }));

      const recapEditor = await screen.findByRole("textbox", { name: "Write or paste a recap" });
      await user.type(recapEditor, " New edits after returning.");
      await waitFor(() => {
        expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(updatedDraft);
      });

      await act(async () => {
        if (completion === "late resolution") {
          pendingInspection.resolve(makeStatus({
            session: 23,
            status: "recap_reused",
            states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
          }));
        } else {
          pendingInspection.reject(new Error("Inspection failed after draft return"));
        }
      });

      expect(JSON.parse(window.localStorage.getItem(storageKey) ?? "{}").rawText).toBe(updatedDraft);
      expect(screen.getByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(updatedDraft);
      firstView.unmount();
      render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
      expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue(updatedDraft);
    },
  );

  it("keeps raw source hidden if the World Graph projection is unavailable", async () => {
    const user = setupIngestUser();
    const artifact = {
      schema_version: "dmb_recap_artifact_record_v1" as const,
      artifact_id: "artifact:recap:longmont-c2:session-23",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      source_recap_path: "corpus/eldyrwild-markdown/Session 23 - Mireward Gate Battle.md",
      run_bundle_uri: "bundle",
      run_manifest_uri: "manifest",
      source_span_index_uri: "index",
      graph_run_refs: [],
      default_projection_mode: "preview_union" as const,
      registered_at: "2026-06-29T00:00:00Z",
      updated_at: "2026-06-29T00:00:00Z",
      registry_source: "scan" as const,
    };
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [artifact],
    });
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (body) =>
      makeStatus({
        campaign_id: body.campaign_id,
        session: body.session,
        status: "recap_reused",
        states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
        paths: {
          ...makeStatus().paths,
          normalized_recap: "Session 23 - Mireward Gate Battle.md",
        },
        ingest_report: {
          corpus_impact: [
            { key: "canonical_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
            { key: "normalized_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
          ],
        },
        entity_spelling_audit: [],
      }),
    );
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockRejectedValue(new Error("World projection unavailable"));

    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
    await screen.findByRole("option", { name: /Session 23/ });
    await user.selectOptions(screen.getByLabelText("Prior processed recap"), artifact.artifact_id);
    await user.click(screen.getByRole("button", { name: "Load processed recap" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("World projection unavailable");
    expect(screen.queryByRole("textbox", { name: "Write or paste a recap" })).not.toBeInTheDocument();
    expect(screen.queryByText("The party held the gate.")).not.toBeInTheDocument();
  });

  it("starts a blank recap from the enriched view", async () => {
    const user = setupIngestUser();
    vi.mocked(liveApi.getRecapArtifacts).mockResolvedValue({
      schema_version: "dmb_recap_artifacts_registry_v1",
      version: "1",
      records: [{
        schema_version: "dmb_recap_artifact_record_v1",
        artifact_id: "artifact:recap:longmont-c2:session-23",
        campaign_id: "longmont-c2",
        session_id: "session-23",
        source_recap_path: "Session 23 - Mireward Gate Battle.md",
        run_bundle_uri: "bundle",
        run_manifest_uri: "manifest",
        source_span_index_uri: "index",
        graph_run_refs: [],
        default_projection_mode: "preview_union",
        registered_at: "2026-06-29T00:00:00Z",
        updated_at: "2026-06-29T00:00:00Z",
        registry_source: "scan",
      }],
    });
    vi.mocked(recapIngestApi.postRecapIngest).mockImplementation(async (body) =>
      makeStatus({
        campaign_id: body.campaign_id,
        session: body.session,
        status: "recap_reused",
        states: ["recap_reused", "normalized_reused", "normalized_current", "ingest_status_inspected"],
        paths: {
          ...makeStatus().paths,
          normalized_recap: "Session 23 - Mireward Gate Battle.md",
        },
        ingest_report: {
          corpus_impact: [
            { key: "canonical_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
            { key: "normalized_recap", relpath: "Session 23 - Mireward Gate Battle.md", exists: true },
          ],
        },
      }),
    );
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    render(<IngestionModule campaignId="longmont-c2" session={24} managedWorldId="elderwyld" />);
    await screen.findByRole("option", { name: /Session 23/ });
    await user.selectOptions(screen.getByLabelText("Prior processed recap"), "artifact:recap:longmont-c2:session-23");
    await user.click(screen.getByRole("button", { name: "Load processed recap" }));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "New recap" }));

    expect(await screen.findByRole("textbox", { name: "Write or paste a recap" })).toHaveValue("");
    expect(screen.queryByRole("region", { name: "Graph-enriched recap" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Process recap" })).not.toBeInTheDocument();
  });

  it("keeps the empty navigation quiet while fresh disk inspection replaces stale draft status", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    const staleResult = makeStatus({
      session: 29,
      status: "recap_applied",
      states: [
        "staged_raw_notes_reused",
        "recap_reused",
        "normalized_reused",
        "recap_applied",
        "ingest_status_inspected",
        "graph_candidate_ready",
      ],
      warnings: ["A prior draft warning"],
      next_actions: ["A stale next action"],
      paths: {
        ...makeStatus().paths,
        canonical_recap: "saved/canonical-session-29.md",
        normalized_recap: "saved/normalized-session-29.md",
      },
      ingest_report: {
        graph_preview: { status: "candidate_validation_ready" },
      },
    });
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "",
      recapSession: 29,
      slug: "",
      title: "Session 29 - The Meat Mind of Mireward Reach",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: staleResult,
      state: { status: "recap_applied", result: staleResult },
      ignoreDiskResume: false,
    }));

    let resolveInspect: ((status: RecapIngestStatus) => void) | undefined;
    const inspectPromise = new Promise<RecapIngestStatus>((resolve) => {
      resolveInspect = resolve;
    });
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") return inspectPromise;
      return makeStatus({ session: 29 });
    });

    render(<IngestionModule campaignId="longmont-c2" session={29} initialSourceSession={29} />);

    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status" })));
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    expect(within(toolbar).queryByRole("status")).not.toBeInTheDocument();
    expect(within(toolbar).queryByText(/reused without overwrite/i)).not.toBeInTheDocument();

    await act(async () => {
      resolveInspect?.(makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        paths: {},
        warnings: [],
        next_actions: [],
        ingest_report: {
          corpus_impact: [
            { key: "canonical_recap", relpath: "corpus/missing-canonical.md", exists: false },
            { key: "normalized_recap", relpath: "corpus/missing-normalized.md", exists: false },
          ],
        },
        entity_spelling_audit: [],
      }));
      await inspectPromise;
    });

    await waitFor(() => expect(screen.getByLabelText("Session title")).toHaveValue("Session 29 - The Meat Mind of Mireward Reach"));
    expect(within(toolbar).queryByRole("status")).not.toBeInTheDocument();
    expect(within(toolbar).queryByText(/reused without overwrite|stale next action/i)).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByText("Evidence & details"));
    const evidence = screen.getByRole("complementary", { name: "Ingestion evidence and proof" });
    expect(evidence).toHaveTextContent("Missing");
    expect(evidence).not.toHaveTextContent("saved/normalized-session-29.md");
    expect(evidence).not.toHaveTextContent("normalized_reused");
    expect(evidence.querySelector(".ingestion-readiness-lanes")).toBeNull();
  });

  it("does not promote an unverified saved status when disk inspection fails", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    const staleResult = makeStatus({
      session: 29,
      status: "recap_applied",
      states: ["recap_reused", "normalized_reused", "recap_applied"],
      paths: {
        ...makeStatus().paths,
        normalized_recap: "saved/unverified-normalized-session-29.md",
      },
    });
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "",
      recapSession: 29,
      slug: "",
      title: "Session 29 - The Meat Mind of Mireward Reach",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: staleResult,
      state: { status: "recap_applied", result: staleResult },
      ignoreDiskResume: false,
    }));
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockRejectedValue(new Error("offline"));

    render(<IngestionModule campaignId="longmont-c2" session={29} initialSourceSession={29} />);

    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status" })));
    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    const warning = await within(toolbar).findByRole("alert");
    expect(warning).toHaveTextContent("Could not verify saved ingest status");
    expect(warning).not.toHaveTextContent(/reused without overwrite/i);
    await userEvent.setup().click(within(toolbar).getByText("Details"));
    expect(within(toolbar).getByText(/browser's saved status may be out of date/i)).toBeVisible();
    expect(document.body.textContent).not.toContain("saved/unverified-normalized-session-29.md");
  });

  it("keeps a completed Process result when the earlier saved-status check fails", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "Session 29 - A Path North\\n\\nThe party finds a path north.",
      recapSession: 29,
      slug: "",
      title: "Session 29 - A Path North",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: null,
      state: { status: "idle" },
      ignoreDiskResume: false,
    }));

    let rejectInspect: ((error: Error) => void) | undefined;
    const inspectPromise = new Promise<RecapIngestStatus>((_resolve, reject) => {
      rejectInspect = reject;
    });
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") return inspectPromise;
      return makeStatus({
        session: 29,
        status: "ready_for_planning_activation",
        states: ["recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
        ingest_report: {
          graph_preview: {
            status: "candidate_validation_ready",
            extraction_run_id: "session-29-run",
            candidate_node_count: 4,
            candidate_edge_count: 3,
          },
        },
      });
    });
    vi.mocked(liveApi.postWorldGraphRecapProjection).mockImplementation(async (request) => ({
      ...session23WorldGraphRecapFixture,
      campaignId: request.campaignId,
      sessionId: request.focus.sessionId!,
      snapshot: { ...session23WorldGraphRecapFixture.snapshot, focus: request.focus },
    }));

    const user = setupIngestUser();
    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" initialSourceSession={29} />);
    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status" })));
    expect(await screen.findByDisplayValue("Session 29 - A Path North\\n\\nThe party finds a path north.")).toBeInTheDocument();

    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await user.click(within(toolbar).getByRole("button", { name: "Process recap" }));

    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({
      operation: "generate_recap_memory",
      include_graph_extraction: true,
    })));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();

    await act(async () => {
      rejectInspect?.(new Error("inspection offline"));
      await inspectPromise.catch(() => undefined);
    });

    expect(within(toolbar).getByRole("status")).toHaveTextContent("Recap processed");
    expect(within(toolbar).queryByText("Could not verify saved ingest status")).not.toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();
  });

  it("keeps the acknowledged Process evidence when a later status inspection returns an older graph state", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    window.localStorage.setItem("dmb.ingestion.longmont-c2.session.29", JSON.stringify({
      version: 3,
      rawText: "Session 29 - A Path North\\n\\nThe party finds a path north.",
      recapSession: 29,
      slug: "",
      title: "Session 29 - A Path North",
      showAdvanced: false,
      forceStage: false,
      forceRecap: false,
      latestResult: null,
      state: { status: "idle" },
      ignoreDiskResume: false,
    }));

    const initialInspection = deferred<RecapIngestStatus>();
    const processResult = makeStatus({
      session: 29,
      status: "ready_for_planning_activation",
      states: ["recap_applied", "normalized_created", "normalized_current", "graph_candidate_ready"],
      ingest_report: {
        graph_preview: {
          status: "candidate_validation_ready",
          extraction_run_id: "session-29-acknowledged-run",
          candidate_node_count: 62,
          candidate_edge_count: 64,
        },
      },
      entity_spelling_audit: [],
    });
    const olderStatus = makeStatus({
      session: 29,
      status: "initialized",
      states: ["ingest_status_inspected"],
      ingest_report: {
        corpus_impact: [],
        graph_preview: { status: "missing" },
      },
      entity_spelling_audit: [],
    });
    let inspectionCount = 0;
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        inspectionCount += 1;
        if (inspectionCount === 1) return initialInspection.promise;
        return olderStatus;
      }
      return processResult;
    });
    vi.mocked(candidateApi.getExactRunCandidateProjection).mockImplementation(async (runId) =>
      candidateRecapProjectionForRun(runId),
    );

    const user = setupIngestUser();
    render(<IngestionModule campaignId="longmont-c2" session={29} managedWorldId="elderwyld" initialSourceSession={29} />);
    await waitFor(() => expect(ingestSpy).toHaveBeenCalledWith(expect.objectContaining({ operation: "inspect_status" })));
    expect(await screen.findByDisplayValue("Session 29 - A Path North\\n\\nThe party finds a path north.")).toBeInTheDocument();

    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await user.click(within(toolbar).getByRole("button", { name: "Process recap" }));
    expect(await screen.findByRole("region", { name: "Graph-enriched recap" })).toBeInTheDocument();

    // The mount-time inspection was invalidated by Process; a later ordinary
    // blur can still inspect disk and must not erase the acknowledged run.
    await act(async () => {
      initialInspection.resolve(makeStatus({
        session: 29,
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }));
    });
    fireEvent.blur(screen.getByLabelText("Recap/source session"));
    await waitFor(() => expect(inspectionCount).toBe(2));

    await user.click(screen.getByText("Evidence & details"));
    const graphPanel = screen.getByRole("region", { name: "Graph preview status" });
    expect(graphPanel).toHaveTextContent("Graph extraction: candidate ready");
    expect(graphPanel).toHaveTextContent("status: candidate_validation_ready");
    expect(screen.getByText("ready_for_planning_activation")).toBeInTheDocument();
    expect(screen.queryByText("No ingestion result yet.")).not.toBeInTheDocument();
  });

  it("allows replacing an existing preview graph when force re-extract is checked", async () => {
    const user = userEvent.setup();
    const ingestSpy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          session: 23,
          status: "ready_for_planning_activation",
          states: ["normalized_reused", "preview_union_store_ready", "ready_for_planning_activation"],
          ingest_report: {
            graph_preview: {
              status: "preview_union_store_ready",
              can_open_union_graph: true,
            },
          },
          entity_spelling_audit: [],
        });
      }
      if (body.operation === "generate_recap_memory") {
        expect(body.force_graph_run).toBe(true);
        expect(body.raw_text).toBeUndefined();
        return makeStatus({
          session: 23,
          status: "ready_for_planning_activation",
          states: ["normalized_reused", "preview_union_store_ready", "ready_for_planning_activation"],
          ingest_report: {
            graph_preview: {
              status: "preview_union_store_ready",
              manifest_path: "out/graph_memory/runs/longmont-c2/session-23/run-2/manifest.json",
              can_open_union_graph: true,
            },
          },
        });
      }
      return makeStatus({ session: 23, entity_spelling_audit: [] });
    });

    render(<IngestionModule campaignId="longmont-c2" session={24} />);

    await waitFor(() => expect(screen.getByText("Graph exists · choose Replace graph to run a fresh extraction.")).toBeInTheDocument());
    expect(screen.queryByText(/A graph already exists for this session/)).not.toBeInTheDocument();
    await user.click(screen.getByText("Advanced graph tools"));
    expect(screen.queryByText(/Check "Replace existing graph"/)).not.toBeInTheDocument();
    expect(screen.getAllByLabelText("Replace graph")).toHaveLength(1);
    const reextractButton = screen.getByRole("button", { name: "Process recap" });
    expect(reextractButton).toBeDisabled();

    const replaceGraph = screen.getByLabelText("Replace graph");
    expect(screen.getAllByLabelText("Replace graph")).toHaveLength(1);
    await user.click(replaceGraph);

    expect(screen.getByRole("button", { name: "Process recap" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Process recap" }));

    await waitFor(() =>
      expect(ingestSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "generate_recap_memory",
          session: 23,
          force_graph_run: true,
        }),
      ),
    );
  });

  it("keeps next action in the nav and shows each file proof once", async () => {
    const titled =
      "Longmont Campaign/Campaign 2/Session Recaps/Session 24 - Mireward Gate Battle.md";
    vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          session: 24,
          status: "ready_for_planning_activation",
          states: [
            "recap_reused",
            "normalized_reused",
            "ready_for_planning_activation",
            "graph_preview_missing",
            "ingest_status_inspected",
          ],
          paths: {
            ...makeStatus().paths,
            canonical_recap: titled,
            normalized_recap:
              "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md",
          },
          warnings: [],
          ingest_report: {
            graph_preview: { status: "missing" },
            corpus_impact: [
              {
                key: "canonical_recap",
                relpath: titled,
                exists: true,
                size_bytes: 8500,
              },
              {
                key: "normalized_recap",
                relpath:
                  "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 24 - Mireward Gate Battle.md",
                exists: true,
                size_bytes: 8900,
              },

            ],
          },
          entity_spelling_audit: [],
        });
      }
      return makeStatus({ session: 24, entity_spelling_audit: [] });
    });

    render(<IngestionModule campaignId="longmont-c2" session={25} />);

    const toolbar = screen.getByRole("navigation", { name: "Ingest workspace navigation" });
    await waitFor(() => expect(within(toolbar).getByRole("status")).toHaveTextContent(/Choose Process to build the enriched recap and graph context/i));
    expect(screen.queryByText("Recap memory")).not.toBeInTheDocument();
    expect(screen.queryByText("Graph preview")).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByText("Evidence & details"));
    const proof = screen.getByRole("region", { name: "Ingestion proof artifacts" });
    expect(proof).toHaveTextContent("Prove");
    expect(proof.querySelector(".ingestion-readiness-lanes")).toBeNull();

    const canonicalRows = screen.getAllByText("canonical recap");
    const proveCanonical = canonicalRows
      .map((node) => node.closest("li"))
      .find((row) => row?.textContent?.includes(titled));
    expect(proveCanonical).toBeTruthy();
    expect(proveCanonical).toHaveTextContent("Found");
  });
  it("review regression preserves editable source after reconciliation refusal", async () => {
    window.history.replaceState({}, "", "/ingest?world=elderwyld&campaign=longmont-c2&session=session-22");
    mockRecapIngestWithInspect(() => makeStatus({
      status: "needs_reconciliation",
      states: ["recap_preview_created", "canonical_recap_conflict", "derivative_reconciliation_required"],
      warnings: ["Canonical source differs; explicit replacement required."],
      entity_spelling_audit: [],
    }));
    const user=setupIngestUser();
    render(<IngestionModule campaignId="longmont-c2" session={22} managedWorldId="elderwyld" initialSourceSession={22} />);
    await fillRecapInputs(user,"The party now travels south.","Session 22 - Road North");
    await user.click(screen.getByRole("button",{name:"Process recap"}));
    await screen.findByText("Source needs attention");
    expect(screen.getByRole("textbox",{name:"Write or paste a recap"})).toHaveValue("The party now travels south.");
    expect(screen.queryByRole("region", { name: "Graph-enriched recap" })).not.toBeInTheDocument();
  });

});
