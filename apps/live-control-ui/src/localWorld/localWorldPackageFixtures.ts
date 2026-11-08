import type { LocalWorldRecord, LocalWorldSnapshot } from "./localWorldRepository";

export function createPackageTestRecord(): LocalWorldRecord {
  const snapshot: LocalWorldSnapshot = {
    worldId: "local-world:package-fixture" as LocalWorldSnapshot["worldId"],
    title: "The Ember Coast",
    objects: [
      { id: "local-world:package-fixture:object:mara" as LocalWorldSnapshot["objects"][number]["id"], name: "Mara Venn", kind: "person", properties: { role: "traveler", tags: ["lead", "shore"] } },
      { id: "local-world:package-fixture:object:tomas" as LocalWorldSnapshot["objects"][number]["id"], name: "Tomas Reed", kind: "person", properties: { role: "traveler", attributes: { trusted: true } } },
      { id: "local-world:package-fixture:object:orchard" as LocalWorldSnapshot["objects"][number]["id"], name: "The Glass Orchard", kind: "location", properties: { region: "North Reach" } },
      { id: "local-world:package-fixture:object:accord" as LocalWorldSnapshot["objects"][number]["id"], name: "The Winter Accord", kind: "event", properties: { year: 412 } },
      { id: "local-world:package-fixture:object:lantern-east" as LocalWorldSnapshot["objects"][number]["id"], name: "The Lantern Keeper", kind: "person", properties: { home: "east" } },
      { id: "local-world:package-fixture:object:lantern-west" as LocalWorldSnapshot["objects"][number]["id"], name: "The Lantern Keeper", kind: "person", properties: { home: "west" } },
    ],
    relationships: [
      { id: "local-world:package-fixture:relationship:negotiated" as LocalWorldSnapshot["relationships"][number]["id"], fromObjectId: "local-world:package-fixture:object:mara" as LocalWorldSnapshot["objects"][number]["id"], toObjectId: "local-world:package-fixture:object:accord" as LocalWorldSnapshot["objects"][number]["id"], kind: "negotiated", properties: { outcome: "signed" } },
      { id: "local-world:package-fixture:relationship:protects" as LocalWorldSnapshot["relationships"][number]["id"], fromObjectId: "local-world:package-fixture:object:tomas" as LocalWorldSnapshot["objects"][number]["id"], toObjectId: "local-world:package-fixture:object:orchard" as LocalWorldSnapshot["objects"][number]["id"], kind: "protects", properties: { since: "winter" } },
    ],
  };
  return {
    snapshot,
    localRevision: 2,
    publishedRevisionId: null,
    layout: {
      positions: {
        "local-world:package-fixture:object:mara": { x: 10, y: 20 },
        "local-world:package-fixture:object:tomas": { x: 30, y: 40 },
        "local-world:package-fixture:object:orchard": { x: 50, y: 60 },
        "local-world:package-fixture:object:accord": { x: 70, y: 80 },
        "local-world:package-fixture:object:lantern-east": { x: 90, y: 100 },
        "local-world:package-fixture:object:lantern-west": { x: 110, y: 120 },
      },
      viewport: { x: -12, y: 5, zoom: 1.25 },
      layoutVersion: 3,
    },
    layoutRevision: 7,
    history: [
      { id: "local-edit:fixture-one" as LocalWorldRecord["history"][number]["id"], localRevision: 1, classification: "buddy-local-only", description: "Created the initial local cast." },
      { id: "local-edit:fixture-two" as LocalWorldRecord["history"][number]["id"], localRevision: 2, classification: "supported-semantic-intent", description: "Connected people and places." },
    ],
  };
}

export const packageFixtureAttachmentBytes = {
  document: new TextEncoder().encode("A locally authored source note, kept as opaque package bytes."),
  asset: new Uint8Array([0, 1, 2, 3, 250, 251, 252, 253, 254, 255]),
} as const;

type FixtureReference = {
  id: string;
  status: "bundled" | "external" | "missing";
  path: string | null;
  mediaType: string;
  locator: string | null;
};

function stable(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stable).join(",")}]`;
  if (value && typeof value === "object") {
    const object = value as Record<string, unknown>;
    return `{${Object.keys(object).sort().map((key) => `${JSON.stringify(key)}:${stable(object[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function digest(bytes: Uint8Array): Promise<string> {
  const buffer = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(buffer).set(bytes);
  const result = await crypto.subtle.digest("SHA-256", buffer);
  return Array.from(new Uint8Array(result), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

/** Build adversarial valid-v1 fixtures independently of the production encoder. */
export async function addPackageFixtureReferences(
  source: ReadonlyMap<string, Uint8Array>,
  references: { readonly documents?: readonly FixtureReference[]; readonly assets?: readonly FixtureReference[] },
  attachments: ReadonlyMap<string, Uint8Array> = new Map(),
  semanticChanges: Record<string, unknown> = {},
): Promise<Map<string, Uint8Array>> {
  const members = new Map([...source].map(([path, bytes]) => [path, new Uint8Array(bytes)]));
  const semantic = JSON.parse(new TextDecoder().decode(members.get("semantic.json"))) as Record<string, unknown>;
  const nextSemantic = { ...semantic, ...semanticChanges, documents: references.documents ?? semantic.documents, assets: references.assets ?? semantic.assets };
  members.set("semantic.json", new TextEncoder().encode(stable(nextSemantic)));
  for (const [path, bytes] of attachments) members.set(path, new Uint8Array(bytes));

  const descriptors = [] as Array<{ path: string; mediaType: string; sizeBytes: number; sha256: string }>;
  for (const [path, bytes] of members) {
    if (path === "manifest.json") continue;
    descriptors.push({
      path,
      mediaType: path.endsWith(".json") ? "application/json" : (references.documents ?? []).find((ref) => ref.path === path)?.mediaType
        ?? (references.assets ?? []).find((ref) => ref.path === path)?.mediaType ?? "application/octet-stream",
      sizeBytes: bytes.byteLength,
      sha256: await digest(bytes),
    });
  }
  descriptors.sort((a, b) => a.path.localeCompare(b.path));
  const attachmentPaths = [...(references.documents ?? []), ...(references.assets ?? [])]
    .filter((ref) => ref.status === "bundled")
    .map((ref) => ref.path!)
    .sort();
  const attachmentDigests = [] as Array<{ path: string; sha256: string }>;
  for (const path of attachmentPaths) attachmentDigests.push({ path, sha256: await digest(members.get(path)!) });
  const semanticDigest = await digest(new TextEncoder().encode(stable({ semantic: nextSemantic, attachments: attachmentDigests })));
  const count = (list: readonly FixtureReference[] = [], status: FixtureReference["status"]) => list.filter((ref) => ref.status === status).length;
  const baseManifest = JSON.parse(new TextDecoder().decode(members.get("manifest.json"))) as Record<string, unknown>;
  const manifest = {
    ...baseManifest,
    memberCount: descriptors.length + 1,
    payloadBytes: descriptors.reduce((sum, descriptor) => sum + descriptor.sizeBytes, 0),
    members: descriptors,
    semanticDigest,
    attachmentAvailability: {
      bundledDocuments: count(references.documents, "bundled"),
      externalDocuments: count(references.documents, "external"),
      missingDocuments: count(references.documents, "missing"),
      bundledAssets: count(references.assets, "bundled"),
      externalAssets: count(references.assets, "external"),
      missingAssets: count(references.assets, "missing"),
    },
  };
  members.set("manifest.json", new TextEncoder().encode(stable(manifest)));
  return members;
}
