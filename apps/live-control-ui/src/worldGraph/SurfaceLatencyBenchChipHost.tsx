/**
 * OPT-BENCH02: deterministic Plan chip when instrumentation is enabled and the
 * Plan document lacks graph-native TipTap chips. Renders a real GraphNodeHoverToken
 * wired through GraphNodeChipRuntime so glance → Expand still exercises product code.
 */

import { useMemo, type ReactNode } from "react";

import {
  GraphNodeHoverToken,
  presentationForNodeId,
  useGraphNodeChipRuntime,
} from "../graphReference";
import { isSurfaceLatencyInstrumentationEnabled } from "./surfaceLatencyMarks";

export function SurfaceLatencyBenchChipHost(): ReactNode {
  if (!isSurfaceLatencyInstrumentationEnabled()) {
    return null;
  }

  return <SurfaceLatencyBenchChipHostInner />;
}

function SurfaceLatencyBenchChipHostInner(): ReactNode {
  const { nodeViews, onSelectNode } = useGraphNodeChipRuntime();
  const first = useMemo(() => {
    const entries = Object.entries(nodeViews);
    if (entries.length === 0) return null;
    const [nodeId, view] = entries[0]!;
    return { nodeId, view };
  }, [nodeViews]);

  if (!first) return null;

  const presentation = presentationForNodeId(nodeViews, first.nodeId, first.view.label);

  return (
    <div
      className="surface-latency-bench-chip-host"
      data-testid="surface-latency-bench-chip-host"
      // Keep above the Ask-DungeonBuddy chrome (bottom dock intercepts bottom-right clicks).
      style={{
        position: "fixed",
        top: 72,
        right: 16,
        zIndex: 80,
        padding: 6,
        background: "rgba(20, 24, 32, 0.92)",
        border: "1px solid rgba(255,255,255,0.12)",
        borderRadius: 6,
      }}
      title="OPT-BENCH02 seeded chip (instrumentation only)"
    >
      <GraphNodeHoverToken
        presentation={presentation}
        label={first.view.label || first.nodeId}
        pinned={false}
        onSelect={() => onSelectNode(first.nodeId)}
      />
    </div>
  );
}
