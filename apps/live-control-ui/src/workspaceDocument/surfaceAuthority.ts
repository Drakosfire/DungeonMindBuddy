import type { WorkspaceDocumentRecord } from "../api/types";
import type {
  WorkspaceDocumentLocalKind,
  WorkspaceDocumentLocalSurface,
} from "../tiptap/state/tiptapLocalState";

/** Declared surface → allowed registry kinds. Opening rejects anything else. */
export const SURFACE_ALLOWED_KINDS: Record<
  WorkspaceDocumentLocalSurface,
  readonly WorkspaceDocumentLocalKind[]
> = {
  build: ["worldbuilding_source"],
  plan: ["plan"],
  runbook: ["runbook"],
};

export type SurfaceAuthorityRejectReason =
  | "document_id_mismatch"
  | "kind_mismatch"
  | "surface_kind_forbidden"
  | "discarded_not_supported"
  | "revision_missing";

export interface SurfaceAuthorityArgs {
  requestedDocumentId: string;
  requestedKind: WorkspaceDocumentLocalKind;
  surface: WorkspaceDocumentLocalSurface;
  record: WorkspaceDocumentRecord;
  loadedRevision: number;
  /** Surfaces that may open discarded documents. Default: none. */
  allowDiscarded?: boolean;
}

export interface SurfaceAuthorityResult {
  ok: boolean;
  rejectReason?: string;
  rejectCode?: SurfaceAuthorityRejectReason;
  /** Authoritative kind from the registry record when ok. */
  authoritativeKind?: WorkspaceDocumentLocalKind;
}

export function assertSurfaceAuthority(args: SurfaceAuthorityArgs): SurfaceAuthorityResult {
  const recordId = args.record.document_id?.trim() ?? "";
  const requestedId = args.requestedDocumentId.trim();
  if (!recordId || recordId !== requestedId) {
    return {
      ok: false,
      rejectCode: "document_id_mismatch",
      rejectReason: `Snapshot document_id ${recordId || "(missing)"} does not match requested ${requestedId}.`,
    };
  }

  if (!Number.isFinite(args.loadedRevision) || args.loadedRevision < 1) {
    return {
      ok: false,
      rejectCode: "revision_missing",
      rejectReason: "Snapshot loaded_revision is missing or invalid.",
    };
  }

  if (args.record.revision !== args.loadedRevision) {
    return {
      ok: false,
      rejectCode: "revision_missing",
      rejectReason: `Snapshot record.revision ${args.record.revision} does not match loaded_revision ${args.loadedRevision}.`,
    };
  }

  if (args.record.status === "discarded" && !args.allowDiscarded) {
    return {
      ok: false,
      rejectCode: "discarded_not_supported",
      rejectReason: "Discarded workspace documents cannot be opened on this surface.",
    };
  }

  const authoritativeKind = args.record.kind as WorkspaceDocumentLocalKind;
  if (args.requestedKind !== authoritativeKind) {
    return {
      ok: false,
      rejectCode: "kind_mismatch",
      rejectReason: `Requested kind ${args.requestedKind} does not match registry kind ${authoritativeKind}.`,
    };
  }

  const allowed = SURFACE_ALLOWED_KINDS[args.surface] ?? [];
  if (!allowed.includes(authoritativeKind)) {
    return {
      ok: false,
      rejectCode: "surface_kind_forbidden",
      rejectReason: `Surface ${args.surface} does not accept document kind ${authoritativeKind}.`,
    };
  }

  return { ok: true, authoritativeKind };
}
