import { AppChrome } from "../chrome/AppChrome";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "../agentInteraction/surfaceInteractionCompat";
import { usePublishSurfaceInteraction } from "../agentInteraction/usePublishSurfaceInteraction";
import { PeekRegionProvider, PeekRegionSlot } from "../surfaceInteraction/peekHost";
import { ToolHostView, type ToolHostViewGroup } from "../surfaceInteraction/toolHost/ToolHostView";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
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

const editDockTarget = { kind: "document", id: "dock-layout-fixture" } as const;

const indexEditDockPublication: SurfaceInteractionPublication = {
  ...ROUTE_COMPATIBILITY_PUBLICATIONS.index,
  label: "Edit dock layout fixture",
  canvas: { canvasId: "edit-dock-layout-fixture", workObject: editDockTarget },
};

const planEditDockPublication: SurfaceInteractionPublication = {
  ...indexEditDockPublication,
  surfaceId: "plan",
  identity: { surfaceId: "plan", instanceKey: "edit-dock-layout-fixture" },
};

function EditHostDockFixture({ surfaceId }: { surfaceId: "index" | "plan" }) {
  const publication = surfaceId === "plan" ? planEditDockPublication : indexEditDockPublication;
  usePublishSurfaceInteraction(publication);
  return (
    <AppChrome
      activeRoute={surfaceId}
      editToolboxLayout="dock"
      editorTools={{
        target: editDockTarget,
        tools: {
          sections: [{
            id: "fixture",
            title: "Editing tools",
            defaultOpen: true,
            actions: [{ id: "fixture-action", label: "Example edit action", onClick: noAction }],
            panel: <p>Mounted EditHost responsive layout content.</p>,
          }],
        },
      }}
    >
      <main
        className={surfaceId === "plan" ? "plan-surface-root" : undefined}
        data-testid="dock-responsive-canvas"
        style={{
          boxSizing: "border-box",
          minWidth: 0,
          minHeight: "24rem",
          padding: "1rem",
          width: "100%",
        }}
      >
        <h1>Central canvas</h1>
        <p>The central work surface retains a usable reading width on a narrow viewport.</p>
      </main>
    </AppChrome>
  );
}

function EditHostDockStory({ surfaceId }: { surfaceId: "index" | "plan" }) {
  return (
    <AgentInteractionProvider>
      <PeekRegionProvider>
        <EditHostDockFixture surfaceId={surfaceId} />
      </PeekRegionProvider>
    </AgentInteractionProvider>
  );
}

export const EditHostDockResponsive = () => <EditHostDockStory surfaceId="plan" />;

export const EditHostDockResponsiveOtherSurface = () => <EditHostDockStory surfaceId="index" />;
