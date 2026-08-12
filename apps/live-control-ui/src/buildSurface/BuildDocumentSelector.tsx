import { useMemo, type ChangeEvent } from "react";

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
  documents: WorkspaceDocumentRecord[] | null;
  listStatus: BuildDocumentListStatus;
  activeDocumentId: string | null;
  activeRecord: WorkspaceDocumentRecord | null;
  preferredCampaignId: string | null;
  switching: boolean;
  onSelect: (documentId: string) => void;
}

export function BuildDocumentSelector({
  documents,
  listStatus,
  activeDocumentId,
  activeRecord,
  preferredCampaignId,
  switching,
  onSelect,
}: BuildDocumentSelectorProps) {
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
      const bucket = byCampaign.get(record.campaign_id) ?? [];
      bucket.push(record);
      byCampaign.set(record.campaign_id, bucket);
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
        label: formatReviewCampaignLabel(campaignId),
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
      const orphanCampaign = activeRecord.campaign_id;
      groups.unshift({
        campaignId: orphanCampaign,
        label: formatReviewCampaignLabel(orphanCampaign),
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
    "aria-label": "Worldbuilding source",
    value: activeDocumentId ?? "",
    onChange: (event: ChangeEvent<HTMLSelectElement>) => {
      const next = event.target.value.trim();
      if (next) onSelect(next);
    },
    disabled: listStatus !== "ready" || switching,
  };

  return (
    <div
      className="build-document-selector build-document-selector--context"
      data-testid="build-document-selector"
      aria-busy={switching}
    >
      <SurfaceContextSelect {...selectProps}>
        {!activeDocumentId ? (
          <option value="" disabled>
            Choose source
          </option>
        ) : null}
        {groupedOptions.map((group) => (
          <optgroup key={group.campaignId} label={group.label}>
            {group.options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </optgroup>
        ))}
      </SurfaceContextSelect>
    </div>
  );
}

function isBuildKnownCampaignId(value: string): value is BuildKnownCampaignId {
  return (BUILD_KNOWN_CAMPAIGN_IDS as readonly string[]).includes(value);
}
