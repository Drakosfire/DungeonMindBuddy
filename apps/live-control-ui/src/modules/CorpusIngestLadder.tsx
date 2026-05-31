import type { RecapIngestStatus } from "../api/types";

import {
  CORPUS_PIPELINE_STEPS,
  corpusReadyForPlanning,
  stepComplete,
} from "./corpusIngestDisplay";

interface CorpusIngestLadderProps {
  result: RecapIngestStatus;
  compact?: boolean;
}

export function CorpusIngestLadder({ result, compact = false }: CorpusIngestLadderProps) {
  const ready = corpusReadyForPlanning(result);

  return (
    <ol className={`corpus-ladder${compact ? " corpus-ladder-compact" : ""}`}>
      {CORPUS_PIPELINE_STEPS.map((step) => {
        const done = stepComplete(result, step);
        const path = result.paths[step.pathKey];
        return (
          <li
            key={step.id}
            className={`corpus-ladder-step${done ? " is-done" : " is-pending"}`}
          >
            <span className="corpus-ladder-marker" aria-hidden="true">
              {done ? "✓" : "○"}
            </span>
            <div className="corpus-ladder-body">
              <span className="corpus-ladder-label">{step.label}</span>
              {!compact && path ? (
                <code className="corpus-ladder-path" title={path}>
                  {path}
                </code>
              ) : null}
            </div>
          </li>
        );
      })}
      <li
        className={`corpus-ladder-step corpus-ladder-summary${
          ready ? " is-done" : " is-pending"
        }`}
      >
        <span className="corpus-ladder-marker" aria-hidden="true">
          {ready ? "✓" : "○"}
        </span>
        <div className="corpus-ladder-body">
          <span className="corpus-ladder-label">Ready for planning activation</span>
        </div>
      </li>
    </ol>
  );
}
