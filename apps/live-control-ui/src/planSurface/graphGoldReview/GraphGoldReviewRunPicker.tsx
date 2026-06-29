import type { GraphIngestRunSummary } from "../../api/types";

interface GraphGoldReviewRunPickerProps {
  runs: GraphIngestRunSummary[];
  selectedManifestPath: string | null;
  onSelect: (manifestPath: string | null) => void;
}

function runLabel(run: GraphIngestRunSummary, index: number): string {
  const stamp = run.updated_at ?? run.created_at ?? "unknown time";
  return `#${index + 1} · ${run.status} · ${stamp}`;
}

export function GraphGoldReviewRunPicker({
  runs,
  selectedManifestPath,
  onSelect,
}: GraphGoldReviewRunPickerProps) {
  if (!runs.length) {
    return <p className="graph-gold-review-note">No preview-ready graph-ingest runs for this session yet.</p>;
  }

  return (
    <label className="graph-gold-review-run-picker">
      <span>Live run</span>
      <select
        value={selectedManifestPath ?? runs[0]?.manifest_path ?? ""}
        onChange={(event) => onSelect(event.target.value || null)}
      >
        {runs.map((run, index) => (
          <option key={run.manifest_path} value={run.manifest_path}>
            {runLabel(run, index)}
          </option>
        ))}
      </select>
    </label>
  );
}
