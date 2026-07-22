import { useCallback, useEffect, useState, type FormEvent } from "react";

import { createWorkspaceDocument } from "../api/liveApi";
import type {
  WorldbuildingAuthorityState,
  WorldbuildingVisibilityState,
} from "../api/types";
import { AppChrome } from "../chrome/AppChrome";
import { useWorkspaceDocumentUrlSelection } from "../workspaceDocument/useWorkspaceDocumentUrlSelection";
import { BuildIngestToolbar } from "./BuildIngestToolbar";
import { BuildSurfaceShell } from "./BuildSurfaceShell";
import { BUILD_NEW_SOURCE_HEADING, BUILD_SURFACE_LABEL, BUILD_SURFACE_ROUTE } from "./buildSurfaceConfig";

function navigateToDocument(documentId: string): void {
  const url = new URL(window.location.href);
  url.pathname = BUILD_SURFACE_ROUTE;
  url.searchParams.set("documentId", documentId);
  window.history.pushState({}, "", url.toString());
  window.dispatchEvent(new PopStateEvent("popstate"));
}

interface NewSourceFormState {
  title: string;
  campaignId: string;
  documentClass: string;
  authorityState: WorldbuildingAuthorityState;
  visibilityState: WorldbuildingVisibilityState;
}

const DEFAULT_FORM: NewSourceFormState = {
  title: "",
  campaignId: "eldyrwild",
  documentClass: "lore",
  authorityState: "draft",
  visibilityState: "internal",
};

export function BuildSurfacePage() {
  const documentId = useWorkspaceDocumentUrlSelection();
  const [form, setForm] = useState<NewSourceFormState>(DEFAULT_FORM);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleCreate = useCallback(async (event: FormEvent) => {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      const created = await createWorkspaceDocument({
        title: form.title.trim() || "Untitled worldbuilding source",
        campaign_id: form.campaignId.trim(),
        kind: "worldbuilding_source",
        source_domain: "worldbuilding",
        document_class: form.documentClass.trim(),
        authority_state: form.authorityState,
        visibility_state: form.visibilityState,
      });
      navigateToDocument(created.document_id);
    } catch (error) {
      setCreateError(error instanceof Error ? error.message : "Unable to create worldbuilding source.");
    } finally {
      setCreating(false);
    }
  }, [form]);

  useEffect(() => {
    if (documentId) return;
    setCreateError(null);
  }, [documentId]);

  if (!documentId) {
    return (
      <AppChrome activeRoute="build">
        <main className="build-surface-new" data-testid="build-new-source-form">
          <h1>{BUILD_SURFACE_LABEL}</h1>
          <p>{BUILD_NEW_SOURCE_HEADING}</p>
          <form onSubmit={(event) => void handleCreate(event)}>
            <label>
              Title
              <input
                data-testid="build-new-title"
                value={form.title}
                onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              />
            </label>
            <label>
              Campaign
              <input
                data-testid="build-new-campaign"
                value={form.campaignId}
                onChange={(event) => setForm((current) => ({ ...current, campaignId: event.target.value }))}
              />
            </label>
            <label>
              Class
              <input
                data-testid="build-new-class"
                value={form.documentClass}
                onChange={(event) => setForm((current) => ({ ...current, documentClass: event.target.value }))}
              />
            </label>
            <label>
              Authority
              <select
                data-testid="build-new-authority"
                value={form.authorityState}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  authorityState: event.target.value as WorldbuildingAuthorityState,
                }))}
              >
                <option value="draft">draft</option>
                <option value="reviewed">reviewed</option>
                <option value="canonical">canonical</option>
              </select>
            </label>
            <label>
              Visibility
              <select
                data-testid="build-new-visibility"
                value={form.visibilityState}
                onChange={(event) => setForm((current) => ({
                  ...current,
                  visibilityState: event.target.value as WorldbuildingVisibilityState,
                }))}
              >
                <option value="internal">internal</option>
                <option value="player_safe">player_safe</option>
              </select>
            </label>
            {createError ? <p role="alert">{createError}</p> : null}
            <button type="submit" data-testid="build-create-button" disabled={creating}>
              Create source
            </button>
          </form>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="build">
      <BuildIngestToolbar />
      <BuildSurfaceShell key={documentId} documentId={documentId} />
    </AppChrome>
  );
}
