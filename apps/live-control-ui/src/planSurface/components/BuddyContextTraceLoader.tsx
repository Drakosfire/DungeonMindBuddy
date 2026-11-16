import { deferredComponent } from '../../ui/deferredComponent'
import { useBuddyTurnInspection } from './BuddyTurnInspection'

const BuddyContextTrace = deferredComponent(() => import('./BuddyContextTrace').then(module => ({default: module.BuddyContextTrace})), 'execution trace')

interface Props {
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId }: Props) {
  const { data, error: message, refresh, running } = useBuddyTurnInspection({ worldId, conversationId, turnId }, enabled)
  if (!enabled) return null
  const error = message ? <div><p role="alert">{message}</p><button type="button" onClick={refresh}>Retry trace read</button></div> : null
  if (error && !data) return error
  if (!data) return <p role="status">Loading execution trace…</p>
  const attempts = data.attempts
  return <div>{error}{!running && attempts.some(trace => trace.closed_at == null || trace.capture_status === 'incomplete')
    ? <p role="note">The turn has ended, but this saved capture is incomplete. Refresh trace to check for a later capture.</p> : null}<p>Captured observation · <button type="button" onClick={refresh}>Refresh trace</button></p>
    {!attempts.length ? running ? <p role="status">Trace capture has not started yet.</p> : <DebugAttempt trace={null} running={running} />
      : attempts.map((trace, index) => index === attempts.length - 1
        ? <DebugAttempt key={trace.trace_id} trace={trace} running={running} />
        : <details key={trace.trace_id}><summary>Earlier attempt {trace.attempt} · {trace.terminal_status ?? 'recording'}</summary>{<DebugAttempt trace={trace} running={running} />}</details>)}
  </div>
}

function DebugAttempt({ trace, running }: { trace: import('../../api/buddyContextTraceTypes').BuddyTurnContextTrace | null; running: boolean }) {
  return <BuddyContextTrace trace={trace} ownerActive={running} />
}
