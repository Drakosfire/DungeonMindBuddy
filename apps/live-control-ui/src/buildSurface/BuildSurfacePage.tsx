import { useHostedAuthStatus } from "../auth/HostedAuthGate";
import { BuildNativeDocument } from "./BuildNativeDocument";
import { listRetainedPdfDocuments, readRetainedPdfDocuments, type RetainedPdf } from "../api/retainedPdfRegions";
import { BuildGraphObjectContext, parseBuildGraphPointerFromLocation } from "./BuildGraphObjectContext";
import { SavedStatblockFullView } from "../statblocks/StatblockPage";
import { readSavedStatblockTarget } from "../statblocks/savedStatblockLocation";
import { useEffect, useMemo, useState } from "react";

import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { announceSelectedWorldLocationChange, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { BUILD_MARKDOWN_CANVAS } from "./buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "./buildDocumentCommands";
import { BuildPdfPreview } from "./BuildPdfPreview";
import { BuildPdfStatblockReview } from "./BuildPdfStatblockReview";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceContext } from "./BuildSurfaceContext";
import { BuildEmptyLanding, BuildSurfaceShell } from "./BuildSurfaceShell";
import { BuildReferenceCapability } from "./reference/BuildReferenceCapability";
import { useBuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";
import "./buildSurface.css";

export function BuildSurfacePage() {
  const hosted = useHostedAuthStatus().status === "authenticated";
  const selectedWorld = useSelectedWorld();
  const worldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [droppedPdf, setDroppedPdf] = useState<{ file: File; worldId: string; version: number }>();
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

  const [entrySearch, setEntrySearch] = useState(() => window.location.search);
  useEffect(() => {
    const syncHistory = () => {
      setDroppedPdf(undefined);
      setEntrySearch(window.location.search);
    };
    window.addEventListener("popstate", syncHistory);
    return () => window.removeEventListener("popstate", syncHistory);
  }, []);
  const params = new URLSearchParams(entrySearch);
  const nativeDocumentId = params.get("world") === worldId ? params.get("nativeDocument") : null;
  const pdfId = params.get("world") === worldId ? params.get("pdf") : null;
  const [authorityPdf, setAuthorityPdf] = useState<{ worldId: string; id: string; entry?: RetainedPdf }>();
  const localPdf = useMemo(() => !hosted && worldId && pdfId
    ? readRetainedPdfDocuments(worldId).find(entry => entry.locator.source_revision_id === pdfId)
    : undefined, [hosted, worldId, pdfId]);
  useEffect(() => {
    if (!worldId || !pdfId || localPdf) return;
    const request = new AbortController();
    listRetainedPdfDocuments(worldId, request.signal).then(
      documents => {
        if (!request.signal.aborted) setAuthorityPdf({ worldId, id: pdfId,
          entry: documents.find(entry => entry.locator.source_revision_id === pdfId) });
      },
      () => { if (!request.signal.aborted) setAuthorityPdf({ worldId, id: pdfId }); },
    );
    return () => request.abort();
  }, [worldId, pdfId, localPdf]);
  const resolvedPdf = authorityPdf?.worldId === worldId && authorityPdf?.id === pdfId ? authorityPdf : undefined;
  const retainedPdf = localPdf ?? resolvedPdf?.entry;
  const graphPointer = useMemo(() => parseBuildGraphPointerFromLocation(entrySearch), [entrySearch]);
  const nativeObject = graphPointer?.nativePin;
  const statblock = readSavedStatblockTarget("/build" + entrySearch);
  const reviewWorldId = params.get("world");
  const [primaryActions, setPrimaryActions] = useState<HTMLDivElement | null>(null);
  const [reviewToolbar, setReviewToolbar] = useState<HTMLDivElement | null>(null);
  const pdfReviewId = (!hosted || reviewWorldId === worldId)
    && new URLSearchParams(window.location.search).get("world") === reviewWorldId
    ? params.get("pdfReview")
    : null;

  return (
    <AppChrome primaryActionsRef={setPrimaryActions} contextToolbarRef={pdfReviewId ? setReviewToolbar : undefined} activeRoute="build" editorTools={editorTools} editToolboxLayout="dock" workspaceLayout="bounded">
      <div style={{display: "contents"}} onDragOver={event => {
        if (!pdfReviewId && !statblock && event.dataTransfer.types.includes("Files")) event.preventDefault();
      }} onDrop={event => {
        if (pdfReviewId || statblock || event.defaultPrevented) return;
        const files = Array.from(event.dataTransfer.files);
        const file = files.length === 1 ? files[0] : undefined;
        if (!file || !(file.type === "application/pdf" || (!file.type && /\.pdf$/i.test(file.name)))) return;
        event.preventDefault();
        if (worldId) {
          setDroppedPdf(previous => ({ file, worldId, version: (previous?.version ?? 0) + 1 }));
        } else {
          window.dispatchEvent(new CustomEvent("dmb:build-pdf-drop", {detail: file}));
        }
      }}>
      {pdfReviewId && reviewWorldId ? (
        <BuildPdfStatblockReview key={`${reviewWorldId}:${pdfReviewId}`} worldId={reviewWorldId} reviewId={pdfReviewId} toolbarHost={reviewToolbar} />
      ) : statblock && statblock.worldId === worldId ? (
        <>
          <BuildSurfaceContext {...controller} primaryActionsHost={primaryActions} />
          <SavedStatblockFullView target={statblock} toolbarHost={hosted ? null : primaryActions} />
        </>
      ) : graphPointer && nativeObject && nativeObject.managed_world_id === worldId ? (
        <BuildGraphObjectContext key={entrySearch} pointer={graphPointer} />
      ) : nativeDocumentId && worldId ? (
        <>
          <BuildSurfaceContext {...controller} primaryActionsHost={primaryActions} />
          <BuildNativeDocument key={`${worldId}:${nativeDocumentId}`} worldId={worldId} revisionId={nativeDocumentId} />
        </>
      ) : params.has("pdf") && worldId ? (
        <>
          <BuildSurfaceContext {...controller} primaryActionsHost={primaryActions} />
          <section className="build-pdf-workspace" aria-label="PDF workspace">
            {retainedPdf ? <BuildPdfPreview key={entrySearch} worldId={worldId} initialRetained={retainedPdf} persistShortcuts={!hosted} />
              : <p role="status">{(!pdfId || resolvedPdf) ? "This retained PDF could not be found." : "Opening PDF…"}</p>}
          </section>
        </>
      ) : droppedPdf && droppedPdf.worldId === worldId ? (
        <section className="build-pdf-workspace" aria-label="PDF workspace">
          <BuildPdfPreview key={droppedPdf.version} worldId={droppedPdf.worldId} initialFile={droppedPdf.file} persistShortcuts={!hosted}
            toolbarControls={<button type="button" onClick={() => setDroppedPdf(undefined)}>Close PDF</button>} />
        </section>
      ) : controller.activeDocumentId ? (
        <MarkdownCanvasSessionProvider
          key={controller.activeDocumentId}
          documentId={controller.activeDocumentId}
          initialSnapshot={controller.initialEditorSnapshot ?? undefined}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildSurfaceContext {...controller} primaryActionsHost={primaryActions} extractionTargetRef={setExtractionTarget} />
          <BuildReferenceCapability documentId={controller.activeDocumentId}>
            <BuildIngestToolbar documentId={controller.activeDocumentId} target={extractionTarget} reviewTarget={reviewTarget} />
            <BuildSurfaceShell onEditorTools={setEditorTools} onReviewTarget={setReviewTarget} />
          </BuildReferenceCapability>
        </MarkdownCanvasSessionProvider>
      ) : (
        <>
          <BuildSurfaceContext {...controller} primaryActionsHost={primaryActions} />
          <BuildEmptyLanding loadStatus={controller.loadStatus} />
          <BuildReferenceCapability documentId={null} />
        </>
      )}
      </div>
    </AppChrome>
  );
}
