import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
import * as liveApi from "../../api/liveApi";
import * as sessionCodec from "./threatPublicationSession";
import { ThreatPublicationPanel, type ThreatPublicationApi } from "./ThreatPublicationPanel";
import {
  SESSION_SCHEMA,
  threatPublicationSessionKey,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";

const DRAFT_ID = "11111111-1111-4111-8111-111111111111";
const OPERATION_ID = "22222222-2222-4222-8222-222222222222";
const OPERATION_ID_NEW = "33333333-3333-4333-8333-333333333333";
const RESOLUTION_ID = "44444444-4444-4444-8444-444444444444";
const PROPOSAL_ID = "55555555-5555-4555-8555-555555555555";
const COMMIT_ID = "66666666-6666-4666-8666-666666666666";
const PARENT_REVISION = "77777777-7777-4777-8777-777777777777";

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

function buildApiMocks(draft = buildDraft()): ThreatPublicationApi {
  return {
    getThreatPublicationOperation: vi.fn().mockResolvedValue(operationResponse(draft)),
    getThreatIdentityResolution: vi.fn().mockResolvedValue(identityDecisionResponse(draft, "publication_identity_created_new")),
    getThreatPublicationProposal: vi.fn().mockResolvedValue(proposalResponse(draft)),
    getThreatPublicationCommit: vi.fn().mockResolvedValue(commitResponse(draft)),
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
    resolution_request_digest: "sha256:request",
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
    proposal_request_digest: "sha256:req",
    sealed_proposal_digest: `sha256:${"a".repeat(64)}`,
    sealed_proposal_version: 1,
    resolution_id: RESOLUTION_ID,
    source_digest: "sha256:source",
    resolution_request_digest: "sha256:request",
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

const MUTATIONS = [
  "beginThreatPublicationOperation", "refreshThreatPublicationOperation", "cancelThreatPublicationOperation",
  "retryThreatPublicationOperation", "prepareThreatIdentityCandidates", "createThreatIdentityResolution",
  "prepareThreatPublicationProposal", "confirmThreatPublicationCommit",
] as const;

function retained(storage: Storage, stage: ThreatPublicationWorkbenchSessionV1["stage"] = "commit", draft = buildDraft()): string {
  const pointer: ThreatPublicationWorkbenchSessionV1 = {
    schema: SESSION_SCHEMA, draft_id: draft.draft_id, draft_version: draft.version,
    operation_id: OPERATION_ID,
    resolution_id: stage === "operation" ? null : RESOLUTION_ID,
    proposal_id: stage === "proposal" || stage === "commit" ? PROPOSAL_ID : null,
    commit_id: stage === "commit" ? COMMIT_ID : null,
    stage, updated_at: "2026-08-04T00:00:00Z",
  };
  const raw = JSON.stringify({ ...pointer, retained_extension: "preserve these bytes too" }, null, 2);
  storage.setItem(threatPublicationSessionKey(draft.draft_id), raw);
  return raw;
}
function watchStorage(storage: Storage) {
  return { write: vi.spyOn(storage, "setItem"), remove: vi.spyOn(storage, "removeItem"), clear: vi.spyOn(storage, "clear") };
}
function unchanged(storage: Storage, raw: string | null, watches: ReturnType<typeof watchStorage>, draft = buildDraft()) {
  expect(storage.getItem(threatPublicationSessionKey(draft.draft_id))).toBe(raw);
  for (const fn of Object.values(watches)) expect(fn).not.toHaveBeenCalled();
  expect(sessionCodec.writeThreatPublicationSession).not.toHaveBeenCalled();
  expect(sessionCodec.clearThreatPublicationSession).not.toHaveBeenCalled();
  for (const name of MUTATIONS) expect(liveApi[name]).not.toHaveBeenCalled();
}

beforeEach(() => {
  for (const name of MUTATIONS) vi.spyOn(liveApi, name).mockImplementation(() => { throw new Error("Retired mutation dispatched"); });
  vi.spyOn(sessionCodec, "writeThreatPublicationSession");
  vi.spyOn(sessionCodec, "clearThreatPublicationSession");
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("ThreatPublicationPanel historical inspection", () => {
  it("retires fresh publication without a pointer and performs no API or storage writes", async () => {
    const storage = createMemoryStorage(), api = buildApiMocks(), watches = watchStorage(storage);
    render(<ThreatPublicationPanel draft={buildDraft({workflow_state: "drafting", accepted_mechanics_ref: null})} api={api} storage={storage} />);
    await screen.findByText("No retained publication pointer in this browser.");
    expect(screen.getByText("Classic publication is retired")).toBeTruthy();
    expect(screen.queryByTestId("publish")).toBeNull();
    expect(screen.queryByTestId("confirm")).toBeNull();
    for (const fn of Object.values(api)) expect(fn).not.toHaveBeenCalled();
    unchanged(storage, null, watches);
  });

  it.each(["operation", "identity", "proposal", "commit"] as const)("reads only exact retained %s stage pointers", async (stage) => {
    const storage = createMemoryStorage(), raw = retained(storage, stage), api = buildApiMocks(), watches = watchStorage(storage);
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByTestId("publication-history-records");
    expect(api.getThreatPublicationOperation).toHaveBeenCalledExactlyOnceWith(DRAFT_ID, OPERATION_ID);
    if (stage !== "operation") expect(api.getThreatIdentityResolution).toHaveBeenCalledExactlyOnceWith(DRAFT_ID, OPERATION_ID, RESOLUTION_ID);
    else expect(api.getThreatIdentityResolution).not.toHaveBeenCalled();
    if (stage === "proposal" || stage === "commit") expect(api.getThreatPublicationProposal).toHaveBeenCalledExactlyOnceWith(DRAFT_ID, OPERATION_ID, PROPOSAL_ID);
    else expect(api.getThreatPublicationProposal).not.toHaveBeenCalled();
    if (stage === "commit") expect(api.getThreatPublicationCommit).toHaveBeenCalledExactlyOnceWith(DRAFT_ID, OPERATION_ID, COMMIT_ID);
    else expect(api.getThreatPublicationCommit).not.toHaveBeenCalled();
    unchanged(storage, raw, watches);
  });

  it.each(["ready", "stale", "cancelled", "superseded"] as const)("keeps the exact pointer for recorded %s operations, without following successors", async (state) => {
    const storage = createMemoryStorage(), raw = retained(storage, "operation"), api = buildApiMocks(), watches = watchStorage(storage);
    vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(buildDraft(), {
      operation: buildOperation(buildDraft(), { state, superseded_by_operation_id: OPERATION_ID_NEW }),
    }));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(`Recorded operation state: ${state}`);
    expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("retry-operation")).toBeNull();
    expect(screen.queryByTestId("cancel-operation")).toBeNull();
    unchanged(storage, raw, watches);
  });

  it.each(["committing", "uncommitted", "ambiguous", "committed_unverified", "committed_verified"] as const)("shows recorded %s commit without converting history into write permission", async (state) => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks(), watches = watchStorage(storage);
    vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {
      commit: commitRecord(buildDraft(), { state }), retry_allowed: true,
    }));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(new RegExp(`Recorded commit state: ${state};`));
    expect(screen.queryByTestId("retry-confirm")).toBeNull();
    expect(screen.queryByTestId("clear-pointer")).toBeNull();
    unchanged(storage, raw, watches);
  });

  it.each(["active", "superseded"] as const)("retains %s identity and proposal records", async (state) => {
    const storage = createMemoryStorage(), raw = retained(storage, "proposal"), api = buildApiMocks(), watches = watchStorage(storage);
    vi.mocked(api.getThreatIdentityResolution).mockResolvedValue(identityDecisionResponse(buildDraft(), "publication_identity_created_new", {state}));
    vi.mocked(api.getThreatPublicationProposal).mockResolvedValue(proposalResponse(buildDraft(), {proposal: proposalRecord(buildDraft(), {state})}));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(`Recorded proposal state: ${state}`);
    unchanged(storage, raw, watches);
  });

  it.each(["missing-operation", "missing-identity", "missing-proposal", "commit-not-found", "corrupt", "outage"])("keeps uncertainty and raw storage after %s", async (failure) => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks(), watches = watchStorage(storage);
    if (failure === "missing-operation") vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(buildDraft(), {operation: null, result_label: "publication_not_found"}));
    if (failure === "missing-identity") vi.mocked(api.getThreatIdentityResolution).mockResolvedValue({...identityDecisionResponse(buildDraft(), "publication_identity_created_new"), resolution: null});
    if (failure === "missing-proposal") vi.mocked(api.getThreatPublicationProposal).mockResolvedValue(proposalResponse(buildDraft(), {proposal: null}));
    if (failure === "commit-not-found") vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {commit: null, commit_admitted: false, result_label: "publication_commit_not_found", retry_allowed: true}));
    if (failure === "corrupt") vi.mocked(api.getThreatPublicationOperation).mockRejectedValue(new Error("corrupt record"));
    if (failure === "outage") vi.mocked(api.getThreatPublicationCommit).mockRejectedValue(new Error("storage offline"));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(/original session remains unchanged and unresolved/i);
    expect(screen.queryByTestId("publication-history-records")).toBeNull();
    unchanged(storage, raw, watches);
  });

  it.each(["outer-draft", "operation", "snapshot", "identity", "proposal", "commit", "world", "link", "missing-revision"])("refuses %s response substitution before displaying recorded facts", async (change) => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks(), watches = watchStorage(storage);
    if (change === "outer-draft") vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(buildDraft(), {draft_id: "foreign"}));
    if (change === "operation") vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(buildDraft(), {operation: buildOperation(buildDraft(), {operation_id: OPERATION_ID_NEW})}));
    if (change === "snapshot") vi.mocked(api.getThreatPublicationOperation).mockResolvedValue(operationResponse(buildDraft(), {operation: buildOperation(buildDraft(), {source_snapshot: sourceSnapshot(buildDraft({draft_id: "foreign"}))})}));
    if (change === "identity") vi.mocked(api.getThreatIdentityResolution).mockResolvedValue(identityDecisionResponse(buildDraft(), "publication_identity_created_new", {resolution_id: "foreign"}));
    if (change === "proposal") vi.mocked(api.getThreatPublicationProposal).mockResolvedValue(proposalResponse(buildDraft(), {proposal: proposalRecord(buildDraft(), {proposal_id: "foreign"})}));
    if (change === "commit") vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {commit: commitRecord(buildDraft(), {commit_id: "foreign"})}));
    if (change === "world") vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {commit: commitRecord(buildDraft(), {world_id: "foreign"})}));
    if (change === "link") vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {commit: commitRecord(buildDraft(), {proposal_request_digest: "foreign"})}));
    if (change === "missing-revision") vi.mocked(api.getThreatPublicationCommit).mockResolvedValue(commitResponse(buildDraft(), {commit: commitRecord(buildDraft(), {committed_revision_id: null})}));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(/original session remains unchanged and unresolved/i);
    expect(screen.queryByTestId("publication-history-records")).toBeNull();
    unchanged(storage, raw, watches);
  });

  it.each(["{broken", "{}", "null"])("preserves corrupt raw session bytes %s", async (raw) => {
    const storage = createMemoryStorage(); storage.setItem(threatPublicationSessionKey(DRAFT_ID), raw);
    const watches = watchStorage(storage), api = buildApiMocks();
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(/original session remains unchanged and unresolved/i);
    expect(api.getThreatPublicationOperation).not.toHaveBeenCalled();
    unchanged(storage, raw, watches);
  });

  it("fails closed when browser storage cannot be read", async () => {
    const storage = createMemoryStorage(), api = buildApiMocks();
    vi.spyOn(storage, "getItem").mockImplementation(() => {throw new Error("blocked storage");});
    const watches = watchStorage(storage);
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByText(/original session remains unchanged and unresolved/i);
    for (const fn of Object.values(watches)) expect(fn).not.toHaveBeenCalled();
    for (const fn of Object.values(api)) expect(fn).not.toHaveBeenCalled();
  });

  it("inspects the original pointer after draft/mechanics changes and remount without re-anchoring", async () => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks(), watches = watchStorage(storage);
    const changed = buildDraft({version: 9, workflow_state: "drafting", accepted_mechanics_ref: null});
    const first = render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByTestId("publication-history-records");
    first.rerender(<ThreatPublicationPanel draft={changed} api={api} storage={storage} />);
    expect(screen.getByTestId("publication-history-records")).toBeTruthy();
    expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/Retained draft version: 3/)).toBeTruthy();
    expect(screen.getByText(/Recorded mechanics: sb-1/)).toBeTruthy();
    first.unmount();
    render(<ThreatPublicationPanel draft={changed} api={api} storage={storage} />);
    await screen.findByTestId("publication-history-records");
    expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(2);
    unchanged(storage, raw, watches);
  });

  it("rereads only the same GET chain and never retries publication", async () => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks(), watches = watchStorage(storage);
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await screen.findByTestId("publication-history-records");
    await userEvent.setup().click(screen.getByRole("button", {name: "Re-read history"}));
    await waitFor(() => expect(api.getThreatPublicationCommit).toHaveBeenCalledTimes(2));
    expect(api.getThreatPublicationCommit).toHaveBeenNthCalledWith(2, DRAFT_ID, OPERATION_ID, COMMIT_ID);
    unchanged(storage, raw, watches);
  });

  it("masks the previous scope immediately and ignores its delayed response", async () => {
    const storage = createMemoryStorage(), rawA = retained(storage, "operation");
    const other = buildDraft({draft_id: OPERATION_ID_NEW, world_id: "other-world", campaign_id: "other-campaign", name: "Other draft"});
    const rawB = retained(storage, "operation", other), api = buildApiMocks(), watches = watchStorage(storage);
    let finish!: (value: ThreatPublicationOperationResponseV1) => void;
    vi.mocked(api.getThreatPublicationOperation).mockReturnValueOnce(new Promise(resolve => {finish = resolve;})).mockResolvedValueOnce(operationResponse(other));
    const mounted = render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await waitFor(() => expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(1));
    mounted.rerender(<ThreatPublicationPanel draft={other} api={api} storage={storage} />);
    expect(screen.queryByTestId("publication-history-records")).toBeNull();
    await screen.findByTestId("publication-history-records");
    await act(async () => {finish(operationResponse(buildDraft(), {operation: buildOperation(buildDraft(), {state: "cancelled"})}));});
    expect(screen.queryByText("Recorded operation state: cancelled")).toBeNull();
    unchanged(storage, rawA, watches);
    expect(storage.getItem(threatPublicationSessionKey(other.draft_id))).toBe(rawB);
  });

  it("discards a delayed reply after the stored pointer changes", async () => {
    const storage = createMemoryStorage(), raw = retained(storage), api = buildApiMocks();
    let finish!: (value: ThreatPublicationOperationResponseV1) => void;
    vi.mocked(api.getThreatPublicationOperation).mockReturnValueOnce(new Promise(resolve => {finish = resolve;}));
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} />);
    await waitFor(() => expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(1));
    const newer = raw.replace('"updated_at": "2026-08-04T00:00:00Z"', '"updated_at": "2026-08-05T00:00:00Z"');
    storage.setItem(threatPublicationSessionKey(DRAFT_ID), newer);
    const watches = watchStorage(storage);
    await act(async () => {finish(operationResponse(buildDraft()));});
    await screen.findByText(/original session remains unchanged and unresolved/i);
    expect(api.getThreatIdentityResolution).not.toHaveBeenCalled();
    unchanged(storage, newer, watches);
  });

  it("does not continue the GET chain or publish dock facts after unmount", async () => {
    const storage = createMemoryStorage(); retained(storage);
    const api = buildApiMocks(), dock = vi.fn();
    let finish!: (value: ThreatPublicationOperationResponseV1) => void;
    vi.mocked(api.getThreatPublicationOperation).mockReturnValueOnce(new Promise(resolve => {finish = resolve;}));
    const mounted = render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} onDockModelChange={dock}/>);
    await waitFor(() => expect(api.getThreatPublicationOperation).toHaveBeenCalledTimes(1));
    mounted.unmount(); dock.mockClear();
    await act(async () => {finish(operationResponse(buildDraft()));});
    expect(api.getThreatIdentityResolution).not.toHaveBeenCalled(); expect(dock).not.toHaveBeenCalled();
  });

  it("retains the dock model shape with only a read-only action", async () => {
    const storage = createMemoryStorage(), raw = retained(storage, "operation"), api = buildApiMocks(), watches = watchStorage(storage), dock = vi.fn();
    render(<ThreatPublicationPanel draft={buildDraft()} api={api} storage={storage} onDockModelChange={dock}/>);
    await screen.findByTestId("publication-history-records");
    const model = dock.mock.calls.at(-1)![0];
    expect(model.actions.map((item: {label: string}) => item.label)).toEqual(["Re-read history"]);
    expect(screen.queryByRole("button", {name: "Re-read history"})).toBeNull();
    unchanged(storage, raw, watches);
  });
});
