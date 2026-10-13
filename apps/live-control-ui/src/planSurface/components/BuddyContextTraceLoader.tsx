import { useEffect, useState } from 'react'
import { getWorldAgentTurnContextTrace } from '../../api/liveApi'
import type { WorldAgentTurnContextTraceResponse } from '../../api/buddyContextTraceTypes'
import { BuddyContextTrace } from './BuddyContextTrace'

interface Props {
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
  load?: typeof getWorldAgentTurnContextTrace
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId, load = getWorldAgentTurnContextTrace }: Props) {
  const key = `${worldId}\u001f${conversationId}\u001f${turnId}`
  const [loaded, setLoaded] = useState<{ key: string; data: WorldAgentTurnContextTraceResponse } | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const [retry, setRetry] = useState(0)
  useEffect(() => {
    if (!enabled || loaded?.key === key) return
    let active = true
    setFailure(null)
    void load(worldId, turnId).then(data => {
      if (!active) return
      if (data.schema !== 'dmb_agent_turn_context_trace_response_v1' || data.world_id !== worldId
        || data.turn_id !== turnId || !Array.isArray(data.attempts)
        || data.attempts.some(trace => trace.schema !== 'dmb_turn_context_trace_v1' || trace.world_id !== worldId
          || trace.turn_id !== turnId || trace.conversation_id !== conversationId)) {
        throw new Error('Trace does not match this conversation turn.')
      }
      setLoaded({ key, data })
    }).catch(() => {
      if (active) setFailure({ key, message: 'Execution trace is unavailable. The message will not be resent.' })
    })
    return () => { active = false }
  }, [enabled, key, worldId, turnId, conversationId, load, retry, loaded?.key])
  if (!enabled) return null
  if (failure?.key === key) return <div><p role="alert">{failure.message}</p><button type="button" onClick={() => setRetry(value => value + 1)}>Retry trace read</button></div>
  if (loaded?.key !== key) return <p role="status">Loading execution trace…</p>
  const attempts = loaded.data.attempts
  if (!attempts.length) return <BuddyContextTrace trace={null} />
  return <div>{attempts.map((trace, index) => index === attempts.length - 1
    ? <BuddyContextTrace key={trace.trace_id} trace={trace} />
    : <details key={trace.trace_id}><summary>Earlier attempt {trace.attempt} · {trace.terminal_status ?? 'recording'}</summary><BuddyContextTrace trace={trace} /></details>)}</div>
}
