import { openIndexedDbLocalWorldRepository, type IndexedDbLocalWorldRepository } from "./indexedDbLocalWorldRepository";
import { encodeLocalWorldPackageV1, parseLocalWorldPackageV1 } from "./localWorldPackageV1";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function deleteDatabase(name: string): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(name);
    request.addEventListener("success", () => resolve(), { once: true });
    request.addEventListener("error", () => reject(request.error ?? new Error("Could not delete isolated browser test database.")), { once: true });
    request.addEventListener("blocked", () => reject(new Error("Isolated browser test database deletion was blocked.")), { once: true });
  });
}

async function run(): Promise<void> {
  const output = document.querySelector<HTMLElement>("#result");
  assert(output, "Browser harness result element is missing.");
  const databaseName = `local-world-package-crypto-test-${crypto.randomUUID()}`;
  let repository: IndexedDbLocalWorldRepository | undefined;
  try {
    assert(typeof crypto.subtle?.digest === "function", "Native browser Web Crypto SHA-256 is unavailable.");
    const opened = await openIndexedDbLocalWorldRepository(databaseName);
    assert(opened.status === "opened", opened.status === "error" ? opened.message : "IndexedDB did not open.");
    repository = opened.repository;

    const created = await repository.createWorld({ title: "Temporary browser codec test" });
    assert(created.status === "created", created.status === "error" ? created.message : "The IndexedDB adapter did not create a World.");
    assert(created.record.localRevision === 0 && created.record.history[0]?.localRevision === 0, "Repository seed did not exercise revision zero.");
    const seedPackage = await encodeLocalWorldPackageV1(created.record);
    assert(seedPackage.status === "encoded", seedPackage.status === "error" ? seedPackage.message : "Seed encoding failed.");
    const parsedSeed = await parseLocalWorldPackageV1(seedPackage.members);
    assert(parsedSeed.status === "staged", parsedSeed.status === "error" ? parsedSeed.message : "Seed parsing failed.");
    assert(parsedSeed.candidate.record.localRevision === 0 && parsedSeed.candidate.record.history[0]?.localRevision === 0, "Revision-zero seed did not survive native browser round-trip.");

    const edited = await repository.commitSemanticEdit({
      worldId: created.record.snapshot.worldId,
      expectedLocalRevision: created.record.localRevision,
      nextSnapshot: { ...created.record.snapshot, title: "Temporary browser codec test, edited" },
      edit: { classification: "buddy-local-only", description: "Updated test title" },
    });
    assert(edited.status === "committed", edited.status === "error" ? edited.message : "The IndexedDB adapter did not commit the semantic test edit.");
    const laidOut = await repository.writeLayout({
      worldId: created.record.snapshot.worldId,
      expectedLayoutRevision: edited.record.layoutRevision,
      nextLayout: { ...edited.record.layout, viewport: { ...edited.record.layout.viewport, x: 12 } },
    });
    assert(laidOut.status === "written", laidOut.status === "error" ? laidOut.message : "The IndexedDB adapter did not write the presentation test layout.");

    const encoded = await encodeLocalWorldPackageV1(laidOut.record);
    assert(encoded.status === "encoded", encoded.status === "error" ? encoded.message : "Updated record encoding failed.");
    const parsed = await parseLocalWorldPackageV1(encoded.members);
    assert(parsed.status === "staged", parsed.status === "error" ? parsed.message : "Updated record parsing failed.");
    assert(parsed.candidate.record.localRevision === 1 && parsed.candidate.record.layoutRevision === 1, "Updated semantic and layout revisions did not survive the browser round-trip.");
    assert(parsed.candidate.record.snapshot.title.endsWith("edited"), "Updated title did not survive the browser round-trip.");
    output.dataset.status = "passed";
    output.textContent = JSON.stringify({ status: "passed", crypto: "native Web Crypto SHA-256", repository: "native IndexedDB", revisionZero: true, editedRoundTrip: true });
  } finally {
    repository?.close();
    await deleteDatabase(databaseName);
  }
}

void run().catch((error: unknown) => {
  const output = document.querySelector<HTMLElement>("#result");
  if (output) {
    output.dataset.status = "failed";
    output.textContent = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  }
});
