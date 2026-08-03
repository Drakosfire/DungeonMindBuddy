import type { ReactNode } from "react";

import type { ActiveProjection, ProjectionKind, ProjectionSize } from "./types";
import type { SurfaceInteractionPublication } from "../types";

/** Stable content catalog ID — reachability only; not the dynamic active content key. */
export const GRAPH_REFERENCE_PROJECTION_ID = "graph-reference" as const;

export interface ProjectionCatalogRenderRequest {
  projectionId: string;
  active: ActiveProjection;
  bindings: Readonly<Record<string, unknown>>;
}

export interface ProjectionCatalogRegistration {
  projectionId: string;
  surfaceId: string;
  kind: ProjectionKind;
  preferredSize: ProjectionSize;
  requiredBindingIds: readonly string[];
  render: (request: ProjectionCatalogRenderRequest) => ReactNode;
}

export type ProjectionCatalogResolutionStatus =
  | "ready"
  | "unregistered"
  | "duplicate_registration"
  | "descriptor_missing"
  | "surface_mismatch"
  | "kind_mismatch"
  | "active_key_mismatch"
  | "preferred_size_mismatch"
  | "binding_missing"
  | "stale_lease"
  | "invalid_registration";

export type ProjectionCatalogResolution =
  | { status: "ready"; body: ReactNode }
  | {
      status: Exclude<ProjectionCatalogResolutionStatus, "ready">;
      body: null;
      missingBindingIds?: readonly string[];
    };

export interface ProjectionCatalogLiveEntry {
  registrationToken: symbol;
  leaseToken: symbol;
  registration: ProjectionCatalogRegistration;
}

function isNonBlankString(value: unknown): value is string {
  return typeof value === "string" && value.length > 0;
}

function hasDuplicateStrings(values: readonly string[]): boolean {
  return new Set(values).size !== values.length;
}

/**
 * Snapshot a registration so caller mutation of requiredBindingIds cannot alter live requirements.
 * Rejects blank IDs, blank surface, unsupported kind/size, and duplicate binding IDs.
 */
export function normalizeProjectionCatalogRegistration(
  input: ProjectionCatalogRegistration,
): ProjectionCatalogRegistration | null {
  if (!isNonBlankString(input.projectionId) || !isNonBlankString(input.surfaceId)) {
    return null;
  }
  if (input.kind !== "tool" && input.kind !== "content") {
    return null;
  }
  if (
    input.preferredSize !== "compact"
    && input.preferredSize !== "wide"
    && input.preferredSize !== "fullscreen"
  ) {
    return null;
  }
  if (!Array.isArray(input.requiredBindingIds) || hasDuplicateStrings(input.requiredBindingIds)) {
    return null;
  }
  if (typeof input.render !== "function") {
    return null;
  }
  return {
    projectionId: input.projectionId,
    surfaceId: input.surfaceId,
    kind: input.kind,
    preferredSize: input.preferredSize,
    requiredBindingIds: Object.freeze([...input.requiredBindingIds]),
    render: input.render,
  };
}

/**
 * Build a read-only binding snapshot without evaluating unrelated accessors.
 * Own data properties are copied by descriptor. Each required ID is read at most
 * once; that same value is used for both authorization and the render snapshot.
 * Extra enumerable getters are never invoked.
 */
function snapshotOpaqueBindingsForAuthorization(
  bindings: Readonly<Record<string, unknown>>,
  requiredBindingIds: readonly string[],
): {
  missingBindingIds: readonly string[];
  bindingSnapshot: Readonly<Record<string, unknown>>;
} {
  const out: Record<string, unknown> = Object.create(null);
  for (const key of Object.keys(bindings)) {
    const descriptor = Object.getOwnPropertyDescriptor(bindings, key);
    if (!descriptor || !Object.prototype.hasOwnProperty.call(descriptor, "value")) {
      continue;
    }
    out[key] = descriptor.value;
  }

  const missingBindingIds: string[] = [];
  for (const id of requiredBindingIds) {
    let value: unknown;
    if (Object.prototype.hasOwnProperty.call(out, id)) {
      value = out[id];
    } else if (Object.prototype.hasOwnProperty.call(bindings, id)) {
      // Single accessor evaluation — reused for auth and render.
      value = bindings[id];
      out[id] = value;
    } else {
      missingBindingIds.push(id);
      continue;
    }
    if (value === null || value === undefined) {
      missingBindingIds.push(id);
    }
  }

  return {
    missingBindingIds,
    bindingSnapshot: Object.freeze(out),
  };
}

/**
 * Pure fail-closed catalog resolution. Invokes a renderer only when every exact
 * lease, publication, identity, kind/size, and binding check passes.
 */
export function resolveProjectionCatalog(args: {
  leaseToken: symbol | null;
  entries: readonly ProjectionCatalogLiveEntry[];
  publication: SurfaceInteractionPublication | null;
  projectionId: string;
  active: ActiveProjection | null;
  bindings: Readonly<Record<string, unknown>>;
}): ProjectionCatalogResolution {
  const { leaseToken, entries, publication, projectionId, active, bindings } = args;

  if (leaseToken === null) {
    return { status: "stale_lease", body: null };
  }
  if (!publication || !active) {
    return { status: "descriptor_missing", body: null };
  }
  if (!isNonBlankString(projectionId)) {
    return { status: "unregistered", body: null };
  }

  const matching = entries.filter(
    (entry) => entry.leaseToken === leaseToken && entry.registration.projectionId === projectionId,
  );
  if (matching.length === 0) {
    return { status: "unregistered", body: null };
  }
  if (matching.length > 1) {
    return { status: "duplicate_registration", body: null };
  }

  const entry = matching[0]!;
  if (entry.leaseToken !== leaseToken) {
    return { status: "stale_lease", body: null };
  }

  const registration = entry.registration;
  const descriptors = publication.projections.filter((descriptor) => descriptor.id === projectionId);
  if (descriptors.length === 0) {
    return { status: "descriptor_missing", body: null };
  }
  // Publication must declare exactly one descriptor for this ID.
  if (descriptors.length > 1) {
    return { status: "duplicate_registration", body: null };
  }
  const descriptor = descriptors[0]!;

  if (descriptor.kind !== registration.kind || active.kind !== registration.kind) {
    return { status: "kind_mismatch", body: null };
  }
  // Tools require exact active-key identity. Content keeps a fixed catalog ID
  // while active.key remains the dynamic content key.
  if (registration.kind === "tool" && active.key !== projectionId) {
    return { status: "active_key_mismatch", body: null };
  }
  if (descriptor.preferredSize !== registration.preferredSize) {
    return { status: "preferred_size_mismatch", body: null };
  }
  if (
    publication.identity.surfaceId !== registration.surfaceId
    || publication.surfaceId !== registration.surfaceId
  ) {
    return { status: "surface_mismatch", body: null };
  }

  const { missingBindingIds, bindingSnapshot } = snapshotOpaqueBindingsForAuthorization(
    bindings,
    registration.requiredBindingIds,
  );
  if (missingBindingIds.length > 0) {
    return { status: "binding_missing", body: null, missingBindingIds };
  }

  const body = registration.render({
    projectionId,
    active,
    bindings: bindingSnapshot,
  });
  return { status: "ready", body };
}
