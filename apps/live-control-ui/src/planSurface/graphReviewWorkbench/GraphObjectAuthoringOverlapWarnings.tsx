import type { ReactNode } from "react";

import type { GraphObjectAuthoringOverlapWarning } from "./graphObjectAuthoringOverlap";

export function GraphObjectAuthoringOverlapWarnings({
  warnings,
  title = "Possible duplicates",
  renderAction,
}: {
  warnings: GraphObjectAuthoringOverlapWarning[];
  title?: string;
  renderAction?: (warning: GraphObjectAuthoringOverlapWarning) => ReactNode;
}) {
  if (warnings.length === 0) {
    return null;
  }

  return (
    <div
      className="graph-object-authoring-overlap-warnings"
      data-testid="graph-object-authoring-overlap-warnings"
      role="status"
    >
      <p className="graph-object-authoring-overlap-warnings-title">{title}</p>
      <ul>
        {warnings.map((warning) => (
          <li key={`${warning.code}:${warning.message}`}>
            {warning.message}
            {renderAction ? renderAction(warning) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
