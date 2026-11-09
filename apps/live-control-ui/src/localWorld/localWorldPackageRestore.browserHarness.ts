import { openIndexedDbLocalWorldRepository } from "./indexedDbLocalWorldRepository";
import { decodeLocalWorldPackageZipV1, encodeLocalWorldPackageZipV1 } from "./localWorldPackageZipV1";
import { encodeLocalWorldPackageV1 } from "./localWorldPackageV1";
import { restoreStagedLocalWorldPackage } from "./localWorldPackageRestore";
import { addPackageFixtureReferences, packageFixtureAttachmentBytes } from "./localWorldPackageFixtures";

function assert(value: unknown, message: string): asserts value { if (!value) throw new Error(message); }
function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonical(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.addEventListener("success", () => resolve(request.result), { once: true });
    request.addEventListener("error", () => reject(request.error), { once: true });
  });
}
async function deleteDb(name: string): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(name);
    request.addEventListener("success", () => resolve(), { once: true });
    request.addEventListener("error", () => reject(request.error), { once: true });
    request.addEventListener("blocked", () => reject(new Error("Disposable test database deletion blocked.")), { once: true });
  });
}

async function run(): Promise<void> {
  const output = document.querySelector<HTMLElement>("#result");
  assert(output, "Missing harness result element.");
  const token = crypto.randomUUID();
  const sourceName = `local-world-restore-source-${token}`;
  const targetName = `local-world-restore-target-${token}`;
  const abortName = `local-world-restore-abort-${token}`;
  const malformedName = `local-world-restore-malformed-${token}`;
  const migrationName = `local-world-restore-migration-${token}`;
  const names = [sourceName, targetName, abortName, malformedName, migrationName];
  const close: Array<() => void> = [];
  try {
    const sourceOpen = await openIndexedDbLocalWorldRepository(sourceName);
    assert(sourceOpen.status === "opened", sourceOpen.status === "error" ? sourceOpen.message : "Source DB did not open.");
    close.push(() => sourceOpen.repository.close());
    const created = await sourceOpen.repository.createWorld({ title: "Native restore source" });
    assert(created.status === "created", "Could not create source record.");
    const semantic = await sourceOpen.repository.commitSemanticEdit({ worldId: created.record.snapshot.worldId, expectedLocalRevision: 0, nextSnapshot: { ...created.record.snapshot, title: "Edited source" }, edit: { classification: "buddy-local-only", description: "browser harness edit" } });
    assert(semantic.status === "committed", "Could not edit source record.");
    const layout = await sourceOpen.repository.writeLayout({ worldId: created.record.snapshot.worldId, expectedLayoutRevision: 0, nextLayout: { ...semantic.record.layout, viewport: { ...semantic.record.layout.viewport, x: 31 } } });
    assert(layout.status === "written", "Could not update source layout.");
    const encoded = await encodeLocalWorldPackageV1(layout.record);
    assert(encoded.status === "encoded", encoded.status === "error" ? encoded.message : "Codec did not encode.");
    const assetBytes = packageFixtureAttachmentBytes.asset;
    const assetHashBytes = await crypto.subtle.digest("SHA-256", assetBytes);
    const assetHash = Array.from(new Uint8Array(assetHashBytes), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const documentPath = "documents/browser-note.txt";
    const assetPath = `assets/${assetHash}`;
    const references = await addPackageFixtureReferences(encoded.members, {
      documents: [{ id: "doc:browser", status: "bundled", path: documentPath, mediaType: "text/plain", locator: null }],
      assets: [{ id: "asset:browser", status: "bundled", path: assetPath, mediaType: "application/octet-stream", locator: null }],
    }, new Map([[documentPath, packageFixtureAttachmentBytes.document], [assetPath, assetBytes]]));
    const archive = await encodeLocalWorldPackageZipV1(references);
    assert(archive.status === "encoded", archive.status === "error" ? archive.message : "ZIP did not encode.");
    const decoded = await decodeLocalWorldPackageZipV1(archive.blob);
    assert(decoded.status === "staged", decoded.status === "error" ? decoded.message : "ZIP did not decode.");

    const targetOpen = await openIndexedDbLocalWorldRepository(targetName);
    assert(targetOpen.status === "opened", targetOpen.status === "error" ? targetOpen.message : "Target DB did not open.");
    close.push(() => targetOpen.repository.close());
    const secondConnection = await openIndexedDbLocalWorldRepository(targetName);
    assert(secondConnection.status === "opened", secondConnection.status === "error" ? secondConnection.message : "Second target connection did not open.");
    close.push(() => secondConnection.repository.close());
    const concurrent = await Promise.all([
      restoreStagedLocalWorldPackage(targetOpen.repository, decoded.parsed.candidate),
      restoreStagedLocalWorldPackage(secondConnection.repository, decoded.parsed.candidate),
    ]);
    assert(concurrent.filter((result) => result.status === "restored").length === 1 && concurrent.filter((result) => result.status === "collision").length === 1, "Concurrent restore did not produce exactly one winner and one collision.");
    const readback = await targetOpen.repository.readWorld(layout.record.snapshot.worldId);
    const sidecar = await targetOpen.repository.readPackageData(layout.record.snapshot.worldId);
    assert(readback.status === "found" && canonical(readback.record) === canonical(layout.record), "Restored semantic/layout/history record differs.");
    assert(sidecar.status === "found", "Restored package supplemental record is missing.");
    assert(sidecar.status === "found"
      && sidecar.data.bundledMembers[documentPath].join(",") === Array.from(packageFixtureAttachmentBytes.document).join(",")
      && sidecar.data.bundledMembers[assetPath].join(",") === Array.from(assetBytes).join(","),
    "Bundled document or binary asset bytes changed during native restore.");
    assert(sidecar.status === "found", "Supplemental readback is required for malformed-record probes.");
    const collision = await restoreStagedLocalWorldPackage(targetOpen.repository, decoded.parsed.candidate);
    assert(collision.status === "collision", "Existing local identity was not refused.");

    const v2 = indexedDB.open(migrationName, 2);
    v2.addEventListener("upgradeneeded", () => {
      const db = v2.result;
      db.createObjectStore("worlds", { keyPath: "snapshot.worldId" });
      const conflicts = db.createObjectStore("conflicts", { keyPath: "id" });
      conflicts.createIndex("worldId", "worldId", { unique: false });
      db.createObjectStore("unrelated-preserved", { keyPath: "id" });
    });
    const oldDb = await requestResult(v2);
    const oldTx = oldDb.transaction(["worlds", "unrelated-preserved"], "readwrite");
    oldTx.objectStore("worlds").add(layout.record);
    oldTx.objectStore("unrelated-preserved").add({ id: "keep", marker: "preserved" });
    await new Promise<void>((resolve, reject) => {
      oldTx.addEventListener("complete", () => resolve(), { once: true });
      oldTx.addEventListener("abort", () => reject(oldTx.error), { once: true });
    });
    oldDb.close();
    const migrated = await openIndexedDbLocalWorldRepository(migrationName);
    assert(migrated.status === "opened", migrated.status === "error" ? migrated.message : "Valid v2 upgrade refused.");
    close.push(() => migrated.repository.close());
    const migratedRecord = await migrated.repository.readWorld(layout.record.snapshot.worldId);
    assert(migratedRecord.status === "found" && canonical(migratedRecord.record) === canonical(layout.record), "v2 data changed during v3 upgrade.");
    migrated.repository.close();
    const checkMigration = await requestResult(indexedDB.open(migrationName));
    assert(checkMigration.version === 3 && checkMigration.objectStoreNames.contains("unrelated-preserved"), "v2 upgrade lost its unrelated store or missed schema v3.");
    const marker = await requestResult(checkMigration.transaction("unrelated-preserved", "readonly").objectStore("unrelated-preserved").get("keep"));
    assert((marker as { marker?: string } | undefined)?.marker === "preserved", "v2 upgrade lost unrelated data.");
    checkMigration.close();

    let writes = 0;
    const abortOpen = await openIndexedDbLocalWorldRepository(abortName, { beforeWrite: (point) => { if (point === "package-restore" && ++writes === 2) throw new DOMException("Simulated quota abort", "QuotaExceededError"); } });
    assert(abortOpen.status === "opened", abortOpen.status === "error" ? abortOpen.message : "Abort DB did not open.");
    close.push(() => abortOpen.repository.close());
    const negativeRecord = { ...structuredClone(layout.record), localRevision: -1 };
    const malformedHistory = {
      ...structuredClone(layout.record),
      history: [{ id: "garbage", localRevision: 0, classification: "invented", description: 5 }] as unknown as typeof layout.record.history,
    };
    assert((await abortOpen.repository.restorePackage(negativeRecord, sidecar.data)).status === "error", "Direct IndexedDB restore accepted a negative revision.");
    assert((await abortOpen.repository.restorePackage(malformedHistory, sidecar.data)).status === "error", "Direct IndexedDB restore accepted malformed history.");
    assert((await abortOpen.repository.readWorld(layout.record.snapshot.worldId)).status === "missing", "Malformed direct restores wrote a record.");
    const malformedPathCases = [
      { namespace: "documents" as const, path: "documents/../escape", id: `local-world:document-path-${token}` },
      { namespace: "assets" as const, path: "assets/../escape", id: `local-world:asset-path-${token}` },
    ];
    for (const item of malformedPathCases) {
      const worldId = item.id as typeof layout.record.snapshot.worldId;
      const malformedRecord = { ...structuredClone(layout.record), snapshot: { ...layout.record.snapshot, worldId } };
      const malformedData = item.namespace === "documents"
        ? {
          ...sidecar.data,
          localWorldId: worldId,
          documents: sidecar.data.documents.map((ref, index) => index === 0 ? { ...ref, path: item.path } : ref),
          bundledMembers: { [item.path]: sidecar.data.bundledMembers[documentPath], [assetPath]: sidecar.data.bundledMembers[assetPath] },
        }
        : {
          ...sidecar.data,
          localWorldId: worldId,
          assets: sidecar.data.assets.map((ref, index) => index === 0 ? { ...ref, path: item.path } : ref),
          bundledMembers: { [documentPath]: sidecar.data.bundledMembers[documentPath], [item.path]: sidecar.data.bundledMembers[assetPath] },
        };
      assert((await targetOpen.repository.restorePackage(malformedRecord, malformedData)).status === "error", `Direct IndexedDB restore accepted ${item.namespace} traversal path.`);
      assert((await targetOpen.repository.readWorld(worldId)).status === "missing", `Malformed ${item.namespace} path wrote a World record.`);
      assert((await targetOpen.repository.readPackageData(worldId)).status === "missing", `Malformed ${item.namespace} path wrote a package sidecar.`);
    }
    const aborted = await restoreStagedLocalWorldPackage(abortOpen.repository, decoded.parsed.candidate);
    assert(aborted.status === "error", "Injected quota-shaped abort unexpectedly committed.");
    assert((await abortOpen.repository.readWorld(layout.record.snapshot.worldId)).status === "missing", "World record survived a paired transaction abort.");
    assert((await abortOpen.repository.readPackageData(layout.record.snapshot.worldId)).status === "missing", "Supplemental record survived a paired transaction abort.");

    const malformed = indexedDB.open(malformedName, 2);
    malformed.addEventListener("upgradeneeded", () => {
      const db = malformed.result;
      const worlds = db.createObjectStore("worlds", { keyPath: "snapshot.worldId" });
      const conflicts = db.createObjectStore("conflicts", { keyPath: "wrongKey" });
      worlds.add(layout.record);
      conflicts.add({ wrongKey: "preserve", marker: "original malformed v2 data" });
    });
    const malformedDb = await requestResult(malformed);
    malformedDb.close();
    const refusal = await openIndexedDbLocalWorldRepository(malformedName);
    assert(refusal.status === "error" && refusal.code === "incompatible-schema", "Malformed v2 schema upgrade was not refused.");
    const preserved = await requestResult(indexedDB.open(malformedName));
    assert(preserved.version === 2 && preserved.objectStoreNames.contains("conflicts"), "Refused migration changed prior database version/schema.");
    const preservedMarker = await requestResult(preserved.transaction("conflicts", "readonly").objectStore("conflicts").get("preserve"));
    assert((preservedMarker as { marker?: string } | undefined)?.marker === "original malformed v2 data", "Refused migration changed the original malformed v2 record.");
    preserved.close();

    output.dataset.status = "passed";
    output.textContent = JSON.stringify({ status: "passed", runtime: "native browser IndexedDB/WebCrypto/ZIP", checks: ["edited repository record ZIP roundtrip", "atomic semantic record plus document/binary sidecar readback", "two-connection concurrent restore has one winner", "collision refusal", "direct invalid revision/history and document/asset traversal rejection before writes", "valid v2 migration preserves local record and unrelated store", "simulated transaction abort preserves empty state", "malformed v2 migration refuses while preserving v2 version and data"], archiveBytes: archive.blob.size, durability: "not a crash, quota-exhaustion, eviction, or cross-browser guarantee" });
  } finally {
    close.forEach((fn) => fn());
    for (const name of names) await deleteDb(name);
  }
}
void run().catch((error: unknown) => {
  const output = document.querySelector<HTMLElement>("#result");
  if (output) { output.dataset.status = "failed"; output.textContent = error instanceof Error ? `${error.name}: ${error.message}` : String(error); }
});
