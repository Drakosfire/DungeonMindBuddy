import { WorkspaceTrashControl } from "../workspaceLifecycle/WorkspaceTrashControl";
import { loadNativeDocuments, nativeDocumentHref } from "./buildNativeDocuments";
import type { NativeSourceMetadata } from "../api/nativeSourceInspection";
import { useEffect, useId, useMemo, useState, useRef } from "react";

import { listRetainedPdfDocuments, retainedPdfBuildHref, type RetainedPdf } from "../api/retainedPdfRegions";
import { listWorldThreatDrafts, type WorldThreatDraftSummary } from "../api/liveApi";
import { buildSavedStatblockHref, readSavedStatblockTarget } from "../statblocks/savedStatblockLocation";
import type { WorkspaceDocumentRecord } from "../api/types";
import { formatReviewCampaignLabel } from "../graphLens/sessionCampaignContext";
import "./buildDocumentPicker.css";
import {
  BUILD_KNOWN_CAMPAIGN_IDS,
  type BuildKnownCampaignId,
} from "./buildBareEntryCampaign";
import type { BuildDocumentListStatus } from "./useBuildWorkspaceDocumentController";

function formatShortDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function buildDocumentOptionLabel(
  record: WorkspaceDocumentRecord,
  sameCampaignRecords: WorkspaceDocumentRecord[],
): string {
  const duplicateTitle = sameCampaignRecords.filter(
    (entry) => entry.title.trim().toLowerCase() === record.title.trim().toLowerCase(),
  ).length > 1;
  if (!duplicateTitle) return record.title;
  const documentClass = record.document_class ?? "lore";
  return `${record.title} · ${documentClass} · updated ${formatShortDate(record.updated_at)}`;
}

interface BuildDocumentSelectorProps {
  worldId?: string | null;
  documents: WorkspaceDocumentRecord[] | null;
  listStatus: BuildDocumentListStatus;
  activeDocumentId: string | null;
  activeRecord: WorkspaceDocumentRecord | null;
  preferredCampaignId: string | null;
  switching: boolean;
  onPageTrashed?: (documentId: string) => void;
  activePageTrashBlocked?: boolean;
  loadMorePages?: () => void;
  onSelect: (documentId: string) => void;
}

export function BuildDocumentSelector({
  worldId,
  documents,
  listStatus,
  activeDocumentId,
  activeRecord,
  preferredCampaignId,
  switching,
  onPageTrashed,
  activePageTrashBlocked,
  loadMorePages,
  onSelect,
}: BuildDocumentSelectorProps) {
  const [query, setQuery] = useState("");
  const [catalog, setCatalog] = useState<{ worldId: string; drafts: WorldThreatDraftSummary[]; error: boolean }>();
  useEffect(() => {
    if (!worldId) return;
    const request = new AbortController();
    listWorldThreatDrafts(worldId, request.signal).then(
      drafts => { if (!request.signal.aborted) setCatalog({ worldId, drafts, error: false }); },
      () => { if (!request.signal.aborted) setCatalog({ worldId, drafts: [], error: true }); },
    );
    return () => request.abort();
  }, [worldId]);
  const currentCatalog = catalog?.worldId === worldId ? catalog : undefined;
  const filter = query.trim().toLowerCase();
  const [category, setCategory] = useState<PickerCategory>("Recent");
  const rowPrefix = useId();
  const dialog = useRef<HTMLDialogElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const recentKey = `buddy:build:recent:${worldId ?? preferredCampaignId ?? ""}`;
  const [recent, setRecent] = useState<string[]>([]);
  const statblocks = (currentCatalog?.drafts ?? []).flatMap(draft => {
    const revisionId = draft.saved_revision_id;
    if (draft.world_id !== worldId || !revisionId) return [];
    return [{
      href: buildSavedStatblockHref({ worldId: draft.world_id, draftId: draft.draft_id, revisionId }),
      title: draft.name,
    }];
  });
  const [pdfCatalog, setPdfCatalog] = useState<{ worldId: string; documents: RetainedPdf[]; error?: boolean }>();
  useEffect(() => {
    if (!worldId) return;
    const request = new AbortController();
    listRetainedPdfDocuments(worldId, request.signal).then(documents => {
      if (!request.signal.aborted) setPdfCatalog({ worldId, documents });
    }, () => {
      if (!request.signal.aborted) setPdfCatalog({ worldId, documents: [], error: true });
    });
    return () => request.abort();
  }, [worldId]);
  const currentPdfCatalog = pdfCatalog?.worldId === worldId ? pdfCatalog : undefined;
  const retainedPdfs = currentPdfCatalog?.documents ?? [];
  const activePdf = retainedPdfs.find(entry => entry.locator.source_revision_id ===
    new URLSearchParams(window.location.search).get("pdf"));
  const [nativeCatalog, setNativeCatalog] = useState<{ worldId: string; sources: NativeSourceMetadata[]; error?: boolean }>();
  useEffect(() => {
    if (!worldId) return;
    const request = new AbortController();
    void loadNativeDocuments(worldId, request.signal).then(({ sources }) => {
      if (!request.signal.aborted) setNativeCatalog({ worldId, sources });
    }, () => {
      if (!request.signal.aborted) setNativeCatalog({ worldId, sources: [], error: true });
    });
    return () => request.abort();
  }, [worldId]);
  const currentNativeCatalog = nativeCatalog?.worldId === worldId ? nativeCatalog : undefined;
  const nativeSources = currentNativeCatalog?.sources ?? [];
  const orderedNativeSources = [
    ...nativeSources.filter(source => source.navigation.kind === "recap").sort((a, b) => {
      const left = a.navigation.session_id;
      const right = b.navigation.session_id;
      if (left && right) {
        const order = right.localeCompare(left, undefined, { numeric: true });
        if (order) return order;
      } else if (left || right) return left ? -1 : 1;
      return (a.navigation.label ?? "").localeCompare(b.navigation.label ?? "")
        || a.source_revision.source_revision_id.localeCompare(b.source_revision.source_revision_id);
    }),
    ...nativeSources.filter(source => source.navigation.kind !== "recap"),
  ];
  const activeNativeId = new URLSearchParams(window.location.search).get("nativeDocument");
  const activeNative = nativeSources.find(source => source.source_revision.source_revision_id === activeNativeId);
  const activeStatblock = readSavedStatblockTarget(window.location.href);

  const groupedOptions = useMemo(() => {
    const campaignOrder = [...BUILD_KNOWN_CAMPAIGN_IDS] as BuildKnownCampaignId[];
    if (preferredCampaignId && isBuildKnownCampaignId(preferredCampaignId)) {
      const idx = campaignOrder.indexOf(preferredCampaignId);
      if (idx > 0) {
        campaignOrder.splice(idx, 1);
        campaignOrder.unshift(preferredCampaignId);
      }
    }

    // Live Canvas/active record wins over a stale registry list entry for the same id
    // (rename can adopt before refreshDocuments completes or if refresh fails).
    const listed = (documents ?? []).map((entry) =>
      activeRecord && entry.document_id === activeRecord.document_id ? activeRecord : entry,
    );

    const byCampaign = new Map<string, WorkspaceDocumentRecord[]>();
    for (const record of listed) {
      const bucket = byCampaign.get(record.campaign_id ?? "") ?? [];
      bucket.push(record);
      byCampaign.set(record.campaign_id ?? "", bucket);
    }

    const groups: Array<{ campaignId: string; label: string; options: Array<{ id: string; label: string }> }> =
      [];
    const seenCampaigns = new Set<string>();

    for (const campaignId of campaignOrder) {
      const records = byCampaign.get(campaignId);
      if (!records?.length) continue;
      seenCampaigns.add(campaignId);
      groups.push({
        campaignId,
        label: formatReviewCampaignLabel(campaignId).replace(/^Longmont /, ""),
        options: records.map((record) => ({
          id: record.document_id,
          label: buildDocumentOptionLabel(record, records),
        })),
      });
    }

    for (const [campaignId, records] of byCampaign.entries()) {
      if (seenCampaigns.has(campaignId)) continue;
      groups.push({
        campaignId,
        label: campaignId ? formatReviewCampaignLabel(campaignId) : "Pages without a campaign tag",
        options: records.map((record) => ({
          id: record.document_id,
          label: buildDocumentOptionLabel(record, records),
        })),
      });
    }

    if (
      activeRecord &&
      !listed.some((entry) => entry.document_id === activeRecord.document_id)
    ) {
      const orphanCampaign = activeRecord.campaign_id ?? "";
      groups.unshift({
        campaignId: orphanCampaign,
        label: orphanCampaign ? formatReviewCampaignLabel(orphanCampaign) : "Pages without a campaign tag",
        options: [
          {
            id: activeRecord.document_id,
            label: `${activeRecord.title} (no longer listed as active)`,
          },
        ],
      });
    }

    return groups;
  }, [activeRecord, documents, preferredCampaignId]);

  const activeId = activeNative && worldId ? nativeDocumentHref(worldId, activeNative)
    : activePdf && worldId ? retainedPdfBuildHref(worldId, activePdf)
    : activeStatblock ? buildSavedStatblockHref(activeStatblock) : activeDocumentId;
  const entries: PickerEntry[] = [
    ...groupedOptions.flatMap(group => group.options.map(option => ({
      ...option, category: "Pages" as const, detail: group.label,
    }))),
    ...statblocks.map(item => ({ id: item.href, label: item.title, category: "Statblocks" as const })),
    ...(worldId ? retainedPdfs.map(entry => ({
      id: retainedPdfBuildHref(worldId, entry), label: entry.name, category: "PDFs" as const,
    })) : []),
    ...(worldId ? orderedNativeSources.map(source => ({
      id: nativeDocumentHref(worldId, source), label: source.navigation.label ?? "Unnamed document",
      category: source.navigation.kind === "recap" ? "Recaps" as const : "Ingested text" as const,
      detail: [source.navigation.campaign_id, source.navigation.session_id && `Session ${source.navigation.session_id}`]
        .filter(Boolean).join(" · "),
    })) : []),
  ];
  useEffect(() => {
    if (!activeId) return;
    try {
      const ids = readRecent(recentKey);
      localStorage.setItem(recentKey, JSON.stringify([activeId, ...ids.filter(id => id !== activeId)].slice(0, 20)));
    } catch {
      // The picker remains available when browser storage is disabled.
    }
  }, [activeId, recentKey]);

  const pageRecords = new Map((documents ?? []).map(record => [record.document_id, record]));
  if (activeRecord) pageRecords.set(activeRecord.document_id, activeRecord);
  const byId = new Map(entries.map(entry => [entry.id, entry]));
  const visible = filter
    ? entries.filter(entry => `${entry.label} ${entry.category} ${entry.detail ?? ""}`.toLowerCase().includes(filter))
    : category === "Recent"
      ? recent.flatMap(id => byId.get(id) ?? [])
      : entries.filter(entry => category === "All documents" || entry.category === category);
  const pending = listStatus === "loading" || Boolean(worldId && (!currentCatalog || !currentPdfCatalog || !currentNativeCatalog));
  const errors = [
    currentCatalog?.error && "Saved statblocks unavailable",
    currentPdfCatalog?.error && "PDF documents unavailable",
    currentNativeCatalog?.error && "Ingested text documents unavailable",
  ].filter(Boolean);

  function closePicker() {
    if (dialog.current?.close) dialog.current.close();
    else dialog.current?.removeAttribute("open");
    trigger.current?.focus();
  }

  function openPicker() {
    setCategory("Recent");
    setQuery("");
    setRecent(readRecent(recentKey));
    if (dialog.current?.showModal) dialog.current.showModal();
    else dialog.current?.setAttribute("open", "");
    search.current?.focus();
  }

  function openDocument(id: string) {
    closePicker();
    if (id.startsWith("/build?")) window.location.assign(id);
    else if (worldId && (activeStatblock || activeNativeId || new URLSearchParams(window.location.search).has("pdf"))) {
      window.location.assign("/build?" + new URLSearchParams({ world: worldId, documentId: id }));
    } else onSelect(id);
  }

  return (
    <div className="build-document-selector build-document-selector--context" data-testid="build-document-selector">
      <button ref={trigger} type="button" className="surface-context-action" data-testid="build-document-select"
        data-guided-control="source" aria-label="Open document" title="Open document" aria-haspopup="dialog" disabled={switching} onClick={openPicker}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
          strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M3 18V6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v2M3 18l2-7h17l-2 7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" />
        </svg>
      </button>
      <dialog ref={dialog} className="build-document-picker" aria-label="Open document" data-native-escape-owner
        onCancel={event => {
          if (event.target !== event.currentTarget) return;
          event.preventDefault();
          closePicker();
        }}>
        <header className="build-document-picker__toolbar">
          <input ref={search} type="search" aria-label="Search documents" placeholder="Search documents"
            value={query} onChange={event => setQuery(event.target.value)} />
          <button type="button" aria-label="Close document picker" onClick={closePicker}>×</button>
        </header>
        <div className="build-document-picker__body">
          <nav aria-label="Document categories">
            {PICKER_CATEGORIES.map(item => <button key={item} type="button"
              aria-pressed={!filter && category === item} onClick={() => { setCategory(item); setQuery(""); }}>
              {item}
            </button>)}
          </nav>
          <section aria-label={filter ? "Search results" : category} className="build-document-picker__results">
            {errors.map(error => <p key={String(error)} role="status">{error}</p>)}
            {visible.length ? <ul>{visible.map((entry, index) => {
              const page = pageRecords.get(entry.id);
              return <li key={entry.id}>
              <button type="button" data-document-id={entry.id} aria-label={entry.label}
                aria-describedby={`${rowPrefix}-${index}`} aria-current={entry.id === activeId ? "page" : undefined}
                onClick={() => openDocument(entry.id)}>
                <span>{entry.label}</span>
                <small id={`${rowPrefix}-${index}`}>{[entry.category, entry.detail].filter(Boolean).join(" · ")}</small>
              </button>
              {worldId && page && onPageTrashed && <WorkspaceTrashControl showTrash={false} deleteLabel={`Move ${page.title} to Trash`}
                worldId={worldId} current={{ kind: "document", id: entry.id, title: page.title, surface: "build", revision: page.revision }}
                blocked={switching || (entry.id === activeDocumentId && activePageTrashBlocked)}
                onTrashed={() => onPageTrashed(entry.id)} />}
            </li>;
            })}</ul> : <p role="status">{pending ? "Loading documents…" : filter ? (loadMorePages ? "No loaded documents match your search." : "No documents match your search.")
              : category === "Recent" ? "Documents you open will appear here." : "No documents in this category."}</p>}
            {loadMorePages && (filter || category === "Pages" || category === "All documents") &&
              <button type="button" disabled={listStatus !== "ready" || switching} onClick={loadMorePages}>
                Load more pages
              </button>}
          </section>
        </div>
      </dialog>
    </div>
  );
}

const PICKER_CATEGORIES = ["Recent", "All documents", "Pages", "Statblocks", "PDFs", "Recaps", "Ingested text"] as const;
type PickerCategory = typeof PICKER_CATEGORIES[number];
type PickerEntry = { id: string; label: string; category: PickerCategory; detail?: string };

function readRecent(key: string): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? "[]");
    return Array.isArray(value) ? value.filter((id): id is string => typeof id === "string") : [];
  } catch {
    return [];
  }
}

function isBuildKnownCampaignId(value: string): value is BuildKnownCampaignId {
  return (BUILD_KNOWN_CAMPAIGN_IDS as readonly string[]).includes(value);
}
