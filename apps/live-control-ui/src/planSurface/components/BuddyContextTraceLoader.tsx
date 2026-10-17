import { useEffect, useRef, useState } from 'react'
import { getWorldAgentTurnContextTrace } from '../../api/liveApi'
import type { WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { BuddyContextTrace } from './BuddyContextTrace'
import { BuddyPromptInspector } from './BuddyPromptInspector'

interface Props {
  promptOnly?: boolean
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
  running?: boolean
  load?: typeof getWorldAgentTurnContextTrace
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId, running = false, load = getWorldAgentTurnContextTrace, promptOnly = false }: Props) {
  const key = `${worldId}\u001f${conversationId}\u001f${turnId}`
  const [loaded, setLoaded] = useState<{ key: string; data: WorldAgentTurnContextTraceResponse } | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const [retry, setRetry] = useState(0)
  const cache = useRef(loaded)
  const handledRetry = useRef(0)
  useEffect(() => {
    if (!enabled) return
    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined
    const isRecording = (data: WorldAgentTurnContextTraceResponse) => {
      const latest = data.attempts.at(-1)
      return latest != null ? latest.closed_at == null : running
    }
    const read = () => void load(worldId, turnId).then(data => {
      if (!active) return
      if (data.schema !== 'dmb_agent_turn_context_trace_response_v1' || data.world_id !== worldId
        || data.turn_id !== turnId || !Array.isArray(data.attempts)
        || data.attempts.some(trace => trace.schema !== 'dmb_turn_context_trace_v1' || trace.world_id !== worldId
          || trace.turn_id !== turnId || trace.conversation_id !== conversationId)) {
        throw new Error('Trace does not match this conversation turn.')
      }
      const next = { key, data }
      cache.current = next
      setLoaded(next)
      setFailure(null)
      if (isRecording(data)) timer = setTimeout(read, 2000)
    }).catch(() => {
      if (active) setFailure({ key, message: 'Execution trace is unavailable. The message will not be resent.' })
    })
    const explicitRetry = handledRetry.current !== retry
    handledRetry.current = retry
    if (cache.current?.key !== key || explicitRetry) {
      setFailure(null)
      read()
    } else if (isRecording(cache.current.data)) {
      timer = setTimeout(read, 2000)
    }
    return () => { active = false; clearTimeout(timer) }
  }, [enabled, key, worldId, turnId, conversationId, running, load, retry])
  if (!enabled) return null
  const error = failure?.key === key ? <div><p role="alert">{failure.message}</p><button type="button" onClick={() => setRetry(value => value + 1)}>Retry trace read</button></div> : null
  if (error && loaded?.key !== key) return error
  if (loaded?.key !== key) return <p role="status">Loading execution trace…</p>
  const attempts = loaded.data.attempts
  if (!attempts.length) return <div>{error}{running
    ? <p role="status">Trace capture has not started yet.</p>
    : promptOnly ? <BuddyPromptInspector trace={null} /> : <BuddyContextTrace trace={null} />}</div>
  return <div>{error}{attempts.map((trace, index) => index === attempts.length - 1
    ? promptOnly ? <BuddyPromptInspector key={trace.trace_id} trace={trace} /> : <BuddyContextTrace key={trace.trace_id} trace={trace} />
    : <details key={trace.trace_id}><summary>Earlier attempt {trace.attempt} · {trace.terminal_status ?? 'recording'}</summary>{promptOnly ? <BuddyPromptInspector trace={trace} /> : <BuddyContextTrace trace={trace} />}</details>)}</div>
}
