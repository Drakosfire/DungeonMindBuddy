import { useEffect, useMemo, useState, type ChangeEvent } from "react";

import { readRetainedPdfDocuments, retainedPdfBuildHref } from "../api/retainedPdfRegions";
import { listWorldThreatDrafts, type WorldThreatDraftSummary } from "../api/liveApi";
import { buildSavedStatblockHref, readSavedStatblockTarget } from "../statblocks/savedStatblockLocation";
import type { WorkspaceDocumentRecord } from "../api/types";
import { formatReviewCampaignLabel } from "../graphLens/sessionCampaignContext";
import { SurfaceContextSelect } from "../surfaceInteraction/contextHost";
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
  const statblocks = (currentCatalog?.drafts ?? []).flatMap(draft => {
    const revisionId = draft.saved_revision_id;
    if (draft.world_id !== worldId || !revisionId || !draft.name.toLowerCase().includes(filter)) return [];
    return [{
      href: buildSavedStatblockHref({ worldId: draft.world_id, draftId: draft.draft_id, revisionId }),
      title: draft.name,
    }];
  });
  const retainedPdfs = worldId ? readRetainedPdfDocuments(worldId) : [];
  const activePdf = retainedPdfs.find(entry => entry.locator.source_revision_id ===
    new URLSearchParams(window.location.search).get("pdf"));
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

  const selectProps = {
    id: "build-document-select",
    "data-testid": "build-document-select",
    "data-guided-control": "source",
    "aria-label": "Open document",
    value: activePdf && worldId ? retainedPdfBuildHref(worldId, activePdf) : activeStatblock ? buildSavedStatblockHref(activeStatblock) : activeDocumentId ?? "",
    onChange: (event: ChangeEvent<HTMLSelectElement>) => {
      const next = event.target.value.trim();
      if (next.startsWith("/build?")) window.location.assign(next);
      else if (next && worldId && (activeStatblock || new URLSearchParams(window.location.search).has("pdf"))) {
        window.location.assign("/build?" + new URLSearchParams({ world: worldId, documentId: next }));
      } else if (next) onSelect(next);
    },
    disabled: switching || (listStatus !== "ready" && statblocks.length === 0 && retainedPdfs.length === 0),
  };

  return (
    <div
      className="build-document-selector build-document-selector--context"
      data-testid="build-document-selector"
      aria-busy={switching}
    >
      <input type="search" aria-label="Search documents" placeholder="Search documents"
        value={query} onChange={event => setQuery(event.target.value)} />
      {currentCatalog?.error && <span role="status">Saved statblocks unavailable</span>}
      <SurfaceContextSelect {...selectProps}>
        {!activeDocumentId ? (
          <option value="" disabled>
            Open document
          </option>
        ) : null}
        {groupedOptions.map((group) => (
          <optgroup key={group.campaignId} label={group.label}>
            {group.options.filter(option => option.id === activeDocumentId || option.label.toLowerCase().includes(filter)).map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </optgroup>
        ))}
        {statblocks.length > 0 && <optgroup label="Saved statblocks">
          {statblocks.map(item => <option key={item.href} value={item.href}>{item.title}</option>)}
        </optgroup>}
        {worldId && retainedPdfs.length > 0 && <optgroup label="PDF documents">
          {retainedPdfs.filter(entry => entry === activePdf || entry.name.toLowerCase().includes(filter)).map(entry => {
            const href = retainedPdfBuildHref(worldId, entry);
            return <option key={href} value={href}>{entry.name}</option>;
          })}
        </optgroup>}
      </SurfaceContextSelect>
    </div>
  );
}

function isBuildKnownCampaignId(value: string): value is BuildKnownCampaignId {
  return (BUILD_KNOWN_CAMPAIGN_IDS as readonly string[]).includes(value);
}
