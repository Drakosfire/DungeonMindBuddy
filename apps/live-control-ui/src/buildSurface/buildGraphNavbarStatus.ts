import type { WorldGraphProjection } from "../api/types";
import type { AppChromeNavbarStatus } from "../chrome/AppChrome";
import type { GraphReferenceProjectionState } from "../graphReference";

/** Format Build's World Graph resolver state for the persistent site nav (single-line, no eyebrow stack). */
export function buildGraphNavbarStatus(input: {
  projectionState: GraphReferenceProjectionState;
  projection: WorldGraphProjection | null;
  projectionError?: string | null;
}): AppChromeNavbarStatus {
  const { projectionState, projection, projectionError } = input;

  if (projectionState === "loading") {
    return {
      id: "build-navbar-graph-status",
      label: "Graph · Loading…",
      tone: "loading",
    };
  }

  if (projectionState === "error") {
    const detail = projectionError?.trim();
    return {
      id: "build-navbar-graph-status",
      label: detail ? `Graph · ${detail}` : "Graph · Error",
      tone: "error",
    };
  }

  if (projectionState === "unavailable") {
    return {
      id: "build-navbar-graph-status",
      label: "Graph · Unavailable",
      tone: "unavailable",
    };
  }

  const nodeCount = projection?.summary.nodeCount ?? 0;
  const revisionId = projection?.snapshot.revisionId?.trim() || null;
  const shortRevision = revisionId && revisionId.length > 12 ? `${revisionId.slice(0, 10)}…` : revisionId;
  const nodes = `${nodeCount} node${nodeCount === 1 ? "" : "s"}`;

  return {
    id: "build-navbar-graph-status",
    label: shortRevision ? `Graph · ${nodes} · ${shortRevision}` : `Graph · ${nodes}`,
    tone: "ready",
  };
}
