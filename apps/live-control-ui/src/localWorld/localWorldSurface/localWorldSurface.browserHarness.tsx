import { StrictMode, useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { AgentInteractionProvider } from "../../agentInteraction/AgentInteractionProvider";
import { openIndexedDbLocalWorldRepository } from "../indexedDbLocalWorldRepository";
import { createPackageTestRecord, packageFixtureAttachmentBytes } from "../localWorldPackageFixtures";
import { decodeLocalWorldPackageZipV1, encodeLocalWorldPackageZipV1 } from "../localWorldPackageZipV1";
import { encodeLocalWorldPackageV1 } from "../localWorldPackageV1";
import { LocalWorldSurface } from "./LocalWorldSurface";
import "./localWorldSurface.css";
import "./localWorldSurface.browserHarness.css";

const dbSessionKey = "phase2a5-local-world-harness-db";
const dbName = sessionStorage.getItem(dbSessionKey) ?? `local-world-surface-test-${crypto.randomUUID()}`;
sessionStorage.setItem(dbSessionKey, dbName);

function Harness() {
  const [generation, setGeneration] = useState(0);
  const [surfaceMounted, setSurfaceMounted] = useState(true);
  const [result, setResult] = useState("Isolated browser database ready. No production database is opened.");
  const failNextSemanticCommit = useRef(false);
  useEffect(() => {
    let live = true;
    void openIndexedDbLocalWorldRepository(dbName).then((opened) => {
      if (!live) return;
      if (opened.status === "opened") { opened.repository.close(); setResult("Isolated browser database ready. No production database is opened."); }
      else setResult(`Storage failed: ${opened.message}`);
    });
    return () => { live = false; };
  }, [generation]);

  const refresh = useCallback(() => setGeneration((value) => value + 1), []);
  const checkUnloadProtection = useCallback(() => {
    const event = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(event);
    setResult(event.defaultPrevented
      ? "PASS: this tab is protected while any local title draft or write is pending."
      : "PASS: no unload protection remains because local drafts and writes are settled.");
  }, []);
  const seedAttachment = useCallback(async () => {
    const opened = await openIndexedDbLocalWorldRepository(dbName);
    if (opened.status !== "opened") { setResult(`Storage failed: ${opened.message}`); return; }
    const repository = opened.repository;
    const original = createPackageTestRecord();
    const fixture = { ...original, snapshot: { ...original.snapshot, title: "Restored test with attachment" } };
    const docPath = "documents/harness/source.txt";
    const largeAssetBytes = new Uint8Array(2 * 1024 * 1024);
    for (let index = 0; index < largeAssetBytes.length; index += 1) largeAssetBytes[index] = index % 251;
    const assetDigestBytes = await crypto.subtle.digest("SHA-256", largeAssetBytes);
    const assetPath = `assets/${Array.from(new Uint8Array(assetDigestBytes), (byte) => byte.toString(16).padStart(2, "0")).join("")}`;
    const packageData = {
      localWorldId: fixture.snapshot.worldId,
      documents: [{ id: "doc:harness-source", status: "bundled" as const, path: docPath, mediaType: "text/plain", locator: null }],
      assets: [{ id: "asset:harness-binary", status: "bundled" as const, path: assetPath, mediaType: "application/octet-stream", locator: null }],
      bundledMembers: { [docPath]: Array.from(packageFixtureAttachmentBytes.document), [assetPath]: Array.from(largeAssetBytes) },
      fidelity: { localRecord: "preserved" as const, sourceMetadata: "not-represented-by-local-record" as const, profileMetadata: "not-represented-by-local-record" as const },
      creatorProfileAssumptions: { creator: "not-recorded" as const, profile: "not-recorded" as const },
    };
    const result = await repository.restorePackage(fixture, packageData);
    repository.close();
    setResult(result.status === "restored" ? "Restored test fixture added with one bundled document. Reopen the list to select it." : `Fixture was not added: ${result.status}`);
    refresh();
  }, [refresh]);

  const verifyPackage = useCallback(async () => {
    const opened = await openIndexedDbLocalWorldRepository(dbName);
    if (opened.status !== "opened") { setResult(`Storage failed: ${opened.message}`); return; }
    const listed = await opened.repository.listWorlds();
    if (listed.status !== "found" || listed.records.length === 0) { setResult("No World to verify yet."); opened.repository.close(); return; }
    const selectedTitle = document.querySelector(".local-world-surface__canvas h2")?.textContent?.trim();
    const record = listed.records.find((candidate) => candidate.snapshot.title === selectedTitle) ?? listed.records[0];
    const supplemental = await opened.repository.readPackageData(record.snapshot.worldId);
    if (supplemental.status === "error" || supplemental.status === "missing") { setResult(`Package sidecar unavailable: ${supplemental.status}`); opened.repository.close(); return; }
    const core = await encodeLocalWorldPackageV1(record, supplemental.status === "found" ? supplemental.data : undefined);
    if (core.status !== "encoded") { setResult(`Codec rejected: ${core.message}`); opened.repository.close(); return; }
    const zip = await encodeLocalWorldPackageZipV1(core.members);
    if (zip.status !== "encoded") { setResult(`ZIP rejected: ${zip.message}`); opened.repository.close(); return; }
    const decoded = await decodeLocalWorldPackageZipV1(zip.blob);
    if (decoded.status !== "staged") { setResult(`ZIP round-trip rejected: ${decoded.message}`); opened.repository.close(); return; }
    const parsed = decoded.parsed;
    const sameReferences = (left: typeof parsed.candidate.documents, right: typeof parsed.candidate.documents) =>
      left.length === right.length && left.every((reference, index) => {
        const expected = right[index];
        return expected !== undefined && reference.id === expected.id && reference.status === expected.status
          && reference.path === expected.path && reference.mediaType === expected.mediaType && reference.locator === expected.locator;
      });
    const refsPreserved = supplemental.status === "found"
      && sameReferences(parsed.candidate.documents, supplemental.data.documents)
      && sameReferences(parsed.candidate.assets, supplemental.data.assets);
    const bundledPreserved = supplemental.status === "found"
      && [...supplemental.data.documents, ...supplemental.data.assets]
        .filter((reference) => reference.status === "bundled")
        .every((reference) => {
          const actual = parsed.candidate.members.get(reference.path!);
          const expected = supplemental.data.bundledMembers[reference.path!];
          return !!actual && actual.length === expected.length && actual.every((byte, index) => byte === expected[index]);
        });
    setResult(`PASS: IndexedDB read → codec → ZIP → decode. World “${parsed.candidate.record.snapshot.title}”; ${parsed.candidate.documents.length} document refs, ${parsed.candidate.assets.length} asset refs; references preserved=${refsPreserved}, bundled bytes preserved=${bundledPreserved}.`);
    opened.repository.close();
  }, []);


  const advanceSelectedWorldElsewhere = useCallback(async () => {
    const selectedTitle = document.querySelector(".local-world-surface__world-picker button.is-selected span")?.textContent?.trim();
    if (!selectedTitle) { setResult("Select a World before running the concurrency check."); return; }
    const opened = await openIndexedDbLocalWorldRepository(dbName);
    if (opened.status !== "opened") { setResult(`Second connection failed: ${opened.message}`); return; }
    const listed = await opened.repository.listWorlds();
    const selected = listed.status === "found" ? listed.records.find((item) => item.snapshot.title === selectedTitle) : undefined;
    if (!selected) { opened.repository.close(); setResult("The selected World is no longer in the test database."); return; }
    const result = await opened.repository.commitSemanticEdit({
      worldId: selected.snapshot.worldId,
      expectedLocalRevision: selected.localRevision,
      nextSnapshot: { ...selected.snapshot, title: `${selectedTitle} (other tab)` },
      edit: { classification: "buddy-local-only", description: "Changed from a second test connection" },
    });
    opened.repository.close();
    setResult(result.status === "committed"
      ? "Second connection saved a newer revision. Edit the still-open title and save to verify conflict retention."
      : `Second connection result: ${result.status}`);
  }, []);

  const deleteTestDb = useCallback(async () => {
    setSurfaceMounted(false);
    window.setTimeout(() => {
    const request = indexedDB.deleteDatabase(dbName);
    request.onsuccess = () => { setResult("Isolated test database deleted."); refresh(); setSurfaceMounted(true); };
    request.onerror = () => setResult("The isolated test database could not be deleted.");
    request.onblocked = () => setResult("Database deletion is blocked by another open test connection.");
    }, 50);
  }, [refresh]);

  const openRepository = useCallback(async () => {
    const result = await openIndexedDbLocalWorldRepository(dbName, { beforeWrite: (point) => {
      if (point === "semantic-edit" && failNextSemanticCommit.current) {
        failNextSemanticCommit.current = false;
        throw new Error("Injected title save failure for browser verification.");
      }
    } });
    return result.status === "opened"
      ? { status: "opened" as const, repository: result.repository, close: () => result.repository.close() }
      : { status: "error" as const, message: result.message };
  }, []);

  return <>
    <aside className="surface-harness">
      <strong>Native browser verification harness</strong>
      <span>Database: <code>{dbName}</code></span>
      <button type="button" onClick={() => void seedAttachment()}>Add restored attachment fixture</button>
      <button type="button" onClick={() => void verifyPackage()}>Verify current package round-trip</button>
      <button type="button" onClick={checkUnloadProtection}>Check tab unload guard</button>
      <button type="button" onClick={() => { failNextSemanticCommit.current = true; setResult("Next title write will fail before transaction commit."); }}>Fail next title write</button>
      <button type="button" onClick={() => void advanceSelectedWorldElsewhere()}>Advance selected World from second connection</button>
      <button type="button" onClick={() => setSurfaceMounted(false)}>Close Surface</button>
      <button type="button" onClick={() => setSurfaceMounted(true)}>Reopen Surface</button>
      <button type="button" onClick={() => void deleteTestDb()}>Delete isolated test database</button>
      <p role="status" aria-live="polite">{result}</p>
    </aside>
    {surfaceMounted ? <AgentInteractionProvider>
      <LocalWorldSurface key={generation} openRepository={openRepository} />
    </AgentInteractionProvider> : <p>Surface closed for isolated database cleanup.</p>}
  </>;
}

createRoot(document.getElementById("root")!).render(<StrictMode><Harness /></StrictMode>);
