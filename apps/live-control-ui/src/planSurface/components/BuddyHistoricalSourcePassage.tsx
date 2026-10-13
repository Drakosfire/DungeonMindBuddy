import { useEffect, useState } from 'react'
import { getWorldAgentTurnContextTrace } from '../../api/liveApi'
import type { BuddyHistoricalSourceReference, BuddyTraceSourcePassage } from '../../api/buddyContextTraceTypes'

export function BuddyHistoricalSourcePassage({ reference, load = getWorldAgentTurnContextTrace }: {
  reference: BuddyHistoricalSourceReference; load?: typeof getWorldAgentTurnContextTrace
}) {
  const key = JSON.stringify(reference)
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState<{ key: string; passage: BuddyTraceSourcePassage } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!open || saved?.key === key) return
    let active = true
    setFailure(null)
    void load(reference.world_id, reference.turn_id).then(data => {
      if (!active) return
      if (data.world_id !== reference.world_id || data.turn_id !== reference.turn_id) throw new Error('scope')
      const matches = data.attempts.filter(trace => trace.world_id === reference.world_id
        && trace.conversation_id === reference.conversation_id && trace.turn_id === reference.turn_id
        && trace.attempt === reference.attempt && trace.trace_id === reference.trace_id)
        .flatMap(trace => trace.observations.filter((item): item is BuddyTraceSourcePassage =>
          item.kind === 'source_passage' && item.world_id === reference.world_id
          && item.source_read_event_id === reference.source_read_event_id
          && item.source_read_id === reference.source_read_id && item.content_sha256 === reference.content_sha256))
      if (matches.length !== 1) throw new Error('provenance')
      setSaved({key, passage:matches[0]})
    }).catch(() => { if (active) setFailure(key) })
    return () => { active = false }
  }, [open, key, reference.world_id, reference.turn_id, reference.conversation_id, reference.attempt,
    reference.trace_id, reference.source_read_event_id, reference.source_read_id, reference.content_sha256, load, retry, saved?.key])
  return <details className="buddy-context-trace__source" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Source memory from an earlier turn</summary>
    {saved?.key === key ? <><p>{saved.passage.source_artifact_id}</p><blockquote>{saved.passage.text}</blockquote>
      <p>Exact earlier passage retained in context before compaction. Historical memory grants no current-turn citation authority.</p></>
      : failure === key ? <><p role="alert">Earlier captured passage is unavailable.</p><button type="button" onClick={()=>setRetry(value=>value+1)}>Retry source trace read</button></>
      : <p role="status">Reading the original source capture…</p>}
  </details>
}
