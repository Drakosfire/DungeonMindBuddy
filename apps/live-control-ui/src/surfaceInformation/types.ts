/**
 * Neutral Surface Information v1 types (SI-2).
 *
 * Authority: Docs/Design/CONTRACT-surface-information-v1.md
 * Runtime-only. One channel observes one projection from one authority.
 */

export type SurfaceInformationAuthority =
  | "dungeonmind"
  | "buddy_app_state"
  | "source_storage"
  | "ingest"
  | "mechanics"
  | "combat"
  | "agent";

export interface SurfaceInformationReference {
  kind: string;
  id: string;
}

export interface SurfaceInformationDescriptor {
  channelId: string;
  informationKind: string;
  providerId: string;
  authority: SurfaceInformationAuthority;
  subject: SurfaceInformationReference;
  scope: readonly SurfaceInformationReference[];
}

export type SurfaceInformationRevision =
  | {
      kind: "exact";
      value: string;
    }
  | {
      kind: "unrevisioned";
    };

export interface SurfaceInformationDiagnostic {
  code: string;
  message: string;
}

export interface SurfaceInformationObservedMetadata {
  revision: SurfaceInformationRevision;
  provenance: readonly SurfaceInformationReference[];
  inspectionTargets: readonly SurfaceInformationReference[];
  diagnostics: readonly SurfaceInformationDiagnostic[];
}

export type SurfaceInformationState<T> =
  | {
      status: "loading";
      diagnostics: readonly SurfaceInformationDiagnostic[];
    }
  | ({
      status: "ready";
      value: T;
    } & SurfaceInformationObservedMetadata)
  | ({
      status: "empty";
    } & SurfaceInformationObservedMetadata)
  | ({
      status: "stale";
      value: T;
      reason: string;
    } & SurfaceInformationObservedMetadata)
  | {
      status: "unavailable";
      reason: string;
      diagnostics: readonly SurfaceInformationDiagnostic[];
    }
  | {
      status: "integrity_error";
      reason: string;
      diagnostics: readonly SurfaceInformationDiagnostic[];
    };

export interface SurfaceInformationSnapshot<T> {
  generation: number;
  state: SurfaceInformationState<T>;
}

/**
 * Opaque observation ticket. Consumers cannot construct a meaningful ticket.
 * Channel-specific, single-current, invalidated by the next beginObservation,
 * successful commit, or dispose.
 */
export interface SurfaceInformationObservationTicket {
  readonly __brand: unique symbol;
}

export interface SurfaceInformationChannel<T> {
  readonly descriptor: SurfaceInformationDescriptor;

  readonly getSnapshot: () => SurfaceInformationSnapshot<T>;

  readonly subscribe: (listener: () => void) => () => void;

  readonly beginObservation: (options?: {
    publishLoading?: boolean;
  }) => SurfaceInformationObservationTicket | null;

  readonly commit: (
    ticket: SurfaceInformationObservationTicket,
    state: Exclude<SurfaceInformationState<T>, { status: "loading" }>,
  ) => boolean;

  readonly dispose: () => void;
}
