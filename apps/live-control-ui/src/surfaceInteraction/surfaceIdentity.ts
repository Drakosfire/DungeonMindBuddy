/**
 * Exact surface identity helpers (SIH-01).
 *
 * Authority: handoff §6.2. Identity is exact `surfaceId` + opaque `instanceKey`;
 * labels never participate and no delimiter joining is permitted.
 */

import type {
  SurfaceInteractionIdentity,
  SurfaceInteractionInstancePart,
} from "./types";

function assertEncodablePart(
  part: SurfaceInteractionInstancePart,
  index: number,
): void {
  if (part === null) return;
  const kind = typeof part;
  if (kind === "string" || kind === "boolean") return;
  if (kind === "number" && Number.isFinite(part)) return;
  // undefined, NaN, and Infinity all serialize to JSON null, and objects would
  // silently re-shape the tuple — any of them would break encoding injectivity.
  throw new TypeError(
    `Surface interaction instance part at index ${index} is not encodable: ` +
      `expected string, finite number, boolean, or null.`,
  );
}

/**
 * JSON tuple encoding: preserves type and tuple boundaries, so distinct typed
 * tuples can never collapse (e.g. ["a","b:c"] vs ["a:b","c"], ["1"] vs [1]).
 */
export function encodeSurfaceInteractionInstanceKey(
  parts: readonly SurfaceInteractionInstancePart[],
): string {
  // Indexed iteration: forEach skips holes, but JSON.stringify serializes them
  // as null — a sparse array would silently collide with explicit null parts.
  for (let index = 0; index < parts.length; index += 1) {
    if (!Object.hasOwn(parts, index)) {
      throw new TypeError(
        `Surface interaction instance part at index ${index} is missing (sparse array); ` +
          `holes serialize as null and would break encoding injectivity.`,
      );
    }
    assertEncodablePart(parts[index] as SurfaceInteractionInstancePart, index);
  }
  return JSON.stringify(parts);
}

/**
 * Generic identity constructor. Deliberately free of Plan-, Build-, Ingest-,
 * campaign-, document-, or session-specific field names; domain helpers remain
 * outside this package until an authorized compatibility slice.
 */
export function buildSurfaceInteractionIdentity(options: {
  surfaceId: string;
  instanceParts: readonly SurfaceInteractionInstancePart[];
}): SurfaceInteractionIdentity {
  return {
    surfaceId: options.surfaceId,
    instanceKey: encodeSurfaceInteractionInstanceKey(options.instanceParts),
  };
}

export function sameSurfaceInteractionIdentity(
  left: SurfaceInteractionIdentity | null | undefined,
  right: SurfaceInteractionIdentity | null | undefined,
): boolean {
  if (!left || !right) return false;
  return left.surfaceId === right.surfaceId && left.instanceKey === right.instanceKey;
}
