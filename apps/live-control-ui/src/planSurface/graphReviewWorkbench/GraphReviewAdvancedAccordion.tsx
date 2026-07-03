import type { ReactNode } from "react";

interface GraphReviewAdvancedAccordionProps {
  title: string;
  description?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}

/**
 * Collapsed-by-default drill-in for diagnostic/metadata content (deltas, evidence,
 * variant inventory, recall scorecards). Keeps the projected prose and object cards
 * as the primary review surface; metadata stays one click away instead of pushing
 * the prose below the fold.
 */
export function GraphReviewAdvancedAccordion({
  title,
  description,
  defaultOpen = false,
  children,
}: GraphReviewAdvancedAccordionProps) {
  return (
    <details className="graph-review-advanced-accordion" open={defaultOpen}>
      <summary>{title}</summary>
      {description ? (
        <p className="graph-review-advanced-accordion-description">{description}</p>
      ) : null}
      <div className="graph-review-advanced-accordion-body">{children}</div>
    </details>
  );
}
