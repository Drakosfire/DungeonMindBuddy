import type {
  WorldGraphObjectProjectionResult,
  WorldGraphObjectReviewedSourceObservation,
} from "../api/types";
import { formatCampaignScopeCompact } from "../graphObjectCard/graphObjectDisplay";
import "./ReviewedSourceObservations.css";

type SourceBinding = {
  evidenceRefId?: string;
  sourceArtifactId?: string;
  sourceRevisionId?: string | null;
  sourceDomain?: string | null;
  sessionId?: string | null;
};

function matchingBinding(
  observation: WorldGraphObjectReviewedSourceObservation,
  bindings: unknown[] | undefined,
): SourceBinding | null {
  for (const value of bindings ?? []) {
    if (!value || typeof value !== "object") continue;
    const binding = value as SourceBinding;
    if (binding.sourceArtifactId !== observation.sourceArtifactId
      || !binding.evidenceRefId
      || !observation.evidenceRefIds.includes(binding.evidenceRefId)
      || (binding.sourceRevisionId && binding.sourceRevisionId !== observation.sourceRevisionId)) continue;
    return binding;
  }
  return null;
}

function sourceLabel(domain: string | null | undefined): string {
  if (domain === "session_recap") return "Session recap";
  if (domain === "worldbuilding") return "Worldbuilding source";
  if (domain === "plan") return "Plan source";
  return "Reviewed source";
}

function sessionLabel(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const match = /^(?:session[-:_ ]*|s)(\d+)$/i.exec(value.trim());
  return match ? `Session ${Number(match[1])}` : null;
}

function timeLabel(observation: WorldGraphObjectReviewedSourceObservation): string {
  const temporal = observation.temporalScope;
  const session = sessionLabel(temporal?.session_id)
    ?? sessionLabel(temporal?.sessionId);
  if (session) return `Applies: ${session}`;
  if (temporal?.kind === "evergreen" || temporal?.kind === "world_timeless") return "Applies: Evergreen";
  if (temporal?.kind === "fictional_time_ref") {
    const ref = temporal.fictional_time_ref;
    return typeof ref === "string" && ref.trim()
      ? `Fictional time: ${ref.trim()}`
      : "Fictional time reference";
  }
  if (temporal?.kind === "session") return "Applies: Session-specific";
  if (typeof temporal?.kind === "string" && temporal.kind !== "unknown") {
    return `Applies: ${temporal.kind.replace(/[_-]/g, " ")}`;
  }
  return "Time scope not specified";
}

function preview(text: string): string {
  if (text.length <= 220) return text;
  const cutoff = text.lastIndexOf(" ", 220);
  return `${text.slice(0, cutoff > 160 ? cutoff : 220).trimEnd()}…`;
}

export function ReviewedSourceObservations({ result }: { result: WorldGraphObjectProjectionResult | null }) {
  if (!result?.found || !result.resolvedNodeId) return null;
  const observations = (result.reviewedSourceObservations ?? []).filter(
    (observation) => observation.subjectNodeId === result.resolvedNodeId,
  );
  const gapCodes = result.coverageGapCodes ?? [];
  const missingIds = result.coverageMissingIds ?? [];
  if (!observations.length && !gapCodes.length && !missingIds.length) return null;

  return (
    <section className="reviewed-source-observations" aria-label="Reviewed source observations">
      {observations.length ? (
        <>
          <h4>From reviewed sources</h4>
          <p className="reviewed-source-observations__intro">
            Separate observations from source material. Their timing and accounts may differ.
          </p>
          <ol className="reviewed-source-observations__list">
            {observations.map((observation) => {
              const binding = matchingBinding(observation, result.sourceBindings);
              const text = observation.text.trim() || "Observation text unavailable.";
              return (
                <li key={observation.assertionId} className="reviewed-source-observations__item">
                  <div className="reviewed-source-observations__context">
                    <span>Source: {sourceLabel(binding?.sourceDomain)}{sessionLabel(binding?.sessionId) ? ` · ${sessionLabel(binding?.sessionId)}` : ""}</span>
                    <span aria-hidden="true">·</span>
                    <span>{timeLabel(observation)}</span>
                    <span>· {formatCampaignScopeCompact(observation.campaignScope) ?? "Campaign not specified"}</span>
                  </div>
                  {text.length > 220 ? (
                    <details className="reviewed-source-observations__text">
                      <summary>{preview(text)} <span>Read full observation</span></summary>
                      <p>{text}</p>
                    </details>
                  ) : <p className="reviewed-source-observations__text">{text}</p>}
                  <details className="reviewed-source-observations__provenance">
                    <summary>Source and review details</summary>
                    <dl>
                      <dt>Source</dt><dd>{observation.sourceArtifactId}</dd>
                      <dt>Source revision</dt><dd>{observation.sourceRevisionId}</dd>
                      <dt>Reviewed in</dt><dd>{observation.reviewId}</dd>
                      <dt>Published in</dt><dd>{observation.publicationRevisionId}</dd>
                      <dt>Assertion</dt><dd>{observation.assertionId}</dd>
                      {observation.temporalScope ? <><dt>Recorded time scope</dt><dd>{JSON.stringify(observation.temporalScope)}</dd></> : null}
                    </dl>
                  </details>
                </li>
              );
            })}
          </ol>
        </>
      ) : null}
      {gapCodes.length || missingIds.length ? (
        <div className="reviewed-source-observations__coverage" role="status">
          Some source context could not be included in this read.
          <details>
            <summary>Coverage details</summary>
            {gapCodes.length ? <p>Gaps: {gapCodes.join(", ")}</p> : null}
            {missingIds.length ? <p>Missing records: {missingIds.join(", ")}</p> : null}
          </details>
        </div>
      ) : null}
    </section>
  );
}
