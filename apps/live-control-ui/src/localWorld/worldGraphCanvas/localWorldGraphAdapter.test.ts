import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "../inMemoryLocalWorldRepository";
import { createTestWorld, fourNodeWorldFixture, sequenceLocalIds } from "../localWorldContractFixtures";
import { createLocalWorldGraphAdapter } from "./localWorldGraphAdapter";
import type { LocalObjectId } from "../localWorldRepository";

async function seeded() {
  const repository = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
  const created = await createTestWorld(repository, "The Ember Coast");
  const result = await repository.commitSemanticEdit({
    worldId: created.snapshot.worldId,
    expectedLocalRevision: created.localRevision,
    nextSnapshot: fourNodeWorldFixture(repository, created.snapshot.worldId),
    edit: { classification: "buddy-local-only", description: "Seed test graph" },
  });
  if (result.status !== "committed") throw new Error("Unable to seed adapter test graph.");
  return { repository, record: result.record, adapter: createLocalWorldGraphAdapter(repository) };
}

describe("local World graph adapter", () => {
  it("renames through semantic CAS and preserves object and assertion identities", async () => {
    const { record, adapter } = await seeded();
    const relationshipIds = record.snapshot.relationships.map((item) => item.id);
    const objectId = record.snapshot.objects[0].id;
    const result = await adapter.renameObject(record, objectId, "Mara of the Reach");
    expect(result.status).toBe("committed");
    if (result.status === "committed") {
      expect(result.record.localRevision).toBe(record.localRevision + 1);
      expect(result.record.snapshot.objects.find((item) => item.id === objectId)?.name).toBe("Mara of the Reach");
      expect(result.record.snapshot.relationships.map((item) => item.id)).toEqual(relationshipIds);
      expect(result.record.history.at(-1)?.description).toContain("Renamed");
    }
  });

  it("creates parallel assertions with new repository identities", async () => {
    const { record, adapter } = await seeded();
    const [from, to] = record.snapshot.objects;
    const input = { fromObjectId: from.id, toObjectId: to.id, kind: "travels with" };
    const first = await adapter.createRelationship(record, input);
    const second = await adapter.createRelationship(record, input);
    expect(first.status).toBe("committed");
    expect(second.status).toBe("conflict");
    if (first.status !== "committed" || second.status !== "conflict") return;
    const firstRelationship = first.record.snapshot.relationships.at(-1)!;
    const losingRelationship = second.candidate.proposedSnapshot.relationships.at(-1)!;
    expect(firstRelationship.id).not.toBe(losingRelationship.id);
    expect(firstRelationship.fromObjectId).toBe(losingRelationship.fromObjectId);
    expect(firstRelationship.toObjectId).toBe(losingRelationship.toObjectId);
    expect(second.committed.snapshot.relationships.at(-1)?.id).toBe(firstRelationship.id);
  });

  it("preserves stale concurrent edit candidates instead of overwriting committed state", async () => {
    const { repository, record, adapter } = await seeded();
    const winner = await adapter.createObject(record, { name: "The Crownless Guide", kind: "person" });
    expect(winner.status).toBe("committed");
    const stale = await adapter.createObject(record, { name: "The Salt Witch", kind: "person" });
    expect(stale.status).toBe("conflict");
    if (stale.status !== "conflict") return;
    expect(stale.committed.localRevision).toBe(record.localRevision + 1);
    expect(stale.candidate.proposedSnapshot.objects.at(-1)?.name).toBe("The Salt Witch");
    expect((await repository.readConflictCandidates(record.snapshot.worldId)).status).toBe("found");
  });

  it("keeps layout revision separate from semantic revision", async () => {
    const { record, adapter } = await seeded();
    const objectId = record.snapshot.objects[0].id;
    const result = await adapter.moveObjects(record, { [objectId]: { x: 222, y: 176 } });
    expect(result.status).toBe("written");
    if (result.status === "written") {
      expect(result.record.layout.positions[objectId]).toEqual({ x: 222, y: 176 });
      expect(result.record.layoutRevision).toBe(record.layoutRevision + 1);
      expect(result.record.localRevision).toBe(record.localRevision);
      expect(result.record.history).toEqual(record.history);
      expect(result.record.snapshot).toEqual(record.snapshot);
    }
  });

  it("captures semantic inputs before an asynchronous commit and preserves failed transactions", async () => {
    let hold = false;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    const repository = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: async (point) => { if (hold && point === "semantic-edit") await gate; },
    });
    const initial = await createTestWorld(repository);
    const record = { ...initial, snapshot: fourNodeWorldFixture(repository, initial.snapshot.worldId) };
    const seeded = await repository.commitSemanticEdit({
      worldId: record.snapshot.worldId, expectedLocalRevision: 0, nextSnapshot: record.snapshot,
      edit: { classification: "buddy-local-only", description: "Seed" },
    });
    if (seeded.status !== "committed") throw new Error("Unable to seed async adapter test.");
    const adapter = createLocalWorldGraphAdapter(repository);
    hold = true;
    const input = { name: "Original name", kind: "person" };
    const pending = adapter.createObject(seeded.record, input);
    input.name = "Mutated later";
    release();
    const result = await pending;
    expect(result.status).toBe("committed");
    if (result.status === "committed") expect(result.record.snapshot.objects.at(-1)?.name).toBe("Original name");
  });

  it("returns truthful validation and repository errors without advancing revisions", async () => {
    const { repository, record, adapter } = await seeded();
    expect((await adapter.renameObject(record, record.snapshot.objects[0].id, "  ")).status).toBe("error");
    expect((await adapter.createRelationship(record, {
      fromObjectId: record.snapshot.objects[0].id,
      toObjectId: "missing" as LocalObjectId,
      kind: "mentions",
    })).status).toBe("error");

    const failingRepository = new InMemoryLocalWorldRepository({
      idFactory: sequenceLocalIds(),
      beforeCommit: (point) => { if (point === "layout" || point === "semantic-edit") throw new Error("disk is busy"); },
    });
    const failingRecord = await createTestWorld(failingRepository);
    const failingAdapter = createLocalWorldGraphAdapter(failingRepository);
    const semanticFailure = await failingAdapter.createObject(failingRecord, { name: "Interrupted", kind: "person" });
    expect(semanticFailure).toMatchObject({ status: "error", message: "disk is busy" });
    const result = await failingAdapter.moveObjects(failingRecord, { node: { x: 50, y: 50 } });
    expect(result).toMatchObject({ status: "error", message: "disk is busy" });
    const failureReadback = await failingRepository.readWorld(failingRecord.snapshot.worldId);
    expect(failureReadback.status).toBe("found");
    if (failureReadback.status === "found") {
      expect(failureReadback.record.localRevision).toBe(failingRecord.localRevision);
      expect(failureReadback.record.snapshot).toEqual(failingRecord.snapshot);
      expect(failureReadback.record.history).toEqual(failingRecord.history);
    }
    const after = await repository.readWorld(record.snapshot.worldId);
    expect(after.status).toBe("found");
    if (after.status === "found") expect(after.record.localRevision).toBe(record.localRevision);
  });
});
