import { useMemo } from "react";

import type { WorkspaceDocumentRecord } from "../../api/types";
import { planDocumentOptionLabel } from "../config/planSessionDescriptor";
import type { PlanDocumentDescriptor } from "../types";

export type PlanDocumentListStatus = "loading" | "ready" | "error";

interface PlanDocumentSelectorProps {
  /** Active Plan documents for the active campaign; null until the first list load settles. */
  documents: WorkspaceDocumentRecord[] | null;
  listStatus: PlanDocumentListStatus;
  /** The currently authoritative document — the control always displays this, never a pending request. */
  activeDocument: PlanDocumentDescriptor;
  switching: boolean;
  switchError: string | null;
  onSelect: (documentId: string) => void;
  onRetryList: () => void;
}

/**
 * Quiet Plan-owned control for choosing the active prep document by exact
 * workspace `documentId`. Selection is navigation; document management
 * (create/rename/archive) is deliberately out of scope.
 */
export function PlanDocumentSelector({
  documents,
  listStatus,
  activeDocument,
  switching,
  switchError,
  onSelect,
  onRetryList,
}: PlanDocumentSelectorProps) {
  const options = useMemo(() => {
    if (listStatus !== "ready" || documents == null) {
      // List unavailable/loading: keep the active document visible and truthful.
      return [{ id: activeDocument.documentId, label: activeDocument.title }];
    }
    const listed = documents.map((record) => ({
      id: record.document_id,
      label: planDocumentOptionLabel(record),
    }));
    if (!documents.some((record) => record.document_id === activeDocument.documentId)) {
      // The active document is not in the refreshed active list: say so rather
      // than letting the control imply a different document is active.
      listed.unshift({
        id: activeDocument.documentId,
        label: `${activeDocument.title} (no longer listed as active)`,
      });
    }
    return listed;
  }, [documents, listStatus, activeDocument.documentId, activeDocument.title]);

  return (
    <div
      className="plan-document-selector"
      data-testid="plan-document-selector"
      aria-busy={switching}
    >
      <label className="plan-document-selector__label" htmlFor="plan-document-select">
        Prep document
      </label>
      <select
        id="plan-document-select"
        data-testid="plan-document-select"
        value={activeDocument.documentId}
        onChange={(event) => onSelect(event.target.value)}
        disabled={listStatus !== "ready"}
      >
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
      {switching ? (
        <span className="plan-document-selector__status" data-testid="plan-document-switching">
          Switching…
        </span>
      ) : null}
      {listStatus === "loading" ? (
        <span className="plan-document-selector__status">Loading documents…</span>
      ) : null}
      {listStatus === "error" ? (
        <>
          <span className="plan-document-selector__status" role="alert">
            Document list unavailable.
          </span>
          <button type="button" className="plan-document-selector__retry" onClick={onRetryList}>
            Retry
          </button>
        </>
      ) : null}
      {switchError ? (
        <p className="plan-document-selector__error" role="alert" data-testid="plan-document-switch-error">
          {switchError}
        </p>
      ) : null}
    </div>
  );
}
