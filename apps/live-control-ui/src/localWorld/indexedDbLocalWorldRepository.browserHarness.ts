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
const testDatabaseNames = ["primary", "migration", "future", "schema", "blocked"];
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
  assert(candidates.status === "found" && candidates.candidates.length === 1, "conflict candidate is retained independently");

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
  assert(persistedCandidates.status === "found" && persistedCandidates.candidates.length === 1, "reopen restores the losing candidate");
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

  const invalidSchemaRequest = indexedDB.open(names.schema, LOCAL_WORLD_DATABASE_SCHEMA_VERSION);
  invalidSchemaRequest.addEventListener("upgradeneeded", () => {
    invalidSchemaRequest.result.createObjectStore(LOCAL_WORLD_DATABASE_STORES.worlds, { keyPath: "snapshot.worldId" });
    invalidSchemaRequest.result.createObjectStore(LOCAL_WORLD_DATABASE_STORES.conflicts, { keyPath: "id" });
  });
  const invalidSchemaDb = await requestResult(invalidSchemaRequest);
  invalidSchemaDb.close();
  const schemaRefusal = await openTestRepository(names.schema, { idFactory: sequenceLocalIds() });
  assert(schemaRefusal.status === "error" && schemaRefusal.code === "incompatible-schema", "current version with missing required index fails closed");
  const schemaUnchanged = await requestResult(indexedDB.open(names.schema));
  assert(
    schemaUnchanged.version === LOCAL_WORLD_DATABASE_SCHEMA_VERSION
      && schemaUnchanged.objectStoreNames.contains(LOCAL_WORLD_DATABASE_STORES.worlds)
      && !schemaUnchanged.transaction(LOCAL_WORLD_DATABASE_STORES.conflicts, "readonly").objectStore(LOCAL_WORLD_DATABASE_STORES.conflicts).indexNames.contains("worldId"),
    "schema refusal leaves the incompatible database inspectable and unchanged",
  );
  schemaUnchanged.close();
  await deleteDatabase(names.schema);

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
