// @vitest-environment node
import { BlobWriter, Uint8ArrayReader, ZipWriter } from "@zip.js/zip.js";
import { describe, expect, it } from "vitest";
import { encodeLocalWorldPackageV1, parseLocalWorldPackageV1 } from "./localWorldPackageV1";
import { addPackageFixtureReferences, createPackageTestRecord, packageFixtureAttachmentBytes } from "./localWorldPackageFixtures";
import { decodeLocalWorldPackageZipV1, encodeLocalWorldPackageZipV1, LOCAL_WORLD_PACKAGE_ZIP_V1 } from "./localWorldPackageZipV1";
import { createTestWorld, sequenceLocalIds } from "./localWorldContractFixtures";
import { InMemoryLocalWorldRepository } from "./inMemoryLocalWorldRepository";

async function membersWithAssets() {
  const core = await encodeLocalWorldPackageV1(createPackageTestRecord());
  if (core.status !== "encoded") throw new Error(core.message);
  const document = packageFixtureAttachmentBytes.document;
  const asset = packageFixtureAttachmentBytes.asset;
  const assetHash = await crypto.subtle.digest("SHA-256", asset);
  const assetName = Array.from(new Uint8Array(assetHash), (b) => b.toString(16).padStart(2, "0")).join("");
  return addPackageFixtureReferences(core.members, {
    documents: [{ id: "doc:opaque", status: "bundled", path: "documents/source.txt", mediaType: "text/plain", locator: null }],
    assets: [{ id: "asset:binary", status: "bundled", path: `assets/${assetName}`, mediaType: "application/octet-stream", locator: null }],
  }, new Map([["documents/source.txt", document], [`assets/${assetName}`, asset]]));
}

async function membersWithDocuments(paths: readonly string[]) {
  const core = await encodeLocalWorldPackageV1(createPackageTestRecord());
  if (core.status !== "encoded") throw new Error(core.message);
  const references = paths.map((path, index) => ({ id: `doc:${index}`, status: "bundled" as const, path, mediaType: "text/plain", locator: null }));
  const attachments = new Map(paths.map((path) => [path, new TextEncoder().encode(`Opaque document bytes for ${path}`)]));
  return addPackageFixtureReferences(core.members, { documents: references }, attachments);
}

async function writeZip(members: ReadonlyMap<string, Uint8Array>): Promise<Blob> {
  const writer = new BlobWriter("application/zip");
  const zip = new ZipWriter(writer, { zip64: false, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true, level: 0, useCompressionStream: false, useWebWorkers: false });
  for (const [path, bytes] of members) await zip.add(path, new Uint8ArrayReader(bytes), { compressionMethod: 0, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true });
  await zip.close();
  return writer.getData();
}

async function writeDeflatedEntry(path: string, data: Uint8Array): Promise<Blob> {
  const writer = new BlobWriter("application/zip");
  const zip = new ZipWriter(writer, { zip64: false, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true, level: 6, useWebWorkers: false });
  await zip.add(path, new Uint8ArrayReader(data), { compressionMethod: 8, dataDescriptor: false, extendedTimestamp: false, useUnicodeFileNames: true });
  await zip.close();
  return writer.getData();
}

async function mutateBlob(blob: Blob, mutate: (bytes: Uint8Array, view: DataView) => void): Promise<Blob> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  mutate(bytes, new DataView(bytes.buffer));
  return new Blob([bytes], { type: "application/zip" });
}

describe("bounded local World ZIP v1 transport", () => {
  it("round-trips a real repository-created snapshot through codec and ZIP", async () => {
    const repository = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const record = await createTestWorld(repository, "ZIP from repository");
    const core = await encodeLocalWorldPackageV1(record);
    expect(core.status).toBe("encoded");
    if (core.status !== "encoded") return;
    const archive = await encodeLocalWorldPackageZipV1(core.members);
    expect(archive.status, archive.status === "error" ? archive.message : "").toBe("encoded");
    if (archive.status !== "encoded") return;
    const decoded = await decodeLocalWorldPackageZipV1(archive.blob);
    expect(decoded.status).toBe("staged");
    if (decoded.status === "staged") expect(decoded.parsed.candidate.record).toEqual(record);
  });

  it("preserves opaque binary attachments and distinct same-name identities", async () => {
    const members = await membersWithAssets();
    const archive = await encodeLocalWorldPackageZipV1(members);
    expect(archive.status, archive.status === "error" ? archive.message : "").toBe("encoded");
    if (archive.status !== "encoded") return;
    const decoded = await decodeLocalWorldPackageZipV1(archive.blob);
    expect(decoded.status).toBe("staged");
    if (decoded.status !== "staged") return;
    expect([...decoded.parsed.candidate.members.keys()].sort()).toEqual([...members.keys()].sort());
    expect(decoded.parsed.candidate.members.get("documents/source.txt")).toEqual(packageFixtureAttachmentBytes.document);
    const assetPath = [...members.keys()].find((path) => path.startsWith("assets/"))!;
    expect(decoded.parsed.candidate.members.get(assetPath)).toEqual(packageFixtureAttachmentBytes.asset);
    expect(decoded.parsed.candidate.record.snapshot.objects.filter((item) => item.name === "The Lantern Keeper")).toHaveLength(2);
  });

  it("round-trips valid Unicode paths and refuses UTF-8 byte overflow or portable collisions before writing", async () => {
    const validPath = "documents/café-notes.txt";
    const validMembers = await membersWithDocuments([validPath]);
    const validArchive = await encodeLocalWorldPackageZipV1(validMembers);
    expect(validArchive.status).toBe("encoded");
    if (validArchive.status !== "encoded") return;
    const validDecoded = await decodeLocalWorldPackageZipV1(validArchive.blob);
    expect(validDecoded.status).toBe("staged");
    if (validDecoded.status === "staged") expect(validDecoded.parsed.candidate.members.get(validPath)).toEqual(validMembers.get(validPath));

    const oversizedPath = `documents/${"é".repeat(130)}`;
    const oversizedMembers = await membersWithDocuments([oversizedPath]);
    expect((await parseLocalWorldPackageV1(oversizedMembers)).status).toBe("error");
    const oversizedExport = await encodeLocalWorldPackageZipV1(oversizedMembers);
    expect(oversizedExport.status).toBe("error");
    expect((await decodeLocalWorldPackageZipV1(await writeZip(new Map([[oversizedPath, new Uint8Array([1])]])))).status).toBe("error");
    const illFormedUnicode = await membersWithDocuments(["documents/\ud800.txt"]);
    expect((await parseLocalWorldPackageV1(illFormedUnicode)).status).toBe("error");
    expect((await encodeLocalWorldPackageZipV1(illFormedUnicode)).status).toBe("error");
    const trailingHighSurrogate = await membersWithDocuments(["documents/file\ud800"]);
    expect((await parseLocalWorldPackageV1(trailingHighSurrogate)).status).toBe("error");

    const collidingPaths = ["documents/Name.txt", "documents/name.txt"];
    const collidingMembers = await membersWithDocuments(collidingPaths);
    expect((await parseLocalWorldPackageV1(collidingMembers)).status).toBe("error");
    const collidingExport = await encodeLocalWorldPackageZipV1(collidingMembers);
    expect(collidingExport.status).toBe("error");
    expect((await decodeLocalWorldPackageZipV1(await writeZip(new Map(collidingPaths.map((path) => [path, new Uint8Array([1])]))))).status).toBe("error");
  });

  it("captures caller bytes synchronously before asynchronous ZIP work", async () => {
    const members = await membersWithAssets();
    const original = new Uint8Array(members.get("documents/source.txt")!);
    const pending = encodeLocalWorldPackageZipV1(members);
    members.get("documents/source.txt")!.fill(0x58);
    const archive = await pending;
    expect(archive.status, archive.status === "error" ? archive.message : "").toBe("encoded");
    if (archive.status !== "encoded") return;
    const decoded = await decodeLocalWorldPackageZipV1(archive.blob);
    expect(decoded.status).toBe("staged");
    if (decoded.status === "staged") expect(decoded.parsed.candidate.members.get("documents/source.txt")).toEqual(original);
  });

  it("rejects encrypted flags and declared ZIP64 expansion before inflation", async () => {
    const members = await membersWithAssets();
    const archive = await writeZip(members);
    const encrypted = await mutateBlob(archive, (bytes, view) => {
      const central = bytes.findIndex((_, i) => i + 4 < bytes.length && view.getUint32(i, true) === 0x02014b50);
      view.setUint16(central + 8, view.getUint16(central + 8, true) | 1, true);
    });
    expect((await decodeLocalWorldPackageZipV1(encrypted)).status).toBe("error");
    const zip64 = await mutateBlob(archive, (bytes, view) => {
      const central = bytes.findIndex((_, i) => i + 4 < bytes.length && view.getUint32(i, true) === 0x02014b50);
      view.setUint32(central + 24, 0xffff_ffff, true);
    });
    const rejected = await decodeLocalWorldPackageZipV1(zip64);
    expect(rejected.status).toBe("error");
    if (rejected.status === "error") expect(rejected.code).toBe("invalid-archive");
    const storedFlags = await mutateBlob(archive, (bytes, view) => {
      const central = bytes.findIndex((_, i) => i + 4 < bytes.length && view.getUint32(i, true) === 0x02014b50);
      const local = view.getUint32(central + 42, true);
      view.setUint16(central + 8, view.getUint16(central + 8, true) | 2, true);
      view.setUint16(local + 6, view.getUint16(local + 6, true) | 2, true);
    });
    expect((await decodeLocalWorldPackageZipV1(storedFlags)).status).toBe("error");
  });

  it("rejects traversal paths and case-colliding package members", async () => {
    const members = await membersWithAssets();
    const archive = await encodeLocalWorldPackageZipV1(members);
    expect(archive.status).toBe("encoded");
    if (archive.status !== "encoded") return;
    const traversal = await mutateBlob(archive.blob, (bytes, view) => {
      let central = -1;
      for (let i = 0; i + 4 < bytes.length; i += 1) {
        if (view.getUint32(i, true) === 0x02014b50 && new TextDecoder().decode(bytes.slice(i + 46, i + 46 + view.getUint16(i + 28, true))) === "manifest.json") { central = i; break; }
      }
      const local = view.getUint32(central + 42, true);
      const name = new TextEncoder().encode("../ifest.json");
      bytes.set(name, central + 46);
      bytes.set(name, local + 30);
    });
    expect((await decodeLocalWorldPackageZipV1(traversal)).status).toBe("error");
    const collision = await writeZip(new Map([
      ["documents/Name.txt", new Uint8Array([1])],
      ["documents/name.txt", new Uint8Array([2])],
    ]));
    expect((await decodeLocalWorldPackageZipV1(collision)).status).toBe("error");
  });

  it("rejects archive-size excess and invalid package payloads without repository writes", async () => {
    const oversized = new Blob([new Uint8Array(LOCAL_WORLD_PACKAGE_ZIP_V1.maxArchiveBytes + 1)]);
    expect((await decodeLocalWorldPackageZipV1(oversized)).status).toBe("error");
    const archive = await writeZip(new Map([["manifest.json", new TextEncoder().encode(JSON.stringify({ kind: "dungeonmindbuddy.local-world-package", version: 99 }))]]));
    const result = await decodeLocalWorldPackageZipV1(archive);
    expect(result.status).toBe("error");
    if (result.status === "error") expect(result.code).toBe("unsupported-version");
    const unrecognizedPath = await writeZip(new Map([["notes.txt", new TextEncoder().encode("not a package path")]]));
    expect((await decodeLocalWorldPackageZipV1(unrecognizedPath)).status).toBe("error");
  });

  it("rejects deflate output that contradicts the declared expansion", async () => {
    const expanded = new Uint8Array(5 * 1024 * 1024).fill(0x41);
    const archive = await writeDeflatedEntry("semantic.json", expanded);
    const declaredOversize = await decodeLocalWorldPackageZipV1(archive);
    expect(declaredOversize.status).toBe("error");
    if (declaredOversize.status === "error") expect(declaredOversize.code).toBe("limit-exceeded");
    const understated = await mutateBlob(archive, (bytes, view) => {
      const central = bytes.findIndex((_, i) => i + 4 < bytes.length && view.getUint32(i, true) === 0x02014b50);
      const local = view.getUint32(central + 42, true);
      // Metadata remains just inside the allowed per-member ceiling; actual streamed output crosses it.
      view.setUint32(central + 24, 4 * 1024 * 1024 - 1, true);
      view.setUint32(local + 22, 4 * 1024 * 1024 - 1, true);
    });
    const result = await decodeLocalWorldPackageZipV1(understated);
    expect(result.status).toBe("error");
    if (result.status === "error") expect(result.code).toBe("invalid-archive");
  });
});
