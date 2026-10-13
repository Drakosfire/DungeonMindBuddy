import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import type { GraphReferenceResolution } from "./types";
import { ResolvedGraphObjectProjection } from "./ResolvedGraphObjectProjection";

vi.mock("../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../api/liveApi")>("../api/liveApi");
  return {
    ...actual,
    postWorldGraphCompleteObject: vi.fn(),
  };
});

import * as liveApi from "../api/liveApi";

const caelynn = session23WorldGraphRecapFixture.nodeViews.pc_caelynn;

function resolvedCaelynn(): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:pc_caelynn",
    reference: null,
    graphNodeId: "pc_caelynn",
    graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeView(caelynn)),
    graphScope: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      revisionId: session23WorldGraphRecapFixture.snapshot.revisionId,
    },
    projectionState: "ready",
    message: "Resolved.",
  };
}

function completeObject(status: "complete" | "partial") {
  return {
    schema: "dmb_world_graph_object_projection_v1" as const,
    found: true,
    completeness: {
      status,
      reason: status === "partial" ? "relationships_truncated" : null,
      truncatedFields: status === "partial" ? ["relationships"] : [],
    },
    snapshot: session23WorldGraphRecapFixture.snapshot,
    requestedNodeId: "pc_caelynn",
    resolvedNodeId: "pc_caelynn",
    node: caelynn,
    relatedNodes: [],
    semanticFingerprint: "fp-test",
  };
}

describe("ResolvedGraphObjectProjection partial completeness", () => {
  beforeEach(() => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockReset();
  });

  it("passes exact managed World scope through the selected-object request", async () => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("complete"));
    render(<ResolvedGraphObjectProjection
      resolution={{
        ...resolvedCaelynn(),
        graphScope: {
          worldId: "of-conks-j1-fresh-rehearsal",
          campaignId: "",
          scopeMode: "world",
          revisionId: "rev:22ef509825ee1048efc73a1a1aa4a60c",
        },
      }}
      originSurface="plan"
    />);
    await waitFor(() => expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledWith(
      expect.objectContaining({
        worldId: "of-conks-j1-fresh-rehearsal",
        campaignId: "",
        scopeMode: "world",
        nodeId: "pc_caelynn",
        revisionPin: "rev:22ef509825ee1048efc73a1a1aa4a60c",
      }),
    ));
  });

  it("does not treat a partial object as ordinary ready", async () => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("partial"));

    const { container } = render(
      <ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" />,
    );

    expect(await screen.findByTestId("complete-object-partial-warning")).toHaveTextContent(
      /Partial World object: truncated relationships/i,
    );
    expect(container.querySelector("[data-complete-object-status='partial']")).toBeTruthy();
    expect(container.querySelector("[data-complete-object-status='ready']")).toBeNull();
    expect(screen.getByText("Caelynn")).toBeInTheDocument();
  });

  it("keeps complete objects as ready without a partial warning", async () => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("complete"));

    const { container } = render(
      <ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" />,
    );

    await waitFor(() => {
      expect(container.querySelector("[data-complete-object-status='ready']")).toBeTruthy();
    });
    expect(screen.queryByTestId("complete-object-partial-warning")).not.toBeInTheDocument();
  });

  it("shows distinct reviewed observations from the serialized complete-object wire when the summary is empty", async () => {
    const first = {
      assertionId: "assertion:1",
      subjectNodeId: "pc_caelynn",
      observationKind: "session_observation" as const,
      text: "The gate was quiet before the attack.",
      entityKind: "npc",
      reviewId: "review:1",
      contributionId: "contribution:1",
      publicationRevisionId: "rev:published:1",
      sourceArtifactId: "artifact:recap:1",
      sourceRevisionId: "sha256:1",
      evidenceRefIds: ["evidence:1"],
      campaignScope: "longmont-c2",
      visibility: "gm",
      epistemicKind: "fact",
      temporalScope: { session_id: "session-20" },
    };
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue({
      ...completeObject("complete"),
      node: { ...caelynn, summary: null, evidenceBadges: [] },
      reviewedSourceObservations: [
        first,
        {
          ...first,
          assertionId: "assertion:2",
          text: "The gate was crowded after the attack.",
          reviewId: "review:2",
          contributionId: "contribution:2",
          publicationRevisionId: "rev:published:2",
          sourceArtifactId: "artifact:recap:2",
          sourceRevisionId: "sha256:2",
          evidenceRefIds: ["evidence:2"],
          temporalScope: { session_id: "session-22" },
        },
      ],
      coverageGapCodes: [],
      coverageMissingIds: [],
      sourceBindings: [
        { evidenceRefId: "evidence:1", sourceArtifactId: "artifact:recap:1", sourceRevisionId: "sha256:1", sourceDomain: "session_recap", sessionId: "session-20", provenanceStatus: "no_source_span" },
        { evidenceRefId: "evidence:2", sourceArtifactId: "artifact:recap:2", sourceRevisionId: "sha256:2", sourceDomain: "session_recap", sessionId: "session-22", provenanceStatus: "no_source_span" },
      ],
    });

    render(<ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" onReadSourceEvidence={vi.fn()} />);
    const notes = await screen.findByRole("region", { name: "Reviewed source observations" });
    expect(within(notes).getByText("The gate was quiet before the attack.")).toBeVisible();
    expect(within(notes).getByText("The gate was crowded after the attack.")).toBeVisible();
    expect(within(notes).getByText("Session 20")).toBeVisible();
    expect(within(notes).getByText("Session 22")).toBeVisible();
    expect(within(notes).getAllByText("Session recap")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Read source" })).not.toBeInTheDocument();
    const sourceDetails = within(notes).getAllByText("Source and review details");
    expect(sourceDetails).toHaveLength(2);
    await userEvent.setup().click(sourceDetails[0]);
    expect(within(notes).getByText("review:1")).toBeVisible();
    expect(within(notes).getByText("assertion:1")).toBeVisible();
  });

  it("keeps long reviewed text available and reports source coverage gaps without exposing raw IDs by default", async () => {
    const longText = `The first account is distinct. ${"This detail belongs to this reviewed source. ".repeat(9)}`;
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue({
      ...completeObject("partial"),
      node: { ...caelynn, summary: null },
      reviewedSourceObservations: [{
        assertionId: "assertion:long",
        subjectNodeId: "pc_caelynn",
        observationKind: "session_observation",
        text: longText,
        entityKind: "npc",
        reviewId: "review:long",
        contributionId: "contribution:long",
        publicationRevisionId: "rev:long",
        sourceArtifactId: "artifact:long",
        sourceRevisionId: "sha256:long",
        evidenceRefIds: ["evidence:long"],
        campaignScope: null,
        visibility: "gm",
        epistemicKind: "fact",
        temporalScope: null,
      }],
      coverageGapCodes: ["missing_source_authority"],
      coverageMissingIds: ["source-revision:missing"],
    });

    render(<ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" />);
    const notes = await screen.findByRole("region", { name: "Reviewed source observations" });
    expect(within(notes).getByText(/Some source context could not be included/)).toBeVisible();
    expect(within(notes).getByText(/Missing records: source-revision:missing/)).not.toBeVisible();
    const expand = within(notes).getByText(/Read full observation/);
    await userEvent.setup().click(expand);
    expect(within(notes).getByText(longText.trim())).toBeVisible();
    expect(screen.getByTestId("complete-object-partial-warning")).toBeVisible();
  });

  it("offers a Plan source passage only from an exact digest-pinned evidence binding", async () => {
    const onReadSourceEvidence = vi.fn();
    const evidenceNode = {
      ...caelynn,
      evidenceBadges: [{
        evidenceRefId: "ev:s25",
        sourceArtifactId: "artifact:s25",
        sourceSpanRefId: "span:s25",
        sourceDomain: "session_recap",
        evidenceRole: "supporting",
        isFocusSessionEvidence: false,
        canOpenSource: true,
        canHighlightSpan: false,
        label: "S25 recap passage",
      }],
    };
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue({
      ...completeObject("complete"),
      node: evidenceNode,
      sourceBindings: [{
        evidenceRefId: "ev:s25",
        sourceArtifactId: "artifact:s25",
        sourceRevisionId: "artifact-rev:s25",
        contentSha256: "a".repeat(64),
        sourceSpanRefId: "span:s25",
        sourceDomain: "session_recap",
        provenanceStatus: "excerpt_ready",
        excerpt: "Lysandra led the warehouse watch through the storm.",
      }],
    });

    render(<ResolvedGraphObjectProjection
      resolution={resolvedCaelynn()}
      originSurface="plan"
      onReadSourceEvidence={onReadSourceEvidence}
    />);
    const readSource = await screen.findByRole("button", { name: "Read source" });
    await userEvent.setup().click(readSource);
    expect(onReadSourceEvidence).toHaveBeenCalledWith(expect.objectContaining({
      id: "ev:s25",
      sourceArtifactId: "artifact:s25",
      sourceSpanRefId: "span:s25",
      excerpt: "Lysandra led the warehouse watch through the storm.",
    }));
    expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledTimes(1);
  });

  it("does not offer a source action for a missing, mismatched, or unverified excerpt", async () => {
    const evidenceNode = {
      ...caelynn,
      evidenceBadges: [{
        evidenceRefId: "ev:s25",
        sourceArtifactId: "artifact:s25",
        sourceSpanRefId: "span:s25",
        sourceDomain: "session_recap",
        evidenceRole: "supporting",
        isFocusSessionEvidence: false,
        canOpenSource: true,
        canHighlightSpan: false,
        label: "S25 recap passage",
      }],
    };
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue({
      ...completeObject("complete"),
      node: evidenceNode,
      sourceBindings: [{
        evidenceRefId: "ev:s25",
        sourceArtifactId: "artifact-other",
        contentSha256: "bad-digest",
        sourceSpanRefId: "span:s25",
        sourceDomain: "session_recap",
        provenanceStatus: "source_not_durable",
        excerpt: "This text must not be exposed.",
      }],
    });
    render(<ResolvedGraphObjectProjection
      resolution={resolvedCaelynn()}
      originSurface="plan"
      onReadSourceEvidence={vi.fn()}
    />);
    await screen.findByText("Caelynn");
    expect(screen.queryByRole("button", { name: "Read source" })).not.toBeInTheDocument();
    expect(screen.queryByText("This text must not be exposed.")).not.toBeInTheDocument();
  });

  it("keeps exact World identity behind Advanced without another request", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("complete"));
    render(<ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="ingest" />);

    const advanced = await screen.findByText("Advanced");
    const panel = advanced.closest("details");
    expect(panel).not.toHaveAttribute("open");
    expect(screen.queryByText("fp-test")).not.toBeVisible();
    await user.click(advanced);
    expect(within(panel!).getByText("fp-test")).toBeVisible();
    expect(within(panel!).getByText("pc_caelynn")).toBeVisible();
    expect(within(panel!).getByText("ingest")).toBeVisible();
    expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledTimes(1);
    await user.click(advanced);
    expect(panel).not.toHaveAttribute("open");
    expect(liveApi.postWorldGraphCompleteObject).toHaveBeenCalledTimes(1);
  });
});
