// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import { InMemoryLocalWorldRepository } from "./inMemoryLocalWorldRepository";
import { createTestWorld, sequenceLocalIds } from "./localWorldContractFixtures";
import { addPackageFixtureReferences, packageFixtureAttachmentBytes } from "./localWorldPackageFixtures";
import { encodeLocalWorldPackageV1, parseLocalWorldPackageV1 } from "./localWorldPackageV1";
import { restoreStagedLocalWorldPackage } from "./localWorldPackageRestore";

async function stagedFrom(record: Awaited<ReturnType<typeof createTestWorld>>) {
  const encoded = await encodeLocalWorldPackageV1(record);
  if (encoded.status !== "encoded") throw new Error(encoded.message);
  const path = "documents/source.txt";
  const ref = { id: "doc:source", status: "bundled" as const, path, mediaType: "text/plain", locator: null };
  const members = await addPackageFixtureReferences(encoded.members, {
    documents: [ref, { id: "doc:external", status: "external", path: null, mediaType: "text/markdown", locator: "https://example.invalid/source.md" }],
    assets: [{ id: "asset:missing", status: "missing", path: null, mediaType: "image/png", locator: null }],
  }, new Map([[path, packageFixtureAttachmentBytes.document]]));
  const parsed = await parseLocalWorldPackageV1(members);
  if (parsed.status !== "staged") throw new Error(parsed.message);
  return parsed.candidate;
}

describe("atomic local package restore contract", () => {
  it("restores an adapter-created world and bundled bytes with metadata and exact revisions", async () => {
    const source = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds("source") });
    let record = await createTestWorld(source, "same title");
    const edited = await source.commitSemanticEdit({ worldId: record.snapshot.worldId, expectedLocalRevision: 0, nextSnapshot: { ...record.snapshot, title: "same title edited" }, edit: { classification: "buddy-local-only", description: "title edit" } });
    expect(edited.status).toBe("committed");
    if (edited.status !== "committed") return;
    record = edited.record;
    const laidOut = await source.writeLayout({ worldId: record.snapshot.worldId, expectedLayoutRevision: 0, nextLayout: { ...record.layout, viewport: { ...record.layout.viewport, x: 9 } } });
    expect(laidOut.status).toBe("written");
    if (laidOut.status !== "written") return;
    const staged = await stagedFrom(laidOut.record);
    const destination = new InMemoryLocalWorldRepository();
    expect((await restoreStagedLocalWorldPackage(destination, staged)).status).toBe("restored");
    expect(await destination.readWorld(record.snapshot.worldId)).toEqual({ status: "found", record: laidOut.record });
    const supplemental = await destination.readPackageData(record.snapshot.worldId);
    expect(supplemental.status).toBe("found");
    if (supplemental.status === "found") {
      expect(supplemental.data.documents).toEqual(staged.documents);
      expect(supplemental.data.assets).toEqual(staged.assets);
      expect(supplemental.data.bundledMembers["documents/source.txt"]).toEqual(Array.from(packageFixtureAttachmentBytes.document));
      expect(supplemental.data.fidelity).toEqual(staged.manifest.fidelity);
      expect(supplemental.data.creatorProfileAssumptions).toEqual(staged.manifest.creatorProfileAssumptions);
    }
  });

  it("refuses collisions without changing the existing record or sidecar; same names with distinct IDs remain separate", async () => {
    const source = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds("same") });
    const first = await createTestWorld(source, "same name");
    const staged = await stagedFrom(first);
    const destination = new InMemoryLocalWorldRepository();
    expect((await restoreStagedLocalWorldPackage(destination, staged)).status).toBe("restored");
    const before = await destination.readWorld(first.snapshot.worldId);
    const sidecarBefore = await destination.readPackageData(first.snapshot.worldId);
    expect((await restoreStagedLocalWorldPackage(destination, staged)).status).toBe("collision");
    expect(await destination.readWorld(first.snapshot.worldId)).toEqual(before);
    expect(await destination.readPackageData(first.snapshot.worldId)).toEqual(sidecarBefore);
    const second = structuredClone(first);
    second.snapshot.worldId = "local-world:another" as typeof second.snapshot.worldId;
    const otherStaged = await stagedFrom(second);
    expect((await restoreStagedLocalWorldPackage(destination, otherStaged)).status).toBe("restored");
    expect((await destination.readWorld(first.snapshot.worldId)).status).toBe("found");
    expect((await destination.readWorld(second.snapshot.worldId)).status).toBe("found");
  });

  it("captures staged bytes before await and leaves no record or sidecar when the in-memory commit hook fails", async () => {
    const source = new InMemoryLocalWorldRepository();
    const staged = await stagedFrom(await createTestWorld(source));
    const repository = new InMemoryLocalWorldRepository({ beforeCommit: (point) => { if (point === "package-restore") throw new Error("simulated quota abort"); } });
    const pending = restoreStagedLocalWorldPackage(repository, staged);
    staged.members.get("documents/source.txt")!.fill(0);
    expect((await pending).status).toBe("error");
    expect(await repository.readWorld(staged.record.snapshot.worldId)).toEqual({ status: "missing" });
    expect(await repository.readPackageData(staged.record.snapshot.worldId)).toEqual({ status: "missing" });
  });

  it("captures the caller-owned record and byte members before asynchronous digest validation", async () => {
    const source = new InMemoryLocalWorldRepository();
    const staged = await stagedFrom(await createTestWorld(source));
    const originalTitle = staged.record.snapshot.title;
    const originalBytes = Array.from(staged.members.get("documents/source.txt")!);
    const destination = new InMemoryLocalWorldRepository();
    const pending = restoreStagedLocalWorldPackage(destination, staged);
    (staged.record.snapshot as { title: string }).title = "mutated after restore call";
    staged.members.get("documents/source.txt")!.fill(0);
    expect((await pending).status).toBe("restored");
    const restored = await destination.readWorld(staged.record.snapshot.worldId);
    const data = await destination.readPackageData(staged.record.snapshot.worldId);
    expect(restored.status).toBe("found");
    if (restored.status === "found") expect(restored.record.snapshot.title).toBe(originalTitle);
    expect(data.status).toBe("found");
    if (data.status === "found") expect(data.data.bundledMembers["documents/source.txt"]).toEqual(originalBytes);
  });

  it("rejects malformed supplemental metadata at the repository boundary before writing", async () => {
    const source = new InMemoryLocalWorldRepository();
    const staged = await stagedFrom(await createTestWorld(source));
    const destination = new InMemoryLocalWorldRepository();
    const invalid = {
      localWorldId: staged.record.snapshot.worldId,
      documents: staged.documents,
      assets: staged.assets,
      bundledMembers: { "documents/source.txt": Array.from(packageFixtureAttachmentBytes.document) },
      fidelity: { ...staged.manifest.fidelity, localRecord: "invented" },
      creatorProfileAssumptions: staged.manifest.creatorProfileAssumptions,
    } as unknown as Parameters<typeof destination.restorePackage>[1];
    expect((await destination.restorePackage(staged.record, invalid)).status).toBe("error");
    expect(await destination.readWorld(staged.record.snapshot.worldId)).toEqual({ status: "missing" });
    expect(await destination.readPackageData(staged.record.snapshot.worldId)).toEqual({ status: "missing" });
  });
});
