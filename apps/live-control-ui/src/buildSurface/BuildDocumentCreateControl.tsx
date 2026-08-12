import { useEffect, useRef, useState } from "react";

import {
  SurfaceContextAction,
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";

export interface BuildDocumentCreateSubmitPayload {
  title: string;
  campaignId: string;
}

export interface BuildDocumentImportSubmitPayload extends BuildDocumentCreateSubmitPayload {
  markdown: string;
}

export interface BuildDocumentCreateControlProps {
  /** Campaigns the operator may create into — must match controller validation. */
  creatableCampaignIds: readonly string[];
  suggestedCampaignId: string | null;
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

function normalizeCreateCampaignId(
  value: string | null | undefined,
  creatable: ReadonlySet<string>,
): string {
  const trimmed = value?.trim() ?? "";
  return trimmed && creatable.has(trimmed) ? trimmed : "";
}

export function BuildDocumentCreateControl({
  creatableCampaignIds,
  suggestedCampaignId,
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
  const creatable = new Set(
    creatableCampaignIds.map((id) => id.trim()).filter(Boolean),
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [campaignId, setCampaignId] = useState(() =>
    normalizeCreateCampaignId(suggestedCampaignId, creatable),
  );
  const [title, setTitle] = useState("");
  const [importMarkdown, setImportMarkdown] = useState("");

  useEffect(() => {
    const next = normalizeCreateCampaignId(suggestedCampaignId, creatable);
    if (next) {
      setCampaignId(next);
      return;
    }
    setCampaignId((current) => normalizeCreateCampaignId(current, creatable));
  }, [creatableCampaignIds, suggestedCampaignId]);

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
    setCreateOpen(false);
    setImportOpen(false);
  }, [activationError, createError, creating, importError]);

  const handleCreateSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating) return;
    const trimmed = title.trim();
    const campaign = campaignId.trim();
    if (!trimmed || !creatable.has(campaign)) return;
    onSubmit({ title: trimmed, campaignId: campaign });
  };

  const handleImportSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating) return;
    const trimmedTitle = title.trim();
    const campaign = campaignId.trim();
    if (!trimmedTitle || !creatable.has(campaign) || importMarkdown.length === 0) return;
    onImportSubmit({ title: trimmedTitle, campaignId: campaign, markdown: importMarkdown });
  };

  const canCreateSubmit =
    !disabled && !creating && Boolean(title.trim()) && creatable.has(campaignId.trim());
  const canImportSubmit =
    !disabled &&
    !creating &&
    Boolean(title.trim()) &&
    importMarkdown.length > 0 &&
    creatable.has(campaignId.trim());

  const sharedFields = (
    <>
      <label className="build-document-create__field build-document-create__field--campaign">
        <span>Campaign</span>
        <select
          data-testid="build-document-create-campaign"
          value={campaignId}
          onChange={(event) => setCampaignId(event.target.value)}
          disabled={disabled || creating}
          required
        >
          {!campaignId ? (
            <option value="" disabled>
              Choose campaign
            </option>
          ) : null}
          {creatableCampaignIds.map((id) => (
            <option key={id} value={id}>
              {id}
            </option>
          ))}
        </select>
      </label>
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
              disabled={disabled || creating || importMarkdown.length === 0}
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
