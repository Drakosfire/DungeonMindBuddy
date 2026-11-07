import {
  cloneLocalWorldValue,
  validateLocalWorldSnapshot,
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
  type LocalWorldRepository,
  type LocalWorldSnapshot,
  type ReadConflictCandidatesResult,
  type ReadWorldResult,
  type WriteLayoutResult,
} from "./localWorldRepository";

export const LOCAL_WORLD_DATABASE_SCHEMA_VERSION = 2;
export const LOCAL_WORLD_DATABASE_STORES = {
  worlds: "worlds",
  conflicts: "conflicts",
} as const;

const WORLD_STORE = LOCAL_WORLD_DATABASE_STORES.worlds;
const CONFLICT_STORE = LOCAL_WORLD_DATABASE_STORES.conflicts;
const CONFLICT_WORLD_INDEX = "worldId";

export type IndexedDbCommitPoint = "create" | "semantic-edit" | "layout";
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
}

function hasCurrentSchema(db: IDBDatabase): boolean {
  if (!db.objectStoreNames.contains(WORLD_STORE) || !db.objectStoreNames.contains(CONFLICT_STORE)) return false;
  const transaction = db.transaction([WORLD_STORE, CONFLICT_STORE], "readonly");
  const conflicts = transaction.objectStore(CONFLICT_STORE);
  return conflicts.indexNames.contains(CONFLICT_WORLD_INDEX);
}

/** Open one isolated named IndexedDB database and fail closed on incompatible schema versions. */
export function openIndexedDbLocalWorldRepository(
  databaseName: string,
  options: IndexedDbLocalWorldRepositoryOptions = {},
): Promise<OpenIndexedDbLocalWorldRepositoryResult> {
  let factory: IDBFactory | null | undefined;
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
        repository: new IndexedDbLocalWorldRepository(db, options.idFactory ?? defaultIdFactory, options.beforeWrite),
      });
    });
  });
}

/** Native IndexedDB adapter. All database names are supplied by the owning caller. */
export class IndexedDbLocalWorldRepository implements LocalWorldRepository {
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
    const worldId = `local-world:${this.idFactory()}` as LocalWorldId;
    const record: LocalWorldRecord = {
      snapshot: { worldId, title: input.title, objects: [], relationships: [] },
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

  async commitSemanticEdit(input: {
    readonly worldId: LocalWorldId;
    readonly expectedLocalRevision: number;
    readonly nextSnapshot: LocalWorldSnapshot;
    readonly edit: {
      readonly classification: "supported-semantic-intent" | "buddy-local-only";
      readonly description: string;
    };
  }): Promise<CommitSemanticResult> {
    const proposedSnapshot = cloneLocalWorldValue(input.nextSnapshot);
    const proposedEdit = cloneLocalWorldValue(input.edit);
    const validationError = validateLocalWorldSnapshot(proposedSnapshot, input.worldId);
    if (validationError) return { status: "error", message: validationError };

    try {
      return await inTransaction(
        this.db,
        [WORLD_STORE, CONFLICT_STORE],
        "readwrite",
        async (transaction) => {
          const worlds = transaction.objectStore(WORLD_STORE);
          const current = await requestResult<LocalWorldRecord | undefined>(worlds.get(input.worldId));
          if (!current) return { status: "missing" };

          if (current.localRevision !== input.expectedLocalRevision) {
            const candidate: LocalWorldConflictCandidate = {
              id: `local-conflict:${this.idFactory()}` as LocalConflictId,
              worldId: input.worldId,
              baseLocalRevision: input.expectedLocalRevision,
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
    const nextLayout = cloneLocalWorldValue(input.nextLayout);
    try {
      return await inTransaction(this.db, WORLD_STORE, "readwrite", async (transaction) => {
        const worlds = transaction.objectStore(WORLD_STORE);
        const current = await requestResult<LocalWorldRecord | undefined>(worlds.get(input.worldId));
        if (!current) return { status: "missing" };
        if (current.layoutRevision !== input.expectedLayoutRevision) {
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

  allocateObjectId(worldId: LocalWorldId): LocalObjectId {
    return `${worldId}:object:${this.idFactory()}` as LocalObjectId;
  }

  allocateRelationshipId(worldId: LocalWorldId): LocalRelationshipId {
    return `${worldId}:relationship:${this.idFactory()}` as LocalRelationshipId;
  }
}
