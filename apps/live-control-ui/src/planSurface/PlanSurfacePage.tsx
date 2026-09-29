import { useEffect, useMemo, useRef, useState } from "react";
import type { Editor, JSONContent } from "@tiptap/core";
import { EditorContent } from "@tiptap/react";

import {
  commitWorldOwnedPlanMarkdownWrite,
  createWorldOwnedPlan,
  getManagedWorldPlanContext,
  LiveApiError,
  getPlanView,
  getWorldOwnedPlanCommittedRevision,
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
  edit_generation?: number;
  create_uncertain?: boolean;
  pending_write?: {
    phase: "prepare" | "commit";
    base_revision: number;
    prepared_revision: number | null;
    base_markdown: string;
    markdown: string;
    edit_generation: number;
  } | null;
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
      edit_generation: typeof value.edit_generation === "number" ? value.edit_generation : 0,
      create_uncertain: value.create_uncertain === true,
      pending_write: value.pending_write && typeof value.pending_write === "object"
        && (value.pending_write.phase === "prepare" || value.pending_write.phase === "commit")
        && typeof value.pending_write.base_revision === "number"
        && typeof value.pending_write.base_markdown === "string"
        && typeof value.pending_write.markdown === "string"
        && typeof value.pending_write.edit_generation === "number"
        ? {
          phase: value.pending_write.phase,
          base_revision: value.pending_write.base_revision,
          prepared_revision: typeof value.pending_write.prepared_revision === "number"
            ? value.pending_write.prepared_revision
            : null,
          base_markdown: value.pending_write.base_markdown,
          markdown: value.pending_write.markdown,
          edit_generation: value.pending_write.edit_generation,
        }
        : null,
    };
  } catch {
    return null;
  }
}

function persistWorldPlanLocalDraft(
  worldId: string,
  draft: Pick<WorldPlanLocalDraftV2, "document_id" | "title" | "markdown" | "revision">
    & Partial<Pick<WorldPlanLocalDraftV2, "edit_generation" | "create_uncertain" | "pending_write">>,
): void {
  try {
    localStorage.setItem(worldPlanLocalDraftKey(worldId), JSON.stringify({
      schema_version: "dmb_plan_promotion_recovery_v2",
      scope_mode: "world",
      world_id: worldId,
      edit_generation: 0,
      create_uncertain: false,
      pending_write: null,
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
  const [createUncertain, setCreateUncertain] = useState(localDraft?.create_uncertain ?? false);
  const [recoveryConflict, setRecoveryConflict] = useState(false);
  const [serverDraft, setServerDraft] = useState<{ title: string; markdown: string; revision: number } | null>(null);
  const [editorGeneration, setEditorGeneration] = useState(0);
  const editorContent = useMemo(() => markdownToTiptapDoc(markdown).doc, [markdown]);
  const [status, setStatus] = useState<LoadStatus>("loading");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(false);
  const selectionEpochRef = useRef(0);
  const documentIdRef = useRef(initialDocumentId);
  const revisionRef = useRef<number | null>(localDraft?.revision ?? null);
  const titleRef = useRef(localDraft?.title ?? "Plan");
  const markdownRef = useRef(localDraft?.markdown ?? "");
  const editGenerationRef = useRef(localDraft?.edit_generation ?? 0);
  const pendingWriteRef = useRef(localDraft?.pending_write ?? null);
  const savingRef = useRef(false);
  const serverMarkdownRef = useRef("");

  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const selectedViewIsCurrent = (epoch: number, expectedDocumentId: string | null) =>
    mountedRef.current
    && selectionEpochRef.current === epoch
    && documentIdRef.current === expectedDocumentId;

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
          const recoverLocal = localDraft?.document_id === initialDocumentId;
          const revisionChangedUnderDraft = recoverLocal
            && localDraft.revision !== snapshot.loaded_revision
            && !localDraft.pending_write;
          const nextTitle = recoverLocal ? localDraft.title : snapshot.record.title;
          const nextMarkdown = recoverLocal ? localDraft.markdown : snapshot.markdown;
          documentIdRef.current = initialDocumentId;
          revisionRef.current = snapshot.loaded_revision;
          titleRef.current = nextTitle;
          markdownRef.current = nextMarkdown;
          serverMarkdownRef.current = snapshot.markdown;
          pendingWriteRef.current = recoverLocal ? localDraft.pending_write ?? null : null;
          setTitle(nextTitle);
          setMarkdown(nextMarkdown);
          setEditorGeneration((value) => value + 1);
          if (revisionChangedUnderDraft) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
            });
            setError("The saved Plan changed since this local draft. Your draft is preserved; choose which version to keep before saving.");
          }
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
            edit_generation: localDraft?.edit_generation ?? 0,
            pending_write: pendingWriteRef.current,
            create_uncertain: false,
          });
        }
        else if (localDraft?.document_id === null) {
          documentIdRef.current = null;
          revisionRef.current = null;
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
    if (savingRef.current) return;
    const epoch = ++selectionEpochRef.current;
    const priorDocumentId = documentIdRef.current;
    setStatus("loading");
    setError(null);
    try {
      const snapshot = await getWorldOwnedPlanSnapshot(nextDocumentId);
      if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
        throw new Error("This Plan does not belong to the selected World.");
      }
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      const url = new URL(window.location.href);
      url.searchParams.set("world", worldId);
      url.searchParams.set("documentId", nextDocumentId);
      window.history.pushState({}, "", `${url.pathname}${url.search}`);
      documentIdRef.current = nextDocumentId;
      revisionRef.current = snapshot.loaded_revision;
      titleRef.current = snapshot.record.title;
      markdownRef.current = snapshot.markdown;
      serverMarkdownRef.current = snapshot.markdown;
      pendingWriteRef.current = null;
      setDocumentId(nextDocumentId);
      setTitle(snapshot.record.title);
      setMarkdown(snapshot.markdown);
      setEditorGeneration((value) => value + 1);
      setRecoveryConflict(false);
      setServerDraft(null);
      setCreateUncertain(false);
      persistWorldPlanLocalDraft(worldId, {
        document_id: nextDocumentId,
        title: snapshot.record.title,
        markdown: snapshot.markdown,
        revision: snapshot.loaded_revision,
        edit_generation: editGenerationRef.current,
        pending_write: null,
        create_uncertain: false,
      });
      setMessage(null);
      setStatus("ready");
    } catch (reason) {
      if (!selectedViewIsCurrent(epoch, priorDocumentId)) return;
      setError(reason instanceof Error ? reason.message : "Plan could not be opened.");
      setStatus("error");
    }
  };

  const resetBlankPlan = () => {
    if (savingRef.current) return;
    ++selectionEpochRef.current;
    documentIdRef.current = null;
    revisionRef.current = null;
    titleRef.current = "Plan";
    markdownRef.current = "";
    pendingWriteRef.current = null;
    setRecoveryConflict(false);
    setServerDraft(null);
    setCreateUncertain(false);
    const url = new URL(window.location.href);
    url.searchParams.set("world", worldId);
    url.searchParams.delete("documentId");
    window.history.pushState({}, "", `${url.pathname}${url.search}`);
    setDocumentId(null);
    setTitle("Plan");
    setMarkdown("");
    setEditorGeneration((value) => value + 1);
    persistWorldPlanLocalDraft(worldId, {
      document_id: null,
      title: "Plan",
      markdown: "",
      revision: null,
      edit_generation: ++editGenerationRef.current,
      pending_write: null,
      create_uncertain: false,
    });
    setMessage(null);
    setError(null);
    setStatus("ready");
  };

  const save = async () => {
    if (savingRef.current || createUncertain || recoveryConflict || !markdownRef.current.trim()) return;
    const epoch = selectionEpochRef.current;
    const initialId = documentIdRef.current;
    let uiDocumentId = initialId;
    const isCurrent = () => selectedViewIsCurrent(epoch, uiDocumentId);
    let exactId = initialId;
    let currentRevision = revisionRef.current;
    let submittedTitle = titleRef.current.trim() || "Plan";
    let submittedMarkdown = markdownRef.current;
    let submittedGeneration = editGenerationRef.current;
    savingRef.current = true;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      if (!exactId) {
        const blankDraft = readWorldPlanLocalDraft(worldId);
        submittedTitle = blankDraft?.title ?? submittedTitle;
        submittedMarkdown = blankDraft?.markdown ?? submittedMarkdown;
        submittedGeneration = blankDraft?.edit_generation ?? submittedGeneration;
        persistWorldPlanLocalDraft(worldId, {
          document_id: null,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: null,
          edit_generation: submittedGeneration,
          create_uncertain: true,
          pending_write: null,
        });
        if (isCurrent()) setCreateUncertain(true);
        let created: WorldOwnedPlanRecordV2;
        try {
          created = await createWorldOwnedPlan({
            schema_version: "dmb_workspace_document_create_v2",
            scope_mode: "world",
            world_id: worldId,
            title: submittedTitle,
          });
        } catch (reason) {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            pending_write: null,
          });
          if (isCurrent()) {
            setError(`World Plan creation response was uncertain. Refresh Saved Plans and select the Plan if it appears; automatic retry is disabled to prevent a duplicate. ${reason instanceof Error ? reason.message : ""}`.trim());
          }
          return;
        }
        if (created.world_id !== worldId || created.campaign_id !== null || created.kind !== "plan") {
          const latest = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: null,
            title: latest?.title ?? submittedTitle,
            markdown: latest?.markdown ?? submittedMarkdown,
            revision: null,
            edit_generation: latest?.edit_generation ?? submittedGeneration,
            create_uncertain: true,
            pending_write: null,
          });
          throw new Error("Server returned a Plan outside the selected World; creation outcome is quarantined.");
        }
        exactId = created.document_id;
        currentRevision = created.revision;
        const latest = readWorldPlanLocalDraft(worldId);
        submittedTitle = latest?.document_id === null ? latest.title : submittedTitle;
        submittedMarkdown = latest?.document_id === null ? latest.markdown : submittedMarkdown;
        submittedGeneration = latest?.edit_generation ?? submittedGeneration;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: submittedTitle,
          markdown: submittedMarkdown,
          revision: currentRevision,
          edit_generation: submittedGeneration,
          create_uncertain: false,
          pending_write: null,
        });
        if (isCurrent() && documentIdRef.current === null) {
          uiDocumentId = exactId;
          documentIdRef.current = exactId;
          revisionRef.current = currentRevision;
          titleRef.current = submittedTitle;
          markdownRef.current = submittedMarkdown;
          serverMarkdownRef.current = "";
          setCreateUncertain(false);
          setDocumentId(exactId);
          setRecords((current) => [created, ...current]);
          const url = new URL(window.location.href);
          url.searchParams.set("world", worldId);
          url.searchParams.set("documentId", exactId);
          window.history.replaceState({}, "", `${url.pathname}${url.search}`);
        }
      }

      if (!exactId || currentRevision == null) {
        throw new Error("The exact World Plan identity or revision is unavailable.");
      }

      let savedLocal = readWorldPlanLocalDraft(worldId);
      if (savedLocal?.document_id === exactId) {
        submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
        submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
        submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
      }

      const previousPending = savedLocal?.document_id === exactId
        ? savedLocal.pending_write ?? null
        : pendingWriteRef.current;
      if (previousPending) {
        const snapshot = await getWorldOwnedPlanSnapshot(exactId);
        if (snapshot.record.world_id !== worldId || snapshot.record.campaign_id !== null) {
          throw new Error("Pending write recovery resolved outside the selected World.");
        }
        let committedMarkdown: string | null = null;
        try {
          const committedRevision = await getWorldOwnedPlanCommittedRevision(exactId);
          if (committedRevision.world_id !== worldId || committedRevision.campaign_id !== null) {
            throw new Error("Committed revision recovery resolved outside the selected World.");
          }
          committedMarkdown = committedRevision.markdown;
        } catch (reason) {
          if (!(reason instanceof LiveApiError && (reason.status === 404 || reason.status === 409))) {
            throw reason;
          }
        }

        const committed = committedMarkdown === previousPending.markdown;
        const preparedCopy = previousPending.prepared_revision !== null
          && snapshot.loaded_revision === previousPending.prepared_revision
          && snapshot.markdown === previousPending.markdown;
        const prepareApplied = previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision + 1
          && snapshot.markdown === previousPending.markdown;
        const prepareDidNotApply = previousPending.phase === "prepare"
          && snapshot.loaded_revision === previousPending.base_revision
          && snapshot.markdown === previousPending.base_markdown;
        if (!committed && !preparedCopy && !prepareApplied && !prepareDidNotApply) {
          if (isCurrent()) {
            setRecoveryConflict(true);
            setServerDraft({
              title: snapshot.record.title,
              markdown: snapshot.markdown,
              revision: snapshot.loaded_revision,
            });
            setError("The previous save outcome cannot be proven against the current World revision. Your local draft is preserved and saving is blocked until you choose a version.");
          }
          return;
        }
        currentRevision = snapshot.loaded_revision;
        revisionRef.current = currentRevision;
        serverMarkdownRef.current = committed ? committedMarkdown ?? snapshot.markdown : snapshot.markdown;
        pendingWriteRef.current = null;
        const latest = readWorldPlanLocalDraft(worldId);
        const preserveLatest = latest?.document_id === exactId
          && (latest.edit_generation ?? 0) > previousPending.edit_generation;
        persistWorldPlanLocalDraft(worldId, {
          document_id: exactId,
          title: preserveLatest ? latest.title : submittedTitle,
          markdown: preserveLatest ? latest.markdown : submittedMarkdown,
          revision: currentRevision,
          edit_generation: preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration,
          create_uncertain: false,
          pending_write: null,
        });
        if (committed && !preserveLatest) {
          if (isCurrent()) {
            setMessage("Saved to this World.");
            setSaving(false);
          }
          return;
        }
        savedLocal = readWorldPlanLocalDraft(worldId);
        if (savedLocal?.document_id === exactId) {
          submittedTitle = isCurrent() ? titleRef.current.trim() || "Plan" : savedLocal.title;
          submittedMarkdown = isCurrent() ? markdownRef.current : savedLocal.markdown;
          submittedGeneration = isCurrent() ? editGenerationRef.current : (savedLocal.edit_generation ?? 0);
        }
      }

      const baseRevision = currentRevision;
      const baseMarkdown = serverMarkdownRef.current;
      const preparing = {
        phase: "prepare" as const,
        base_revision: baseRevision,
        prepared_revision: null,
        base_markdown: baseMarkdown,
        markdown: submittedMarkdown,
        edit_generation: submittedGeneration,
      };
      pendingWriteRef.current = preparing;
      const beforePrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: beforePrepare?.title ?? submittedTitle,
        markdown: beforePrepare?.markdown ?? submittedMarkdown,
        revision: baseRevision,
        edit_generation: beforePrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparing,
      });
      const scope = {
        schema_version: "dmb_tiptap_markdown_write_prepare_v2" as const,
        scope_mode: "world" as const,
        world_id: worldId,
      };
      const prepared = await prepareTiptapMarkdownWrite({
        ...scope,
        document_id: exactId,
        markdown: submittedMarkdown,
        expected_revision: baseRevision,
      });
      if (!prepared.writer_ok || !prepared.writer_confirm_token || prepared.world_id !== worldId) {
        throw new Error(prepared.warnings.join(" ") || "Plan write could not be prepared.");
      }
      currentRevision = prepared.registry_revision;
      revisionRef.current = currentRevision;
      const preparedWrite = {
        ...preparing,
        phase: "commit" as const,
        prepared_revision: prepared.registry_revision,
      };
      pendingWriteRef.current = preparedWrite;
      const afterPrepare = readWorldPlanLocalDraft(worldId);
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: afterPrepare?.title ?? submittedTitle,
        markdown: afterPrepare?.markdown ?? submittedMarkdown,
        revision: prepared.registry_revision,
        edit_generation: afterPrepare?.edit_generation ?? submittedGeneration,
        create_uncertain: false,
        pending_write: preparedWrite,
      });

      const committed = await commitWorldOwnedPlanMarkdownWrite({
        schema_version: "dmb_tiptap_markdown_write_commit_v2",
        scope_mode: "world",
        world_id: worldId,
        document_id: exactId,
        markdown: submittedMarkdown,
        expected_revision: prepared.registry_revision,
        writer_confirm_token: prepared.writer_confirm_token,
      });
      if (committed.world_id !== worldId || committed.committed_record.schema_version !== "dmb_world_owned_plan_record_v2") {
        throw new Error("Commit receipt did not preserve World-owned Plan scope.");
      }
      currentRevision = committed.registry_revision;
      revisionRef.current = currentRevision;
      serverMarkdownRef.current = submittedMarkdown;
      pendingWriteRef.current = null;
      const latest = readWorldPlanLocalDraft(worldId);
      const preserveLatest = latest?.document_id === exactId
        && (latest.edit_generation ?? 0) > submittedGeneration;
      const finalTitle = preserveLatest ? latest.title : committed.title;
      const finalMarkdown = preserveLatest ? latest.markdown : submittedMarkdown;
      const finalGeneration = preserveLatest ? latest.edit_generation ?? submittedGeneration : submittedGeneration;
      persistWorldPlanLocalDraft(worldId, {
        document_id: exactId,
        title: finalTitle,
        markdown: finalMarkdown,
        revision: currentRevision,
        edit_generation: finalGeneration,
        create_uncertain: false,
        pending_write: null,
      });
      if (isCurrent()) {
        if (!preserveLatest) {
          titleRef.current = committed.title;
          markdownRef.current = submittedMarkdown;
          setTitle(committed.title);
          setMarkdown(submittedMarkdown);
          setEditorGeneration((value) => value + 1);
        }
        setRecords((current) => current.map((record) => record.document_id === exactId ? committed.committed_record : record));
        setCreateUncertain(false);
        setRecoveryConflict(false);
        setServerDraft(null);
        setMessage("Saved to this World.");
      }
    } catch (reason) {
      if (isCurrent()) {
        setError(reason instanceof Error ? reason.message : "Plan could not be saved.");
      }
    } finally {
      savingRef.current = false;
      if (isCurrent()) setSaving(false);
    }
  };

  const refreshSavedPlans = async () => {
    const epoch = selectionEpochRef.current;
    const selectedId = documentIdRef.current;
    try {
      const inventory = await listWorldOwnedPlans(worldId);
      if (!selectedViewIsCurrent(epoch, selectedId) || inventory.world_id !== worldId) return;
      setRecords(inventory.records);
      setMessage("Saved Plans refreshed. Select an exact saved Plan if the earlier create succeeded.");
      setError(null);
    } catch (reason) {
      if (selectedViewIsCurrent(epoch, selectedId)) {
        setError(reason instanceof Error ? reason.message : "Saved Plans could not be refreshed.");
      }
    }
  };

  const useServerVersion = () => {
    if (!serverDraft) return;
    titleRef.current = serverDraft.title;
    markdownRef.current = serverDraft.markdown;
    revisionRef.current = serverDraft.revision;
    pendingWriteRef.current = null;
    const generation = ++editGenerationRef.current;
    setTitle(serverDraft.title);
    setMarkdown(serverDraft.markdown);
    setEditorGeneration((value) => value + 1);
    setRecoveryConflict(false);
    setServerDraft(null);
    setError(null);
    persistWorldPlanLocalDraft(worldId, {
      document_id: documentIdRef.current,
      title: serverDraft.title,
      markdown: serverDraft.markdown,
      revision: serverDraft.revision,
      edit_generation: generation,
      create_uncertain: false,
      pending_write: null,
    });
  };

  return (
    <AppChrome activeRoute="plan">
      <main className="app-status" data-testid="world-owned-plan">
        <h1>Plan</h1>
        <p>{worldName}</p>
        <p>Planning belongs to this World. It is not attached to a campaign or session.</p>
        {records.length || createUncertain ? (
          <label>Saved Plans
            <select value={documentId ?? ""} disabled={saving || status === "loading"} onChange={(event) => event.target.value ? void openPlan(event.target.value) : resetBlankPlan()}>
              <option value="">New blank Plan</option>
              {records.map((record) => <option key={record.document_id} value={record.document_id}>{record.title}</option>)}
            </select>
          </label>
        ) : null}
        {createUncertain ? (
          <section role="alert">
            <p>Plan creation may have succeeded, but its response was lost. Refresh Saved Plans and select the exact Plan if it appears. Automatic creation retry is blocked to avoid duplicates.</p>
            <button type="button" onClick={() => void refreshSavedPlans()} disabled={saving}>Refresh Saved Plans</button>
          </section>
        ) : null}
        {documentId ? <button type="button" onClick={resetBlankPlan} disabled={saving}>New blank Plan</button> : null}
        {recoveryConflict && serverDraft ? (
          <section role="alert">
            <p>The server Plan changed while a local draft was pending. Your local text is preserved, but cannot overwrite the newer server version silently.</p>
            <button type="button" onClick={useServerVersion}>Use saved Plan version</button>
          </section>
        ) : null}
        <label>Plan title<input value={title} onChange={(event) => {
          const next = event.target.value;
          titleRef.current = next;
          const generation = ++editGenerationRef.current;
          setTitle(next);
          const saved = readWorldPlanLocalDraft(worldId);
          persistWorldPlanLocalDraft(worldId, {
            document_id: documentIdRef.current,
            title: next,
            markdown: markdownRef.current,
            revision: revisionRef.current,
            edit_generation: generation,
            create_uncertain: createUncertain,
            pending_write: saved?.pending_write ?? pendingWriteRef.current,
          });
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
                markdownRef.current = next;
                const generation = ++editGenerationRef.current;
                setMarkdown(next);
                const saved = readWorldPlanLocalDraft(worldId);
                persistWorldPlanLocalDraft(worldId, {
                  document_id: documentIdRef.current,
                  title: titleRef.current,
                  markdown: next,
                  revision: revisionRef.current,
                  edit_generation: generation,
                  create_uncertain: createUncertain,
                  pending_write: saved?.pending_write ?? pendingWriteRef.current,
                });
              }
            }}
          >
            {(editor) => <EditorContent editor={editor} aria-label="Markdown plan" />}
          </MarkdownEditorCore>
        </div>
        <button type="button" onClick={() => void save()} disabled={status !== "ready" || saving || createUncertain || recoveryConflict || !markdown.trim()}>
          {saving ? "Saving…" : "Save Plan"}
        </button>
        {status === "loading" ? <p role="status">Loading World Plan…</p> : null}
        {message ? <p role="status">{message}</p> : null}
        {error ? <p role="alert">{error}</p> : null}
      </main>
    </AppChrome>
  );
}
