import { useEffect, useState } from 'react';
import type { RulesAnswerContext } from '../api/rulesLookupTypes';
import { RulesHistoricalCitation } from './RulesHistoricalCitation';

/** Receives only a validated accepted map; controls derive from server identity, never Markdown URLs. */
export function RulesAnswerEvidence({ context, answer, active = true }: { context: RulesAnswerContext; answer: string; active?: boolean }) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => { if (!active) setExpanded(false); }, [active]);
  if (!active) return null;
  const b = context.accepted_binding, chars = Array.from(answer);
  if (!b.support_table.length) return null;
  return <details open={expanded} onToggle={event => setExpanded(event.currentTarget.open)}><summary>Rules references</summary>{expanded && b.support_table.map(source => <div key={source.support_id}>
    {b.segment_map.filter(segment => segment.support_refs.some(ref => ref.support_id === source.support_id))
      .map(segment => <blockquote key={segment.ordinal}>{chars.slice(segment.text_start, segment.text_end).join('')}</blockquote>)}
    <RulesHistoricalCitation label={source.source_label} target={{ worldId: b.world_id, conversationId: b.conversation_id,
      turnId: b.turn_id, attempt: b.product_attempt, supportId: source.support_id, supportSha256: source.support_sha256 }} />
  </div>)}</details>;
}
