import { afterEach, expect, it, vi } from "vitest";
import { planScenePositionKey, readPlanScenePosition, writePlanScenePosition } from "./planScenePosition";

afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });

it("partitions saved scene IDs by exact World and Plan, including separator characters", () => {
  writePlanScenePosition("a:b", "c", "scene:one");
  writePlanScenePosition("a", "b:c", "scene:two");
  expect(readPlanScenePosition("a:b", "c")).toBe("scene:one");
  expect(readPlanScenePosition("a", "b:c")).toBe("scene:two");
  expect(readPlanScenePosition("other", "c")).toBeNull();
  writePlanScenePosition("a:b", "c", null);
  expect(readPlanScenePosition("a:b", "c")).toBeNull();
  expect(readPlanScenePosition("a", "b:c")).toBe("scene:two");
});

it.each(["not json", "null", "{}", "[]", "42", '\"\"', '\"  \"'])("ignores malformed or empty navigation memory %s", (raw) => {
  sessionStorage.setItem(planScenePositionKey("world", "plan"), raw);
  expect(readPlanScenePosition("world", "plan")).toBeNull();
});

it("tolerates unavailable storage without affecting edits", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => { throw new Error("denied"); });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new Error("quota"); });
  vi.spyOn(Storage.prototype, "removeItem").mockImplementation(() => { throw new Error("denied"); });
  expect(readPlanScenePosition("world", "plan")).toBeNull();
  expect(() => writePlanScenePosition("world", "plan", "scene:one")).not.toThrow();
  expect(() => writePlanScenePosition("world", "plan", null)).not.toThrow();
});
