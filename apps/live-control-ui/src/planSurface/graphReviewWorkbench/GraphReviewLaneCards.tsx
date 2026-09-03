import type { ReactNode } from "react";

import type { GraphReviewLane } from "../../api/types";
import { unknownIfBlank } from "./graphReviewWorkbenchUtils";
import type { GraphReviewCatalogRun } from "./graphReviewWorkbenchUtils";

interface GraphReviewLaneCardsProps {
  goldLane: GraphReviewLane | null;
  liveLane: GraphReviewLane | null;
  liveRun: GraphReviewCatalogRun | null;
}

function formatRecord(value: Record<string, unknown> | undefined): string {
  if (!value || Object.keys(value).length === 0) return "Unknown";
  return JSON.stringify(value);
}

function Field({ label, value }: { label: string; value: string | number | undefined | null }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value == null || value === "" ? "Unknown" : value}</dd>
    </div>
  );
}

function LaneDetails({
  summary,
  children,
}: {
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="graph-review-lane-details">
      <summary>{summary}</summary>
      <dl className="graph-review-lane-meta">{children}</dl>
    </details>
  );
}

export function GraphReviewLaneCards({ goldLane, liveLane, liveRun }: GraphReviewLaneCardsProps) {
  const revision = liveRun
    ? (liveRun.run as { revision?: number }).revision
    : null;
  return (
    <section className="graph-review-lane-grid" aria-label="Graph review lanes">
      <article className="graph-review-lane-card">
        <header className="graph-review-lane-card-header">
          <div>
            <p className="plan-surface-kicker">Expected / Gold</p>
            <h3>{goldLane?.label ?? "Gold lane"}</h3>
          </div>
          <span>{goldLane?.status ?? "unknown"}</span>
        </header>
        {goldLane ? (
          <>
            <LaneDetails summary="Advanced lane details">
              <Field label="Nodes" value={goldLane.counts.nodes} />
              <Field label="Edges" value={goldLane.counts.edges} />
              <Field label="Evidence refs" value={goldLane.counts.evidenceRefs} />
              <Field label="Role" value={goldLane.role} />
              <Field label="Source kind" value={goldLane.sourceKind} />
              <Field label="Campaign" value={goldLane.campaignId} />
              <Field label="Session" value={goldLane.sessionId} />
              <Field label="Gold fixture id" value={String(goldLane.metadata.diagnostics?.goldFixtureId ?? "Unknown")} />
              <Field label="Gold manifest path" value={goldLane.manifestPath} />
              <Field label="Gold graph path" value={goldLane.goldPath} />
              <Field label="Beats" value={goldLane.counts.beats} />
            </LaneDetails>
          </>
        ) : (
          <p className="graph-review-note">Select a gold-backed session to inspect the expected lane.</p>
        )}
      </article>

      <article className="graph-review-lane-card">
        <header className="graph-review-lane-card-header">
          <div>
            <p className="plan-surface-kicker">Live / ExtractionRun</p>
            <h3>{liveLane?.label ?? "Live lane"}</h3>
          </div>
          <span>{liveLane?.status ?? "unknown"}</span>
        </header>
        {liveLane && liveRun ? (
          <>
            <LaneDetails summary="Advanced run details">
              <Field label="Run id" value={liveRun.run.run_id} />
              <Field label="Status" value={liveRun.run.status} />
              <Field label="Revision" value={revision} />
              <Field label="Source domain" value={liveRun.run.source_domain} />
              <Field label="Source artifact" value={liveRun.run.source_artifact_id} />
              <Field label="Campaign" value={liveRun.run.campaign_id} />
              <Field label="Session" value={liveRun.run.session_id} />
              <Field label="Profile" value={unknownIfBlank(liveRun.run.profile_id)} />
              <Field
                label="Compatibility locator"
                value={liveRun.compatibilityManifestPath ?? "Unavailable"}
              />
              <Field label="Updated at" value={liveRun.run.updated_at} />
              <Field label="Created at" value={liveRun.run.created_at} />
              <Field
                label="Diagnostics"
                value={formatRecord(liveRun.run.diagnostics as Record<string, unknown> | undefined)}
              />
            </LaneDetails>
          </>
        ) : (
          <p className="graph-review-note">No canonical ExtractionRun selected for this session yet.</p>
        )}
      </article>
    </section>
  );
}
