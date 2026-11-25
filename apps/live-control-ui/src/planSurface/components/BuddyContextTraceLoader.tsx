import { deferredComponent } from '../../ui/deferredComponent'
import { useBuddyTurnInspection } from './BuddyTurnInspection'

const BuddyContextTrace = deferredComponent(() => import('./BuddyContextTrace').then(module => ({default: module.BuddyContextTrace})), 'execution trace')

interface Props {
  replyDetails?: boolean
  enabled: boolean
  worldId: string
  turnId: string
  conversationId: string
}

export function BuddyContextTraceLoader({ enabled, worldId, turnId, conversationId, replyDetails }: Props) {
  const { data, error: message, refresh, running } = useBuddyTurnInspection({ worldId, conversationId, turnId }, enabled)
  if (!enabled) return null
  const error = message ? <div><p role="alert">{message}</p><button type="button" onClick={refresh}>Retry trace read</button></div> : null
  if (error && !data) return error
  if (!data) return <p role="status">Loading execution trace…</p>
  const latest = data.attempts.at(-1)
  const earlier = data.attempts.slice(0, -1).reverse()
  const incomplete = !running && (!latest || latest.closed_at == null || latest.capture_status === 'incomplete')
  const captureControls = error ?? ((!replyDetails || incomplete) && <button type="button" onClick={refresh}>Refresh trace</button>)
  return <div>{captureControls}
    {!latest && running ? <p role="status">Trace capture has not started yet.</p>
      : <DebugAttempt key={latest?.trace_id} trace={latest ?? null} running={running} replyDetails={replyDetails} />}
    {earlier.length > 0 && <details>
      <summary>Earlier trace attempts</summary>
      {earlier.map(trace => <details key={trace.trace_id}>
        <summary>Attempt {trace.attempt}</summary>
        <DebugAttempt trace={trace} running={false} replyDetails={replyDetails} />
      </details>)}
    </details>}
  </div>
}

function DebugAttempt({ trace, running, replyDetails }: { trace: import('../../api/buddyContextTraceTypes').BuddyTurnContextTrace | null; running: boolean; replyDetails?: boolean }) {
  return <BuddyContextTrace trace={trace} ownerActive={running} replyDetails={replyDetails} />
}
