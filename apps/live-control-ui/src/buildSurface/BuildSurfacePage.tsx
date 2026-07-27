import { useEffect, useMemo, useRef, useState } from "react";

import { createWorkspaceDocument } from "../api/liveApi";
import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { useWorkspaceDocumentUrlSelection } from "../workspaceDocument/useWorkspaceDocumentUrlSelection";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceShell } from "./BuildSurfaceShell";
import { BUILD_SURFACE_LABEL, BUILD_SURFACE_ROUTE } from "./buildSurfaceConfig";
import {
  BUILD_WORLDBUILDING_STARTER_TITLE,
  buildWorldbuildingStarterContent,
} from "./buildWorldbuildingStarter";

import "../../../../evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css";
import "../tiptap/tiptapSpike.css";
import "./buildSurface.css";

function navigateToDocument(documentId: string): void {
  const url = new URL(window.location.href);
  url.pathname = BUILD_SURFACE_ROUTE;
  url.searchParams.set("documentId", documentId);
  window.history.replaceState({}, "", url.toString());
  window.dispatchEvent(new PopStateEvent("popstate"));
}

/**
 * Bare /build auto-creates a draft and lands on the preloaded markdown canvas.
 */
export function BuildSurfacePage() {
  const documentId = useWorkspaceDocumentUrlSelection();
  const [createError, setCreateError] = useState<string | null>(null);
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);
  const createStartedRef = useRef(false);
  const emptyMarkdownFallback = useMemo(() => buildWorldbuildingStarterContent(), []);

  useEffect(() => {
    if (documentId || createStartedRef.current) {
      return;
    }
    createStartedRef.current = true;
    setCreateError(null);
    void createWorkspaceDocument({
      title: BUILD_WORLDBUILDING_STARTER_TITLE,
      campaign_id: "eldyrwild",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    })
      .then((created) => {
        navigateToDocument(created.document_id);
      })
      .catch((error: unknown) => {
        createStartedRef.current = false;
        setCreateError(
          error instanceof Error ? error.message : "Unable to create worldbuilding source.",
        );
      });
  }, [documentId]);

  if (!documentId) {
    return (
      <AppChrome activeRoute="build">
        <main className="app-status" data-testid="build-new-source-opening">
          {createError ? (
            <>
              <h1>{BUILD_SURFACE_LABEL}</h1>
              <p role="alert" data-testid="build-create-error">
                {createError}
              </p>
            </>
          ) : (
            <p>Opening worldbuilding canvas…</p>
          )}
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="build" editorTools={editorTools} editToolboxLayout="dock">
      <MarkdownCanvasSessionProvider
        key={documentId}
        documentId={documentId}
        surface={BUILD_MARKDOWN_CANVAS.surface}
        kind={BUILD_MARKDOWN_CANVAS.kind}
        saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        emptyMarkdownFallback={emptyMarkdownFallback}
      >
        <BuildIngestToolbar documentId={documentId} />
        <BuildSurfaceShell onEditorToolsChange={setEditorTools} />
      </MarkdownCanvasSessionProvider>
    </AppChrome>
  );
}
