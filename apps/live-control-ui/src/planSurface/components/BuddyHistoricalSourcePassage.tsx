import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getWorldAgentHistoricalSourcePassage } from '../../api/liveApi'
import { getReadWaveVersion, subscribeReadWave } from '../../api/inFlightReads'
import type { BuddyHistoricalSourceReference, BuddyTraceSourcePassage } from '../../api/buddyContextTraceTypes'

function identity(ref: BuddyHistoricalSourceReference) {
  return JSON.stringify([ref.schema, ref.world_id, ref.conversation_id, ref.turn_id, ref.attempt,
    ref.trace_id, ref.source_read_event_id, ref.source_read_id, ref.content_sha256])
}

export function BuddyHistoricalSourcePassage({ reference, load = getWorldAgentHistoricalSourcePassage }: {
  reference: BuddyHistoricalSourceReference; load?: typeof getWorldAgentHistoricalSourcePassage
}) {
  const wave = useSyncExternalStore(subscribeReadWave, getReadWaveVersion, getReadWaveVersion)
  const key = JSON.stringify([identity(reference), wave])
  const currentKey = useRef(key)
  currentKey.current = key
  const [open, setOpen] = useState(false)
  const [saved, setSaved] = useState<{ key: string; passage: BuddyTraceSourcePassage } | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (saved?.key !== key) setSaved(null)
    if (!open || saved?.key === key) return
    let active = true
    const controller = new AbortController()
    const owns = () => active && currentKey.current === key && getReadWaveVersion() === wave
    setFailure(null)
    void load(reference, controller.signal).then(async data => {
      if (!owns()) return
      const passage = data.passage
      if (data.schema !== 'dmb_agent_historical_source_passage_v1' || !data.reference
        || identity(data.reference) !== identity(reference) || !passage || passage.kind !== 'source_passage'
        || passage.world_id !== reference.world_id || passage.source_read_event_id !== reference.source_read_event_id
        || passage.source_read_id !== reference.source_read_id || passage.content_sha256 !== reference.content_sha256
        || (passage.source_name != null && typeof passage.source_name !== 'string')
        || typeof passage.text !== 'string' || [...passage.text].length !== passage.returned_chars
        || passage.returned_chars < 1 || passage.returned_chars > 12000
        || new TextEncoder().encode(JSON.stringify(data)).byteLength > 65536) throw new Error('provenance')
      const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(passage.text))),
        byte => byte.toString(16).padStart(2, '0')).join('')
      if (digest !== reference.content_sha256) throw new Error('digest')
      if (owns()) setSaved({key, passage})
    }).catch(() => { if (owns()) setFailure(key) })
    return () => { active = false; controller.abort() }
  }, [open, key, load, retry, wave])
  // A new access/read wave hides already displayed private bytes before effect cleanup.
  return <details className="buddy-context-trace__source" onToggle={event => setOpen(event.currentTarget.open)}>
    <summary>Source memory from an earlier turn</summary>
    {saved?.key === key ? <><p>{saved.passage.source_name?.trim() || 'Source name unavailable'}</p>
      {saved.passage.line_start != null && <p>{saved.passage.line_start === saved.passage.line_end
        ? `Line ${saved.passage.line_start}` : `Lines ${saved.passage.line_start}–${saved.passage.line_end}`}</p>}
      <blockquote>{saved.passage.text}</blockquote>
      <p>Exact earlier passage retained in context before compaction. Historical memory grants no current-turn citation authority.</p>
      <details><summary>Pinned source reference</summary><pre>{JSON.stringify({
        source_artifact: saved.passage.source_artifact_id, source_revision: saved.passage.source_revision_id,
        content_sha256: saved.passage.content_sha256,
      }, null, 2)}</pre></details></>
      : failure === key ? <><p role="alert">Earlier captured passage is unavailable.</p><button type="button" onClick={()=>setRetry(value=>value+1)}>Retry passage read</button></>
      : <p role="status">Reading the original source capture…</p>}
  </details>
}
