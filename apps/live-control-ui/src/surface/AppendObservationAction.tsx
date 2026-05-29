import { useState } from "react";

import type {
  ProjectionCapability,
  ProjectionCommand,
  ProjectionTarget,
  ProjectionWriteResult,
} from "../api/types";

interface AppendObservationActionProps {
  target: ProjectionTarget;
  capability: ProjectionCapability;
  onSubmitCommand: (command: ProjectionCommand) => Promise<ProjectionWriteResult>;
  onAccepted?: (result: ProjectionWriteResult) => Promise<void> | void;
}

function makeIdempotencyKey(target: ProjectionTarget): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `ui-append-observation:${target.target_type}:${target.target_id}:${crypto.randomUUID()}`;
  }
  return `ui-append-observation:${target.target_type}:${target.target_id}:${Date.now()}`;
}

export function AppendObservationAction({
  target,
  capability,
  onSubmitCommand,
  onAccepted,
}: AppendObservationActionProps) {
  const [expanded, setExpanded] = useState(false);
  const [observation, setObservation] = useState("");
  const [sessionClock, setSessionClock] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ProjectionWriteResult | null>(null);

  const trimmedObservation = observation.trim();
  const tooLong = trimmedObservation.length > 2000;
  const canSubmit = trimmedObservation.length > 0 && !tooLong && !submitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!trimmedObservation) {
      setError("Observation is required.");
      return;
    }
    if (tooLong) {
      setError("Observation must be 2000 characters or fewer.");
      return;
    }
    const command: ProjectionCommand = {
      command_type: "append_observation",
      target,
      lane: "observed_play",
      payload: {
        observation: trimmedObservation,
        session_clock: sessionClock.trim() || "live-control",
        visibility: "live_note",
      },
      evidence: [],
      requested_by: {
        requester_type: "human_ui",
        requester_id: "live-control-ui",
      },
      idempotency_key: makeIdempotencyKey(target),
    };
    setSubmitting(true);
    try {
      const writeResult = await onSubmitCommand(command);
      setResult(writeResult);
      if (writeResult.status === "accepted" || writeResult.status === "noop") {
        await onAccepted?.(writeResult);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit command.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="append-observation-action" aria-label="Append observation action">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        disabled={!capability.enabled || submitting}
      >
        Append observation
      </button>
      {expanded ? (
        <form className="append-observation-form" onSubmit={handleSubmit}>
          <label>
            Observation
            <textarea
              aria-label="Observation"
              value={observation}
              onChange={(e) => setObservation(e.target.value)}
              maxLength={2100}
              disabled={submitting}
            />
          </label>
          <label>
            Session clock (optional)
            <input
              aria-label="Session clock (optional)"
              value={sessionClock}
              onChange={(e) => setSessionClock(e.target.value)}
              disabled={submitting}
            />
          </label>
          <div className="append-observation-actions">
            <button type="submit" disabled={!canSubmit}>
              {submitting ? "Submitting…" : "Submit observation"}
            </button>
            <button type="button" onClick={() => setExpanded(false)} disabled={submitting}>
              Cancel
            </button>
          </div>
          {error ? <p className="module-error">{error}</p> : null}
          {tooLong ? (
            <p className="module-error">Observation must be 2000 characters or fewer.</p>
          ) : null}
          {result ? (
            <div className="write-result">
              {result.status === "accepted" ? (
                <>
                  <p className="write-result-title">Observation appended.</p>
                  {result.events_appended.map((id) => (
                    <p key={id} className="module-muted">
                      Event: {id}
                    </p>
                  ))}
                  {result.invalidations.length > 0 ? (
                    <p className="module-muted">
                      Invalidated: {result.invalidations.map((i) => i.projection_key).join(", ")}
                    </p>
                  ) : null}
                </>
              ) : null}
              {result.status === "rejected" ? (
                <>
                  <p className="write-result-title">Command rejected.</p>
                  {result.conflicts.map((conflict, idx) => (
                    <p key={`${conflict.conflict_type}:${idx}`} className="module-muted">
                      {conflict.conflict_type}: {conflict.message}
                    </p>
                  ))}
                </>
              ) : null}
              {result.status === "noop" ? (
                <>
                  <p className="write-result-title">No change.</p>
                  {result.diagnostics.map((diag, idx) => (
                    <p key={`${diag}:${idx}`} className="module-muted">
                      {diag}
                    </p>
                  ))}
                </>
              ) : null}
              {result.status === "conflict" ? (
                <>
                  <p className="write-result-title">Conflict.</p>
                  {result.conflicts.map((conflict, idx) => (
                    <p key={`${conflict.conflict_type}:${idx}`} className="module-muted">
                      {conflict.conflict_type}: {conflict.message}
                    </p>
                  ))}
                </>
              ) : null}
            </div>
          ) : null}
        </form>
      ) : null}
    </section>
  );
}
