import { useState } from "react";

import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  candidateScopeLabel,
  formatResolverCandidateLabel,
} from "./graphObjectCandidateScope";
import type { GraphObjectAuthoringLinkExistingOperation } from "./graphObjectAuthoringDraft";

const MAX_BIND_CANDIDATES = 5;

function readableCandidateType(candidate: GraphReviewExistingObjectCandidate): string | null {
  const raw = (candidate.role || candidate.kind || "").trim().toLocaleLowerCase();
  if (!raw) return null;
  if (raw === "pc" || raw === "player_character" || raw === "player character") {
    return "player character";
  }
  if (raw === "npc" || raw === "non_player_character" || raw === "non-player character") {
    return "NPC";
  }
  return raw.replace(/_/g, " ");
}

function candidateIdentitySentence(
  phrase: string,
  candidate: GraphReviewExistingObjectCandidate,
): string {
  const candidateLabel = candidate.label.trim();
  const type = readableCandidateType(candidate);
  const isPartyMember =
    candidate.graph_scope === "party_pc" ||
    candidate.source_label?.toLocaleLowerCase().includes("party") === true;
  const details = [
    type ? `the ${type}` : null,
    isPartyMember ? "a member of the party" : null,
  ].filter(Boolean) as string[];
  const detailSentence = details.length > 1
    ? `${details[0]} who is ${details.slice(1).join(" and ")}`
    : details[0] ?? `the object from ${candidateScopeLabel(candidate)}`;

  if (candidateLabel.toLocaleLowerCase() === phrase.toLocaleLowerCase()) {
    return `${phrase} is probably ${detailSentence}.`;
  }
  return `“${phrase}” is probably ${candidateLabel}, ${detailSentence}.`;
}

function confidenceLabel(confidence: GraphReviewExistingObjectCandidate["confidence"]): string {
  return `${confidence.charAt(0).toLocaleUpperCase()}${confidence.slice(1)} confidence`;
}

export function GraphObjectAuthoringBindExistingPanel({
  selectedText,
  status,
  error = null,
  candidates,
  onBindExisting,
  binding = false,
  wizardMode = false,
  onChooseCreateNew,
}: {
  selectedText: string;
  status: "idle" | "loading" | "ready" | "error";
  error?: string | null;
  candidates: GraphReviewExistingObjectCandidate[];
  onBindExisting: (
    candidate: GraphReviewExistingObjectCandidate,
    operation: GraphObjectAuthoringLinkExistingOperation,
  ) => void;
  binding?: boolean;
  wizardMode?: boolean;
  onChooseCreateNew?: () => void;
}) {
  const [showAllCandidates, setShowAllCandidates] = useState(false);
  const phrase = selectedText.trim();
  if (!phrase) {
    return null;
  }

  const topCandidates = candidates.slice(0, MAX_BIND_CANDIDATES);
  const confidentDuplicateCandidates = topCandidates.filter(
    (candidate) =>
      candidate.confidence === "high" &&
      candidate.label.trim().toLocaleLowerCase() === phrase.toLocaleLowerCase(),
  );
  // A recap phrase is already known to be present in the current recap. When
  // the resolver finds both that projection row and a wider-scope identity,
  // lead with the wider-scope identity so the suggestion is actually useful.
  const confidentDuplicate =
    confidentDuplicateCandidates.find(
      (candidate) => candidate.graph_scope !== "current_recap_projection",
    ) ?? confidentDuplicateCandidates[0];
  const confidentDuplicateOperation: GraphObjectAuthoringLinkExistingOperation =
    confidentDuplicate ? "reference" : "alias";
  const showCandidateList = !wizardMode || showAllCandidates;

  return (
    <section
      className="graph-object-authoring-bind-existing"
      aria-label="Bind highlighted text to an existing object"
      data-testid="graph-object-authoring-bind-existing"
      data-wizard-mode={wizardMode ? "true" : "false"}
    >
      {!wizardMode ? (
        <header className="graph-object-authoring-bind-existing-header">
          <p className="plan-surface-kicker">Bind or create</p>
          <h4>Is “{phrase}” already in the campaign?</h4>
          <p className="graph-object-authoring-surface-hint">
            An exact primary-label match is the existing object. A different phrase can be staged as an alias, or you can keep scrolling to create a new object.
          </p>
        </header>
      ) : null}

      {status === "loading" ? (
        <p role="status" data-testid="graph-object-authoring-bind-existing-loading">
          Searching campaign sources…
        </p>
      ) : null}

      {status === "error" ? (
        <p role="alert" data-testid="graph-object-authoring-bind-existing-error">
          {error ?? "Could not search existing objects."}
        </p>
      ) : null}

      {wizardMode && confidentDuplicate ? (
        <div
          className="graph-object-authoring-duplicate-suggestion"
          role="dialog"
          aria-labelledby="graph-object-authoring-duplicate-suggestion-title"
          data-testid="graph-object-authoring-duplicate-suggestion"
        >
          <p className="plan-surface-kicker">Confident duplicate suggestion</p>
          <h5 id="graph-object-authoring-duplicate-suggestion-title">
            Probably the same object
          </h5>
          <p data-testid="graph-object-authoring-duplicate-sentence">
            {candidateIdentitySentence(phrase, confidentDuplicate)}
          </p>
          <dl className="graph-object-authoring-duplicate-details">
            <div>
              <dt>Object</dt>
              <dd>{confidentDuplicate.label}</dd>
            </div>
            <div>
              <dt>Type</dt>
              <dd>{readableCandidateType(confidentDuplicate) ?? "—"}</dd>
            </div>
            <div>
              <dt>Context</dt>
              <dd>{candidateScopeLabel(confidentDuplicate)}</dd>
            </div>
            <div>
              <dt>Match</dt>
              <dd>{confidenceLabel(confidentDuplicate.confidence)}</dd>
            </div>
          </dl>
          <div className="graph-object-authoring-surface-actions">
            <button
              type="button"
              data-testid="graph-object-authoring-duplicate-use-existing-button"
              disabled={binding}
              onClick={() => onBindExisting(confidentDuplicate, confidentDuplicateOperation)}
            >
              Use {confidentDuplicate.label}
            </button>
            {onChooseCreateNew ? (
              <button
                type="button"
                className="graph-object-authoring-secondary-action"
                disabled={binding}
                onClick={onChooseCreateNew}
              >
                This is different
              </button>
            ) : null}
          </div>
        </div>
      ) : null}

      {wizardMode && !confidentDuplicate && topCandidates.length > 0 ? (
        <p className="graph-object-authoring-bind-existing-no-confident-match">
          No confident duplicate was found yet. See all matches if you want to choose an existing object.
        </p>
      ) : null}

      {status === "ready" && topCandidates.length === 0 ? (
        <p data-testid="graph-object-authoring-bind-existing-empty">
          No likely existing objects matched. Create a new object below if this
          phrase should become its own node.
        </p>
      ) : null}

      {wizardMode && topCandidates.length > 0 ? (
        <button
          type="button"
          className="graph-object-authoring-see-all-matches"
          data-testid="graph-object-authoring-see-all-matches"
          onClick={() => setShowAllCandidates((current) => !current)}
        >
          {showAllCandidates ? "Hide all matches" : "See all matches"}
        </button>
      ) : null}

      {topCandidates.length > 0 && showCandidateList ? (
        <ul
          className="graph-object-authoring-bind-existing-list"
          data-testid="graph-object-authoring-bind-existing-list"
        >
          {topCandidates.map((candidate) => {
            const exactPrimaryLabel = candidate.label.trim().toLocaleLowerCase() === phrase.toLocaleLowerCase();
            const operation: GraphObjectAuthoringLinkExistingOperation = exactPrimaryLabel
              ? "reference"
              : "alias";
            return (
              <li
                key={`${candidate.graph_scope ?? candidate.source}:${candidate.candidate_id}`}
                className="graph-object-authoring-bind-existing-item"
              >
                <div className="graph-object-authoring-bind-existing-meta">
                  <p className="graph-object-authoring-bind-existing-label">
                    {formatResolverCandidateLabel(candidate)}
                  </p>
                  <p className="graph-object-authoring-bind-existing-subline">
                    {candidateScopeLabel(candidate)}
                    {candidate.confidence ? ` · ${candidate.confidence}` : ""}
                    {candidate.reason ? ` · ${candidate.reason}` : ""}
                    {exactPrimaryLabel ? " · exact primary-label match" : " · different label"}
                  </p>
                </div>
                <button
                  type="button"
                  data-testid={
                    exactPrimaryLabel
                      ? "graph-object-authoring-bind-as-reference-button"
                      : "graph-object-authoring-bind-as-alias-button"
                  }
                  disabled={binding}
                  onClick={() => onBindExisting(candidate, operation)}
                >
                  {wizardMode
                    ? exactPrimaryLabel
                      ? `Use ${candidate.label}`
                      : `Add ${candidate.label} as alias`
                    : exactPrimaryLabel
                      ? "Use existing node"
                      : "Add as alias"}
                </button>
              </li>
            );
          })}
        </ul>
      ) : null}

    </section>
  );
}
