import { PeekRegionProvider, PeekRegionSlot } from "../surfaceInteraction/peekHost";
import type { SurfaceInteractionToolContribution } from "../surfaceInteraction/types";
import type { ToolHostGroup } from "../surfaceInteraction/toolHost/groupTools";
import { ToolHostView } from "../surfaceInteraction/toolHost/ToolHostView";
import "../styles.css";

const tools: readonly SurfaceInteractionToolContribution[] = [
  {
    id: "inspect-world",
    label: "Inspect World",
    eyebrow: "Reference",
    placement: { groupId: "memory", groupLabel: "Memory", groupOrder: 0, itemOrder: 0 },
    availability: { status: "enabled" },
    activation: { kind: "command", invoke: () => undefined },
  },
  {
    id: "diagnostics",
    label: "Diagnostics",
    eyebrow: "Review",
    placement: { groupId: "memory", groupLabel: "Memory", groupOrder: 0, itemOrder: 1 },
    availability: { status: "disabled", disabledReason: "Review-only fixture" },
    activation: { kind: "command", invoke: () => undefined },
  },
];

const groups: readonly ToolHostGroup[] = [
  { groupId: "memory", groupLabel: "Memory", groupOrder: 0, tools },
];

const noAction = () => undefined;

export const ToolHostOverlay = () => (
  <>
    <main style={{ maxWidth: 760, margin: "7rem auto", padding: 32 }}>
      <h1>Current work</h1>
      <p>ToolHost remains a secondary launcher over the active page.</p>
    </main>
    <ToolHostView
      groups={groups}
      isOpen
      usesIngestPeek={false}
      onToggle={noAction}
      onDismiss={noAction}
      onActivate={noAction}
    />
  </>
);

export const ToolHostPeek = () => (
  <PeekRegionProvider>
    <div className="app-chrome-workspace" style={{ minHeight: "100vh", padding: "5rem 2rem 2rem" }}>
      <main className="app-chrome-center" style={{ padding: "1rem 2rem" }}>
        <h1>Session recap</h1>
        <p>The exact loaded recap stays in the center while Tools claim secondary context.</p>
      </main>
      <PeekRegionSlot />
    </div>
    <ToolHostView
      groups={groups}
      isOpen
      usesIngestPeek
      onToggle={noAction}
      onDismiss={noAction}
      onActivate={noAction}
    />
  </PeekRegionProvider>
);
