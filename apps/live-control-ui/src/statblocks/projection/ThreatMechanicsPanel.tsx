import { StatblockRenderer } from "../render/StatblockRenderer";
import type { ThreatSheetBindingViewModel, ThreatSheetLoadStatus } from "./threatSheetViewModel";
import "./threatSheetProjection.css";

export interface ThreatMechanicsPanelProps {
  loadStatus: ThreatSheetLoadStatus;
  bindings: readonly ThreatSheetBindingViewModel[];
  message?: string | null;
}

function BindingStatusPanel({ binding }: { binding: ThreatSheetBindingViewModel }) {
  return (
    <section
      className="threat-sheet-projection__binding-panel"
      aria-label={`Binding status ${binding.bindingId ?? binding.relationshipEdgeId}`}
      data-testid="threat-sheet-binding-status"
      data-hydration-status={binding.hydrationStatus}
    >
      <h4>
        {binding.role ?? "Binding"}
        {binding.phaseKey ? ` · ${binding.phaseKey}` : ""}
        {binding.variantLabel ? ` · ${binding.variantLabel}` : ""}
      </h4>
      <p className="threat-sheet-projection__binding-locator">
        Status: <strong>{binding.hydrationStatus}</strong>
        {binding.statblockId ? (
          <>
            {" "}
            · statblock <code>{binding.statblockId}</code>
          </>
        ) : null}
        {binding.revisionId ? (
          <>
            {" "}
            · revision <code>{binding.revisionId}</code>
          </>
        ) : null}
        {binding.definitionDigest ? (
          <>
            {" "}
            · digest <code>{binding.definitionDigest}</code>
          </>
        ) : null}
      </p>
      {binding.message ? <p className="module-muted">{binding.message}</p> : null}
    </section>
  );
}

function bindingHeading(binding: ThreatSheetBindingViewModel): string {
  const parts = [
    binding.role ?? "Binding",
    binding.phaseKey,
    binding.variantLabel,
    binding.hydrationStatus,
  ].filter((part): part is string => Boolean(part));
  return parts.join(" · ");
}

/**
 * Surface-neutral immutable mechanics rendering.
 * Does not own Plan actions, Play occurrence copy, or Combat.
 */
export function ThreatMechanicsPanel({
  loadStatus,
  bindings,
  message = null,
}: ThreatMechanicsPanelProps) {
  return (
    <div className="threat-mechanics-panel" data-testid="threat-mechanics-panel">
      {loadStatus === "loading" ? (
        <p className="threat-sheet-projection__status threat-sheet-projection__status--loading" role="status">
          Loading exact mechanics…
        </p>
      ) : null}

      {loadStatus !== "loading" && loadStatus !== "ready" ? (
        <p
          className="threat-sheet-projection__status threat-sheet-projection__status--error"
          role="status"
          data-testid="threat-sheet-load-status"
          data-load-status={loadStatus}
        >
          {message ?? `Exact mechanics ${loadStatus.replace(/_/g, " ")}.`}
        </p>
      ) : null}

      <div className="threat-sheet-projection__bindings">
        {bindings.map((binding) =>
          binding.hydrationStatus === "available" && binding.revision ? (
            <section
              key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}
              className="threat-sheet-projection__full-statblock"
            >
              {bindings.length > 1 ? <h4>{bindingHeading(binding)}</h4> : null}
              <StatblockRenderer revision={binding.revision} mode="full" chrome="campaign" />
            </section>
          ) : (
            <BindingStatusPanel
              key={`${binding.relationshipEdgeId}:${binding.bindingId ?? "none"}`}
              binding={binding}
            />
          ),
        )}
      </div>
    </div>
  );
}
