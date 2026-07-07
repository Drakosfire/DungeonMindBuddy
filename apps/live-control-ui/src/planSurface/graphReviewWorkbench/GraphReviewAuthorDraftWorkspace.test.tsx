import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getGoldGraphProjection,
  getUnionSupergraphProjection,
} from "../../api/liveApi";
import type {
  GraphIngestRunSummary,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphReviewAuthorDraftToolPanel } from "./GraphReviewAuthorDraftToolPanel";
import { GraphReviewAuthorDraftWorkspace } from "./GraphReviewAuthorDraftWorkspace";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

function AuthorModeProbe() {
  const { authorDraft } = useGraphReviewLiveState();
  return <span data-testid="author-mode">{authorDraft.authorMode}</span>;
}

function AuthorDraftPanelHarness() {
  const [showPanel, setShowPanel] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setShowPanel(false)}>
        Hide author draft panel
      </button>
      {showPanel ? <GraphReviewAuthorDraftToolPanel /> : null}
      <AuthorModeProbe />
    </>
  );
}

vi.mock("../../api/liveApi", async () => {
  const actual =
    await vi.importActual<typeof import("../../api/liveApi")>(
      "../../api/liveApi",
    );
  return {
    ...actual,
    getGoldGraphProjection: vi.fn(),
    getUnionSupergraphProjection: vi.fn(),
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

const projectionWithMentions: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-23",
  graph_id: "graph-a",
  markdown:
    "The party met [Alden](dmb-node:alden) and [Bera](dmb-node:bera) at the gate.",
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
      summary: "Guards the gate.",
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
      summary: "Scouts ahead.",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
    },
  },
  source_spans: [],
  mentions: [],
};

describe("GraphReviewAuthorDraftWorkspace", () => {
  beforeEach(() => {
    sessionStorage.removeItem("graph-object-authoring-staged:longmont-c2:session-23");
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projectionWithMentions,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMentions);
  });

  it("renders fullscreen split workspace with Tiptap reader and authoring rail", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("graph-review-authoring-rail")).toBeInTheDocument();
    expect(screen.getByLabelText("Authoring recap")).toBeInTheDocument();
    await waitFor(() => {
      expect(document.querySelector(".union-supergraph-tiptap-reader")).toBeInTheDocument();
    });
  });

  it("shows workflow tabs and a resize handle", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );

    expect(screen.getByRole("tab", { name: "New object" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByRole("tab", { name: "Existing object" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Relationships" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Stage & commit" })).toBeInTheDocument();
    expect(screen.getByTestId("graph-review-author-draft-resize-handle")).toBeInTheDocument();
  });

  it("does not switch to the existing-object tab when a pill is clicked", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );

    const reader = screen.getByLabelText("Authoring recap");
    const aldenPill = await waitFor(() => {
      const pill = within(reader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(aldenPill);

    expect(screen.getByRole("tab", { name: "New object" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(
      screen.queryByRole("dialog", { name: "Selected object: Alden" }),
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Existing object" }));
    expect(screen.getByText("Search existing objects")).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Link to recap pill: Alden/i),
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Modify or link an existing object"),
    ).not.toBeInTheDocument();
  });

  it("feeds pill clicks into the relationship form on the relationships tab", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );

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
  });

  it("stages a relationship after source and target pills without dialog churn", async () => {
    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );

    const reader = screen.getByLabelText("Authoring recap");
    const aldenPill = await waitFor(() =>
      within(reader)
        .getAllByRole("button", { name: /Alden/ })
        .find((button) => button.classList.contains("recap-node-token")) as HTMLButtonElement,
    );
    const beraPill = within(reader)
      .getAllByRole("button", { name: /Bera/ })
      .find((button) => button.classList.contains("recap-node-token")) as HTMLButtonElement;

    fireEvent.click(aldenPill);
    fireEvent.click(beraPill);
    fireEvent.click(screen.getByRole("tab", { name: "Relationships" }));

    expect(screen.getByLabelText("Source object")).toHaveValue("existing_node:alden");
    expect(screen.getByLabelText("Target object")).toHaveValue("existing_node:bera");

    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));
    fireEvent.click(screen.getByRole("tab", { name: "Stage & commit" }));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveAttribute("data-proposal-kind", "relationship");
    expect(stagedProposal).toHaveTextContent("Alden");
    expect(stagedProposal).toHaveTextContent("Bera");
  });

  it("opens graph object authoring from Tiptap text selection in the rail", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue({
      ...projectionWithMentions,
      markdown: "The gang arrived at the gate.",
      node_views: {},
    });

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftWorkspace />,
    });

    await waitFor(() => {
      expect(document.querySelector(".ProseMirror")).toBeTruthy();
    });

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
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    fireEvent.click(screen.getByRole("tab", { name: "Stage & commit" }));

    const stagedProposal = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(stagedProposal).toHaveTextContent("Questionable Company");
  });
});

describe("GraphReviewAuthorDraftToolPanel", () => {
  beforeEach(() => {
    vi.mocked(getUnionSupergraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockReset();
    vi.mocked(getGoldGraphProjection).mockResolvedValue({
      ...projectionWithMentions,
      source_kind: "gold_fixture",
      gold_fixture_id: "fixture-a",
      gold_fixture_relpath: "gold/session-23.json",
    });
  });

  it("renders empty state when projection is not ready", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewAuthorDraftToolPanel />,
    });

    expect(
      screen.getByText(
        "Select a live run with a projection before authoring draft corrections.",
      ),
    ).toBeInTheDocument();
  });

  it("shows authoring workspace when projection is ready", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMentions);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorDraftToolPanel />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("graph-review-author-draft-workspace")).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("tab", { name: "New object" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("button", { name: "Return to review" })).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-object-authoring-surface")).toBeInTheDocument();
  });

  it("returns to review mode when the author draft panel unmounts", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMentions);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <AuthorDraftPanelHarness />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("author_draft"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide author draft panel" }));

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("review"),
    );
  });
});
