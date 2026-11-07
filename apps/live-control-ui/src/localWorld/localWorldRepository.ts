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
