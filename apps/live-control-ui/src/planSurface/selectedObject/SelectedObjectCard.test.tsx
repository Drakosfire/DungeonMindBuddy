import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ReferenceResolution } from "../reference/referenceResolver";
import { ProjectionProvider } from "../projection/projectionContext";
import type { SurfaceConfig, PlanSessionDescriptor } from "../types";
import { SelectedObjectCard } from "./SelectedObjectCard";

vi.mock("../../api/liveApi", () => ({
  resolveRoll: vi.fn(),
  postCitationSource: vi.fn(),
}));

import { postCitationSource, resolveRoll } from "../../api/liveApi";
import { FIXTURE_DOC_ID } from "../config/planSessionDescriptor";

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    ingestSession: 23,
    liveSession: 23,
  },
  tools: [
    { id: "statblock", label: "Statblock", size: "wide" },
  ],
  canvas: { documentId: FIXTURE_DOC_ID },
  theme: {},
  sessionDescriptor: {
    surfaceId: "plan",
    campaignId: "longmont-c2",
    campaignLabel: "Longmont C2",
    memorySession: 23,
    liveSession: 23,
    sourceStatusLabel: "unknown",
    sourceStatusKind: "unknown",
    planningDocument: {
      documentId: FIXTURE_DOC_ID,
      title: "C2 Session 24 Prep",
      targetRelpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 24 Prep.md",
      storageKey: `dmb.workspaceDocument.${FIXTURE_DOC_ID}`,
      status: "active", contentStatus: "draft", revision: 1, kind: "plan", campaignId: "longmont-c2", targetSession: 23,
    },
  },
};

function renderCard(
  resolution: ReferenceResolution,
  options?: { sessionDescriptor?: PlanSessionDescriptor },
) {
  const sessionDescriptor = options
    ? options.sessionDescriptor
    : surfaceConfig.sessionDescriptor;

  return render(
    <ProjectionProvider config={surfaceConfig}>
      <SelectedObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />
    </ProjectionProvider>,
  );
}

describe("SelectedObjectCard", () => {
  it("renders title, type badge, summary, primary fields, and source path", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: {
        title: "North Reach Gate",
        district: "North Reach",
        table_note: "Crowded checkpoint.",
      },
    });

    expect(screen.getByRole("heading", { name: "North Reach Gate" })).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Crowded checkpoint.")).toBeInTheDocument();
    expect(screen.getByText("District")).toBeInTheDocument();
    expect(screen.getByText("North Reach")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("corpus/locations/north_reach_gate.md")).toBeInTheDocument();
  });

  it("renders Review memory in /ingest link with campaign and session query", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      item: { title: "North Reach Gate" },
    });

    expect(screen.getByRole("link", { name: "Review memory in /ingest" })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-23",
    );
  });

  it("falls back to plain /ingest when session descriptor is absent", () => {
    renderCard(
      {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "location",
          refId: "north-reach-gate",
          label: "North Reach Gate",
        },
        message: "Resolved from live location index.",
        item: { title: "North Reach Gate" },
      },
      { sessionDescriptor: undefined },
    );

    expect(screen.getByRole("link", { name: "Review memory in /ingest" })).toHaveAttribute(
      "href",
      "/ingest",
    );
  });

  it("omits empty fields", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "npc",
        refId: "lysandro-ironveil",
        label: "Lysandro Ironveil",
      },
      message: "Resolved from live npc index.",
      item: {
        title: "Lysandro Ironveil",
        table_note: "Human accelerant at the gate.",
      },
    });

    expect(screen.queryByText("Faction")).not.toBeInTheDocument();
    expect(screen.getByText("Human accelerant at the gate.")).toBeInTheDocument();
  });

  it("renders unresolved card without crashing", () => {
    renderCard({
      status: "unresolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Could not resolve this reference.",
    });

    const card = screen.getByLabelText(/North Reach Gate selected object/i);
    expect(within(card).getByText(/Could not resolve this reference/i)).toBeInTheDocument();
    expect(within(card).getByText("Type")).toBeInTheDocument();
    expect(within(card).getByText("north-reach-gate")).toBeInTheDocument();
  });

  it("does not render edit-lock copy", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "statblock",
        refId: "tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      message: "Resolved from live statblock index.",
      item: { title: "Tripod Null-Calf", challenge_rating: "5" },
    });

    expect(screen.queryByText(/Read-only until unlocked/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/two-phase corpus writer/i)).not.toBeInTheDocument();
  });

  it("opens generic statblock tool and shows honest note", async () => {
    const user = userEvent.setup();
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "statblock",
        refId: "tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      message: "Resolved from live statblock index.",
      item: { title: "Tripod Null-Calf", challenge_rating: "5" },
    });

    expect(screen.getByRole("button", { name: "Open statblock tool" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open statblock tool" }));
    expect(screen.getByText(/Selected object context is not loaded into the workbench yet/i)).toBeInTheDocument();
  });

  it("roll-table card with dice calls resolveRoll and displays result", async () => {
    const user = userEvent.setup();
    vi.mocked(resolveRoll).mockResolvedValue({
      table_id: "gate-dilemma-d12",
      roll: 7,
      title: "Gate Dilemma d12",
      row_text: "Pressure rises.",
      row_locator: "row-7",
      source_path: "corpus/tables/gate_dilemma_d12.md",
      provenance: {},
    });

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "roll-table",
        refId: "gate-dilemma-d12",
        label: "Gate Dilemma d12",
      },
      message: "Resolved from live roll-table index.",
      item: {
        table_id: "gate-dilemma-d12",
        title: "Gate Dilemma d12",
        dice: "d12",
      },
    });

    await user.click(screen.getByRole("button", { name: "Roll d12" }));

    await waitFor(() => {
      expect(resolveRoll).toHaveBeenCalledWith("d12");
    });
    expect(screen.getByText(/Roll result: d12 → 7/i)).toBeInTheDocument();
  });

  it("roll-table card without dice does not show Roll button", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "roll-table",
        refId: "gate-dilemma",
        label: "Gate Dilemma",
      },
      message: "Resolved from live roll-table index.",
      item: {
        table_id: "gate-dilemma",
        title: "Gate Dilemma",
      },
    });

    expect(screen.queryByRole("button", { name: /^Roll /i })).not.toBeInTheDocument();
  });

  it("roll failure shows an error and does not crash", async () => {
    const user = userEvent.setup();
    vi.mocked(resolveRoll).mockRejectedValue(new Error("Roll service unavailable"));

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "roll-table",
        refId: "gate-dilemma-d12",
        label: "Gate Dilemma d12",
      },
      message: "Resolved from live roll-table index.",
      item: {
        table_id: "gate-dilemma-d12",
        title: "Gate Dilemma d12",
        dice: "d12",
      },
    });

    await user.click(screen.getByRole("button", { name: "Roll d12" }));

    await waitFor(() => {
      expect(screen.getByText("Roll service unavailable")).toBeInTheDocument();
    });
  });

  it("renders Show source preview when source path exists", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: {
        title: "North Reach Gate",
        corpus_display_path: "corpus/locations/north_reach_gate.md",
      },
    });

    expect(screen.getByRole("button", { name: "Show source preview" })).toBeInTheDocument();
  });

  it("does not render Show source preview when no source path exists", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "npc",
        refId: "lysandro-ironveil",
        label: "Lysandro Ironveil",
      },
      message: "Resolved from live npc index.",
      item: { title: "Lysandro Ironveil" },
    });

    expect(screen.queryByRole("button", { name: "Show source preview" })).not.toBeInTheDocument();
  });

  it("clicking Show source preview calls postCitationSource with path", async () => {
    const user = userEvent.setup();
    vi.mocked(postCitationSource).mockResolvedValue({
      schema_version: "dmb_citation_source_v1",
      path: "corpus/locations/north_reach_gate.md",
      content_type: "text/markdown",
      content: "# North Reach Gate\nCrowded checkpoint.",
      truncated: false,
      highlight: {
        line_start: null,
        line_end: null,
        text_excerpt: null,
        match_source: "none",
      },
      diagnostics: [],
    });

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: {
        title: "North Reach Gate",
        corpus_display_path: "corpus/locations/north_reach_gate.md",
      },
    });

    await user.click(screen.getByRole("button", { name: "Show source preview" }));

    await waitFor(() => {
      expect(postCitationSource).toHaveBeenCalledWith({
        path: "corpus/locations/north_reach_gate.md",
      });
    });
    expect(screen.getByLabelText("Source preview")).toBeInTheDocument();
    expect(screen.getByText(/# North Reach Gate/i)).toBeInTheDocument();
  });

  it("source preview renders highlighted excerpt when highlight exists", async () => {
    const user = userEvent.setup();
    vi.mocked(postCitationSource).mockResolvedValue({
      schema_version: "dmb_citation_source_v1",
      path: "corpus/locations/north_reach_gate.md",
      content_type: "text/markdown",
      content: "# North Reach Gate\nCrowded checkpoint.\nMore detail.",
      truncated: false,
      highlight: {
        line_start: 2,
        line_end: 2,
        text_excerpt: "Crowded checkpoint.",
        match_source: "line_range",
      },
      diagnostics: [],
    });

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: { title: "North Reach Gate" },
    });

    await user.click(screen.getByRole("button", { name: "Show source preview" }));

    await waitFor(() => {
      expect(screen.getByText("Highlighted excerpt")).toBeInTheDocument();
    });
    expect(screen.getByText("Lines 2–2")).toBeInTheDocument();
    expect(screen.getByText("Crowded checkpoint.")).toBeInTheDocument();
  });

  it("source preview shows truncated warning when response.truncated is true", async () => {
    const user = userEvent.setup();
    vi.mocked(postCitationSource).mockResolvedValue({
      schema_version: "dmb_citation_source_v1",
      path: "corpus/locations/north_reach_gate.md",
      content_type: "text/markdown",
      content: "# North Reach Gate",
      truncated: true,
      highlight: {
        line_start: null,
        line_end: null,
        text_excerpt: null,
        match_source: "none",
      },
      diagnostics: ["reader truncated at 32kb"],
    });

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: { title: "North Reach Gate" },
    });

    await user.click(screen.getByRole("button", { name: "Show source preview" }));

    await waitFor(() => {
      expect(screen.getByText(/Preview truncated by source reader/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/reader truncated at 32kb/i)).toBeInTheDocument();
  });

  it("source preview clips long UI content and shows UI clipped warning", async () => {
    const user = userEvent.setup();
    vi.mocked(postCitationSource).mockResolvedValue({
      schema_version: "dmb_citation_source_v1",
      path: "corpus/locations/north_reach_gate.md",
      content_type: "text/markdown",
      content: "x".repeat(7000),
      truncated: false,
      highlight: {
        line_start: null,
        line_end: null,
        text_excerpt: null,
        match_source: "none",
      },
      diagnostics: [],
    });

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: { title: "North Reach Gate" },
    });

    await user.click(screen.getByRole("button", { name: "Show source preview" }));

    await waitFor(() => {
      expect(screen.getByText(/UI preview clipped/i)).toBeInTheDocument();
    });
  });

  it("source preview failure shows error and does not crash", async () => {
    const user = userEvent.setup();
    vi.mocked(postCitationSource).mockRejectedValue(new Error("File not found"));

    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: { title: "North Reach Gate" },
    });

    await user.click(screen.getByRole("button", { name: "Show source preview" }));

    await waitFor(() => {
      expect(screen.getByText("Unable to preview source: File not found")).toBeInTheDocument();
    });
    expect(screen.getByRole("heading", { name: "North Reach Gate" })).toBeInTheDocument();
  });
});
