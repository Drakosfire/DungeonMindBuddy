import { getNativeSourceCatalog, readNativeSource } from "../api/liveApi";
import { sameInspectionPin } from "../api/nativeGraphInspection";
import type { NativeSourceMetadata } from "../api/nativeSourceInspection";

export function nativeDocumentHref(worldId: string, source: NativeSourceMetadata) {
  return "/build?" + new URLSearchParams({
    world: worldId, nativeDocument: source.source_revision.source_revision_id,
  });
}

export async function loadNativeDocuments(worldId: string, signal: AbortSignal) {
  const packet = await getNativeSourceCatalog({
    managed_world_id: worldId, scope_mode: "world", campaign_id: null,
  }, signal);
  const { scope, catalogue } = packet;
  if (packet.schema !== "dmb_native_source_catalog_v1" || scope.managed_world_id !== worldId ||
    scope.scope_mode !== "world" || scope.campaign_id !== null ||
    catalogue.space_id !== scope.native_world_id || catalogue.revision_id !== scope.revision_id) {
    throw new Error("The World changed. Reopen the document.");
  }
  return { scope, sources: catalogue.sources.filter(source => source.navigation && source.evidence_ref_ids[0]) };
}

export async function readBuildNativeDocument(worldId: string, revisionId: string, signal: AbortSignal) {
  const { scope, sources } = await loadNativeDocuments(worldId, signal);
  const source = sources.find(entry => entry.source_revision.source_revision_id === revisionId);
  if (!source) throw new Error("This document is unavailable in the selected World.");
  const evidenceId = source.evidence_ref_ids[0];
  const artifactId = source.source_artifact.source_artifact_id;
  const packet = await readNativeSource(scope, {
    source_artifact_id: artifactId, source_revision_id: revisionId, evidence_ref_id: evidenceId,
  }, signal);
  const body = packet.source;
  if (packet.schema !== "dmb_native_source_body_v1" || !sameInspectionPin(packet.scope, scope) ||
    body.status !== "available" || typeof body.body_text !== "string" ||
    body.source_artifact_id !== artifactId || body.source_revision_id !== revisionId ||
    body.evidence_ref_id !== evidenceId || body.body_sha256 !== source.source_revision.content_sha256) {
    throw new Error("The exact document revision is unavailable.");
  }
  return { title: source.navigation.label ?? "Unnamed document", markdown: body.body_text };
}
