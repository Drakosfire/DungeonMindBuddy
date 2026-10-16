import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import * as liveApi from "../../api/liveApi";
import type {
  ExactRunReviewPackage,
  ManagedWorldGraphProjectionResponse,
  WorldbuildingWritePlanResponse,
} from "../../api/types";
import { GraphReviewWorldbuildingObservationReview } from "./GraphReviewWorldbuildingObservationReview";

const review: ExactRunReviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1",
  runId: "run-gazetteer-1",
  sourceDomain: "worldbuilding",
  sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
  sourceRevisionId: "source-rev-1",
  sourceProse: "Mirathorn is a city on the eastern coast.",
  worldId: "elderwyld",
  inspectionStatus: "ready",
  diagnostics: [],
  assertions: [
    {
      assertionId: "place:mirathorn",
      kind: "object",
      label: "Mirathorn",
      summary: "A coastal city.",
      evidence: [{
        sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
        sourceSpanRefId: "span:source:p1",
        paragraphText: "Mirathorn is a city on the eastern coast.",
        anchorQuotes: ["Mirathorn is a city"],
        invalidAnchorQuotes: [],
        startLine: 1,
        endLine: 1,
      }],
    },
    {
      assertionId: "obs:mirathorn:coast",
      kind: "source_observation",
      label: "Eastern coastline",
      summary: "The city stands on an exposed coast.",
      subjectCandidateNodeId: "place:mirathorn",
      evidence: [{
        sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
        sourceSpanRefId: "span:source:p1",
        paragraphText: "Mirathorn is a city on the eastern coast.",
        anchorQuotes: ["eastern coast"],
        invalidAnchorQuotes: [],
        startLine: 1,
        endLine: 1,
      }],
    },
  ],
};

function reviewInWorld(worldId: string, runId: string): ExactRunReviewPackage {
  const sourceArtifactId = `artifact:worldbuilding:${worldId}:r2`;
  return {
    ...review,
    runId,
    sourceArtifactId,
    sourceRevisionId: `${runId}:source-revision`,
    worldId,
    assertions: review.assertions.map((assertion) => ({
      ...assertion,
      evidence: assertion.evidence.map((evidence) => ({
        ...evidence,
        sourceArtifactId,
        sourceSpanRefId: evidence.sourceSpanRefId.replace("source", worldId),
      })),
    })),
  };
}

function graphProjection(
  managedWorldId = "elderwyld",
  overrides: Partial<ManagedWorldGraphProjectionResponse["projection"]["snapshot"]> = {},
): ManagedWorldGraphProjectionResponse {
  return {
    schema: "dmb_managed_world_graph_projection_v1",
    managedWorldId,
    nativeWorldId: managedWorldId,
    bindingVersion: 1,
    projection: {
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: managedWorldId,
        campaignId: "",
        revisionId: "rev:head-1",
        headRevisionId: "rev:head-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        ...overrides,
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    },
  };
}

function preparedPlan(): WorldbuildingWritePlanResponse {
  return {
    schema: "dmb_worldbuilding_write_plan_v2",
    version: 2,
    planId: "plan-1",
    planDigest: "plan-digest",
    decisionDigest: "decision-digest",
    worldId: "elderwyld",
    parentRevisionId: "rev:head-1",
    runId: "run-gazetteer-1",
    sourceDomain: "worldbuilding",
    sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
    sourceRevisionId: "source-rev-1",
    extractionProfile: "worldbuilding_gazetteer_v1@1.11",
    candidatePreviewId: "preview-1",
    candidateSchema: "dmb_candidate_graph_v1",
    candidateVersion: "0.2",
    effect: {
      contributionMeta: {
        sourceKind: "source_extraction",
        sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
        sourceRevisionId: "source-rev-1",
        extractionProfile: "worldbuilding_gazetteer_v1@1.11",
        campaignScope: null,
        authoredBy: "live_control:worldbuilding_write_plan",
      },
      acceptedProposals: [{
        assertionId: "proposal:coastline",
        assertionKind: "attribute",
        subjectNodeId: "node:mirathorn",
        predicate: "worldbuilding_observation",
        label: "Eastern coastline",
        value: { summary: "The city stands on an exposed coast." },
        sourceArtifactId: "artifact:worldbuilding:elderwyld:r1",
        sourceRevisionId: "source-rev-1",
      }],
      rejectedAssertions: [],
      unresolvedMentions: [],
      deferredCandidateIds: [],
      nodeIdMap: { "place:mirathorn": "node:mirathorn" },
      decisionSnapshot: [],
      candidateEffectMap: {},
      identityOutcomeSnapshot: {},
    },
    summary: {
      createNewNodeCount: 1,
      bindExistingNodeCount: 0,
      acceptedEdgeCount: 0,
      rejectedCandidateCount: 0,
      deferredCandidateCount: 0,
      acceptedAssertionCount: 2,
    },
    diagnostics: [],
    confirmable: false,
    confirmableReason: "Prepared plan is inert.",
  };
}

describe("GraphReviewWorldbuildingObservationReview", () => {
  afterEach(() => vi.restoreAllMocks());

  it("requires explicit subject decisions and prepares every exact-run disposition without confirming", async () => {
    const user = userEvent.setup();
    const projectionSpy = vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockResolvedValue(graphProjection());
    const prepareSpy = vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan")
      .mockResolvedValue(preparedPlan());
    render(<GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />);

    const prepareButton = screen.getByRole("button", { name: "Prepare review plan" });
    expect(prepareButton).toBeDisabled();
    await screen.findByText("World elderwyld · graph revision rev:head-1");

    const observation = screen.getByText("Eastern coastline").closest("li");
    expect(observation).not.toBeNull();
    expect(within(observation as HTMLElement).getByRole("radio", { name: "Accept" })).toBeDisabled();

    const object = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    expect(object).not.toBeNull();
    await user.click(within(object as HTMLElement).getByRole("radio", { name: "Create new" }));
    await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Accept" }));
    expect(prepareButton).toBeEnabled();
    await user.click(prepareButton);

    await waitFor(() => expect(prepareSpy).toHaveBeenCalledWith({
      runId: "run-gazetteer-1",
      expectedParentRevisionId: "rev:head-1",
      dispositions: [
        { assertionId: "place:mirathorn", decision: "create_new" },
        { assertionId: "obs:mirathorn:coast", decision: "accept" },
      ],
    }));
    expect(projectionSpy).toHaveBeenCalledWith(expect.objectContaining({
      schema: "dmb_managed_world_graph_projection_request_v1",
      managedWorldId: "elderwyld",
      queryText: "Mirathorn",
    }));
    expect(await screen.findByText("Review plan is ready")).toBeInTheDocument();
    expect(screen.getByText(/not published to the World Graph/)).toBeInTheDocument();
    await user.click(screen.getByText(/Prepared graph effects/));
    expect(screen.getByText(/node:mirathorn · The city stands on an exposed coast/)).toBeInTheDocument();
    expect(screen.getByText(/Supported by artifact:worldbuilding:elderwyld:r1 · source-rev-1/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirm|publish/i })).not.toBeInTheDocument();
  });

  it("requires binding targets from the pinned World Graph search", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockImplementation(async (request) => {
      if (request.queryText === "Mirathorn") return graphProjection();
      return {
        ...graphProjection(),
        projection: {
          ...graphProjection().projection,
          nodes: [{
            nodeId: "node:mirathorn",
            label: "Mirathorn",
            kind: "location",
            role: "place",
            aliases: [],
            sourceDomains: ["worldbuilding"],
            campaignScope: null,
            summary: "The city.",
            anchoredToFocusSession: false,
            evidenceBadges: [],
            adjacency: [],
            suggestedExpansions: [],
            evidenceRefIds: [],
            sourceArtifactIds: [],
          }],
        },
      };
    });
    const prepareSpy = vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan")
      .mockResolvedValue(preparedPlan());
    render(<GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />);
    await screen.findByText("World elderwyld · graph revision rev:head-1");

    const object = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    expect(object).not.toBeNull();
    await user.click(within(object as HTMLElement).getByRole("radio", { name: "Use existing" }));
    await user.type(within(object as HTMLElement).getByLabelText("Search existing Mirathorn"), "Mira");
    await user.selectOptions(
      await within(object as HTMLElement).findByRole("combobox"),
      "node:mirathorn",
    );
    const observation = screen.getByText("Eastern coastline").closest("li");
    await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Accept" }));
    await user.click(screen.getByRole("button", { name: "Prepare review plan" }));

    await waitFor(() => expect(prepareSpy).toHaveBeenCalledWith(expect.objectContaining({
      expectedParentRevisionId: "rev:head-1",
      dispositions: [
        { assertionId: "place:mirathorn", decision: "bind_existing", targetNodeId: "node:mirathorn" },
        { assertionId: "obs:mirathorn:coast", decision: "accept" },
      ],
    })));
  });

  it("requires accepted identities for both relationship endpoints", async () => {
    const user = userEvent.setup();
    const reviewWithRelationship: ExactRunReviewPackage = {
      ...review,
      assertions: [
        ...review.assertions,
        {
          assertionId: "place:coast",
          kind: "object",
          label: "Eastern coast",
          summary: "The coast near Mirathorn.",
          evidence: [{
            sourceArtifactId: review.sourceArtifactId,
            sourceSpanRefId: "span:source:p1",
            paragraphText: "Mirathorn is a city on the eastern coast.",
            anchorQuotes: ["eastern coast"],
            invalidAnchorQuotes: [],
          }],
        },
        {
          assertionId: "edge:mirathorn-coast",
          kind: "relationship",
          label: "coastal city",
          summary: "place:mirathorn → place:coast",
          evidence: [{
            sourceArtifactId: review.sourceArtifactId,
            sourceSpanRefId: "span:source:p1",
            paragraphText: "Mirathorn is a city on the eastern coast.",
            anchorQuotes: ["eastern coast"],
            invalidAnchorQuotes: [],
          }],
        },
      ],
    };
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(graphProjection());
    const prepareSpy = vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan")
      .mockResolvedValue(preparedPlan());
    render(<GraphReviewWorldbuildingObservationReview review={reviewWithRelationship} managedWorldId="elderwyld" />);
    await screen.findByText("World elderwyld · graph revision rev:head-1");

    const relationship = screen.getByText("coastal city", { selector: "h4" }).closest("li");
    expect(relationship).not.toBeNull();
    const accept = within(relationship as HTMLElement).getByRole("radio", { name: "Accept" });
    expect(accept).toBeDisabled();

    const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    const coast = screen.getByText("Eastern coast", { selector: "h4" }).closest("li");
    const observation = screen.getByText("Eastern coastline").closest("li");
    await user.click(within(place as HTMLElement).getByRole("radio", { name: "Create new" }));
    await user.click(within(coast as HTMLElement).getByRole("radio", { name: "Create new" }));
    await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Defer" }));
    expect(accept).toBeEnabled();
    await user.click(accept);
    expect(screen.getByRole("button", { name: "Prepare review plan" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Prepare review plan" }));
    await waitFor(() => expect(prepareSpy).toHaveBeenCalledWith(expect.objectContaining({
      dispositions: [
        { assertionId: "place:mirathorn", decision: "create_new" },
        { assertionId: "obs:mirathorn:coast", decision: "defer" },
        { assertionId: "place:coast", decision: "create_new" },
        { assertionId: "edge:mirathorn-coast", decision: "accept" },
      ],
    })));
  });

  it("blocks acceptance when evidence is missing or belongs to another source", async () => {
    const user = userEvent.setup();
    const invalidReview: ExactRunReviewPackage = {
      ...review,
      assertions: review.assertions.map((assertion) => assertion.kind === "source_observation"
        ? { ...assertion, evidence: [{
            ...assertion.evidence[0],
            sourceArtifactId: "artifact:other-world",
          }] }
        : assertion),
    };
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(graphProjection());
    render(<GraphReviewWorldbuildingObservationReview review={invalidReview} managedWorldId="elderwyld" />);
    await screen.findByText("World elderwyld · graph revision rev:head-1");

    const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    const observation = screen.getByText("Eastern coastline").closest("li");
    await user.click(within(place as HTMLElement).getByRole("radio", { name: "Create new" }));
    expect(within(observation as HTMLElement).getByRole("radio", { name: "Accept" })).toBeDisabled();
    expect(screen.getByText(/Acceptance is disabled because this candidate has no valid evidence/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prepare review plan" })).toBeDisabled();
  });

  it("stops an existing-object search when the managed World binding changes", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockImplementation(async (request) =>
      request.queryText === "Mirathorn"
        ? graphProjection()
        : { ...graphProjection(), bindingVersion: 2 },
    );
    render(<GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />);
    await screen.findByText("World elderwyld · graph revision rev:head-1");

    const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    await user.click(within(place as HTMLElement).getByRole("radio", { name: "Use existing" }));
    await user.type(within(place as HTMLElement).getByLabelText("Search existing Mirathorn"), "Mir");

    expect(await screen.findByText(/World binding changed during review/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prepare review plan" })).toBeDisabled();
  });

  it("blocks stale graph heads and exact candidates owned by another World", async () => {
    vi.spyOn(liveApi, "postManagedWorldGraphProjection")
      .mockResolvedValueOnce(graphProjection("elderwyld", { revisionId: "rev:old", headRevisionId: "rev:new", isHead: false }))
      .mockResolvedValue(graphProjection());
    const { rerender } = render(
      <GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />,
    );
    expect(await screen.findByText(/World Graph changed while this review was open/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prepare review plan" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Refresh graph snapshot and restart review" }));
    expect(await screen.findByText("World elderwyld · graph revision rev:head-1")).toBeInTheDocument();

    rerender(<GraphReviewWorldbuildingObservationReview review={{ ...review, worldId: "other-world" }} managedWorldId="elderwyld" />);
    expect(await screen.findByText(/belongs to a different World/)).toBeInTheDocument();
  });
});

describe("stale prepare request isolation", () => {
  it("does not attach a late old-run plan to a new review", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(graphProjection());
    let resolvePlan!: (plan: WorldbuildingWritePlanResponse) => void;
    vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan").mockImplementation(
      () => new Promise((resolve) => { resolvePlan = resolve; }),
    );
    const { rerender } = render(
      <GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />,
    );
    await screen.findByText("World elderwyld · graph revision rev:head-1");
    const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    const observation = screen.getByText("Eastern coastline").closest("li");
    expect(place).not.toBeNull();
    expect(observation).not.toBeNull();
    await user.click(within(place as HTMLElement).getByRole("radio", { name: "Create new" }));
    await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Accept" }));
    await user.click(screen.getByRole("button", { name: "Prepare review plan" }));

    rerender(
      <GraphReviewWorldbuildingObservationReview
        review={{ ...review, runId: "run-new" }}
        managedWorldId="elderwyld"
      />,
    );
    await screen.findByText("World elderwyld · graph revision rev:head-1");
    await act(async () => {
      resolvePlan(preparedPlan());
      await Promise.resolve();
    });
    expect(screen.queryByRole("region", { name: "Prepared review plan" })).not.toBeInTheDocument();
    expect(screen.queryByText("artifact:worldbuilding:elderwyld:r1")).not.toBeInTheDocument();
  });

  it("invalidates a prepare request when selection changes across Worlds and back", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockImplementation(async ({ managedWorldId }) =>
      graphProjection(managedWorldId),
    );
    let resolvePlan!: (plan: WorldbuildingWritePlanResponse) => void;
    vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan").mockImplementation(
      () => new Promise((resolve) => { resolvePlan = resolve; }),
    );
    const { rerender } = render(
      <GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />,
    );
    await screen.findByText("World elderwyld · graph revision rev:head-1");
    const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
    const observation = screen.getByText("Eastern coastline").closest("li");
    expect(place).not.toBeNull();
    expect(observation).not.toBeNull();
    await user.click(within(place as HTMLElement).getByRole("radio", { name: "Create new" }));
    await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Accept" }));
    await user.click(screen.getByRole("button", { name: "Prepare review plan" }));

    const otherWorldId = "other-world";
    const otherWorldReview = reviewInWorld(otherWorldId, "run-other-world");
    rerender(
      <GraphReviewWorldbuildingObservationReview review={otherWorldReview} managedWorldId={otherWorldId} />,
    );
    await screen.findByText("World other-world · graph revision rev:head-1");
    rerender(<GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />);
    await screen.findByText("World elderwyld · graph revision rev:head-1");
    await act(async () => {
      resolvePlan(preparedPlan());
      await Promise.resolve();
    });
    expect(screen.queryByRole("region", { name: "Prepared review plan" })).not.toBeInTheDocument();
  });

  it("keeps a newer review's pending state when an old prepare fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockImplementation(async ({ managedWorldId }) =>
      graphProjection(managedWorldId),
    );
    const pending: Array<{
      resolve: (plan: WorldbuildingWritePlanResponse) => void;
      reject: (error: Error) => void;
    }> = [];
    vi.spyOn(extractPromoteApi, "prepareWorldbuildingWritePlan").mockImplementation(
      () => new Promise((resolve, reject) => { pending.push({ resolve, reject }); }),
    );
    const { rerender } = render(
      <GraphReviewWorldbuildingObservationReview review={review} managedWorldId="elderwyld" />,
    );
    await screen.findByText("World elderwyld · graph revision rev:head-1");
    const chooseAndPrepare = async () => {
      const place = screen.getByText("Mirathorn", { selector: "h4" }).closest("li");
      const observation = screen.getByText("Eastern coastline").closest("li");
      expect(place).not.toBeNull();
      expect(observation).not.toBeNull();
      await user.click(within(place as HTMLElement).getByRole("radio", { name: "Create new" }));
      await user.click(within(observation as HTMLElement).getByRole("radio", { name: "Accept" }));
      await user.click(screen.getByRole("button", { name: "Prepare review plan" }));
    };
    await chooseAndPrepare();
    expect(pending).toHaveLength(1);

    const otherWorldReview = reviewInWorld("other-world", "run-new");
    rerender(
      <GraphReviewWorldbuildingObservationReview review={otherWorldReview} managedWorldId="other-world" />,
    );
    await screen.findByText("World other-world · graph revision rev:head-1");
    await chooseAndPrepare();
    expect(pending).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Preparing review…" })).toBeDisabled();

    await act(async () => {
      pending[0].reject(new Error("Old run failed"));
      await Promise.resolve();
    });
    expect(screen.queryByText("Old run failed")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preparing review…" })).toBeDisabled();

    pending[1].resolve({
      ...preparedPlan(),
      runId: otherWorldReview.runId,
      worldId: otherWorldReview.worldId,
      sourceArtifactId: otherWorldReview.sourceArtifactId,
      sourceRevisionId: otherWorldReview.sourceRevisionId,
    });
    expect(await screen.findByText("Review plan is ready")).toBeInTheDocument();
  });
});
