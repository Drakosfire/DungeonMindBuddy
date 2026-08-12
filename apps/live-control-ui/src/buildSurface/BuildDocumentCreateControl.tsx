import { useEffect, useRef, useState } from "react";

import {
  SurfaceContextAction,
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";

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
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [destinationValue, setDestinationValue] = useState(() =>
    normalizeDestinationValue(suggestedDestinationValue, destinationOptions),
  );
  const [worldName, setWorldName] = useState("");
  const [title, setTitle] = useState("");
  const [importMarkdown, setImportMarkdown] = useState("");

  useEffect(() => {
    // Preserve an intentional New world… selection (and any still-valid explicit
    // destination) across managed-world list refreshes. Do not snap back to the
    // suggested campaign after create W succeeds but source create fails.
    setDestinationValue((current) => {
      if (current === NEW_WORLD_VALUE) return NEW_WORLD_VALUE;
      if (current && destinationOptions.some((option) => option.value === current)) {
        return current;
      }
      return normalizeDestinationValue(suggestedDestinationValue, destinationOptions);
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
    setCreateOpen(false);
    setImportOpen(false);
  }, [activationError, createError, creating, importError]);

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
    onSubmit({ title: trimmed, destination: resolvedDestination });
  };

  const handleImportSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating || !resolvedDestination) return;
    const trimmedTitle = title.trim();
    if (!trimmedTitle || importMarkdown.trim().length === 0) return;
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
    Boolean(title.trim()) &&
    importMarkdown.trim().length > 0 &&
    resolvedDestination != null;

  const sharedFields = (
    <>
      <label className="build-document-create__field build-document-create__field--destination">
        <span>Destination</span>
        <select
          data-testid="build-document-create-destination"
          value={destinationValue}
          onChange={(event) => setDestinationValue(event.target.value)}
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
      <label className="build-document-create__field build-document-create__field--title">
        <span>Title</span>
        <input
          type="text"
          data-testid="build-document-create-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          placeholder="Ironveil Property"
          disabled={disabled || creating}
        />
      </label>
    </>
  );

  const createForm = (
    <form
      className="build-document-create__form"
      data-testid="build-document-create-form"
      onSubmit={handleCreateSubmit}
    >
      <div className="build-document-create__controls">
        {sharedFields}
        <div className="build-document-create__actions">
          <button
            type="button"
            data-testid="build-document-create-cancel"
            onClick={() => setCreateOpen(false)}
            disabled={disabled || creating}
          >
            Cancel
          </button>
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
        {sharedFields}
        <label className="build-document-create__field build-document-create__field--markdown">
          <span>Markdown</span>
          <textarea
            data-testid="build-document-import-markdown"
            value={importMarkdown}
            onChange={(event) => setImportMarkdown(event.target.value)}
            placeholder="# Source title&#10;&#10;Paste external Markdown here."
            rows={8}
            disabled={disabled || creating}
          />
        </label>
        <div className="build-document-create__actions">
          <button
            type="button"
            data-testid="build-document-import-cancel"
            onClick={() => setImportOpen(false)}
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
              onClick={() => onRetryImport({ markdown: importMarkdown })}
              disabled={disabled || creating || importMarkdown.trim().length === 0}
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
        title="New source"
        align="end"
        placement="beside"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceContextAction
            data-testid="build-document-create-open"
            onClick={() => setCreateOpen(true)}
            disabled={disabled || creating}
          >
            + New source
          </SurfaceContextAction>
        }
      >
        {createForm}
      </SurfaceContextPopover>
      <SurfaceContextPopover
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Import source"
        align="end"
        placement="beside"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceContextAction
            data-testid="build-document-import-open"
            onClick={() => setImportOpen(true)}
            disabled={disabled || creating}
          >
            Import source
          </SurfaceContextAction>
        }
      >
        {importForm}
      </SurfaceContextPopover>
    </div>
  );
}

export { NEW_WORLD_VALUE as BUILD_NEW_WORLD_DESTINATION_VALUE };
