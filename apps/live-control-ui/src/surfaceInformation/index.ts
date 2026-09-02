/**
 * Public surface of the Surface Information v1 contract (SI-2).
 *
 * Exports only the neutral descriptor/state/channel types and factory.
 * No Plan, Build, Play, chrome, React, or provider symbols.
 */

export type {
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

export { createSurfaceInformationChannel } from "./channel";
