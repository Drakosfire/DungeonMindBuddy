import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { PlanContextDescriptor } from "../types";
import { clearProjectionRequestCache } from "../reference/projectionRequestCache";
import { GraphReviewWorkbenchModule } from "./GraphReviewWorkbenchModule";

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
  vi.spyOn(liveApi, "getRecapArtifacts").mockResolvedValue({ records: [] });
  vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockResolvedValue({
    campaign_id: "longmont-c2",
    session_id: "session-23",
    graph_id: "warm-recap",
    markdown: "Warm recap",
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
  vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev-1",
      headRevisionId: "rev-1",
      isHead: true,
      focus: { kind: "session", sessionId: "session-23" },
      admissibility: "gm",
    },
    summary: {
      nodeCount: 0,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      sourceTruncated: false,
    },
    nodes: [],
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  });
}

describe("GraphReviewWorkbenchModule", () => {
  beforeEach(() => {
    mockWorkbenchApis();
    window.sessionStorage.clear();
  });

  afterEach(() => {
    clearProjectionRequestCache();
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

    // Blank landing must not pay for chip/reference world projection.
    expect(liveApi.postWorldGraphProjection).not.toHaveBeenCalled();
    // Draft-session recap warm-up should fire in the background.
    await waitFor(() =>
      expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalled(),
    );
    expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalledWith(
      expect.objectContaining({
        campaignId: "longmont-c2",
        scopeMode: "world",
        focus: expect.objectContaining({
          kind: "session",
          sessionId: "session-23",
        }),
      }),
    );
    await waitFor(() =>
      expect(screen.getByTestId("graph-review-activity")).toHaveAttribute("data-phase", "warm"),
    );
    expect(screen.getByTestId("graph-review-activity")).toHaveTextContent(
      /Longmont C2 · Session 23 ready/i,
    );
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
