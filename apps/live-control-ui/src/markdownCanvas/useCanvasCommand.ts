import { useCallback, useEffect, useRef, useState } from "react";

import type {
  ActiveDocumentCommand,
  AdmissionLookupResult,
  AdmittedDocumentEnvelope,
  DocumentAdmissionPolicy,
  DocumentCommandExecuteContext,
  DocumentCommandResult,
  DocumentCommandSpec,
} from "./markdownCanvasTypes";

export type AdmissionLookup = (policy: DocumentAdmissionPolicy) => AdmissionLookupResult;

export interface CanvasCommandHostArgs {
  documentId: string;
  lookupAdmission: AdmissionLookup;
}

export interface CanvasCommandHost {
  activeCommand: ActiveDocumentCommand | null;
  runDocumentCommand: <T>(
    spec: DocumentCommandSpec,
    execute: (ctx: DocumentCommandExecuteContext) => Promise<T>,
  ) => Promise<DocumentCommandResult<T>>;
}

/**
 * Document-bound command arbitration. Owns duplicate/conflict/admission/invalidation;
 * does not interpret plugin return values (runs, handoffs, etc.).
 */
export function useCanvasCommand(args: CanvasCommandHostArgs): CanvasCommandHost {
  const { documentId, lookupAdmission } = args;
  const [activeCommand, setActiveCommand] = useState<ActiveDocumentCommand | null>(null);
  const activeRef = useRef<{
    id: string;
    documentId: string;
    invalidateOnDocumentChange: boolean;
    controller: AbortController;
  } | null>(null);
  const mountedRef = useRef(true);
  const documentIdRef = useRef(documentId);
  documentIdRef.current = documentId;

  const invalidateActive = useCallback((reason: "document_change" | "unmount") => {
    const current = activeRef.current;
    if (!current) return;
    if (reason === "document_change" && !current.invalidateOnDocumentChange) return;
    current.controller.abort(reason);
    activeRef.current = null;
    if (mountedRef.current) setActiveCommand(null);
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      invalidateActive("unmount");
    };
  }, [invalidateActive]);

  useEffect(() => {
    invalidateActive("document_change");
  }, [documentId, invalidateActive]);

  const runDocumentCommand = useCallback(
    async <T,>(
      spec: DocumentCommandSpec,
      execute: (ctx: DocumentCommandExecuteContext) => Promise<T>,
    ): Promise<DocumentCommandResult<T>> => {
      const selectedDocumentId = documentIdRef.current;
      const current = activeRef.current;
      if (current) {
        if (current.id === spec.id) {
          return { ok: false, reason: `Command ${spec.id} is already running.`, code: "duplicate_command" };
        }
        if (spec.conflictsWith.includes(current.id)) {
          return {
            ok: false,
            reason: `Command ${spec.id} conflicts with active ${current.id}.`,
            code: "conflict",
          };
        }
        return {
          ok: false,
          reason: `Command ${spec.id} cannot start while ${current.id} is active.`,
          code: "conflict",
        };
      }

      let envelope: AdmittedDocumentEnvelope | null = null;
      if (spec.admission !== "none") {
        const admission = lookupAdmission(spec.admission);
        if (!admission.ok) {
          return {
            ok: false,
            reason: admission.code,
            code: "admission_failed",
            admissionCode: admission.code,
            admissionDetail: admission.detail,
          };
        }
        envelope = admission.envelope;
        if (envelope.documentId !== selectedDocumentId) {
          return {
            ok: false,
            reason: "document_identity_mismatch",
            code: "admission_failed",
            admissionCode: "document_identity_mismatch",
          };
        }
      }

      const controller = new AbortController();
      const startedAt = Date.now();
      activeRef.current = {
        id: spec.id,
        documentId: selectedDocumentId,
        invalidateOnDocumentChange: spec.invalidateOnDocumentChange !== false,
        controller,
      };
      setActiveCommand({ id: spec.id, documentId: selectedDocumentId, startedAt });

      try {
        const value = await execute({
          envelope,
          signal: controller.signal,
          documentId: selectedDocumentId,
        });
        if (controller.signal.aborted) {
          return { ok: false, reason: "Command was invalidated.", code: "invalidated" };
        }
        if (documentIdRef.current !== selectedDocumentId) {
          return { ok: false, reason: "Document selection changed.", code: "invalidated" };
        }
        if (!mountedRef.current) {
          return { ok: false, reason: "Canvas unmounted.", code: "invalidated" };
        }
        return { ok: true, value };
      } catch (error) {
        if (controller.signal.aborted) {
          return { ok: false, reason: "Command was aborted.", code: "aborted" };
        }
        return {
          ok: false,
          reason: error instanceof Error ? error.message : "Document command failed.",
          code: "execute_failed",
        };
      } finally {
        if (activeRef.current?.controller === controller) {
          activeRef.current = null;
          if (mountedRef.current) setActiveCommand(null);
        }
      }
    },
    [lookupAdmission],
  );

  return { activeCommand, runDocumentCommand };
}
