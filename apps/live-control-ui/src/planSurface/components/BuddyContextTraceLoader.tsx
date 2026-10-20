import { deferredComponent } from '../../ui/deferredComponent'
import { useBuddyTurnInspection } from './BuddyTurnInspection'

const BuddyContextTrace = deferredComponent(() => import('./BuddyContextTrace').then(module => ({default: module.BuddyContextTrace})), 'execution trace')
const BuddyPromptInspector = deferredComponent(() => import('./BuddyPromptInspector').then(module => ({default: module.BuddyPromptInspector})), 'captured request')

interface Props {
  promptOnly?: boolean
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId, promptOnly = false }: Props) {
  const { data, error: message, refresh, running } = useBuddyTurnInspection({ worldId, conversationId, turnId }, enabled)
  if (!enabled) return null
  const error = message ? <div><p role="alert">{message}</p><button type="button" onClick={refresh}>Retry trace read</button></div> : null
  if (error && !data) return error
  if (!data) return <p role="status">Loading execution trace…</p>
  const attempts = data.attempts
  return <div>{error}<p>Captured observation · <button type="button" onClick={refresh}>Refresh trace</button></p>
    {!attempts.length ? running ? <p role="status">Trace capture has not started yet.</p> : promptOnly ? <BuddyPromptInspector trace={null} /> : <BuddyContextTrace trace={null} />
      : attempts.map((trace, index) => index === attempts.length - 1
        ? promptOnly ? <BuddyPromptInspector key={trace.trace_id} trace={trace} /> : <BuddyContextTrace key={trace.trace_id} trace={trace} />
        : <details key={trace.trace_id}><summary>Earlier attempt {trace.attempt} · {trace.terminal_status ?? 'recording'}</summary>{promptOnly ? <BuddyPromptInspector trace={trace} /> : <BuddyContextTrace trace={trace} />}</details>)}
  </div>
}
