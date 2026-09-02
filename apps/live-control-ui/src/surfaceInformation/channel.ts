/**
 * Runtime Surface Information channel (SI-2).
 *
 * Neutral external-store primitive: descriptor identity, ticket ordering,
 * monotonic generations, referential snapshot semantics, subscriber notify,
 * dispose. Owns no domain data and performs no durable mutation.
 */

import type {
  SurfaceInformationAuthority,
  SurfaceInformationChannel,
  SurfaceInformationDescriptor,
  SurfaceInformationDiagnostic,
  SurfaceInformationObservationTicket,
  SurfaceInformationObservedMetadata,
  SurfaceInformationReference,
  SurfaceInformationRevision,
  SurfaceInformationSnapshot,
  SurfaceInformationState,
} from "./types";

const AUTHORITIES: ReadonlySet<SurfaceInformationAuthority> = new Set([
  "dungeonmind",
  "buddy_app_state",
  "source_storage",
  "ingest",
  "mechanics",
  "combat",
  "agent",
]);

class ObservationTicket {
  constructor(
    readonly channelToken: symbol,
    readonly seq: number,
  ) {
    Object.freeze(this);
  }
}

function isBlank(value: string): boolean {
  return value.trim().length === 0;
}

function freezeReference(reference: SurfaceInformationReference): SurfaceInformationReference {
  return Object.freeze({ kind: reference.kind, id: reference.id });
}

function freezeDiagnostic(
  diagnostic: SurfaceInformationDiagnostic,
): SurfaceInformationDiagnostic {
  return Object.freeze({ code: diagnostic.code, message: diagnostic.message });
}

function freezeRevision(revision: SurfaceInformationRevision): SurfaceInformationRevision {
  if (revision.kind === "exact") {
    return Object.freeze({ kind: "exact", value: revision.value });
  }
  return Object.freeze({ kind: "unrevisioned" });
}

function freezeObservedMetadata(
  metadata: SurfaceInformationObservedMetadata,
): SurfaceInformationObservedMetadata {
  return Object.freeze({
    revision: freezeRevision(metadata.revision),
    provenance: Object.freeze(metadata.provenance.map(freezeReference)),
    inspectionTargets: Object.freeze(metadata.inspectionTargets.map(freezeReference)),
    diagnostics: Object.freeze(metadata.diagnostics.map(freezeDiagnostic)),
  });
}

function freezeState<T>(state: SurfaceInformationState<T>): SurfaceInformationState<T> {
  if (state.status === "loading") {
    return Object.freeze({
      status: "loading",
      diagnostics: Object.freeze(state.diagnostics.map(freezeDiagnostic)),
    });
  }
  if (state.status === "unavailable" || state.status === "integrity_error") {
    return Object.freeze({
      status: state.status,
      reason: state.reason,
      diagnostics: Object.freeze(state.diagnostics.map(freezeDiagnostic)),
    });
  }
  const observed = freezeObservedMetadata(state);
  if (state.status === "empty") {
    return Object.freeze({
      status: "empty",
      ...observed,
    });
  }
  if (state.status === "stale") {
    return Object.freeze({
      status: "stale",
      value: state.value,
      reason: state.reason,
      ...observed,
    });
  }
  return Object.freeze({
    status: "ready",
    value: state.value,
    ...observed,
  });
}

function freezeDescriptor(
  descriptor: SurfaceInformationDescriptor,
): SurfaceInformationDescriptor {
  return Object.freeze({
    channelId: descriptor.channelId,
    informationKind: descriptor.informationKind,
    providerId: descriptor.providerId,
    authority: descriptor.authority,
    subject: freezeReference(descriptor.subject),
    scope: Object.freeze(descriptor.scope.map(freezeReference)),
  });
}

function assertDescriptor(descriptor: SurfaceInformationDescriptor): void {
  const required: Array<[string, string]> = [
    ["channelId", descriptor.channelId],
    ["informationKind", descriptor.informationKind],
    ["providerId", descriptor.providerId],
  ];
  for (const [name, value] of required) {
    if (typeof value !== "string" || isBlank(value)) {
      throw new Error(`Surface Information descriptor ${name} must be a non-blank string.`);
    }
  }
  if (!AUTHORITIES.has(descriptor.authority)) {
    throw new Error(
      "Surface Information descriptor authority must be one explicit v1 authority.",
    );
  }
  if (
    typeof descriptor.subject?.kind !== "string" ||
    isBlank(descriptor.subject.kind) ||
    typeof descriptor.subject?.id !== "string" ||
    isBlank(descriptor.subject.id)
  ) {
    throw new Error("Surface Information descriptor subject must have non-blank kind and id.");
  }
  if (!Array.isArray(descriptor.scope)) {
    throw new Error("Surface Information descriptor scope must be an array of references.");
  }
  for (const [index, reference] of descriptor.scope.entries()) {
    if (
      typeof reference?.kind !== "string" ||
      isBlank(reference.kind) ||
      typeof reference?.id !== "string" ||
      isBlank(reference.id)
    ) {
      throw new Error(
        `Surface Information descriptor scope[${index}] must have non-blank kind and id.`,
      );
    }
  }
}

function isObservationTicket(value: unknown): value is ObservationTicket {
  return value instanceof ObservationTicket;
}

export function createSurfaceInformationChannel<T>(
  descriptor: SurfaceInformationDescriptor,
): SurfaceInformationChannel<T> {
  assertDescriptor(descriptor);
  const frozenDescriptor = freezeDescriptor(descriptor);
  const channelToken = Symbol(frozenDescriptor.channelId);

  let generation = 0;
  let snapshot: SurfaceInformationSnapshot<T> = Object.freeze({
    generation: 0,
    state: freezeState<T>({ status: "loading", diagnostics: [] }),
  });
  let currentTicket: ObservationTicket | null = null;
  let nextSeq = 1;
  let disposed = false;
  const listeners = new Set<() => void>();

  const notify = (): void => {
    for (const listener of [...listeners]) {
      listener();
    }
  };

  const acceptVisible = (state: SurfaceInformationState<T>): void => {
    generation += 1;
    snapshot = Object.freeze({
      generation,
      state: freezeState(state),
    });
    notify();
  };

  const getSnapshot = (): SurfaceInformationSnapshot<T> => snapshot;

  const subscribe = (listener: () => void): (() => void) => {
    if (disposed) {
      return () => {};
    }
    listeners.add(listener);
    let active = true;
    return () => {
      if (!active) return;
      active = false;
      listeners.delete(listener);
    };
  };

  const beginObservation = (options?: {
    publishLoading?: boolean;
  }): SurfaceInformationObservationTicket | null => {
    if (disposed) return null;
    const ticket = new ObservationTicket(channelToken, nextSeq);
    nextSeq += 1;
    currentTicket = ticket;
    if (options?.publishLoading !== false) {
      acceptVisible({ status: "loading", diagnostics: [] });
    }
    return ticket as unknown as SurfaceInformationObservationTicket;
  };

  const commit = (
    ticket: SurfaceInformationObservationTicket,
    state: Exclude<SurfaceInformationState<T>, { status: "loading" }>,
  ): boolean => {
    if (disposed) return false;
    if (!isObservationTicket(ticket)) return false;
    if (currentTicket === null) return false;
    if (ticket.channelToken !== channelToken || ticket.seq !== currentTicket.seq) {
      return false;
    }
    if ((state as SurfaceInformationState<T>).status === "loading") return false;
    currentTicket = null;
    acceptVisible(state);
    return true;
  };

  const dispose = (): void => {
    disposed = true;
    currentTicket = null;
    listeners.clear();
  };

  return Object.freeze({
    descriptor: frozenDescriptor,
    getSnapshot,
    subscribe,
    beginObservation,
    commit,
    dispose,
  });
}
