import { useLayoutEffect, useRef, useState } from "react";
import { getAgentSourcePassage } from "../../api/liveApi";
import type { WorldBuildGraphCompletionV2, SurfaceSourceCompletionV1, SurfaceEvidenceCompletion } from "../../api/types";
import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";

import {exact,canonical} from "../../shared/sourcePassageProtocol";
export {isBuildSourceCompletion,isSurfaceSourceCompletion} from "../../shared/sourcePassageProtocol";

export function BuildSourcePassageEvidence({ completion, worldId, turnId, segmentIndex, showClaimText = true }: {
  completion: WorldBuildGraphCompletionV2 | SurfaceSourceCompletionV1 | SurfaceEvidenceCompletion; worldId: string; turnId: string; segmentIndex?: number; showClaimText?: boolean;
}) {
  const epoch = useRef(0);
  const [opened, setOpened] = useState<{index: number; status: "loading" | "ready" | "unavailable"; content?: string} | null>(null);
  const [visible, setVisible] = useState(8);
  const identity = `${worldId}/${turnId}/${segmentIndex ?? "all"}/${canonical(completion)}`;
  useLayoutEffect(() => { epoch.current++; setOpened(null); setVisible(8); return () => { epoch.current++; }; }, [identity]);
  const seen = new Set<string>();
  const choices = completion.source_citations.flatMap((citation, index) => {
    if (segmentIndex !== undefined && citation.segment_index !== segmentIndex) return [];
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
      {showClaimText ? <p>{completion.answer_segments[citation.segment_index]?.text}</p> : null}
      <button type="button" onClick={() => { void open(index); }}>{"source_name" in citation ? `Read ${citation.source_name} · ${citation.receipt.line_start === null ? "passage" : `lines ${citation.receipt.line_start}–${citation.receipt.line_end}`}` : `Read passage ${choice + 1}`}</button>
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
