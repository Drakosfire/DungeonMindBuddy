import { useEffect, useState } from "react";

import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { announceSelectedWorldLocationChange } from "../selectedWorld/SelectedWorldContext";
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
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);
  const controller = useBuildWorkspaceDocumentController();
  const [extractionTarget, setExtractionTarget] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!controller.activeRecord || typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("documentId") === controller.activeRecord.document_id) {
      announceSelectedWorldLocationChange();
    }
  }, [controller.activeRecord]);

  return (
    <AppChrome activeRoute="build" editorTools={editorTools} editToolboxLayout="overlay">
      {controller.activeDocumentId ? (
        <MarkdownCanvasSessionProvider
          key={controller.activeDocumentId}
          documentId={controller.activeDocumentId}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildSurfaceContext {...controller} extractionTargetRef={setExtractionTarget} />
          <BuildReferenceCapability documentId={controller.activeDocumentId}>
            <BuildIngestToolbar documentId={controller.activeDocumentId} target={extractionTarget} />
            <BuildSurfaceShell onEditorTools={setEditorTools} />
          </BuildReferenceCapability>
        </MarkdownCanvasSessionProvider>
      ) : (
        <>
          <BuildSurfaceContext {...controller} />
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
