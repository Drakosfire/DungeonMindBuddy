import { describe, expect, it } from "vitest";
import {
  InMemoryLocalWorldRepository,
  InMemoryLocalWorldStore,
} from "./inMemoryLocalWorldRepository";
import {
  createTestWorld,
  fourNodeWorldFixture,
  sameNameWorldPeopleFixture,
  sequenceLocalIds,
} from "./localWorldContractFixtures";
import { openIndexedDbLocalWorldRepository } from "./indexedDbLocalWorldRepository";
import type {
  LocalWorldLayout,
  LocalWorldId,
} from "./localWorldRepository";

const localOnlyEdit = {
  classification: "buddy-local-only" as const,
  description: "Edited the local draft",
};

describe("IndexedDB adapter availability", () => {
  it("reports unavailable when the browser IndexedDB accessor throws", async () => {
    const previous = Object.getOwnPropertyDescriptor(globalThis, "indexedDB");
    Object.defineProperty(globalThis, "indexedDB", {
      configurable: true,
      get() {
        throw new DOMException("Storage is blocked", "SecurityError");
      },
    });

    try {
      await expect(openIndexedDbLocalWorldRepository("unused-test-db")).resolves.toMatchObject({
        status: "error",
        code: "unavailable",
      });
    } finally {
      if (previous) Object.defineProperty(globalThis, "indexedDB", previous);
      else delete (globalThis as typeof globalThis & { indexedDB?: IDBFactory }).indexedDB;
    }
  });
});

describe("LocalWorldRepository contract with the in-memory reference adapter", () => {
  it("creates stable local identities and keeps local and published revisions distinct", async () => {
    const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const record = await createTestWorld(repo);
    const objectId = repo.allocateObjectId(record.snapshot.worldId);
    const relationshipId = repo.allocateRelationshipId(record.snapshot.worldId);

    expect(record.localRevision).toBe(0);
    expect(record.publishedRevisionId).toBeNull();
    expect(objectId).toMatch(/^local-world:fixture-\d+:object:fixture-\d+$/);
    expect(relationshipId).toMatch(/^local-world:fixture-\d+:relationship:fixture-\d+$/);
    expect(repo.allocateObjectId(record.snapshot.worldId)).not.toBe(objectId);
  });

  it("reads four related test nodes through a new facade and preserves same-name identities", async () => {
    const store = new InMemoryLocalWorldStore();
    const repo = new InMemoryLocalWorldRepository({ store, idFactory: sequenceLocalIds() });
    const initial = await createTestWorld(repo);
    const fixture = fourNodeWorldFixture(repo, initial.snapshot.worldId);
    const sameNamePeople = sameNameWorldPeopleFixture(repo, initial.snapshot.worldId);
    const snapshot = { ...fixture, objects: [...fixture.objects, ...sameNamePeople] };
    const committed = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: snapshot,
      edit: { classification: "supported-semantic-intent", description: "Added initial test graph" },
    });

    expect(committed.status).toBe("committed");
    if (committed.status !== "committed") return;
    expect(committed.record.snapshot.objects).toHaveLength(6);
    expect(committed.record.snapshot.relationships).toHaveLength(2);
    expect(committed.record.snapshot.objects[4].name).toBe(committed.record.snapshot.objects[5].name);
    expect(committed.record.snapshot.objects[4].id).not.toBe(committed.record.snapshot.objects[5].id);

    // A new facade can read this process-local store. This is not a browser reload test.
    const reopenedFacade = new InMemoryLocalWorldRepository({ store, idFactory: sequenceLocalIds() });
    const read = await reopenedFacade.readWorld(initial.snapshot.worldId);
    expect(read.status).toBe("found");
    if (read.status === "found") {
      expect(read.record.snapshot).toEqual(committed.record.snapshot);
      expect(read.record.localRevision).toBe(1);
      expect(read.record.history).toHaveLength(2);
    }

    const freshStoreFacade = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    expect(await freshStoreFacade.readWorld(initial.snapshot.worldId)).toEqual({ status: "missing" });
  });

  it("preserves the committed version and the complete losing candidate on stale CAS", async () => {
    const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const initial = await createTestWorld(repo);
    const winnerSnapshot = { ...initial.snapshot, title: "Winning title" };
    const winner = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: winnerSnapshot,
      edit: localOnlyEdit,
    });
    expect(winner.status).toBe("committed");

    const losingSnapshot = fourNodeWorldFixture(repo, initial.snapshot.worldId);
    const result = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: losingSnapshot,
      edit: { classification: "buddy-local-only", description: "Complete losing graph proposal" },
    });
    expect(result.status).toBe("conflict");
    if (result.status !== "conflict") return;
    expect(result.committed.snapshot.title).toBe("Winning title");
    expect(result.committed.localRevision).toBe(1);
    expect(result.candidate.baseLocalRevision).toBe(0);
    expect(result.candidate.currentLocalRevision).toBe(1);
    expect(result.candidate.proposedSnapshot).toEqual(losingSnapshot);
    expect(result.candidate.proposedSnapshot.objects).toHaveLength(4);

    const candidates = await repo.readConflictCandidates(initial.snapshot.worldId);
    expect(candidates.status).toBe("found");
    if (candidates.status === "found") expect(candidates.candidates).toEqual([result.candidate]);
  });

  it("atomically leaves snapshot and history unchanged when the transaction fails", async () => {
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: (point) => {
        if (point === "semantic-edit") throw new Error("simulated transaction failure");
      },
    });
    const initial = await createTestWorld(repo);
    const result = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: fourNodeWorldFixture(repo, initial.snapshot.worldId),
      edit: localOnlyEdit,
    });
    expect(result).toEqual({ status: "error", message: "simulated transaction failure" });

    const read = await repo.readWorld(initial.snapshot.worldId);
    expect(read.status).toBe("found");
    if (read.status === "found") {
      expect(read.record).toEqual(initial);
      expect(read.record.localRevision).toBe(0);
      expect(read.record.history).toHaveLength(1);
    }
  });

  it("copies input and output values so callers cannot mutate repository state", async () => {
    const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const initial = await createTestWorld(repo);
    const input = fourNodeWorldFixture(repo, initial.snapshot.worldId);
    const result = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: input,
      edit: localOnlyEdit,
    });
    expect(result.status).toBe("committed");

    input.objects[0].properties.role = "mutated after call";
    if (result.status === "committed") {
      (result.record.snapshot.objects[0].properties as Record<string, unknown>).role = "mutated result";
    }
    const read = await repo.readWorld(initial.snapshot.worldId);
    expect(read.status).toBe("found");
    if (read.status === "found") {
      expect(read.record.snapshot.objects[0].properties.role).toBe("traveler");
    }
  });

  it("lets racing writes at one expected revision commit once and retain the loser", async () => {
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: async (point) => { if (point === "semantic-edit") await gate; },
    });
    const initial = await createTestWorld(repo);
    const a = repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: { ...initial.snapshot, title: "A" },
      edit: localOnlyEdit,
    });
    const b = repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: { ...initial.snapshot, title: "B" },
      edit: localOnlyEdit,
    });
    release();
    const results = await Promise.all([a, b]);
    expect(results.map((item) => item.status).sort()).toEqual(["committed", "conflict"]);
    const read = await repo.readWorld(initial.snapshot.worldId);
    expect(read.status).toBe("found");
    const candidates = await repo.readConflictCandidates(initial.snapshot.worldId);
    expect(candidates.status).toBe("found");
    if (read.status === "found" && candidates.status === "found") {
      expect(read.record.localRevision).toBe(1);
      expect(candidates.candidates).toHaveLength(1);
    }
  });

  it("keeps layout writes on their own revision and outside semantic history", async () => {
    const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const initial = await createTestWorld(repo);
    const layout: LocalWorldLayout = {
      positions: { "local-node": { x: 240, y: 90 } },
      viewport: { x: 12, y: -7, zoom: 1.4 },
      layoutVersion: 1,
    };
    const written = await repo.writeLayout({
      worldId: initial.snapshot.worldId,
      expectedLayoutRevision: 0,
      nextLayout: layout,
    });
    expect(written.status).toBe("written");
    if (written.status !== "written") return;
    expect(written.record.layoutRevision).toBe(1);
    expect(written.record.localRevision).toBe(initial.localRevision);
    expect(written.record.snapshot).toEqual(initial.snapshot);
    expect(written.record.history).toEqual(initial.history);

    const staleLayout = await repo.writeLayout({
      worldId: initial.snapshot.worldId,
      expectedLayoutRevision: 0,
      nextLayout: { ...layout, viewport: { x: 0, y: 0, zoom: 2 } },
    });
    expect(staleLayout.status).toBe("conflict");
  });

  it("distinguishes missing Worlds from failed transactions", async () => {
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: (point) => {
        if (point === "semantic-edit") throw new Error("storage unavailable");
      },
    });
    const initial = await createTestWorld(repo);
    const missing = await repo.readWorld("local-world:absent" as LocalWorldId);
    expect(missing).toEqual({ status: "missing" });
    const failure = await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: initial.snapshot,
      edit: localOnlyEdit,
    });
    expect(failure).toEqual({ status: "error", message: "storage unavailable" });
  });
});
