import type {WorldBuildSourceCompletion,SurfaceSourceCompletionV1} from "../api/types";

type ObjectValue = Record<string, unknown>;
const record = (v: unknown): v is ObjectValue => !!v && typeof v === "object" && !Array.isArray(v);
export const exact = (v: unknown, keys: string[]): v is ObjectValue => record(v)
  && Object.keys(v).length === keys.length && keys.every(key => key in v);
const digest = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v);
const boundedText = (v: unknown, max: number): v is string => typeof v === "string" && !!v.trim() && v.length <= max;

/** Closed V2 presentation shape. APP independently owns actual receipt authorization. */
export function isBuildSourceCompletion(value: unknown, receiptHash: string, sourceHash: string): value is WorldBuildSourceCompletion {
  return isSourceCompletion(value, receiptHash, sourceHash);
}
export function isSurfaceSourceCompletion(value: unknown, receiptHash: string, surface: "plan"|"play"): value is SurfaceSourceCompletionV1 {
  return isSourceCompletion(value, receiptHash, undefined, surface);
}
function isSourceCompletion(value: unknown, receiptHash: string, sourceHash?: string, surface?: "plan"|"play"): boolean {
  const named = surface !== undefined || (record(value) && value.schema === "dmb_build_graph_completion_v3");
  if (!exact(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status", "answer_segments", "citation_map", "source_citations", ...(surface ? ["surface_id"] : [])])
    || value.schema !== (surface ? "dmb_surface_source_completion_v1" : named ? "dmb_build_graph_completion_v3" : "dmb_build_graph_completion_v2") || (surface && value.surface_id !== surface) || value.context_receipt_sha256 !== receiptHash
    || value.citation_map !== null || !Array.isArray(value.answer_segments) || !value.answer_segments.length
    || value.answer_segments.length > 128 || !Array.isArray(value.source_citations) || value.source_citations.length > 16384
    || !["source_grounded", "source_grounded_partial", "source_insufficient_evidence"].includes(String(value.answer_context_status))) return false;
  const claimIndices = new Set<number>();
  let saved = false;
  for (const [index, segment] of value.answer_segments.entries()) {
    if (!record(segment) || !boundedText(segment.text, 4000)) return false;
    if (segment.kind === "source_passage_claim" || segment.kind === "connective") {
      if (!exact(segment, ["kind", "text"])) return false;
      if (segment.kind === "source_passage_claim") claimIndices.add(index);
    } else if (surface && segment.kind === "proposal") {
      if (!exact(segment, ["kind", "text", "label"]) || !["invented_idea", "image_prompt"].includes(String(segment.label))) return false;
    } else if (!surface && segment.kind === "saved_source_claim") {
      if (!exact(segment, ["kind", "text", "content_sha256"]) || segment.content_sha256 !== sourceHash) return false;
      saved = true;
    } else return false;
  }
  if (value.answer_basis !== (saved ? "saved_source_and_opened_passages" : "opened_source_passages")) return false;
  if ((surface && !["source_grounded", "source_grounded_partial"].includes(String(value.answer_context_status))) || (value.answer_context_status === "source_insufficient_evidence" ? (claimIndices.size > 0 || saved) : !claimIndices.size)) return false;
  const cited = new Set<number>(), seen = new Set<string>();
  for (const citation of value.source_citations) {
    if (!exact(citation, ["segment_index", "text_sha256", "provider_attempt_id", "envelope_sha256", "read_event_id", "receipt", ...(named ? ["source_name"] : [])])
      || !Number.isSafeInteger(citation.segment_index) || !claimIndices.has(citation.segment_index as number)
      || !digest(citation.text_sha256) || !digest(citation.envelope_sha256)
      || !uuid(citation.provider_attempt_id) || !uuid(citation.read_event_id)
      || (named && (typeof citation.source_name !== "string" || !citation.source_name.trim()))) return false;
    const r = citation.receipt;
    if (!exact(r, ["source_read_id", "anchor_id", "evidence_ref_id", "source_artifact_id", "source_revision_id", "outcome", "content_sha256", "line_start", "line_end", "returned_chars", "truncated", "evidence_sufficiency_status"])
      || !boundedText(r.source_read_id, 128) || !boundedText(r.anchor_id, 256)
      || !boundedText(r.evidence_ref_id, 1024) || !boundedText(r.source_artifact_id, 256)
      || !boundedText(r.source_revision_id, 256) || !digest(r.content_sha256)
      || r.outcome !== "enough" || r.truncated !== false || r.evidence_sufficiency_status !== "sufficient"
      || !Number.isSafeInteger(r.returned_chars) || (r.returned_chars as number) < 1 || (r.returned_chars as number) > 12000
      || !((r.line_start === null && r.line_end === null) || (Number.isSafeInteger(r.line_start)
        && Number.isSafeInteger(r.line_end) && (r.line_start as number) > 0 && (r.line_end as number) >= (r.line_start as number)))) return false;
    const key = `${citation.segment_index}/${citation.read_event_id}/${r.source_read_id}`;
    if (seen.has(key)) return false;
    seen.add(key); cited.add(citation.segment_index as number);
  }
  return cited.size === claimIndices.size;
}

export function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (record(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

