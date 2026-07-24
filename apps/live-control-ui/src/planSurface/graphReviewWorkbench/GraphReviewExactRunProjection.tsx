import { useMemo, useState } from "react";

import type { ExactRunReviewAssertion, ExactRunReviewPackage } from "../../api/types";

interface GraphReviewExactRunProjectionProps {
  review: ExactRunReviewPackage;
}

export function GraphReviewExactRunProjection({ review }: GraphReviewExactRunProjectionProps) {
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

  return (
    <div
      className="graph-review-exact-run-projection"
      data-testid="graph-review-exact-run-projection"
    >
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
