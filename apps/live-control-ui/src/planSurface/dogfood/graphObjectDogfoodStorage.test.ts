import { beforeEach, describe, expect, it } from "vitest";

import { fixturePlanSessionDescriptor, FIXTURE_DOC_ID, workspaceDocumentStorageKey } from "../config/planSessionDescriptor";
import {
  addNodeToDogfoodList,
  createEmptyGraphObjectDogfoodState,
  removeNodeFromDogfoodList,
  setNodeNotes,
  setNodeUsefulness,
} from "./graphObjectDogfoodModel";
import {
  clearGraphObjectDogfoodState,
  graphObjectDogfoodStorageKey,
  loadGraphObjectDogfoodState,
  saveGraphObjectDogfoodState,
} from "./graphObjectDogfoodStorage";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

describe("graphObjectDogfoodStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("uses campaign and document id in the storage key", () => {
    expect(graphObjectDogfoodStorageKey(sessionDescriptor)).toBe(
      `dmb.planGraphObjectDogfood.longmont-c2.${FIXTURE_DOC_ID}`,
    );
  });

  it("persists usefulness and notes locally", () => {
    let state = createEmptyGraphObjectDogfoodState();
    state = addNodeToDogfoodList(state, "npc-glowkindle");
    state = setNodeUsefulness(state, "npc-glowkindle", "useful");
    state = setNodeNotes(state, "npc-glowkindle", "Good summary and relationships.");

    saveGraphObjectDogfoodState(localStorage, sessionDescriptor, state);
    const loaded = loadGraphObjectDogfoodState(localStorage, sessionDescriptor);

    expect(loaded.addedNodeIds).toEqual(["npc-glowkindle"]);
    expect(loaded.usefulnessByNodeId["npc-glowkindle"]).toBe("useful");
    expect(loaded.notesByNodeId["npc-glowkindle"]).toBe("Good summary and relationships.");
  });

  it("does not duplicate on add", () => {
    let state = createEmptyGraphObjectDogfoodState();
    state = addNodeToDogfoodList(state, "npc-glowkindle");
    state = addNodeToDogfoodList(state, "npc-glowkindle");
    expect(state.addedNodeIds).toEqual(["npc-glowkindle"]);
  });

  it("remove tracks removed ids without implying graph deletion", () => {
    let state = addNodeToDogfoodList(createEmptyGraphObjectDogfoodState(), "npc-glowkindle");
    state = removeNodeFromDogfoodList(state, "npc-glowkindle");
    expect(state.addedNodeIds).toEqual([]);
    expect(state.removedNodeIds).toEqual(["npc-glowkindle"]);
  });

  it("clear removes only dogfood storage", () => {
    const canvasKey = workspaceDocumentStorageKey(FIXTURE_DOC_ID);
    localStorage.setItem(canvasKey, JSON.stringify({ doc: "board" }));
    saveGraphObjectDogfoodState(
      localStorage,
      sessionDescriptor,
      addNodeToDogfoodList(createEmptyGraphObjectDogfoodState(), "npc-glowkindle"),
    );

    clearGraphObjectDogfoodState(localStorage, sessionDescriptor);

    expect(localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor))).toBeNull();
    expect(localStorage.getItem(canvasKey)).toContain("board");
  });
});
