import { useEffect, useMemo, useState } from "react";

import "./GraphReviewExactRunProjection.css";

import type {
  ExactRunEvidenceQuoteCorrection,
  ExactRunReviewAssertion,
  ExactRunReviewPackage,
} from "../../api/types";

interface GraphReviewExactRunProjectionProps {
  review: ExactRunReviewPackage;
  correctionEnabled?: boolean;
  correctionPending?: boolean;
  correctionError?: string | null;
  onCorrectEvidence?: (corrections: ExactRunEvidenceQuoteCorrection[]) => void;
}

export function GraphReviewExactRunProjection({
  review,
  correctionEnabled = false,
  correctionPending = false,
  correctionError = null,
  onCorrectEvidence,
}: GraphReviewExactRunProjectionProps) {
  const [selectedAssertionId, setSelectedAssertionId] = useState<string | null>(
    review.assertions[0]?.assertionId ?? null,
  );
  const selected = useMemo(
    () =>
      review.assertions.find((item) => item.assertionId === selectedAssertionId) ??
      review.assertions[0] ??
      null,
    [review.assertions, selectedAssertionId],
  );
  const highlightedSpanIds = useMemo(
    () => new Set((selected?.evidence ?? []).map((item) => item.sourceSpanRefId)),
    [selected],
  );
  const [replacements, setReplacements] = useState<Record<string, string>>({});
  useEffect(() => setReplacements({}), [review.runId]);
  const invalidTargets = useMemo(() => review.assertions.flatMap((assertion) =>
    assertion.evidence.flatMap((evidence, evidenceIndex) =>
      evidence.anchorQuotes.flatMap((quote, quoteIndex) =>
        evidence.invalidAnchorQuotes?.includes(quote)
          ? [{
              key: `${assertion.assertionId}:${evidenceIndex}:${quoteIndex}`,
              label: assertion.label,
              paragraph: evidence.paragraphText,
              correction: {
                assertionId: assertion.assertionId,
                evidenceIndex,
                sourceSpanRefId: evidence.sourceSpanRefId,
                quoteIndex,
                originalQuote: quote,
              },
            }]
          : [],
      ),
    ),
  ), [review.assertions]);
  const readyToCorrect = invalidTargets.length > 0 && invalidTargets.every(
    (target) => (replacements[target.key] ?? "").trim().length > 0,
  );

  return (
    <div
      className="graph-review-exact-run-projection"
      data-testid="graph-review-exact-run-projection"
    >
      {review.inspectionStatus === "invalid_evidence" ? (
        <p className="graph-review-error" data-testid="graph-review-invalid-evidence-block">
          {review.invalidEvidenceCount ?? "Some"} nonliteral evidence quote(s) in this exact
          candidate. Inspect the affected assertions below; publication is blocked.
        </p>
      ) : null}
      {review.derivedFromRunId ? (
        <p data-testid="graph-review-derived-candidate-lineage">
          Reviewed evidence child of exact run <code>{review.derivedFromRunId}</code>.
          The original candidate remains unchanged.
        </p>
      ) : null}
      {correctionEnabled && invalidTargets.length > 0 ? (
        <form
          data-testid="graph-review-evidence-correction-form"
          onSubmit={(event) => {
            event.preventDefault();
            if (!readyToCorrect || correctionPending || !onCorrectEvidence) return;
            onCorrectEvidence(invalidTargets.map((target) => ({
              ...target.correction,
              replacementQuote: replacements[target.key].trim(),
            })));
          }}
        >
          <h3>Correct nonliteral evidence</h3>
          <p>Choose exact words from each pinned source paragraph. This creates a new child run; it never edits this one.</p>
          {invalidTargets.map((target) => (
            <label key={target.key}>
              {target.label}: replace “{target.correction.originalQuote}”
              <blockquote>{target.paragraph}</blockquote>
              <input
                aria-label={`Literal replacement for ${target.label} quote ${target.correction.quoteIndex + 1}`}
                value={replacements[target.key] ?? ""}
                onChange={(event) => setReplacements((current) => ({
                  ...current, [target.key]: event.target.value,
                }))}
              />
            </label>
          ))}
          {correctionError ? <p className="graph-review-error" role="alert">{correctionError}</p> : null}
          <button type="submit" disabled={!readyToCorrect || correctionPending}>
            {correctionPending ? "Checking corrections…" : "Create reviewed child candidate"}
          </button>
        </form>
      ) : null}
      <section
        className="graph-review-exact-run-source"
        data-testid="graph-review-exact-run-source"
        aria-label="Canonical source prose"
      >
        <h3>Source</h3>
        <p className="graph-review-exact-run-source-meta">
          <code>{review.sourceArtifactId}</code>
          {" · "}
          {review.sourceDomain}
          {review.campaignId ? ` · campaign ${review.campaignId}` : " · no campaign"}
          {review.sessionId ? ` · session ${review.sessionId}` : " · no session"}
        </p>
        <pre
          className="graph-review-exact-run-source-prose"
          data-testid="graph-review-exact-run-source-prose"
        >
          {review.sourceProse}
        </pre>
      </section>

      <section
        className="graph-review-exact-run-assertions"
        data-testid="graph-review-exact-run-assertions"
        aria-label="Exact-run assertions and evidence"
      >
        <h3>Assertions</h3>
        <ul className="graph-review-exact-run-assertion-list">
          {review.assertions.map((assertion) => (
            <li key={assertion.assertionId}>
              <button
                type="button"
                className={
                  selected?.assertionId === assertion.assertionId
                    ? "graph-review-exact-run-assertion is-selected"
                    : "graph-review-exact-run-assertion"
                }
                data-testid={`graph-review-exact-run-assertion-${assertion.assertionId}`}
                aria-pressed={selected?.assertionId === assertion.assertionId}
                onClick={() => setSelectedAssertionId(assertion.assertionId)}
              >
                <strong>{assertion.label}</strong>
                {assertion.evidence.some((item) => (item.invalidAnchorQuotes?.length ?? 0) > 0)
                  ? <span>Invalid evidence</span> : null}
                <span>
                  {assertion.kind}
                  {assertion.summary ? ` · ${assertion.summary}` : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>

        {selected ? (
          <ExactRunAssertionEvidence
            assertion={selected}
            highlightedSpanIds={highlightedSpanIds}
          />
        ) : (
          <p className="plan-projection-empty">No assertions in this exact run.</p>
        )}
      </section>
    </div>
  );
}

function ExactRunAssertionEvidence({
  assertion,
  highlightedSpanIds,
}: {
  assertion: ExactRunReviewAssertion;
  highlightedSpanIds: Set<string>;
}) {
  return (
    <div
      className="graph-review-exact-run-evidence"
      data-testid="graph-review-exact-run-evidence"
      data-assertion-id={assertion.assertionId}
    >
      <h4>
        Evidence for <code>{assertion.label}</code>
      </h4>
      {assertion.evidence.length === 0 ? (
        <p className="graph-review-error">No source evidence bound to this assertion.</p>
      ) : (
        <ul>
          {assertion.evidence.map((item) => (
            <li
              key={`${item.sourceSpanRefId}:${item.startLine ?? 0}`}
              className={
                highlightedSpanIds.has(item.sourceSpanRefId)
                  ? "graph-review-exact-run-evidence-item is-highlighted"
                  : "graph-review-exact-run-evidence-item"
              }
              data-testid="graph-review-exact-run-evidence-item"
              data-span-id={item.sourceSpanRefId}
            >
              <p>
                Span <code>{item.sourceSpanRefId}</code>
                {item.startLine != null
                  ? ` · lines ${item.startLine}${item.endLine != null && item.endLine !== item.startLine ? `–${item.endLine}` : ""}`
                  : ""}
              </p>
              {item.anchorQuotes.length > 0 ? (
                <p data-testid="graph-review-exact-run-evidence-quote">
                  Quote: “{item.anchorQuotes.join(" · ")}”
                </p>
              ) : null}
              {(item.invalidAnchorQuotes?.length ?? 0) > 0 ? (
                <p className="graph-review-error" data-testid="graph-review-invalid-evidence-quote">
                  Not found in this exact source paragraph: “{item.invalidAnchorQuotes?.join(" · ")}”
                </p>
              ) : null}
              <blockquote data-testid="graph-review-exact-run-evidence-paragraph">
                {item.paragraphText || "(span paragraph unavailable)"}
              </blockquote>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
