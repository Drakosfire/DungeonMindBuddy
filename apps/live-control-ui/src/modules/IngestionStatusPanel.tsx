import type { ReactNode } from "react";

import type { RecapIngestStatus } from "../api/types";

interface IngestionStatusPanelProps {
  result: RecapIngestStatus | null;
}

function rows(values: string[]): ReactNode {
  if (values.length === 0) {
    return <li className="module-muted">None</li>;
  }
  return (
    <>
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </>
  );
}

export function IngestionStatusPanel({ result }: IngestionStatusPanelProps) {
  if (!result) {
    return <p className="module-muted">No ingestion result yet.</p>;
  }
  const report = result.ingest_report ?? {};
  const previewDiff = typeof report.preview_diff === "string" ? report.preview_diff : "";

  return (
    <section className="ingestion-status-panel">
      <h4>Status</h4>
      <p>
        <strong>{result.status}</strong>
      </p>
      <div className="ingestion-status-columns">
        <div>
          <h5>States</h5>
          <ul>{rows(result.states)}</ul>
        </div>
        <div>
          <h5>Warnings</h5>
          <ul>{rows(result.warnings)}</ul>
        </div>
        <div>
          <h5>Errors</h5>
          <ul>{rows(result.errors)}</ul>
        </div>
        <div>
          <h5>Next actions</h5>
          <ul>{rows(result.next_actions)}</ul>
        </div>
      </div>

      <h4>Canonical preview</h4>
      <ul>
        <li>title_line_stripped: {String(report.title_line_stripped ?? false)}</li>
        <li>paragraph_count_in: {String(report.paragraph_count_in ?? "-")}</li>
        <li>paragraph_count_out: {String(report.paragraph_count_out ?? "-")}</li>
        <li>duplicates_detected: {String(report.duplicates_detected ?? "-")}</li>
        <li>duplicates_removed: {String(report.duplicates_removed ?? "-")}</li>
        <li>session_memory_record_count: {String(report.session_memory_record_count ?? "-")}</li>
        <li>session_memory_check: {String(report.session_memory_check ?? "-")}</li>
      </ul>
      <h5>Preview diff</h5>
      <pre aria-label="Canonical preview diff">{previewDiff || "(no diff available)"}</pre>
    </section>
  );
}
