import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { PlanContextDescriptor } from "../types";
import { GraphReviewWorkbenchModule } from "./GraphReviewWorkbenchModule";

const context: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  ingestSession: 23,
  headerLabel: "Ingest",
};

const worldSession = {
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  session_id: "session-23",
  session_number: 23,
  contribution_count: 2,
  contribution_ids: ["contribution:test-a", "contribution:test-b"],
  source_artifact_ids: ["artifact:recap:longmont-c2:session-23"],
  head_revision_id: "rev:test",
  recap_available: true,
  browseable: true,
};

function nodeView(nodeId: string, label: string, role: string, summary: string) {
  return {
    nodeId,
    label,
    kind: "npc",
    role,
    summary,
    aliases: [] as string[],
    sourceDomains: [] as string[],
    evidenceBadges: [] as [],
    adjacency: [] as [],
    suggestedExpansions: [] as [],
    anchoredToFocusSession: true,
    campaignScope: "longmont-c2",
    evidenceRefIds: [] as string[],
    sourceArtifactIds: [] as string[],
  };
}

function mockRecapProjection(overrides: {
  campaignId?: string;
  sessionId?: string;
} = {}) {
  const campaignId = overrides.campaignId ?? "longmont-c2";
  const sessionId = overrides.sessionId ?? "session-23";
  return {
    schema: "dmb_world_graph_recap_projection_v1" as const,
    campaignId,
    sessionId,
    graphId: "graph-a",
    snapshot: {
      worldId: "eldyrwild",
      campaignId,
      revisionId: "rev:test",
      headRevisionId: "rev:test",
      isHead: true,
      focus: { kind: "session" as const, sessionId, campaignId },
      admissibility: "gm",
      scopeMode: "campaign" as const,
    },
    markdown: "[Alden](dmb-node:alden) watched [Bera](dmb-node:bera).",
    focus: {
      focusSessionId: sessionId,
      focusedEvidenceRefIds: [],
      focusedEdgeIds: [],
      focusedNodeIds: ["alden", "bera"],
    },
    nodeViews: {
      alden: nodeView("alden", "Alden", "gate warden", "Alden guards the western gate."),
      bera: nodeView("bera", "Bera", "scout", "Bera scouts the old road."),
    },
    sourceSpans: [],
    mentions: [
      {
        mentionId: "m-alden",
        nodeId: "alden",
        label: "Alden",
        startOffset: 0,
        endOffset: 5,
        evidenceRefIds: [],
      },
      {
        mentionId: "m-bera",
        nodeId: "bera",
        label: "Bera",
        startOffset: 14,
        endOffset: 18,
        evidenceRefIds: [],
      },
    ],
    diagnostics: [],
    trustBoundary: { canTrust: [], cannotTrust: [] },
  };
}

function mockWorkbenchApis(
  sessions: Array<typeof worldSession> = [worldSession],
) {
  vi.spyOn(liveApi, "getWorldGraphSessions").mockResolvedValue({
    schema_version: "dmb_world_graph_sessions_v1",
    version: "0.1",
    world_id: "eldyrwild",
    head_revision_id: "rev:test",
    sessions,
  });
  vi.spyOn(liveApi, "postWorldGraphRecapProjection").mockImplementation(
    async (request) =>
      mockRecapProjection({
        campaignId: request.campaignId,
        sessionId: request.focus.sessionId ?? "session-23",
      }),
  );
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
      screen.getByText(/Load a World Graph session to review committed objects/i),
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
    expect(liveApi.postWorldGraphRecapProjection).toHaveBeenCalled();
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
    expect(window.location.search).not.toContain("run=");
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
    expect(window.location.search).not.toContain("run=");
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

    mockWorkbenchApis([
      worldSession,
      {
        ...worldSession,
        session_id: "session-22",
        session_number: 22,
        source_artifact_ids: ["artifact:recap:longmont-c2:session-22"],
      },
    ]);

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

  it("loads a browse session without calling gold compare", async () => {
    const compareSpy = vi.spyOn(liveApi, "getGoldReviewCompare");
    mockWorkbenchApis([
      {
        ...worldSession,
        campaign_id: "longmont-c1",
        session_id: "session-2",
        session_number: 2,
        source_artifact_ids: ["artifact:recap:longmont-c1:session-2"],
      },
    ]);

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
