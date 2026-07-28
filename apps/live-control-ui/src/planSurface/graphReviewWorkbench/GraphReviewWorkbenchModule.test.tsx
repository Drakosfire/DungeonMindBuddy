import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import * as liveApi from "../../api/liveApi";
import type {
  ExtractPromoteConfirmReceipt,
  WorldGraphProjection,
} from "../../api/types";
import type { PlanContextDescriptor } from "../types";
import { GraphReviewLiveStateProvider, useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { GraphReviewWorkbenchModule } from "./GraphReviewWorkbenchModule";
import {
  catalogRunBindingKey,
  exactRunBindingKey,
} from "./graphReviewCommittedAuthority";
import { GraphReviewExactRunProjection } from "./GraphReviewExactRunProjection";
import { GraphReviewCommittedProjectionPanel } from "./GraphReviewCommittedProjectionPanel";
import { ProjectionProvider } from "../projection/projectionContext";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  ingestSession: 23,
  headerLabel: "Ingest",
};

const sessionWithRun = {
  session_id: "session-23",
  session_number: 23,
  campaign_id: "longmont-c2",
  gold_fixture_id: "gold-23",
  gold_manifest_path: "m23",
  gold_graph_path: "g23",
  gold_counts: { nodes: 2, edges: 1, evidence_refs: 1, beats: 0 },
  available_runs: [
    {
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
    },
  ],
};

function mockWorkbenchApis() {
  vi.spyOn(liveApi, "getGraphIngestRuns").mockResolvedValue({
    schema_version: "dmb_graph_ingest_run_registry_v1",
    version: "0.1",
    runs: sessionWithRun.available_runs,
  });
  vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
    schema_version: "dmb_graph_gold_review_sessions_v1",
    version: "0.1",
    sessions: [sessionWithRun],
  });
  vi.spyOn(liveApi, "getManualReviewBeds").mockResolvedValue({
    schema_version: "dmb_graph_manual_review_beds_v1",
    version: "0.1",
    beds: [],
  });
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
    markdown: "[Alden](dmb-node:alden) watched [Bera](dmb-node:bera).",
    focus: {
      focus_session_id: "session-23",
      focused_evidence_ref_ids: [],
      focused_edge_ids: [],
      focused_node_ids: [],
    },
    node_views: {
      alden: {
        node_id: "alden",
        label: "Alden",
        kind: "npc",
        role: "gate warden",
        summary: "Alden guards the western gate.",
        aliases: [],
        source_domains: [],
        evidence_badges: [],
        adjacency: [],
      },
      bera: {
        node_id: "bera",
        label: "Bera",
        kind: "npc",
        role: "scout",
        summary: "Bera scouts the old road.",
        aliases: [],
        source_domains: [],
        evidence_badges: [],
        adjacency: [],
      },
    },
    source_spans: [],
    mentions: [
      {
        mention_id: "m-alden",
        node_id: "alden",
        label: "Alden",
        start_offset: 0,
        end_offset: 5,
        anchor_status: "anchored",
      },
      {
        mention_id: "m-bera",
        node_id: "bera",
        label: "Bera",
        start_offset: 14,
        end_offset: 18,
        anchor_status: "anchored",
      },
    ],
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
}

describe("GraphReviewWorkbenchModule", () => {
  beforeEach(() => {
    mockWorkbenchApis();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    document.body.classList.remove("plan-toolbox-open");
    window.sessionStorage.clear();
  });

  it("starts empty on a fresh visit without a session query param", async () => {
    window.history.replaceState({}, "", "/ingest");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument(),
    );

    expect(
      screen.getByText(/Load an ingested session to review extracted objects/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-projection-reader")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Campaign")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
  });

  it("exposes Ingest Recap from the toolbox before a session is loaded", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("button", { name: "Ingest Recap" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Diagnostics" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Author Draft" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Author Node" })).toBeInTheDocument();
  });

  it("auto-loads when a session query param is present", async () => {
    window.history.replaceState({}, "", "/ingest?session=session-23");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.getByText("Session 23 · longmont-c2")).toBeInTheDocument();
    expect(screen.queryByLabelText("Campaign")).not.toBeInTheDocument();
  });

  it("loads prose after choosing a session in the load dialog", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Load recap" }));
    await user.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(window.location.search).toContain("session=session-23");
    expect(window.location.search).toContain("campaign=longmont-c2");
    expect(window.location.search).toContain("run=artifacts%2Frun-a%2Fmanifest.json");
  });

  it("keeps the loaded graph after a remount that simulates browser refresh", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest");
    const first = render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Load recap" }));
    await user.click(screen.getByRole("button", { name: "Load" }));
    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    const restoredUrl = `${window.location.pathname}${window.location.search}`;
    first.unmount();
    window.history.replaceState({}, "", restoredUrl);
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(screen.getByText("Session 23 · longmont-c2")).toBeInTheDocument();
    expect(window.location.search).toContain("run=artifacts%2Frun-a%2Fmanifest.json");
  });

  it("opens toolbox with Ingest Recap and Diagnostics tools", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest?session=session-23");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("button", { name: "Ingest Recap" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Diagnostics" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Author Draft" })).not.toBeInTheDocument();
  });

  it("opens diagnostics content from the toolbox", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest?session=session-23");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Diagnostics" }));

    expect(
      await screen.findByRole("heading", { name: "Gold-vs-live smoke alarms" }),
    ).toBeInTheDocument();
  });

  it("author node drawer enables relationship staging from projected pills", async () => {
    const user = userEvent.setup();
    window.history.replaceState({}, "", "/ingest?session=session-23");
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Author Node" }));

    await screen.findByTestId("graph-review-author-draft-workspace");

    const reader = screen.getByLabelText("Authoring recap");
    const aldenPill = await waitFor(() => {
      const pill = within(reader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(aldenPill);
    fireEvent.click(screen.getByRole("tab", { name: "Relationships" }));
    expect(screen.getByLabelText("Source object")).toHaveValue("existing_node:alden");

    const beraPill = within(reader)
      .getAllByRole("button", { name: /Bera/ })
      .find((button) => button.classList.contains("recap-node-token")) as HTMLButtonElement;
    fireEvent.click(beraPill);
    expect(screen.getByLabelText("Target object")).toHaveValue("existing_node:bera");
    expect(
      screen.getByRole("button", { name: "Stage relationship" }),
    ).toBeEnabled();
  });

  it("opens Author Node from legacy author-draft tool query", async () => {
    window.history.replaceState(
      {},
      "",
      "/ingest?session=session-23&tool=graph-review-author-draft",
    );
    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );
    expect(window.location.search).not.toContain("tool=graph-review-author-draft");
    expect(screen.getByRole("button", { name: "Author Node" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("preserves tool query param when applying a new session from the load dialog", async () => {
    const user = userEvent.setup();
    window.history.replaceState(
      {},
      "",
      "/ingest?session=session-23&tool=graph-review-diagnostics",
    );

    vi.spyOn(liveApi, "getGraphIngestRuns").mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "0.1",
      runs: sessionWithRun.available_runs,
    });
    vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "0.1",
      sessions: [
        sessionWithRun,
        {
          ...sessionWithRun,
          session_id: "session-22",
          session_number: 22,
          available_runs: sessionWithRun.available_runs,
        },
      ],
    });

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    await user.click(screen.getByRole("button", { name: "Load recap" }));
    await user.click(screen.getByRole("tab", { name: /Session 22/i }));
    await user.click(screen.getByRole("button", { name: "Load" }));

    await waitFor(() =>
      expect(window.location.search).toContain("session=session-22"),
    );
    expect(window.location.search).toContain("tool=graph-review-diagnostics");
  });

  it("loads a run-only session without calling gold compare", async () => {
    const user = userEvent.setup();
    const runOnlySession = {
      ...sessionWithRun.available_runs[0],
      campaign_id: "longmont-c1",
      session_id: "session-2",
      run_label: "C1S2 run",
    };
    vi.spyOn(liveApi, "getGraphIngestRuns").mockResolvedValue({
      schema_version: "dmb_graph_ingest_run_registry_v1",
      version: "0.1",
      runs: [runOnlySession],
    });
    vi.spyOn(liveApi, "getGoldReviewSessions").mockResolvedValue({
      schema_version: "dmb_graph_gold_review_sessions_v1",
      version: "0.1",
      sessions: [],
    });
    const compareSpy = vi.spyOn(liveApi, "getGoldReviewCompare");

    window.history.replaceState({}, "", "/ingest?session=session-2&campaign=longmont-c1");
    render(
      <GraphReviewWorkbenchModule
        context={{ ...context, campaignId: "longmont-c1", ingestSession: 2 }}
      />,
    );

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(screen.getByText("Session 2 · longmont-c1")).toBeInTheDocument();
    expect(compareSpy).not.toHaveBeenCalled();
    expect(screen.queryByText(/Loading gold fixture projection/i)).not.toBeInTheDocument();
  });
});

describe("GraphReviewWorkbenchModule committed authority binding", () => {
  function committedProjection(
    label: string,
    revisionId = "rev:committed",
  ): WorldGraphProjection {
    return {
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId,
        headRevisionId: revisionId,
        isHead: true,
        focus: { kind: "session", sessionId: "session-23", campaignId: "longmont-c2" },
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
          label,
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
  }

  const receipt: ExtractPromoteConfirmReceipt = {
    schema: "dmb_extract_promote_confirm_v2",
    outcome: "committed",
    worldId: "eldyrwild",
    proposalId: "prop-1",
    proposalDigest: "digest-a",
    parentRevisionId: "rev:parent",
    committedRevisionId: "rev:committed",
    headAdvanced: true,
    selectedAssertionIds: ["a-1"],
    acceptedAssertionIds: ["a-1"],
    affectedObjectIds: ["object-1"],
    appliedAssertionCount: 1,
    auditStatus: "ok",
    warnings: [],
  };

  function CommittedProbe() {
    const {
      adoptCommittedReceipt,
      committedPhase,
      committedReceipt,
      committedSelectedObjectId,
    } = useGraphReviewLiveState();
    return (
      <div>
        <button
          type="button"
          data-testid="probe-adopt"
          onClick={() => {
            void adoptCommittedReceipt(receipt);
          }}
        >
          Adopt
        </button>
        <span data-testid="probe-phase">{committedPhase}</span>
        <span data-testid="probe-receipt">
          {committedReceipt?.committedRevisionId ?? "none"}
        </span>
        <span data-testid="probe-selected">
          {committedSelectedObjectId ?? "none"}
        </span>
      </div>
    );
  }

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("clears committed authority when catalog binding identity changes", async () => {
    vi.spyOn(liveApi, "getUnionSupergraphProjection").mockResolvedValue({
      campaign_id: "longmont-c2",
      session_id: "session-23",
      graph_id: "graph-a",
      markdown: "# Candidate",
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
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      committedProjection("Hesta Ironroot"),
    );

    function BindingHost({ liveRunId }: { liveRunId: string }) {
      return (
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-23"
          liveRun={null}
          committedBinding={{
            kind: "catalog_run",
            key: catalogRunBindingKey({
              runId: liveRunId,
              campaignId: "longmont-c2",
              sessionId: "session-23",
            }),
            runId: liveRunId,
            campaignId: "longmont-c2",
            sessionId: "session-23",
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <CommittedProbe />
        </GraphReviewLiveStateProvider>
      );
    }

    const { rerender } = render(<BindingHost liveRunId="run-a" />);
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready"),
    );
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("rev:committed");

    rerender(<BindingHost liveRunId="run-b" />);
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("candidate"),
    );
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("none");
  });

  it("preserves committed authority on same-binding refresh remount", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(
      committedProjection("Hesta Ironroot"),
    );

    function BindingHost() {
      return (
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-23"
          liveRun={null}
          committedBinding={{
            kind: "catalog_run",
            key: catalogRunBindingKey({
              runId: "run-a",
              campaignId: "longmont-c2",
              sessionId: "session-23",
            }),
            runId: "run-a",
            campaignId: "longmont-c2",
            sessionId: "session-23",
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <CommittedProbe />
        </GraphReviewLiveStateProvider>
      );
    }

    const first = render(<BindingHost />);
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready"),
    );
    first.unmount();

    // Same binding remount starts candidate; preservation is owned by not clearing
    // while the binding identity is unchanged during an in-tree refresh.
    const second = render(<BindingHost />);
    expect(screen.getByTestId("probe-phase")).toHaveTextContent("candidate");
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready"),
    );
    second.rerender(<BindingHost />);
    expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready");
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("rev:committed");
  });

  it("suppresses stale deferred committed loads via generation counter", async () => {
    let resolveFirst!: (value: WorldGraphProjection) => void;
    let resolveSecond!: (value: WorldGraphProjection) => void;
    const firstDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveFirst = resolve;
    });
    const secondDeferred = new Promise<WorldGraphProjection>((resolve) => {
      resolveSecond = resolve;
    });
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    postSpy.mockReturnValueOnce(firstDeferred).mockReturnValueOnce(secondDeferred);

    function BindingHost() {
      return (
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-23"
          liveRun={null}
          committedBinding={{
            kind: "catalog_run",
            key: catalogRunBindingKey({
              runId: "run-a",
              campaignId: "longmont-c2",
              sessionId: "session-23",
            }),
            runId: "run-a",
            campaignId: "longmont-c2",
            sessionId: "session-23",
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <CommittedProbe />
        </GraphReviewLiveStateProvider>
      );
    }

    render(<BindingHost />);
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("loading"),
    );
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() => expect(postSpy).toHaveBeenCalledTimes(2));

    resolveFirst(committedProjection("Stale Label", "rev:committed"));
    resolveSecond(committedProjection("Hesta Ironroot", "rev:committed"));

    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready"),
    );
    expect(screen.getByTestId("probe-selected")).toHaveTextContent("object-1");
    // Durable second response wins; stale first must not leave conflicting UI.
    expect(screen.queryByText("Stale Label")).toBeNull();
  });

  it("discards deferred run-A projection after switching committedBinding to run B", async () => {
    let resolveA!: (value: WorldGraphProjection) => void;
    const deferredA = new Promise<WorldGraphProjection>((resolve) => {
      resolveA = resolve;
    });
    const postSpy = vi.spyOn(liveApi, "postWorldGraphProjection");
    postSpy.mockReturnValueOnce(deferredA);

    function BindingHost({ runId }: { runId: string }) {
      return (
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-23"
          liveRun={null}
          committedBinding={{
            kind: "catalog_run",
            key: catalogRunBindingKey({
              runId,
              campaignId: "longmont-c2",
              sessionId: "session-23",
            }),
            runId,
            campaignId: "longmont-c2",
            sessionId: "session-23",
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <CommittedProbe />
        </GraphReviewLiveStateProvider>
      );
    }

    const { rerender } = render(<BindingHost runId="run-a" />);
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("loading"),
    );
    expect(postSpy).toHaveBeenCalledTimes(1);

    // Switch binding while run-A projection is still in flight.
    rerender(<BindingHost runId="run-b" />);
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("candidate"),
    );
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("none");
    expect(screen.getByTestId("probe-selected")).toHaveTextContent("none");

    resolveA(committedProjection("Run A Only Label", "rev:run-a"));

    // Allow any late resolution microtasks to flush; authority must stay clear of A.
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("candidate"),
    );
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("none");
    expect(screen.getByTestId("probe-selected")).toHaveTextContent("none");
    expect(screen.queryByText("Run A Only Label")).toBeNull();
    expect(postSpy).toHaveBeenCalledTimes(1);
  });

  it("clears committed authority when exact-run session scope changes for same run+artifact", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockImplementation(async (request) => ({
      ...committedProjection("Hesta Ironroot"),
      snapshot: {
        ...committedProjection("Hesta Ironroot").snapshot,
        campaignId: request.campaignId,
        revisionId: request.revisionPin ?? "rev:committed",
        headRevisionId: request.revisionPin ?? "rev:committed",
        focus: request.focus,
        scopeMode: request.scopeMode,
      },
    }));

    function ExactBindingHost({ sessionId }: { sessionId: string | null }) {
      return (
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId={sessionId ?? ""}
          liveRun={null}
          committedBinding={{
            kind: "exact_run",
            key: exactRunBindingKey({
              runId: "er-1",
              sourceArtifactId: "art-1",
              campaignId: "longmont-c2",
              sessionId,
            }),
            runId: "er-1",
            sourceArtifactId: "art-1",
            campaignId: "longmont-c2",
            sessionId,
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <CommittedProbe />
        </GraphReviewLiveStateProvider>
      );
    }

    const { rerender } = render(<ExactBindingHost sessionId="session-22" />);
    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("ready"),
    );

    rerender(<ExactBindingHost sessionId="session-23" />);
    await waitFor(() =>
      expect(screen.getByTestId("probe-phase")).toHaveTextContent("candidate"),
    );
    expect(screen.getByTestId("probe-receipt")).toHaveTextContent("none");
  });

  it("hides exact-run candidate prose and assertions after committed authority is adopted", async () => {
    vi.spyOn(liveApi, "postWorldGraphProjection").mockImplementation(async (request) => ({
      ...committedProjection("Hesta Ironroot"),
      snapshot: {
        ...committedProjection("Hesta Ironroot").snapshot,
        campaignId: request.campaignId,
        revisionId: request.revisionPin ?? "rev:committed",
        headRevisionId: request.revisionPin ?? "rev:committed",
        focus: request.focus,
        scopeMode: request.scopeMode,
      },
    }));

    const exactReview = {
      schema: "dmb_extract_promote_exact_run_review_v1" as const,
      runId: "er-1",
      sourceDomain: "recap",
      sourceArtifactId: "art-1",
      sourceRevisionId: "sha256:abc",
      campaignId: "longmont-c2",
      sessionId: "session-22",
      sourceProse: "# Candidate exact-run source prose that must disappear",
      assertions: [
        {
          assertionId: "a-candidate",
          kind: "object" as const,
          label: "Candidate Exact Assertion",
          summary: "Must not remain primary after adopt",
          evidence: [],
        },
      ],
      diagnostics: [],
      promotable: true,
      promotableReason: null,
    };

    function ExactSurfaceHost() {
      const { committedPhase, adoptCommittedReceipt } = useGraphReviewLiveState();
      return (
        <div data-testid="graph-review-exact-run-panel">
          <button
            type="button"
            data-testid="probe-adopt"
            onClick={() => {
              void adoptCommittedReceipt(receipt);
            }}
          >
            Adopt
          </button>
          {committedPhase !== "candidate" ? (
            <GraphReviewCommittedProjectionPanel />
          ) : (
            <GraphReviewExactRunProjection review={exactReview} />
          )}
        </div>
      );
    }

    const config = createIngestSurfaceConfig(context);
    render(
      <ProjectionProvider config={config}>
        <GraphReviewLiveStateProvider
          campaignId="longmont-c2"
          sessionId="session-22"
          liveRun={null}
          committedBinding={{
            kind: "exact_run",
            key: exactRunBindingKey({
              runId: "er-1",
              sourceArtifactId: "art-1",
              campaignId: "longmont-c2",
              sessionId: "session-22",
            }),
            runId: "er-1",
            sourceArtifactId: "art-1",
            campaignId: "longmont-c2",
            sessionId: "session-22",
          }}
          compare={null}
          compareStatus="idle"
          compareError={null}
          selection={null}
          onSelectSelection={() => undefined}
        >
          <ExactSurfaceHost />
        </GraphReviewLiveStateProvider>
      </ProjectionProvider>,
    );

    expect(screen.getByTestId("graph-review-exact-run-source-prose")).toHaveTextContent(
      /Candidate exact-run source prose/,
    );
    expect(screen.getByTestId("graph-review-exact-run-assertions")).toBeInTheDocument();
    expect(
      screen.getByTestId("graph-review-exact-run-assertion-a-candidate"),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("probe-adopt"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-committed-projection-panel")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("graph-review-exact-run-source-prose")).toBeNull();
    expect(screen.queryByTestId("graph-review-exact-run-assertions")).toBeNull();
    expect(
      screen.queryByTestId("graph-review-exact-run-assertion-a-candidate"),
    ).toBeNull();
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
  });
});

describe("GraphReviewWorkbenchModule exact-run primary after confirm", () => {
  beforeEach(() => {
    mockWorkbenchApis();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    window.history.replaceState({}, "", "/");
    window.sessionStorage.clear();
  });

  it("removes exact-run source/assertions as primary after terminal confirm adopt", async () => {
    const recapRun = {
      schema_version: "dmb_extraction_run_v1" as const,
      version: "1.0",
      run_id: "extraction-run-recap-1",
      source_artifact_id: "artifact:recap:longmont-c2:session-22:abcdef123456",
      source_domain: "recap",
      status: "reviewable" as const,
      campaign_id: "longmont-c2",
      session_id: "session-22",
      profile_id: "recap_extraction_v0@0.1",
      components: {
        candidate_graph: {
          kind: "candidate_graph",
          uri: "out/graph_memory/runs/extraction/recap1/candidate_graph.json",
          exists: true,
        },
      },
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
      schema_version: "dmb_extraction_run_status_v1",
      run: recapRun,
      source_artifact_id: recapRun.source_artifact_id,
      document_id: "doc-1",
      document_revision: 3,
      source_content_sha256: "sha256:abc",
      graph_review_handoff: {
        href:
          "/ingest?extractionRunId=extraction-run-recap-1"
          + "&sourceArtifactId=artifact:recap:longmont-c2:session-22:abcdef123456"
          + "&documentId=doc-1&revision=3",
        extraction_run_id: recapRun.run_id,
        source_artifact_id: recapRun.source_artifact_id,
        document_id: "doc-1",
        document_revision: 3,
      },
    });
    vi.spyOn(extractPromoteApi, "getExactRunReviewPackage").mockResolvedValue({
      schema: "dmb_extract_promote_exact_run_review_v1",
      runId: recapRun.run_id,
      sourceDomain: "recap",
      sourceArtifactId: recapRun.source_artifact_id,
      sourceRevisionId: "sha256:abc",
      campaignId: "longmont-c2",
      sessionId: "session-22",
      sourceProse: "# Exact-run candidate prose must leave after confirm",
      assertions: [
        {
          assertionId: "a-exact",
          kind: "object",
          label: "Exact Candidate Object",
          summary: "candidate",
          evidence: [],
        },
      ],
      diagnostics: [],
      promotable: true,
      promotableReason: null,
    });
    vi.spyOn(extractPromoteApi, "prepareExtractPromote").mockResolvedValue({
      schema: "dmb_extract_promote_prepare_v1",
      proposalId: "prop-1",
      proposalDigest: "digest-a",
      parentRevisionId: "rev:parent",
      worldId: "eldyrwild",
      acceptedProposalsCount: 1,
      unresolvedMentionsCount: 0,
      rejectedAssertionsCount: 0,
      reviewPackage: { schema: "dmb_extract_promote_proposal_v1" },
      reviewItems: [
        {
          assertionId: "a-exact",
          sliceQualifiedId: "0:source_extraction::a-exact",
          kind: "object",
          label: "Exact Candidate Object",
          action: "create",
          identityOutcome: "created_new",
          summary: "Create new object",
          warnings: [],
          selectable: true,
          selectedByDefault: true,
          dependsOnAssertionIds: [],
          dependsOnSliceQualifiedIds: [],
        },
      ],
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
    vi.spyOn(extractPromoteApi, "confirmExtractPromote").mockResolvedValue({
      schema: "dmb_extract_promote_confirm_v2",
      outcome: "committed",
      worldId: "eldyrwild",
      proposalId: "prop-1",
      proposalDigest: "digest-a",
      parentRevisionId: "rev:parent",
      committedRevisionId: "rev:committed",
      headAdvanced: true,
      selectedAssertionIds: ["a-exact"],
      acceptedAssertionIds: ["a-exact"],
      affectedObjectIds: ["object-1"],
      appliedAssertionCount: 1,
      auditStatus: "ok",
      warnings: [],
    });
    vi.spyOn(liveApi, "postWorldGraphProjection").mockImplementation(async (request) => ({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: request.worldId,
        campaignId: request.campaignId,
        revisionId: request.revisionPin ?? "rev:committed",
        headRevisionId: request.revisionPin ?? "rev:committed",
        isHead: true,
        focus: request.focus,
        admissibility: "gm",
        scopeMode: request.scopeMode,
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
    }));

    render(<GraphReviewWorkbenchModule context={context} />);

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-exact-run-source-prose")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("graph-review-exact-run-assertion-a-exact"),
    ).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("graph-review-exact-run-prepare"));
    await waitFor(() => {
      expect(screen.getByTestId("graph-review-extract-promote-merge-cta")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("graph-review-extract-promote-merge-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-committed-projection-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("graph-review-exact-run-panel")).toHaveAttribute(
      "data-committed-primary",
      "true",
    );
    expect(screen.queryByTestId("graph-review-exact-run-source-prose")).toBeNull();
    expect(screen.queryByTestId("graph-review-exact-run-assertions")).toBeNull();
    expect(
      screen.queryByTestId("graph-review-exact-run-assertion-a-exact"),
    ).toBeNull();
    expect(screen.getAllByText("Hesta Ironroot").length).toBeGreaterThan(0);
  });
});

