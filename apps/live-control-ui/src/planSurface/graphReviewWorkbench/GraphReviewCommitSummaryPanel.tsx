import type { GraphGoldAuthoringCommitResponse } from "../../api/types";

interface Props {
  commitResponse: GraphGoldAuthoringCommitResponse;
}

export function GraphReviewCommitSummaryPanel({ commitResponse }: Props) {
  return (
    <div>
      <dl className="graph-review-lane-meta">
        <div><dt>Commit id</dt><dd>{commitResponse.commit_id}</dd></div>
        <div><dt>Fixture relpath</dt><dd>{commitResponse.fixture_relpath}</dd></div>
        <div><dt>Backup relpath</dt><dd>{commitResponse.backup_relpath ?? "No backup written"}</dd></div>
        <div><dt>Event log relpath</dt><dd>{commitResponse.event_log_relpath ?? "No event written"}</dd></div>
        <div><dt>Nodes added</dt><dd>{commitResponse.changed_counts.nodes_added}</dd></div>
        <div><dt>Nodes asserted</dt><dd>{commitResponse.changed_counts.nodes_asserted}</dd></div>
        <div><dt>Edges added</dt><dd>{commitResponse.changed_counts.edges_added}</dd></div>
        <div><dt>Link intents recorded</dt><dd>{commitResponse.changed_counts.link_intents_recorded}</dd></div>
        <div><dt>Operations skipped</dt><dd>{commitResponse.changed_counts.operations_skipped}</dd></div>
      </dl>
      <h5>Applied operations</h5>
      <ul>{commitResponse.applied_operations.map((operation) => <li key={operation.operation_id}>{operation.summary}</li>)}</ul>
      <h5>Skipped operations</h5>
      <ul>{commitResponse.skipped_operations.map((operation) => <li key={operation.operation_id}>{operation.reason}</li>)}</ul>
      {commitResponse.diagnostics.length ? <ul>{commitResponse.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
    </div>
  );
}
