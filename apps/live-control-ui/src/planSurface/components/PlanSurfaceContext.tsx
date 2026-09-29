import { useMemo } from "react";

import type { WorkspaceDocumentRecord, WorldOwnedPlanRecordV2 } from "../../api/types";
import { buildPlanSurfaceIdentity } from "../../agentInteraction/projectionSurfacePublication";
import { buildSurfaceInteractionIdentity } from "../../surfaceInteraction/surfaceIdentity";
import {
  SurfaceContextBadge,
  SurfaceContextAction,
  SurfaceContextModule,
  SurfaceContextSelect,
  SurfaceContextStatus,
  SurfaceContextValue,
  useSurfaceContextContribution,
} from "../../surfaceInteraction/contextHost";
import type { PlanDocumentDescriptor } from "../types";
import {
  PlanDocumentCreateControl,
  type PlanDocumentCreateControlProps,
} from "./PlanDocumentCreateControl";
import { PlanDocumentSelector, type PlanDocumentListStatus } from "./PlanDocumentSelector";

export interface PlanSurfaceContextProps {
  campaignId: string;
  liveSession: number;
  memorySession: number | null;
  documents: WorkspaceDocumentRecord[] | null;
  listStatus: PlanDocumentListStatus;
  activeDocument: PlanDocumentDescriptor | null;
  switching: boolean;
  switchError: string | null;
  /** Canvas authoring save/dirty label — board metadata, not canvas chrome. */
  saveStatusLabel?: string | null;
  onSelect: (documentId: string) => void;
  onRetryList: () => void;
  createControlProps: Omit<
    PlanDocumentCreateControlProps,
    "presentation" | "disabled"
  > & { disabled?: boolean };
}

/** World-owned Plan context uses its real World/document key, never campaign/session aliases. */
export interface WorldPlanSurfaceContextProps {
  worldId: string;
  worldName: string;
  documentId: string | null;
  records: WorldOwnedPlanRecordV2[];
  disabled?: boolean;
  onSelect: (documentId: string) => void;
  onNewPlan: () => void;
}

export function WorldPlanSurfaceContext({
  worldId,
  worldName,
  documentId,
  records,
  disabled = false,
  onSelect,
  onNewPlan,
}: WorldPlanSurfaceContextProps) {
  const surfaceIdentity = useMemo(() => buildSurfaceInteractionIdentity({
    surfaceId: "plan",
    instanceParts: ["world-plan", worldId, documentId],
  }), [documentId, worldId]);

  const content = useMemo(() => (
    <SurfaceContextModule label="PLAN" className="plan-surface-context">
      <div className="plan-surface-context__row" data-testid="world-plan-surface-context">
        <SurfaceContextBadge>{worldName}</SurfaceContextBadge>
        <SurfaceContextSelect
          id="world-plan-document-select"
          data-testid="world-plan-document-select"
          aria-label="Plan document"
          value={documentId ?? ""}
          disabled={disabled}
          onChange={(event) => event.target.value ? onSelect(event.target.value) : onNewPlan()}
        >
          <option value="">New blank Plan</option>
          {records.map((record) => (
            <option key={record.document_id} value={record.document_id}>
              {record.title || "Untitled Plan"}
            </option>
          ))}
        </SurfaceContextSelect>
        {documentId ? (
          <SurfaceContextAction type="button" onClick={onNewPlan} disabled={disabled}>
            New blank Plan
          </SurfaceContextAction>
        ) : null}
      </div>
    </SurfaceContextModule>
  ), [disabled, documentId, onNewPlan, onSelect, records, worldName]);

  useSurfaceContextContribution({
    id: "plan-world-context",
    order: 10,
    surfaceIdentity,
    content,
  });

  return null;
}

export function PlanSurfaceContext({
  campaignId,
  liveSession,
  memorySession,
  documents,
  listStatus,
  activeDocument,
  switching,
  switchError,
  saveStatusLabel = null,
  onSelect,
  onRetryList,
  createControlProps,
}: PlanSurfaceContextProps) {
  const surfaceIdentity = useMemo(() => {
    if (activeDocument) {
      return buildPlanSurfaceIdentity({
        documentId: activeDocument.documentId,
        campaignId,
        liveSession,
        memorySession,
      });
    }
    return buildSurfaceInteractionIdentity({
      surfaceId: "plan",
      instanceParts: ["plan", "empty", campaignId, liveSession],
    });
  }, [activeDocument, campaignId, liveSession, memorySession]);

  const content = useMemo(
    () => (
      <SurfaceContextModule label="PREP" className="plan-surface-context">
        <div className="plan-surface-context__row">
          {activeDocument ? (
            <>
              {/* Active title for identity assertions; selector remains the visible control. */}
              <span data-testid="plan-canvas-title" hidden>
                {activeDocument.title}
              </span>
              <PlanDocumentSelector
                variant="context"
                documents={documents}
                listStatus={listStatus}
                activeDocument={activeDocument}
                switching={switching}
                switchError={null}
                onSelect={onSelect}
                onRetryList={onRetryList}
              />
              {activeDocument.targetSession != null ? (
                <SurfaceContextBadge>S{activeDocument.targetSession}</SurfaceContextBadge>
              ) : null}
              {saveStatusLabel ? (
                <SurfaceContextStatus
                  data-testid="plan-canvas-save-status"
                  className="plan-surface-context__save-status"
                  tone={/unsaved|error|fail/i.test(saveStatusLabel) ? "warning" : "neutral"}
                >
                  {saveStatusLabel}
                </SurfaceContextStatus>
              ) : null}
            </>
          ) : (
            <SurfaceContextValue>No prep loaded</SurfaceContextValue>
          )}
          <PlanDocumentCreateControl
            {...createControlProps}
            presentation="context"
            disabled={createControlProps.disabled ?? switching}
          />
        </div>
        {listStatus === "error" ? (
          <SurfaceContextStatus tone="error">
            Document list unavailable.{" "}
            <button type="button" className="plan-surface-context__retry" onClick={onRetryList}>
              Retry
            </button>
          </SurfaceContextStatus>
        ) : null}
        {switching ? <SurfaceContextStatus>Switching…</SurfaceContextStatus> : null}
        {switchError ? (
          <SurfaceContextStatus tone="error">
            {switchError} Try selecting another prep document.
          </SurfaceContextStatus>
        ) : null}
      </SurfaceContextModule>
    ),
    [
      activeDocument,
      createControlProps,
      documents,
      listStatus,
      onRetryList,
      onSelect,
      saveStatusLabel,
      switchError,
      switching,
    ],
  );

  useSurfaceContextContribution({
    id: "plan-prep",
    order: 10,
    surfaceIdentity,
    content,
  });

  return null;
}
