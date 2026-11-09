// @vitest-environment jsdom
import { describe, expect, it, vi } from "vitest";
import { InMemoryLocalWorldRepository } from "./inMemoryLocalWorldRepository";
import {
  encodeLocalWorldPackageV1,
  LOCAL_WORLD_PACKAGE_V1,
  parseLocalWorldPackageV1,
} from "./localWorldPackageV1";
import {
  addPackageFixtureReferences,
  createPackageTestRecord,
  packageFixtureAttachmentBytes,
} from "./localWorldPackageFixtures";
import type { LocalWorldRecord } from "./localWorldRepository";
import { createTestWorld, sequenceLocalIds } from "./localWorldContractFixtures";

const encoder = new TextEncoder();
const decoder = new TextDecoder();

function jsonMember(members: ReadonlyMap<string, Uint8Array>, path: string): Record<string, unknown> {
  return JSON.parse(decoder.decode(members.get(path))) as Record<string, unknown>;
}

function replaceJsonMember(members: ReadonlyMap<string, Uint8Array>, path: string, value: unknown): Map<string, Uint8Array> {
  const next = new Map([...members].map(([memberPath, bytes]) => [memberPath, new Uint8Array(bytes)]));
  next.set(path, encoder.encode(JSON.stringify(value)));
  return next;
}

async function hash(bytes: Uint8Array): Promise<string> {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  const result = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function encodedFixture(record = createPackageTestRecord()): Promise<Map<string, Uint8Array>> {
  const result = await encodeLocalWorldPackageV1(record);
  if (result.status !== "encoded") throw new Error(result.message);
  return new Map(result.members);
}

describe("normalized local World package v1 core", () => {
  it("round-trips the repository-created revision-zero seed and subsequent semantic/layout edits", async () => {
    const repository = new InMemoryLocalWorldRepository({ idFactory: sequenceLocalIds() });
    const seed = await createTestWorld(repository, "Repository seed");
    expect(seed.localRevision).toBe(0);
    expect(seed.history[0]).toMatchObject({ localRevision: 0, description: "Created local World draft" });

    const encodedSeed = await encodeLocalWorldPackageV1(seed);
    expect(encodedSeed.status).toBe("encoded");
    if (encodedSeed.status !== "encoded") return;
    const parsedSeed = await parseLocalWorldPackageV1(encodedSeed.members);
    expect(parsedSeed.status).toBe("staged");
    if (parsedSeed.status !== "staged") return;
    expect(parsedSeed.candidate.record).toEqual(seed);

    const edited = await repository.commitSemanticEdit({
      worldId: seed.snapshot.worldId,
      expectedLocalRevision: seed.localRevision,
      nextSnapshot: { ...seed.snapshot, title: "Repository-edited World" },
      edit: { classification: "buddy-local-only", description: "Updated the local title" },
    });
    expect(edited.status).toBe("committed");
    if (edited.status !== "committed") return;
    const laidOut = await repository.writeLayout({
      worldId: seed.snapshot.worldId,
      expectedLayoutRevision: edited.record.layoutRevision,
      nextLayout: { ...edited.record.layout, viewport: { ...edited.record.layout.viewport, x: 18 } },
    });
    expect(laidOut.status).toBe("written");
    if (laidOut.status !== "written") return;

    const encodedUpdated = await encodeLocalWorldPackageV1(laidOut.record);
    expect(encodedUpdated.status).toBe("encoded");
    if (encodedUpdated.status !== "encoded") return;
    const parsedUpdated = await parseLocalWorldPackageV1(encodedUpdated.members);
    expect(parsedUpdated.status).toBe("staged");
    if (parsedUpdated.status === "staged") expect(parsedUpdated.candidate.record).toEqual(laidOut.record);
  });

  it("round-trips semantic identities, same-name objects, layout, history and honest limitations", async () => {
    const record = createPackageTestRecord();
    const encoded = await encodeLocalWorldPackageV1(record);
    expect(encoded.status).toBe("encoded");
    if (encoded.status !== "encoded") return;

    const parsed = await parseLocalWorldPackageV1(encoded.members);
    expect(parsed.status).toBe("staged");
    if (parsed.status !== "staged") return;
    expect(parsed.candidate.record).toEqual(record);
    expect(parsed.candidate.record.snapshot.objects.filter((node) => node.name === "The Lantern Keeper").map((node) => node.id))
      .toEqual(["local-world:package-fixture:object:lantern-east", "local-world:package-fixture:object:lantern-west"]);
    expect(parsed.candidate.record.snapshot.relationships.map((edge) => edge.fromObjectId)).toEqual([
      "local-world:package-fixture:object:mara", "local-world:package-fixture:object:tomas",
    ]);
    expect(parsed.candidate.manifest.fidelity).toEqual({
      localRecord: "preserved",
      sourceMetadata: "not-represented-by-local-record",
      profileMetadata: "not-represented-by-local-record",
    });
    expect(parsed.candidate.manifest.creatorProfileAssumptions).toEqual({ creator: "not-recorded", profile: "not-recorded" });
    expect(parsed.candidate.manifest.historyCoverage).toMatchObject({ status: "included", entryCount: 2, completeness: "unknown" });
  });

  it("re-exports a restored 2 MiB binary attachment using attachment limits, not the JSON member limit", async () => {
    const repository = new InMemoryLocalWorldRepository();
    const record = createPackageTestRecord();
    const pathBytes = new Uint8Array(2 * 1024 * 1024);
    for (let index = 0; index < pathBytes.length; index += 1) pathBytes[index] = index % 251;
    const digest = await hash(pathBytes);
    const path = `assets/${digest}`;
    const data = {
      localWorldId: record.snapshot.worldId,
      documents: [],
      assets: [{ id: "asset:large-restored", status: "bundled" as const, path, mediaType: "application/octet-stream", locator: null }],
      bundledMembers: { [path]: Array.from(pathBytes) },
      fidelity: { localRecord: "preserved" as const, sourceMetadata: "not-represented-by-local-record" as const, profileMetadata: "not-represented-by-local-record" as const },
      creatorProfileAssumptions: { creator: "not-recorded" as const, profile: "not-recorded" as const },
    };
    expect((await repository.restorePackage(record, data)).status).toBe("restored");
    const sidecar = await repository.readPackageData(record.snapshot.worldId);
    expect(sidecar.status).toBe("found");
    if (sidecar.status !== "found") return;

    const encoded = await encodeLocalWorldPackageV1(record, sidecar.data);
    expect(encoded.status).toBe("encoded");
    if (encoded.status !== "encoded") return;
    expect(encoded.members.get(path)?.byteLength).toBe(pathBytes.byteLength);
    const parsed = await parseLocalWorldPackageV1(encoded.members);
    expect(parsed.status).toBe("staged");
    if (parsed.status !== "staged") return;
    expect(parsed.candidate.assets).toEqual(data.assets);
    expect(parsed.candidate.members.get(path)).toEqual(pathBytes);
    expect(parsed.candidate.manifest.fidelity).toEqual(data.fidelity);
    expect(parsed.candidate.manifest.creatorProfileAssumptions).toEqual(data.creatorProfileAssumptions);
  }, 30_000);

  it("refuses an attachment over its byte limit before cloning caller-owned data", async () => {
    const record = createPackageTestRecord();
    const path = `documents/${"a".repeat(32)}.bin`;
    const sidecar = {
      localWorldId: record.snapshot.worldId,
      documents: [{ id: "doc:oversized", status: "bundled" as const, path, mediaType: "application/octet-stream", locator: null }],
      assets: [],
      bundledMembers: { [path]: new Array(LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes + 1) },
      fidelity: { localRecord: "preserved" as const, sourceMetadata: "not-represented-by-local-record" as const, profileMetadata: "not-represented-by-local-record" as const },
      creatorProfileAssumptions: { creator: "not-recorded" as const, profile: "not-recorded" as const },
    };
    const clone = vi.spyOn(globalThis, "structuredClone");
    const result = await encodeLocalWorldPackageV1(record, sidecar);
    expect(result.status).toBe("error");
    if (result.status === "error") expect(result.code).toBe("limit-exceeded");
    expect(clone).not.toHaveBeenCalled();
    clone.mockRestore();
  });

  it("declares empty history as omitted without claiming complete provenance", async () => {
    const record = createPackageTestRecord();
    record.history = [];
    const encoded = await encodeLocalWorldPackageV1(record);
    expect(encoded.status).toBe("encoded");
    if (encoded.status !== "encoded") return;
    expect(encoded.members.has("history.json")).toBe(false);
    expect(jsonMember(encoded.members, "manifest.json").historyCoverage).toEqual({
      status: "omitted", entryCount: 0, firstLocalRevision: null, lastLocalRevision: null, completeness: "unknown",
    });
    const parsed = await parseLocalWorldPackageV1(encoded.members);
    expect(parsed.status).toBe("staged");
    if (parsed.status === "staged") expect(parsed.candidate.record.history).toEqual([]);
  });

  it("has deterministic semantic digests and keeps layout outside semantic meaning", async () => {
    const first = createPackageTestRecord();
    const second = structuredClone(first);
    second.layout.viewport.x = 900;
    second.layout.positions["local-world:package-fixture:object:mara"].x = -44;
    const [a, b, repeat] = await Promise.all([
      encodeLocalWorldPackageV1(first),
      encodeLocalWorldPackageV1(second),
      encodeLocalWorldPackageV1(first),
    ]);
    expect(a.status).toBe("encoded");
    expect(b.status).toBe("encoded");
    expect(repeat.status).toBe("encoded");
    if (a.status !== "encoded" || b.status !== "encoded" || repeat.status !== "encoded") return;
    expect(jsonMember(a.members, "manifest.json").semanticDigest).toBe(jsonMember(b.members, "manifest.json").semanticDigest);
    expect(jsonMember(a.members, "manifest.json").semanticDigest).toBe(jsonMember(repeat.members, "manifest.json").semanticDigest);
    expect(a.members.get("layout.json")).not.toEqual(b.members.get("layout.json"));
    const reversed = new Map([...a.members].reverse());
    const parsed = await parseLocalWorldPackageV1(reversed);
    expect(parsed.status).toBe("staged");
  });

  it("captures mutable record and member bytes synchronously before digest awaits", async () => {
    const record = structuredClone(createPackageTestRecord());
    const pendingEncode = encodeLocalWorldPackageV1(record);
    record.snapshot.title = "Changed after call";
    record.localRevision = 88;
    record.layout.viewport.x = 444;
    record.history[0].description = "Changed after call";
    const encoded = await pendingEncode;
    expect(encoded.status).toBe("encoded");
    if (encoded.status !== "encoded") return;
    expect(jsonMember(encoded.members, "semantic.json").snapshot).toMatchObject({ title: "The Ember Coast" });
    expect(jsonMember(encoded.members, "semantic.json").localRevision).toBe(2);
    expect(jsonMember(encoded.members, "layout.json").layout.viewport).toMatchObject({ x: -12 });
    expect(JSON.parse(decoder.decode(encoded.members.get("history.json"))).at(0).description).toBe("Created the initial local cast.");

    const mutableBytes = new Map([...encoded.members].map(([path, bytes]) => [path, new Uint8Array(bytes)]));
    const semantic = mutableBytes.get("semantic.json")!;
    const pendingParse = parseLocalWorldPackageV1(mutableBytes);
    semantic.fill(0);
    mutableBytes.clear();
    const parsed = await pendingParse;
    expect(parsed.status).toBe("staged");
    if (parsed.status === "staged") expect(parsed.candidate.record.snapshot.title).toBe("The Ember Coast");
  });

  it("preserves declared bundled, external and missing attachments without fetching", async () => {
    const base = await encodedFixture();
    const assetBytes = packageFixtureAttachmentBytes.asset;
    const assetDigest = await hash(assetBytes);
    const documentPath = "documents/source-notes/primary.txt";
    const assetPath = `assets/${assetDigest}`;
    const documentRef = { id: "doc:primary", status: "bundled" as const, path: documentPath, mediaType: "text/plain", locator: null };
    const externalRef = { id: "doc:remote", status: "external" as const, path: null, mediaType: "text/markdown", locator: "https://example.invalid/lore.md" };
    const missingAsset = { id: "asset:missing", status: "missing" as const, path: null, mediaType: "image/png", locator: null };
    const packageMembers = await addPackageFixtureReferences(
      base,
      { documents: [documentRef, externalRef], assets: [missingAsset] },
      new Map([[documentPath, packageFixtureAttachmentBytes.document]]),
    );
    const withBundledAsset = await addPackageFixtureReferences(
      packageMembers,
      { documents: [documentRef, externalRef], assets: [{ id: "asset:bundle", status: "bundled", path: assetPath, mediaType: "application/octet-stream", locator: null }, missingAsset] },
      new Map([[documentPath, packageFixtureAttachmentBytes.document], [assetPath, assetBytes]]),
    );

    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const parsed = await parseLocalWorldPackageV1(withBundledAsset);
    vi.unstubAllGlobals();
    expect(parsed.status).toBe("staged");
    if (parsed.status !== "staged") return;
    expect(parsed.candidate.documents).toEqual([documentRef, externalRef]);
    expect(parsed.candidate.assets).toEqual([
      { id: "asset:bundle", status: "bundled", path: assetPath, mediaType: "application/octet-stream", locator: null },
      missingAsset,
    ]);
    expect(Array.from(parsed.candidate.members.get(assetPath)!)).toEqual(Array.from(assetBytes));
    expect(Array.from(parsed.candidate.members.get(documentPath)!)).toEqual(Array.from(packageFixtureAttachmentBytes.document));
    expect(fetch).not.toHaveBeenCalled();
    expect(parsed.candidate.manifest.attachmentAvailability).toEqual({
      bundledDocuments: 1, externalDocuments: 1, missingDocuments: 0,
      bundledAssets: 1, externalAssets: 0, missingAssets: 1,
    });
  });

  it("changes the semantic digest for semantic or bundled source-byte changes", async () => {
    const base = await encodedFixture();
    const path = "documents/source-note.txt";
    const reference = { id: "doc:source", status: "bundled" as const, path, mediaType: "text/plain", locator: null };
    const originalBytes = encoder.encode("Exact original source text.");
    const updatedBytes = encoder.encode("Exact updated source text.");
    const original = await addPackageFixtureReferences(base, { documents: [reference], assets: [] }, new Map([[path, originalBytes]]));
    const updatedSource = await addPackageFixtureReferences(base, { documents: [reference], assets: [] }, new Map([[path, updatedBytes]]));
    const changedMeaning = await addPackageFixtureReferences(
      base,
      { documents: [reference], assets: [] },
      new Map([[path, originalBytes]]),
      { snapshot: { ...(jsonMember(base, "semantic.json").snapshot as object), title: "Changed semantic meaning" } },
    );
    expect(jsonMember(original, "manifest.json").semanticDigest).not.toBe(jsonMember(updatedSource, "manifest.json").semanticDigest);
    expect(jsonMember(original, "manifest.json").semanticDigest).not.toBe(jsonMember(changedMeaning, "manifest.json").semanticDigest);
    expect((await parseLocalWorldPackageV1(original)).status).toBe("staged");
    expect((await parseLocalWorldPackageV1(updatedSource)).status).toBe("staged");
    const mutatedDocument = new Map(original);
    mutatedDocument.set(path, encoder.encode("Tampered source bytes."));
    expect(await parseLocalWorldPackageV1(mutatedDocument)).toMatchObject({ status: "error", code: "invalid-package" });
  });

  it("rejects unsafe paths, malformed or unknown manifests, inaccurate sizes and digests", async () => {
    const members = await encodedFixture();
    const badUtf8 = new Map([["manifest.json", new Uint8Array([0xff, 0xfe])]]);
    expect(await parseLocalWorldPackageV1(badUtf8)).toMatchObject({ status: "error", code: "invalid-package" });

    const invalidSemantic = new Map(members);
    const badSemanticBytes = new Uint8Array([0xff]);
    const badManifest = jsonMember(members, "manifest.json");
    const badSemanticDigest = await hash(badSemanticBytes);
    const badDescriptors = (badManifest.members as Array<Record<string, unknown>>).map((entry) => entry.path === "semantic.json"
      ? { ...entry, sizeBytes: badSemanticBytes.byteLength, sha256: badSemanticDigest }
      : entry);
    invalidSemantic.set("semantic.json", badSemanticBytes);
    invalidSemantic.set("manifest.json", encoder.encode(JSON.stringify({
      ...badManifest,
      members: badDescriptors,
      payloadBytes: badDescriptors.reduce((sum, entry) => sum + Number(entry.sizeBytes), 0),
    })));
    expect(await parseLocalWorldPackageV1(invalidSemantic)).toMatchObject({ status: "error", code: "invalid-package" });

    const unsupported = replaceJsonMember(members, "manifest.json", { ...jsonMember(members, "manifest.json"), version: 2 });
    expect(await parseLocalWorldPackageV1(unsupported)).toMatchObject({ status: "error", code: "unsupported-version" });

    const unsafe = new Map(members);
    unsafe.set("documents/../secret.txt", encoder.encode("secret"));
    expect(await parseLocalWorldPackageV1(unsafe)).toMatchObject({ status: "error", code: "invalid-package" });
    for (const path of ["/absolute.txt", "documents//empty.txt", "documents/a\\b.txt", "documents/./x.txt", "documents/../x.txt", "documents/C:/drive.txt", "documents/control\u0001.txt"]) {
      const unsafePath = new Map(members);
      unsafePath.set(path, encoder.encode("x"));
      expect(await parseLocalWorldPackageV1(unsafePath)).toMatchObject({ status: "error", code: "invalid-package" });
    }
    const nonNormalizedUnicode = new Map(members);
    nonNormalizedUnicode.set("documents/cafe\u0301.txt", encoder.encode("x"));
    expect(await parseLocalWorldPackageV1(nonNormalizedUnicode)).toMatchObject({ status: "error", code: "invalid-package" });

    const manifest = jsonMember(members, "manifest.json");
    const descriptor = (manifest.members as Array<Record<string, unknown>>).find((entry) => entry.path === "semantic.json")!;
    const wrongSize = replaceJsonMember(members, "manifest.json", {
      ...manifest,
      members: (manifest.members as Array<Record<string, unknown>>).map((entry) => entry.path === "semantic.json" ? { ...entry, sizeBytes: Number(entry.sizeBytes) + 1 } : entry),
    });
    expect(await parseLocalWorldPackageV1(wrongSize)).toMatchObject({ status: "error", code: "invalid-package" });
    const wrongDigest = replaceJsonMember(members, "manifest.json", {
      ...manifest,
      members: (manifest.members as Array<Record<string, unknown>>).map((entry) => entry.path === "semantic.json" ? { ...entry, sha256: "0".repeat(64) } : entry),
    });
    expect(await parseLocalWorldPackageV1(wrongDigest)).toMatchObject({ status: "error", code: "invalid-package" });
    expect(descriptor.sizeBytes).toBe((members.get("semantic.json") ?? new Uint8Array()).byteLength);
  });

  it("accepts member paths at the declared boundary and rejects longer or deeper paths", async () => {
    const base = await encodedFixture();
    const maxLengthPath = `documents/${"a".repeat(246)}`;
    const maxLengthPackage = await addPackageFixtureReferences(
      base,
      { documents: [{ id: "doc:max-path", status: "bundled", path: maxLengthPath, mediaType: "text/plain", locator: null }] },
      new Map([[maxLengthPath, encoder.encode("ok")]]),
    );
    expect((await parseLocalWorldPackageV1(maxLengthPackage)).status).toBe("staged");

    const maxSegmentsPath = `documents/${Array.from({ length: 15 }, () => "part").join("/")}`;
    const maxSegmentsPackage = await addPackageFixtureReferences(
      base,
      { documents: [{ id: "doc:max-depth", status: "bundled", path: maxSegmentsPath, mediaType: "text/plain", locator: null }] },
      new Map([[maxSegmentsPath, encoder.encode("ok")]]),
    );
    expect((await parseLocalWorldPackageV1(maxSegmentsPackage)).status).toBe("staged");

    for (const path of [`documents/${"a".repeat(247)}`, `documents/${Array.from({ length: 16 }, () => "part").join("/")}`]) {
      const invalid = new Map(base);
      invalid.set(path, encoder.encode("too long or deep"));
      expect(await parseLocalWorldPackageV1(invalid)).toMatchObject({ status: "error", code: "invalid-package" });
    }
  });

  it("enforces byte, member, depth, object, relationship and history bounds without truncation", async () => {
    const tooManyMembers = new Map<string, Uint8Array>();
    for (let index = 0; index < LOCAL_WORLD_PACKAGE_V1.limits.memberCount + 1; index += 1) tooManyMembers.set(`member-${index}`, new Uint8Array());
    expect(await parseLocalWorldPackageV1(tooManyMembers)).toMatchObject({ status: "error", code: "limit-exceeded" });
    expect(await parseLocalWorldPackageV1(new Map([["manifest.json", new Uint8Array(LOCAL_WORLD_PACKAGE_V1.limits.totalBytes + 1)]])))
      .toMatchObject({ status: "error", code: "limit-exceeded" });
    const base = await encodedFixture();
    const baseManifest = jsonMember(base, "manifest.json");
    const firstDescriptor = (baseManifest.members as Array<Record<string, unknown>>)[0];
    const oversizedInventory = replaceJsonMember(base, "manifest.json", {
      ...baseManifest,
      memberCount: 3,
      members: Array.from({ length: LOCAL_WORLD_PACKAGE_V1.limits.memberCount }, () => firstDescriptor),
    });
    expect(await parseLocalWorldPackageV1(oversizedInventory)).toMatchObject({ status: "error", code: "limit-exceeded" });
    const manyReferences = Array.from({ length: LOCAL_WORLD_PACKAGE_V1.limits.referenceCount + 1 }, (_, index) => ({
      id: `external:${index}`, status: "external" as const, path: null, mediaType: "text/plain", locator: `ref:${index}`,
    }));
    const tooManyReferences = await addPackageFixtureReferences(base, { documents: manyReferences, assets: [] });
    expect(await parseLocalWorldPackageV1(tooManyReferences)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const oversizedJson = await encodedFixture();
    oversizedJson.set("semantic.json", new Uint8Array(LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes + 1));
    expect(await parseLocalWorldPackageV1(oversizedJson)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const oversizedAttachment = await encodedFixture();
    oversizedAttachment.set(`assets/${"a".repeat(64)}`, new Uint8Array(LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes + 1));
    expect(await parseLocalWorldPackageV1(oversizedAttachment)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const deepRecord = createPackageTestRecord();
    let nested: Record<string, unknown> = {};
    const root = nested;
    for (let index = 0; index < LOCAL_WORLD_PACKAGE_V1.limits.jsonDepth + 2; index += 1) {
      const child: Record<string, unknown> = {};
      nested.next = child;
      nested = child;
    }
    (deepRecord.snapshot.objects[0].properties as Record<string, unknown>).deep = root;
    expect(await encodeLocalWorldPackageV1(deepRecord)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const tooManyObjects = createPackageTestRecord();
    const object = tooManyObjects.snapshot.objects[0];
    tooManyObjects.snapshot.objects = Array.from({ length: LOCAL_WORLD_PACKAGE_V1.limits.objectCount + 1 }, (_, index) => ({ ...object, id: `local-world:package-fixture:object:${index}` as typeof object.id }));
    tooManyObjects.snapshot.relationships = [];
    tooManyObjects.layout.positions = {};
    expect(await encodeLocalWorldPackageV1(tooManyObjects)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const tooManyRelationships = createPackageTestRecord();
    const relationship = tooManyRelationships.snapshot.relationships[0];
    tooManyRelationships.snapshot.relationships = Array.from({ length: LOCAL_WORLD_PACKAGE_V1.limits.relationshipCount + 1 }, (_, index) => ({ ...relationship, id: `local-world:package-fixture:relationship:${index}` as typeof relationship.id }));
    expect(await encodeLocalWorldPackageV1(tooManyRelationships)).toMatchObject({ status: "error", code: "limit-exceeded" });

    const tooMuchHistory = createPackageTestRecord();
    const entry = tooMuchHistory.history[0];
    tooMuchHistory.localRevision = LOCAL_WORLD_PACKAGE_V1.limits.historyCount + 1;
    tooMuchHistory.history = Array.from({ length: LOCAL_WORLD_PACKAGE_V1.limits.historyCount + 1 }, (_, index) => ({ ...entry, id: `local-edit:${index}` as typeof entry.id, localRevision: index + 1 }));
    expect(await encodeLocalWorldPackageV1(tooMuchHistory)).toMatchObject({ status: "error", code: "limit-exceeded" });
  });

  it("rejects duplicate IDs, dangling references, unknown schema fields and unreferenced attachments", async () => {
    const record = createPackageTestRecord();
    const duplicate = structuredClone(record);
    duplicate.snapshot.objects[1].id = duplicate.snapshot.objects[0].id;
    expect(await encodeLocalWorldPackageV1(duplicate)).toMatchObject({ status: "error", code: "invalid-record" });

    const duplicateRelationship = structuredClone(record);
    duplicateRelationship.snapshot.relationships[1].id = duplicateRelationship.snapshot.relationships[0].id;
    expect(await encodeLocalWorldPackageV1(duplicateRelationship)).toMatchObject({ status: "error", code: "invalid-record" });

    const dangling = structuredClone(record);
    dangling.snapshot.relationships[0].toObjectId = "local-world:package-fixture:object:absent" as typeof dangling.snapshot.objects[number]["id"];
    expect(await encodeLocalWorldPackageV1(dangling)).toMatchObject({ status: "error", code: "invalid-record" });

    const base = await encodedFixture();
    const semantic = jsonMember(base, "semantic.json");
    const brokenRelationships = structuredClone(semantic.snapshot as Record<string, unknown>);
    const relationships = brokenRelationships.relationships as Array<Record<string, unknown>>;
    relationships[0].toObjectId = "local-world:package-fixture:object:absent";
    const invalidReference = await addPackageFixtureReferences(base, {}, new Map(), { snapshot: brokenRelationships });
    const invalidReferenceResult = await parseLocalWorldPackageV1(invalidReference);
    if (invalidReferenceResult.status === "error") expect(invalidReferenceResult.code).toBe("invalid-record");
    else expect(invalidReferenceResult.status).toBe("error");

    const unknownField = await addPackageFixtureReferences(base, {}, new Map(), { futureField: true });
    expect(await parseLocalWorldPackageV1(unknownField)).toMatchObject({ status: "error", code: "invalid-package" });

    const orphanBytes = encoder.encode("orphan");
    const orphan = await addPackageFixtureReferences(base, {}, new Map([["documents/orphan.txt", orphanBytes]]));
    expect(await parseLocalWorldPackageV1(orphan)).toMatchObject({ status: "error", code: "invalid-package" });
  });

  it("refuses hidden top-level data and non-index numeric array properties instead of dropping them", async () => {
    const hiddenField = createPackageTestRecord();
    Object.defineProperty(hiddenField, "sourceMetadata", { value: { document: "must-not-disappear" }, enumerable: false });
    expect(await encodeLocalWorldPackageV1(hiddenField)).toMatchObject({ status: "error" });

    const namedArrayProperty = createPackageTestRecord();
    Object.defineProperty(namedArrayProperty.snapshot.objects[0].properties.tags as unknown[], "4294967295", {
      value: "must-not-disappear",
      enumerable: true,
    });
    expect(await encodeLocalWorldPackageV1(namedArrayProperty)).toMatchObject({ status: "error" });
  });

  it("keeps staged results isolated from both input buffers and package members", async () => {
    const members = await encodedFixture();
    const parsed = await parseLocalWorldPackageV1(members);
    expect(parsed.status).toBe("staged");
    if (parsed.status !== "staged") return;
    const sourceSemantic = members.get("semantic.json")!;
    const stagedSemantic = parsed.candidate.members.get("semantic.json")!;
    stagedSemantic.fill(0);
    (parsed.candidate.record.snapshot as { title: string }).title = "mutated staged output";
    expect(sourceSemantic.some((byte) => byte !== 0)).toBe(true);
    expect(JSON.parse(decoder.decode(members.get("semantic.json"))).snapshot.title).toBe("The Ember Coast");
  });
});
