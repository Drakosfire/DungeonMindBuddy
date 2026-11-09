/**
 * Buddy-owned boundary for an anonymous local World draft. This contract is
 * asynchronous so a future browser store cannot masquerade as synchronous
 * Web Storage. It says nothing about durability until an adapter proves it.
 */

export type LocalWorldId = string & { readonly __brand: "LocalWorldId" };
export type LocalObjectId = string & { readonly __brand: "LocalObjectId" };
export type LocalRelationshipId = string & { readonly __brand: "LocalRelationshipId" };
export type LocalEditId = string & { readonly __brand: "LocalEditId" };
export type LocalConflictId = string & { readonly __brand: "LocalConflictId" };
export type PublishedRevisionId = string & { readonly __brand: "PublishedRevisionId" };

/** Package attachment path policy is owned here so both staged parsing and direct repository writes share it. */
export const LOCAL_WORLD_PACKAGE_MEMBER_PATH_LIMITS = {
  bytes: 256,
  segments: 16,
} as const;

const packageMemberPathEncoder = new TextEncoder();
const packageAssetPathPattern = /^assets\/[0-9a-f]{64}$/;

export function isLocalWorldPackageMemberPath(path: string): boolean {
  if (!path || !isWellFormedUnicode(path)
    || path.length > LOCAL_WORLD_PACKAGE_MEMBER_PATH_LIMITS.bytes
    || packageMemberPathEncoder.encode(path).byteLength > LOCAL_WORLD_PACKAGE_MEMBER_PATH_LIMITS.bytes
    || path.startsWith("/") || path.includes("\\") || /[\u0000-\u001f\u007f]/.test(path)
    || path !== path.normalize("NFC")) return false;
  const segments = path.split("/");
  if (segments.length > LOCAL_WORLD_PACKAGE_MEMBER_PATH_LIMITS.segments
    || segments.some((segment) => !segment || segment === "." || segment === ".." || segment.includes(":"))) return false;
  if (path === "semantic.json" || path === "layout.json" || path === "history.json") return true;
  if (path.startsWith("documents/")) return segments.length >= 2;
  return packageAssetPathPattern.test(path);
}

function isWellFormedUnicode(value: string): boolean {
  for (let index = 0; index < value.length; index += 1) {
    const code = value.charCodeAt(index);
    if (code >= 0xd800 && code <= 0xdbff) {
      const next = value.charCodeAt(index + 1);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
      index += 1;
    } else if (code >= 0xdc00 && code <= 0xdfff) return false;
  }
  return true;
}

export type LocalJsonValue =
  | null
  | boolean
  | number
  | string
  | LocalJsonValue[]
  | { [key: string]: LocalJsonValue };

export interface LocalWorldObject {
  readonly id: LocalObjectId;
  readonly name: string;
  readonly kind: string;
  readonly properties: Readonly<Record<string, LocalJsonValue>>;
}

export interface LocalWorldRelationship {
  readonly id: LocalRelationshipId;
  readonly fromObjectId: LocalObjectId;
  readonly toObjectId: LocalObjectId;
  readonly kind: string;
  readonly properties: Readonly<Record<string, LocalJsonValue>>;
}

export interface LocalWorldSnapshot {
  readonly worldId: LocalWorldId;
  readonly title: string;
  readonly objects: readonly LocalWorldObject[];
  readonly relationships: readonly LocalWorldRelationship[];
}

/** Canvas state has an independent optimistic revision and never changes World meaning. */
export interface LocalWorldLayout {
  readonly positions: Readonly<Record<string, { readonly x: number; readonly y: number }>>;
  readonly viewport: { readonly x: number; readonly y: number; readonly zoom: number };
  readonly layoutVersion: number;
}

export interface LocalWorldRecord {
  readonly snapshot: LocalWorldSnapshot;
  /** Monotonic Buddy-local semantic revision. Not a DungeonMind revision. */
  readonly localRevision: number;
  /** Only populated after a future owner verifies a real DungeonMind publication. */
  readonly publishedRevisionId: PublishedRevisionId | null;
  readonly layout: LocalWorldLayout;
  readonly layoutRevision: number;
  readonly history: readonly LocalWorldHistoryEntry[];
}

export type LocalEditClassification = "supported-semantic-intent" | "buddy-local-only";

export interface LocalWorldHistoryEntry {
  readonly id: LocalEditId;
  readonly localRevision: number;
  /** Informational only in A1; no executable/replayable operation payload is defined here. */
  readonly classification: LocalEditClassification;
  readonly description: string;
}

export interface LocalWorldConflictCandidate {
  readonly id: LocalConflictId;
  readonly worldId: LocalWorldId;
  readonly baseLocalRevision: number;
  readonly currentLocalRevision: number;
  readonly proposedSnapshot: LocalWorldSnapshot;
  readonly edit: Omit<LocalWorldHistoryEntry, "id" | "localRevision">;
}

export interface LocalWorldRepository {
  createWorld(input: { readonly title: string }): Promise<CreateWorldResult>;
  readWorld(worldId: LocalWorldId): Promise<ReadWorldResult>;
  commitSemanticEdit(input: {
    readonly worldId: LocalWorldId;
    readonly expectedLocalRevision: number;
    readonly nextSnapshot: LocalWorldSnapshot;
    readonly edit: Omit<LocalWorldHistoryEntry, "id" | "localRevision">;
  }): Promise<CommitSemanticResult>;
  writeLayout(input: {
    readonly worldId: LocalWorldId;
    readonly expectedLayoutRevision: number;
    readonly nextLayout: LocalWorldLayout;
  }): Promise<WriteLayoutResult>;
  readConflictCandidates(worldId: LocalWorldId): Promise<ReadConflictCandidatesResult>;
  allocateObjectId(worldId: LocalWorldId): LocalObjectId;
  allocateRelationshipId(worldId: LocalWorldId): LocalRelationshipId;
}

export interface LocalPackageReference {
  readonly id: string;
  readonly status: "bundled" | "external" | "missing";
  readonly path: string | null;
  readonly mediaType: string;
  readonly locator: string | null;
}

/** Supplemental package data is distinct from the semantic World record. */
export interface LocalWorldPackageData {
  readonly localWorldId: LocalWorldId;
  readonly documents: readonly LocalPackageReference[];
  readonly assets: readonly LocalPackageReference[];
  /** Only bytes for references declared bundled are retained. */
  readonly bundledMembers: Readonly<Record<string, readonly number[]>>;
  readonly fidelity: {
    readonly localRecord: "preserved";
    readonly sourceMetadata: "not-represented-by-local-record";
    readonly profileMetadata: "not-represented-by-local-record";
  };
  readonly creatorProfileAssumptions: { readonly creator: "not-recorded"; readonly profile: "not-recorded" };
}

export type RestoreLocalWorldPackageResult =
  | { readonly status: "restored"; readonly record: LocalWorldRecord }
  | { readonly status: "collision" }
  | { readonly status: "error"; readonly message: string };
export type ReadLocalWorldPackageDataResult =
  | { readonly status: "found"; readonly data: LocalWorldPackageData }
  | { readonly status: "not-stored" }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

/** Optional package restore capability; ordinary editor consumers remain on LocalWorldRepository. */
export interface LocalWorldPackageRepository extends LocalWorldRepository {
  listWorlds(): Promise<ListLocalWorldsResult>;
  restorePackage(record: LocalWorldRecord, data: LocalWorldPackageData): Promise<RestoreLocalWorldPackageResult>;
  readPackageData(worldId: LocalWorldId): Promise<ReadLocalWorldPackageDataResult>;
}

export type ListLocalWorldsResult =
  | { readonly status: "found"; readonly records: readonly LocalWorldRecord[] }
  | { readonly status: "error"; readonly message: string };

export function validateLocalWorldPackageData(data: LocalWorldPackageData, expectedWorldId: LocalWorldId): string | null {
  if (data.localWorldId !== expectedWorldId) return "Package data belongs to another local World.";
  if (data.fidelity?.localRecord !== "preserved"
    || data.fidelity?.sourceMetadata !== "not-represented-by-local-record"
    || data.fidelity?.profileMetadata !== "not-represented-by-local-record"
    || data.creatorProfileAssumptions?.creator !== "not-recorded"
    || data.creatorProfileAssumptions?.profile !== "not-recorded") {
    return "Package fidelity and creator/profile declarations are unsupported.";
  }
  const refs = [data.documents, data.assets];
  const bundledPaths = new Set<string>();
  const pathMediaTypes = new Map<string, string>();
  for (const [groupIndex, group] of refs.entries()) {
    if (!Array.isArray(group)) return "Package attachment references must be arrays.";
    const ids = new Set<string>();
    for (const ref of group) {
      if (!ref || typeof ref !== "object") return "Package attachment reference is malformed.";
      if (!ref.id || ids.has(ref.id)) return "Package attachment references contain an empty or duplicate ID.";
      ids.add(ref.id);
      if (ref.status !== "bundled" && ref.status !== "external" && ref.status !== "missing") return "Package attachment availability is unsupported.";
      if (!/^[a-z0-9!#$&^_.+-]+\/[a-z0-9!#$&^_.+-]+$/i.test(ref.mediaType)) return "Package attachment media type is invalid.";
      if (ref.locator !== null && typeof ref.locator !== "string") return "Package attachment locator must be text or null.";
      if (ref.status === "bundled") {
        const prefix = groupIndex === 0 ? "documents/" : "assets/";
        if (!ref.path || !ref.path.startsWith(prefix) || !isLocalWorldPackageMemberPath(ref.path)) {
          return "Bundled attachment path is unsafe or outside its declared namespace.";
        }
        bundledPaths.add(ref.path);
        const priorMediaType = pathMediaTypes.get(ref.path);
        if (priorMediaType !== undefined && priorMediaType !== ref.mediaType) return "References sharing a bundled path must agree on media type.";
        pathMediaTypes.set(ref.path, ref.mediaType);
      } else if (ref.path !== null) return "External or missing attachments cannot claim bundled member paths.";
    }
  }
  if (!data.bundledMembers || typeof data.bundledMembers !== "object" || Array.isArray(data.bundledMembers)) return "Bundled attachment bytes are malformed.";
  const memberPaths = Object.keys(data.bundledMembers);
  if (memberPaths.length !== bundledPaths.size || memberPaths.some((path) => !bundledPaths.has(path))) {
    return "Bundled attachment bytes do not match the declared references.";
  }
  for (const bytes of Object.values(data.bundledMembers)) {
    if (!Array.isArray(bytes) || bytes.some((byte) => !Number.isInteger(byte) || byte < 0 || byte > 255)) {
      return "Bundled attachment bytes are malformed.";
    }
  }
  return null;
}

export type ReadWorldResult =
  | { readonly status: "found"; readonly record: LocalWorldRecord }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

export type CreateWorldResult =
  | { readonly status: "created"; readonly record: LocalWorldRecord }
  | { readonly status: "error"; readonly message: string };

export type CommitSemanticResult =
  | { readonly status: "committed"; readonly record: LocalWorldRecord }
  | {
      readonly status: "conflict";
      readonly committed: LocalWorldRecord;
      readonly candidate: LocalWorldConflictCandidate;
    }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

export type WriteLayoutResult =
  | { readonly status: "written"; readonly record: LocalWorldRecord }
  | { readonly status: "conflict"; readonly record: LocalWorldRecord }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

export type ReadConflictCandidatesResult =
  | { readonly status: "found"; readonly candidates: readonly LocalWorldConflictCandidate[] }
  | { readonly status: "missing" }
  | { readonly status: "error"; readonly message: string };

export function cloneLocalWorldValue<T>(value: T): T {
  return structuredClone(value);
}

/** Shared identity/reference validation for every Buddy-local repository adapter. */
export function validateLocalWorldSnapshot(
  snapshot: LocalWorldSnapshot,
  expectedWorldId: LocalWorldId,
): string | null {
  if (snapshot.worldId !== expectedWorldId) return "The proposed snapshot belongs to another local World.";
  const objectIds = new Set<string>();
  for (const object of snapshot.objects) {
    if (objectIds.has(object.id)) return "The proposed snapshot contains duplicate local object IDs.";
    objectIds.add(object.id);
  }
  const relationshipIds = new Set<string>();
  for (const relationship of snapshot.relationships) {
    if (relationshipIds.has(relationship.id)) {
      return "The proposed snapshot contains duplicate local relationship IDs.";
    }
    relationshipIds.add(relationship.id);
    if (!objectIds.has(relationship.fromObjectId) || !objectIds.has(relationship.toObjectId)) {
      return "The proposed relationship refers to a missing local object.";
    }
  }
  return null;
}
