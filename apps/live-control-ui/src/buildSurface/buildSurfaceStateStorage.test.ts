import { describe, expect, it } from "vitest";

import {
  BUILD_SURFACE_STATE_SCHEMA,
  buildBuildSurfaceStateSnapshot,
  buildSurfaceStateStorageKey,
  clearBuildSurfaceState,
  readBuildSurfaceState,
  writeBuildSurfaceState,
} from "./buildSurfaceStateStorage";

describe("buildSurfaceStateStorage", () => {
  it("round-trips UI identifiers and draft only", () => {
    const storage = new Map<string, string>();
    const api = {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => {
        storage.set(key, value);
      },
      removeItem: (key: string) => {
        storage.delete(key);
      },
    };

    const snapshot = buildBuildSurfaceStateSnapshot({
      documentId: "doc-1",
      ui: {
        isLocked: false,
        isEditDockOpen: true,
        graphRefSearchQuery: "Glowkindle",
        activeToolId: "build-extraction-run-inspector",
        activeGraphNodeId: "npc:glowkindle",
      },
      draftJson: { type: "doc", content: [{ type: "paragraph" }] },
      now: "2026-08-02T00:00:00.000Z",
    });

    writeBuildSurfaceState(api, snapshot);
    expect(storage.has(buildSurfaceStateStorageKey("doc-1"))).toBe(true);

    const restored = readBuildSurfaceState(api, "doc-1");
    expect(restored).toEqual({
      schema: BUILD_SURFACE_STATE_SCHEMA,
      surfaceId: "build",
      documentId: "doc-1",
      updatedAt: "2026-08-02T00:00:00.000Z",
      ui: {
        isLocked: false,
        isEditDockOpen: true,
        graphRefSearchQuery: "Glowkindle",
        activeToolId: "build-extraction-run-inspector",
        activeGraphNodeId: "npc:glowkindle",
      },
      draft: { tiptap_json: { type: "doc", content: [{ type: "paragraph" }] } },
    });

    clearBuildSurfaceState(api, "doc-1");
    expect(readBuildSurfaceState(api, "doc-1")).toBeNull();
  });

  it("rejects foreign document ids and malformed payloads", () => {
    const storage = {
      getItem: () =>
        JSON.stringify({
          schema: BUILD_SURFACE_STATE_SCHEMA,
          surfaceId: "build",
          documentId: "other",
          updatedAt: "2026-08-02T00:00:00.000Z",
          ui: {
            isLocked: true,
            isEditDockOpen: false,
            graphRefSearchQuery: "",
            activeToolId: null,
            activeGraphNodeId: null,
          },
          draft: null,
        }),
    };
    expect(readBuildSurfaceState(storage, "doc-1")).toBeNull();
  });
});
