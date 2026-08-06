import { afterEach, describe, expect, it, vi } from "vitest";

import {
  SESSION_SCHEMA,
  clearThreatPublicationSession,
  parseThreatPublicationSession,
  readThreatPublicationSession,
  threatPublicationSessionKey,
  writeThreatPublicationSession,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";

const DRAFT_ID = "00000000-0000-4000-8000-000000000001";

const POINTER_FIELD_NAMES = [
  "schema",
  "draft_id",
  "draft_version",
  "operation_id",
  "resolution_id",
  "proposal_id",
  "commit_id",
  "stage",
  "updated_at",
] as const;

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

function baseSession(
  overrides: Partial<ThreatPublicationWorkbenchSessionV1> = {},
): ThreatPublicationWorkbenchSessionV1 {
  return {
    schema: SESSION_SCHEMA,
    draft_id: DRAFT_ID,
    draft_version: 2,
    operation_id: "op-001",
    resolution_id: null,
    proposal_id: null,
    commit_id: null,
    stage: "operation",
    updated_at: "2026-08-04T00:00:00.000Z",
    ...overrides,
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("threatPublicationSession", () => {
  it("round-trips write → read with exact IDs and stage", () => {
    const storage = createMemoryStorage();
    const session = baseSession({
      resolution_id: "res-001",
      proposal_id: "prop-001",
      commit_id: "commit-001",
      stage: "commit",
    });

    writeThreatPublicationSession(session, storage);
    expect(readThreatPublicationSession(DRAFT_ID, storage)).toEqual(session);
    expect(storage.getItem(threatPublicationSessionKey(DRAFT_ID))).toBe(JSON.stringify(session));
  });

  it("returns null for corrupt JSON", () => {
    const storage = createMemoryStorage();
    storage.setItem(threatPublicationSessionKey(DRAFT_ID), "{not-json");

    expect(readThreatPublicationSession(DRAFT_ID, storage)).toBeNull();
    expect(parseThreatPublicationSession("{not-json")).toBeNull();
  });

  it("returns null for wrong schema", () => {
    const payload = {
      ...baseSession(),
      schema: "dmb_other_schema_v1",
    };

    expect(parseThreatPublicationSession(payload)).toBeNull();
    expect(readThreatPublicationSession(DRAFT_ID, storageWith(payload))).toBeNull();
  });

  it("returns null when stored draft_id does not match requested draftId", () => {
    const storage = createMemoryStorage();
    writeThreatPublicationSession(
      baseSession({ draft_id: "00000000-0000-4000-8000-000000000099" }),
      storage,
    );

    expect(readThreatPublicationSession(DRAFT_ID, storage)).toBeNull();
  });

  it("returns null when a required field is missing", () => {
    const { operation_id: _removed, ...withoutOperationId } = baseSession();
    expect(parseThreatPublicationSession(withoutOperationId)).toBeNull();

    const storage = createMemoryStorage();
    storage.setItem(
      threatPublicationSessionKey(DRAFT_ID),
      JSON.stringify(withoutOperationId),
    );
    expect(readThreatPublicationSession(DRAFT_ID, storage)).toBeNull();
  });

  it("clear removes the stored record", () => {
    const storage = createMemoryStorage();
    writeThreatPublicationSession(baseSession(), storage);
    expect(storage.getItem(threatPublicationSessionKey(DRAFT_ID))).not.toBeNull();

    clearThreatPublicationSession(DRAFT_ID, storage);
    expect(storage.getItem(threatPublicationSessionKey(DRAFT_ID))).toBeNull();
    expect(readThreatPublicationSession(DRAFT_ID, storage)).toBeNull();
  });

  it("overwrites stage forward for the same draft", () => {
    const storage = createMemoryStorage();
    writeThreatPublicationSession(baseSession({ stage: "operation" }), storage);
    writeThreatPublicationSession(
      baseSession({
        stage: "identity",
        resolution_id: "res-001",
        updated_at: "2026-08-04T01:00:00.000Z",
      }),
      storage,
    );
    writeThreatPublicationSession(
      baseSession({
        stage: "proposal",
        resolution_id: "res-001",
        proposal_id: "prop-001",
        updated_at: "2026-08-04T02:00:00.000Z",
      }),
      storage,
    );
    writeThreatPublicationSession(
      baseSession({
        stage: "commit",
        resolution_id: "res-001",
        proposal_id: "prop-001",
        commit_id: "commit-001",
        updated_at: "2026-08-04T03:00:00.000Z",
      }),
      storage,
    );

    expect(readThreatPublicationSession(DRAFT_ID, storage)).toEqual(
      baseSession({
        stage: "commit",
        resolution_id: "res-001",
        proposal_id: "prop-001",
        commit_id: "commit-001",
        updated_at: "2026-08-04T03:00:00.000Z",
      }),
    );
  });

  it("persists pointer-only JSON without heavy publication payloads", () => {
    const storage = createMemoryStorage();
    const polluted = {
      ...baseSession({
        resolution_id: "res-001",
        proposal_id: "prop-001",
      }),
      candidate_set: [{ candidate_id: "cand-001", body: { hp: 30 } }],
      sealed_proposal: { graph: { nodes: [] } },
      definition: { name: "Threat" },
      digests: { mechanics: "abc123" },
      result_label: "verified_success",
      graph: { nodes: [{ id: "n1" }], edges: [] },
    } as ThreatPublicationWorkbenchSessionV1;

    writeThreatPublicationSession(polluted, storage);

    const raw = storage.getItem(threatPublicationSessionKey(DRAFT_ID));
    expect(raw).not.toBeNull();
    expect(raw).not.toContain("candidate_set");
    expect(raw).not.toContain("sealed_proposal");
    expect(raw).not.toContain("definition");
    expect(raw).not.toContain("digests");
    expect(raw).not.toContain("result_label");
    expect(raw).not.toContain("graph");

    const parsed = JSON.parse(raw!) as Record<string, unknown>;
    expect(Object.keys(parsed).sort()).toEqual([...POINTER_FIELD_NAMES].sort());
  });
});

function storageWith(payload: unknown): Storage {
  const storage = createMemoryStorage();
  storage.setItem(threatPublicationSessionKey(DRAFT_ID), JSON.stringify(payload));
  return storage;
}
