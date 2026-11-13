import { useEffect, useState } from "react";

import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { announceSelectedWorldLocationChange } from "../selectedWorld/SelectedWorldContext";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceContext } from "./BuildSurfaceContext";
import { BuildEmptyLanding, BuildSurfaceShell } from "./BuildSurfaceShell";
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";
import { useBuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";
import "./buildSurface.css";

export function BuildSurfacePage() {
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);
  const controller = useBuildWorkspaceDocumentController();
  const [extractionTarget, setExtractionTarget] = useState<HTMLDivElement | null>(null);
  const [reviewTarget, setReviewTarget] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!controller.activeRecord || typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("documentId") === controller.activeRecord.document_id) {
      announceSelectedWorldLocationChange();
    }
  }, [controller.activeRecord]);

  // A review opened inline adds a reload URL without replacing the live import workspace.
  const [entrySearch, setEntrySearch] = useState(() => window.location.search);
  useEffect(() => {
    const syncHistory = () => setEntrySearch(window.location.search);
    window.addEventListener("popstate", syncHistory);
    return () => window.removeEventListener("popstate", syncHistory);
  }, []);
  const params = new URLSearchParams(entrySearch);
  const reviewWorldId = params.get("world");
  const pdfReviewId = new URLSearchParams(window.location.search).get("world") === reviewWorldId
    ? params.get("pdfReview")
    : null;

  return (
    <AppChrome activeRoute="build" editorTools={editorTools} editToolboxLayout="dock" workspaceLayout="bounded">
      <div style={{display: "contents"}} onDragOver={event => {
        if (!pdfReviewId && event.dataTransfer.types.includes("Files")) event.preventDefault();
      }} onDrop={event => {
        if (pdfReviewId || event.defaultPrevented) return;
        const files = Array.from(event.dataTransfer.files);
        const file = files.length === 1 ? files[0] : undefined;
        if (!file || !(file.type === "application/pdf" || (!file.type && /\.pdf$/i.test(file.name)))) return;
        event.preventDefault();
        window.dispatchEvent(new CustomEvent("dmb:build-pdf-drop", {detail: file}));
      }}>
      {pdfReviewId && reviewWorldId ? (
        <BuildPdfStatblockReview key={`${reviewWorldId}:${pdfReviewId}`} worldId={reviewWorldId} reviewId={pdfReviewId} />
      ) : controller.activeDocumentId ? (
        <MarkdownCanvasSessionProvider
          key={controller.activeDocumentId}
          documentId={controller.activeDocumentId}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildSurfaceContext {...controller} extractionTargetRef={setExtractionTarget} />
          <BuildReferenceCapability documentId={controller.activeDocumentId}>
            <BuildIngestToolbar documentId={controller.activeDocumentId} target={extractionTarget} reviewTarget={reviewTarget} />
            <BuildSurfaceShell onEditorTools={setEditorTools} onReviewTarget={setReviewTarget} />
          </BuildReferenceCapability>
        </MarkdownCanvasSessionProvider>
      ) : (
        <>
          <BuildSurfaceContext {...controller} />
          <BuildEmptyLanding loadStatus={controller.loadStatus} />
          <BuildReferenceCapability documentId={null} />
        </>
      )}
      </div>
    </AppChrome>
  );
}
