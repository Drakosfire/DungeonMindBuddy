import type { AuthoredOverlayProjectionSummary } from "../../api/types";

function countByKind(summary: AuthoredOverlayProjectionSummary): string {
  const parts: string[] = [];
  if (summary.projected_node_count > 0) {
    parts.push(
      `${summary.projected_node_count} new object${summary.projected_node_count === 1 ? "" : "s"}`,
    );
  }
  if (summary.projected_link_existing_count > 0) {
    parts.push(
      `${summary.projected_link_existing_count} linked alias${summary.projected_link_existing_count === 1 ? "" : "es"}`,
    );
  }
  if (summary.projected_relationship_count > 0) {
    parts.push(
      `${summary.projected_relationship_count} relationship${summary.projected_relationship_count === 1 ? "" : "s"}`,
    );
  }
  return parts.length ? parts.join(" · ") : "0 projected";
}

export function GraphAuthoredOverlaySummary({
  summary,
}: {
  summary: AuthoredOverlayProjectionSummary | null | undefined;
}) {
  if (!summary) {
    return (
      <p className="graph-authored-overlay-summary graph-authored-overlay-summary--missing">
        No authored overlay committed for this session yet.
      </p>
    );
  }

  if (!summary.loaded) {
    const missingOnly = summary.diagnostics.every(
      (item) => item.code === "authored_overlay_missing",
    );
    if (missingOnly) {
      return (
        <p
          className="graph-authored-overlay-summary graph-authored-overlay-summary--missing"
          data-testid="graph-authored-overlay-summary"
        >
          No authored overlay committed for this session yet.
        </p>
      );
    }
    return (
      <div
        className="graph-authored-overlay-summary graph-authored-overlay-summary--error"
        data-testid="graph-authored-overlay-summary"
        role="status"
      >
        <p>Authored overlay could not be loaded.</p>
        <ul>
          {summary.diagnostics.map((item) => (
            <li key={`${item.code}:${item.message}`}>{item.message}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <p
      className="graph-authored-overlay-summary graph-authored-overlay-summary--loaded"
      data-testid="graph-authored-overlay-summary"
      role="status"
    >
      Authored overlay loaded: {summary.assertion_count} assertion
      {summary.assertion_count === 1 ? "" : "s"} · {countByKind(summary)}
    </p>
  );
}
