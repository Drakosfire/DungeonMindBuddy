import {
  cloneLocalWorldValue,
  type CommitSemanticResult,
  type CreateWorldResult,
  type LocalConflictId,
  type LocalEditId,
  type LocalObjectId,
  type LocalRelationshipId,
  type LocalWorldConflictCandidate,
  type LocalWorldId,
  type LocalWorldLayout,
  type LocalWorldRecord,
  type LocalWorldPackageData,
  type LocalWorldPackageRepository,
  type RestoreLocalWorldPackageResult,
  type ReadLocalWorldPackageDataResult,
  type LocalWorldSnapshot,
  type ReadConflictCandidatesResult,
  type ReadWorldResult,
  type WriteLayoutResult,
  validateLocalWorldSnapshot,
  validateLocalWorldPackageData,
} from "./localWorldRepository";
import { validateLocalWorldRecordForPackage } from "./localWorldPackageV1";

/**
 * Shared only by in-memory repository facades. It deliberately has no browser
 * storage adapter and no serialization/durability behavior.
 */
export class InMemoryLocalWorldStore {
  readonly worlds = new Map<LocalWorldId, LocalWorldRecord>();
  readonly conflictCandidates = new Map<LocalWorldId, LocalWorldConflictCandidate[]>();
  readonly packageData = new Map<LocalWorldId, LocalWorldPackageData>();
}

export type InMemoryCommitPoint = "create" | "semantic-edit" | "layout" | "package-restore";
export type InMemoryCommitHook = (point: InMemoryCommitPoint) => void | Promise<void>;
export type LocalIdFactory = () => string;

export interface InMemoryLocalWorldRepositoryOptions {
  readonly store?: InMemoryLocalWorldStore;
  readonly idFactory?: LocalIdFactory;
  /** Test seam for exercising failure before the atomic in-memory state swap. */
  readonly beforeCommit?: InMemoryCommitHook;
}

const emptyLayout = (): LocalWorldLayout => ({
  positions: {},
  viewport: { x: 0, y: 0, zoom: 1 },
  layoutVersion: 1,
});

function defaultIdFactory(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") return globalThis.crypto.randomUUID();
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The in-memory local World operation failed.";
}

/**
 * Reference implementation of the async repository contract. State swaps are
 * synchronous after the optional hook, making snapshot/history writes one
 * indivisible JavaScript turn for this test adapter. This is not a durability
 * or cross-tab guarantee.
 */
export class InMemoryLocalWorldRepository implements LocalWorldPackageRepository {
  private readonly store: InMemoryLocalWorldStore;
  private readonly idFactory: LocalIdFactory;
  private readonly beforeCommit: InMemoryCommitHook;

  constructor(options: InMemoryLocalWorldRepositoryOptions = {}) {
    this.store = options.store ?? new InMemoryLocalWorldStore();
    this.idFactory = options.idFactory ?? defaultIdFactory;
    this.beforeCommit = options.beforeCommit ?? (() => undefined);
  }

  async createWorld(input: { readonly title: string }): Promise<CreateWorldResult> {
    const title = input.title;
    const worldId = `local-world:${this.idFactory()}` as LocalWorldId;
    const record: LocalWorldRecord = {
      snapshot: { worldId, title, objects: [], relationships: [] },
      localRevision: 0,
      publishedRevisionId: null,
      layout: emptyLayout(),
      layoutRevision: 0,
      history: [{
        id: `local-edit:${this.idFactory()}` as LocalEditId,
        localRevision: 0,
        classification: "buddy-local-only",
        description: "Created local World draft",
      }],
    };

    try {
      await this.beforeCommit("create");
      if (this.store.worlds.has(worldId)) {
        return { status: "error", message: "The generated local World ID already exists." };
      }
      this.store.worlds.set(worldId, cloneLocalWorldValue(record));
      this.store.conflictCandidates.set(worldId, []);
      return { status: "created", record: cloneLocalWorldValue(record) };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async readWorld(worldId: LocalWorldId): Promise<ReadWorldResult> {
    try {
      const record = this.store.worlds.get(worldId);
      return record
        ? { status: "found", record: cloneLocalWorldValue(record) }
        : { status: "missing" };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async restorePackage(recordInput: LocalWorldRecord, dataInput: LocalWorldPackageData): Promise<RestoreLocalWorldPackageResult> {
    let record: LocalWorldRecord;
    let data: LocalWorldPackageData;
    try {
      record = cloneLocalWorldValue(recordInput);
      data = cloneLocalWorldValue(dataInput);
    } catch (error) { return { status: "error", message: errorMessage(error) }; }
    const worldId = record.snapshot.worldId;
    const invalidRecord = validateLocalWorldRecordForPackage(record);
    if (invalidRecord) return { status: "error", message: invalidRecord };
    const invalidData = validateLocalWorldPackageData(data, worldId);
    if (invalidData) return { status: "error", message: invalidData };
    const invalid = validateLocalWorldSnapshot(record.snapshot, worldId);
    if (invalid) return { status: "error", message: invalid };
    try {
      await this.beforeCommit("package-restore");
      if (this.store.worlds.has(worldId)) return { status: "collision" };
      // Publish both maps synchronously only after all fallible preparation completes.
      this.store.worlds.set(worldId, cloneLocalWorldValue(record));
      this.store.conflictCandidates.set(worldId, []);
      this.store.packageData.set(worldId, cloneLocalWorldValue(data));
      return { status: "restored", record: cloneLocalWorldValue(record) };
    } catch (error) { return { status: "error", message: errorMessage(error) }; }
  }

  async readPackageData(worldId: LocalWorldId): Promise<ReadLocalWorldPackageDataResult> {
    if (!this.store.worlds.has(worldId)) return { status: "missing" };
    const data = this.store.packageData.get(worldId);
    return data ? { status: "found", data: cloneLocalWorldValue(data) } : { status: "not-stored" };
  }

  async commitSemanticEdit(input: {
    readonly worldId: LocalWorldId;
    readonly expectedLocalRevision: number;
    readonly nextSnapshot: LocalWorldSnapshot;
    readonly edit: {
      readonly classification: "supported-semantic-intent" | "buddy-local-only";
      readonly description: string;
    };
  }): Promise<CommitSemanticResult> {
    // Capture caller-owned data before awaiting so later mutation cannot alter a queued write.
    const worldId = input.worldId;
    const expectedLocalRevision = input.expectedLocalRevision;
    const proposedSnapshot = cloneLocalWorldValue(input.nextSnapshot);
    const proposedEdit = cloneLocalWorldValue(input.edit);
    const validationError = validateLocalWorldSnapshot(proposedSnapshot, worldId);
    if (validationError) return { status: "error", message: validationError };

    try {
      await this.beforeCommit("semantic-edit");
      const current = this.store.worlds.get(worldId);
      if (!current) return { status: "missing" };
      if (current.localRevision !== expectedLocalRevision) {
        const candidate: LocalWorldConflictCandidate = {
          id: `local-conflict:${this.idFactory()}` as LocalConflictId,
          worldId,
          baseLocalRevision: expectedLocalRevision,
          currentLocalRevision: current.localRevision,
          proposedSnapshot,
          edit: proposedEdit,
        };
        const candidates = this.store.conflictCandidates.get(worldId) ?? [];
        this.store.conflictCandidates.set(worldId, [...candidates, cloneLocalWorldValue(candidate)]);
        return {
          status: "conflict",
          committed: cloneLocalWorldValue(current),
          candidate: cloneLocalWorldValue(candidate),
        };
      }

      const nextRevision = current.localRevision + 1;
      const next: LocalWorldRecord = {
        ...current,
        snapshot: proposedSnapshot,
        localRevision: nextRevision,
        history: [...current.history, {
          id: `local-edit:${this.idFactory()}` as LocalEditId,
          localRevision: nextRevision,
          ...proposedEdit,
        }],
      };
      // One map replacement publishes snapshot and its history entry together.
      this.store.worlds.set(worldId, cloneLocalWorldValue(next));
      return { status: "committed", record: cloneLocalWorldValue(next) };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async writeLayout(input: {
    readonly worldId: LocalWorldId;
    readonly expectedLayoutRevision: number;
    readonly nextLayout: LocalWorldLayout;
  }): Promise<WriteLayoutResult> {
    const worldId = input.worldId;
    const expectedLayoutRevision = input.expectedLayoutRevision;
    const nextLayout = cloneLocalWorldValue(input.nextLayout);
    try {
      await this.beforeCommit("layout");
      const current = this.store.worlds.get(worldId);
      if (!current) return { status: "missing" };
      if (current.layoutRevision !== expectedLayoutRevision) {
        return { status: "conflict", record: cloneLocalWorldValue(current) };
      }
      const next: LocalWorldRecord = {
        ...current,
        layout: nextLayout,
        layoutRevision: current.layoutRevision + 1,
      };
      this.store.worlds.set(worldId, cloneLocalWorldValue(next));
      return { status: "written", record: cloneLocalWorldValue(next) };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async readConflictCandidates(worldId: LocalWorldId): Promise<ReadConflictCandidatesResult> {
    try {
      if (!this.store.worlds.has(worldId)) return { status: "missing" };
      return {
        status: "found",
        candidates: cloneLocalWorldValue(this.store.conflictCandidates.get(worldId) ?? []),
      };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  allocateObjectId(worldId: LocalWorldId): LocalObjectId {
    return `${worldId}:object:${this.idFactory()}` as LocalObjectId;
  }

  allocateRelationshipId(worldId: LocalWorldId): LocalRelationshipId {
    return `${worldId}:relationship:${this.idFactory()}` as LocalRelationshipId;
  }
}
