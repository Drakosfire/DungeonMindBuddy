import { useLayoutEffect, useRef, useState } from "react";
import { getAgentSourcePassage } from "../../api/liveApi";
import type { WorldBuildGraphCompletionV2 } from "../../api/types";
import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";

type ObjectValue = Record<string, unknown>;
const record = (v: unknown): v is ObjectValue => !!v && typeof v === "object" && !Array.isArray(v);
const exact = (v: unknown, keys: string[]): v is ObjectValue => record(v)
  && Object.keys(v).length === keys.length && keys.every(key => key in v);
const digest = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v);
const boundedText = (v: unknown, max: number): v is string => typeof v === "string" && !!v.trim() && v.length <= max;

/** Closed V2 presentation shape. APP independently owns actual receipt authorization. */
export function isBuildSourceCompletion(value: unknown, receiptHash: string, sourceHash: string): value is WorldBuildGraphCompletionV2 {
  if (!exact(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status", "answer_segments", "citation_map", "source_citations"])
    || value.schema !== "dmb_build_graph_completion_v2" || value.context_receipt_sha256 !== receiptHash
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
    } else if (segment.kind === "saved_source_claim") {
      if (!exact(segment, ["kind", "text", "content_sha256"]) || segment.content_sha256 !== sourceHash) return false;
      saved = true;
    } else return false;
  }
  if (value.answer_basis !== (saved ? "saved_source_and_opened_passages" : "opened_source_passages")) return false;
  if (value.answer_context_status === "source_insufficient_evidence" ? (claimIndices.size > 0 || saved) : !claimIndices.size) return false;
  const cited = new Set<number>(), seen = new Set<string>();
  for (const citation of value.source_citations) {
    if (!exact(citation, ["segment_index", "text_sha256", "provider_attempt_id", "envelope_sha256", "read_event_id", "receipt"])
      || !Number.isSafeInteger(citation.segment_index) || !claimIndices.has(citation.segment_index as number)
      || !digest(citation.text_sha256) || !digest(citation.envelope_sha256)
      || !uuid(citation.provider_attempt_id) || !uuid(citation.read_event_id)) return false;
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

function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (record(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

export function BuildSourcePassageEvidence({ completion, worldId, turnId }: {
  completion: WorldBuildGraphCompletionV2; worldId: string; turnId: string;
}) {
  const epoch = useRef(0);
  const [opened, setOpened] = useState<{index: number; status: "loading" | "ready" | "unavailable"; content?: string} | null>(null);
  const [visible, setVisible] = useState(8);
  const identity = `${worldId}/${turnId}/${canonical(completion)}`;
  useLayoutEffect(() => { epoch.current++; setOpened(null); setVisible(8); return () => { epoch.current++; }; }, [identity]);
  const seen = new Set<string>();
  const choices = completion.source_citations.flatMap((citation, index) => {
    const r = citation.receipt;
    const key = canonical([citation.segment_index, r.source_artifact_id, r.source_revision_id, r.content_sha256, r.line_start, r.line_end]);
    if (seen.has(key)) return [];
    seen.add(key); return [{citation, index}];
  });
  async function open(index: number) {
    const requestEpoch = ++epoch.current;
    const citation = completion.source_citations[index]!;
    setOpened({index, status: "loading"});
    try {
      const result = await getAgentSourcePassage(worldId, turnId, index);
      if (requestEpoch !== epoch.current) return;
      if (!exact(result, ["schema", "target", "citation", "content"]) || result.schema !== "dmb_agent_source_passage_read_v1"
        || !exact(result.target, ["schema", "kind", "world_id", "turn_id", "citation_index"])
        || result.target.schema !== "dmb_agent_source_passage_open_target_v1" || result.target.kind !== "source_passage"
        || result.target.world_id !== worldId || result.target.turn_id !== turnId || result.target.citation_index !== index
        || canonical(result.citation) !== canonical(citation) || typeof result.content !== "string"
        || [...result.content].length !== citation.receipt.returned_chars) throw new Error("Source binding differs");
      const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(result.content));
      const actual = Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, "0")).join("");
      if (actual !== citation.receipt.content_sha256) throw new Error("Source digest differs");
      if (requestEpoch === epoch.current) setOpened({index, status: "ready", content: result.content});
    } catch {
      if (requestEpoch === epoch.current) setOpened({index, status: "unavailable"});
    }
  }
  return <section aria-label="Source passages">
    {!choices.length ? <p>No passage-backed claims were made in this answer.</p> : null}
    {choices.slice(0, visible).map(({citation, index}, choice) => <div key={index}>
      <p>{completion.answer_segments[citation.segment_index]?.text}</p>
      <button type="button" onClick={() => { void open(index); }}>Read passage {choice + 1}</button>
    </div>)}
    {visible < choices.length ? <button type="button" onClick={() => setVisible(v => v + 8)}>Show more passages</button> : null}
    {opened ? <section aria-label="Opened source passage" aria-live="polite">
      <button type="button" onClick={() => { epoch.current++; setOpened(null); }}>Close passage</button>
      {opened.status === "loading" ? <p>Opening passage…</p> : opened.status === "unavailable"
        ? <p>The exact cited passage is unavailable. No newer text has been substituted.</p>
        : <WorldPlanAgentAnswer answer={opened.content ?? ""} />}
    </section> : null}
  </section>;
}
