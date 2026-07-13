import type { PlanSessionDescriptor } from "../types";
import {
  createEmptyGraphObjectDogfoodState,
  type GraphObjectDogfoodState,
  type GraphObjectDogfoodUsefulness,
} from "./graphObjectDogfoodModel";

const USEFULNESS_VALUES = new Set<GraphObjectDogfoodUsefulness>([
  "useful",
  "thin",
  "confusing",
  "wrong",
  "unknown",
]);

export function graphObjectDogfoodStorageKey(
  sessionDescriptor: PlanSessionDescriptor,
): string {
  return `dmb.planGraphObjectDogfood.${sessionDescriptor.campaignId}.session-${sessionDescriptor.prepSession}`;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((entry) => String(entry ?? "").trim())
    .filter(Boolean);
}

function asStringRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object") return {};
  const out: Record<string, string> = {};
  for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
    const id = String(key || "").trim();
    if (!id) continue;
    out[id] = String(entry ?? "");
  }
  return out;
}

function asUsefulnessRecord(value: unknown): Record<string, GraphObjectDogfoodUsefulness> {
  if (!value || typeof value !== "object") return {};
  const out: Record<string, GraphObjectDogfoodUsefulness> = {};
  for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
    const id = String(key || "").trim();
    const usefulness = String(entry ?? "") as GraphObjectDogfoodUsefulness;
    if (!id || !USEFULNESS_VALUES.has(usefulness)) continue;
    out[id] = usefulness;
  }
  return out;
}

export function loadGraphObjectDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
): GraphObjectDogfoodState {
  const key = graphObjectDogfoodStorageKey(sessionDescriptor);
  const raw = storage.getItem(key);
  if (!raw) {
    return createEmptyGraphObjectDogfoodState();
  }
  try {
    const parsed = JSON.parse(raw) as Partial<GraphObjectDogfoodState>;
    return {
      addedNodeIds: asStringArray(parsed.addedNodeIds),
      viewedNodeIds: asStringArray(parsed.viewedNodeIds),
      removedNodeIds: asStringArray(parsed.removedNodeIds),
      notesByNodeId: asStringRecord(parsed.notesByNodeId),
      usefulnessByNodeId: asUsefulnessRecord(parsed.usefulnessByNodeId),
    };
  } catch {
    return createEmptyGraphObjectDogfoodState();
  }
}

export function saveGraphObjectDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
  state: GraphObjectDogfoodState,
): void {
  const key = graphObjectDogfoodStorageKey(sessionDescriptor);
  storage.setItem(key, JSON.stringify(state));
}

export function clearGraphObjectDogfoodState(
  storage: Storage,
  sessionDescriptor: PlanSessionDescriptor,
): void {
  storage.removeItem(graphObjectDogfoodStorageKey(sessionDescriptor));
}
