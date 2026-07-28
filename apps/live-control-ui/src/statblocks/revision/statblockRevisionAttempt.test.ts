import { afterEach, describe, expect, it, vi } from "vitest";

import type { ThreatDraftV1 } from "../../api/types";
import type {
  GeneratedStatblockCandidateV1,
  StatblockDefinitionV1_Input,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { createEditorStateFromOutput } from "../editor/statblockEditorState";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import {
  buildReviseRequestFromWorkingCopy,
  candidateWorkingCopyStorageKey,
  classifyReviseResult,
  isReviseAttemptCompleted,
  markReviseAwaitingLocalRefresh,
  markReviseAttemptCompleted,
  normalizeRevisionInstructionsFromTextarea,
  proveReconciledRefOnDraft,
  readCandidateWorkingCopy,
  readStoredReviseAttempt,
  revisePanelActions,
  unicodeCodePointLength,
  validateStoredReviseAttempt,
  writeCandidateWorkingCopy,
  writeStoredReviseAttempt,
} from "./statblockRevisionAttempt";

const candidate = fixture as GeneratedStatblockCandidateV1;

function minimalDraft(overrides: Partial<ThreatDraftV1> = {}): ThreatDraftV1 {
  return {
    schema: "dmb_threat_draft_v1",
    draft_id: "00000000-0000-4000-8000-000000000001",
    version: 2,
    world_id: "world",
    campaign_id: "campaign",
    focus: null,
    name: "Threat",
    description: "Desc",
    threat_kind: "creature",
    intended_roles: ["brute"],
    tags: [],
    generation_intent: {
      ruleset: { system: "dnd5e", edition: "2024", house_ruleset_id: null },
      target_cr: "3",
      complexity: null,
      must_include: [],
      must_avoid: [],
    },
    encounter_context: { party_level: 5, party_size: 4, terrain_notes: [] },
    graph_context_snapshot: {
      graph_revision_id: "rev:abc",
      selected_node_ids: [],
      admitted_source_anchor_ids: [],
    },
    candidate_refs: [],
    accepted_mechanics_ref: null,
    workflow_state: "candidate_ready",
    created_by: "gm",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  sessionStorage.clear();
});

describe("statblockRevisionAttempt", () => {
  it("normalizes instructions: trim, drop empty, preserve internal whitespace", () => {
    const result = normalizeRevisionInstructionsFromTextarea("  Increase AC \n\n  Add  reaction  ");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.instructions).toEqual(["Increase AC", "Add  reaction"]);
    }
  });

  it("keeps commas inside one instruction line", () => {
    const result = normalizeRevisionInstructionsFromTextarea("Buff HP, add resistances");
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.instructions).toEqual(["Buff HP, add resistances"]);
  });

  it("rejects more than 16 instructions", () => {
    const lines = Array.from({ length: 17 }, (_, i) => `line ${i}`);
    const result = normalizeRevisionInstructionsFromTextarea(lines.join("\n"));
    expect(result.ok).toBe(false);
  });

  it("rejects long single instruction", () => {
    const result = normalizeRevisionInstructionsFromTextarea("x".repeat(501));
    expect(result.ok).toBe(false);
  });

  it("counts emoji as one code point toward per-line limit", () => {
    const emoji = "😀";
    expect(unicodeCodePointLength(emoji)).toBe(1);
    expect(emoji.length).toBe(2);
    const within = normalizeRevisionInstructionsFromTextarea(`${"😀".repeat(500)}`);
    expect(within.ok).toBe(true);
    const over = normalizeRevisionInstructionsFromTextarea(`${"😀".repeat(501)}`);
    expect(over.ok).toBe(false);
  });

  it("rejects total payload over 4000 code points", () => {
    const result = normalizeRevisionInstructionsFromTextarea(`${"a".repeat(4001)}`);
    expect(result.ok).toBe(false);
  });

  it("isReviseAttemptCompleted is false while awaiting local refresh", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-await",
      draft,
      editorState,
      revisionInstructions: ["Buff"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const base = {
      schema: "dmb_sbw06_revise_attempt_v1" as const,
      draft_id: draft.draft_id,
      source_candidate_id: "cand_a",
      request_id: built.request.request_id,
      raw_instructions: "Buff",
      request: built.request,
      last_result: "reconciled" as const,
      candidate_id: "cand_new",
      created_at: new Date().toISOString(),
    };
    const awaiting = markReviseAwaitingLocalRefresh(base, "cand_new");
    expect(isReviseAttemptCompleted(awaiting)).toBe(false);
    const done = markReviseAttemptCompleted(awaiting, "cand_new");
    expect(isReviseAttemptCompleted(done)).toBe(true);
  });

  it("revisePanelActions maps terminal_failure to start new without resume", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-term",
      draft,
      editorState,
      revisionInstructions: ["x"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const attempt = {
      schema: "dmb_sbw06_revise_attempt_v1" as const,
      draft_id: draft.draft_id,
      source_candidate_id: "cand_a",
      request_id: built.request.request_id,
      raw_instructions: "x",
      request: built.request,
      last_result: "terminal_failure" as const,
      candidate_id: null,
      created_at: new Date().toISOString(),
    };
    const actions = revisePanelActions(attempt);
    expect(actions.showStartNew).toBe(true);
    expect(actions.showResume).toBe(false);
    expect(actions.allowCreateNew).toBe(false);
  });

  it("revisePanelActions allows create rebuild after stale_version preclaim", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-pre",
      draft,
      editorState,
      revisionInstructions: ["x"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const attempt = {
      schema: "dmb_sbw06_revise_attempt_v1" as const,
      draft_id: draft.draft_id,
      source_candidate_id: "cand_a",
      request_id: built.request.request_id,
      raw_instructions: "x",
      request: built.request,
      last_result: null,
      candidate_id: null,
      created_at: new Date().toISOString(),
      ui_preclaim: "stale_version" as const,
    };
    const actions = revisePanelActions(attempt);
    expect(actions.showResume).toBe(false);
    expect(actions.allowCreateNew).toBe(true);
    expect(actions.freezeReplaySource).toBe(false);
  });

  it("revisePanelActions allows resume for revise_busy and revise_history_full", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-busy",
      draft,
      editorState,
      revisionInstructions: ["x"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    for (const last_result of ["revise_busy", "revise_history_full"] as const) {
      const actions = revisePanelActions({
        schema: "dmb_sbw06_revise_attempt_v1",
        draft_id: draft.draft_id,
        source_candidate_id: "cand_a",
        request_id: built.request.request_id,
        raw_instructions: "x",
        request: built.request,
        last_result,
        candidate_id: null,
        created_at: new Date().toISOString(),
      });
      expect(actions.showResume).toBe(true);
      expect(actions.showStartNew).toBe(false);
      expect(actions.allowCreateNew).toBe(false);
      expect(actions.freezeReplaySource).toBe(true);
      expect(classifyReviseResult(last_result)).toBe("resume_same");
    }
  });

  it("revisePanelActions offers retry local refresh while awaiting_local_refresh", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-refresh",
      draft,
      editorState,
      revisionInstructions: ["x"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const awaiting = markReviseAwaitingLocalRefresh(
      {
        schema: "dmb_sbw06_revise_attempt_v1",
        draft_id: draft.draft_id,
        source_candidate_id: "cand_a",
        request_id: built.request.request_id,
        raw_instructions: "x",
        request: built.request,
        last_result: null,
        candidate_id: null,
        created_at: new Date().toISOString(),
      },
      "cand_new",
    );
    const actions = revisePanelActions(awaiting);
    expect(actions.awaitingLocalRefresh).toBe(true);
    expect(actions.showRetryLocalRefresh).toBe(true);
    expect(actions.showResume).toBe(false);
  });

  it("writeStoredReviseAttempt fails closed when sessionStorage rejects", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-store-fail",
      draft,
      editorState,
      revisionInstructions: ["Buff"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const attempt = {
      schema: "dmb_sbw06_revise_attempt_v1" as const,
      draft_id: draft.draft_id,
      source_candidate_id: "cand_a",
      request_id: built.request.request_id,
      raw_instructions: "Buff",
      request: built.request,
      last_result: null,
      candidate_id: null,
      created_at: new Date().toISOString(),
    };
    const setItem = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError");
    });
    expect(writeStoredReviseAttempt(attempt)).toBe(false);
    setItem.mockRestore();
  });

  it("builds request from working copy snapshot and stateRevision", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const edited = {
      ...editorState.workingCopy,
      identity: { ...editorState.workingCopy.identity, name: "Edited Name" },
    };
    const withEdit = { ...editorState, workingCopy: edited as StatblockDefinitionV1_Input };
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-1",
      draft,
      editorState: withEdit,
      revisionInstructions: ["More AC"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(true);
    if (built.ok) {
      expect(built.request.source_definition.identity?.name).toBe("Edited Name");
      expect(built.request.editor_state_revision).toBe(String(withEdit.stateRevision));
      expect(built.request.expected_draft_version).toBe(2);
    }
  });

  it("blocks ruleset mismatch before POST", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft({
      generation_intent: {
        ruleset: { system: "pathfinder", edition: "2e", house_ruleset_id: null },
        target_cr: null,
        complexity: null,
        must_include: [],
        must_avoid: [],
      },
    });
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-1",
      draft,
      editorState,
      revisionInstructions: ["x"],
      preserveElementKeys: true,
    });
    expect(built.ok).toBe(false);
  });

  it("round-trips stored attempt without mutating request body", () => {
    const editorState = createEditorStateFromOutput(candidate.definition);
    const draft = minimalDraft();
    const built = buildReviseRequestFromWorkingCopy({
      requestId: "req-roundtrip",
      draft,
      editorState,
      revisionInstructions: ["Buff"],
      preserveElementKeys: false,
    });
    expect(built.ok).toBe(true);
    if (!built.ok) return;
    const attempt = {
      schema: "dmb_sbw06_revise_attempt_v1" as const,
      draft_id: draft.draft_id,
      source_candidate_id: "cand_a",
      request_id: built.request.request_id,
      raw_instructions: "Buff",
      request: built.request,
      last_result: null,
      candidate_id: null,
      created_at: new Date().toISOString(),
    };
    writeStoredReviseAttempt(attempt);
    const read = readStoredReviseAttempt(draft.draft_id);
    expect(read?.request).toEqual(built.request);
  });

  it("validateStoredReviseAttempt fails closed on corrupt payload", () => {
    expect(
      validateStoredReviseAttempt({ schema: "wrong", draft_id: minimalDraft().draft_id }, minimalDraft().draft_id),
    ).toBeNull();
  });

  it("candidate-scoped storage isolates working copies", () => {
    const draftId = minimalDraft().draft_id;
    writeCandidateWorkingCopy(draftId, "cand_a", { identity: { name: "A" } } as StatblockDefinitionV1_Input);
    writeCandidateWorkingCopy(draftId, "cand_b", { identity: { name: "B" } } as StatblockDefinitionV1_Input);
    expect(readCandidateWorkingCopy(draftId, "cand_a")?.identity?.name).toBe("A");
    expect(readCandidateWorkingCopy(draftId, "cand_b")?.identity?.name).toBe("B");
    expect(sessionStorage.getItem(candidateWorkingCopyStorageKey(draftId, "cand_a"))).not.toContain('"B"');
  });

  it("classifies every backend revise result label", () => {
    const labels = [
      "revise_claimed",
      "dispatched_unknown",
      "candidate_received",
      "cache_stored_ref_pending",
      "reconciled",
      "revise_busy",
      "revise_history_full",
      "revise_input_conflict",
      "revise_integrity_conflict",
      "revise_blocked",
      "revise_draft_unavailable",
      "terminal_failure",
    ] as const;
    for (const label of labels) {
      expect(classifyReviseResult(label)).toBeTruthy();
    }
  });

  it("proveReconciledRefOnDraft requires matching request and lineage", () => {
    const draft = minimalDraft({
      candidate_refs: [
        {
          candidate_id: "cand_new",
          generated_from_draft_version: 2,
          request_id: "req-1",
          created_at: "2026-01-01T00:00:00Z",
          status: "active",
          lineage: {
            schema: "dmb_candidate_lineage_v1",
            revise_request_id: "req-1",
            source_origin_kind: "edited_working_copy",
            instruction_options_digest: `sha256:${"a".repeat(64)}`,
            created_at: "2026-01-01T00:00:00Z",
            edited_working_copy: {
              draft_id: minimalDraft().draft_id,
              source_draft_version: 2,
              editor_state_revision: "3",
              source_definition_digest: `sha256:${"b".repeat(64)}`,
            },
          },
        },
      ],
    });
    expect(proveReconciledRefOnDraft(draft, "cand_new", "req-1")?.candidate_id).toBe("cand_new");
    expect(proveReconciledRefOnDraft(draft, "cand_new", "req-other")).toBeNull();
  });
});
