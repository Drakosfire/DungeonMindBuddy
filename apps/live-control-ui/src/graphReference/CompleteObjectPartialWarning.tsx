import type { WorldGraphObjectProjectionResult } from "../api/types";
import { completeWorldObjectPartialCopy } from "./fullWorldObjectProjection";

export function CompleteObjectPartialWarning({
  result,
}: {
  result: WorldGraphObjectProjectionResult | null;
}) {
  if (!result || result.completeness.status !== "partial") return null;
  return (
    <p
      className="graph-preview-error"
      role="status"
      data-testid="complete-object-partial-warning"
    >
      {completeWorldObjectPartialCopy(result)}
    </p>
  );
}
