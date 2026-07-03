import type { GraphGoldAuthoringVerifyCommitResponse } from "../../api/types";

interface Props {
  verificationResponse: GraphGoldAuthoringVerifyCommitResponse;
  onShowCommittedObject?: (targetId: string) => void;
  canShowCommittedObject?: (targetId: string) => boolean;
}

function title(operationType: string): string {
  return operationType.split("_").map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ");
}

export function GraphReviewCommitVerificationPanel({ verificationResponse, onShowCommittedObject, canShowCommittedObject }: Props) {
  const verificationCopy = verificationResponse.verification_status === "verified"
    ? "Gold projection reloaded. Committed changes verified."
    : verificationResponse.verification_status === "missing"
      ? "Gold projection reloaded, but expected committed changes were not found."
      : "Gold projection reloaded. Some committed changes are fixture-only or event-only.";

  return (
    <section aria-label="Verified committed changes">
      <h5>Verified committed changes</h5>
      <p role="status">{verificationCopy}</p>
      <ul>
        {verificationResponse.checked_operations.map((operation) => (
          <li key={operation.operation_id}>
            <strong>{title(operation.operation_type)}</strong> — Status: {operation.verification_status.replaceAll("_", " ")}
            {operation.target_id ? <> Target: {operation.target_id}</> : null}
            <p>{operation.summary}</p>
            {operation.verification_status === "recorded_event_only" && operation.operation_type === "link_existing_intent" ? <p>No identity link was written.</p> : null}
            {operation.target_id && operation.verification_status === "found_in_gold_projection" && onShowCommittedObject && (canShowCommittedObject?.(operation.target_id) ?? true) ? <button type="button" onClick={() => onShowCommittedObject(operation.target_id!)}>Show {operation.target_id}</button> : null}
          </li>
        ))}
      </ul>
      {verificationResponse.diagnostics.length ? <ul>{verificationResponse.diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}-${index}`}>{diagnostic.message}</li>)}</ul> : null}
    </section>
  );
}
