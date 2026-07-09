import type { SurfaceConfig } from "../types";
import { buildPlanIngestHref } from "../config/planSessionDescriptor";

interface PlanNavBarProps {
  config: SurfaceConfig;
}

function formatDocumentStatus(
  status: NonNullable<SurfaceConfig["sessionDescriptor"]>["planningDocument"]["status"],
): string {
  switch (status) {
    case "local_draft":
      return "local draft";
    case "durable":
      return "saved";
    case "missing":
      return "missing";
    default:
      return "unknown";
  }
}

export function PlanNavBar({ config }: PlanNavBarProps) {
  const sessionDescriptor = config.sessionDescriptor;
  const planningDocument = sessionDescriptor?.planningDocument;

  return (
    <header className="plan-nav-bar">
      <div className="plan-nav-primary">
        <p className="plan-surface-kicker">{config.label}</p>
        <h1 className="plan-nav-title" data-testid="plan-context-header">
          {config.context.headerLabel}
        </h1>
        {sessionDescriptor ? (
          <div className="plan-nav-context-strip" aria-label="Plan session context">
            <p className="plan-nav-context-line" data-testid="plan-memory-source">
              Memory/source: {sessionDescriptor.sourceStatusLabel}
            </p>
            {planningDocument ? (
              <>
                <p className="plan-nav-context-line" data-testid="plan-document-context">
                  Board: {planningDocument.title} · {formatDocumentStatus(planningDocument.status)}
                </p>
                <p className="plan-nav-context-line plan-nav-context-mono" data-testid="plan-document-target">
                  Target: {planningDocument.targetRelpath ?? "TBD durable planning path"}
                </p>
                <p className="plan-nav-context-line plan-nav-draft-note" data-testid="plan-local-draft-note">
                  Local draft · browser-local until durable save lands
                </p>
              </>
            ) : null}
          </div>
        ) : (
          <p className="plan-nav-subtitle">
            Intentional planning surface. Use Live Play as the static command-board baseline.
          </p>
        )}
      </div>
      <nav className="plan-nav-links" aria-label="Plan surface navigation">
        {sessionDescriptor ? (
          <a href={buildPlanIngestHref(sessionDescriptor)}>Review memory</a>
        ) : null}
        <a href="/plan" aria-current="page">
          Plan
        </a>
        <a href="/ingest">Ingest</a>
        <a href="/evals/c2_live_prep/mireward-prep/live-play.html">Live Play</a>
        <a href="/surface">Live Control</a>
        <a href="/">Index</a>
      </nav>
    </header>
  );
}
