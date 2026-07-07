import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
  resolveGraphReviewExistingObjectCandidates,
} from "../../api/liveApi";
import type {
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphReviewLiveProjectionPanel } from "./GraphReviewLiveProjectionPanel";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>(
      "../../api/liveApi",
    );
  return {
    ...actual,
    getGoldGraphProjection: vi.fn(),
    getUnionSupergraphProjection: vi.fn(),
    resolveGraphReviewExistingObjectCandidates: vi.fn(),
  };
});

const baseRun: GraphIngestRunSummary = {
  manifest_path: "artifacts/run-a/manifest.json",
  run_dir: "artifacts/run-a",
  campaign_id: "longmont-c2",
  session_id: "session-23",
  status: "succeeded",
  updated_at: null,
  created_at: null,
  preview_union_store_path: "artifacts/run-a/preview-union.json",
  preview_union_store_valid: true,
  node_count: 2,
  edge_count: 1,
  evidence_ref_count: 3,
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

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-23",
  graph_id: "graph-a",
  markdown: "# Projected recap",
  focus: {
    focus_session_id: "session-23",
    focused_evidence_ref_ids: [],
    focused_edge_ids: [],
    focused_node_ids: [],
  },
  node_views: {},
  source_spans: [
    {
      span_id: "p2",
      kind: "paragraph",
      ordinal: 2,
      text_excerpt: "Second",
      line_start: null,
      line_end: null,
    },
  ],
  mentions: [],
};

const projectionWithMention: UnionSupergraphProjectionResponse = {
  ...projection,
  markdown: "The party met [Alden](dmb-node:alden) at the gate.",
  node_views: {
    alden: {
      node_id: "alden",
      label: "Alden",
      kind: "npc",
      role: "gate warden",
      summary: "Alden guards the western gate and knows the patrol routes.",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
    },
  },
  mentions: [
    {
      mention_id: "mention-alden",
      node_id: "alden",
      label: "Alden",
      start_offset: 14,
      end_offset: 19,
      anchor_status: "anchored",
    },
  ],
};

describe("GraphReviewLiveProjectionPanel", () => {
  beforeEach(() => {
    sessionStorage.removeItem("graph-object-authoring-staged:longmont-c2:session-23");
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockReset();
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValue({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c2",
      session_id: "session-23",
      selected_node_id: "",
      selected_label: "",
      candidates: [],
      warnings: [],
    });
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projection,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });
  });

  it("renders an empty state when no live run is selected", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewLiveProjectionPanel />,
    });

    expect(
      screen.getByText(
        "Select a live graph-ingest run to render its source projection.",
      ),
    ).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("renders unavailable metadata and does not call the projection API", () => {
    renderGraphReviewLiveHarness({
      liveRun: {
        ...baseRun,
        preview_union_available: false,
        next_actions: ["Generate preview union"],
      },
      children: <GraphReviewLiveProjectionPanel />,
    });

    expect(
      screen.getByText(
        "Selected live run does not have a preview-union projection available yet.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Generate preview union")).toBeInTheDocument();
    expect(getUnionSupergraphProjection).not.toHaveBeenCalled();
  });

  it("loads the selected run projection by manifest and preview-union paths", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue({
      ...projection,
      authored_overlay: {
        loaded: true,
        assertion_count: 2,
        projected_node_count: 0,
        projected_link_existing_count: 1,
        projected_relationship_count: 1,
        diagnostics: [],
      },
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(getUnionSupergraphProjection).toHaveBeenCalledWith({
      campaignId: "longmont-c2",
      sessionId: "session-23",
      graphRunManifestPath: "artifacts/run-a/manifest.json",
      previewUnionStorePath: "artifacts/run-a/preview-union.json",
    });
    expect(getUnionSupergraphProjection).not.toHaveBeenCalledWith(
      expect.objectContaining({ useLatestGraphIngest: true }),
    );
    expect(screen.getByLabelText("Ingested recap")).toBeInTheDocument();
    expect(screen.queryByText("Live Run · read-only")).not.toBeInTheDocument();
    expect(screen.queryByText("Selected live lane")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Source projection" }),
    ).not.toBeInTheDocument();
  });

  it("renders a single live lane without fetching gold projection when hasGold is false", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(getGoldGraphProjection).not.toHaveBeenCalled();
    expect(screen.getByLabelText("Ingested recap projection")).toBeInTheDocument();
    expect(screen.queryByText(/Loading gold fixture projection/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Ingested recap")).toBeInTheDocument();
  });

  it("opens and closes one projected interaction surface from a graph mention", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(
      projectionWithMention,
    );
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projectionWithMention,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    const liveReader = screen.getByTestId("graph-projection-reader");
    const liveAldenPill = await waitFor(() => {
      const pill = within(liveReader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(liveAldenPill);

    const dialog = screen.getByRole("dialog", { name: "Alden" });
    expect(dialog).toHaveTextContent("Selected object");
    expect(dialog).toHaveTextContent("Live Run · read-only");
    expect(dialog).toHaveTextContent(
      "Alden guards the western gate and knows the patrol routes.",
    );
    expect(dialog).toHaveTextContent("No link or merge is written here.");
    expect(
      screen.queryByRole("button", { name: "Highlight counterpart" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Stage node assertion" }),
    ).not.toBeInTheDocument();

    fireEvent.click(
      screen.getByRole("button", { name: "Close selected object" }),
    );
    expect(
      screen.queryByRole("dialog", { name: "Alden" }),
    ).not.toBeInTheDocument();
  });

  it("preserves gold-vs-live compare decorations on the live lane when authoring mode is off", async () => {
    const goldNodeViews = {
      "gold:alden": {
        node_id: "gold:alden",
        label: "Alden",
        kind: "npc" as const,
        role: "gate warden",
        summary: null,
        aliases: [],
        source_domains: [],
        evidence_badges: [],
        adjacency: [],
      },
    };
    const liveNodeViews = {
      "live:alden": {
        ...goldNodeViews["gold:alden"],
        node_id: "live:alden",
      },
    };
    const goldProjectionPayload: UnionSupergraphProjectionResponse = {
      ...projection,
      markdown: "The party met [Alden](dmb-node:gold:alden) at the gate.",
      node_views: goldNodeViews,
      mentions: [],
    };
    const liveProjectionPayload: UnionSupergraphProjectionResponse = {
      ...projection,
      markdown: "The party met [Alden](dmb-node:live:alden) at the gate.",
      node_views: liveNodeViews,
      mentions: [],
    };

    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(liveProjectionPayload);
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...goldProjectionPayload,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    const liveReader = screen.getByLabelText("Live run prose");
    expect(liveReader).toHaveAttribute("data-lane-role", "live");
    const livePill = await waitFor(() => {
      const pill = within(liveReader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    expect(livePill).toHaveAttribute("data-delta-status");
    expect(
      liveReader.querySelector(".union-supergraph-tiptap-reader"),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-action")).not.toBeInTheDocument();
  });

  it("switches the live lane to the Tiptap authoring reader once authoring mode is enabled", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: true,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(
      document.querySelector(".union-supergraph-tiptap-reader"),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("graph-authoring-mode-toggle"));

    await waitFor(() => {
      expect(
        document.querySelector(".union-supergraph-tiptap-reader"),
      ).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Live run prose")).toBeInTheDocument();
  });

  it("opens the graph object authoring surface from a Tiptap text selection and stages a local draft", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue({
      ...projection,
      markdown: "The gang arrived at the gate.",
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("graph-authoring-mode-toggle"));

    await waitFor(() => {
      expect(document.querySelector(".ProseMirror")).toBeTruthy();
    });
    expect(
      screen.getByText(/Highlight source text in the recap/i),
    ).toBeInTheDocument();

    const proseMirror = document.querySelector(".ProseMirror") as HTMLElement;
    const paragraph = proseMirror.querySelector("p") as HTMLElement;
    const textNode = paragraph.firstChild as Text;
    const startIndex = textNode.textContent!.indexOf("gang");
    const range = document.createRange();
    range.setStart(textNode, startIndex);
    range.setEnd(textNode, startIndex + 4);
    const domSelection = window.getSelection();
    domSelection?.removeAllRanges();
    domSelection?.addRange(range);
    fireEvent.mouseUp(proseMirror);

    await waitFor(() => {
      expect(screen.getByTestId("graph-authoring-action")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("graph-authoring-action"));

    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    expect(screen.getByLabelText("Visibility")).toHaveValue("gm_private");

    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
    expect(stagedProposal).toHaveTextContent("Aliases: gang");
    expect(screen.getByText("Staged locally. No graph write has happened.")).toBeInTheDocument();
  });

  it("lets the user target an existing graph object without first clicking to inspect it", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMention);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("graph-authoring-mode-toggle"));

    // "Alden" is already loaded as part of the projection's node views. It must be
    // targetable from the relationship picker even though no pill has been clicked.
    const sourcePicker = screen.getByLabelText("Source object") as HTMLSelectElement;
    const existingOption = within(sourcePicker).getByRole("option", { name: /Alden/ });
    expect(existingOption).toBeInTheDocument();

    fireEvent.change(sourcePicker, { target: { value: "existing_node:alden" } });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    fireEvent.change(screen.getByPlaceholderText("Type a label for an object not staged yet"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "relationship");
    expect(stagedProposal).toHaveTextContent("Alden");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
  });

  it("stages a link-existing and a relationship proposal alongside object drafts", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMention);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      hasGold: false,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("graph-authoring-mode-toggle"));

    const liveReader = screen.getByTestId("graph-projection-reader");
    const aldenPill = await waitFor(() => {
      const pill = within(liveReader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(aldenPill);
    fireEvent.click(screen.getByRole("button", { name: "Close selected object" }));

    // Relationship authoring is available even without a highlighted text selection,
    // and can target any existing graph object already loaded in the projection
    // ("Alden"), not just the last-inspected one.
    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:alden" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), { target: { value: "manual" } });
    fireEvent.change(screen.getByPlaceholderText("Type a label for an object not staged yet"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    const relationshipProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(relationshipProposal).toHaveAttribute("data-proposal-kind", "relationship");
    expect(relationshipProposal).toHaveTextContent("Alden");
    expect(relationshipProposal).toHaveTextContent("Questionable Company");
    expect(screen.getByText("Staged locally. No graph write has happened.")).toBeInTheDocument();

    // Now select the "gang" text span and stage a link-existing proposal against
    // the same inspected node, alongside the relationship proposal above.
    const proseMirror = liveReader.querySelector(".ProseMirror") as HTMLElement;
    const paragraph = proseMirror.querySelector("p") as HTMLElement;
    const textNode = paragraph.firstChild as Text;
    const startIndex = textNode.textContent!.indexOf("party");
    const range = document.createRange();
    range.setStart(textNode, startIndex);
    range.setEnd(textNode, startIndex + "party".length);
    const domSelection = window.getSelection();
    domSelection?.removeAllRanges();
    domSelection?.addRange(range);
    fireEvent.mouseUp(proseMirror);

    await waitFor(() => {
      expect(screen.getByTestId("graph-authoring-action")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("graph-authoring-action"));
    fireEvent.click(screen.getByTestId("graph-object-authoring-mode-link-existing"));
    fireEvent.change(screen.getByLabelText("Existing object"), {
      target: { value: "existing_node:alden" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-link-existing-button"));

    const stagedProposals = screen.getAllByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposals).toHaveLength(2);
    const linkExistingProposal = stagedProposals.find(
      (node) => node.getAttribute("data-proposal-kind") === "link_existing",
    );
    expect(linkExistingProposal).toBeTruthy();
    expect(linkExistingProposal).toHaveTextContent("party");
    expect(linkExistingProposal).toHaveTextContent("Alden");
  });

  it("does not render diagnostic panels on the main surface", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projection);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-projection-reader")).toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("heading", { name: "Gold-vs-live smoke alarms" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Author Draft text-selection actions"),
    ).not.toBeInTheDocument();
  });

  it("renders a friendly error for failed projection loading", async () => {
    vi.mocked(getUnionSupergraphProjection).mockRejectedValue(
      new Error("Projection fixture missing"),
    );

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewLiveProjectionPanel />,
    });

    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Projection fixture missing",
      ),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Selected run: Run A");
  });
});
