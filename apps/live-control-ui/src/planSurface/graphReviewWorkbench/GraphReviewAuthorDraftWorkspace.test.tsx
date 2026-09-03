import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { useEffect, useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  commitGraphObjectAuthoringWrite,
  getGoldGraphProjection,
  getUnionSupergraphProjection,
  prepareGraphObjectAuthoringWrite,
} from "../../api/liveApi";
import type {
  ExtractionRunRecord,
  UnionSupergraphProjectionResponse,
} from "../../api/types";
import { GraphReviewAuthorNodePanel } from "./GraphReviewAuthorNodePanel";
import { GraphReviewAuthorDraftWorkspace } from "./GraphReviewAuthorDraftWorkspace";
import { renderGraphReviewLiveHarness } from "./graphReviewLiveStateTestHarness";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";
import { toCatalogRun, type GraphReviewCatalogRun } from "./graphReviewWorkbenchUtils";

function canonicalRun(overrides: Partial<ExtractionRunRecord> = {}): ExtractionRunRecord {
  return {
    schema_version: "dmb_extraction_run_v1",
    version: "1.0",
    run_id: "run-a",
    source_artifact_id: "sa_1",
    source_domain: "recap",
    status: "reviewable",
    campaign_id: "longmont-c2",
    session_id: "session-23",
    ...overrides,
  };
}

function catalogRun(
  overrides: Partial<ExtractionRunRecord> = {},
  compatibilityManifestPath: string | null = "artifacts/run-a/manifest.json",
): GraphReviewCatalogRun {
  return toCatalogRun(canonicalRun(overrides), compatibilityManifestPath);
}

function AuthorModeProbe() {
  const { authorDraft } = useGraphReviewLiveState();
  return <span data-testid="author-mode">{authorDraft.authorMode}</span>;
}

function AuthorNodePanelHarness() {
  const [showPanel, setShowPanel] = useState(true);
  return (
    <>
      <button type="button" onClick={() => setShowPanel(false)}>
        Hide author node panel
      </button>
      {showPanel ? (
        <AuthorNodeModeMount>
          <GraphReviewAuthorNodePanel />
        </AuthorNodeModeMount>
      ) : null}
      <AuthorModeProbe />
    </>
  );
}

function AuthorNodeModeMount({ children }: { children: React.ReactNode }) {
  const { authorDraft } = useGraphReviewLiveState();
  useEffect(() => {
    authorDraft.setAuthorMode("author_draft");
    return () => {
      authorDraft.setAuthorMode("review");
    };
  }, [authorDraft.setAuthorMode]);
  return children;
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
    prepareGraphObjectAuthoringWrite: vi.fn(),
    commitGraphObjectAuthoringWrite: vi.fn(),
  };
});

const baseRun = catalogRun();

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
      screen.getByLabelText(/Link recap text to existing object: Alden/i),
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
    const projectionAfterCreate = {
      ...projectionWithMentions,
      markdown: "The gang arrived at the gate.",
      node_views: {
        "authored:assert-test123": {
          node_id: "authored:assert-test123",
          label: "Questionable Company",
          kind: "party",
          role: null,
          aliases: ["gang"],
          summary: null,
          source_domains: ["authored_overlay"],
          adjacency: [],
          evidence_badges: [],
        },
      },
    };
    vi.mocked(getUnionSupergraphProjection)
      .mockResolvedValueOnce({
        ...projectionWithMentions,
        markdown: "The gang arrived at the gate.",
        node_views: {},
      })
      .mockResolvedValue(projectionAfterCreate);
    vi.mocked(prepareGraphObjectAuthoringWrite).mockResolvedValue({
      prepared: true,
      campaign_id: "longmont-c2",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      current_overlay_token: "token-before",
      proposed_assertions_digest: "digest",
      confirm_token: "confirm-token",
      assertion_count: 1,
      event_count: 1,
      assertions_preview: [],
      overlay_summary: {
        existing_assertion_count: 0,
        proposed_assertion_count: 1,
        total_assertion_count: 1,
        object_count: 1,
        link_existing_count: 0,
        relationship_count: 0,
        merge_objects_count: 0,
      },
      diagnostics: [],
      no_mutation_guarantees: [],
    });
    vi.mocked(commitGraphObjectAuthoringWrite).mockImplementation(async (request) => ({
      committed: true,
      campaign_id: "longmont-c2",
      overlay_path: "/tmp/overlay.json",
      event_log_path: "/tmp/events.jsonl",
      assertion_count: 1,
      event_count: 1,
      new_overlay_token: "token-after",
      diagnostics: [],
      no_mutation_guarantees: [],
      created_node_ids: {
        [request.proposals[0]?.localProposalId ?? "missing"]: "authored:assert-test123",
      },
    }));

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
      expect(
        screen.getByTestId("graph-object-authoring-use-selected-text-button"),
      ).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-use-selected-text-button"));

    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    fireEvent.change(screen.getByLabelText("Label"), {
      target: { value: "Questionable Company" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    await waitFor(() => {
      expect(prepareGraphObjectAuthoringWrite).toHaveBeenCalled();
      expect(commitGraphObjectAuthoringWrite).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(screen.getByRole("tab", { name: "Existing object" })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });
    await waitFor(() => {
      expect(
        screen.getByTestId("graph-review-authoring-next-relationships-button"),
      ).toBeInTheDocument();
    });
  });
});

describe("GraphReviewAuthorNodePanel", () => {
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

  it("renders load guidance when projection is not ready", () => {
    renderGraphReviewLiveHarness({
      liveRun: null,
      children: <GraphReviewAuthorNodePanel />,
    });

    expect(
      screen.getByText(
        "Load an ingested session to author graph nodes from the projected recap.",
      ),
    ).toBeInTheDocument();
  });

  it("shows authoring workspace when projection is ready", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMentions);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <GraphReviewAuthorNodePanel />,
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

  it("returns to review mode when the author node panel unmounts", async () => {
    vi.mocked(getUnionSupergraphProjection).mockResolvedValue(projectionWithMentions);

    renderGraphReviewLiveHarness({
      liveRun: baseRun,
      children: <AuthorNodePanelHarness />,
    });

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("author_draft"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Hide author node panel" }));

    await waitFor(() =>
      expect(screen.getByTestId("author-mode")).toHaveTextContent("review"),
    );
  });
});
