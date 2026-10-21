import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import * as extractPromoteApi from "../../api/extractPromoteApi";
import type {
  ExactRunReviewPackage,
  FirstWorldGraphConfirmReceipt,
  FirstWorldGraphPlan,
} from "../../api/types";
import {firstWorldRecoveryKey,readFirstWorldRecovery} from './firstWorldPublicationRecovery';
import {
  buildFirstWorldDecisions,
  GraphReviewFirstWorldPublishSheet,
} from "./GraphReviewFirstWorldPublishSheet";

vi.mock("../../api/extractPromoteApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/extractPromoteApi")>();
  return {
    ...actual,
    prepareFirstWorldGraph: vi.fn(),
    confirmFirstWorldGraph: vi.fn(),
  };
});

const baseReview: ExactRunReviewPackage = {
  schema: "dmb_extract_promote_exact_run_review_v1",
  runId: "run-glass-orchard",
  sourceDomain: "worldbuilding",
  inspectionStatus:"ready",
  sourceArtifactId: "artifact:worldbuilding:glass:r1:abcdef123456",
  sourceRevisionId: "sha256:"+"a".repeat(64),
  campaignId: null,
  sessionId: null,
  sourceProse: "# Glass Orchard\n\nSample prose.\n",
  assertions: [
    {
      assertionId: "obj_session22_vial",
      kind: "object",
      label: "vial",
      summary: "Puddle sample vial",
      evidence: [
        {
          sourceArtifactId: "artifact:worldbuilding:glass:r1:abcdef123456",
          sourceSpanRefId: "span:p1",
          paragraphText: "Sample prose.",
          anchorQuotes: ["Sample prose."],
        },
      ],
    },
    {
      assertionId: "mystery_puddles",
      kind: "object",
      label: "mystery puddles",
      summary: "Shimmering puddles",
      evidence: [
        {
          sourceArtifactId: "artifact:worldbuilding:glass:r1:abcdef123456",
          sourceSpanRefId: "span:p2",
          paragraphText: "Sample prose.",
          anchorQuotes: ["Sample prose."],
        },
      ],
    },
    {
      assertionId: "e33",
      kind: "relationship",
      label: "vial —contains→ mystery puddles",
      summary: "obj_session22_vial → mystery_puddles",
      evidence: [
        {
          sourceArtifactId: "artifact:worldbuilding:glass:r1:abcdef123456",
          sourceSpanRefId: "span:p3",
          paragraphText: "Sample prose.",
          anchorQuotes: ["Sample prose."],
        },
      ],
    },
  ],
  diagnostics: [],
  promotable: false,
  promotableReason: "Worldbuilding runs are inspect-only for generic promote.",
  worldId: "the-glass-orchard",
  worldState: "uninitialized",
  firstWorldPublishEligible: true,
  firstWorldPublishReason: null,
};

function sealedPlan(
  overrides: Partial<FirstWorldGraphPlan> = {},
): FirstWorldGraphPlan {
  return {
    schema: "dmb_first_world_graph_plan_v1",
    planId: "first-world-graph-plan:abc123",
    planDigest: "sha256:"+"b".repeat(64),
    decisionDigest: "sha256:"+"c".repeat(64),
    worldId: "the-glass-orchard",
    runId: baseReview.runId,
    sourceArtifactId: baseReview.sourceArtifactId,
    sourceRevisionId: baseReview.sourceRevisionId,
    workspaceDocumentId: "doc-glass",
    workspaceDocumentRevision: "3",
    extractionProfile: "worldbuilding_shepherds_flock_v0@0.1",
    acceptedAssertionIds: ["obj_session22_vial", "mystery_puddles", "e33"],
    rejectedAssertionIds: [],
    contributionId: "contribution:glass",
    contributionPayloadSha256: "d".repeat(64),
    reviewedEffect: {decision_snapshot:baseReview.assertions.map(row=>({assertion_id:row.assertionId,
      candidate_kind:row.kind==='object'?'node':'edge',decision:row.kind==='object'?'create_new':'accept',target_node_id:null}))},
    summary: {
      createNewNodeCount: 2,
      acceptedEdgeCount: 1,
      rejectedCandidateCount: 0,
      acceptedAssertionCount: 3,
    },
    confirmable: true,
    diagnostics: [],
    ...overrides,
  };
}

function confirmReceipt(
  overrides: Partial<FirstWorldGraphConfirmReceipt> = {},
): FirstWorldGraphConfirmReceipt {
  return {
    schema: "dmb_first_world_graph_confirm_v1",
    outcome: "initialized",
    worldId: "the-glass-orchard",
    planId: "first-world-graph-plan:abc123",
    planDigest: "sha256:"+"b".repeat(64),
    decisionDigest: "sha256:"+"c".repeat(64),
    sourceArtifactId: baseReview.sourceArtifactId,
    sourceRevisionId: baseReview.sourceRevisionId,
    contributionId: "contribution:glass",
    baselineRevisionId: null,
    committedRevisionId: "rev:glass:1",
    appliedAssertionCount: 3,
    acceptedAssertionIds: ["obj_session22_vial", "mystery_puddles", "e33"],
    rejectedAssertionIds: [],
    auditStatus: "ok",
    warnings: [],
    ...overrides,
  };
}

describe("GraphReviewFirstWorldPublishSheet", () => {
  beforeEach(() => {
    localStorage.clear();
    Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_key:string,action:()=>unknown)=>Promise.resolve(action())}});
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockReset();
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockReset();
  });

  afterEach(() => {
    cleanup();vi.restoreAllMocks();
  });

  it("shows world identity and Create World Graph CTA when eligible", () => {
    render(<GraphReviewFirstWorldPublishSheet review={baseReview} />);

    expect(screen.getByTestId("graph-review-first-world-publish-sheet")).toBeInTheDocument();
    expect(screen.getByText(/The Glass Orchard/i)).toBeInTheDocument();
    expect(screen.getByText("the-glass-orchard")).toBeInTheDocument();
    expect(screen.getByTestId("graph-review-first-world-create-cta")).toHaveTextContent(
      /Create World Graph/i,
    );
  });

  it("disables dependent relationship Keep when an endpoint object is ignored", async () => {
    render(<GraphReviewFirstWorldPublishSheet review={baseReview} />);

    const vial = screen.getByRole("checkbox", { name: "Keep vial" });
    const edge = screen.getByRole("checkbox", {
      name: "Keep vial —contains→ mystery puddles",
    });
    expect(vial).toBeChecked();
    expect(edge).toBeChecked();

    await userEvent.click(vial);

    expect(vial).not.toBeChecked();
    expect(edge).not.toBeChecked();
    expect(edge).toBeDisabled();
    expect(
      screen.getByTestId("graph-review-first-world-relationship-blocked-e33"),
    ).toHaveTextContent(/endpoint object is ignored/i);
    expect(screen.getByTestId("graph-review-first-world-selection-status")).toHaveAttribute(
      "data-selected-count",
      "1",
    );
  });

  it("submit builds correct first-world decision mapping", async () => {
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(sealedPlan());
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockResolvedValue(confirmReceipt());

    render(<GraphReviewFirstWorldPublishSheet review={baseReview} />);

    await userEvent.click(screen.getByTestId("graph-review-first-world-create-cta"));

    await waitFor(() => {
      expect(extractPromoteApi.prepareFirstWorldGraph).toHaveBeenCalledWith({
        runId: baseReview.runId,
        decisions: [
          { assertionId: "obj_session22_vial", decision: "create_new" },
          { assertionId: "mystery_puddles", decision: "create_new" },
          { assertionId: "e33", decision: "accept" },
        ],
      });
    });
  });

  it("confirm success retains the terminal receipt without catalog refresh", async () => {
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(sealedPlan());
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockResolvedValue(confirmReceipt());

    render(
      <GraphReviewFirstWorldPublishSheet
        review={baseReview}
      />,
    );

    await userEvent.click(screen.getByTestId("graph-review-first-world-create-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-first-world-receipt")).toBeInTheDocument();
    });
    expect(screen.getByTestId("graph-review-first-world-receipt")).toHaveAttribute(
      "data-outcome",
      "initialized",
    );
    expect(screen.getByText(/World Graph created/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-review-first-world-create-cta")).not.toBeInTheDocument();
  });

  it("unknown confirm error offers exact-plan retry without re-prepare", async () => {
    const plan = sealedPlan();
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(plan);
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph)
      .mockRejectedValueOnce(new TypeError("network down"))
      .mockResolvedValueOnce(confirmReceipt());

    render(<GraphReviewFirstWorldPublishSheet review={baseReview} />);

    await userEvent.click(screen.getByTestId("graph-review-first-world-create-cta"));

    await waitFor(() => {
      expect(screen.getByTestId("graph-review-first-world-retry-exact-confirm")).toBeInTheDocument();
    });
    expect(extractPromoteApi.prepareFirstWorldGraph).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByTestId("graph-review-first-world-retry-exact-confirm"));

    await waitFor(() => {
      expect(extractPromoteApi.confirmFirstWorldGraph).toHaveBeenCalledTimes(2);
    });
    expect(extractPromoteApi.confirmFirstWorldGraph).toHaveBeenLastCalledWith({ plan });
    expect(extractPromoteApi.prepareFirstWorldGraph).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("graph-review-first-world-receipt")).toBeInTheDocument();
  });

  it('retains the original request before confirm and recovers after reload into an initialized World',async()=>{
    const plan=sealedPlan();vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(plan);
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockImplementationOnce(async()=>{
      expect(readFirstWorldRecovery(baseReview)).toMatchObject({submitted:true,plan});
      throw new TypeError('lost acknowledgement');
    }).mockResolvedValueOnce(confirmReceipt({outcome:'already_initialized'}));
    const view=render(<GraphReviewFirstWorldPublishSheet review={baseReview}/>);
    fireEvent.click(screen.getByTestId('graph-review-first-world-create-cta'));
    await screen.findByTestId('graph-review-first-world-retry-exact-confirm');view.unmount();
    render(<GraphReviewFirstWorldPublishSheet review={{...baseReview,firstWorldPublishEligible:false,worldState:'initialized'}}/>);
    expect(extractPromoteApi.confirmFirstWorldGraph).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('graph-review-first-world-create-cta')).not.toBeInTheDocument();
    expect(screen.getByRole('checkbox',{name:'Keep vial'})).toBeDisabled();
    fireEvent.click(screen.getByTestId('graph-review-first-world-retry-exact-confirm'));
    await screen.findByTestId('graph-review-first-world-receipt');
    expect(extractPromoteApi.prepareFirstWorldGraph).toHaveBeenCalledTimes(1);
    expect(extractPromoteApi.confirmFirstWorldGraph).toHaveBeenNthCalledWith(2,{plan});
  });
  it('keeps typed confirm errors uncertain and prevents a replacement prepare',async()=>{
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(sealedPlan());
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockRejectedValue(new extractPromoteApi.ExtractPromoteApiError('server lost delivery',503,'unknown'));
    render(<GraphReviewFirstWorldPublishSheet review={baseReview}/>);
    fireEvent.click(screen.getByTestId('graph-review-first-world-create-cta'));
    await screen.findByTestId('graph-review-first-world-retry-exact-confirm');
    expect(screen.queryByTestId('graph-review-first-world-retry-prepare')).not.toBeInTheDocument();
    expect(readFirstWorldRecovery(baseReview)?.submitted).toBe(true);
  });
  it.each(['worldId','planId','sourceArtifactId','sourceRevisionId','decisionDigest'] as const)('retains recovery after a foreign receipt %s',async field=>{
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(sealedPlan());
    vi.mocked(extractPromoteApi.confirmFirstWorldGraph).mockResolvedValue({...confirmReceipt(),[field]:'foreign'} as FirstWorldGraphConfirmReceipt);
    render(<GraphReviewFirstWorldPublishSheet review={baseReview}/>);fireEvent.click(screen.getByTestId('graph-review-first-world-create-cta'));
    await screen.findByTestId('graph-review-first-world-retry-exact-confirm');
    expect(screen.queryByTestId('graph-review-first-world-receipt')).not.toBeInTheDocument();
    expect(readFirstWorldRecovery(baseReview)?.submitted).toBe(true);
  });
  it('blocks confirm when request persistence fails',async()=>{
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockResolvedValue(sealedPlan());
    vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('quota');});
    render(<GraphReviewFirstWorldPublishSheet review={baseReview}/>);fireEvent.click(screen.getByTestId('graph-review-first-world-create-cta'));
    expect(await screen.findByRole('alert')).toHaveTextContent('quota');
    expect(extractPromoteApi.confirmFirstWorldGraph).not.toHaveBeenCalled();
  });
  it('does not persist or confirm a prepared reply after source changes',async()=>{
    let resolve!:(v:FirstWorldGraphPlan)=>void;
    vi.mocked(extractPromoteApi.prepareFirstWorldGraph).mockReturnValue(new Promise(r=>{resolve=r;}));
    const view=render(<GraphReviewFirstWorldPublishSheet review={baseReview}/>);fireEvent.click(screen.getByTestId('graph-review-first-world-create-cta'));
    view.rerender(<GraphReviewFirstWorldPublishSheet review={{...baseReview,runId:'different-run'}}/>);
    await act(async()=>resolve(sealedPlan()));
    expect(localStorage.getItem(firstWorldRecoveryKey(baseReview))).toBeNull();
    expect(extractPromoteApi.confirmFirstWorldGraph).not.toHaveBeenCalled();
  });
  it("does not render Create World Graph when firstWorldPublishEligible is false", () => {
    render(
      <GraphReviewFirstWorldPublishSheet
        review={{ ...baseReview, firstWorldPublishEligible: false }}
      />,
    );

    expect(screen.queryByTestId("graph-review-first-world-create-cta")).not.toBeInTheDocument();
  });
});

describe("buildFirstWorldDecisions", () => {
  it("maps Keep/Ignore to create_new/accept/reject", () => {
    const keep = new Map<string, boolean>([
      ["obj_session22_vial", true],
      ["mystery_puddles", false],
      ["e33", false],
    ]);
    expect(buildFirstWorldDecisions(baseReview.assertions, keep)).toEqual([
      { assertionId: "obj_session22_vial", decision: "create_new" },
      { assertionId: "mystery_puddles", decision: "reject" },
      { assertionId: "e33", decision: "reject" },
    ]);
  });
});
