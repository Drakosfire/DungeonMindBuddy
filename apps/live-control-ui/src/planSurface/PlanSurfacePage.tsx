import { useEffect, useMemo, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import {
  commitWorldOwnedPlanMarkdownWrite,
  createWorldOwnedPlan,
  getManagedWorldPlanContext,
  getPlanView,
  getWorldOwnedPlanSnapshot,
  listWorldOwnedPlans,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { PlanViewProjection, WorldOwnedPlanRecordV2 } from "../api/types";
import { MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { useSelectedWorld } from "../selectedWorld/SelectedWorldContext";

type LoadStatus = "loading" | "ready" | "error";

export function PlanSurfacePage() {
  const selectedWorld = useSelectedWorld();
  const managedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [error, setError] = useState<string | null>(null);
  const [planView, setPlanView] = useState<PlanViewProjection | null>(null);
  const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);

  useEffect(() => {
    if (selectedWorld.kind === "loading" || selectedWorld.kind === "error" || managedWorldId) return;
    let cancelled = false;
    (async () => {
      setStatus("loading");
      setError(null);
      setPlanView(null);
      try {
        const response = await getPlanView(managedWorldId);
        if (!cancelled) {
          if (managedWorldId && (
            response.world_id !== managedWorldId
            || response.campaign_id !== managedWorldId
          )) {
            throw new Error(`Plan context does not match selected World ${managedWorldId}.`);
          }
          setPlanView(response);
          setStatus("ready");
        }
      } catch (loadError) {
        if (!cancelled) {
          setStatus("error");
          setError(loadError instanceof Error ? loadError.message : "Failed to load plan context");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [managedWorldId, selectedWorld.kind]);

  if (selectedWorld.kind === "loading") {
    return <AppChrome activeRoute="plan"><main className="app-status"><p>Resolving selected World…</p></main></AppChrome>;
  }
  if (selectedWorld.kind === "error") {
    return <AppChrome activeRoute="plan"><main className="app-status app-error"><h1>Plan</h1><p>{selectedWorld.message}</p></main></AppChrome>;
  }
  if (managedWorldId) return <WorldOwnedPlanPage key={managedWorldId} worldId={managedWorldId} worldName={selectedWorld.kind === "managed" ? selectedWorld.name : managedWorldId} />;

  if (status === "loading") {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status">
          <p>Loading plan surface…</p>
        </main>
      </AppChrome>
    );
  }

  if (status === "error" || !planView) {
    return (
      <AppChrome activeRoute="plan">
        <main className="app-status app-error">
          <h1>Plan</h1>
          <p>{error ?? "Unable to load plan context."}</p>
        </main>
      </AppChrome>
    );
  }

  return (
    <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
      <PlanSurfaceShell planView={planView} onEditorToolsChange={setEditorTools} />
    </AppChrome>
  );
}

interface WorldPlanLocalDraftV2 {
  schema_version: "dmb_plan_promotion_recovery_v2";
  scope_mode: "world";
  world_id: string;
  document_id: string | null;
  title: string;
  markdown: string;
  revision: number | null;
}

function worldPlanLocalDraftKey(worldId: string): string {
  return `dmb:world-plan-local-draft:v2:${worldId}`;
}

function readWorldPlanLocalDraft(worldId: string): WorldPlanLocalDraftV2 | null {
  try {
    const raw = localStorage.getItem(worldPlanLocalDraftKey(worldId));
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<WorldPlanLocalDraftV2>;
    if (value.schema_version !== "dmb_plan_promotion_recovery_v2" || value.scope_mode !== "world"
      || value.world_id !== worldId || typeof value.title !== "string" || typeof value.markdown !== "string") return null;
    return {
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: typeof value.document_id === "string" ? value.document_id : null,
      title: value.title,
      markdown: value.markdown,
      revision: typeof value.revision === "number" ? value.revision : null,
    };
  } catch {
    return null;
  }
}

function persistWorldPlanLocalDraft(
  worldId: string,
  draft: Pick<WorldPlanLocalDraftV2, "document_id" | "title" | "markdown" | "revision">,
): void {
  try {
    localStorage.setItem(worldPlanLocalDraftKey(worldId), JSON.stringify({
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      ...draft,
    } satisfies WorldPlanLocalDraftV2));
  } catch {
    // Browser-local recovery is best effort; durable Save remains server-owned.
  }
}

function WorldOwnedPlanPage({ worldId, worldName }: { worldId: string; worldName: string }) {
  const [localDraft] = useState(() => readWorldPlanLocalDraft(worldId));
  const [initialDocumentId] = useState(() =>
    new URLSearchParams(window.location.search).get("documentId")?.trim() || localDraft?.document_id || null,
  );
  const [records, setRecords] = useState<WorldOwnedPlanRecordV2[]>([]);
  const [documentId, setDocumentId] = useState<string | null>(initialDocumentId);
  const [title, setTitle] = useState(localDraft?.title ?? "Plan");
  const [markdown, setMarkdown] = useState(localDraft?.markdown ?? "");
  const [editorGeneration, setEditorGeneration] = useState(0);
  const editorContent = useMemo(() => markdownToTiptapDoc(markdown).doc, [markdown]);
  const [revision, setRevision] = useState<number | null>(localDraft?.revision ?? null);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const context = await getManagedWorldPlanContext(worldId);
        if (context.schema_version !== "dmb_managed_world_plan_context_v2"
          || context.scope_mode !== "world" || context.world_id !== worldId
          || context.campaign_id !== null || context.session !== null) {
          throw new Error("Managed Plan context does not match the selected World.");
        }
        const inventory = await listWorldOwnedPlans(worldId);
        if (inventory.world_id !== worldId) throw new Error("World Plan inventory does not match the selected World.");
        if (cancelled) return;
        setRecords(inventory.records);
        if (initialDocumentId) {
          const snapshot = await getWorldOwnedPlanSnapshot(initialDocumentId);
          if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null || snapshot.record.kind !== "plan") {
            throw new Error("This Plan does not belong to the selected World.");
          }
          if (cancelled) return;
          const recoverLocal = localDraft?.document_id === initialDocumentId
            && localDraft.revision === snapshot.loaded_revision;
          const nextTitle = recoverLocal ? localDraft.title : snapshot.record.title;
          const nextMarkdown = recoverLocal ? localDraft.markdown : snapshot.markdown;
          setTitle(nextTitle);
          setMarkdown(nextMarkdown);
          setEditorGeneration((value) => value + 1);
          setRevision(snapshot.loaded_revision);
          if (!new URLSearchParams(window.location.search).has("documentId")) {
            const url = new URL(window.location.href);
            url.searchParams.set("world", worldId);
            url.searchParams.set("documentId", initialDocumentId);
            window.history.replaceState({}, "", `${url.pathname}${url.search}`);
          }
          persistWorldPlanLocalDraft(worldId, {
            document_id: initialDocumentId,
            title: nextTitle,
            markdown: nextMarkdown,
            revision: snapshot.loaded_revision,
          });
        }
        else if (localDraft?.document_id === null) {
          persistWorldPlanLocalDraft(worldId, localDraft);
        }
        if (!cancelled) setStatus("ready");
      } catch (reason) {
        if (!cancelled) {
          setError(reason instanceof Error ? reason.message : "World Plan could not be loaded.");
          setStatus("error");
        }
      }
    })();
    return () => { cancelled = true; };
  }, [initialDocumentId, localDraft, worldId]);

  const openPlan = async (nextDocumentId: string) => {
    setStatus("loading");
    setError(null);
    try {
      const snapshot = await getWorldOwnedPlanSnapshot(nextDocumentId);
      if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
        throw new Error("This Plan does not belong to the selected World.");
      }
      const url = new URL(window.location.href);
      url.searchParams.set("world", worldId);
      url.searchParams.set("documentId", nextDocumentId);
      window.history.pushState({}, "", `${url.pathname}${url.search}`);
      setDocumentId(nextDocumentId);
      setTitle(snapshot.record.title);
      setMarkdown(snapshot.markdown);
      setEditorGeneration((value) => value + 1);
      setRevision(snapshot.loaded_revision);
      persistWorldPlanLocalDraft(worldId, {
        document_id: nextDocumentId,
        title: snapshot.record.title,
        markdown: snapshot.markdown,
        revision: snapshot.loaded_revision,
      });
      setMessage(null);
      setStatus("ready");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Plan could not be opened.");
      setStatus("error");
    }
  };

  const resetBlankPlan = () => {
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    url.searchParams.delete("documentId");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setDocumentId(null);
    setTitle("Plan");
    setMarkdown("");
    setEditorGeneration((value) => value + 1);
    setRevision(null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: null,
      title: "Plan",
      markdown: "",
      revision: null,
    });
    setMessage(null);
    setError(null);
    setStatus("ready");
  };

  const save = async () => {
    if (saving || !markdown.trim()) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      let exactId = documentId;
      let currentRevision = revision;
      if (!exactId) {
        const created = await createWorldOwnedPlan({
          schema_version: "dmb_workspace_document_create_v2",
          scope_mode: "world",
          world_id: worldId,
          title: title.trim() || "Plan",
        });
        if (created.world_id !== worldId || created.campaign_id !== null) throw new Error("Server returned a Plan outside the selected World.");
        exactId = created.document_id;
        currentRevision = created.revision;
        setDocumentId(exactId);
        setRevision(currentRevision);
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: title.trim() || "Plan",
          markdown,
          revision: currentRevision,
        });
        setRecords((current) => [created, ...current]);
        const url = new URL(window.location.href);
        url.searchParams.set("world", worldId);
        url.searchParams.set("documentId", exactId);
        window.history.replaceState({}, "", `${url.pathname}${url.search}`);
      }
      const scope = {
        schema_version: "dmb_tiptap_markdown_write_prepare_v2" as const,
        scope_mode: "world" as const,
        world_id: worldId,
      };
      const prepared = await prepareTiptapMarkdownWrite({
        ...scope,
        document_id: exactId,
        markdown,
        expected_revision: currentRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token || prepared.world_id !== worldId) {
        throw new Error(prepared.warnings.join(" ") || "Plan write could not be prepared.");
      }
      const committed = await commitWorldOwnedPlanMarkdownWrite({
        schema_version: "dmb_tiptap_markdown_write_commit_v2",
        scope_mode: "world",
        world_id: worldId,
        document_id: exactId,
        markdown,
        expected_revision: prepared.registry_revision,
        writer_confirm_token: prepared.writer_confirm_token,
      });
      if (committed.world_id !== worldId || committed.committed_record.schema_version !== "dmb_world_owned_plan_record_v2") {
        throw new Error("Commit receipt did not preserve World-owned Plan scope.");
      }
      const snapshot = await getWorldOwnedPlanSnapshot(exactId);
      setRevision(snapshot.loaded_revision);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: snapshot.record.title,
        markdown: snapshot.markdown,
        revision: snapshot.loaded_revision,
      });
      setTitle(snapshot.record.title);
      setMarkdown(snapshot.markdown);
      setRecords((current) => current.map((record) => record.document_id === exactId ? snapshot.record : record));
      setMessage("Saved to this World.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Plan could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <AppChrome activeRoute="plan">
      <main className="app-status" data-testid="world-owned-plan">
        <h1>Plan</h1>
        <p>{worldName}</p>
        <p>Planning belongs to this World. It is not attached to a campaign or session.</p>
        {records.length ? (
          <label>Saved Plans
            <select value={documentId ?? ""} onChange={(event) => event.target.value ? void openPlan(event.target.value) : resetBlankPlan()}>
              <option value="">New blank Plan</option>
              {records.map((record) => <option key={record.document_id} value={record.document_id}>{record.title}</option>)}
            </select>
          </label>
        ) : null}
        {documentId ? <button type="button" onClick={resetBlankPlan}>New blank Plan</button> : null}
        <label>Plan title<input value={title} onChange={(event) => {
          const next = event.target.value;
          setTitle(next);
          persistWorldPlanLocalDraft(worldId, { document_id: documentId, title: next, markdown, revision });
        }} /></label>
        <div className="world-owned-plan__editor" data-testid="world-owned-plan-editor">
          <MarkdownEditorCore
            content={editorContent}
            documentKey={`${worldId}:${documentId ?? "local"}:${editorGeneration}`}
            editable
            dataTestId="world-owned-plan-markdown-editor"
            onUpdate={(json: JSONContent, _editor: Editor, meta) => {
              if (!meta.programmatic) {
                const next = defaultMarkdownDocumentAdapter.exportMarkdown(json);
                setMarkdown(next);
                persistWorldPlanLocalDraft(worldId, { document_id: documentId, title, markdown: next, revision });
              }
            }}
          >
            {(editor) => <EditorContent editor={editor} aria-label="Markdown plan" />}
          </MarkdownEditorCore>
        </div>
        <button type="button" onClick={() => void save()} disabled={status !== "ready" || saving || !markdown.trim()}>
          {saving ? "Saving…" : "Save Plan"}
        </button>
        {status === "loading" ? <p role="status">Loading World Plan…</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </main>
    </AppChrome>
  );
}
