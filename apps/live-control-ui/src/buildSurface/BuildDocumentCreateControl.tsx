import { useEffect, useRef, useState } from "react";

import {
  SurfaceContextAction,
  SurfaceContextPopover,
} from "../surfaceInteraction/contextHost";
import {
  BUILD_KNOWN_CAMPAIGN_IDS,
  isBuildKnownCampaignId,
} from "./buildBareEntryCampaign";

export interface BuildDocumentCreateSubmitPayload {
  title: string;
  campaignId: string;
}

export interface BuildDocumentCreateControlProps {
  suggestedCampaignId: string | null;
  creating?: boolean;
  createError?: string | null;
  activationError?: string | null;
  onSubmit: (payload: BuildDocumentCreateSubmitPayload) => void;
  onRetryOpen?: () => void;
  disabled?: boolean;
}

function normalizeCreateCampaignId(value: string | null | undefined): string {
  return isBuildKnownCampaignId(value) ? value : "";
}

export function BuildDocumentCreateControl({
  suggestedCampaignId,
  creating = false,
  createError = null,
  activationError = null,
  onSubmit,
  onRetryOpen,
  disabled = false,
}: BuildDocumentCreateControlProps) {
  const [open, setOpen] = useState(false);
  const [campaignId, setCampaignId] = useState(() =>
    normalizeCreateCampaignId(suggestedCampaignId),
  );
  const [title, setTitle] = useState("");

  useEffect(() => {
    const next = normalizeCreateCampaignId(suggestedCampaignId);
    if (next) {
      setCampaignId(next);
      return;
    }
    // Suggestion cleared or foreign: keep only a still-visible selection.
    setCampaignId((current) => normalizeCreateCampaignId(current));
  }, [suggestedCampaignId]);

  useEffect(() => {
    if (createError || activationError) {
      setOpen(true);
    }
  }, [createError, activationError]);

  const wasCreatingRef = useRef(false);
  useEffect(() => {
    const finishedCreating = wasCreatingRef.current && !creating;
    wasCreatingRef.current = creating;
    if (!finishedCreating || createError || activationError) return;
    setTitle("");
    setOpen(false);
  }, [activationError, createError, creating]);

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (disabled || creating) return;
    const trimmed = title.trim();
    const campaign = campaignId.trim();
    if (!trimmed || !isBuildKnownCampaignId(campaign)) return;
    onSubmit({ title: trimmed, campaignId: campaign });
  };

  const canSubmit =
    !disabled &&
    !creating &&
    Boolean(title.trim()) &&
    isBuildKnownCampaignId(campaignId);
  const createForm = (
    <form
      className="build-document-create__form"
      data-testid="build-document-create-form"
      onSubmit={handleSubmit}
    >
      <div className="build-document-create__controls">
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
            {BUILD_KNOWN_CAMPAIGN_IDS.map((id) => (
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
        <div className="build-document-create__actions">
          <button
            type="button"
            data-testid="build-document-create-cancel"
            onClick={() => setOpen(false)}
            disabled={disabled || creating}
          >
            Cancel
          </button>
          <button type="submit" data-testid="build-document-create-submit" disabled={!canSubmit}>
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

  return (
    <div className="build-document-create build-document-create--context" data-testid="build-document-create">
      <SurfaceContextPopover
        open={open}
        onOpenChange={setOpen}
        title="New source"
        align="end"
        placement="beside"
        className="surface-context-popover--wide"
        trigger={
          <SurfaceContextAction
            data-testid="build-document-create-open"
            onClick={() => setOpen(true)}
            disabled={disabled || creating}
          >
            + New source
          </SurfaceContextAction>
        }
      >
        {createForm}
      </SurfaceContextPopover>
    </div>
  );
}
