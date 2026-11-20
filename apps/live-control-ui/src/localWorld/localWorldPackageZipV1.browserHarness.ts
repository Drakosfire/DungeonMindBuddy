import { openIndexedDbLocalWorldRepository } from "./indexedDbLocalWorldRepository";
import { encodeLocalWorldPackageV1 } from "./localWorldPackageV1";
import { decodeLocalWorldPackageZipV1, encodeLocalWorldPackageZipV1 } from "./localWorldPackageZipV1";

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) throw new Error(message);
}

async function deleteDatabase(name: string): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const request = indexedDB.deleteDatabase(name);
    request.addEventListener("success", () => resolve(), { once: true });
    request.addEventListener("error", () => reject(request.error ?? new Error("Could not delete isolated test database.")), { once: true });
    request.addEventListener("blocked", () => reject(new Error("Isolated test database deletion was blocked.")), { once: true });
  });
}

async function run(): Promise<void> {
  const output = document.querySelector<HTMLElement>("#result");
  assert(output, "Browser harness output element is missing.");
  const databaseName = `local-world-zip-transport-${crypto.randomUUID()}`;
  let closeRepository: (() => void) | undefined;
  try {
    assert(typeof crypto.subtle?.digest === "function", "Native Web Crypto SHA-256 is unavailable.");
    const opened = await openIndexedDbLocalWorldRepository(databaseName);
    assert(opened.status === "opened", opened.status === "error" ? opened.message : "IndexedDB did not open.");
    closeRepository = () => opened.repository.close();
    const created = await opened.repository.createWorld({ title: "Temporary browser ZIP test" });
    assert(created.status === "created", created.status === "error" ? created.message : "IndexedDB did not create the isolated World.");
    const packageResult = await encodeLocalWorldPackageV1(created.record);
    assert(packageResult.status === "encoded", packageResult.status === "error" ? packageResult.message : "Package core did not encode the repository record.");
    const archiveResult = await encodeLocalWorldPackageZipV1(packageResult.members);
    assert(archiveResult.status === "encoded", archiveResult.status === "error" ? archiveResult.message : "ZIP transport did not encode the package.");
    const decoded = await decodeLocalWorldPackageZipV1(archiveResult.blob);
    assert(decoded.status === "staged", decoded.status === "error" ? `${decoded.code}: ${decoded.message}` : "ZIP transport did not stage the package.");
    assert(decoded.parsed.candidate.record.snapshot.worldId === created.record.snapshot.worldId, "Local World identity changed through native-browser ZIP transport.");
    assert(decoded.parsed.candidate.record.localRevision === 0, "Revision-zero repository seed changed through ZIP transport.");
    output.dataset.status = "passed";
    output.textContent = JSON.stringify({ status: "passed", runtime: "native browser", crypto: "Web Crypto", zipBlobBytes: archiveResult.blob.size, repositorySeedRevision: 0, decode: "validated staged member map", databaseWrites: "isolated create only; ZIP decode does not write" });
  } finally {
    closeRepository?.();
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
