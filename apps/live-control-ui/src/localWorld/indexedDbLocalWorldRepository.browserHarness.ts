import {
  type IndexedDbLocalWorldRepositoryOptions,
  LOCAL_WORLD_DATABASE_SCHEMA_VERSION,
  LOCAL_WORLD_DATABASE_STORES,
  IndexedDbLocalWorldRepository,
  openIndexedDbLocalWorldRepository,
} from "./indexedDbLocalWorldRepository";
import {
  createTestWorld,
  fourNodeWorldFixture,
  sameNameWorldPeopleFixture,
  sequenceLocalIds,
} from "./localWorldContractFixtures";
import type { LocalWorldId, LocalWorldRecord } from "./localWorldRepository";

const output = document.getElementById("result");
const checks: string[] = [];
const repositoryHandles: IndexedDbLocalWorldRepository[] = [];
const rawDatabaseHandles: IDBDatabase[] = [];
const testDatabaseNames = [
  "primary", "migration", "future", "schema", "blocked",
  "world-key-path", "world-auto-increment", "conflict-key-path", "conflict-auto-increment",
  "index-key-path", "index-unique", "index-multi-entry",
];
const token = crypto.randomUUID();
const names = Object.fromEntries(testDatabaseNames.map((name) => [
  name,
  `dmb-local-world-test-${token}-${name}`,
])) as Record<(typeof testDatabaseNames)[number], string>;

function assert(condition: unknown, message: string): void {
  if (!condition) throw new Error(message);
  checks.push(message);
  output!.textContent = `RUNNING ${checks.length}/${message}`;
}

function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.addEventListener("success", () => resolve(request.result), { once: true });
    request.addEventListener("error", () => reject(request.error ?? new Error("IndexedDB request failed.")), { once: true });
  });
}

function deleteDatabase(name: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.deleteDatabase(name);
    request.addEventListener("success", () => resolve(), { once: true });
    request.addEventListener("error", () => reject(request.error ?? new Error("Database deletion failed.")), { once: true });
    request.addEventListener("blocked", () => reject(new Error(`Isolated test database delete was blocked: ${name}`)), { once: true });
  });
}

async function openTestRepository(name: string, options: IndexedDbLocalWorldRepositoryOptions = {}) {
  const result = await openIndexedDbLocalWorldRepository(name, options);
  if (result.status === "opened") repositoryHandles.push(result.repository);
  return result;
}

async function openLegacyVersionOneDatabase(name: string): Promise<{
  readonly db: IDBDatabase;
  readonly worldId: LocalWorldId;
  readonly record: LocalWorldRecord;
}> {
  const worldId = `local-world:legacy-${token}` as LocalWorldId;
  const ids = sequenceLocalIds();
  const fixtureRepository = {
    allocateObjectId: (id: LocalWorldId) => `${id}:object:${ids()}` as LocalWorldRecord["snapshot"]["objects"][number]["id"],
    allocateRelationshipId: (id: LocalWorldId) => `${id}:relationship:${ids()}` as LocalWorldRecord["snapshot"]["relationships"][number]["id"],
  };
  const snapshot = fourNodeWorldFixture(fixtureRepository, worldId);
  const record: LocalWorldRecord = {
    snapshot,
    localRevision: 4,
    publishedRevisionId: null,
    layout: { positions: {}, viewport: { x: 0, y: 0, zoom: 1 }, layoutVersion: 1 },
    layoutRevision: 2,
    history: [{
      id: "local-edit:legacy-v1" as LocalWorldRecord["history"][number]["id"],
      localRevision: 4,
      classification: "buddy-local-only",
      description: "Version-one migration fixture",
    }],
  };
  const candidate = {
    id: "local-conflict:legacy-v1" as const,
    worldId,
    baseLocalRevision: 3,
    currentLocalRevision: 4,
    proposedSnapshot: { ...snapshot, title: "Preserved legacy candidate" },
    edit: { classification: "buddy-local-only" as const, description: "Legacy conflict fixture" },
  };

  const request = indexedDB.open(name, 1);
  request.addEventListener("upgradeneeded", () => {
    request.result.createObjectStore(LOCAL_WORLD_DATABASE_STORES.worlds, { keyPath: "snapshot.worldId" });
    request.result.createObjectStore(LOCAL_WORLD_DATABASE_STORES.conflicts, { keyPath: "id" });
  });
  const db = await requestResult(request);
  rawDatabaseHandles.push(db);
  const transaction = db.transaction([
    LOCAL_WORLD_DATABASE_STORES.worlds,
    LOCAL_WORLD_DATABASE_STORES.conflicts,
  ], "readwrite");
  transaction.objectStore(LOCAL_WORLD_DATABASE_STORES.worlds).add(record);
  transaction.objectStore(LOCAL_WORLD_DATABASE_STORES.conflicts).add(candidate);
  await new Promise<void>((resolve, reject) => {
    transaction.addEventListener("complete", () => resolve(), { once: true });
    transaction.addEventListener("abort", () => reject(transaction.error), { once: true });
  });
  return { db, worldId, record };
}

interface MalformedSchemaOptions {
  readonly worldsKeyPath?: string;
  readonly worldsAutoIncrement?: boolean;
  readonly conflictsKeyPath?: string;
  readonly conflictsAutoIncrement?: boolean;
  readonly indexKeyPath?: string;
  readonly indexUnique?: boolean;
  readonly indexMultiEntry?: boolean;
  readonly omitIndex?: boolean;
}

async function openMalformedCurrentSchema(name: string, options: MalformedSchemaOptions): Promise<IDBDatabase> {
  const worldId = `local-world:preserved-${token}`;
  const request = indexedDB.open(name, LOCAL_WORLD_DATABASE_SCHEMA_VERSION);
  request.addEventListener("upgradeneeded", () => {
    const db = request.result;
    const worlds = db.createObjectStore(LOCAL_WORLD_DATABASE_STORES.worlds, {
      keyPath: options.worldsKeyPath ?? "snapshot.worldId",
      autoIncrement: options.worldsAutoIncrement ?? false,
    });
    const conflicts = db.createObjectStore(LOCAL_WORLD_DATABASE_STORES.conflicts, {
      keyPath: options.conflictsKeyPath ?? "id",
      autoIncrement: options.conflictsAutoIncrement ?? false,
    });
    if (!options.omitIndex) {
      conflicts.createIndex("worldId", options.indexKeyPath ?? "worldId", {
        unique: options.indexUnique ?? false,
        multiEntry: options.indexMultiEntry ?? false,
      });
    }
    worlds.add({ id: "preserved-world", worldId, snapshot: { worldId }, marker: "retain-world" });
    conflicts.add({ id: "preserved-candidate", worldId, marker: "retain-candidate" });
  });
  return requestResult(request);
}

async function run(): Promise<void> {
  const unavailable = await openTestRepository(names.primary, { factory: null });
  assert(unavailable.status === "error" && unavailable.code === "unavailable", "unavailable storage is explicit");

  const opened = await openTestRepository(names.primary, { idFactory: sequenceLocalIds() });
  assert(opened.status === "opened", "native IndexedDB opens an isolated database");
  if (opened.status !== "opened") throw new Error(opened.message);
  let repository: IndexedDbLocalWorldRepository | undefined = opened.repository;
  const initial = await createTestWorld(repository);
  const fourNodes = fourNodeWorldFixture(repository, initial.snapshot.worldId);
  const sameNamePeople = sameNameWorldPeopleFixture(repository, initial.snapshot.worldId);
  const proposed = { ...fourNodes, objects: [...fourNodes.objects, ...sameNamePeople] };
  const committed = await repository.commitSemanticEdit({
    worldId: initial.snapshot.worldId,
    expectedLocalRevision: 0,
    nextSnapshot: proposed,
    edit: { classification: "buddy-local-only", description: "Browser test fixture" },
  });
  assert(committed.status === "committed", "semantic snapshot and history commit to IndexedDB");
  if (committed.status !== "committed") throw new Error(committed.status === "error" ? committed.message : committed.status);
  assert(committed.record.snapshot.objects.length === 6, "fixture keeps same-name entities as distinct nodes");
  assert(committed.record.snapshot.objects[4].id !== committed.record.snapshot.objects[5].id, "same-name nodes retain distinct local IDs");

  (proposed.objects[0].properties as Record<string, unknown>).role = "caller changed input";
  (committed.record.snapshot.objects[1].properties as Record<string, unknown>).role = "caller changed result";
  let read = await repository.readWorld(initial.snapshot.worldId);
  assert(
    read.status === "found"
      && (read.record.snapshot.objects[0].properties as Record<string, unknown>).role === "traveler",
    "structured-clone storage isolates input and output objects",
  );
  if (read.status !== "found") throw new Error(read.status);

  const layout = await repository.writeLayout({
    worldId: initial.snapshot.worldId,
    expectedLayoutRevision: 0,
    nextLayout: {
      positions: { [read.record.snapshot.objects[0].id]: { x: 90, y: 130 } },
      viewport: { x: 2, y: -4, zoom: 1.2 },
      layoutVersion: 1,
    },
  });
  assert(layout.status === "written" && layout.record.localRevision === 1 && layout.record.history.length === 2, "layout writes advance presentation revision only");

  const peerOpen = await openTestRepository(names.primary, { idFactory: sequenceLocalIds() });
  assert(peerOpen.status === "opened", "a second repository connection participates in CAS race");
  if (peerOpen.status !== "opened") throw new Error(peerOpen.message);
  const concurrent = await Promise.all([
    peerOpen.repository.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 1,
      nextSnapshot: { ...read.record.snapshot, title: "Concurrent A" },
      edit: { classification: "buddy-local-only", description: "Concurrent A" },
    }),
    repository.commitSemanticEdit({
      worldId: initial.snapshot.worldId,
      expectedLocalRevision: 1,
      nextSnapshot: { ...read.record.snapshot, title: "Concurrent B" },
      edit: { classification: "buddy-local-only", description: "Concurrent B" },
    }),
  ]);
  peerOpen.repository.close();
  assert(concurrent.filter((result) => result.status === "committed").length === 1, "overlapping IndexedDB CAS writes commit exactly once");
  assert(concurrent.filter((result) => result.status === "conflict").length === 1, "second IndexedDB CAS write returns conflict");
  const winner = concurrent.find((result) => result.status === "committed");
  const loser = concurrent.find((result) => result.status === "conflict");
  if (!winner || winner.status !== "committed" || !loser || loser.status !== "conflict") throw new Error("CAS results did not include one commit and one conflict");
  assert(loser.candidate.proposedSnapshot.title !== winner.record.snapshot.title, "losing candidate remains separate from current snapshot");
  assert(loser.candidate.proposedSnapshot.objects.length === 6 && loser.candidate.proposedSnapshot.relationships.length === 2, "candidate retains the complete semantic proposal");

  const secondaryWorld = await createTestWorld(repository, "Untouched secondary World");
  const semanticHeaderRequest = {
    worldId: initial.snapshot.worldId,
    expectedLocalRevision: 1,
    nextSnapshot: { ...winner.record.snapshot, title: "Mutation-after-call candidate" },
    edit: { classification: "buddy-local-only" as const, description: "Header mutation regression" },
  };
  const pendingSemanticHeader = repository.commitSemanticEdit(semanticHeaderRequest);
  semanticHeaderRequest.worldId = secondaryWorld.snapshot.worldId;
  semanticHeaderRequest.expectedLocalRevision = 2;
  const semanticHeaderResult = await pendingSemanticHeader;
  assert(
    semanticHeaderResult.status === "conflict"
      && semanticHeaderResult.candidate.worldId === initial.snapshot.worldId
      && semanticHeaderResult.candidate.baseLocalRevision === 1
      && semanticHeaderResult.candidate.proposedSnapshot.worldId === initial.snapshot.worldId,
    "semantic CAS and identity headers are captured before IndexedDB request awaits",
  );
  const secondaryRead = await repository.readWorld(secondaryWorld.snapshot.worldId);
  assert(
    secondaryRead.status === "found" && secondaryRead.record.snapshot.title === "Untouched secondary World",
    "mutating request identity after invocation cannot redirect a semantic write",
  );

  const layoutHeaderRequest = {
    worldId: initial.snapshot.worldId,
    expectedLayoutRevision: 0,
    nextLayout: {
      positions: { [winner.record.snapshot.objects[0].id]: { x: 222, y: 333 } },
      viewport: { x: 0, y: 0, zoom: 1 },
      layoutVersion: 1,
    },
  };
  const pendingLayoutHeader = repository.writeLayout(layoutHeaderRequest);
  layoutHeaderRequest.worldId = secondaryWorld.snapshot.worldId;
  layoutHeaderRequest.expectedLayoutRevision = 1;
  const layoutHeaderResult = await pendingLayoutHeader;
  assert(
    layoutHeaderResult.status === "conflict" && layoutHeaderResult.record.layoutRevision === 1,
    "layout CAS and identity headers are captured before IndexedDB request awaits",
  );
  const secondaryAfterLayout = await repository.readWorld(secondaryWorld.snapshot.worldId);
  assert(
    secondaryAfterLayout.status === "found" && secondaryAfterLayout.record.layoutRevision === 0,
    "mutating request identity after invocation cannot redirect a layout write",
  );

  const createHeaderRequest = { title: "Captured at invocation" };
  const pendingCreateHeader = repository.createWorld(createHeaderRequest);
  createHeaderRequest.title = "Mutated after invocation";
  const createHeaderResult = await pendingCreateHeader;
  assert(
    createHeaderResult.status === "created" && createHeaderResult.record.snapshot.title === "Captured at invocation",
    "create title is captured before the first transaction await",
  );

  const failureConnection = await openTestRepository(names.primary, {
    idFactory: sequenceLocalIds(),
    beforeWrite: (point) => {
      if (point === "semantic-edit") throw new DOMException("Synthetic quota-shaped abort test", "QuotaExceededError");
    },
  });
  assert(failureConnection.status === "opened", "separate connection opens same isolated test database");
  if (failureConnection.status !== "opened") throw new Error(failureConnection.message);
  const beforeAbort = await repository.readWorld(initial.snapshot.worldId);
  if (beforeAbort.status !== "found") throw new Error("Committed World missing before abort test");
  const injectedFailure = await failureConnection.repository.commitSemanticEdit({
    worldId: initial.snapshot.worldId,
    expectedLocalRevision: beforeAbort.record.localRevision,
    nextSnapshot: { ...beforeAbort.record.snapshot, title: "This abort must preserve the prior value" },
    edit: { classification: "buddy-local-only", description: "Synthetic quota test" },
  });
  failureConnection.repository.close();
  assert(injectedFailure.status === "error" && injectedFailure.message.includes("QuotaExceededError"), "synthetic quota-shaped error aborts IndexedDB transaction");
  const afterAbort = await repository.readWorld(initial.snapshot.worldId);
  assert(afterAbort.status === "found" && afterAbort.record.localRevision === 2, "aborted transaction preserves the prior committed revision");
  const candidates = await repository.readConflictCandidates(initial.snapshot.worldId);
  assert(candidates.status === "found" && candidates.candidates.length === 2, "conflict candidates from CAS and header mutation are retained independently");

  const persistedWorldId = initial.snapshot.worldId;
  repository.close();
  repository = undefined;
  const reopened = await openTestRepository(names.primary, { idFactory: sequenceLocalIds() });
  assert(reopened.status === "opened", "closing and reopening the database preserves state in real Chrome");
  if (reopened.status !== "opened") throw new Error(reopened.message);
  repository = reopened.repository;
  const persisted = await repository.readWorld(persistedWorldId);
  assert(persisted.status === "found" && persisted.record.localRevision === 2, "reopen restores the latest semantic snapshot");
  assert(persisted.status === "found" && persisted.record.layoutRevision === 1, "reopen restores separate layout revision");
  const persistedCandidates = await repository.readConflictCandidates(persistedWorldId);
  assert(persistedCandidates.status === "found" && persistedCandidates.candidates.length === 2, "reopen restores both retained conflict candidates");
  if (persisted.status !== "found") throw new Error(persisted.status);
  (persisted.record.snapshot.objects[0].properties as Record<string, unknown>).role = "mutated read result";
  const afterReadMutation = await repository.readWorld(persistedWorldId);
  assert(
    afterReadMutation.status === "found"
      && (afterReadMutation.record.snapshot.objects[0].properties as Record<string, unknown>).role === "traveler",
    "reopened data is not aliased to read results",
  );
  repository.close();
  repository = undefined;
  await deleteDatabase(names.primary);

  const legacy = await openLegacyVersionOneDatabase(names.migration);
  legacy.db.close();
  const migration = await openTestRepository(names.migration, { idFactory: sequenceLocalIds() });
  assert(migration.status === "opened", "v1 schema migrates to v2");
  if (migration.status !== "opened") throw new Error(migration.message);
  assert(migration.repository.databaseVersion === LOCAL_WORLD_DATABASE_SCHEMA_VERSION, "migration reaches the declared database version");
  const migrated = await migration.repository.readWorld(legacy.worldId);
  const migratedCandidates = await migration.repository.readConflictCandidates(legacy.worldId);
  assert(migrated.status === "found" && migrated.record.snapshot.objects.length === 4, "schema upgrade preserves the semantic snapshot");
  assert(migratedCandidates.status === "found" && migratedCandidates.candidates[0]?.proposedSnapshot.title === "Preserved legacy candidate", "schema upgrade preserves conflict candidates and indexes them");
  migration.repository.close();
  await deleteDatabase(names.migration);

  const malformedSchemas: Array<{
    readonly name: string;
    readonly label: string;
    readonly options: MalformedSchemaOptions;
  }> = [
    { name: names.schema, label: "missing required index", options: { omitIndex: true } },
    { name: names["world-key-path"], label: "world store keyPath", options: { worldsKeyPath: "worldId" } },
    { name: names["world-auto-increment"], label: "world store autoIncrement", options: { worldsAutoIncrement: true } },
    { name: names["conflict-key-path"], label: "conflict store keyPath", options: { conflictsKeyPath: "worldId" } },
    { name: names["conflict-auto-increment"], label: "conflict store autoIncrement", options: { conflictsAutoIncrement: true } },
    { name: names["index-key-path"], label: "conflict lookup index keyPath", options: { indexKeyPath: "id" } },
    { name: names["index-unique"], label: "conflict lookup index unique flag", options: { indexUnique: true } },
    { name: names["index-multi-entry"], label: "conflict lookup index multiEntry flag", options: { indexMultiEntry: true } },
  ];
  for (const malformed of malformedSchemas) {
    const invalidDb = await openMalformedCurrentSchema(malformed.name, malformed.options);
    const originalWorlds = invalidDb.transaction(LOCAL_WORLD_DATABASE_STORES.worlds, "readonly").objectStore(LOCAL_WORLD_DATABASE_STORES.worlds);
    const originalConflicts = invalidDb.transaction(LOCAL_WORLD_DATABASE_STORES.conflicts, "readonly").objectStore(LOCAL_WORLD_DATABASE_STORES.conflicts);
    const originalIndex = originalConflicts.indexNames.contains("worldId")
      ? originalConflicts.index("worldId")
      : undefined;
    const originalSchema = {
      version: invalidDb.version,
      worldsKeyPath: originalWorlds.keyPath,
      worldsAutoIncrement: originalWorlds.autoIncrement,
      conflictsKeyPath: originalConflicts.keyPath,
      conflictsAutoIncrement: originalConflicts.autoIncrement,
      indexKeyPath: originalIndex?.keyPath,
      indexUnique: originalIndex?.unique,
      indexMultiEntry: originalIndex?.multiEntry,
    };
    invalidDb.close();
    const refusal = await openTestRepository(malformed.name, { idFactory: sequenceLocalIds() });
    assert(
      refusal.status === "error" && refusal.code === "incompatible-schema",
      `same-version schema with wrong ${malformed.label} fails closed`,
    );
    if (refusal.status === "opened") {
      refusal.repository.close();
      throw new Error(`Malformed same-version schema unexpectedly opened: ${malformed.label}`);
    }
    const preservedDb = await requestResult(indexedDB.open(malformed.name));
    const tx = preservedDb.transaction([LOCAL_WORLD_DATABASE_STORES.worlds, LOCAL_WORLD_DATABASE_STORES.conflicts], "readonly");
    const preservedWorldStore = tx.objectStore(LOCAL_WORLD_DATABASE_STORES.worlds);
    const preservedConflictStore = tx.objectStore(LOCAL_WORLD_DATABASE_STORES.conflicts);
    const preservedIndex = preservedConflictStore.indexNames.contains("worldId")
      ? preservedConflictStore.index("worldId")
      : undefined;
    const [worldMarkers, conflictMarkers] = await Promise.all([
      requestResult<Array<{ readonly marker?: string }>>(preservedWorldStore.getAll()),
      requestResult<Array<{ readonly marker?: string }>>(preservedConflictStore.getAll()),
    ]);
    assert(
      preservedDb.version === LOCAL_WORLD_DATABASE_SCHEMA_VERSION
        && preservedWorldStore.keyPath === originalSchema.worldsKeyPath
        && preservedWorldStore.autoIncrement === originalSchema.worldsAutoIncrement
        && preservedConflictStore.keyPath === originalSchema.conflictsKeyPath
        && preservedConflictStore.autoIncrement === originalSchema.conflictsAutoIncrement
        && preservedIndex?.keyPath === originalSchema.indexKeyPath
        && preservedIndex?.unique === originalSchema.indexUnique
        && preservedIndex?.multiEntry === originalSchema.indexMultiEntry
        && worldMarkers.some((record) => record.marker === "retain-world")
        && conflictMarkers.some((record) => record.marker === "retain-candidate"),
      `schema refusal preserves schema and data for ${malformed.label}`,
    );
    preservedDb.close();
    await deleteDatabase(malformed.name);
  }

  const futureDbRequest = indexedDB.open(names.future, LOCAL_WORLD_DATABASE_SCHEMA_VERSION + 1);
  futureDbRequest.addEventListener("upgradeneeded", () => futureDbRequest.result.createObjectStore("future-only", { keyPath: "id" }));
  const futureDb = await requestResult(futureDbRequest);
  futureDb.close();
  const futureRefusal = await openTestRepository(names.future, { idFactory: sequenceLocalIds() });
  assert(futureRefusal.status === "error" && futureRefusal.code === "incompatible-version", "unknown future schema fails closed");
  const futureUnchanged = await requestResult(indexedDB.open(names.future));
  assert(futureUnchanged.version === LOCAL_WORLD_DATABASE_SCHEMA_VERSION + 1 && futureUnchanged.objectStoreNames.contains("future-only"), "version refusal leaves the future database unchanged");
  futureUnchanged.close();
  await deleteDatabase(names.future);

  const blockedLegacy = await openLegacyVersionOneDatabase(names.blocked);
  const blockedUpgrade = await openTestRepository(names.blocked, { idFactory: sequenceLocalIds() });
  assert(blockedUpgrade.status === "error" && blockedUpgrade.code === "blocked", "blocked version upgrade reports recoverable state");
  blockedLegacy.db.close();
  await new Promise((resolve) => setTimeout(resolve, 50));
  const retried = await openTestRepository(names.blocked, { idFactory: sequenceLocalIds() });
  assert(retried.status === "opened", "closing older connection allows safe retry");
  if (retried.status !== "opened") throw new Error(retried.message);
  const recovered = await retried.repository.readWorld(blockedLegacy.worldId);
  assert(recovered.status === "found" && recovered.record.snapshot.objects.length === 4, "blocked upgrade preserves recoverable prior data");
  retried.repository.close();
  await deleteDatabase(names.blocked);

  output!.textContent = JSON.stringify({ status: "PASS", browser: navigator.userAgent, notes: [
    "Real system Chrome and native IndexedDB; fresh temporary profile and test-only database names.",
    "QuotaExceededError was injected to verify the abort path; actual quota exhaustion was not induced.",
    "Connection close/reopen tests persistence within the temporary browser profile; power-loss and browser eviction are not tested.",
  ], checks }, null, 2);
}

run().catch(async (error: unknown) => {
  output!.textContent = JSON.stringify({
    status: "FAIL",
    browser: navigator.userAgent,
    checks,
    error: error instanceof Error ? `${error.name}: ${error.message}\n${error.stack ?? ""}` : String(error),
  }, null, 2);
  for (const repository of repositoryHandles) {
    try { repository.close(); } catch { /* Continue closing other isolated handles. */ }
  }
  for (const db of rawDatabaseHandles) {
    try { db.close(); } catch { /* Continue closing other isolated handles. */ }
  }
  for (const name of Object.values(names)) {
    try { await deleteDatabase(name); } catch { /* Temporary profile removal is the final cleanup boundary. */ }
  }
});
