import type { ReactNode } from "react";

import { IngestionModule } from "../../modules/IngestionModule";
import { StatblockWorkbenchModule } from "../../surface/modules/StatblockWorkbenchModule";
import type { PlanContextDescriptor } from "../types";
import type { ReferenceResolution } from "../reference/referenceResolver";
import { resolutionToSourceUnit } from "../derivedViews/derivedViewsAdapter";
import { useEditCapability } from "../edit/editCapability";

export interface ToolProjectionProps {
  context: PlanContextDescriptor;
}

export interface ContentProjectionProps {
  resolution: ReferenceResolution;
}

function ContentSurfacePanel({ resolution }: ContentProjectionProps) {
  const unit = resolutionToSourceUnit(resolution);
  const { isLocked, toggleLock, canEdit } = useEditCapability();

  return (
    <section className="plan-content-surface" aria-label="Reference content">
      <header className="plan-content-surface-header">
        <div>
          <p className="plan-surface-kicker">Resolved reference</p>
          <h3>{resolution.ref.label}</h3>
        </div>
        <button type="button" onClick={toggleLock} aria-pressed={isLocked}>
          {isLocked ? "Unlock edit" : "Lock edit"}
        </button>
      </header>
      <p className="plan-content-summary">{unit.summary}</p>
      {unit.sourcePath ? (
        <p className="plan-content-path">
          <code>{unit.sourcePath}</code>
        </p>
      ) : null}
      <dl className="plan-content-fields">
        {Object.entries(unit.fields).map(([key, value]) => (
          <div key={key}>
            <dt>{key}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {!canEdit ? (
        <p className="plan-content-note">Read-only until unlocked. Edits commit through the two-phase corpus writer.</p>
      ) : (
        <p className="plan-content-note plan-content-note-editable">
          Edit unlocked. Use the canvas Edit bar or file-write flow for committed changes.
        </p>
      )}
    </section>
  );
}

export function renderToolProjection(toolId: string, context: PlanContextDescriptor): ReactNode {
  if (toolId === "ingest-recap") {
    return (
      <IngestionModule
        campaignId={context.campaignId}
        session={context.ingestSession}
      />
    );
  }
  if (toolId === "statblock") {
    return <StatblockWorkbenchModule />;
  }
  return <p className="plan-projection-empty">Unknown tool: {toolId}</p>;
}

export function renderContentProjection(resolution: ReferenceResolution): ReactNode {
  return <ContentSurfacePanel resolution={resolution} />;
}
