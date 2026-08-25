import { describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../api/liveApi";
import type {
  PlayRunRecord,
  PlayRunReferenceManifest,
  WorkspaceCommittedRevision,
} from "../api/types";
import {
  bindStartRunAttempt,
  confirmCreatedRun,
  executeStartRunAttempt,
  sameIntendedManifestBinding,
  sameIntendedRunBinding,
  type StartRunBinding,
  type StartRunDeps,
} from "./startRunAttempt";

const RUN_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const OTHER_RUN_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const DOCUMENT_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const SHA_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";

function committed(overrides: Partial<WorkspaceCommittedRevision> = {}): WorkspaceCommittedRevision {
  return {
    schema_version: "dmb_workspace_committed_revision_v1",
    document_id: DOCUMENT_ID,
    kind: "runbook",
    campaign_id: "longmont-c2",
    title: "North Gate Runbook",
    status: "active",
    object_revision: 7,
    work_revision_id: "11111111-1111-4111-8111-111111111111",
    revision_n: 7,
    markdown: "# Gate\n",
    content_sha256: SHA_A,
    has_divergent_working_copy: false,
    target_relpath: "out/workspace/runbooks/north-gate.md",
    ...overrides,
  };
}

function binding(overrides: Partial<StartRunBinding> = {}): StartRunBinding {
  return {
    runId: RUN_ID,
    playableArtifactId: DOCUMENT_ID,
    expectedPlayableRevision: 7,
    expectedPlayableContentSha256: SHA_A,
    ...overrides,
  };
}

function runRecord(overrides: Partial<PlayRunRecord> = {}): PlayRunRecord {
  return {
    schema_version: "dmb_play_run_record_v1",
    run_id: RUN_ID,
    campaign_id: "longmont-c2",
    playable_artifact_id: DOCUMENT_ID,
    playable_revision: 7,
    playable_content_sha256: SHA_A,
    run_revision: 1,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    progress: {
      current_scene_id: null,
      current_beat_id: null,
      resolved_beat_ids: [],
      selections: {},
      notes_by_element_id: {},
    },
    ...overrides,
  };
}

function manifest(overrides: Partial<PlayRunReferenceManifest> = {}): PlayRunReferenceManifest {
  const run = runRecord();
  return {
    schema_version: "dmb_play_run_reference_manifest_v1",
    run_id: run.run_id,
    playable_artifact_id: run.playable_artifact_id,
    playable_revision: run.playable_revision,
    playable_content_sha256: run.playable_content_sha256,
    elements: [{ kind: "scene", element_id: "scene:gate" }],
    sealed_at: "2026-08-17T00:00:00Z",
    ...overrides,
  };
}

function deps(overrides: Partial<StartRunDeps> = {}): StartRunDeps & {
  generateRunId: ReturnType<typeof vi.fn>;
  getCommittedRevision: ReturnType<typeof vi.fn>;
  putRun: ReturnType<typeof vi.fn>;
  getRun: ReturnType<typeof vi.fn>;
  putManifest: ReturnType<typeof vi.fn>;
  getManifest: ReturnType<typeof vi.fn>;
} {
  return {
    generateRunId: vi.fn(() => RUN_ID),
    getCommittedRevision: vi.fn(async () => committed()),
    putRun: vi.fn(async () => runRecord()),
    getRun: vi.fn(async () => runRecord()),
    putManifest: vi.fn(async () => manifest()),
    getManifest: vi.fn(async () => manifest()),
    ...overrides,
  };
}

describe("startRunAttempt preflight", () => {
  it("binds the exact committed revision_n and SHA", () => {
    const bound = bindStartRunAttempt(RUN_ID, DOCUMENT_ID, committed());
    expect(bound).toEqual({ ok: true, binding: binding() });
  });

  it("binds revision_n even when object_revision has advanced", () => {
    const bound = bindStartRunAttempt(RUN_ID, DOCUMENT_ID, committed({ object_revision: 18 }));
    expect(bound).toEqual({ ok: true, binding: binding() });
  });

  it("refuses discarded and divergent WorkingCopy revisions", () => {
    expect(bindStartRunAttempt(RUN_ID, DOCUMENT_ID, committed({ status: "discarded" })).ok).toBe(false);
    expect(bindStartRunAttempt(RUN_ID, DOCUMENT_ID, committed({ has_divergent_working_copy: true })).ok).toBe(false);
  });

  it("does not treat a missing target file as Playable authority", () => {
    const bound = bindStartRunAttempt(RUN_ID, DOCUMENT_ID, committed({ target_relpath: null }));
    expect(bound).toEqual({ ok: true, binding: binding() });
  });
});

describe("startRunAttempt binding equality", () => {
  it("adopts an exact create replay and rejects a different binding", () => {
    expect(sameIntendedRunBinding(runRecord(), binding())).toBe(true);
    expect(confirmCreatedRun(runRecord({ playable_revision: 8, playable_content_sha256: SHA_B }), binding()).status).toBe("block");
    expect(sameIntendedManifestBinding(manifest(), runRecord())).toBe(true);
    expect(sameIntendedManifestBinding(manifest({ playable_revision: 8 }), runRecord())).toBe(false);
  });
});

describe("executeStartRunAttempt", () => {
  it("sends the exact snapshot revision and SHA to P2A then seals without a second UUID", async () => {
    const api = deps();
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("ready");
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
    expect(api.putRun).toHaveBeenCalledWith(RUN_ID, {
      playable_artifact_id: DOCUMENT_ID,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
    expect(api.putManifest).toHaveBeenCalledWith(RUN_ID);
    expect(api.putManifest.mock.calls[0]?.[1]).toBeUndefined();
  });

  it("blocks snapshot drift 409 without sealing or minting another UUID", async () => {
    const api = deps({
      putRun: vi.fn(async () => {
        throw new LiveApiError("expected Playable revision/digest no longer matches", 409);
      }),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("blocked");
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
    expect(api.putManifest).not.toHaveBeenCalled();
    expect(api.getCommittedRevision).toHaveBeenCalledTimes(1);
  });

  it("reconciles a lost create response by adopting the exact existing UUID", async () => {
    const api = deps({
      putRun: vi.fn(async () => {
        throw new Error("network");
      }),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("ready");
    if (result.outcome === "ready") expect(result.binding.runId).toBe(RUN_ID);
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
    expect(api.getRun).toHaveBeenCalledWith(RUN_ID);
    expect(api.putManifest).toHaveBeenCalledWith(RUN_ID);
  });

  it("keeps the same UUID when a lost create GET is 404", async () => {
    const api = deps({
      putRun: vi.fn(async () => {
        throw new Error("network");
      }),
      getRun: vi.fn(async () => {
        throw new LiveApiError("not found", 404);
      }),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result).toMatchObject({ outcome: "replay_create", binding: { runId: RUN_ID } });
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
    expect(api.putManifest).not.toHaveBeenCalled();

    api.putRun.mockResolvedValue(runRecord());
    const replayed = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: result.outcome === "replay_create" ? result.binding : null,
      phase: "replay_create",
      deps: api,
    });
    expect(replayed.outcome).toBe("ready");
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
    expect(api.putRun).toHaveBeenLastCalledWith(RUN_ID, {
      playable_artifact_id: DOCUMENT_ID,
      expected_playable_revision: 7,
      expected_playable_content_sha256: SHA_A,
    });
  });

  it("fails closed when the reconciled Run has a different binding", async () => {
    const api = deps({
      putRun: vi.fn(async () => runRecord({ playable_revision: 8, playable_content_sha256: SHA_B })),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("blocked");
    expect(api.putManifest).not.toHaveBeenCalled();
  });

  it("reports Run created / setup incomplete when seal 409s after create", async () => {
    const api = deps({
      putManifest: vi.fn(async () => {
        throw new LiveApiError("workspace advanced", 409);
      }),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("incomplete");
    if (result.outcome === "incomplete") {
      expect(result.binding.runId).toBe(RUN_ID);
      expect(result.detail).toContain(RUN_ID);
    }
  });

  it("navigates after a lost seal response when GET proves the exact manifest", async () => {
    const api = deps({
      putManifest: vi.fn(async () => {
        throw new Error("network");
      }),
    });
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: null,
      phase: "fresh",
      deps: api,
    });
    expect(result.outcome).toBe("ready");
    expect(api.getManifest).toHaveBeenCalledWith(RUN_ID);
    expect(api.generateRunId).toHaveBeenCalledTimes(1);
  });

  it("retries seal on the same Run UUID without allocating another", async () => {
    const api = deps();
    const result = await executeStartRunAttempt({
      selectedDocumentId: DOCUMENT_ID,
      attempt: binding(),
      phase: "retry_seal",
      deps: api,
    });
    expect(result.outcome).toBe("ready");
    expect(api.generateRunId).not.toHaveBeenCalled();
    expect(api.putRun).not.toHaveBeenCalled();
    expect(api.putManifest).toHaveBeenCalledWith(RUN_ID);
  });

  it("never silently reuses a prior UUID for a different Runbook", async () => {
    const api = deps();
    const result = await executeStartRunAttempt({
      selectedDocumentId: OTHER_RUN_ID,
      attempt: binding(),
      phase: "replay_create",
      deps: api,
    });
    expect(result.outcome).toBe("blocked");
    expect(api.putRun).not.toHaveBeenCalled();
  });
});
