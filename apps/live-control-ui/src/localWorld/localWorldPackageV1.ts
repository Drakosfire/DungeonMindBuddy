import { cloneLocalWorldValue, validateLocalWorldSnapshot } from "./localWorldRepository";
import type {
  LocalWorldHistoryEntry,
  LocalWorldId,
  LocalWorldLayout,
  LocalWorldRecord,
  LocalWorldSnapshot,
} from "./localWorldRepository";

export const LOCAL_WORLD_PACKAGE_V1 = {
  kind: "dungeonmindbuddy.local-world-package",
  version: 1,
  limits: {
    totalBytes: 16 * 1024 * 1024,
    memberCount: 256,
    referenceCount: 256,
    jsonMemberBytes: 4 * 1024 * 1024,
    attachmentBytes: 8 * 1024 * 1024,
    objectCount: 5_000,
    relationshipCount: 10_000,
    historyCount: 1_000,
    jsonDepth: 64,
  },
} as const;

export interface LocalWorldPackageMemberDescriptor {
  readonly path: string;
  readonly mediaType: string;
  readonly sizeBytes: number;
  readonly sha256: string;
}

export type LocalWorldPackageReferenceStatus = "bundled" | "external" | "missing";

/** A package attachment is preserved in staged parsing but is not a LocalWorldRecord field. */
export interface LocalWorldPackageReference {
  readonly id: string;
  readonly status: LocalWorldPackageReferenceStatus;
  readonly path: string | null;
  readonly mediaType: string;
  /** Informational locator only. The codec never navigates to or fetches it. */
  readonly locator: string | null;
}

export interface LocalWorldPackageManifestV1 {
  readonly kind: typeof LOCAL_WORLD_PACKAGE_V1.kind;
  readonly version: 1;
  readonly memberCount: number;
  /** Sum of all members other than manifest.json. */
  readonly payloadBytes: number;
  readonly members: readonly LocalWorldPackageMemberDescriptor[];
  readonly semanticDigest: string;
  readonly historyCoverage: {
    readonly status: "included" | "omitted";
    readonly entryCount: number;
    readonly firstLocalRevision: number | null;
    readonly lastLocalRevision: number | null;
    readonly completeness: "unknown";
  };
  readonly attachmentAvailability: {
    readonly bundledDocuments: number;
    readonly externalDocuments: number;
    readonly missingDocuments: number;
    readonly bundledAssets: number;
    readonly externalAssets: number;
    readonly missingAssets: number;
  };
  readonly fidelity: {
    readonly localRecord: "preserved";
    readonly sourceMetadata: "not-represented-by-local-record";
    readonly profileMetadata: "not-represented-by-local-record";
  };
  readonly creatorProfileAssumptions: {
    readonly creator: "not-recorded";
    readonly profile: "not-recorded";
  };
}

export interface LocalWorldPackageSemanticV1 {
  readonly localWorldId: LocalWorldId;
  readonly localRevision: number;
  readonly publishedRevisionId: string | null;
  readonly snapshot: LocalWorldSnapshot;
  readonly documents: readonly LocalWorldPackageReference[];
  readonly assets: readonly LocalWorldPackageReference[];
}

export interface StagedLocalWorldPackageV1 {
  readonly manifest: LocalWorldPackageManifestV1;
  readonly record: LocalWorldRecord;
  /** Extra typed package refs and their member bytes remain staged, never silently dropped. */
  readonly documents: readonly LocalWorldPackageReference[];
  readonly assets: readonly LocalWorldPackageReference[];
  readonly members: ReadonlyMap<string, Uint8Array>;
}

export type LocalWorldPackageErrorCode =
  | "invalid-record"
  | "invalid-package"
  | "unsupported-version"
  | "unsupported-member"
  | "limit-exceeded"
  | "digest-unavailable";

export type EncodeLocalWorldPackageV1Result =
  | { readonly status: "encoded"; readonly members: ReadonlyMap<string, Uint8Array> }
  | { readonly status: "error"; readonly code: LocalWorldPackageErrorCode; readonly message: string };

export type ParseLocalWorldPackageV1Result =
  | { readonly status: "staged"; readonly candidate: StagedLocalWorldPackageV1 }
  | { readonly status: "error"; readonly code: LocalWorldPackageErrorCode; readonly message: string };

const MANIFEST_PATH = "manifest.json";
const SEMANTIC_PATH = "semantic.json";
const LAYOUT_PATH = "layout.json";
const HISTORY_PATH = "history.json";
const JSON_MEDIA_TYPE = "application/json";
const SHA256_PATTERN = /^[0-9a-f]{64}$/;
const MEDIA_TYPE_PATTERN = /^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+$/i;
const encoder = new TextEncoder();

interface PackageSemanticWire extends LocalWorldPackageSemanticV1 {}
interface PackageLayoutWire {
  readonly layoutRevision: number;
  readonly layout: LocalWorldLayout;
}

class PackageProblem extends Error {
  constructor(readonly code: LocalWorldPackageErrorCode, message: string) {
    super(message);
  }
}

function fail(code: LocalWorldPackageErrorCode, message: string): never {
  throw new PackageProblem(code, message);
}

function objectRecord(value: unknown, label: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    fail("invalid-package", `${label} must be a JSON object.`);
  }
  return value as Record<string, unknown>;
}

function exactKeys(value: Record<string, unknown>, expected: readonly string[], label: string): void {
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) fail("invalid-package", `${label} must be a plain JSON object.`);
  if (Object.getOwnPropertySymbols(value).length > 0) fail("invalid-package", `${label} cannot contain symbol fields.`);
  // Include hidden own string properties in the schema check. Object.keys()
  // would silently miss non-enumerable source/provenance fields during export.
  const actual = Object.getOwnPropertyNames(value).sort();
  const wanted = [...expected].sort();
  if (actual.length !== wanted.length || actual.some((key, index) => key !== wanted[index])) {
    fail("invalid-package", `${label} has unsupported or missing fields.`);
  }
  const descriptors = Object.getOwnPropertyDescriptors(value);
  for (const key of actual) {
    const descriptor = descriptors[key];
    if (!descriptor.enumerable || !("value" in descriptor)) fail("invalid-package", `${label} cannot contain hidden fields or accessors.`);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isInteger(value: unknown, minimum = 0): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum;
}

function jsonStringByteLength(value: string, stopAfter: number): number {
  let bytes = 2;
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code === 0x22 || code === 0x5c) bytes += 2;
    else if (code <= 0x1f) bytes += 6;
    else if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (next >= 0xdc00 && next <= 0xdfff) {
        bytes += 4;
        index += 1;
      } else bytes += 6;
    } else if (code >= 0xdc00 && code <= 0xdfff) bytes += 6;
    else if (code <= 0x7f) bytes += 1;
    else if (code <= 0x7ff) bytes += 2;
    else bytes += 3;
    if (bytes > stopAfter) return bytes;
  }
  return bytes;
}

/** Serialize JSON canonically while enforcing a byte/depth bound during traversal. */
function canonicalJson(value: unknown, maxBytes = LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes): string {
  let byteCount = 0;
  const ancestors = new Set<object>();
  const parts: string[] = [];
  const append = (text: string, knownBytes?: number) => {
    byteCount += knownBytes ?? text.length;
    if (byteCount > maxBytes) fail("limit-exceeded", "A JSON member exceeds the 4 MiB member limit.");
    parts.push(text);
  };
  const visit = (item: unknown, depth: number): void => {
    if (depth > LOCAL_WORLD_PACKAGE_V1.limits.jsonDepth) fail("limit-exceeded", "JSON nesting exceeds the depth limit of 64.");
    if (item === null) return append("null");
    if (typeof item === "boolean") return append(item ? "true" : "false");
    if (typeof item === "number") {
      if (!Number.isFinite(item)) fail("invalid-package", "JSON numbers must be finite.");
      return append(JSON.stringify(item));
    }
    if (typeof item === "string") {
      const size = jsonStringByteLength(item, maxBytes - byteCount);
      if (size > maxBytes - byteCount) fail("limit-exceeded", "A JSON member exceeds the 4 MiB member limit.");
      return append(JSON.stringify(item), size);
    }
    if (typeof item !== "object") fail("invalid-package", "The package contains a non-JSON value.");
    if (ancestors.has(item)) fail("invalid-package", "Cyclic values are not valid package JSON.");
    if (Object.getOwnPropertySymbols(item).length > 0) fail("invalid-package", "Symbol properties are not supported package data.");
    ancestors.add(item);
    if (Array.isArray(item)) {
      const descriptors = Object.getOwnPropertyDescriptors(item);
      for (const key of Object.getOwnPropertyNames(item)) {
        if (key === "length") continue;
        if (!/^(0|[1-9]\d*)$/.test(key)) fail("invalid-package", "JSON arrays cannot contain named properties.");
        const index = Number(key);
        if (!Number.isSafeInteger(index) || index >= item.length || index > 0xffff_fffe) {
          fail("invalid-package", "JSON arrays cannot contain non-index numeric properties.");
        }
      }
      append("[");
      for (let index = 0; index < item.length; index += 1) {
        const descriptor = descriptors[String(index)];
        if (!descriptor || !descriptor.enumerable || !("value" in descriptor)) fail("invalid-package", "JSON arrays cannot contain holes or accessors.");
        if (index > 0) append(",");
        visit(descriptor.value, depth + 1);
      }
      append("]");
    } else {
      const prototype = Object.getPrototypeOf(item);
      if (prototype !== Object.prototype && prototype !== null) fail("invalid-package", "Package JSON objects must be plain objects.");
      const descriptors = Object.getOwnPropertyDescriptors(item);
      const keys = Object.keys(descriptors).sort();
      append("{");
      keys.forEach((key, index) => {
        const descriptor = descriptors[key];
        if (!descriptor.enumerable || !("value" in descriptor)) fail("invalid-package", "Package JSON cannot contain accessors or hidden fields.");
        if (index > 0) append(",");
        visit(key, depth + 1);
        append(":");
        visit(descriptor.value, depth + 1);
      });
      append("}");
    }
    ancestors.delete(item);
  };
  visit(value, 0);
  return parts.join("");
}

function encodeJson(value: unknown): Uint8Array {
  return encoder.encode(canonicalJson(value));
}

function decodeJson(bytes: Uint8Array, label: string): unknown {
  if (bytes.byteLength > LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes) {
    fail("limit-exceeded", `${label} exceeds the 4 MiB JSON member limit.`);
  }
  try {
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return JSON.parse(text) as unknown;
  } catch {
    fail("invalid-package", `${label} is not valid UTF-8 JSON.`);
  }
}

async function sha256(bytes: Uint8Array): Promise<string> {
  const subtle = globalThis.crypto?.subtle;
  if (!subtle) fail("digest-unavailable", "SHA-256 is unavailable in this environment.");
  const digestInput = new ArrayBuffer(bytes.byteLength);
  new Uint8Array(digestInput).set(bytes);
  const digest = await subtle.digest("SHA-256", digestInput);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function validateLayout(layout: unknown, snapshot: LocalWorldSnapshot, revision: unknown): asserts revision is number {
  if (!isInteger(revision)) fail("invalid-record", "Layout revision must be a non-negative integer.");
  const record = objectRecord(layout, "layout");
  exactKeys(record, ["positions", "viewport", "layoutVersion"], "layout");
  if (!isInteger(record.layoutVersion)) fail("invalid-record", "Layout version must be a non-negative integer.");
  const viewport = objectRecord(record.viewport, "layout viewport");
  exactKeys(viewport, ["x", "y", "zoom"], "layout viewport");
  if (![viewport.x, viewport.y, viewport.zoom].every((value) => typeof value === "number" && Number.isFinite(value)) || (viewport.zoom as number) <= 0) {
    fail("invalid-record", "Layout viewport coordinates must be finite and zoom must be positive.");
  }
  const positions = objectRecord(record.positions, "layout positions");
  const objectIds = new Set(snapshot.objects.map((object) => object.id));
  for (const [id, pointValue] of Object.entries(positions)) {
    if (!objectIds.has(id as LocalWorldSnapshot["objects"][number]["id"])) {
      fail("invalid-record", "Layout contains a position for an unknown local object ID.");
    }
    const point = objectRecord(pointValue, "layout position");
    exactKeys(point, ["x", "y"], "layout position");
    if (![point.x, point.y].every((value) => typeof value === "number" && Number.isFinite(value))) {
      fail("invalid-record", "Layout position coordinates must be finite.");
    }
  }
}

function validateSnapshot(snapshotValue: unknown, worldId: unknown): LocalWorldSnapshot {
  const snapshot = objectRecord(snapshotValue, "semantic snapshot");
  exactKeys(snapshot, ["worldId", "title", "objects", "relationships"], "semantic snapshot");
  if (typeof snapshot.worldId !== "string" || typeof snapshot.title !== "string" || !Array.isArray(snapshot.objects) || !Array.isArray(snapshot.relationships)) {
    fail("invalid-record", "Semantic snapshot fields have invalid types.");
  }
  if (snapshot.objects.length > LOCAL_WORLD_PACKAGE_V1.limits.objectCount) fail("limit-exceeded", "World exceeds the 5,000 object limit.");
  if (snapshot.relationships.length > LOCAL_WORLD_PACKAGE_V1.limits.relationshipCount) fail("limit-exceeded", "World exceeds the 10,000 relationship limit.");
  const localSnapshot = snapshotValue as LocalWorldSnapshot;
  if (typeof worldId !== "string" || !worldId.startsWith("local-world:") || localSnapshot.worldId !== worldId) {
    fail("invalid-record", "A local World identity must use its Buddy-local namespace and match the semantic snapshot.");
  }
  const error = validateLocalWorldSnapshot(localSnapshot, localSnapshot.worldId);
  if (error) fail("invalid-record", error);
  for (const object of localSnapshot.objects) {
    exactKeys(object as unknown as Record<string, unknown>, ["id", "name", "kind", "properties"], "semantic object");
    if (!object || typeof object.id !== "string" || !object.id.startsWith(`${worldId}:object:`) || typeof object.name !== "string" || typeof object.kind !== "string" || !isRecord(object.properties)) {
      fail("invalid-record", "A semantic object has invalid fields.");
    }
  }
  for (const relationship of localSnapshot.relationships) {
    exactKeys(relationship as unknown as Record<string, unknown>, ["id", "fromObjectId", "toObjectId", "kind", "properties"], "semantic relationship");
    if (!relationship || typeof relationship.id !== "string" || !relationship.id.startsWith(`${worldId}:relationship:`) || typeof relationship.kind !== "string" || !isRecord(relationship.properties)) {
      fail("invalid-record", "A semantic relationship has invalid fields.");
    }
  }
  return localSnapshot;
}

function validateHistory(value: unknown, localRevision: number): readonly LocalWorldHistoryEntry[] {
  if (!Array.isArray(value)) fail("invalid-record", "History must be an array.");
  if (value.length > LOCAL_WORLD_PACKAGE_V1.limits.historyCount) fail("limit-exceeded", "History exceeds the 1,000 entry package limit.");
  const ids = new Set<string>();
  // Repository-created Worlds start at semantic revision 0 and carry a seed
  // history event at that same revision. Later history entries remain strict.
  let previousRevision = -1;
  for (const entryValue of value) {
    const entry = objectRecord(entryValue, "history entry");
    exactKeys(entry, ["id", "localRevision", "classification", "description"], "history entry");
    if (typeof entry.id !== "string" || !entry.id.startsWith("local-edit:") || ids.has(entry.id)) fail("invalid-record", "History contains an invalid or duplicate local edit ID.");
    if (!isInteger(entry.localRevision) || entry.localRevision > localRevision || entry.localRevision <= previousRevision) {
      fail("invalid-record", "History revisions must be increasing and no greater than the local revision.");
    }
    if (entry.classification !== "supported-semantic-intent" && entry.classification !== "buddy-local-only") {
      fail("invalid-record", "History contains an unsupported classification.");
    }
    if (typeof entry.description !== "string") fail("invalid-record", "History description must be a string.");
    ids.add(entry.id);
    previousRevision = entry.localRevision;
  }
  return value as readonly LocalWorldHistoryEntry[];
}

function validateRecord(record: LocalWorldRecord): void {
  if (!isRecord(record)) fail("invalid-record", "Local World record must be an object.");
  exactKeys(record as unknown as Record<string, unknown>, ["snapshot", "localRevision", "publishedRevisionId", "layout", "layoutRevision", "history"], "local World record");
  if (!isInteger(record.localRevision) || !isInteger(record.layoutRevision)) fail("invalid-record", "World revisions must be non-negative safe integers.");
  if (record.publishedRevisionId !== null && (typeof record.publishedRevisionId !== "string" || !record.publishedRevisionId)) {
    fail("invalid-record", "Published revision identity must be null or a non-empty verified ID.");
  }
  const snapshot = validateSnapshot(record.snapshot, record.snapshot?.worldId);
  validateLayout(record.layout, snapshot, record.layoutRevision);
  validateHistory(record.history, record.localRevision);
}

export function isLocalWorldPackageMemberPath(path: string): boolean {
  if (!path || path.length > 256 || path.startsWith("/") || path.includes("\\") || /[\u0000-\u001f\u007f]/.test(path) || path !== path.normalize("NFC")) return false;
  const segments = path.split("/");
  if (segments.length > 16 || segments.some((segment) => !segment || segment === "." || segment === ".." || segment.includes(":"))) return false;
  if (path === SEMANTIC_PATH || path === LAYOUT_PATH || path === HISTORY_PATH) return true;
  if (path.startsWith("documents/")) return segments.length >= 2 && segments.slice(1).every((part) => part !== "");
  if (path.startsWith("assets/")) return segments.length === 2 && SHA256_PATTERN.test(segments[1]);
  return false;
}

function validateMediaType(value: unknown): value is string {
  return typeof value === "string" && MEDIA_TYPE_PATTERN.test(value);
}

function validateReferences(value: unknown, expectedKind: "documents" | "assets"): readonly LocalWorldPackageReference[] {
  if (!Array.isArray(value)) fail("invalid-package", `${expectedKind} references must be an array.`);
  const ids = new Set<string>();
  return value.map((entryValue) => {
    const entry = objectRecord(entryValue, `${expectedKind} reference`);
    exactKeys(entry, ["id", "status", "path", "mediaType", "locator"], `${expectedKind} reference`);
    if (typeof entry.id !== "string" || !entry.id || ids.has(entry.id)) fail("invalid-package", `${expectedKind} reference IDs must be unique non-empty strings.`);
    if (entry.status !== "bundled" && entry.status !== "external" && entry.status !== "missing") fail("invalid-package", `${expectedKind} reference has an unknown availability status.`);
    if (!validateMediaType(entry.mediaType)) fail("invalid-package", `${expectedKind} reference has an invalid media type.`);
    if (entry.locator !== null && typeof entry.locator !== "string") fail("invalid-package", `${expectedKind} locator must be text or null.`);
    if (entry.status === "bundled") {
      if (typeof entry.path !== "string" || !isLocalWorldPackageMemberPath(entry.path) || !entry.path.startsWith(`${expectedKind}/`)) {
        fail("invalid-package", `Bundled ${expectedKind} need a safe in-package path.`);
      }
    } else if (entry.path !== null) fail("invalid-package", `External or missing ${expectedKind} cannot point at a bundled member.`);
    ids.add(entry.id);
    return entry as unknown as LocalWorldPackageReference;
  });
}

function expectedAvailability(documents: readonly LocalWorldPackageReference[], assets: readonly LocalWorldPackageReference[]) {
  const count = (refs: readonly LocalWorldPackageReference[], status: LocalWorldPackageReferenceStatus) => refs.filter((ref) => ref.status === status).length;
  return {
    bundledDocuments: count(documents, "bundled"),
    externalDocuments: count(documents, "external"),
    missingDocuments: count(documents, "missing"),
    bundledAssets: count(assets, "bundled"),
    externalAssets: count(assets, "external"),
    missingAssets: count(assets, "missing"),
  };
}

async function semanticDigest(semantic: PackageSemanticWire, members: ReadonlyMap<string, Uint8Array>): Promise<string> {
  const bundledPaths = [...semantic.documents, ...semantic.assets]
    .filter((reference) => reference.status === "bundled")
    .map((reference) => reference.path!)
    .sort();
  const attachmentDigests = [] as Array<{ path: string; sha256: string }>;
  for (const path of bundledPaths) {
    const bytes = members.get(path);
    if (!bytes) fail("invalid-package", `Bundled reference is missing its member: ${path}`);
    attachmentDigests.push({ path, sha256: await sha256(bytes) });
  }
  const semanticCanonical = JSON.parse(canonicalJson(semantic)) as unknown;
  const digestInput = canonicalJson(
    { semantic: semanticCanonical, attachments: attachmentDigests },
    LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes + 128 * 1024,
  );
  return sha256(encoder.encode(digestInput));
}

function manifestFromUnknown(value: unknown): LocalWorldPackageManifestV1 {
  const manifest = objectRecord(value, "manifest");
  if (manifest.kind !== LOCAL_WORLD_PACKAGE_V1.kind) fail("invalid-package", "Package kind is unsupported.");
  if (manifest.version !== 1) fail("unsupported-version", "Only package version 1 is supported.");
  exactKeys(manifest, ["kind", "version", "memberCount", "payloadBytes", "members", "semanticDigest", "historyCoverage", "attachmentAvailability", "fidelity", "creatorProfileAssumptions"], "manifest");
  if (!isInteger(manifest.memberCount, 1) || manifest.memberCount > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "Package member count exceeds 256.");
  if (!isInteger(manifest.payloadBytes) || typeof manifest.semanticDigest !== "string" || !SHA256_PATTERN.test(manifest.semanticDigest)) fail("invalid-package", "Manifest byte count or semantic digest is invalid.");
  if (!Array.isArray(manifest.members)) fail("invalid-package", "Manifest members must be an array.");
  if (manifest.members.length + 1 > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "Manifest inventory exceeds the 256 member limit.");
  if (manifest.members.length + 1 !== manifest.memberCount) fail("invalid-package", "Manifest member count does not match its inventory length.");
  const history = objectRecord(manifest.historyCoverage, "history coverage");
  exactKeys(history, ["status", "entryCount", "firstLocalRevision", "lastLocalRevision", "completeness"], "history coverage");
  if ((history.status !== "included" && history.status !== "omitted") || !isInteger(history.entryCount) || history.completeness !== "unknown") fail("invalid-package", "History coverage metadata is invalid.");
  if (history.status === "included" && history.entryCount < 1) fail("invalid-package", "Empty history must be declared omitted.");
  if (history.status === "omitted" && history.entryCount !== 0) fail("invalid-package", "Omitted history cannot declare entries.");
  const attachmentAvailability = objectRecord(manifest.attachmentAvailability, "attachment availability");
  exactKeys(attachmentAvailability, ["bundledDocuments", "externalDocuments", "missingDocuments", "bundledAssets", "externalAssets", "missingAssets"], "attachment availability");
  for (const valueCount of Object.values(attachmentAvailability)) if (!isInteger(valueCount)) fail("invalid-package", "Attachment counts must be non-negative integers.");
  const fidelity = objectRecord(manifest.fidelity, "fidelity metadata");
  exactKeys(fidelity, ["localRecord", "sourceMetadata", "profileMetadata"], "fidelity metadata");
  if (fidelity.localRecord !== "preserved" || fidelity.sourceMetadata !== "not-represented-by-local-record" || fidelity.profileMetadata !== "not-represented-by-local-record") {
    fail("invalid-package", "Package fidelity declarations are unsupported or misleading.");
  }
  const creatorProfileAssumptions = objectRecord(manifest.creatorProfileAssumptions, "creator/profile assumptions");
  exactKeys(creatorProfileAssumptions, ["creator", "profile"], "creator/profile assumptions");
  if (creatorProfileAssumptions.creator !== "not-recorded" || creatorProfileAssumptions.profile !== "not-recorded") fail("invalid-package", "Creator/profile assumptions must remain explicitly unrecorded.");
  const descriptors = manifest.members.map((entry) => {
    const descriptor = objectRecord(entry, "member descriptor");
    exactKeys(descriptor, ["path", "mediaType", "sizeBytes", "sha256"], "member descriptor");
    if (typeof descriptor.path !== "string" || !isLocalWorldPackageMemberPath(descriptor.path) || descriptor.path === MANIFEST_PATH) fail("invalid-package", "Member path is unsafe or unsupported.");
    if (!validateMediaType(descriptor.mediaType) || !isInteger(descriptor.sizeBytes, 1) || typeof descriptor.sha256 !== "string" || !SHA256_PATTERN.test(descriptor.sha256)) {
      fail("invalid-package", `Member descriptor is invalid: ${descriptor.path}`);
    }
    const isJson = descriptor.path === SEMANTIC_PATH || descriptor.path === LAYOUT_PATH || descriptor.path === HISTORY_PATH;
    const maxSize = isJson ? LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes : LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes;
    if (descriptor.sizeBytes > maxSize) fail("limit-exceeded", `Member exceeds its declared size limit: ${descriptor.path}`);
    if (isJson && descriptor.mediaType !== JSON_MEDIA_TYPE) fail("invalid-package", `JSON member has the wrong media type: ${descriptor.path}`);
    return descriptor as unknown as LocalWorldPackageMemberDescriptor;
  });
  const paths = descriptors.map((descriptor) => descriptor.path);
  if (new Set(paths).size !== paths.length) fail("invalid-package", "Manifest contains duplicate normalized member paths.");
  if (paths.length + 1 !== manifest.memberCount) fail("invalid-package", "Manifest member count does not match its member inventory.");
  if (!paths.includes(SEMANTIC_PATH) || !paths.includes(LAYOUT_PATH)) fail("invalid-package", "Package lacks a required semantic or layout member.");
  if ((history.status === "included") !== paths.includes(HISTORY_PATH)) fail("invalid-package", "History member and coverage declaration disagree.");
  return manifest as unknown as LocalWorldPackageManifestV1;
}

/**
 * Encode the fields represented by LocalWorldRecord into a normalized package
 * member map. This is not a ZIP writer or a complete portable package exporter.
 */
export async function encodeLocalWorldPackageV1(record: LocalWorldRecord): Promise<EncodeLocalWorldPackageV1Result> {
  try {
    validateRecord(record);
  } catch (error) {
    const problem = error instanceof PackageProblem ? error : new PackageProblem("invalid-record", "Local World record cannot be encoded.");
    return { status: "error", code: problem.code, message: problem.message };
  }
  try {
    const semantic: PackageSemanticWire = {
      localWorldId: record.snapshot.worldId,
      localRevision: record.localRevision,
      publishedRevisionId: record.publishedRevisionId,
      snapshot: record.snapshot,
      documents: [],
      assets: [],
    };
    const members = new Map<string, Uint8Array>();
    const semanticBytes = encodeJson(semantic);
    const semanticSnapshot = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(semanticBytes)) as PackageSemanticWire;
    const layoutBytes = encodeJson({ layoutRevision: record.layoutRevision, layout: record.layout } satisfies PackageLayoutWire);
    if (record.history.length > LOCAL_WORLD_PACKAGE_V1.limits.historyCount) fail("limit-exceeded", "History exceeds the 1,000 entry package limit.");
    const historyBytes = record.history.length > 0 ? encodeJson(record.history) : null;
    const capturedHistory = historyBytes
      ? JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(historyBytes)) as readonly LocalWorldHistoryEntry[]
      : [];
    members.set(SEMANTIC_PATH, semanticBytes);
    members.set(LAYOUT_PATH, layoutBytes);
    if (historyBytes) members.set(HISTORY_PATH, historyBytes);
    const descriptors: LocalWorldPackageMemberDescriptor[] = [];
    for (const [path, bytes] of members) {
      descriptors.push({ path, mediaType: JSON_MEDIA_TYPE, sizeBytes: bytes.byteLength, sha256: await sha256(bytes) });
    }
    descriptors.sort((left, right) => left.path < right.path ? -1 : left.path > right.path ? 1 : 0);
    const manifest: LocalWorldPackageManifestV1 = {
      kind: LOCAL_WORLD_PACKAGE_V1.kind,
      version: 1,
      memberCount: descriptors.length + 1,
      payloadBytes: descriptors.reduce((sum, descriptor) => sum + descriptor.sizeBytes, 0),
      members: descriptors,
      semanticDigest: await semanticDigest(semanticSnapshot, members),
      historyCoverage: capturedHistory.length > 0
        ? {
          status: "included",
          entryCount: capturedHistory.length,
          firstLocalRevision: capturedHistory[0].localRevision,
          lastLocalRevision: capturedHistory[capturedHistory.length - 1].localRevision,
          completeness: "unknown",
        }
        : { status: "omitted", entryCount: 0, firstLocalRevision: null, lastLocalRevision: null, completeness: "unknown" },
      attachmentAvailability: expectedAvailability([], []),
      fidelity: {
        localRecord: "preserved",
        sourceMetadata: "not-represented-by-local-record",
        profileMetadata: "not-represented-by-local-record",
      },
      creatorProfileAssumptions: { creator: "not-recorded", profile: "not-recorded" },
    };
    const manifestBytes = encodeJson(manifest);
    members.set(MANIFEST_PATH, manifestBytes);
    if (members.size > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "Package exceeds the 256 member limit.");
    const total = [...members.values()].reduce((sum, bytes) => sum + bytes.byteLength, 0);
    if (total > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) fail("limit-exceeded", "Package exceeds the 16 MiB total byte limit.");
    return { status: "encoded", members };
  } catch (error) {
    const problem = error instanceof PackageProblem ? error : new PackageProblem("invalid-record", "Local World package encoding failed.");
    return { status: "error", code: problem.code, message: problem.message };
  }
}

function validateSemanticWire(value: unknown): PackageSemanticWire {
  const semantic = objectRecord(value, "semantic member");
  exactKeys(semantic, ["localWorldId", "localRevision", "publishedRevisionId", "snapshot", "documents", "assets"], "semantic member");
  if (typeof semantic.localWorldId !== "string" || !isInteger(semantic.localRevision)) fail("invalid-package", "Local World identity/revision is invalid.");
  if (semantic.publishedRevisionId !== null && (typeof semantic.publishedRevisionId !== "string" || !semantic.publishedRevisionId)) fail("invalid-package", "Published revision ID must be null or non-empty text.");
  const snapshot = validateSnapshot(semantic.snapshot, semantic.localWorldId);
  if (!Array.isArray(semantic.documents) || !Array.isArray(semantic.assets)) fail("invalid-package", "Attachment references must be arrays.");
  if (semantic.documents.length + semantic.assets.length > LOCAL_WORLD_PACKAGE_V1.limits.referenceCount) fail("limit-exceeded", "Package exceeds the 256 attachment-reference limit.");
  const documents = validateReferences(semantic.documents, "documents");
  const assets = validateReferences(semantic.assets, "assets");
  return { localWorldId: semantic.localWorldId as LocalWorldId, localRevision: semantic.localRevision, publishedRevisionId: semantic.publishedRevisionId as string | null, snapshot, documents, assets };
}

function validateLayoutWire(value: unknown, snapshot: LocalWorldSnapshot): PackageLayoutWire {
  const layoutWire = objectRecord(value, "layout member");
  exactKeys(layoutWire, ["layoutRevision", "layout"], "layout member");
  validateLayout(layoutWire.layout, snapshot, layoutWire.layoutRevision);
  return layoutWire as unknown as PackageLayoutWire;
}

function validateHistoryCoverage(manifest: LocalWorldPackageManifestV1, history: readonly LocalWorldHistoryEntry[]): void {
  const coverage = manifest.historyCoverage;
  if (coverage.entryCount !== history.length) fail("invalid-package", "History coverage count does not match the stored history.");
  if (history.length === 0) {
    if (coverage.status !== "omitted" || coverage.firstLocalRevision !== null || coverage.lastLocalRevision !== null) fail("invalid-package", "Empty history coverage is malformed.");
  } else if (coverage.status !== "included" || coverage.firstLocalRevision !== history[0].localRevision || coverage.lastLocalRevision !== history[history.length - 1].localRevision) {
    fail("invalid-package", "History coverage range does not match included entries.");
  }
}

function validateAttachmentMembers(
  semantic: PackageSemanticWire,
  memberMap: ReadonlyMap<string, Uint8Array>,
  descriptors: readonly LocalWorldPackageMemberDescriptor[],
): void {
  const declared = new Map(descriptors.map((descriptor) => [descriptor.path, descriptor]));
  const references = [...semantic.documents, ...semantic.assets].filter((reference) => reference.status === "bundled");
  const referencedPaths = new Set(references.map((reference) => reference.path!));
  for (const reference of references) {
    const path = reference.path!;
    const bytes = memberMap.get(path);
    const descriptor = declared.get(path);
    if (!bytes || !descriptor) fail("invalid-package", `Bundled attachment is missing from the package: ${path}`);
    if (descriptor.mediaType !== reference.mediaType) fail("invalid-package", `Attachment media type disagrees with its reference: ${path}`);
    if (path.startsWith("assets/") && path.slice("assets/".length) !== descriptor.sha256) fail("invalid-package", `Asset path does not match its SHA-256 digest: ${path}`);
  }
  for (const path of declared.keys()) {
    if ((path.startsWith("documents/") || path.startsWith("assets/")) && !referencedPaths.has(path)) {
      fail("invalid-package", `Unreferenced attachment would be silently ignored: ${path}`);
    }
  }
}

/** Parse and validate a normalized member map. This performs no repository mutation. */
export async function parseLocalWorldPackageV1(inputMembers: ReadonlyMap<string, Uint8Array>): Promise<ParseLocalWorldPackageV1Result> {
  let capturedEntries: Array<[string, Uint8Array]>;
  try {
    // Preflight advertised count/path/byte bounds before copying any member buffers.
    const inputEntries = [...inputMembers];
    if (inputEntries.length > LOCAL_WORLD_PACKAGE_V1.limits.memberCount) fail("limit-exceeded", "Package exceeds the 256 member limit.");
    let advertisedBytes = 0;
    for (const [path, bytes] of inputEntries) {
      if (!ArrayBuffer.isView(bytes) || Object.prototype.toString.call(bytes) !== "[object Uint8Array]") {
        fail("invalid-package", "Package members must be Uint8Array values.");
      }
      const byteView = bytes as Uint8Array;
      if (typeof path !== "string" || (path !== MANIFEST_PATH && !isLocalWorldPackageMemberPath(path))) fail("invalid-package", `Unsafe or unsupported member path: ${path}`);
      const isJson = path === MANIFEST_PATH || path === SEMANTIC_PATH || path === LAYOUT_PATH || path === HISTORY_PATH;
      const maxSize = isJson ? LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes : LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes;
      if (byteView.byteLength > maxSize) fail("limit-exceeded", `Member exceeds its size limit: ${path}`);
      advertisedBytes += byteView.byteLength;
      if (advertisedBytes > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) fail("limit-exceeded", "Package exceeds the 16 MiB total byte limit.");
    }
    // No await occurred: copy now, so later caller mutation cannot change parsing.
    capturedEntries = inputEntries.map(([path, bytes]) => [path, new Uint8Array(bytes as Uint8Array)]);
  } catch (error) {
    const problem = error instanceof PackageProblem ? error : new PackageProblem("invalid-package", "Package members could not be captured.");
    return { status: "error", code: problem.code, message: problem.message };
  }
  try {
    if (new Set(capturedEntries.map(([path]) => path)).size !== capturedEntries.length) fail("invalid-package", "Package has duplicate member paths.");
    for (const [path, bytes] of capturedEntries) {
      if (path !== MANIFEST_PATH && !isLocalWorldPackageMemberPath(path)) fail("invalid-package", `Unsafe or unsupported member path: ${path}`);
      if (path !== MANIFEST_PATH && !path.startsWith("documents/") && !path.startsWith("assets/") && bytes.byteLength > LOCAL_WORLD_PACKAGE_V1.limits.jsonMemberBytes) {
        fail("limit-exceeded", `JSON member exceeds 4 MiB: ${path}`);
      }
      if ((path.startsWith("documents/") || path.startsWith("assets/")) && bytes.byteLength > LOCAL_WORLD_PACKAGE_V1.limits.attachmentBytes) {
        fail("limit-exceeded", `Attachment exceeds 8 MiB: ${path}`);
      }
    }
    const totalBytes = capturedEntries.reduce((sum, [, bytes]) => sum + bytes.byteLength, 0);
    if (totalBytes > LOCAL_WORLD_PACKAGE_V1.limits.totalBytes) fail("limit-exceeded", "Package exceeds the 16 MiB total byte limit.");
    const memberMap = new Map(capturedEntries);
    const manifestBytes = memberMap.get(MANIFEST_PATH);
    if (!manifestBytes) fail("invalid-package", "Package lacks manifest.json.");
    const manifest = manifestFromUnknown(decodeJson(manifestBytes, MANIFEST_PATH));
    const expectedPaths = new Set([MANIFEST_PATH, ...manifest.members.map((descriptor) => descriptor.path)]);
    if (expectedPaths.size !== memberMap.size || [...memberMap.keys()].some((path) => !expectedPaths.has(path))) {
      fail("invalid-package", "Member map contains undeclared or missing members.");
    }
    const payloadBytes = manifest.members.reduce((sum, descriptor) => sum + descriptor.sizeBytes, 0);
    if (payloadBytes !== manifest.payloadBytes) fail("invalid-package", "Manifest payload byte count is inaccurate.");
    for (const descriptor of manifest.members) {
      const bytes = memberMap.get(descriptor.path)!;
      if (bytes.byteLength !== descriptor.sizeBytes) fail("invalid-package", `Member byte count is inaccurate: ${descriptor.path}`);
      if (await sha256(bytes) !== descriptor.sha256) fail("invalid-package", `Member digest does not match: ${descriptor.path}`);
    }
    const semanticBytes = memberMap.get(SEMANTIC_PATH)!;
    const semantic = validateSemanticWire(decodeJson(semanticBytes, SEMANTIC_PATH));
    const layoutWire = validateLayoutWire(decodeJson(memberMap.get(LAYOUT_PATH)!, LAYOUT_PATH), semantic.snapshot);
    const historyBytes = memberMap.get(HISTORY_PATH);
    const history = historyBytes ? validateHistory(decodeJson(historyBytes, HISTORY_PATH), semantic.localRevision) : [];
    validateHistoryCoverage(manifest, history);
    const availability = expectedAvailability(semantic.documents, semantic.assets);
    if (canonicalJson(availability) !== canonicalJson(manifest.attachmentAvailability)) fail("invalid-package", "Attachment availability counts disagree with semantic references.");
    validateAttachmentMembers(semantic, memberMap, manifest.members);
    if (await semanticDigest(semantic, memberMap) !== manifest.semanticDigest) fail("invalid-package", "Semantic digest does not match the validated meaning and attachment digests.");
    const record: LocalWorldRecord = {
      snapshot: semantic.snapshot,
      localRevision: semantic.localRevision,
      publishedRevisionId: semantic.publishedRevisionId as LocalWorldRecord["publishedRevisionId"],
      layout: layoutWire.layout,
      layoutRevision: layoutWire.layoutRevision,
      history,
    };
    validateRecord(record);
    return {
      status: "staged",
      candidate: {
        manifest,
        record: cloneLocalWorldValue(record),
        documents: cloneLocalWorldValue(semantic.documents),
        assets: cloneLocalWorldValue(semantic.assets),
        members: new Map([...memberMap].map(([path, bytes]) => [path, new Uint8Array(bytes)])),
      },
    };
  } catch (error) {
    const problem = error instanceof PackageProblem ? error : new PackageProblem("invalid-package", "Package validation failed.");
    return { status: "error", code: problem.code, message: problem.message };
  }
}
