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
  fireEvent.click(screen.getByRole("button", { name: "Author Node" }));
  return { onInspectNode };
}

describe("PublishedRecapLocalAuthoring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("preserves exact recap source identity and exposes governed publish only after review", async () => {
    renderHost();

    const host = await screen.findByTestId("published-recap-local-authoring");
    expect(host).toHaveAttribute("data-write-authority", "governed-world");
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
    expect(screen.getByTestId("graph-object-authoring-surface")).toHaveAttribute(
      "data-workflow",
      "published-local-wizard",
    );
    expect(screen.getByTestId("graph-object-authoring-published-wizard")).toHaveAttribute(
      "data-wizard-step",
      "resolve",
    );
    const preview = screen.getByTestId("published-recap-working-projection-preview");
    expect(screen.getByTestId("published-recap-working-projection-preview-toggle")).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    expect(within(preview).queryByRole("article")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-prepare-commit-panel")).not.toBeInTheDocument();
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("keeps the local Author Node expandable without losing its right-anchored host", () => {
    renderHost();

    const authorNode = screen.getByTestId("graph-review-author-node");
    expect(authorNode).toHaveAttribute("data-mode", "published-local");
    expect(authorNode).toHaveAttribute("data-expanded", "false");
    expect(screen.getByRole("button", { name: "Expand Author Node" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Expand Author Node" }));

    expect(authorNode).toHaveAttribute("data-expanded", "true");
    expect(screen.getByRole("button", { name: "Collapse Author Node" })).toBeInTheDocument();
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
    fireEvent.click(screen.getByTestId("graph-object-authoring-wizard-next"));
    expect(screen.getByLabelText("Label")).toHaveValue("gang");
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    fireEvent.click(screen.getByTestId("graph-object-authoring-skip-relationship"));

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "object");
    expect(staged).toHaveTextContent("gang");
    expect(document.querySelector('button[data-graph-node-id^="local-authoring:"]')).toBeTruthy();
    await expectPersistedRecapIdentity(recapRecord, "object");
    expect(screen.getByTestId("graph-object-authoring-wizard-final-state")).toHaveTextContent(
      "Local review complete",
    );
    expect(screen.getByTestId("graph-object-authoring-prepare-commit-panel")).toBeInTheDocument();
    fireEvent.click(within(staged).getByRole("button", { name: "Remove" }));
    expect(document.querySelector('button[data-graph-node-id^="local-authoring:"]')).toBeNull();
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
    fireEvent.click(screen.getByTestId("graph-object-authoring-wizard-next"));

    expect(onInspectNode).toHaveBeenCalledWith("pc_caelynn");
    expect(screen.getByTestId("published-recap-local-authoring")).toHaveAttribute(
      "data-existing-node-id",
      "pc_caelynn",
    );
    expect(screen.getByLabelText("Label")).toHaveValue("Caelynn");
    expect(document.querySelector(".graph-object-authoring-selected-source-phrase")).toHaveTextContent("Caelynn");
    expect(screen.queryByTestId("graph-object-authoring-pending-selection")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-use-selected-text-button")).not.toBeInTheDocument();
  });

  it("keeps new-object authoring in its own tab and remembers selected relationship nodes", async () => {
    renderHost();

    const caelynnPill = await waitFor(() =>
      screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((item) => item.classList.contains("recap-node-token")) as HTMLButtonElement,
    );
    fireEvent.click(caelynnPill);

    const contextTabs = screen.getByRole("navigation", { name: "Authoring contexts" });
    expect(within(contextTabs).getByTestId("graph-object-authoring-context-tab-current")).toHaveTextContent("Caelynn");
    expect(within(contextTabs).getByTestId("graph-object-authoring-context-tab-new")).toBeInTheDocument();

    fireEvent.click(within(contextTabs).getByTestId("graph-object-authoring-context-tab-new"));
    expect(screen.getByTestId("graph-object-authoring-published-wizard")).toHaveAttribute(
      "data-wizard-step",
      "details",
    );
    expect(screen.getByTestId("graph-object-authoring-context-tab-new")).toHaveAttribute(
      "aria-current",
      "page",
    );

    const mirathornPill = await waitFor(() =>
      screen
        .getAllByRole("button", { name: "Mirathorn" })
        .find((item) => item.classList.contains("recap-node-token")) as HTMLButtonElement,
    );
    fireEvent.click(mirathornPill);
    expect(screen.getByTestId("graph-object-authoring-context-tab-current")).toHaveTextContent("Mirathorn");
    expect(within(screen.getByRole("navigation", { name: "Authoring contexts" })).getByRole("button", { name: "Caelynn" })).toBeInTheDocument();
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

    fireEvent.click(await screen.findByTestId("graph-object-authoring-see-all-matches"));
    const bindList = await screen.findByTestId("graph-object-authoring-bind-existing-list");
    const aliasButton = within(bindList).getByTestId("graph-object-authoring-bind-as-alias-button");
    expect(aliasButton).toHaveTextContent('Add “gang” as alias');
    fireEvent.click(aliasButton);

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "link_existing");
    expect(staged).toHaveTextContent("Questionable Company");
    expect(document.querySelector('button[data-graph-node-id="party:questionable_company"]')).toBeTruthy();
    await expectPersistedRecapIdentity(recapRecord, "link_existing");
    expect(prepareGraphObjectAuthoringWrite).not.toHaveBeenCalled();
    expect(commitGraphObjectAuthoringWrite).not.toHaveBeenCalled();
  });

  it("uses existing-node identity semantics for an exact primary-label match", async () => {
    vi.mocked(resolveGraphReviewExistingObjectCandidates).mockResolvedValueOnce({
      schema: "dmb_graph_review_existing_object_resolver_response_v1",
      campaign_id: "longmont-c2",
      session_id: "session-27",
      selected_node_id: "selection:gang",
      selected_label: "gang",
      candidates: [
        {
          candidate_id: "node:gang",
          label: "gang",
          kind: "party",
          confidence: "high",
          score: 1,
          reason: "exact primary-label match",
          source: "union_supergraph",
          suggested_action: "link_existing_later",
          matched_features: ["label"],
          graph_scope: "current_recap_projection",
        },
      ],
      warnings: [],
      diagnostics: [],
      scopes_searched: ["current_recap_projection"],
    });

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

    const duplicateSuggestion = await screen.findByTestId("graph-object-authoring-duplicate-suggestion");
    expect(duplicateSuggestion).toHaveTextContent(/Confident duplicate suggestion/i);
    expect(duplicateSuggestion).toHaveTextContent(/gang is probably/i);
    expect(screen.queryByTestId("graph-object-authoring-bind-existing-list")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("graph-object-authoring-see-all-matches"));
    expect(screen.getByTestId("graph-object-authoring-bind-existing-list")).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-authoring-create-new-from-identity-button")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("graph-object-authoring-duplicate-use-existing-button"));
    const persisted = readPersistedProposals();
    expect(persisted[0]).toMatchObject({
      proposalKind: "link_existing",
      operation: "reference",
      existingObjectRef: { nodeId: "node:gang" },
    });
  });

  it("stages a local relationship from existing recap nodes", async () => {
    renderHost();
    fireEvent.click(screen.getByTestId("graph-object-authoring-wizard-relationship"));

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
    fireEvent.click(screen.getByTestId("graph-object-authoring-skip-relationship"));

    expect(screen.getByTestId("graph-object-authoring-published-wizard")).toHaveAttribute(
      "data-wizard-step",
      "review",
    );
    expect(screen.getByTestId("graph-object-authoring-wizard-final-state")).toHaveTextContent(
      "Local review complete",
    );
    expect(screen.getByTestId("graph-object-authoring-wizard-final-state")).toHaveTextContent(
      "explicit confirmation",
    );
    expect(screen.getByRole("list", { name: "Authoring steps (status only)" })).toHaveAttribute(
      "data-step-indicator",
      "status",
    );

    const staged = screen.getByTestId("graph-object-authoring-staged-proposal");
    expect(staged).toHaveAttribute("data-proposal-kind", "object");
    await expectPersistedRecapIdentity(recapRecord, "object");
  });

  it("does not invent an artifact id when the recap record has none", async () => {
    renderHost({ recapRecord: { ...recapRecord, source_artifact_id: null } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-start-manual-draft-button"));
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "New contact" } });
    fireEvent.click(screen.getByTestId("graph-object-authoring-stage-button"));
    fireEvent.click(screen.getByTestId("graph-object-authoring-skip-relationship"));

    await expectPersistedRecapIdentity({ ...recapRecord, source_artifact_id: null }, "object");
  });
});
