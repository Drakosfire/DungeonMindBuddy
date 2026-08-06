import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type {
  ThreatDraftV1,
  ThreatIdentityCandidateSetV1,
  ThreatIdentityCandidateV1,
  ThreatPublicationCommitResponseV1,
  ThreatPublicationCommitV1,
  ThreatPublicationIdentityResolutionV1,
  ThreatPublicationIdentityResponseV1,
  ThreatPublicationOperationResponseV1,
  ThreatPublicationOperationV1,
  ThreatPublicationProposalResponseV1,
  ThreatPublicationProposalV1,
  ThreatPublicationSourceSnapshotV1,
} from "../../api/types";
import { ThreatPublicationPanel, type ThreatPublicationApi, type ThreatPublicationPanelProps } from "./ThreatPublicationPanel";
import {
  SESSION_SCHEMA,
  readThreatPublicationSession,
  writeThreatPublicationSession,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";

const DRAFT_ID = "11111111-1111-4111-8111-111111111111";
const OPERATION_ID = "22222222-2222-4222-8222-222222222222";
const OPERATION_ID_NEW = "33333333-3333-4333-8333-333333333333";
const RESOLUTION_ID = "44444444-4444-4444-8444-444444444444";
const PROPOSAL_ID = "55555555-5555-4555-8555-555555555555";
const COMMIT_ID = "66666666-6666-4666-8666-666666666666";
const PARENT_REVISION = "77777777-7777-4777-8777-777777777777";
const PARENT_REVISION_FRESH = "88888888-8888-4888-8888-888888888888";

function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key)! : null;
    },
    key(index: number) {
      return [...store.keys()][index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  };
}

function sequentialIdGenerator(ids: readonly string[]): () => string {
  let index = 0;
  return () => {
    const id = ids[index] ?? `generated-${index}`;
    index += 1;
    return id;
  };
}

function buildApiMocks(): ThreatPublicationApi {
  return {
    beginThreatPublicationOperation: vi.fn(),
    getThreatPublicationOperation: vi.fn(),
    refreshThreatPublicationOperation: vi.fn(),
    cancelThreatPublicationOperation: vi.fn(),
    retryThreatPublicationOperation: vi.fn(),
    prepareThreatIdentityCandidates: vi.fn(),
    createThreatIdentityResolution: vi.fn(),
    getThreatIdentityResolution: vi.fn(),
    prepareThreatPublicationProposal: vi.fn(),
    getThreatPublicationProposal: vi.fn(),
    confirmThreatPublicationCommit: vi.fn(),
    getThreatPublicationCommit: vi.fn(),
  };
}

function buildDraft(overrides: Partial<ThreatDraftV1> = {}): ThreatDraftV1 {
  return {
    schema: "dmb_threat_draft_v1",
    draft_id: DRAFT_ID,
    version: 3,
    world_id: "world-1",
    campaign_id: "campaign-1",
    focus: null,
    name: "Tripod Null-Calf",
    slug_hint: null,
    description: "A three-legged aberration.",
    threat_kind: "aberration",
    intended_roles: ["skirmisher"],
    tags: [],
    generation_intent: {
      ruleset: { system: "dnd5e", edition: "2014", house_ruleset_id: null },
      target_cr: "3",
      complexity: null,
      must_include: [],
      must_avoid: [],
    },
    encounter_context: { party_level: 5, party_size: 4, terrain_notes: [] },
    graph_context_snapshot: { graph_revision_id: null, selected_node_ids: [], admitted_source_anchor_ids: [] },
    candidate_refs: [],
    accepted_mechanics_ref: {
      provider: "dungeonmind",
      statblock_id: "sb-1",
      revision_id: "sb-rev-1",
      contract: "dungeonmind.dungeonbuddy-statblocks",
      contract_version: "1.0.0",
      definition_digest: "sha256:abc",
      accepted_from_candidate_id: null,
      accepted_from_draft_version: 2,
      accepted_at: "2026-08-01T00:00:00.000Z",
    },
    workflow_state: "mechanics_saved",
    created_by: "gm",
    created_at: "2026-08-01T00:00:00.000Z",
    updated_at: "2026-08-01T00:00:00.000Z",
    ...overrides,
  };
}

function sourceSnapshot(draft: ThreatDraftV1): ThreatPublicationSourceSnapshotV1 {
  return {
    schema: "dmb_threat_publication_source_v1",
    draft_id: draft.draft_id,
    draft_version: draft.version,
    world_id: draft.world_id,
    campaign_id: draft.campaign_id,
    focus: draft.focus ?? null,
    name: draft.name,
    slug_hint: draft.slug_hint ?? null,
    description: draft.description,
    threat_kind: draft.threat_kind,
    intended_roles: draft.intended_roles,
    tags: draft.tags,
    generation_intent: draft.generation_intent,
    encounter_context: draft.encounter_context,
    graph_context_snapshot: draft.graph_context_snapshot,
    accepted_mechanics_ref: draft.accepted_mechanics_ref!,
  };
}

function buildOperation(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationOperationV1> = {},
): ThreatPublicationOperationV1 {
  return {
    schema: "dmb_threat_publication_operation_v1",
    operation_id: OPERATION_ID,
    request_digest: "sha256:req",
    source_snapshot: sourceSnapshot(draft),
    source_digest: "sha256:source",
    expected_parent_revision_id: PARENT_REVISION,
    state: "ready",
    stale_reasons: [],
    supersedes_operation_id: null,
    superseded_by_operation_id: null,
    cancelled_by: null,
    cancellation_note: null,
    operator_note: null,
    created_by: "workbench-gm",
    created_at: "2026-08-04T00:00:00.000Z",
    updated_at: "2026-08-04T00:00:00.000Z",
    ...overrides,
  };
}

function operationResponse(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationOperationResponseV1> = {},
): ThreatPublicationOperationResponseV1 {
  return {
    schema: "dmb_threat_publication_operation_response_v1",
    draft_id: draft.draft_id,
    result_label: "publication_ready",
    operation: buildOperation(draft),
    message: null,
    ...overrides,
  };
}

function buildCandidate(overrides: Partial<ThreatIdentityCandidateV1> = {}): ThreatIdentityCandidateV1 {
  return {
    node_id: "threat:existing-1",
    label: "Existing Threat",
    kind: "threat",
    role: "creature",
    aliases: [],
    campaign_scope: "campaign-1",
    summary: "An existing threat.",
    source_domains: [],
    binding_ids: [],
    has_exact_accepted_binding: false,
    match_score: 0.5,
    match_reasons: ["name_similarity"],
    exact_name_collision: false,
    ...overrides,
  };
}

function buildCandidateSet(
  draft: ThreatDraftV1,
  candidates: ThreatIdentityCandidateV1[],
): ThreatIdentityCandidateSetV1 {
  return {
    schema: "dmb_threat_identity_candidate_set_v1",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    source_digest: "sha256:source",
    expected_parent_revision_id: PARENT_REVISION,
    matching_profile: "dmb_threat_identity_match_v1",
    candidate_query: draft.name,
    eligible_threat_count: candidates.length,
    exact_collision_count: candidates.filter((candidate) => candidate.exact_name_collision).length,
    truncated: false,
    candidates,
    candidate_set_digest: "sha256:candidates",
  };
}

function identityCandidatesReadyResponse(
  draft: ThreatDraftV1,
  candidates: ThreatIdentityCandidateV1[],
): ThreatPublicationIdentityResponseV1 {
  return {
    schema: "dmb_threat_publication_identity_response_v1",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    result_label: "publication_identity_candidates_ready",
    candidate_set: buildCandidateSet(draft, candidates),
    resolution: null,
    predecessor_state: "ready",
    predecessor_usable: true,
    message: null,
  };
}

function resolutionRecord(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationIdentityResolutionV1> = {},
): ThreatPublicationIdentityResolutionV1 {
  return {
    schema: "dmb_threat_publication_identity_resolution_v1",
    resolution_id: RESOLUTION_ID,
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    source_digest: "sha256:source",
    expected_parent_revision_id: PARENT_REVISION,
    matching_profile: "dmb_threat_identity_match_v1",
    candidate_query: draft.name,
    candidate_set: buildCandidateSet(draft, []),
    candidate_set_digest: "sha256:candidates",
    request_digest: "sha256:request",
    decision: "create_new",
    selected_target: null,
    created_node_id: null,
    rejected_candidate_node_ids: [],
    actor: "workbench-gm",
    reason: "Create new Threat",
    state: "active",
    supersedes_resolution_id: null,
    superseded_by_resolution_id: null,
    created_at: "2026-08-04T00:00:00.000Z",
    updated_at: "2026-08-04T00:00:00.000Z",
    ...overrides,
  };
}

function identityDecisionResponse(
  draft: ThreatDraftV1,
  resultLabel: ThreatPublicationIdentityResponseV1["result_label"],
  resolutionOverrides: Partial<ThreatPublicationIdentityResolutionV1> = {},
): ThreatPublicationIdentityResponseV1 {
  return {
    schema: "dmb_threat_publication_identity_response_v1",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    result_label: resultLabel,
    candidate_set: null,
    resolution: resolutionRecord(draft, resolutionOverrides),
    predecessor_state: "ready",
    predecessor_usable: true,
    message: null,
  };
}

function proposalRecord(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationProposalV1> = {},
): ThreatPublicationProposalV1 {
  return {
    schema: "dmb_threat_publication_proposal_v1",
    proposal_id: PROPOSAL_ID,
    request_digest: "sha256:req",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    resolution_id: RESOLUTION_ID,
    source_digest: "sha256:source",
    resolution_request_digest: "sha256:resreq",
    candidate_set_digest: "sha256:candidates",
    expected_parent_revision_id: PARENT_REVISION,
    decision: "create_new",
    threat_node_id: "threat:new-1",
    sealed_proposal_id: "sealed-1",
    sealed_proposal_digest: `sha256:${"a".repeat(64)}`,
    sealed_proposal_version: 1,
    sealed_proposal: {},
    expected_contribution_id: "contrib-1",
    accepted_assertion_ids: ["assert-1"],
    effect_summary: {
      decision: "create_new",
      threat_node_id: "threat:new-1",
      external_resource_node_id: "resource-1",
      binding_edge_id: "edge-1",
      accepted_assertion_count: 3,
      authored_field_assertion_count: 2,
    },
    state: "active",
    supersedes_proposal_id: null,
    superseded_by_proposal_id: null,
    created_by: "workbench-gm",
    operator_note: null,
    created_at: "2026-08-04T00:00:00.000Z",
    updated_at: "2026-08-04T00:00:00.000Z",
    ...overrides,
  };
}

function proposalResponse(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationProposalResponseV1> = {},
): ThreatPublicationProposalResponseV1 {
  return {
    schema: "dmb_threat_publication_proposal_response_v1",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    resolution_id: RESOLUTION_ID,
    result_label: "publication_proposal_ready",
    proposal: proposalRecord(draft),
    message: null,
    ...overrides,
  };
}

function commitRecord(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationCommitV1> = {},
): ThreatPublicationCommitV1 {
  return {
    schema: "dmb_threat_publication_commit_v1",
    commit_id: COMMIT_ID,
    request_digest: "sha256:req",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    proposal_id: PROPOSAL_ID,
    proposal_request_digest: "sha256:preq",
    sealed_proposal_digest: `sha256:${"a".repeat(64)}`,
    sealed_proposal_version: 1,
    resolution_id: RESOLUTION_ID,
    source_digest: "sha256:source",
    resolution_request_digest: "sha256:resreq",
    candidate_set_digest: "sha256:candidates",
    world_id: draft.world_id,
    campaign_id: draft.campaign_id,
    expected_parent_revision_id: PARENT_REVISION,
    expected_contribution_id: "contrib-1",
    expected_contribution_source_payload_sha256: `sha256:${"b".repeat(64)}`,
    accepted_assertion_ids: ["assert-1"],
    decision: "create_new",
    threat_node_id: "threat:new-1",
    selected_target: null,
    external_resource_node_id: "resource-1",
    binding_id: "binding-1",
    binding_edge_id: "edge-1",
    state: "committed_verified",
    merge_attempt_count: 1,
    committed_revision_id: "rev-head-2",
    recovered_via_operation_lookup: false,
    verification_status: "passed",
    verification_codes: [],
    warnings: [],
    created_by: "workbench-gm",
    operator_note: null,
    created_at: "2026-08-04T00:00:00.000Z",
    updated_at: "2026-08-04T00:00:00.000Z",
    ...overrides,
  };
}

function commitResponse(
  draft: ThreatDraftV1,
  overrides: Partial<ThreatPublicationCommitResponseV1> = {},
): ThreatPublicationCommitResponseV1 {
  return {
    schema: "dmb_threat_publication_commit_response_v1",
    draft_id: draft.draft_id,
    operation_id: OPERATION_ID,
    proposal_id: PROPOSAL_ID,
    commit_id: COMMIT_ID,
    result_label: "publication_commit_verified",
    commit_admitted: true,
    commit: commitRecord(draft),
    retry_allowed: false,
    message: null,
    ...overrides,
  };
}

describe("ThreatPublicationPanel", () => {
  it("shows Publish for an eligible draft and a prerequisite message otherwise, never calling the API when ineligible", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const eligibleRender = render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );
    expect(await screen.findByTestId("publish")).toBeInTheDocument();
    eligibleRender.unmount();

    const ineligibleDraft = buildDraft({ workflow_state: "drafting", accepted_mechanics_ref: null });
    render(
      <ThreatPublicationPanel
        draft={ineligibleDraft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
      />,
    );
    expect(screen.queryByTestId("publish")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(/accepted mechanics/i);
    expect(api.beginThreatPublicationOperation).not.toHaveBeenCalled();
  });

  it("writes the session pointer before begin resolves and shows the candidate CTA once ready", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    let resolveBegin: ((value: ThreatPublicationOperationResponseV1) => void) | undefined;
    vi.mocked(api.beginThreatPublicationOperation).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveBegin = resolve;
        }),
    );
    const user = userEvent.setup();

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));

    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      operation_id: OPERATION_ID,
      resolution_id: null,
      proposal_id: null,
      commit_id: null,
      stage: "operation",
    });
    expect(api.beginThreatPublicationOperation).toHaveBeenCalledWith(draft.draft_id, {
      schema: "dmb_begin_threat_publication_operation_request_v1",
      operation_id: OPERATION_ID,
      expected_draft_version: draft.version,
      expected_parent_revision_id: PARENT_REVISION,
      actor: "workbench-gm",
      operator_note: null,
    });
    expect(screen.queryByTestId("publish")).not.toBeInTheDocument();

    await act(async () => {
      resolveBegin?.(operationResponse(draft));
      await Promise.resolve();
    });

    expect(await screen.findByTestId("prepare-candidates")).toBeInTheDocument();
  });

  it("shows an honest blocked state for publication_busy without a matching local operation", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue({
      schema: "dmb_threat_publication_operation_response_v1",
      draft_id: draft.draft_id,
      result_label: "publication_busy",
      operation: null,
      message: "Another publication operation is active.",
    });
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));

    expect(await screen.findByRole("status")).toHaveTextContent(
      /another publication is active and cannot be safely recovered/i,
    );
    expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    expect(api.beginThreatPublicationOperation).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("cancel-operation")).not.toBeInTheDocument();
  });

  it("disables create-new until every exact_name_collision candidate is rejected, then posts the rejected ids", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    const collidingA = buildCandidate({ node_id: "threat:collide-a", label: "Collide A", exact_name_collision: true });
    const collidingB = buildCandidate({ node_id: "threat:collide-b", label: "Collide B", exact_name_collision: true });
    const clean = buildCandidate({ node_id: "threat:clean", label: "Clean", exact_name_collision: false });
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [collidingA, collidingB, clean]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", {
        decision: "create_new",
        rejected_candidate_node_ids: [collidingA.node_id, collidingB.node_id],
      }),
    );
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await screen.findByTestId("decide-create");

    expect(screen.getByTestId("decide-create")).toBeDisabled();

    await user.click(screen.getByTestId(`reject-candidate-${collidingA.node_id}`));
    expect(screen.getByTestId("decide-create")).toBeDisabled();

    await user.click(screen.getByTestId(`reject-candidate-${collidingB.node_id}`));
    expect(screen.getByTestId("decide-create")).toBeEnabled();

    await user.click(screen.getByTestId("decide-create"));

    expect(api.createThreatIdentityResolution).toHaveBeenCalledWith(
      draft.draft_id,
      OPERATION_ID,
      expect.objectContaining({
        resolution_id: RESOLUTION_ID,
        decision: "create_new",
        rejected_candidate_node_ids: [collidingA.node_id, collidingB.node_id],
      }),
    );
  });

  it("posts the exact selected node_id for connect-existing", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    const candidateOne = buildCandidate({ node_id: "threat:one", label: "One" });
    const candidateTwo = buildCandidate({ node_id: "threat:two", label: "Two" });
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [candidateOne, candidateTwo]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_connected_existing", {
        decision: "connect_existing",
        selected_target: candidateTwo,
      }),
    );
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await screen.findByTestId("decide-connect");
    expect(screen.getByTestId("decide-connect")).toBeDisabled();

    await user.click(screen.getByTestId(`select-connect-${candidateTwo.node_id}`));
    expect(screen.getByTestId("decide-connect")).toBeEnabled();
    await user.click(screen.getByTestId("decide-connect"));

    expect(api.createThreatIdentityResolution).toHaveBeenCalledWith(
      draft.draft_id,
      OPERATION_ID,
      expect.objectContaining({
        decision: "connect_existing",
        target_node_id: candidateTwo.node_id,
      }),
    );
  });

  it("ends the journey on refuse without preparing a proposal or confirming", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [buildCandidate()]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_refused", { decision: "refuse" }),
    );
    vi.mocked(api.cancelThreatPublicationOperation).mockResolvedValue({
      schema: "dmb_threat_publication_operation_response_v1",
      draft_id: draft.draft_id,
      result_label: "publication_cancelled",
      operation: {
        ...operationResponse(draft).operation!,
        state: "cancelled",
      },
      message: "Cancelled by operator.",
    });
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-refuse"));

    expect(await screen.findByText(/no graph write occurred/i)).toBeInTheDocument();
    expect(api.prepareThreatPublicationProposal).not.toHaveBeenCalled();
    expect(api.confirmThreatPublicationCommit).not.toHaveBeenCalled();
    await waitFor(() => {
      expect(api.cancelThreatPublicationOperation).toHaveBeenCalledWith(
        draft.draft_id,
        OPERATION_ID,
        expect.objectContaining({
          schema: "dmb_cancel_threat_publication_operation_request_v1",
          note: "released after identity refuse",
        }),
      );
    });
    expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    // After refuse releases the server lock, Publish is available again.
    expect(await screen.findByTestId("publish")).toBeInTheDocument();
  });

  it("keeps refusal recovery distinct until a retry returns publication_cancelled", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [buildCandidate()]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_refused", { decision: "refuse" }),
    );
    vi.mocked(api.cancelThreatPublicationOperation)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce({
        schema: "dmb_threat_publication_operation_response_v1",
        draft_id: draft.draft_id,
        result_label: "publication_cancelled",
        operation: {
          ...operationResponse(draft).operation!,
          state: "cancelled",
        },
        message: "Cancelled by operator.",
      });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-refuse"));

    expect(
      within(await screen.findByTestId("identity-decision")).getByRole("alert"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("retry-cancel")).toBeInTheDocument();
    expect(screen.getByTestId("reread-operation")).toBeInTheDocument();
    expect(screen.queryByTestId("publication-start-over")).not.toBeInTheDocument();
    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      operation_id: OPERATION_ID,
      resolution_id: RESOLUTION_ID,
      stage: "identity",
    });

    await user.click(screen.getByTestId("retry-cancel"));

    await waitFor(() => {
      expect(api.cancelThreatPublicationOperation).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId("publish")).toBeInTheDocument();
    });
    expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
  });

  it("shows published on a verified commit, confirms exactly once, and removes Confirm permanently", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue(commitResponse(draft));

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    expect(await screen.findByText(/^Published\./)).toBeInTheDocument();
    expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("confirm")).not.toBeInTheDocument();
  });

  it("shows verification-needs-attention copy for committed_unverified, never confirms twice, and allows reread", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    const unverifiedResponse = commitResponse(draft, {
      result_label: "publication_commit_committed_unverified",
      commit: commitRecord(draft, {
        state: "committed_unverified",
        verification_status: "degraded",
        verification_codes: ["vc-mismatch-1"],
      }),
    });
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue(unverifiedResponse);
    vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(unverifiedResponse);

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    expect(await screen.findByText(/verification needs attention/i)).toBeInTheDocument();
    expect(screen.queryByTestId("confirm")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("reread-commit"));
    expect(api.getThreatPublicationCommit).toHaveBeenCalledWith(draft.draft_id, OPERATION_ID, COMMIT_ID);
    expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);
  });

  it("preserves the commit id across a lost confirm response and never confirms twice after remount", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockRejectedValue(new TypeError("Failed to fetch"));

    const user = userEvent.setup();
    const firstMount = render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        commit_id: COMMIT_ID,
        stage: "commit",
      });
    });
    expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);

    firstMount.unmount();

    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.getThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.getThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(draft));

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    await waitFor(() => {
      expect(api.getThreatPublicationCommit).toHaveBeenCalledWith(draft.draft_id, OPERATION_ID, COMMIT_ID);
    });
    expect(await screen.findByText(/^Published\./)).toBeInTheDocument();
    expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);
  });

  it("ignores a stale begin resolution after switching to a different draft", async () => {
    const api = buildApiMocks();
    const draftA = buildDraft({ draft_id: "draft-a" });
    const draftB = buildDraft({ draft_id: "draft-b" });
    const storage = createMemoryStorage();
    let resolveBeginA: ((value: ThreatPublicationOperationResponseV1) => void) | undefined;
    vi.mocked(api.beginThreatPublicationOperation).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveBeginA = resolve;
        }),
    );

    const user = userEvent.setup();
    const { rerender } = render(
      <ThreatPublicationPanel
        draft={draftA}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    expect(readThreatPublicationSession(draftA.draft_id, storage)).not.toBeNull();

    rerender(
      <ThreatPublicationPanel
        draft={draftB}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator(["op-b"])}
      />,
    );

    expect(await screen.findByTestId("publish")).toBeInTheDocument();

    await act(async () => {
      resolveBeginA?.(operationResponse(draftA));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByTestId("publish")).toBeInTheDocument();
    expect(screen.queryByTestId("prepare-candidates")).not.toBeInTheDocument();
    expect(readThreatPublicationSession(draftB.draft_id, storage)).toBeNull();
    expect(readThreatPublicationSession(draftA.draft_id, storage)).not.toBeNull();
  });

  it("does not update state or open the next step when prepare-candidates resolves after unmount", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    let resolveCandidates: ((value: ThreatPublicationIdentityResponseV1) => void) | undefined;
    vi.mocked(api.prepareThreatIdentityCandidates).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCandidates = resolve;
        }),
    );
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    const user = userEvent.setup();
    const { unmount } = render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));

    unmount();

    await act(async () => {
      resolveCandidates?.(identityCandidatesReadyResponse(draft, [buildCandidate()]));
      await Promise.resolve();
    });

    expect(consoleError).not.toHaveBeenCalled();
    consoleError.mockRestore();
  });

  it("fails closed with a recovery error on restore identity mismatch and never auto-fires begin", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    const pointer: ThreatPublicationWorkbenchSessionV1 = {
      schema: SESSION_SCHEMA,
      draft_id: draft.draft_id,
      draft_version: draft.version,
      operation_id: OPERATION_ID,
      resolution_id: null,
      proposal_id: null,
      commit_id: null,
      stage: "operation",
      updated_at: "2026-08-04T00:00:00.000Z",
    };
    writeThreatPublicationSession(pointer, storage);

    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, { draft_id: "some-other-draft" }),
    );

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    expect(await screen.findByText(/could not be safely restored/i)).toBeInTheDocument();
    expect(api.beginThreatPublicationOperation).not.toHaveBeenCalled();
  });

  function staleOperationResponse(
    draft: ThreatDraftV1,
    overrides: Partial<ThreatPublicationOperationResponseV1> = {},
  ): ThreatPublicationOperationResponseV1 {
    return operationResponse(draft, {
      result_label: "publication_stale",
      operation: buildOperation(draft, {
        state: "stale",
        stale_reasons: ["graph_parent_changed"],
      }),
      ...overrides,
    });
  }

  function writeOperationPointer(
    draft: ThreatDraftV1,
    storage: Storage,
    operationId: string = OPERATION_ID,
  ): void {
    writeThreatPublicationSession(
      {
        schema: SESSION_SCHEMA,
        draft_id: draft.draft_id,
        draft_version: draft.version,
        operation_id: operationId,
        resolution_id: null,
        proposal_id: null,
        commit_id: null,
        stage: "operation",
        updated_at: "2026-08-04T00:00:00.000Z",
      },
      storage,
    );
  }

  async function mountRestoredStaleOperation(
    api: ThreatPublicationApi,
    draft: ThreatDraftV1,
    storage: Storage,
    extraProps: Partial<ThreatPublicationPanelProps> = {},
  ): Promise<void> {
    writeOperationPointer(draft, storage);
    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(staleOperationResponse(draft));
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        {...extraProps}
      />,
    );
    await screen.findByTestId("retry-operation");
  }

  it("does not advance the session pointer when a rejected operation retry returns no ready successor", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    await mountRestoredStaleOperation(api, draft, storage, {
      generateId: sequentialIdGenerator([OPERATION_ID_NEW]),
    });

    vi.mocked(api.refreshThreatPublicationOperation).mockResolvedValue(staleOperationResponse(draft));
    vi.mocked(api.retryThreatPublicationOperation).mockResolvedValue({
      schema: "dmb_threat_publication_operation_response_v1",
      draft_id: draft.draft_id,
      result_label: "publication_parent_mismatch",
      operation: buildOperation(draft, { state: "stale", stale_reasons: ["graph_parent_changed"] }),
      message: "Parent revision no longer matches.",
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("retry-operation"));

    await waitFor(() => {
      expect(api.retryThreatPublicationOperation).toHaveBeenCalledTimes(1);
    });

    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      operation_id: OPERATION_ID,
    });
    expect(screen.getByText(new RegExp(`operation_id: ${OPERATION_ID}`))).toBeInTheDocument();
    expect(screen.getByText(/Parent revision no longer matches/)).toBeInTheDocument();
    expect(screen.getByTestId("operation-status")).toHaveAttribute(
      "data-operation-result",
      "publication_parent_mismatch",
    );
    expect(screen.queryByTestId("retry-operation")).not.toBeInTheDocument();
  });

  it("shows retry-operation again only after refresh returns publication_stale", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    await mountRestoredStaleOperation(api, draft, storage, {
      generateId: sequentialIdGenerator([OPERATION_ID_NEW]),
    });

    vi.mocked(api.refreshThreatPublicationOperation)
      .mockResolvedValueOnce(staleOperationResponse(draft))
      .mockResolvedValueOnce(staleOperationResponse(draft));
    vi.mocked(api.retryThreatPublicationOperation).mockResolvedValue({
      schema: "dmb_threat_publication_operation_response_v1",
      draft_id: draft.draft_id,
      result_label: "publication_source_mismatch",
      operation: buildOperation(draft, { state: "stale", stale_reasons: ["graph_parent_changed"] }),
      message: "Source digest no longer matches.",
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("retry-operation"));

    await waitFor(() => {
      expect(screen.getByTestId("operation-status")).toHaveAttribute(
        "data-operation-result",
        "publication_source_mismatch",
      );
    });
    expect(screen.queryByTestId("retry-operation")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("refresh-operation"));

    await waitFor(() => {
      expect(screen.getByTestId("operation-status")).toHaveAttribute("data-operation-result", "publication_stale");
    });
    expect(screen.getByTestId("retry-operation")).toBeInTheDocument();
  });

  it("advances the session pointer only after a successful stale retry returns publication_ready with the new operation id", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    await mountRestoredStaleOperation(api, draft, storage, {
      generateId: sequentialIdGenerator([OPERATION_ID_NEW]),
    });

    vi.mocked(api.refreshThreatPublicationOperation).mockResolvedValue(staleOperationResponse(draft));
    vi.mocked(api.retryThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        result_label: "publication_ready",
        operation: buildOperation(draft, {
          operation_id: OPERATION_ID_NEW,
          state: "ready",
          stale_reasons: [],
        }),
      }),
    );

    const user = userEvent.setup();
    await user.click(screen.getByTestId("retry-operation"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID_NEW,
      });
    });
    expect(screen.getByText(new RegExp(`operation_id: ${OPERATION_ID_NEW}`))).toBeInTheDocument();
    expect(screen.getByTestId("prepare-candidates")).toBeInTheDocument();
    expect(screen.queryByTestId("retry-operation")).not.toBeInTheDocument();
  });

  it("shows retry-operation only for stale-active operations and refresh-operation for any active operation", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();

    const cases: Array<{
      label: ThreatPublicationOperationResponseV1["result_label"];
      state: ThreatPublicationOperationV1["state"];
      expectRetry: boolean;
      expectIdle: boolean;
    }> = [
      { label: "publication_ready", state: "ready", expectRetry: false, expectIdle: false },
      { label: "publication_cancelled", state: "cancelled", expectRetry: false, expectIdle: true },
      { label: "publication_invalid_state", state: "ready", expectRetry: false, expectIdle: false },
      { label: "publication_stale", state: "stale", expectRetry: true, expectIdle: false },
    ];

    for (const testCase of cases) {
      storage.clear();
      vi.clearAllMocks();
      writeOperationPointer(draft, storage);
      vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
        operationResponse(draft, {
          result_label: testCase.label,
          operation: buildOperation(draft, { state: testCase.state }),
        }),
      );

      const { unmount } = render(
        <ThreatPublicationPanel
          draft={draft}
          expectedParentRevisionId={PARENT_REVISION}
          api={api}
          storage={storage}
        />,
      );

      if (testCase.expectIdle) {
        expect(await screen.findByTestId("publish")).toBeInTheDocument();
        expect(screen.queryByTestId("refresh-operation")).not.toBeInTheDocument();
        expect(screen.queryByTestId("retry-operation")).not.toBeInTheDocument();
      } else {
        await waitFor(() => {
          expect(screen.getByTestId("refresh-operation")).toBeInTheDocument();
        });
        if (testCase.expectRetry) {
          expect(screen.getByTestId("retry-operation")).toBeInTheDocument();
        } else {
          expect(screen.queryByTestId("retry-operation")).not.toBeInTheDocument();
        }
      }
      unmount();
    }
  });

  it("clears the stored session when operation reread returns publication_cancelled", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    writeOperationPointer(draft, storage);
    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        result_label: "publication_ready",
        operation: buildOperation(draft, { state: "ready" }),
      }),
    );
    vi.mocked(api.refreshThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        result_label: "publication_cancelled",
        operation: buildOperation(draft, { state: "cancelled" }),
        message: "Cancelled by operator.",
      }),
    );

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    await user.click(await screen.findByTestId("refresh-operation"));
    await waitFor(() => {
      expect(screen.getByTestId("publish")).toBeInTheDocument();
      expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    });
    expect(api.refreshThreatPublicationOperation).toHaveBeenCalledWith(draft.draft_id, OPERATION_ID);
  });

  it("passes a freshly resolved parent revision id to retryThreatPublicationOperation", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    const resolveExpectedParentRevisionId = vi.fn().mockResolvedValue(PARENT_REVISION_FRESH);
    await mountRestoredStaleOperation(api, draft, storage, {
      generateId: sequentialIdGenerator([OPERATION_ID_NEW]),
      resolveExpectedParentRevisionId,
    });

    vi.mocked(api.refreshThreatPublicationOperation).mockResolvedValue(staleOperationResponse(draft));
    vi.mocked(api.retryThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        result_label: "publication_parent_mismatch",
        operation: buildOperation(draft, { state: "stale", stale_reasons: ["graph_parent_changed"] }),
      }),
    );

    const user = userEvent.setup();
    await user.click(screen.getByTestId("retry-operation"));

    await waitFor(() => {
      expect(resolveExpectedParentRevisionId).toHaveBeenCalledTimes(1);
    });
    expect(api.retryThreatPublicationOperation).toHaveBeenCalledWith(
      draft.draft_id,
      OPERATION_ID,
      expect.objectContaining({
        new_operation_id: OPERATION_ID_NEW,
        expected_parent_revision_id: PARENT_REVISION_FRESH,
      }),
    );
  });

  it("reuses the same commit id and sealed proposal digest when retrying recovery_pending confirmation", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    const sealedDigest = `sha256:${"a".repeat(64)}`;

    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(
      proposalResponse(draft, {
        proposal: proposalRecord(draft, {
          sealed_proposal_digest: sealedDigest,
          expected_parent_revision_id: PARENT_REVISION,
        }),
      }),
    );

    const recoveryPending = commitResponse(draft, {
      result_label: "publication_commit_recovery_pending",
      retry_allowed: true,
      commit: commitRecord(draft, {
        state: "committing",
        merge_attempt_count: 1,
        committed_revision_id: null,
      }),
    });
    vi.mocked(api.confirmThreatPublicationCommit)
      .mockResolvedValueOnce(recoveryPending)
      .mockResolvedValueOnce(commitResponse(draft));

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    await screen.findByTestId("retry-confirm");
    await user.click(screen.getByTestId("retry-confirm"));

    await waitFor(() => {
      expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(2);
    });

    const firstCall = vi.mocked(api.confirmThreatPublicationCommit).mock.calls[0]?.[3];
    const secondCall = vi.mocked(api.confirmThreatPublicationCommit).mock.calls[1]?.[3];
    expect(firstCall?.commit_id).toBe(COMMIT_ID);
    expect(secondCall?.commit_id).toBe(COMMIT_ID);
    expect(firstCall?.sealed_proposal_digest).toBe(sealedDigest);
    expect(secondCall?.sealed_proposal_digest).toBe(sealedDigest);
    expect(firstCall?.expected_parent_revision_id).toBe(PARENT_REVISION);
    expect(secondCall?.expected_parent_revision_id).toBe(PARENT_REVISION);
  });

  it("re-anchors on draft version or accepted mechanics changes and blocks stale async from completing", async () => {
    const api = buildApiMocks();
    const draftV3 = buildDraft({ version: 3 });
    const draftV4 = buildDraft({
      version: 4,
      accepted_mechanics_ref: {
        ...buildDraft().accepted_mechanics_ref!,
        revision_id: "sb-rev-v4",
        definition_digest: "sha256:v4digest",
      },
    });
    const storage = createMemoryStorage();
    writeThreatPublicationSession(
      {
        schema: SESSION_SCHEMA,
        draft_id: draftV3.draft_id,
        draft_version: 3,
        operation_id: OPERATION_ID,
        resolution_id: null,
        proposal_id: null,
        commit_id: null,
        stage: "operation",
        updated_at: "2026-08-04T00:00:00.000Z",
      },
      storage,
    );

    const mismatchRender = render(
      <ThreatPublicationPanel
        draft={draftV4}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );
    expect(await screen.findByText(/draft changed since a publication was started/i)).toBeInTheDocument();
    expect(screen.getByTestId("clear-pointer")).toBeInTheDocument();
    expect(api.getThreatPublicationOperation).not.toHaveBeenCalled();
    mismatchRender.unmount();

    storage.clear();
    let resolveBegin: ((value: ThreatPublicationOperationResponseV1) => void) | undefined;
    vi.mocked(api.beginThreatPublicationOperation).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveBegin = resolve;
        }),
    );
    const user = userEvent.setup();
    const { rerender } = render(
      <ThreatPublicationPanel
        draft={draftV3}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    rerender(
      <ThreatPublicationPanel
        draft={draftV4}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    expect(await screen.findByText(/draft changed since a publication was started/i)).toBeInTheDocument();
    expect(screen.queryByTestId("prepare-candidates")).not.toBeInTheDocument();

    await act(async () => {
      resolveBegin?.(operationResponse(draftV3));
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText(/draft changed since a publication was started/i)).toBeInTheDocument();
    expect(screen.queryByTestId("prepare-candidates")).not.toBeInTheDocument();
  });

  it("shows accepted mechanics from the operation source snapshot, not the mutable draft prop", async () => {
    const api = buildApiMocks();
    const draftCurrent = buildDraft({
      accepted_mechanics_ref: {
        ...buildDraft().accepted_mechanics_ref!,
        revision_id: "sb-rev-NEW",
        definition_digest: "sha256:newdigest",
      },
    });
    const snapshotDraft = buildDraft({
      accepted_mechanics_ref: {
        ...buildDraft().accepted_mechanics_ref!,
        revision_id: "sb-rev-OLD",
        definition_digest: "sha256:olddigest",
      },
    });

    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(
      operationResponse(draftCurrent, {
        operation: buildOperation(draftCurrent, {
          source_snapshot: sourceSnapshot(snapshotDraft),
        }),
      }),
    );
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draftCurrent, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draftCurrent, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draftCurrent));

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draftCurrent}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));

    expect(await screen.findByTestId("proposal-review")).toBeInTheDocument();
    const proposalReview = screen.getByTestId("proposal-review");
    expect(within(proposalReview).getByText(/sb-rev-OLD/)).toBeInTheDocument();
    expect(within(proposalReview).queryByText(/sb-rev-NEW/)).not.toBeInTheDocument();
    expect(within(proposalReview).getByText(/sha256:olddigest/)).toBeInTheDocument();
  });

  it("keeps connect and reject selections mutually exclusive and omits the connect target from rejected ids", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    const target = buildCandidate({ node_id: "threat:connect-target", label: "Connect Target" });
    const other = buildCandidate({ node_id: "threat:other", label: "Other" });
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [target, other]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_connected_existing", {
        decision: "connect_existing",
        selected_target: target,
      }),
    );

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));

    await user.click(screen.getByTestId(`reject-candidate-${target.node_id}`));
    expect(screen.getByTestId(`reject-candidate-${target.node_id}`)).toBeChecked();
    expect(screen.getByTestId(`select-connect-${target.node_id}`)).not.toBeChecked();

    await user.click(screen.getByTestId(`select-connect-${target.node_id}`));
    expect(screen.getByTestId(`reject-candidate-${target.node_id}`)).not.toBeChecked();
    expect(screen.getByTestId(`select-connect-${target.node_id}`)).toBeChecked();

    await user.click(screen.getByTestId(`reject-candidate-${target.node_id}`));
    expect(screen.getByTestId(`select-connect-${target.node_id}`)).not.toBeChecked();

    await user.click(screen.getByTestId(`select-connect-${target.node_id}`));
    await user.click(screen.getByTestId("decide-connect"));

    expect(api.createThreatIdentityResolution).toHaveBeenCalledWith(
      draft.draft_id,
      OPERATION_ID,
      expect.objectContaining({
        decision: "connect_existing",
        target_node_id: target.node_id,
        rejected_candidate_node_ids: [],
      }),
    );
  });

  it("clears identity decision controls when the candidate set changes during create resolution", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [buildCandidate()]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue({
      schema: "dmb_threat_publication_identity_response_v1",
      draft_id: draft.draft_id,
      operation_id: OPERATION_ID,
      result_label: "publication_identity_candidate_set_changed",
      candidate_set: null,
      resolution: null,
      predecessor_state: "ready",
      predecessor_usable: true,
      message: "Candidate set changed upstream.",
    });

    const user = userEvent.setup();
    const { unmount } = render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    expect(screen.getByTestId("identity-candidates")).toBeInTheDocument();

    await user.click(screen.getByTestId("decide-create"));

    await waitFor(() => {
      expect(screen.queryByTestId("identity-candidates")).not.toBeInTheDocument();
    });
    expect(screen.queryByTestId("decide-create")).not.toBeInTheDocument();
    expect(screen.queryByTestId("decide-connect")).not.toBeInTheDocument();
    expect(screen.getByTestId("prepare-candidates")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent(/candidate set changed/i);
    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      operation_id: OPERATION_ID,
      resolution_id: null,
      proposal_id: null,
      commit_id: null,
      stage: "operation",
    });

    unmount();

    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    expect(await screen.findByTestId("prepare-candidates")).toBeInTheDocument();
    expect(screen.queryByText(/could not be safely restored/i)).not.toBeInTheDocument();
  });

  it("rolls back proposal_id to identity stage when prepare proposal is definitively rejected", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue({
      schema: "dmb_threat_publication_proposal_response_v1",
      draft_id: draft.draft_id,
      operation_id: OPERATION_ID,
      resolution_id: RESOLUTION_ID,
      result_label: "publication_proposal_operation_not_ready",
      proposal: null,
      message: "Operation parent revision no longer matches.",
    });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID,
        resolution_id: RESOLUTION_ID,
        proposal_id: null,
        stage: "identity",
      });
    });
    expect(screen.getByTestId("prepare-proposal")).toBeInTheDocument();
    expect(screen.queryByTestId("proposal-review")).not.toBeInTheDocument();
    expect(screen.getByTestId("identity-decision")).toBeInTheDocument();
  });

  it("clears the session pointer when begin returns a definitive rejection without an operation", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue({
      schema: "dmb_threat_publication_operation_response_v1",
      draft_id: draft.draft_id,
      result_label: "publication_parent_mismatch",
      operation: null,
      message: "Parent revision no longer matches.",
    });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    });
    expect(screen.getByText(/Parent revision no longer matches/)).toBeInTheDocument();
    expect(screen.getByTestId("publish")).toBeInTheDocument();
    expect(screen.queryByTestId("publication-active")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refresh-operation")).not.toBeInTheDocument();
  });

  it("follows superseded_by_operation_id on restore and advances the session pointer atomically", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    writeOperationPointer(draft, storage, OPERATION_ID);

    vi.mocked(api.getThreatPublicationOperation).mockImplementation((_draftId, operationId) => {
      if (operationId === OPERATION_ID) {
        return Promise.resolve(
          operationResponse(draft, {
            result_label: "publication_superseded",
            operation: buildOperation(draft, {
              state: "superseded",
              superseded_by_operation_id: OPERATION_ID_NEW,
            }),
          }),
        );
      }
      if (operationId === OPERATION_ID_NEW) {
        return Promise.resolve(
          operationResponse(draft, {
            result_label: "publication_ready",
            operation: buildOperation(draft, {
              operation_id: OPERATION_ID_NEW,
              state: "ready",
              stale_reasons: [],
            }),
          }),
        );
      }
      return Promise.reject(new Error(`Unexpected operation id ${operationId}`));
    });

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID_NEW,
        resolution_id: null,
        proposal_id: null,
        commit_id: null,
        stage: "operation",
      });
    });
    expect(screen.getByText(new RegExp(`operation_id: ${OPERATION_ID_NEW}`))).toBeInTheDocument();
    expect(await screen.findByTestId("prepare-candidates")).toBeInTheDocument();
    expect(screen.queryByText(/could not be safely restored/i)).not.toBeInTheDocument();
  });

  it("hides cancel-operation after identity, proposal, or commit authority exists", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue(commitResponse(draft));

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    expect(await screen.findByTestId("cancel-operation")).toBeInTheDocument();

    await user.click(await screen.findByTestId("prepare-candidates"));
    expect(screen.getByTestId("cancel-operation")).toBeInTheDocument();

    await user.click(await screen.findByTestId("decide-create"));
    await waitFor(() => {
      expect(screen.queryByTestId("cancel-operation")).not.toBeInTheDocument();
    });

    await user.click(await screen.findByTestId("prepare-proposal"));
    expect(screen.queryByTestId("cancel-operation")).not.toBeInTheDocument();

    await user.click(await screen.findByTestId("confirm"));
    await waitFor(() => {
      expect(screen.queryByTestId("cancel-operation")).not.toBeInTheDocument();
    });
  });

  it("does not treat a verified commit label as durable without committed_revision_id", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));

    const labelOnlyVerified = commitResponse(draft, {
      result_label: "publication_commit_verified",
      commit: commitRecord(draft, { committed_revision_id: null }),
    });
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue(labelOnlyVerified);
    vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(labelOnlyVerified);

    const user = userEvent.setup();
    const firstMount = render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    await waitFor(() => {
      expect(screen.getByTestId("commit-status")).toHaveAttribute(
        "data-commit-result",
        "publication_commit_verified",
      );
    });
    const publishedLine = screen.getByText(/^Published\./);
    expect(publishedLine).toBeInTheDocument();
    expect(publishedLine).not.toHaveTextContent("rev-head-2");
    expect(screen.queryByTestId("retry-confirm")).not.toBeInTheDocument();

    firstMount.unmount();

    writeThreatPublicationSession(
      {
        schema: SESSION_SCHEMA,
        draft_id: draft.draft_id,
        draft_version: draft.version,
        operation_id: OPERATION_ID,
        resolution_id: null,
        proposal_id: null,
        commit_id: null,
        stage: "operation",
        updated_at: "2026-08-04T00:00:00.000Z",
      },
      storage,
    );
    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
      staleOperationResponse(draft),
    );

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    expect(await screen.findByTestId("retry-operation")).toBeInTheDocument();
  });

  it("fails closed on restore when the operation source snapshot draft_id mismatches the active draft", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    writeOperationPointer(draft, storage);

    const foreignDraft = buildDraft({ draft_id: "99999999-9999-4999-8999-999999999999" });
    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        operation: buildOperation(draft, {
          source_snapshot: sourceSnapshot(foreignDraft),
        }),
      }),
    );

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    expect(await screen.findByText(/source snapshot does not match the active draft/i)).toBeInTheDocument();
    expect(api.getThreatIdentityResolution).not.toHaveBeenCalled();
  });

  it("offers clear-pointer after a recovery error and returns to idle when used", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    writeOperationPointer(draft, storage);

    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(
      operationResponse(draft, {
        draft_id: "99999999-9999-4999-8999-999999999999",
        operation: buildOperation(draft),
      }),
    );

    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
      />,
    );

    expect(await screen.findByText(/could not be safely restored/i)).toBeInTheDocument();
    expect(screen.getByTestId("clear-pointer")).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByTestId("clear-pointer"));

    expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    expect(screen.getByTestId("publish")).toBeInTheDocument();
  });

  it("shows accepted assertion count without summing authored field assertions", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(
      proposalResponse(draft, {
        proposal: proposalRecord(draft, {
          effect_summary: {
            decision: "create_new",
            threat_node_id: "threat:new-1",
            external_resource_node_id: "resource-1",
            binding_edge_id: "edge-1",
            accepted_assertion_count: 3,
            authored_field_assertion_count: 2,
          },
        }),
      }),
    );

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));

    expect(await screen.findByText("Accepted assertions: 3 (2 authored fields)")).toBeInTheDocument();
    expect(screen.queryByText(/Accepted assertions: 5/)).not.toBeInTheDocument();
  });

  it("keeps the uncertain resolution id after a lost identity response and only permits same-id replay or exact GET", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    const RESOLUTION_ID_B = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValueOnce(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );

    const user = userEvent.setup();
    const generateId = sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, RESOLUTION_ID_B]);
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={generateId}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        resolution_id: RESOLUTION_ID,
        stage: "identity",
      });
    });
    expect(await screen.findByTestId("identity-uncertainty")).toBeInTheDocument();
    expect(screen.queryByTestId("decide-create")).not.toBeInTheDocument();
    expect(screen.queryByTestId("decide-connect")).not.toBeInTheDocument();
    expect(screen.queryByTestId("decide-refuse")).not.toBeInTheDocument();
    expect(api.createThreatIdentityResolution).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("replay-identity"));

    await waitFor(() => {
      expect(api.createThreatIdentityResolution).toHaveBeenCalledTimes(2);
    });
    expect(api.createThreatIdentityResolution).toHaveBeenLastCalledWith(
      draft.draft_id,
      OPERATION_ID,
      expect.objectContaining({ resolution_id: RESOLUTION_ID }),
    );
    expect(await screen.findByTestId("identity-decision")).toBeInTheDocument();
    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      resolution_id: RESOLUTION_ID,
    });
  });

  it("keeps the uncertain proposal id after a lost prepare response and only permits same-id replay or exact GET", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    const PROPOSAL_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValueOnce(proposalResponse(draft));

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, PROPOSAL_ID_B])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        proposal_id: PROPOSAL_ID,
        stage: "proposal",
      });
    });
    expect(await screen.findByTestId("proposal-uncertainty")).toBeInTheDocument();
    expect(screen.queryByTestId("prepare-proposal")).not.toBeInTheDocument();
    expect(api.prepareThreatPublicationProposal).toHaveBeenCalledTimes(1);

    await user.click(screen.getByTestId("replay-proposal"));

    await waitFor(() => {
      expect(api.prepareThreatPublicationProposal).toHaveBeenCalledTimes(2);
    });
    expect(api.prepareThreatPublicationProposal).toHaveBeenLastCalledWith(
      draft.draft_id,
      OPERATION_ID,
      RESOLUTION_ID,
      expect.objectContaining({ proposal_id: PROPOSAL_ID }),
    );
    expect(await screen.findByTestId("proposal-review")).toBeInTheDocument();
  });

  it("rolls commit_id back to proposal stage when confirm returns any pre-admission rejection with commit null", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue({
      schema: "dmb_threat_publication_commit_response_v1",
      draft_id: draft.draft_id,
      operation_id: OPERATION_ID,
      proposal_id: PROPOSAL_ID,
      commit_id: COMMIT_ID,
      result_label: "publication_commit_integrity_failure",
      commit_admitted: false,
      commit: null,
      retry_allowed: false,
      message: "graph head could not be read before admission",
    });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        proposal_id: PROPOSAL_ID,
        commit_id: null,
        stage: "proposal",
      });
    });
    expect(screen.getByText(/graph head could not be read before admission/)).toBeInTheDocument();
    expect(screen.getByTestId("confirm")).toBeInTheDocument();
    expect(screen.queryByTestId("commit-status")).not.toBeInTheDocument();
    expect(screen.queryByTestId("reread-commit")).not.toBeInTheDocument();
  });

  it("retains the exact commit pointer when confirm cannot determine ledger admission", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockResolvedValue({
      schema: "dmb_threat_publication_commit_response_v1",
      draft_id: draft.draft_id,
      operation_id: OPERATION_ID,
      proposal_id: PROPOSAL_ID,
      commit_id: COMMIT_ID,
      result_label: "publication_commit_storage_unavailable",
      commit_admitted: null,
      commit: null,
      retry_allowed: false,
      message: "publication commit ledger unavailable",
    });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID,
        proposal_id: PROPOSAL_ID,
        commit_id: COMMIT_ID,
        stage: "commit",
      });
    });
    expect(screen.getByTestId("reread-commit")).toBeInTheDocument();
    expect(screen.queryByTestId("confirm")).not.toBeInTheDocument();
    expect(screen.getByText(/ledger unavailable/i)).toBeInTheDocument();
  });

  it("rolls an exact GET not-found back to proposal review without treating it as a POST rejection", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(identityCandidatesReadyResponse(draft, []));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockRejectedValue(new TypeError("Failed to fetch"));
    vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(
      commitResponse(draft, {
        result_label: "publication_commit_not_found",
        commit_admitted: false,
        commit: null,
        message: "publication commit not found",
      }),
    );

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    await user.click(await screen.findByTestId("prepare-candidates"));
    await user.click(await screen.findByTestId("decide-create"));
    await user.click(await screen.findByTestId("prepare-proposal"));
    await user.click(await screen.findByTestId("confirm"));
    await screen.findByTestId("reread-commit");
    await user.click(screen.getByTestId("reread-commit"));

    await waitFor(() => {
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID,
        resolution_id: RESOLUTION_ID,
        proposal_id: PROPOSAL_ID,
        commit_id: null,
        stage: "proposal",
      });
    });
    expect(screen.getByTestId("confirm")).toBeInTheDocument();
    expect(screen.getByText(/publication commit not found/i)).toBeInTheDocument();
    expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);
  });

  it("returns to a fresh Publish path only after an exact publication_cancelled result", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const storage = createMemoryStorage();
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.cancelThreatPublicationOperation)
      .mockResolvedValueOnce({
        schema: "dmb_threat_publication_operation_response_v1",
        draft_id: draft.draft_id,
        result_label: "publication_not_found",
        operation: null,
        message: "Publication operation was not found.",
      })
      .mockResolvedValueOnce({
        schema: "dmb_threat_publication_operation_response_v1",
        draft_id: draft.draft_id,
        result_label: "publication_cancelled",
        operation: buildOperation(draft, { state: "cancelled" }),
        message: "Cancelled by operator.",
      });

    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));
    expect(await screen.findByTestId("cancel-operation")).toBeInTheDocument();

    await user.click(screen.getByTestId("cancel-operation"));

    await waitFor(() => {
      expect(screen.getByTestId("operation-status")).toHaveAttribute(
        "data-operation-result",
        "publication_not_found",
      );
    });
    expect(screen.queryByTestId("publish")).not.toBeInTheDocument();
    expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
      operation_id: OPERATION_ID,
    });

    await user.click(screen.getByTestId("cancel-operation"));

    await waitFor(() => {
      expect(screen.getByTestId("publish")).toBeInTheDocument();
    });
    expect(readThreatPublicationSession(draft.draft_id, storage)).toBeNull();
    expect(screen.getByText(/Cancelled by operator|Publication cancelled/)).toBeInTheDocument();
    expect(screen.queryByTestId("publication-active")).not.toBeInTheDocument();
  });

  it("projects Publish into onDockModelChange and hides the in-panel Publish CTA", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const onDockModelChange = vi.fn();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      expect(onDockModelChange).toHaveBeenCalled();
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    expect(screen.queryByTestId("publish")).not.toBeInTheDocument();
    expect(screen.getByText(/Use Publish Threat in the floating bar/i)).toBeInTheDocument();
  });

  it("auto-prepares identity candidates when dock-driven and begin returns publication_ready", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:auto", label: "Auto" });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [candidate]),
    );
    const onDockModelChange = vi.fn();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publishAction = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publishAction!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledWith(draft.draft_id, OPERATION_ID);
      expect(screen.getByTestId("identity-candidates")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("prepare-candidates")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refresh-operation")).not.toBeInTheDocument();
    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.status).toMatch(/identity candidate/i);
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "cancel-operation")).toBe(
        true,
      );
    });
  });

  it("auto-prepares the proposal after create_new when dock-driven", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:auto-create", label: "Auto Create", exact_name_collision: false });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [candidate]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    const onDockModelChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publishAction = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publishAction!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });
    await screen.findByTestId("identity-candidates");
    await user.click(screen.getByTestId("decide-create"));

    await waitFor(() => {
      expect(api.prepareThreatPublicationProposal).toHaveBeenCalled();
      expect(screen.getByTestId("proposal-review")).toBeInTheDocument();
    });
    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "confirm")).toBe(
        true,
      );
      expect(latest?.status).toMatch(/confirm to publish/i);
    });
  });

  it("offers dock candidate refresh after an unavailable candidate prepare", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:refresh", label: "Refresh me" });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates)
      .mockResolvedValueOnce({
        ...identityCandidatesReadyResponse(draft, []),
        result_label: "publication_identity_graph_unavailable",
        candidate_set: null,
        message: "Identity graph is unavailable.",
      })
      .mockResolvedValueOnce(identityCandidatesReadyResponse(draft, [candidate]));
    const onDockModelChange = vi.fn();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publish = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publish!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledTimes(1);
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates")).toBe(
        true,
      );
    });
    const refresh = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates"));
    await act(async () => {
      refresh!.actions.find((action: { testId: string }) => action.testId === "refresh-candidates")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId("identity-candidates")).toBeInTheDocument();
    });
  });

  it("offers dock candidate refresh after a candidate transport failure", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:transport-refresh", label: "Transport refresh" });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates)
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(identityCandidatesReadyResponse(draft, [candidate]));
    const onDockModelChange = vi.fn();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(true);
    });
    const publish = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publish!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledTimes(1);
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.status).toMatch(/failed to fetch/i);
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates")).toBe(
        true,
      );
    });
    const refresh = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates"));
    await act(async () => {
      refresh!.actions.find((action: { testId: string }) => action.testId === "refresh-candidates")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId("identity-candidates")).toHaveTextContent("Transport refresh");
    });
  });

  it("offers dock candidate refresh after the server changes the frozen candidate set", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const firstCandidate = buildCandidate({
      node_id: "threat:changed-first",
      label: "Changed first",
      exact_name_collision: false,
    });
    const replacementCandidate = buildCandidate({
      node_id: "threat:changed-second",
      label: "Changed second",
      exact_name_collision: false,
    });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates)
      .mockResolvedValueOnce(identityCandidatesReadyResponse(draft, [firstCandidate]))
      .mockResolvedValueOnce(identityCandidatesReadyResponse(draft, [replacementCandidate]));
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue({
      ...identityDecisionResponse(draft, "publication_identity_candidate_set_changed"),
      candidate_set: null,
      resolution: null,
      message: "Candidate set changed upstream.",
    });
    const onDockModelChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publish = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publish!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });
    await screen.findByTestId("identity-candidates");
    await user.click(screen.getByTestId("decide-create"));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/candidate set changed/i);
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates")).toBe(
        true,
      );
    });
    const refresh = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "refresh-candidates"));
    await act(async () => {
      refresh!.actions.find((action: { testId: string }) => action.testId === "refresh-candidates")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatIdentityCandidates).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId("identity-candidates")).toHaveTextContent("Changed second");
    });
  });

  it("offers dock proposal retry after a typed proposal rejection", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:proposal-retry", exact_name_collision: false });
    const retryProposalId = "proposal-retry";
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [candidate]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal)
      .mockResolvedValueOnce({
        ...proposalResponse(draft),
        result_label: "publication_proposal_parent_mismatch",
        proposal: null,
        message: "The graph parent changed.",
      })
      .mockResolvedValueOnce(
        proposalResponse(draft, {
          proposal: proposalRecord(draft, { proposal_id: retryProposalId }),
        }),
      );
    const onDockModelChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, retryProposalId])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publish = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publish!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });
    await screen.findByTestId("identity-candidates");
    await user.click(screen.getByTestId("decide-create"));

    await waitFor(() => {
      expect(api.prepareThreatPublicationProposal).toHaveBeenCalledTimes(1);
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "retry-proposal")).toBe(
        true,
      );
    });
    const retry = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "retry-proposal"));
    await act(async () => {
      retry!.actions.find((action: { testId: string }) => action.testId === "retry-proposal")!.onClick();
    });

    await waitFor(() => {
      expect(api.prepareThreatPublicationProposal).toHaveBeenCalledTimes(2);
      expect(screen.getByTestId("proposal-review")).toBeInTheDocument();
    });
  });

  it("preserves the exact commit pointer after a lost dock confirm response", async () => {
    const api = buildApiMocks();
    const draft = buildDraft();
    const candidate = buildCandidate({ node_id: "threat:lost-dock", exact_name_collision: false });
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [candidate]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_created_new", { decision: "create_new" }),
    );
    vi.mocked(api.prepareThreatPublicationProposal).mockResolvedValue(proposalResponse(draft));
    vi.mocked(api.confirmThreatPublicationCommit).mockRejectedValue(new TypeError("Failed to fetch"));
    const storage = createMemoryStorage();
    const onDockModelChange = vi.fn();
    const user = userEvent.setup();
    render(
      <ThreatPublicationPanel
        draft={draft}
        expectedParentRevisionId={PARENT_REVISION}
        api={api}
        storage={storage}
        generateId={sequentialIdGenerator([OPERATION_ID, RESOLUTION_ID, PROPOSAL_ID, COMMIT_ID])}
        onDockModelChange={onDockModelChange}
      />,
    );

    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "publish")).toBe(
        true,
      );
    });
    const publish = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "publish"));
    await act(async () => {
      publish!.actions.find((action: { testId: string }) => action.testId === "publish")!.onClick();
    });
    await screen.findByTestId("identity-candidates");
    await user.click(screen.getByTestId("decide-create"));
    await waitFor(() => {
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "confirm")).toBe(
        true,
      );
    });
    const confirm = onDockModelChange.mock.calls
      .map((call) => call[0])
      .reverse()
      .find((model) => model?.actions.some((action: { testId: string }) => action.testId === "confirm"));
    await act(async () => {
      confirm!.actions.find((action: { testId: string }) => action.testId === "confirm")!.onClick();
    });

    await waitFor(() => {
      expect(api.confirmThreatPublicationCommit).toHaveBeenCalledTimes(1);
      expect(readThreatPublicationSession(draft.draft_id, storage)).toMatchObject({
        operation_id: OPERATION_ID,
        proposal_id: PROPOSAL_ID,
        commit_id: COMMIT_ID,
        stage: "commit",
      });
      const latest = onDockModelChange.mock.calls.at(-1)?.[0];
      expect(latest?.actions.some((action: { testId: string }) => action.testId === "reread-commit")).toBe(
        true,
      );
    });
  });
});
