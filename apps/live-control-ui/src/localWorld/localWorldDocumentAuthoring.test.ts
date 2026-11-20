import { describe, expect, it } from "vitest";
import {
  emptyLocalWorldPackageData,
  encodeWorldNotes,
  LOCAL_WORLD_NOTES_DOCUMENT_ID,
  LOCAL_WORLD_NOTES_DOCUMENT_PATH,
  LOCAL_WORLD_NOTES_MAX_BYTES,
  readWorldNotesPackageData,
  writeWorldNotesPackageData,
} from "./localWorldDocumentAuthoring";
import type { LocalWorldId, LocalWorldPackageData } from "./localWorldRepository";

const worldId = "local-world:notes-fixture" as LocalWorldId;

describe("local World notes package adapter", () => {
  it("round-trips valid Unicode and keeps a concrete byte limit", () => {
    const encoded = encodeWorldNotes("# Nótt\n\nA quiet harbor 🌊\n");
    expect("error" in encoded).toBe(false);
    if ("error" in encoded) return;
    const written = writeWorldNotesPackageData(emptyLocalWorldPackageData(worldId), worldId, encoded.bytes);
    expect(written.status).toBe("written");
    if (written.status !== "written") return;
    expect(readWorldNotesPackageData(written.data, worldId)).toEqual({
      status: "found",
      markdown: "# Nótt\n\nA quiet harbor 🌊\n",
      documentExists: true,
    });
    expect(encodeWorldNotes("x".repeat(LOCAL_WORLD_NOTES_MAX_BYTES + 1))).toEqual({
      error: "World notes exceed the 1 MiB local document limit.",
    });
  });

  it("preserves existing source and asset members while updating only the reserved notes member", () => {
    const sourcePath = "documents/source/field-notes.txt";
    const assetPath = `assets/${"a".repeat(64)}`;
    const data: LocalWorldPackageData = {
      ...emptyLocalWorldPackageData(worldId),
      documents: [{ id: "source:field-notes", status: "bundled", path: sourcePath, mediaType: "text/plain", locator: null }],
      assets: [{ id: "asset:map", status: "bundled", path: assetPath, mediaType: "image/png", locator: null }],
      bundledMembers: { [sourcePath]: [0, 1, 255], [assetPath]: [137, 80, 78, 71] },
    };
    const updated = writeWorldNotesPackageData(data, worldId, [35, 32, 78, 111, 116, 101, 115]);
    expect(updated.status).toBe("written");
    if (updated.status !== "written") return;
    expect(updated.data.documents).toEqual([
      ...data.documents,
      { id: LOCAL_WORLD_NOTES_DOCUMENT_ID, status: "bundled", path: LOCAL_WORLD_NOTES_DOCUMENT_PATH, mediaType: "text/markdown", locator: null },
    ]);
    expect(updated.data.bundledMembers[sourcePath]).toEqual([0, 1, 255]);
    expect(updated.data.bundledMembers[assetPath]).toEqual([137, 80, 78, 71]);
    expect(updated.data.bundledMembers[LOCAL_WORLD_NOTES_DOCUMENT_PATH]).toEqual([35, 32, 78, 111, 116, 101, 115]);
    expect(data.documents).toHaveLength(1);
    expect(data.bundledMembers[LOCAL_WORLD_NOTES_DOCUMENT_PATH]).toBeUndefined();
  });

  it("refuses a same-path imported document and malformed UTF-8 without changing source data", () => {
    const collision: LocalWorldPackageData = {
      ...emptyLocalWorldPackageData(worldId),
      documents: [{ id: "imported:notes", status: "bundled", path: LOCAL_WORLD_NOTES_DOCUMENT_PATH, mediaType: "text/plain", locator: null }],
      bundledMembers: { [LOCAL_WORLD_NOTES_DOCUMENT_PATH]: [0xff] },
    };
    const before = structuredClone(collision);
    expect(writeWorldNotesPackageData(collision, worldId, [65]).status).toBe("error");
    expect(readWorldNotesPackageData(collision, worldId).status).toBe("error");
    expect(collision).toEqual(before);
  });

  it("rejects lone surrogate input rather than replacing it silently", () => {
    expect(encodeWorldNotes("bad\ud800text")).toEqual({
      error: "World notes contain invalid Unicode and were not saved.",
    });
  });
});
