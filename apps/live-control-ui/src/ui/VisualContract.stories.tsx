import { PeekRegionProvider, PeekRegionSlot } from "../surfaceInteraction/peekHost";
import { ToolHostView, type ToolHostViewGroup } from "../surfaceInteraction/toolHost/ToolHostView";
import "../styles.css";

const groups: readonly ToolHostViewGroup[] = [{
  groupId: "memory",
  groupLabel: "Memory",
  groupOrder: 0,
  tools: [
    {
      id: "inspect-world",
      label: "Inspect World",
      eyebrow: "Reference",
      availability: { status: "enabled" },
    },
    {
      id: "diagnostics",
      label: "Diagnostics",
      eyebrow: "Review",
      availability: { status: "disabled", disabledReason: "Review-only fixture" },
    },
  ],
}];

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
