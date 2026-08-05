import { act, render, screen, waitFor } from "@testing-library/react";
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
import { ThreatPublicationPanel, type ThreatPublicationApi } from "./ThreatPublicationPanel";
import {
  SESSION_SCHEMA,
  readThreatPublicationSession,
  writeThreatPublicationSession,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";

const DRAFT_ID = "draft-1";
const OPERATION_ID = "op-1";
const RESOLUTION_ID = "res-1";
const PROPOSAL_ID = "prop-1";
const COMMIT_ID = "commit-1";
const PARENT_REVISION = "rev-head-1";

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
        storage={createMemoryStorage()}
        generateId={sequentialIdGenerator([OPERATION_ID])}
      />,
    );

    await user.click(screen.getByTestId("publish"));

    expect(await screen.findByRole("status")).toHaveTextContent(
      /another publication is active and cannot be safely recovered/i,
    );
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
    vi.mocked(api.beginThreatPublicationOperation).mockResolvedValue(operationResponse(draft));
    vi.mocked(api.prepareThreatIdentityCandidates).mockResolvedValue(
      identityCandidatesReadyResponse(draft, [buildCandidate()]),
    );
    vi.mocked(api.createThreatIdentityResolution).mockResolvedValue(
      identityDecisionResponse(draft, "publication_identity_refused", { decision: "refuse" }),
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
    await user.click(await screen.findByTestId("decide-refuse"));

    expect(await screen.findByText(/no graph write occurred/i)).toBeInTheDocument();
    expect(api.prepareThreatPublicationProposal).not.toHaveBeenCalled();
    expect(api.confirmThreatPublicationCommit).not.toHaveBeenCalled();
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
});
