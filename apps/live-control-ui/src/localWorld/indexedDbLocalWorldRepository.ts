import {
  cloneLocalWorldValue,
  validateLocalWorldSnapshot,
  validateLocalWorldPackageData,
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
  type ListLocalWorldsResult,
  type LocalWorldSnapshot,
  type ReadConflictCandidatesResult,
  type ReadWorldResult,
  type WriteLayoutResult,
} from "./localWorldRepository";
import { validateLocalWorldRecordForPackage } from "./localWorldPackageV1";

export const LOCAL_WORLD_DATABASE_SCHEMA_VERSION = 3;
export const LOCAL_WORLD_DATABASE_NAME = "dungeonmindbuddy-local-worlds";
export const LOCAL_WORLD_DATABASE_STORES = {
  worlds: "worlds",
  conflicts: "conflicts",
  packageData: "packageData",
} as const;

const WORLD_STORE = LOCAL_WORLD_DATABASE_STORES.worlds;
const CONFLICT_STORE = LOCAL_WORLD_DATABASE_STORES.conflicts;
const PACKAGE_DATA_STORE = LOCAL_WORLD_DATABASE_STORES.packageData;
const CONFLICT_WORLD_INDEX = "worldId";

export type IndexedDbCommitPoint = "create" | "semantic-edit" | "layout" | "package-restore";
export type IndexedDbCommitHook = (point: IndexedDbCommitPoint) => void;
type IdFactory = () => string;
type OpenErrorCode =
  | "unavailable"
  | "blocked"
  | "incompatible-version"
  | "incompatible-schema"
  | "open-failed";

export interface IndexedDbLocalWorldRepositoryOptions {
  /** Defaults to this realm's native IndexedDB. `null` explicitly represents unavailable storage. */
  readonly factory?: IDBFactory | null;
  readonly idFactory?: IdFactory;
  /** Synchronous fault-injection seam; do not use to perform asynchronous work in a transaction. */
  readonly beforeWrite?: IndexedDbCommitHook;
}

export type OpenIndexedDbLocalWorldRepositoryResult =
  | { readonly status: "opened"; readonly repository: IndexedDbLocalWorldRepository }
  | {
      readonly status: "error";
      readonly code: OpenErrorCode;
      readonly message: string;
    };

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
  if (error instanceof DOMException) return `${error.name}: ${error.message}`;
  return error instanceof Error ? error.message : "The local World database operation failed.";
}

function errorCode(error: unknown): OpenErrorCode {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "VersionError") return "incompatible-version";
  return "open-failed";
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.addEventListener("success", () => resolve(request.result), { once: true });
    request.addEventListener("error", () => reject(request.error ?? new Error("IndexedDB request failed.")), {
      once: true,
    });
  });
}

function transactionFinished(transaction: IDBTransaction): Promise<void> {
  return new Promise((resolve, reject) => {
    transaction.addEventListener("complete", () => resolve(), { once: true });
    transaction.addEventListener("abort", () => reject(
      transaction.error ?? new DOMException("The IndexedDB transaction was aborted.", "AbortError"),
    ), { once: true });
    transaction.addEventListener("error", () => {
      // The abort event supplies the final transaction error.
    }, { once: true });
  });
}

async function inTransaction<T>(
  db: IDBDatabase,
  stores: string | string[],
  mode: IDBTransactionMode,
  operation: (transaction: IDBTransaction) => Promise<T>,
): Promise<T> {
  const transaction = db.transaction(stores, mode);
  const finished = transactionFinished(transaction);
  try {
    const result = await operation(transaction);
    await finished;
    return result;
  } catch (error) {
    try {
      transaction.abort();
    } catch {
      // The transaction may already have aborted or completed; its completion promise is authoritative.
    }
    await finished.catch(() => undefined);
    throw error;
  }
}

function upgradeDatabase(request: IDBOpenDBRequest, oldVersion: number): void {
  const db = request.result;
  if (oldVersion > 0) {
    const tx = request.transaction!;
    if (!db.objectStoreNames.contains(WORLD_STORE) || !db.objectStoreNames.contains(CONFLICT_STORE)) throw new Error("Existing local World schema is missing required stores; upgrade refused.");
    const worlds = tx.objectStore(WORLD_STORE);
    const conflicts = tx.objectStore(CONFLICT_STORE);
    if (worlds.keyPath !== "snapshot.worldId" || worlds.autoIncrement || conflicts.keyPath !== "id" || conflicts.autoIncrement) {
      throw new Error("Existing local World schema has incompatible key semantics; upgrade refused.");
    }
    if (oldVersion >= 2) {
      if (!conflicts.indexNames.contains(CONFLICT_WORLD_INDEX)) throw new Error("Existing conflict index is missing; upgrade refused.");
      const index = conflicts.index(CONFLICT_WORLD_INDEX);
      if (index.keyPath !== "worldId" || index.unique || index.multiEntry) throw new Error("Existing conflict index is incompatible; upgrade refused.");
    }
  }
  if (oldVersion < 1) {
    db.createObjectStore(WORLD_STORE, { keyPath: "snapshot.worldId" });
    db.createObjectStore(CONFLICT_STORE, { keyPath: "id" });
  }
  if (oldVersion < 2) {
    const conflicts = request.transaction!.objectStore(CONFLICT_STORE);
    if (!conflicts.indexNames.contains(CONFLICT_WORLD_INDEX)) {
      conflicts.createIndex(CONFLICT_WORLD_INDEX, "worldId", { unique: false });
    }
  }
  if (oldVersion < 3) db.createObjectStore(PACKAGE_DATA_STORE, { keyPath: "localWorldId" });
}

function hasCurrentSchema(db: IDBDatabase): boolean {
  if (!db.objectStoreNames.contains(WORLD_STORE) || !db.objectStoreNames.contains(CONFLICT_STORE) || !db.objectStoreNames.contains(PACKAGE_DATA_STORE)) return false;
  const transaction = db.transaction([WORLD_STORE, CONFLICT_STORE, PACKAGE_DATA_STORE], "readonly");
  const worlds = transaction.objectStore(WORLD_STORE);
  const conflicts = transaction.objectStore(CONFLICT_STORE);
  const packageData = transaction.objectStore(PACKAGE_DATA_STORE);
  if (worlds.keyPath !== "snapshot.worldId" || worlds.autoIncrement) return false;
  if (conflicts.keyPath !== "id" || conflicts.autoIncrement) return false;
  if (!conflicts.indexNames.contains(CONFLICT_WORLD_INDEX)) return false;
  const worldIndex = conflicts.index(CONFLICT_WORLD_INDEX);
  return worldIndex.keyPath === "worldId" && !worldIndex.unique && !worldIndex.multiEntry
    && packageData.keyPath === "localWorldId" && !packageData.autoIncrement;
}

/** Open one isolated named IndexedDB database and fail closed on incompatible schema versions. */
export function openIndexedDbLocalWorldRepository(
  databaseName: string,
  options: IndexedDbLocalWorldRepositoryOptions = {},
): Promise<OpenIndexedDbLocalWorldRepositoryResult> {
  let factory: IDBFactory | null | undefined;
  const idFactory = options.idFactory ?? defaultIdFactory;
  const beforeWrite = options.beforeWrite;
  try {
    factory = options.factory === undefined ? globalThis.indexedDB : options.factory;
  } catch (error) {
    return Promise.resolve({
      status: "error",
      code: "unavailable",
      message: errorMessage(error),
    });
  }
  if (!factory) {
    return Promise.resolve({
      status: "error",
      code: "unavailable",
      message: "IndexedDB is unavailable in this browser context.",
    });
  }

  return new Promise((resolve) => {
    let settled = false;
    const finish = (result: OpenIndexedDbLocalWorldRepositoryResult) => {
      if (settled) return;
      settled = true;
      resolve(result);
    };
    let request: IDBOpenDBRequest;
    try {
      request = factory.open(databaseName, LOCAL_WORLD_DATABASE_SCHEMA_VERSION);
    } catch (error) {
      finish({ status: "error", code: errorCode(error), message: errorMessage(error) });
      return;
    }

    request.addEventListener("upgradeneeded", (event) => {
      try {
        upgradeDatabase(request, (event as IDBVersionChangeEvent).oldVersion);
      } catch (error) {
        try {
          request.transaction?.abort();
        } catch {
          // The open request error reports the aborted upgrade.
        }
        finish({ status: "error", code: "incompatible-schema", message: errorMessage(error) });
      }
    });
    request.addEventListener("blocked", () => {
      finish({
        status: "error",
        code: "blocked",
        message: "An older tab is blocking the local World database upgrade. Close it and retry.",
      });
    });
    request.addEventListener("error", () => {
      finish({
        status: "error",
        code: errorCode(request.error),
        message: errorMessage(request.error),
      });
    });
    request.addEventListener("success", () => {
      const db = request.result;
      // A blocked request may succeed after we reported the blocked state; do not leak the late handle.
      if (settled) {
        db.close();
        return;
      }
      let compatible = false;
      try {
        compatible = hasCurrentSchema(db);
      } catch {
        compatible = false;
      }
      if (!compatible) {
        db.close();
        finish({
          status: "error",
          code: "incompatible-schema",
          message: "The local World database is missing required stores or indexes.",
        });
        return;
      }
      db.onversionchange = () => db.close();
      finish({
        status: "opened",
        repository: new IndexedDbLocalWorldRepository(db, idFactory, beforeWrite),
      });
    });
  });
}

/** Native IndexedDB adapter. All database names are supplied by the owning caller. */
export class IndexedDbLocalWorldRepository implements LocalWorldPackageRepository {
  constructor(
    private readonly db: IDBDatabase,
    private readonly idFactory: IdFactory = defaultIdFactory,
    private readonly beforeWrite: IndexedDbCommitHook = () => undefined,
  ) {}

  close(): void {
    this.db.close();
  }

  get databaseVersion(): number {
    return this.db.version;
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
      await inTransaction(this.db, [WORLD_STORE, CONFLICT_STORE], "readwrite", async (transaction) => {
        this.beforeWrite("create");
        await requestResult(transaction.objectStore(WORLD_STORE).add(record));
      });
      return { status: "created", record: cloneLocalWorldValue(record) };
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async readWorld(worldId: LocalWorldId): Promise<ReadWorldResult> {
    try {
      return await inTransaction(this.db, WORLD_STORE, "readonly", async (transaction) => {
        const record = await requestResult<LocalWorldRecord | undefined>(
          transaction.objectStore(WORLD_STORE).get(worldId),
        );
        return record
          ? { status: "found", record: cloneLocalWorldValue(record) }
          : { status: "missing" };
      });
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async listWorlds(): Promise<ListLocalWorldsResult> {
    try {
      return await inTransaction(this.db, WORLD_STORE, "readonly", async (transaction) => {
        const records = await requestResult<LocalWorldRecord[]>(transaction.objectStore(WORLD_STORE).getAll());
        records.sort((left, right) => left.snapshot.title.localeCompare(right.snapshot.title) || left.snapshot.worldId.localeCompare(right.snapshot.worldId));
        return { status: "found", records: cloneLocalWorldValue(records) };
      });
    } catch (error) { return { status: "error", message: errorMessage(error) }; }
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
    const worldId = input.worldId;
    const expectedLocalRevision = input.expectedLocalRevision;
    const proposedSnapshot = cloneLocalWorldValue(input.nextSnapshot);
    const proposedEdit = cloneLocalWorldValue(input.edit);
    const validationError = validateLocalWorldSnapshot(proposedSnapshot, worldId);
    if (validationError) return { status: "error", message: validationError };

    try {
      return await inTransaction(
        this.db,
        [WORLD_STORE, CONFLICT_STORE],
        "readwrite",
        async (transaction) => {
          const worlds = transaction.objectStore(WORLD_STORE);
          const current = await requestResult<LocalWorldRecord | undefined>(worlds.get(worldId));
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
            this.beforeWrite("semantic-edit");
            await requestResult(transaction.objectStore(CONFLICT_STORE).add(candidate));
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
          this.beforeWrite("semantic-edit");
          await requestResult(worlds.put(next));
          return { status: "committed", record: cloneLocalWorldValue(next) };
        },
      );
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
      return await inTransaction(this.db, WORLD_STORE, "readwrite", async (transaction) => {
        const worlds = transaction.objectStore(WORLD_STORE);
        const current = await requestResult<LocalWorldRecord | undefined>(worlds.get(worldId));
        if (!current) return { status: "missing" };
        if (current.layoutRevision !== expectedLayoutRevision) {
          return { status: "conflict", record: cloneLocalWorldValue(current) };
        }
        const next: LocalWorldRecord = {
          ...current,
          layout: nextLayout,
          layoutRevision: current.layoutRevision + 1,
        };
        this.beforeWrite("layout");
        await requestResult(worlds.put(next));
        return { status: "written", record: cloneLocalWorldValue(next) };
      });
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async readConflictCandidates(worldId: LocalWorldId): Promise<ReadConflictCandidatesResult> {
    try {
      return await inTransaction(
        this.db,
        [WORLD_STORE, CONFLICT_STORE],
        "readonly",
        async (transaction) => {
          const current = await requestResult<LocalWorldRecord | undefined>(
            transaction.objectStore(WORLD_STORE).get(worldId),
          );
          if (!current) return { status: "missing" };
          const candidates = await requestResult<LocalWorldConflictCandidate[]>(
            transaction.objectStore(CONFLICT_STORE).index(CONFLICT_WORLD_INDEX).getAll(worldId),
          );
          return { status: "found", candidates: cloneLocalWorldValue(candidates) };
        },
      );
    } catch (error) {
      return { status: "error", message: errorMessage(error) };
    }
  }

  async restorePackage(recordInput: LocalWorldRecord, dataInput: LocalWorldPackageData): Promise<RestoreLocalWorldPackageResult> {
    let record: LocalWorldRecord;
    let data: LocalWorldPackageData;
    try {
      // Structured copies happen synchronously, before opening/awaiting a transaction.
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
      return await inTransaction(this.db, [WORLD_STORE, PACKAGE_DATA_STORE], "readwrite", async (transaction) => {
        const worlds = transaction.objectStore(WORLD_STORE);
        const existing = await requestResult<LocalWorldRecord | undefined>(worlds.get(worldId));
        if (existing) return { status: "collision" };
        this.beforeWrite("package-restore");
        await requestResult(worlds.add(record));
        this.beforeWrite("package-restore");
        await requestResult(transaction.objectStore(PACKAGE_DATA_STORE).add(data));
        return { status: "restored", record: cloneLocalWorldValue(record) };
      });
    } catch (error) { return { status: "error", message: errorMessage(error) }; }
  }

  async readPackageData(worldId: LocalWorldId): Promise<ReadLocalWorldPackageDataResult> {
    try {
      return await inTransaction(this.db, [WORLD_STORE, PACKAGE_DATA_STORE], "readonly", async (transaction) => {
        const worlds = transaction.objectStore(WORLD_STORE);
        const record = await requestResult<LocalWorldRecord | undefined>(worlds.get(worldId));
        if (!record) return { status: "missing" };
        const data = await requestResult<LocalWorldPackageData | undefined>(transaction.objectStore(PACKAGE_DATA_STORE).get(worldId));
        return data ? { status: "found", data: cloneLocalWorldValue(data) } : { status: "not-stored" };
      });
    } catch (error) { return { status: "error", message: errorMessage(error) }; }
  }

  allocateObjectId(worldId: LocalWorldId): LocalObjectId {
    return `${worldId}:object:${this.idFactory()}` as LocalObjectId;
  }

  allocateRelationshipId(worldId: LocalWorldId): LocalRelationshipId {
    return `${worldId}:relationship:${this.idFactory()}` as LocalRelationshipId;
  }
}
