import { BuildPdfPreview } from "./BuildPdfPreview";
import { SurfaceNavbarIconButton } from "../surfaceInteraction/contextHost/SurfaceNavbarIconButton";
import { useEffect, useRef, useState } from "react";
import { BUILD_STUDIO_ACTION, type BuildStudioAction } from "./buildStudioActions";

import {
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";

function isMarkdownImportText(value: string): boolean {
  return Boolean(value.trim())
    && !/^\uFEFF*%PDF-/.test(value)
    && !/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/.test(value);
}

/** Explicit Build destination — never invent campaign/world identity from titles. */
export type BuildSourceDestinationIntent =
  | { kind: "campaign"; campaignId: string }
  | { kind: "world"; worldId: string }
  | { kind: "new_world"; name: string };

export type BuildSourceDestinationOption =
  | {
      kind: "campaign";
      campaignId: string;
      worldId: string;
      label: string;
      value: string;
    }
  | {
      kind: "world";
      worldId: string;
      label: string;
      value: string;
    };

export interface BuildDocumentCreateSubmitPayload {
  starter?: boolean;
  title: string;
  destination: BuildSourceDestinationIntent;
}

export interface BuildDocumentImportSubmitPayload extends BuildDocumentCreateSubmitPayload {
  markdown: string;
}

export interface BuildDocumentCreateControlProps {
  destinationOptions: readonly BuildSourceDestinationOption[];
  suggestedDestinationValue: string | null;
  creating?: boolean;
  createError?: string | null;
  activationError?: string | null;
  importError?: string | null;
  pendingImportDocumentId?: string | null;
  onSubmit: (payload: BuildDocumentCreateSubmitPayload) => void;
  onImportSubmit: (payload: BuildDocumentImportSubmitPayload) => void;
  onRetryOpen?: () => void;
  onRetryImport?: (payload: { markdown: string }) => void;
  disabled?: boolean;
}

const NEW_WORLD_VALUE = "__new_world__";

type DestinationSelectionProvenance = "explicit" | "derived";

type DestinationSelection = {
  value: string;
  provenance: DestinationSelectionProvenance;
};

function normalizeDestinationValue(
  value: string | null | undefined,
  options: readonly BuildSourceDestinationOption[],
): string {
  const trimmed = value?.trim() ?? "";
  if (trimmed && options.some((option) => option.value === trimmed)) {
    return trimmed;
  }
  return "";
}

function isDestinationStillValid(
  value: string,
  options: readonly BuildSourceDestinationOption[],
): boolean {
  if (value === NEW_WORLD_VALUE) return true;
  return Boolean(value) && options.some((option) => option.value === value);
}

function parseExistingDestination(
  value: string,
  options: readonly BuildSourceDestinationOption[],
): BuildSourceDestinationIntent | null {
  const option = options.find((row) => row.value === value);
  if (!option) return null;
  if (option.kind === "campaign") {
    return { kind: "campaign", campaignId: option.campaignId };
  }
  return { kind: "world", worldId: option.worldId };
}

export function BuildDocumentCreateControl({
  destinationOptions,
  suggestedDestinationValue,
  creating = false,
  createError = null,
  activationError = null,
  importError = null,
  pendingImportDocumentId = null,
  onSubmit,
  onImportSubmit,
  onRetryOpen,
  onRetryImport,
  disabled = false,
}: BuildDocumentCreateControlProps) {
  const [droppedPdf, setDroppedPdf] = useState<{file: File; sequence: number}>();
  useEffect(() => {
    function openPdf(event: Event) {
      if (disabled || creating) return;
      const file = (event as CustomEvent<File>).detail;
      setDroppedPdf(previous => ({file, sequence: (previous?.sequence ?? 0) + 1}));
      setDestinationSelection({value: normalizeDestinationValue(suggestedDestinationValue, destinationOptions), provenance: "derived"});
      setImportOpen(true);
    }
    window.addEventListener("dmb:build-pdf-drop", openPdf);
    return () => window.removeEventListener("dmb:build-pdf-drop", openPdf);
  }, [creating, disabled, destinationOptions, suggestedDestinationValue]);
  const [createOpen, setCreateOpen] = useState(false);
  const [starter, setStarter] = useState(true);
  useEffect(() => {
    const open = (event: Event) => {
      if (disabled || creating) return;
      const action = (event as CustomEvent<BuildStudioAction>).detail;
      if (action === "new") setCreateOpen(true);
      if (action === "import") setImportOpen(true);
    };
    window.addEventListener(BUILD_STUDIO_ACTION, open);
    return () => window.removeEventListener(BUILD_STUDIO_ACTION, open);
  }, [disabled, creating]);
  const [importOpen, setImportOpen] = useState(false);
  const [openPdfPreviewKey, setOpenPdfPreviewKey] = useState<string>();
  function closeImport() {
    setImportOpen(false);
    setDroppedPdf(undefined);
    setOpenPdfPreviewKey(undefined);
  }
  const [destinationSelection, setDestinationSelection] = useState<DestinationSelection>(() => ({
    value: normalizeDestinationValue(suggestedDestinationValue, destinationOptions),
    provenance: "derived",
  }));
  const [worldName, setWorldName] = useState("");
  const [title, setTitle] = useState("");
  const [importMarkdown, setImportMarkdown] = useState("");
  const [importFileError, setImportFileError] = useState<string | null>(null);
  const [readingImportFile, setReadingImportFile] = useState(false);
  const importFileRead = useRef(0);

  const destinationValue = destinationSelection.value;

  useEffect(() => {
    // Preserve explicit GM intent (including New world…) across option refreshes.
    // Derived/default selections must follow a new authoritative suggestion —
    // e.g. C1→C2 navigation, or campaign→managed-world collision after worlds load.
    setDestinationSelection((current) => {
      if (current.provenance === "explicit" && isDestinationStillValid(current.value, destinationOptions)) {
        return current;
      }
      return {
        value: normalizeDestinationValue(suggestedDestinationValue, destinationOptions),
        provenance: "derived",
      };
    });
  }, [destinationOptions, suggestedDestinationValue]);

  useEffect(() => {
    if (createError || activationError) {
      setCreateOpen(true);
    }
  }, [createError, activationError]);

  useEffect(() => {
    if (importError) {
      setImportOpen(true);
    }
  }, [importError]);

  const wasCreatingRef = useRef(false);
  useEffect(() => {
    const finishedCreating = wasCreatingRef.current && !creating;
    wasCreatingRef.current = creating;
    if (!finishedCreating || createError || activationError || importError) return;
    setTitle("");
    setImportMarkdown("");
    setWorldName("");
    setDestinationSelection({
      value: normalizeDestinationValue(suggestedDestinationValue, destinationOptions),
      provenance: "derived",
    });
    setCreateOpen(false);
    closeImport();
  }, [
    activationError,
    createError,
    creating,
    destinationOptions,
    importError,
    suggestedDestinationValue,
  ]);

  const isNewWorld = destinationValue === NEW_WORLD_VALUE;
  const resolvedDestination: BuildSourceDestinationIntent | null = isNewWorld
    ? worldName.trim()
      ? { kind: "new_world", name: worldName.trim() }
      : null
    : parseExistingDestination(destinationValue, destinationOptions);

  const handleCreateSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating || !resolvedDestination) return;
    const trimmed = title.trim();
    if (!trimmed) return;
    onSubmit({ title: trimmed, destination: resolvedDestination, starter });
  };

  const handleImportFile = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.currentTarget.files?.[0];
    event.currentTarget.value = "";
    if (!file) return;
    const read = ++importFileRead.current;
    setReadingImportFile(true);
    setImportFileError(null);
    try {
      if (!/\.(?:md|markdown)$/i.test(file.name)) {
        throw new Error("Choose a .md or .markdown file.");
      }
      let markdown: string;
      try {
        markdown = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true })
          .decode(await file.arrayBuffer());
      } catch {
        throw new Error("The file could not be read as UTF-8 text.");
      }
      if (!isMarkdownImportText(markdown)) {
        throw new Error("Choose a non-empty Markdown text file.");
      }
      if (read === importFileRead.current) {
        setImportMarkdown(markdown);
      }
    } catch (error) {
      if (read === importFileRead.current) {
        setImportFileError(error instanceof Error ? error.message : "Could not read the file.");
      }
    } finally {
      if (read === importFileRead.current) setReadingImportFile(false);
    }
  };

  const suggestedImportTitle = importMarkdown
    .split(/\r?\n/)
    .find(line => line.trim())
    ?.trim().replace(/^#{1,6}\s+/, "").slice(0, 120) ?? "";
  const importTitle = title.trim() || suggestedImportTitle;

  const pdfWorldId = resolvedDestination?.kind === "world" ? resolvedDestination.worldId : undefined;
  const pdfPreviewKey = JSON.stringify([pdfWorldId, droppedPdf?.sequence]);

  const handleImportSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating || !resolvedDestination) return;
    const trimmedTitle = importTitle;
    if (readingImportFile || importFileError || !trimmedTitle) return;
    if (!isMarkdownImportText(importMarkdown)) {
      setImportFileError("Enter non-empty Markdown text.");
      return;
    }
    onImportSubmit({
      title: trimmedTitle,
      destination: resolvedDestination,
      markdown: importMarkdown,
    });
  };

  const canCreateSubmit =
    !disabled && !creating && Boolean(title.trim()) && resolvedDestination != null;
  const canImportSubmit =
    !disabled &&
    !creating &&
    Boolean(importTitle) &&
    !readingImportFile &&
    !importFileError &&
    importMarkdown.trim().length > 0 &&
    resolvedDestination != null;

  const worldFields = (
    <>
      <label className="build-document-create__field build-document-create__field--destination">
        <span>World</span>
        <select
          data-testid="build-document-create-destination"
          value={destinationValue}
          onChange={(event) => {
            setDestinationSelection({
              value: event.target.value,
              provenance: "explicit",
            });
          }}
          disabled={disabled || creating}
          required
        >
          {!destinationValue ? (
            <option value="" disabled>
              Choose destination
            </option>
          ) : null}
          {destinationOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
          <option value={NEW_WORLD_VALUE}>New world…</option>
        </select>
      </label>
      {isNewWorld ? (
        <label className="build-document-create__field build-document-create__field--world-name">
          <span>World name</span>
          <input
            type="text"
            data-testid="build-document-create-world-name"
            value={worldName}
            onChange={(event) => setWorldName(event.target.value)}
            placeholder="The Glass Orchard"
            disabled={disabled || creating}
          />
        </label>
      ) : null}
    </>
  );

  const titleField = (suggestion?: string) => (
      <label className="build-document-create__field build-document-create__field--title">
        <span>Title</span>
        <input
          type="text"
          data-testid="build-document-create-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder={suggestion || "Ironveil Property"}
          disabled={disabled || creating}
        />
      </label>
  );

  const createForm = (
    <form
      className="build-document-create__form"
      data-testid="build-document-create-form"
      onSubmit={handleCreateSubmit}
    >
      <div className="build-document-create__controls">
        {worldFields}
        {titleField()}
        <div className="build-document-create__actions">
          <button
            type="button"
            data-testid="build-document-create-cancel"
            onClick={() => setCreateOpen(false)}
            disabled={disabled || creating}
          >
            Cancel
          </button>
          <label className="build-starter-choice"><input type="checkbox" checked={starter} onChange={event => setStarter(event.target.checked)} /> Start with worldbuilding prompts</label>
          <button type="submit" data-testid="build-document-create-submit" disabled={!canCreateSubmit}>
            {creating ? "Creating…" : "Create source"}
          </button>
          {activationError && onRetryOpen ? (
            <button
              type="button"
              data-testid="build-document-create-retry-open"
              onClick={onRetryOpen}
              disabled={disabled || creating}
            >
              Retry Open
            </button>
          ) : null}
        </div>
      </div>
      <div className="build-document-create__status" aria-live="polite">
        {createError ? (
          <p className="build-document-create__error" role="alert" data-testid="build-document-create-error">
            {createError}
          </p>
        ) : null}
        {activationError ? (
          <p
            className="build-document-create__error"
            role="alert"
            data-testid="build-document-create-activation-error"
          >
            Created but could not open: {activationError}
          </p>
        ) : null}
      </div>
    </form>
  );

  const importForm = (
    <form
      className="build-document-create__form"
      data-testid="build-document-import-form"
      onSubmit={handleImportSubmit}
    >
      <div className="build-document-create__controls">
        {titleField(suggestedImportTitle)}
        <label className="build-document-create__field">
          <span>Choose Markdown file</span>
          <input type="file" accept=".md,.markdown" onChange={handleImportFile}
            disabled={disabled || creating} />
        </label>
        {importFileError && <p role="alert">{importFileError}</p>}
        <label className="build-document-create__field build-document-create__field--markdown">
          <span>Markdown</span>
          <textarea
            data-testid="build-document-import-markdown"
            value={importMarkdown}
            onChange={(event) => {
              ++importFileRead.current;
              setReadingImportFile(false);
              setImportFileError(null);
              setImportMarkdown(event.target.value);
            }}
            onDragOver={event => {
              if (event.dataTransfer.types.includes("Files")) event.preventDefault();
            }}
            onDrop={event => {
              const file = event.dataTransfer.files[0];
              if (!file) return;
              event.preventDefault();
              if (!/\.pdf$/i.test(file.name)) {
                setImportFileError("Drop a PDF or use the Markdown file picker.");
                return;
              }
              setDroppedPdf(previous => ({ file, sequence: (previous?.sequence ?? 0) + 1 }));
            }}
            placeholder="Paste text or drop a PDF here"
            rows={8}
            disabled={disabled || creating}
          />
        </label>
        <div className="build-document-create__actions">
          <button
            type="button"
            data-testid="build-document-import-cancel"
            onClick={() => {
              ++importFileRead.current;
              setReadingImportFile(false);
              setImportFileError(null);
              closeImport();
            }}
            disabled={disabled || creating}
          >
            Cancel
          </button>
          <button type="submit" data-testid="build-document-import-submit" disabled={!canImportSubmit}>
            {creating ? "Importing…" : "Import source"}
          </button>
          {importError && pendingImportDocumentId && onRetryImport ? (
            <button
              type="button"
              data-testid="build-document-import-retry"
              onClick={() => {
                if (!isMarkdownImportText(importMarkdown)) {
                  setImportFileError("Enter non-empty Markdown text.");
                  return;
                }
                onRetryImport({ markdown: importMarkdown });
              }}
              disabled={disabled || creating || readingImportFile || Boolean(importFileError) || importMarkdown.trim().length === 0}
            >
              Retry import
            </button>
          ) : null}
          {activationError && onRetryOpen ? (
            <button
              type="button"
              data-testid="build-document-import-retry-open"
              onClick={onRetryOpen}
              disabled={disabled || creating}
            >
              Retry Open
            </button>
          ) : null}
        </div>
      </div>
      <div className="build-document-create__status" aria-live="polite">
        {importError ? (
          <p className="build-document-create__error" role="alert" data-testid="build-document-import-error">
            {importError}
          </p>
        ) : null}
        {activationError ? (
          <p
            className="build-document-create__error"
            role="alert"
            data-testid="build-document-import-activation-error"
          >
            {activationError}
          </p>
        ) : null}
      </div>
    </form>
  );

  return (
    <div className="build-document-create build-document-create--context" data-testid="build-document-create">
      <SurfaceContextPopover
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="New page"
        align="end"
        placement="below"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceNavbarIconButton icon="new" label="New page"
            data-testid="build-document-create-open"
            onClick={() => setCreateOpen(true)}
            disabled={disabled || creating}
          />
        }
      >
        {createForm}
      </SurfaceContextPopover>
      <SurfaceContextPopover
        open={importOpen}
        onOpenChange={open => { if (open) setImportOpen(true); else closeImport(); }}
        title="Import source"
        align="end"
        placement="below"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceNavbarIconButton icon="import" label="Import source"
            data-testid="build-document-import-open"
            onClick={() => setImportOpen(true)}
            disabled={disabled || creating}
          />
        }
      >
        {worldFields}
        <BuildPdfPreview
          key={pdfPreviewKey}
          worldId={pdfWorldId}
          initialFile={droppedPdf?.file}
          onPdfOpen={() => setOpenPdfPreviewKey(pdfPreviewKey)}
        />
        {!droppedPdf && openPdfPreviewKey !== pdfPreviewKey && importForm}
      </SurfaceContextPopover>
    </div>
  );
}

export { NEW_WORLD_VALUE as BUILD_NEW_WORLD_DESTINATION_VALUE };
