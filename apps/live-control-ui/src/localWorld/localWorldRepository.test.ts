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
  it("captures every semantic request header before an asynchronous adapter hook", async () => {
    let holdWrites = false;
    let releaseWrite!: () => void;
    const gate = new Promise<void>((resolve) => { releaseWrite = resolve; });
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: async (point) => {
        if (holdWrites && point === "semantic-edit") await gate;
      },
    });
    const first = await createTestWorld(repo);
    const second = await createTestWorld(repo);
    const winner = await repo.commitSemanticEdit({
      worldId: first.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: { ...first.snapshot, title: "Winner" },
      edit: localOnlyEdit,
    });
    expect(winner.status).toBe("committed");

    holdWrites = true;
    const request = {
      worldId: first.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: { ...first.snapshot, title: "Stale candidate" },
      edit: localOnlyEdit,
    };
    const pending = repo.commitSemanticEdit(request);
    request.worldId = second.snapshot.worldId;
    request.expectedLocalRevision = 1;
    releaseWrite();

    const result = await pending;
    expect(result.status).toBe("conflict");
    if (result.status !== "conflict") return;
    expect(result.committed.snapshot.worldId).toBe(first.snapshot.worldId);
    expect(result.committed.snapshot.title).toBe("Winner");
    expect(result.candidate.worldId).toBe(first.snapshot.worldId);
    expect(result.candidate.baseLocalRevision).toBe(0);
    expect(result.candidate.proposedSnapshot.worldId).toBe(first.snapshot.worldId);
    expect((await repo.readWorld(second.snapshot.worldId)).status).toBe("found");
  });

  it("captures the layout revision header before an asynchronous adapter hook", async () => {
    let holdWrites = false;
    let releaseWrite!: () => void;
    const gate = new Promise<void>((resolve) => { releaseWrite = resolve; });
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: async (point) => {
        if (holdWrites && point === "layout") await gate;
      },
    });
    const initial = await createTestWorld(repo);
    const winningLayout: LocalWorldLayout = {
      positions: { node: { x: 10, y: 10 } },
      viewport: { x: 0, y: 0, zoom: 1 },
      layoutVersion: 1,
    };
    await repo.writeLayout({
      worldId: initial.snapshot.worldId,
      expectedLayoutRevision: 0,
      nextLayout: winningLayout,
    });

    holdWrites = true;
    const request = {
      worldId: initial.snapshot.worldId,
      expectedLayoutRevision: 0,
      nextLayout: { ...winningLayout, positions: { node: { x: 90, y: 90 } } },
    };
    const pending = repo.writeLayout(request);
    request.expectedLayoutRevision = 1;
    releaseWrite();

    const result = await pending;
    expect(result.status).toBe("conflict");
    if (result.status === "conflict") expect(result.record.layout).toEqual(winningLayout);
  });

  it("captures the create title before an asynchronous adapter hook", async () => {
    let holdWrites = false;
    let releaseWrite!: () => void;
    const gate = new Promise<void>((resolve) => { releaseWrite = resolve; });
    const repo = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: async (point) => {
        if (holdWrites && point === "create") await gate;
      },
    });
    holdWrites = true;
    const request = { title: "Original title" };
    const pending = repo.createWorld(request);
    request.title = "Mutated after call";
    releaseWrite();

    const result = await pending;
    expect(result.status).toBe("created");
    if (result.status === "created") expect(result.record.snapshot.title).toBe("Original title");
  });

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


describe("Buddy-owned local World notes port", () => {
  it("returns a World and its mutable sidecar as one export snapshot", async () => {
    const repo = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const record = await createTestWorld(repo);
    await repo.commitWorldNotes({ worldId: record.snapshot.worldId, expectedLocalRevision: 0, markdown: "snapshot note" });
    const snapshot = await repo.readWorldExportSnapshot(record.snapshot.worldId);
    expect(snapshot.status).toBe("found");
    if (snapshot.status !== "found") return;
    expect(snapshot.record.localRevision).toBe(1);
    expect(snapshot.data?.bundledMembers["documents/buddy-world-notes.md"]).toEqual(Array.from(new TextEncoder().encode("snapshot note")));
  });

  it("commits notes with local revision/history and retains a losing body through a fresh repository facade", async () => {
    const store = new InMemoryLocalWorldStore();
    const repo = new InMemoryLocalWorldRepository({ store, idFactory: sequenceLocalIds() });
    const record = await createTestWorld(repo, "Notes world");
    const empty = await repo.readWorldNotes(record.snapshot.worldId);
    expect(empty.status).toBe("found");
    if (empty.status !== "found") return;
    expect(empty.state).toMatchObject({ localRevision: 0, documentExists: false, markdown: "" });

    const saved = await repo.commitWorldNotes({ worldId: record.snapshot.worldId, expectedLocalRevision: 0, markdown: "# Harbor\n\nA blue door." });
    expect(saved.status).toBe("committed");
    if (saved.status !== "committed") return;
    expect(saved.record.localRevision).toBe(1);
    expect(saved.record.history.at(-1)).toMatchObject({ localRevision: 1, classification: "buddy-local-only" });

    const stale = await repo.commitWorldNotes({ worldId: record.snapshot.worldId, expectedLocalRevision: 0, markdown: "# My unsaved harbor" });
    expect(stale.status).toBe("conflict");
    if (stale.status !== "conflict") return;
    expect(stale.candidate.proposedPackageData).toBeDefined();
    const reopened = await new InMemoryLocalWorldRepository({ store }).readWorldNotes(record.snapshot.worldId);
    expect(reopened.status).toBe("found");
    if (reopened.status !== "found") return;
    expect(reopened.state.markdown).toBe("# Harbor\n\nA blue door.");
    expect(reopened.state.conflictCandidates).toHaveLength(1);
    const candidate = reopened.state.conflictCandidates[0];
    expect(candidate.proposedPackageData?.bundledMembers["documents/buddy-world-notes.md"]).toEqual(Array.from(new TextEncoder().encode("# My unsaved harbor")));
    expect(await repo.discardWorldNotesConflict(record.snapshot.worldId, candidate.id)).toBe("discarded");
    const afterDiscard = await repo.readWorldNotes(record.snapshot.worldId);
    expect(afterDiscard.status).toBe("found");
    if (afterDiscard.status === "found") expect(afterDiscard.state.conflictCandidates).toHaveLength(0);
  });

  it("preserves committed note and revision when the atomic write hook fails", async () => {
    let shouldFail = false;
    const repo = new InMemoryLocalWorldRepository({ beforeCommit: (point) => { if (shouldFail && point === "document-edit") throw new Error("simulated transaction abort"); } });
    const record = await createTestWorld(repo);
    expect((await repo.commitWorldNotes({ worldId: record.snapshot.worldId, expectedLocalRevision: 0, markdown: "old body" })).status).toBe("committed");
    shouldFail = true;
    const failed = await repo.commitWorldNotes({ worldId: record.snapshot.worldId, expectedLocalRevision: 1, markdown: "new body" });
    expect(failed.status).toBe("error");
    const world = await repo.readWorld(record.snapshot.worldId);
    const notes = await repo.readWorldNotes(record.snapshot.worldId);
    expect(world.status).toBe("found");
    if (world.status === "found") expect(world.record.localRevision).toBe(1);
    expect(notes.status).toBe("found");
    if (notes.status === "found") expect(notes.state.markdown).toBe("old body");
  });

  it("does not erase a later conflict candidate when an earlier discard is delayed", async () => {
    let releaseDiscard!: () => void;
    let discardStarted!: () => void;
    const gate = new Promise<void>((resolve) => { releaseDiscard = resolve; });
    const started = new Promise<void>((resolve) => { discardStarted = resolve; });
    const repo = new InMemoryLocalWorldRepository({
      beforeCommit: async (point) => {
        if (point === "document-conflict-discard") { discardStarted(); await gate; }
      },
    });
    const initial = await createTestWorld(repo);
    await repo.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 0,
      nextSnapshot: { ...initial.snapshot, title: "Concurrent revision" },
      edit: { classification: "buddy-local-only", description: "Concurrent title edit" },
    });
    const first = await repo.commitWorldNotes({ worldId: initial.snapshot.worldId, expectedLocalRevision: 0, markdown: "first candidate" });
    expect(first.status).toBe("conflict");
    if (first.status !== "conflict") return;
    const discarding = repo.discardWorldNotesConflict(initial.snapshot.worldId, first.candidate.id);
    await started;
    const second = await repo.commitWorldNotes({ worldId: initial.snapshot.worldId, expectedLocalRevision: 0, markdown: "second candidate" });
    expect(second.status).toBe("conflict");
    releaseDiscard();
    expect(await discarding).toBe("discarded");
    const notes = await repo.readWorldNotes(initial.snapshot.worldId);
    expect(notes.status).toBe("found");
    if (notes.status === "found") {
      expect(notes.state.conflictCandidates).toHaveLength(1);
      expect(notes.state.conflictCandidates[0].proposedPackageData?.bundledMembers["documents/buddy-world-notes.md"]).toEqual(Array.from(new TextEncoder().encode("second candidate")));
    }
  });
});
