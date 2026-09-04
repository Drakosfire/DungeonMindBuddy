import type { GraphReviewCatalogRun } from "./graphReviewWorkbenchUtils";
import {
  catalogRunStatus,
  isCatalogRunInspectable,
} from "./graphReviewWorkbenchUtils";

interface GraphReviewRunPickerProps {
  runs: GraphReviewCatalogRun[];
  selectedRunId: string | null;
  onSelect: (runId: string | null) => void;
}

function runLabel(entry: GraphReviewCatalogRun, index: number): string {
  const run = entry.run;
  const stamp = run.updated_at ?? run.created_at ?? "unknown time";
  const status = catalogRunStatus(run) || "unknown";
  return `#${index + 1} · ${run.run_id} · ${status} · ${stamp}`;
}

export function GraphReviewRunPicker({
  runs,
  selectedRunId,
  onSelect,
}: GraphReviewRunPickerProps) {
  if (!runs.length) {
    return (
      <p className="graph-gold-review-note">
        No canonical ExtractionRuns for this session yet.
      </p>
    );
  }

  return (
    <label className="graph-gold-review-run-picker">
      <span>Live run</span>
      <select
        value={selectedRunId ?? ""}
        onChange={(event) => onSelect(event.target.value || null)}
      >
        <option value="">Select a run</option>
        {runs.map((entry, index) => (
          <option key={entry.run.run_id} value={entry.run.run_id}>
            {runLabel(entry, index)}
            {isCatalogRunInspectable(entry.run) ? "" : " · not review-ready"}
          </option>
        ))}
      </select>
    </label>
  );
}
