import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../api/liveApi", () => ({
  prepareGraphObjectAuthoringWrite: vi.fn(),
  commitGraphObjectAuthoringWrite: vi.fn(),
  resolveGraphReviewExistingObjectCandidates: vi.fn().mockResolvedValue({
    schema: "dmb_graph_review_existing_object_resolver_response_v1",
    campaign_id: "longmont-c2",
    session_id: "session-27",
    selected_node_id: "selection",
    selected_label: "selection",
    candidates: [],
    warnings: [],
    diagnostics: [],
    scopes_searched: [],
  }),
}));

import {
  commitGraphObjectAuthoringWrite,
  prepareGraphObjectAuthoringWrite,
  resolveGraphReviewExistingObjectCandidates,
} from "../../api/liveApi";
import type { GraphProjectionNodeView, RecapArtifactRecord } from "../../api/types";
import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import type { GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";
import { PublishedRecapLocalAuthoring } from "./PublishedRecapLocalAuthoring";

const caelynn: GraphProjectionNodeView = {
  node_id: "pc_caelynn",
  label: "Caelynn",
  kind: "pc",
  role: "pc",
  aliases: ["Caelynn"],
  source_domains: ["recap"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
};

const mirathorn: GraphProjectionNodeView = {
  node_id: "loc_mirathorn",
  label: "Mirathorn",
  kind: "location",
  role: "location",
  aliases: ["Mirathorn"],
  source_domains: ["worldbuilding"],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: false,
};

const recapRecord: RecapArtifactRecord = {
  schema_version: "dmb_recap_artifact_record_v1",
  artifact_id: "longmont-c2/session-27",
  campaign_id: "longmont-c2",
  session_id: "session-27",
  source_artifact_id: "artifact:recap:longmont-c2:session-27",
  source_recap_path: "corpus/eldyrwild-markdown/Session 27 - Recap.md",
  breadcrumb_seed_path: null,
  session_memory_records_path: null,
  run_bundle_uri: "",
  run_manifest_uri: "",
  source_span_index_uri: "",
  provenance_index_uri: null,
  graph_run_refs: [],
  default_graph_run_uri: null,
  default_projection_mode: "recap_graph",
  source_sha256: "sha256:session-27",
  registered_at: "2026-06-28T00:00:00Z",
  updated_at: "2026-06-28T00:00:00Z",
  registry_source: "scan",
};

const STAGED_STORAGE_KEY = "graph-object-authoring-staged:longmont-c2:session-27";

function readPersistedProposals(): GraphObjectAuthoringProposal[] {
  const raw = sessionStorage.getItem(STAGED_STORAGE_KEY);
  expect(raw).toBeTruthy();
  const parsed = JSON.parse(raw as string) as unknown;
  expect(Array.isArray(parsed)).toBe(true);
  return parsed as GraphObjectAuthoringProposal[];
}

function selectionFromPersistedProposal(
  proposal: GraphObjectAuthoringProposal,
): GraphAuthoringSelection | null {
  return proposal.proposalKind === "merge_objects" ? null : (proposal.selection ?? null);
}

async function expectPersistedRecapIdentity(
  record: RecapArtifactRecord,
  proposalKind?: GraphObjectAuthoringProposal["proposalKind"],
) {
  await waitFor(() => {
    const proposals = readPersistedProposals();
    const proposal = proposalKind
      ? proposals.find((item) => item.proposalKind === proposalKind)
      : proposals[proposals.length - 1];
    expect(proposal).toBeDefined();
    const selection = selectionFromPersistedProposal(proposal!);
    expect(selection).toMatchObject({
      campaignId: record.campaign_id,
      sessionId: record.session_id,
      sourceArtifactPath: record.source_recap_path,
      sourceArtifactSha256: record.source_sha256,
      sourceArtifactId: record.source_artifact_id,
      sourceSpanRefId: null,
    });
  });
}

function renderHost(overrides: Partial<Parameters<typeof PublishedRecapLocalAuthoring>[0]> = {}) {
  const onInspectNode = vi.fn();
  render(
    <PublishedRecapLocalAuthoring
      campaignId="longmont-c2"
      sessionId="session-27"
      graphId="graph-c2s27"
      markdown="The gang met [Caelynn](dmb-node:pc_caelynn) near [Mirathorn](dmb-node:loc_mirathorn)."
      nodeViews={{ pc_caelynn: caelynn, loc_mirathorn: mirathorn }}
      recapRecord={recapRecord}
      onInspectNode={onInspectNode}
      {...overrides}
    />,
  );
  return { onInspectNode };
}

describe("PublishedRecapLocalAuthoring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("keeps published browse non-write and preserves exact recap source identity", async () => {
    renderHost();

    const host = await screen.findByTestId("published-recap-local-authoring");
    expect(host).toHaveAttribute("data-write-authority", "none");
    expect(host).toHaveAttribute("data-source-artifact-id", "artifact:recap:longmont-c2:session-27");
    expect(host).toHaveAttribute(
      "data-source-artifact-path",
      "corpus/eldyrwild-markdown/Session 27 - Recap.md",
    );
    expect(host).toHaveAttribute("data-source-artifact-sha256", "sha256:session-27");
    expect(host).toHaveAttribute("data-source-span-ref-id", "null");
    expect(screen.getByTestId("graph-object-authoring-surface")).toHaveAttribute(
      "data-local-stage-only",
      "true",
    );
    expect(screen.queryByTestId("graph-object-authoring-prepare-commit-panel")).not.toBeInTheDocument();
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("stages a local object from highlighted recap text without write APIs", async () => {
    renderHost();

    await waitFor(() => {
      expect(document.querySelector(".ProseMirror")).toBeTruthy();
    });
    const proseMirror = document.querySelector(".ProseMirror") as HTMLElement;
    const paragraph = proseMirror.querySelector("p");
    const range = document.createRange();
    const textNode = paragraph!.firstChild as Text;
    const startIndex = textNode.textContent!.indexOf("gang");
    range.setStart(textNode, startIndex);
    range.setEnd(textNode, startIndex + 4);
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    fireEvent.mouseUp(proseMirror);

    fireEvent.click(await screen.findByTestId("graph-authoring-action"));
    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "object");
    expect(staged).toHaveTextContent("gang");
    await expectPersistedRecapIdentity(recapRecord, "object");
    expect(screen.getByText(/Local drafts only/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-prepare-commit-panel")).not.toBeInTheDocument();
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("seeds local authoring from an existing pill while still inspecting the node", async () => {
    const { onInspectNode } = renderHost();

    const pill = await waitFor(() => {
      const button = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((item) => item.classList.contains("recap-node-token"));
      expect(button).toBeTruthy();
      return button as HTMLButtonElement;
    });
    fireEvent.click(pill);

    expect(onInspectNode).toHaveBeenCalledWith("pc_caelynn");
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-existing-node-id",
      "pc_caelynn",
    );
    expect(screen.getByLabelText("Label")).toHaveValue("Caelynn");
    expect(document.querySelector(".graph-object-authoring-selected-source-phrase")).toHaveTextContent("Caelynn");
  });

  it("stages link_existing locally from a resolver candidate", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValueOnce({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c2",
      session_id: "session-27",
      selected_node_id: "selection:gang",
      selected_label: "gang",
      candidates: [
        {
          candidate_id: "party:questionable_company",
          label: "Questionable Company",
          kind: "party",
          confidence: "high",
          score: 0.9,
          reason: "alias match",
          source: "union_supergraph",
          suggested_action: "link_existing_later",
          matched_features: ["alias"],
          graph_scope: "party_pc",
        },
      ],
      warnings: [],
      diagnostics: [],
      scopes_searched: ["party_pc"],
    });

    renderHost();
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "gang" } });

    await waitFor(() => {
      expect(document.querySelector(".ProseMirror")).toBeTruthy();
    });
    const proseMirror = document.querySelector(".ProseMirror") as HTMLElement;
    const paragraph = proseMirror.querySelector("p");
    const range = document.createRange();
    const textNode = paragraph!.firstChild as Text;
    const startIndex = textNode.textContent!.indexOf("gang");
    range.setStart(textNode, startIndex);
    range.setEnd(textNode, startIndex + 4);
    window.getSelection()?.removeAllRanges();
    window.getSelection()?.addRange(range);
    fireEvent.mouseUp(proseMirror);
    fireEvent.click(await screen.findByTestId("graph-authoring-action"));

    const bindList = await screen.findByTestId("graph-object-authoring-bind-existing-list");
    fireEvent.click(within(bindList).getByTestId("graph-object-authoring-bind-as-alias-button"));

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "link_existing");
    expect(staged).toHaveTextContent("Questionable Company");
    await expectPersistedRecapIdentity(recapRecord, "link_existing");
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("stages a local relationship from existing recap nodes", async () => {
    renderHost();

    fireEvent.change(screen.getByLabelText("Source object"), {
      target: { value: "existing_node:pc_caelynn" },
    });
    fireEvent.change(screen.getByLabelText("Relationship type"), {
      target: { value: "located_in" },
    });
    fireEvent.change(screen.getByLabelText("Target object"), {
      target: { value: "existing_node:loc_mirathorn" },
    });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-relationship-button"));

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "relationship");
    expect(staged).toHaveTextContent("Caelynn");
    expect(staged).toHaveTextContent("Mirathorn");
    await expectPersistedRecapIdentity(recapRecord, "relationship");
    fireEvent.click(within(staged).getByRole("button", { name: "Remove" }));
    expect(screen.queryByTestId("graph-object-authoring-staged-proposal")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(sessionStorage.getItem(STAGED_STORAGE_KEY)).toBeNull();
    });
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("stages a manual object draft with recap path, hash, and artifact id and no span", async () => {
    renderHost();
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "New contact" } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "object");
    await expectPersistedRecapIdentity(recapRecord, "object");
  });

  it("does not invent an artifact id when the recap record has none", async () => {
    renderHost({ recapRecord: { ...recapRecord, source_artifact_id: null } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "New contact" } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));

    await expectPersistedRecapIdentity({ ...recapRecord, source_artifact_id: null }, "object");
  });
});
