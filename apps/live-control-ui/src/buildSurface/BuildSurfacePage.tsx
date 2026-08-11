import { AppChrome } from "../chrome/AppChrome";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceContext } from "./BuildSurfaceContext";
import { BuildSurfaceShell } from "./BuildSurfaceShell";
import { BUILD_SURFACE_LABEL } from "./buildSurfaceConfig";
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";
import { useBuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";
import "./buildSurface.css";

export function BuildSurfacePage() {
  const controller = useBuildWorkspaceDocumentController();

  return (
    <AppChrome activeRoute="build">
      <BuildSurfaceContext {...controller} />
      {controller.activeDocumentId ? (
        <MarkdownCanvasSessionProvider
          key={controller.activeDocumentId}
          documentId={controller.activeDocumentId}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={controller.activeDocumentId}>
            <BuildIngestToolbar documentId={controller.activeDocumentId} />
            <BuildSurfaceShell
              onAuthoringStatusChange={controller.setAuthoringStatusLabel}
            />
          </BuildReferenceCapability>
        </MarkdownCanvasSessionProvider>
      ) : (
        <>
          <main
            className={
              controller.loadStatus === "error"
                ? "build-surface-empty app-error"
                : "build-surface-empty"
            }
            data-testid="build-surface-empty"
          >
            <h1>{BUILD_SURFACE_LABEL}</h1>
            {controller.loadStatus === "error" ? (
              <p role="alert">Could not open that source. Try another.</p>
            ) : controller.loadStatus === "loading" ? (
              <p>Loading worldbuilding source…</p>
            ) : (
              <p>Choose or create a source above.</p>
            )}
          </main>
          <BuildReferenceCapability documentId={null} />
        </>
      )}
    </AppChrome>
  );
}
