import type { PlanGraphContextRequest } from "../reference/planGraphContextRequest";

export interface PlanGraphContextDiagnosticsProps {
  graphContext: PlanGraphContextRequest;
  /** Compact layout for Insert-refs toolbox; default is dogfood panel. */
  compact?: boolean;
}

export function PlanGraphContextDiagnostics({
  graphContext,
  compact = false,
}: PlanGraphContextDiagnosticsProps) {
  return (
    <dl
      className={
        compact
          ? "plan-graph-context-diagnostics plan-graph-context-diagnostics--compact"
          : "plan-graph-context-diagnostics"
      }
      data-testid="plan-graph-context-diagnostics"
      aria-label="Requested Plan graph context"
    >
      <div>
        <dt>campaignId</dt>
        <dd>{graphContext.campaignId}</dd>
      </div>
      <div>
        <dt>prepSession</dt>
        <dd>{graphContext.prepSession}</dd>
      </div>
      <div>
        <dt>memorySession</dt>
        <dd>{graphContext.memorySession}</dd>
      </div>
      <div>
        <dt>liveSession</dt>
        <dd>{graphContext.liveSession}</dd>
      </div>
      <div>
        <dt>projection mode</dt>
        <dd>{graphContext.projectionMode}</dd>
      </div>
      <div>
        <dt>requested sessionId</dt>
        <dd>{graphContext.requestedSessionId}</dd>
      </div>
    </dl>
  );
}
