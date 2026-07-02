import type { GraphIngestRunSummary, GraphReviewLane } from "../../api/types";
import { unknownIfBlank, yesNo } from "./graphReviewWorkbenchUtils";

interface GraphReviewLaneCardsProps {
  goldLane: GraphReviewLane | null;
  liveLane: GraphReviewLane | null;
  liveRun: GraphIngestRunSummary | null;
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

export function GraphReviewLaneCards({ goldLane, liveLane, liveRun }: GraphReviewLaneCardsProps) {
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
          <dl className="graph-review-lane-meta">
            <Field label="Role" value={goldLane.role} />
            <Field label="Source kind" value={goldLane.sourceKind} />
            <Field label="Campaign" value={goldLane.campaignId} />
            <Field label="Session" value={goldLane.sessionId} />
            <Field label="Gold fixture id" value={String(goldLane.metadata.diagnostics?.goldFixtureId ?? "Unknown")} />
            <Field label="Gold manifest path" value={goldLane.manifestPath} />
            <Field label="Gold graph path" value={goldLane.goldPath} />
            <Field label="Nodes" value={goldLane.counts.nodes} />
            <Field label="Edges" value={goldLane.counts.edges} />
            <Field label="Beats" value={goldLane.counts.beats} />
            <Field label="Evidence refs" value={goldLane.counts.evidenceRefs} />
          </dl>
        ) : (
          <p className="graph-review-note">Select a gold-backed session to inspect the expected lane.</p>
        )}
      </article>

      <article className="graph-review-lane-card">
        <header className="graph-review-lane-card-header">
          <div>
            <p className="plan-surface-kicker">Live / Graph-ingest</p>
            <h3>{liveLane?.label ?? "Live lane"}</h3>
          </div>
          <span>{liveLane?.status ?? "unknown"}</span>
        </header>
        {liveLane && liveRun ? (
          <dl className="graph-review-lane-meta">
            <Field label="Role" value={liveLane.role} />
            <Field label="Source kind" value={liveLane.sourceKind} />
            <Field label="Run label" value={unknownIfBlank(liveRun.run_label)} />
            <Field label="Run id" value={liveLane.metadata.runId} />
            <Field label="Raw status" value={liveRun.status} />
            <Field label="Manifest path" value={liveLane.manifestPath} />
            <Field label="Run dir" value={liveLane.artifactPath} />
            <Field label="Preview union path" value={liveLane.previewUnionPath} />
            <Field label="Preview union available" value={yesNo(liveRun.preview_union_available)} />
            <Field label="Model id" value={liveLane.metadata.modelId} />
            <Field label="Model provider" value={unknownIfBlank(liveRun.model_provider)} />
            <Field label="Extraction profile" value={liveLane.metadata.extractionProfile} />
            <Field label="Extraction mode" value={liveLane.metadata.extractionMode} />
            <Field label="Vocabulary mode" value={liveLane.metadata.vocabularyMode} />
            <Field label="Nodes" value={liveLane.counts.nodes} />
            <Field label="Edges" value={liveLane.counts.edges} />
            <Field label="Evidence refs" value={liveLane.counts.evidenceRefs} />
            <Field label="Generated at" value={liveRun.generated_at} />
            <Field label="Updated at" value={liveRun.updated_at} />
            <Field label="Created at" value={liveRun.created_at} />
            <Field label="Next actions" value={liveRun.next_actions.length ? liveRun.next_actions.join(", ") : "Unknown"} />
            <Field label="Runner options" value={formatRecord(liveRun.runner_options_summary)} />
            <Field label="Diagnostics" value={formatRecord(liveRun.diagnostics_summary)} />
          </dl>
        ) : (
          <p className="graph-review-note">No live graph-ingest runs available for this session yet.</p>
        )}
      </article>
    </section>
  );
}
