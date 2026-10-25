import { useLayoutEffect, useRef, useState } from "react";
import { getAgentSavedSection } from "../../api/liveApi";
import type { SavedBuildSectionTargetV1, WorldBuildGraphReceiptV1 } from "../../api/types";
import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";
import type {CitationChoice} from "./SourceCitationEvidence";

type RecordValue = Record<string, unknown>;
const record = (v: unknown): v is RecordValue => !!v && typeof v === "object" && !Array.isArray(v);
const exact = (v: unknown, keys: string[]): v is RecordValue => record(v)
  && Object.keys(v).length === keys.length && keys.every(k => k in v);
const uuid = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v);
const digest = (v: unknown): v is string => typeof v === "string" && /^[a-f0-9]{64}$/.test(v);
function canonical(v: unknown): string {
  if (Array.isArray(v)) return `[${v.map(canonical).join(",")}]`;
  if (record(v)) return `{${Object.keys(v).sort().map(k => `${JSON.stringify(k)}:${canonical(v[k])}`).join(",")}}`;
  return JSON.stringify(v);
}
export function isSavedSectionTargets(value: unknown, basis: WorldBuildGraphReceiptV1["source_basis"], completion: unknown): value is SavedBuildSectionTargetV1[] {
  if (!Array.isArray(value) || value.length > 16384) return false;
  const segments = record(completion) && Array.isArray(completion.answer_segments) ? completion.answer_segments : [];
  const seen = new Set<string>();
  return value.every(t => {
    if (!exact(t, ["schema", "kind", "world_id", "turn_id", "segment_index", "section_event_id", "section_read_id", "source_basis", "source_class", "line_start", "line_end", "excerpt_sha256", "text_sha256"])
      || t.schema !== "dmb_saved_build_section_target_v1" || t.kind !== "saved_build_section"
      || t.world_id !== basis.world_id || !uuid(t.turn_id) || !uuid(t.section_event_id) || !uuid(t.section_read_id)
      || !Number.isSafeInteger(t.segment_index) || (t.segment_index as number) < 0 || (t.segment_index as number) > 127
      || !Number.isSafeInteger(t.line_start) || !Number.isSafeInteger(t.line_end)
      || (t.line_start as number) < 1 || (t.line_end as number) < (t.line_start as number)
      || !digest(t.excerpt_sha256) || !digest(t.text_sha256)
      || t.source_class !== "saved_authored_source_not_played_truth"
      || canonical(t.source_basis) !== canonical(basis)) return false;
    const segment = segments[t.segment_index as number];
    if (!record(segment) || segment.kind !== "saved_source_claim" || segment.content_sha256 !== basis.content_sha256) return false;
    const key = `${t.turn_id}/${t.segment_index}/${t.section_event_id}`;
    if (seen.has(key)) return false;
    seen.add(key); return true;
  });
}
async function hash(text: string) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
}
export type SavedSectionEvidenceProps = {
  sourceName: string | null;
  targets: SavedBuildSectionTargetV1[]; basis: WorldBuildGraphReceiptV1["source_basis"];
  segments: {kind: string; text: string; content_sha256?: string}[]; worldId: string; turnId: string;
};
export function savedSectionChoices({targets,basis,segments,worldId,turnId,sourceName}:SavedSectionEvidenceProps,isCurrent:()=>boolean=()=>true):CitationChoice[] {
  if(worldId!==basis.world_id || !isSavedSectionTargets(targets,basis,{answer_segments:segments})
    || !targets.every(t=>t.turn_id===turnId))return [];
  return targets.map((target,index)=>({
    key:`saved:${target.segment_index}:${target.section_event_id}`,number:index+1,segmentIndex:target.segment_index,
    title:`${sourceName ?? "Source name unavailable"} · saved revision ${basis.registry_revision} · lines ${target.line_start}–${target.line_end}`,
    label:sourceName ? `Read ${sourceName} · lines ${target.line_start}–${target.line_end}` : `Read saved lines ${target.line_start}–${target.line_end}`,
    kind:'section',load:async()=>{
      if(await hash(segments[target.segment_index]!.text)!==target.text_sha256)throw new Error("Claim differs");
      if(!isCurrent())throw new Error("Source owner retired");
      const result=await getAgentSavedSection(target);
      if(!exact(result,["schema","target","content"]) || result.schema!=="dmb_saved_build_section_read_v1"
        || canonical(result.target)!==canonical(target) || typeof result.content!=="string" || !result.content.trim()
        || await hash(result.content)!==target.excerpt_sha256)throw new Error("Historical source differs");
      return result.content;
    },
  }));
}
export function BuildSavedSectionEvidence({targets,basis,segments,worldId,turnId,sourceName}:SavedSectionEvidenceProps) {
  const epoch = useRef(0);
  const [opened, setOpened] = useState<{index: number; status: "loading" | "ready" | "unavailable"; content?: string} | null>(null);
  const [visible, setVisible] = useState(8);
  const identity = canonical({worldId, turnId, targets, basis, segments});
  useLayoutEffect(() => { epoch.current++; setOpened(null); setVisible(8); return () => { epoch.current++; }; }, [identity]);
  const valid = worldId === basis.world_id && isSavedSectionTargets(targets, basis, {answer_segments: segments})
    && targets.every(t => t.turn_id === turnId);
  if (!valid || !targets.length) return null;
  async function open(index: number) {
    const requestEpoch = ++epoch.current;
    setOpened({index, status: "loading"});
    try {
      const choices=savedSectionChoices({targets,basis,segments,worldId,turnId,sourceName},()=>requestEpoch===epoch.current);
      const content=await choices[index]!.load();
      if(requestEpoch===epoch.current)setOpened({index,status:"ready",content});
    } catch { if (requestEpoch === epoch.current) setOpened({index, status: "unavailable"}); }
  }
  return <section aria-label="Saved-source evidence">
    <p>{sourceName ?? "Source name unavailable"} · authored worldbuilding</p>
    {targets.slice(0, visible).map((t, index) => <div key={`${t.segment_index}/${t.section_event_id}`}>
      <p>{segments[t.segment_index]?.text}</p>
      <button type="button" onClick={() => { void open(index); }}>{sourceName ? `Read ${sourceName} · lines ` : "Read saved lines "}{t.line_start}–{t.line_end}</button>
    </div>)}
    {visible < targets.length ? <button type="button" onClick={() => setVisible(v => v + 8)}>Show more saved sections</button> : null}
    {opened ? <section aria-label="Opened saved-source section" aria-live="polite">
      <button type="button" onClick={() => { epoch.current++; setOpened(null); }}>Close saved section</button>
      {opened.status === "loading" ? <p>Opening saved section…</p> : opened.status === "unavailable"
        ? <p>The exact saved section is unavailable. No newer text has been substituted.</p>
        : <WorldPlanAgentAnswer answer={opened.content ?? ""} />}
    </section> : null}
  </section>;
}
